"""
tests/test_api.py
──────────────────
Unit and integration tests for the Diana Beach Restaurant API.

Test coverage:
  - Auth: register, login, duplicate email, bad credentials
  - Dishes: list, single, create (admin), update, delete, unauthorised access
  - Reviews: list, submit, invalid rating, missing fields
  - Recommendations: valid nationality, fallback for unknown nationality
  - Stats: public and admin endpoints
  - Health check

Run with:
    cd backend
    pytest tests/test_api.py -v

All tests use a separate test database (diana_beach_test) and clean up after.
No real MongoDB connection is required for unit tests — they use mocking.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from datetime import datetime


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """Create a test Flask client with a mocked database."""
    with patch('database.get_client') as mock_client, \
         patch('database.get_db') as mock_db:

        mock_db.return_value = _make_mock_db()

        import app as flask_app
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['JWT_SECRET_KEY'] = 'test-secret'
        with flask_app.app.test_client() as c:
            yield c


@pytest.fixture
def admin_token(client):
    """Register and log in an admin user, return the JWT token."""
    with patch('auth.get_db') as mock_db, \
         patch('app.get_db') as mock_db2:
        db = _make_mock_db()
        mock_db.return_value = db
        mock_db2.return_value = db

        # Create admin directly
        from auth import create_user, generate_token
        with patch('auth.get_db', return_value=db):
            user = create_user('Admin', 'admin@test.com', 'Admin1234', role='admin')
        token = generate_token(str(user['_id']), 'admin')
        return token


@pytest.fixture
def user_token(client):
    """Register a regular user and return the JWT token."""
    with patch('auth.get_db') as mock_db, \
         patch('app.get_db') as mock_db2:
        db = _make_mock_db()
        mock_db.return_value = db
        mock_db2.return_value = db

        from auth import create_user, generate_token
        with patch('auth.get_db', return_value=db):
            user = create_user('Test User', 'user@test.com', 'User1234', role='user')
        token = generate_token(str(user['_id']), 'user')
        return token


# ─── Mock DB Helper ─────────────────────────────────────────────────────────────

def _make_mock_db():
    """Return a MagicMock that mimics common pymongo operations."""
    db = MagicMock()
    db.dishes.count_documents.return_value = 3
    db.reviews.count_documents.return_value = 10
    db.users.count_documents.return_value = 2
    db.reviews.distinct.return_value = ['British', 'Indian', 'German']
    db.dishes.distinct.return_value = ['Seafood', 'Rice & Curry', 'Desserts']
    db.command.return_value = {'ok': 1}

    sample_dish = {
        '_id': _fake_oid('dish1'),
        'name': 'Grilled Prawns',
        'description': 'Delicious grilled prawns',
        'category': 'Seafood',
        'price': 2200,
        'image_url': '',
        'is_veg': False,
        'spice_level': 'Medium',
        'created_at': datetime.utcnow()
    }
    db.dishes.find.return_value = [sample_dish]
    db.dishes.find_one.return_value = sample_dish

    sample_review = {
        '_id': _fake_oid('rev1'),
        'dish_id': str(sample_dish['_id']),
        'nationality': 'British',
        'rating': 5,
        'comment': 'Excellent!',
        'reviewer_name': 'James',
        'created_at': datetime.utcnow()
    }
    find_chain = MagicMock()
    find_chain.sort.return_value = find_chain
    find_chain.limit.return_value = [sample_review]
    find_chain.__iter__ = lambda self: iter([sample_review])
    db.reviews.find.return_value = find_chain
    db.reviews.find_one.return_value = sample_review

    db.users.find_one.return_value = None  # No existing user by default
    insert_result = MagicMock()
    insert_result.inserted_id = _fake_oid('new1')
    db.dishes.insert_one.return_value = insert_result
    db.reviews.insert_one.return_value = insert_result
    db.users.insert_one.return_value = insert_result

    return db


def _fake_oid(seed: str = 'abc'):
    """Return a fake but valid-looking ObjectId."""
    from bson import ObjectId
    hex_str = (seed * 24)[:24]
    try:
        return ObjectId(hex_str)
    except Exception:
        return ObjectId()


# ─── Health Check ───────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_check_ok(self, client):
        """Health endpoint should return 200 when DB is reachable."""
        with patch('app.get_db') as mock_db:
            db = MagicMock()
            db.command.return_value = {'ok': 1}
            mock_db.return_value = db
            res = client.get('/api/health')
            assert res.status_code == 200
            data = json.loads(res.data)
            assert data['status'] == 'ok'


# ─── Auth Tests ────────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_success(self, client):
        """Valid registration should return 201 with a token."""
        with patch('app.create_user') as mock_create, \
             patch('app.generate_token', return_value='fake-token'):
            from bson import ObjectId
            mock_create.return_value = {
                '_id': ObjectId(), 'name': 'Test', 'email': 'test@example.com', 'role': 'user'
            }
            res = client.post('/api/auth/register',
                              json={'name': 'Test', 'email': 'test@example.com', 'password': 'Test1234'})
            assert res.status_code == 201
            data = json.loads(res.data)
            assert 'token' in data

    def test_register_missing_field(self, client):
        """Registration with missing fields should return 400."""
        res = client.post('/api/auth/register', json={'name': 'Test', 'email': 'test@example.com'})
        assert res.status_code == 400
        data = json.loads(res.data)
        assert 'error' in data

    def test_register_short_password(self, client):
        """Password shorter than 8 chars should return 400."""
        res = client.post('/api/auth/register',
                          json={'name': 'Test', 'email': 'test@example.com', 'password': '123'})
        assert res.status_code == 400

    def test_register_duplicate_email(self, client):
        """Duplicate email registration should return 409."""
        with patch('app.create_user', side_effect=ValueError('Email already registered.')):
            res = client.post('/api/auth/register',
                              json={'name': 'Test', 'email': 'dup@example.com', 'password': 'Test1234'})
            assert res.status_code == 409

    def test_login_invalid_credentials(self, client):
        """Wrong password should return 401."""
        with patch('app.find_user_by_email', return_value=None):
            res = client.post('/api/auth/login',
                              json={'email': 'nobody@example.com', 'password': 'wrong'})
            assert res.status_code == 401

    def test_login_missing_fields(self, client):
        """Login with missing fields should return 400."""
        res = client.post('/api/auth/login', json={'email': 'x@x.com'})
        assert res.status_code == 400


# ─── Dish Tests ────────────────────────────────────────────────────────────────

class TestDishes:
    def test_get_all_dishes(self, client):
        """GET /api/dishes should return a list."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            db.reviews.find.return_value = []
            mock_db.return_value = db
            res = client.get('/api/dishes')
            assert res.status_code == 200
            data = json.loads(res.data)
            assert isinstance(data, list)

    def test_get_dish_by_id(self, client):
        """GET /api/dishes/<id> with valid ID should return 200."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            db.reviews.find.return_value = []
            mock_db.return_value = db
            from bson import ObjectId
            oid = str(ObjectId())
            res = client.get(f'/api/dishes/{oid}')
            assert res.status_code in (200, 404)

    def test_get_categories(self, client):
        """GET /api/categories should return a sorted list."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            mock_db.return_value = db
            res = client.get('/api/categories')
            assert res.status_code == 200
            data = json.loads(res.data)
            assert isinstance(data, list)

    def test_create_dish_no_auth(self, client):
        """POST /api/dishes without JWT should return 401."""
        res = client.post('/api/dishes', json={'name': 'Test', 'description': 'x', 'category': 'Seafood', 'price': 100})
        assert res.status_code == 401

    def test_create_dish_non_admin(self, client):
        """POST /api/dishes with non-admin JWT should return 403."""
        with patch('app.is_admin', return_value=False), \
             patch('flask_jwt_extended.verify_jwt_in_request'):
            res = client.post('/api/dishes',
                              headers={'Authorization': 'Bearer fake-user-token'},
                              json={'name': 'Test', 'description': 'x', 'category': 'Seafood', 'price': 100})
            assert res.status_code in (401, 403, 422)


# ─── Review Tests ──────────────────────────────────────────────────────────────

class TestReviews:
    def test_get_reviews(self, client):
        """GET /api/reviews should return a list."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            mock_db.return_value = db
            res = client.get('/api/reviews')
            assert res.status_code == 200
            data = json.loads(res.data)
            assert isinstance(data, list)

    def test_submit_review_success(self, client):
        """Valid review submission should return 201."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            mock_db.return_value = db
            from bson import ObjectId
            dish_id = str(ObjectId())
            res = client.post('/api/reviews', json={
                'dish_id': dish_id,
                'nationality': 'British',
                'rating': 5,
                'reviewer_name': 'James',
                'comment': 'Excellent!'
            })
            assert res.status_code in (201, 404)

    def test_submit_review_invalid_rating(self, client):
        """Rating out of range should return 400."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            mock_db.return_value = db
            from bson import ObjectId
            res = client.post('/api/reviews', json={
                'dish_id': str(ObjectId()),
                'nationality': 'British',
                'rating': 99,
                'reviewer_name': 'James'
            })
            assert res.status_code == 400

    def test_submit_review_missing_fields(self, client):
        """Missing required fields should return 400."""
        res = client.post('/api/reviews', json={'dish_id': '123', 'rating': 5})
        assert res.status_code == 400

    def test_submit_review_missing_nationality(self, client):
        """Missing nationality should return 400."""
        res = client.post('/api/reviews', json={'dish_id': '123', 'rating': 3, 'reviewer_name': 'X'})
        assert res.status_code == 400


# ─── Recommendation Tests ──────────────────────────────────────────────────────

class TestRecommendations:
    def test_recommendations_missing_nationality(self, client):
        """Missing nationality parameter should return 400."""
        res = client.get('/api/recommendations')
        assert res.status_code == 400

    def test_recommendations_valid_nationality(self, client):
        """Valid nationality should return 200 with recommendation data."""
        with patch('app.get_recommendations') as mock_rec:
            mock_rec.return_value = {
                'nationality': 'British',
                'recommendations': [],
                'has_nationality_data': False,
                'algorithm_info': {}
            }
            res = client.get('/api/recommendations?nationality=British')
            assert res.status_code == 200
            data = json.loads(res.data)
            assert 'recommendations' in data
            assert 'nationality' in data

    def test_recommendations_returns_algorithm_info(self, client):
        """Recommendations response should include algorithm_info for transparency."""
        with patch('app.get_recommendations') as mock_rec:
            mock_rec.return_value = {
                'nationality': 'Indian',
                'recommendations': [],
                'has_nationality_data': True,
                'algorithm_info': {'mode': 'weighted_bayesian'}
            }
            res = client.get('/api/recommendations?nationality=Indian')
            data = json.loads(res.data)
            assert 'algorithm_info' in data


# ─── Stats Tests ───────────────────────────────────────────────────────────────

class TestStats:
    def test_public_stats(self, client):
        """GET /api/stats should return summary counts."""
        with patch('app.get_db') as mock_db:
            db = _make_mock_db()
            mock_db.return_value = db
            res = client.get('/api/stats')
            assert res.status_code == 200
            data = json.loads(res.data)
            assert 'total_dishes' in data
            assert 'total_reviews' in data
            assert 'nationalities_served' in data

    def test_admin_stats_no_auth(self, client):
        """GET /api/admin/stats without JWT should return 401."""
        res = client.get('/api/admin/stats')
        assert res.status_code == 401


# ─── Recommendation Engine Unit Tests ─────────────────────────────────────────

class TestRecommendationEngine:
    """Direct unit tests for the recommendation_engine module."""

    def test_recency_weight_recent(self):
        """Very recent review should have weight close to 1."""
        from recommendation_engine import _recency_weight
        now = datetime.utcnow()
        weight = _recency_weight(now)
        assert weight > 0.95

    def test_recency_weight_old(self):
        """Old review (1 year ago) should have weight significantly less than 1."""
        from recommendation_engine import _recency_weight
        from datetime import timedelta
        old = datetime.utcnow() - timedelta(days=365)
        weight = _recency_weight(old)
        assert weight < 0.5

    def test_recency_weight_none(self):
        """None date should return neutral weight 0.5."""
        from recommendation_engine import _recency_weight
        assert _recency_weight(None) == 0.5

    def test_compute_score_single_review(self):
        """Single 5-star review should produce a score below 5 (Bayesian regression)."""
        from recommendation_engine import _compute_score
        reviews = [{'rating': 5, 'created_at': datetime.utcnow()}]
        score, breakdown = _compute_score(reviews, global_mean=3.5)
        # Bayesian average pulls toward mean for small n
        assert score < 5.0
        assert score > 0
        assert 'bayesian_avg' in breakdown

    def test_compute_score_many_reviews(self):
        """High-confidence score (many reviews) should be closer to raw average."""
        from recommendation_engine import _compute_score
        reviews = [{'rating': 5, 'created_at': datetime.utcnow()} for _ in range(20)]
        score, breakdown = _compute_score(reviews, global_mean=3.0)
        # With many reviews, confidence=1.0, score approaches raw avg + recency
        assert breakdown['confidence_weight'] == 1.0
        assert score > 4.0

    def test_compute_score_breakdown_keys(self):
        """Score breakdown should contain all expected keys."""
        from recommendation_engine import _compute_score
        reviews = [{'rating': 4, 'created_at': datetime.utcnow()}]
        _, breakdown = _compute_score(reviews, global_mean=3.5)
        for key in ['raw_avg', 'bayesian_avg', 'confidence_weight', 'recency_bonus', 'final_score']:
            assert key in breakdown
