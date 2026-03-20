"""
app.py
──────
Main Flask application for Diana Beach Restaurant.

API Endpoints
─────────────
Auth:
  POST /api/auth/register       Register a new user
  POST /api/auth/login          Login, returns JWT token

Dishes (public):
  GET  /api/dishes              List all dishes (optional ?category=)
  GET  /api/dishes/<id>         Get single dish by ID
  GET  /api/categories          List distinct dish categories

Dishes (admin only):
  POST   /api/dishes            Create a new dish
  PUT    /api/dishes/<id>       Update a dish
  DELETE /api/dishes/<id>       Delete a dish

Reviews:
  GET  /api/reviews             List reviews (?dish_id= or ?nationality=)
  POST /api/reviews             Submit a new review (JWT required)

Recommendations:
  GET  /api/recommendations?nationality=   Weighted personalised recommendations

Stats & Admin:
  GET  /api/stats               Public summary stats
  GET  /api/admin/stats         Detailed admin analytics (admin JWT required)
  GET  /api/nationalities       List all nationalities that have left reviews
"""

import logging
import logging.handlers
import os
from datetime import datetime

from bson import ObjectId
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import (JWTManager, jwt_required,
                                get_jwt_identity)
from urllib.parse import quote_plus

from auth import (create_user, find_user_by_email,
                  generate_token, is_admin, verify_password)
from config import config
from database import get_db
from recommendation_engine import get_recommendations

# ─── Logging Setup ────────────────────────────────────────────────────────────

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            'logs/app.log', maxBytes=1_000_000, backupCount=3
        )
    ]
)
logger = logging.getLogger(__name__)

# ─── Flask App Factory ────────────────────────────────────────────────────────

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.JWT_ACCESS_TOKEN_EXPIRES

CORS(app, resources={r'/api/*': {'origins': '*'}})
jwt = JWTManager(app)

# ─── Local Food Images Serving ─────────────────────────────────────────
FOOD_IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FoodImages"))

@app.route("/images/<path:filename>")
def serve_food_images(filename: str):
    """
    Serve dish images stored locally in `diana-v2/FoodImages`.
    Frontend uses `/images/<filename>` URLs returned by the backend.
    """
    return send_from_directory(FOOD_IMAGES_DIR, filename)


# ─── Utilities ────────────────────────────────────────────────────────────────

def _to_oid(id_str: str):
    """Convert a string to MongoDB ObjectId, or return the string on failure."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None


def _serialise_dish(dish: dict, db=None) -> dict:
    """Convert a MongoDB dish document to a JSON-safe dict, including avg rating."""
    if db is None:
        db = get_db()
    reviews = list(db.reviews.find({'dish_id': str(dish['_id'])}, {'_id': 0, 'rating': 1}))
    avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else 0
    return {
        'id': str(dish['_id']),
        'name': dish.get('name', ''),
        'description': dish.get('description', ''),
        'category': dish.get('category', ''),
        'price': dish.get('price', 0),
        'image_url': dish.get('image_url', ''),
        'is_veg': dish.get('is_veg', False),
        'spice_level': dish.get('spice_level', 'Medium'),
        'is_top_seller': dish.get('is_top_seller', False),
        'avg_rating': avg,
        'review_count': len(reviews)
    }


def _serialise_review(r: dict, db=None) -> dict:
    """Convert a MongoDB review document to a JSON-safe dict."""
    if db is None:
        db = get_db()
    dish = db.dishes.find_one({'_id': _to_oid(r.get('dish_id', ''))})
    dish_name = dish['name'] if dish else 'Unknown'
    created = r.get('created_at', datetime.utcnow())
    return {
        'id': str(r['_id']),
        'dish_id': r.get('dish_id', ''),
        'dish_name': dish_name,
        'nationality': r.get('nationality', ''),
        'rating': r.get('rating', 0),
        'comment': r.get('comment', ''),
        'reviewer_name': r.get('reviewer_name', ''),
        'created_at': created.strftime('%Y-%m-%d %H:%M') if hasattr(created, 'strftime') else str(created)
    }


def _validate_fields(data: dict, required: list) -> str | None:
    """Return an error message if any required field is missing, else None."""
    for field in required:
        if field not in data or str(data[field]).strip() == '':
            return f'Missing required field: {field}'
    return None


def _default_image_url(dish_name: str) -> str:
    """
    Generate a reasonable default dish image URL based on dish name.
    Uses Unsplash Source (no API key) with a stable keyword query.
    """
    q = (dish_name or '').strip()
    if not q:
        q = 'food'
    # Prefer common food keywords if present
    low = q.lower()
    keywords = [
        ('biryani', 'biryani'),
        ('biriyani', 'biryani'),
        ('kottu', 'kottu roti'),
        ('lamprais', 'lamprais'),
        ('watalappan', 'watalappan'),
        ('curd', 'curd treacle'),
        ('treacle', 'kithul treacle'),
        ('king coconut', 'king coconut'),
        ('coconut', 'coconut drink'),
        ('lassi', 'mango lassi'),
        ('lemonade', 'lemonade'),
        ('crab', 'garlic crab'),
        ('prawn', 'grilled prawns'),
        ('calamari', 'calamari'),
        ('tuna', 'tuna steak'),
        ('fish', 'fish curry'),
        ('papaya', 'papaya salad'),
        ('spring roll', 'spring rolls'),
        ('rice', 'rice and curry'),
        ('curry', 'sri lankan curry'),
        ('dessert', 'sri lankan dessert'),
    ]
    for needle, kw in keywords:
        if needle in low:
            q = kw
            break
    return f"https://source.unsplash.com/800x600/?{quote_plus(q)}"


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    err = _validate_fields(data, ['name', 'email', 'password'])
    if err:
        return jsonify({'error': err}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400
    try:
        user = create_user(data['name'], data['email'], data['password'])
        token = generate_token(str(user['_id']), user['role'])
        return jsonify({'message': 'Registration successful.', 'token': token,
                        'user': {'name': user['name'], 'email': user['email'], 'role': user['role']}}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 409


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate a user and return a JWT token."""
    data = request.get_json(silent=True) or {}
    err = _validate_fields(data, ['email', 'password'])
    if err:
        return jsonify({'error': err}), 400
    user = find_user_by_email(data['email'])
    if not user or not verify_password(data['password'], user['password_hash']):
        return jsonify({'error': 'Invalid email or password.'}), 401
    token = generate_token(str(user['_id']), user['role'])
    return jsonify({'message': 'Login successful.', 'token': token,
                    'user': {'name': user['name'], 'email': user['email'], 'role': user['role']}})


# ─── Dish Routes ──────────────────────────────────────────────────────────────

@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    """Return all dishes, optionally filtered by category."""
    db = get_db()
    query = {}
    cat = request.args.get('category')
    if cat:
        query['category'] = cat
    dishes = list(db.dishes.find(query))
    return jsonify([_serialise_dish(d, db) for d in dishes])


@app.route('/api/dishes/<dish_id>', methods=['GET'])
def get_dish(dish_id):
    """Return a single dish by its ID."""
    db = get_db()
    dish = db.dishes.find_one({'_id': _to_oid(dish_id)})
    if not dish:
        return jsonify({'error': 'Dish not found.'}), 404
    return jsonify(_serialise_dish(dish, db))


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Return all distinct dish categories."""
    db = get_db()
    cats = db.dishes.distinct('category')
    return jsonify(sorted(cats))


@app.route('/api/dishes', methods=['POST'])
@jwt_required()
def create_dish():
    """Create a new dish. Admin only."""
    if not is_admin():
        return jsonify({'error': 'Admin access required.'}), 403
    data = request.get_json(silent=True) or {}
    err = _validate_fields(data, ['name', 'description', 'category', 'price'])
    if err:
        return jsonify({'error': err}), 400
    try:
        price = float(data['price'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Price must be a number.'}), 400
    db = get_db()
    image_url = (data.get('image_url') or '').strip()
    if not image_url:
        image_url = _default_image_url(data.get('name', ''))
    doc = {
        'name': data['name'].strip(),
        'description': data['description'].strip(),
        'category': data['category'].strip(),
        'price': price,
        'image_url': image_url,
        'is_veg': bool(data.get('is_veg', False)),
        'spice_level': data.get('spice_level', 'Medium'),
        'is_top_seller': bool(data.get('is_top_seller', False)),
        'created_at': datetime.utcnow()
    }
    result = db.dishes.insert_one(doc)
    doc['_id'] = result.inserted_id
    return jsonify(_serialise_dish(doc, db)), 201


@app.route('/api/dishes/<dish_id>', methods=['PUT'])
@jwt_required()
def update_dish(dish_id):
    """Update an existing dish. Admin only."""
    if not is_admin():
        return jsonify({'error': 'Admin access required.'}), 403
    db = get_db()
    oid = _to_oid(dish_id)
    if not oid or not db.dishes.find_one({'_id': oid}):
        return jsonify({'error': 'Dish not found.'}), 404
    data = request.get_json(silent=True) or {}
    allowed = ['name', 'description', 'category', 'price', 'image_url', 'is_veg', 'spice_level', 'is_top_seller']
    updates = {k: v for k, v in data.items() if k in allowed}
    if 'image_url' in updates:
        img = (updates.get('image_url') or '').strip()
        if not img:
            # If admin clears the image, regenerate from name (updated name if provided)
            name_for_img = updates.get('name') or (db.dishes.find_one({'_id': oid}) or {}).get('name', '')
            updates['image_url'] = _default_image_url(name_for_img)
        else:
            updates['image_url'] = img
    if 'price' in updates:
        try:
            updates['price'] = float(updates['price'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Price must be a number.'}), 400
    db.dishes.update_one({'_id': oid}, {'$set': updates})
    dish = db.dishes.find_one({'_id': oid})
    return jsonify(_serialise_dish(dish, db))


@app.route('/api/dishes/<dish_id>', methods=['DELETE'])
@jwt_required()
def delete_dish(dish_id):
    """Delete a dish and all its reviews. Admin only."""
    if not is_admin():
        return jsonify({'error': 'Admin access required.'}), 403
    db = get_db()
    oid = _to_oid(dish_id)
    if not oid or not db.dishes.find_one({'_id': oid}):
        return jsonify({'error': 'Dish not found.'}), 404
    db.reviews.delete_many({'dish_id': dish_id})
    db.dishes.delete_one({'_id': oid})
    return jsonify({'message': 'Dish deleted.'})


# ─── Review Routes ────────────────────────────────────────────────────────────

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    """Return reviews filtered by dish_id, nationality, or most recent 20."""
    db = get_db()
    dish_id = request.args.get('dish_id')
    nationality = request.args.get('nationality')
    query = {}
    if dish_id:
        query['dish_id'] = dish_id
    elif nationality:
        query['nationality'] = {'$regex': f'^{nationality}$', '$options': 'i'}
    reviews = list(db.reviews.find(query).sort('created_at', -1).limit(50))
    return jsonify([_serialise_review(r, db) for r in reviews])


@app.route('/api/reviews', methods=['POST'])
def add_review():
    """
    Submit a new review.
    Authentication is optional — guests can review without an account.
    """
    data = request.get_json(silent=True) or {}
    err = _validate_fields(data, ['dish_id', 'nationality', 'rating', 'reviewer_name'])
    if err:
        return jsonify({'error': err}), 400
    try:
        rating = int(data['rating'])
        if not 1 <= rating <= 5:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'error': 'Rating must be an integer between 1 and 5.'}), 400
    db = get_db()
    dish = db.dishes.find_one({'_id': _to_oid(data['dish_id'])})
    if not dish:
        return jsonify({'error': 'Dish not found.'}), 404
    doc = {
        'dish_id': data['dish_id'],
        'nationality': data['nationality'].strip().title(),
        'rating': rating,
        'comment': data.get('comment', '').strip(),
        'reviewer_name': data['reviewer_name'].strip(),
        'created_at': datetime.utcnow()
    }
    result = db.reviews.insert_one(doc)
    doc['_id'] = result.inserted_id
    return jsonify({'message': 'Review submitted. Thank you!',
                    'review': _serialise_review(doc, db)}), 201


@app.route('/api/reviews/<review_id>', methods=['DELETE'])
@jwt_required()
def delete_review(review_id):
    """Delete a review. Admin only."""
    if not is_admin():
        return jsonify({'error': 'Admin access required.'}), 403
    db = get_db()
    oid = _to_oid(review_id)
    if not oid or not db.reviews.find_one({'_id': oid}):
        return jsonify({'error': 'Review not found.'}), 404
    db.reviews.delete_one({'_id': oid})
    return jsonify({'message': 'Review deleted.'})


# ─── Recommendation Route ─────────────────────────────────────────────────────

@app.route('/api/recommendations', methods=['GET'])
def recommendations():
    """
    Return personalised dish recommendations for a given nationality.
    Uses the weighted Bayesian algorithm from recommendation_engine.py.
    """
    nationality = request.args.get('nationality', '').strip()
    if not nationality:
        return jsonify({'error': 'nationality parameter is required.'}), 400
    result = get_recommendations(nationality)
    return jsonify(result)


# ─── Stats Routes ─────────────────────────────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def stats():
    """Return public summary statistics for the homepage."""
    db = get_db()
    total_dishes = db.dishes.count_documents({})
    total_reviews = db.reviews.count_documents({})
    nationalities = len(db.reviews.distinct('nationality'))
    return jsonify({
        'total_dishes': total_dishes,
        'total_reviews': total_reviews,
        'nationalities_served': nationalities
    })


@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def admin_stats():
    """
    Return detailed analytics for the admin dashboard.
    Includes: top dishes, reviews per nationality, reviews over time.
    Admin JWT required.
    """
    if not is_admin():
        return jsonify({'error': 'Admin access required.'}), 403

    db = get_db()

    # Top dishes by average rating
    dishes = list(db.dishes.find())
    dish_stats = []
    for d in dishes:
        reviews = list(db.reviews.find({'dish_id': str(d['_id'])}, {'_id': 0, 'rating': 1}))
        avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1) if reviews else 0
        dish_stats.append({'name': d['name'], 'category': d['category'],
                           'avg_rating': avg, 'review_count': len(reviews)})
    dish_stats.sort(key=lambda x: x['avg_rating'], reverse=True)

    # Reviews per nationality (pie chart data)
    nat_pipeline = [{'$group': {'_id': '$nationality', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}}, {'$limit': 10}]
    nat_data = [{'nationality': r['_id'], 'count': r['count']}
                for r in db.reviews.aggregate(nat_pipeline)]

    # Reviews over time (last 30 days, for line chart)
    from datetime import timedelta
    now = datetime.utcnow()
    timeline = []
    for i in range(29, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59)
        count = db.reviews.count_documents({'created_at': {'$gte': day_start, '$lte': day_end}})
        timeline.append({'date': day.strftime('%Y-%m-%d'), 'count': count})

    # Category breakdown
    cat_pipeline = [{'$group': {'_id': '$category', 'count': {'$sum': 1}}}]
    cat_data = [{'category': r['_id'], 'count': r['count']}
                for r in db.dishes.aggregate(cat_pipeline)]

    return jsonify({
        'summary': {
            'total_dishes': db.dishes.count_documents({}),
            'total_reviews': db.reviews.count_documents({}),
            'total_users': db.users.count_documents({}),
            'nationalities_served': len(db.reviews.distinct('nationality'))
        },
        'top_dishes': dish_stats[:8],
        'reviews_by_nationality': nat_data,
        'reviews_timeline': timeline,
        'dishes_by_category': cat_data
    })


# ─── Nationalities Route ──────────────────────────────────────────────────────

@app.route('/api/nationalities', methods=['GET'])
def get_nationalities():
    """Return all distinct nationalities that have submitted reviews."""
    db = get_db()
    nats = sorted(db.reviews.distinct('nationality'))
    return jsonify(nats)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    """Simple health check endpoint for deployment verification."""
    try:
        db = get_db()
        db.command('ping')
        return jsonify({'status': 'ok', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'database': str(e)}), 500


# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found.'}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'error': 'Method not allowed.'}), 405


@app.errorhandler(500)
def server_error(e):
    logger.exception('Internal server error')
    return jsonify({'error': 'Internal server error.'}), 500


if __name__ == '__main__':
    app.run(debug=config.DEBUG, port=5000)
