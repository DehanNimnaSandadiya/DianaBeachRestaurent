"""
seed_data.py
────────────
Database seeder for Diana Beach Restaurant.

This file is used to (re)populate:
  - the `dishes` collection
  - the `reviews` collection (used by recommendations + avg rating)
and keep an admin user in place.

Run:
  python seed_data.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
import re
from urllib.parse import quote

from database import get_db
from auth import create_user, find_user_by_email
from config import config


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─── Local Food Images Serving (for DB) ────────────────────────────────
FOOD_IMAGES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FoodImages"))
LOCAL_IMAGE_BASE_URL = "/images/"
_IMAGE_FILENAME_MAP: dict[str, str] | None = None
_IMAGE_TOKEN_MAP: dict[str, set[str]] | None = None


def _tokenize_for_match(s: str) -> set[str]:
    """
    Tokenize strings for fuzzy matching between dish names and image filenames.
    Includes a basic plural->singular heuristic (e.g. 'prawns' -> 'prawn').
    """
    if not s:
        return set()
    tokens = set(re.findall(r"[a-z0-9]+", s.lower()))
    # Add singular-ish forms for plural tokens
    for t in list(tokens):
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            tokens.add(t[:-1])
    return tokens


def _get_image_filename_map() -> dict[str, str]:
    """
    Build a mapping:
      dish-name-lower -> exact filename in FoodImages
    so we can set `image_url` reliably for each seeded dish.
    """
    global _IMAGE_FILENAME_MAP
    if _IMAGE_FILENAME_MAP is not None:
        return _IMAGE_FILENAME_MAP

    mapping: dict[str, str] = {}
    token_map: dict[str, set[str]] = {}
    try:
        for entry in os.listdir(FOOD_IMAGES_DIR):
            path = os.path.join(FOOD_IMAGES_DIR, entry)
            if not os.path.isfile(path):
                continue
            if not entry.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
                continue
            stem = os.path.splitext(entry)[0].strip().lower()
            mapping[stem] = entry
            token_map[stem] = _tokenize_for_match(stem)
    except FileNotFoundError:
        logger.warning(f"FoodImages folder not found at: {FOOD_IMAGES_DIR}")

    _IMAGE_FILENAME_MAP = mapping
    # Keep tokens in sync with filenames
    global _IMAGE_TOKEN_MAP
    _IMAGE_TOKEN_MAP = token_map
    return mapping


def _image_url_for_dish_name(dish_name: str) -> str:
    if not dish_name:
        return ""
    mapping = _get_image_filename_map()
    normalized = dish_name.strip().lower()
    filename = mapping.get(normalized)
    if filename:
        return LOCAL_IMAGE_BASE_URL + quote(filename)

    # Fallback: fuzzy match by keyword overlap against filenames in FoodImages.
    dish_tokens = _tokenize_for_match(dish_name)
    if not dish_tokens:
        return ""

    token_map = _IMAGE_TOKEN_MAP or {}
    best_stem = None
    best_score = 0
    for stem, img_tokens in token_map.items():
        score = len(dish_tokens.intersection(img_tokens))
        if score > best_score:
            best_score = score
            best_stem = stem

    if not best_stem or best_score <= 0:
        # Last resort: use a generic external image so UI never stays blank.
        return "https://source.unsplash.com/800x600/?" + quote(dish_name.strip())

    # Always prefer the best overlap candidate, even if not perfect.
    return LOCAL_IMAGE_BASE_URL + quote(mapping[best_stem])


# ─── Menu ──────────────────────────────────────────────────────────────────

# Category names must match `menu.html` filter tabs and dishEmoji() mapping.
MENU_CATEGORIES: dict[str, list[str]] = {
    "Starters": [
        "Prawns Cocktail",
        "Bruschetta with Feta",
        "Spring Rolls",
        "Teriyaki Fish",
        "Sesame Custard Tuna",
    ],
    "Soups": [
        "Tomato Soup",
        "Cream of Seafood Chowder",
        "Cream of Chicken",
        "Cream of Mushroom",
        "Tom Yum Seafood",
    ],
    "Salads": [
        "Greek Salad",
        "Caesar Salad",
        "Hawaiian Chicken Salad",
        "Thai Prawn Salad",
        "Tuna Vegetable Salad",
    ],
    "Chicken": [
        "Devilled Chicken",
        "Sri Lankan Red Chicken Curry",
        "Honey Garlic Chicken",
        "Chicken Parmigiana",
        "Chicken Shawarma",
    ],
    "Seafood": [
        "Tuna Steak",
        "Grilled Sea Fish",
        "Prawn Tempura",
        "Hot Butter Cuttlefish",
        "Crab Curry",
    ],
    "Pasta": [
        "Seafood Marinara",
        "Bolognese",
        "Carbonara",
        "Cream Chicken Pasta",
        "Tomato Herbs Pasta",
    ],
    "Burgers & Sandwiches": [
        "Crispy Chicken Burger",
        "Tuna Burger",
        "Club Sandwich",
        "Cheese Tomato Sandwich",
        "Mango Avocado Wrap",
    ],
    "Rice & Noodles": [
        "Vegetable Rice",
        "Thai Spicy Chicken Rice",
        "Seafood Chop Suey Rice",
        "Vegetable Noodles",
        "Mee Goreng",
    ],
    "Breakfast": [
        "Egg Benedict",
        "Avocado Toast",
        "Sri Lankan Pancake",
        "Smoothie Bowl",
        "Turtle Breakfast",
    ],
    "Desserts": [
        "Brownie with Ice Cream",
        "Cheesecake",
        "Watalappan",
        "Banana Caramel Ice Cream",
        "Fruit Salad with Ice Cream",
    ],
    "Drinks": [
        # Non-alcoholic
        "Mango Juice",
        "Lime Juice",
        "Cappuccino",
        "Hot Chocolate",

        # Alcoholic / cocktails (selected items + compact 10 dataset)
        "Mojito Classic",
        "Margarita",
        "Cosmopolitan",
        "Blue Lagoon",
        "Tequila Sunrise",
        "Long Island Iced Tea",
        "Whiskey Coke",
        "Gin & Tonic",
        "Vodka",
        "Whiskey",
    ],
}


NATIONALITY_DISHES: dict[str, list[str]] = {
    "Sri Lankan": [
        "Devilled Chicken",
        "Sri Lankan Red Chicken Curry",
        "Hot Butter Cuttlefish",
        "Crab Curry",
        "Watalappan",
        "Sri Lankan Pancake",
        "Kiribath (Milk Rice)",
        "Pol Sambol",
        "Ceylon Tea",
        "King Coconut",
    ],
    "Indian": [
        "Chicken Curry",
        "Masala Rice",
        "Vegetable Rice",
        "Roti / Flatbread",
        "Paneer-style dishes (veg option)",
        "Samosa / Street snacks",
        "Masala Chai",
        "Lassi (Mango / Sweet)",
        "Butter Chicken",
        "Biryani",
    ],
    "Chinese": [
        "Spring Rolls",
        "Vegetable Noodles",
        "Fried Rice",
        "Sweet & Sour Chicken",
        "Chop Suey",
        "Dumplings",
        "Hot & Sour Soup",
        "Green Tea",
        "Stir Fry Vegetables",
        "Prawn Tempura (Asian-style)",
    ],
    "Japanese": [
        "Teriyaki Fish",
        "Grilled Fish",
        "Sushi",
        "Ramen",
        "Tempura",
        "Miso Soup",
        "Rice Bowl",
        "Matcha Tea",
        "Sashimi",
        "Green Tea",
    ],
    "Korean": [
        "Spicy Chicken",
        "Korean BBQ",
        "Kimchi",
        "Bibimbap",
        "Korean Noodles",
        "Seafood Soup",
        "Rice Bowl",
        "Korean Fried Chicken",
        "Barley Tea",
        "Soju-style drinks",
    ],
    "British": [
        "Fish & Chips",
        "Grilled Fish",
        "Club Sandwich",
        "Roast Chicken",
        "Mashed Potatoes",
        "Tomato Soup",
        "English Breakfast",
        "Tea (Black Tea)",
        "Pie / Meat Pie",
        "Coffee",
    ],
    "American": [
        "Chicken Burger",
        "Beef Burger",
        "Club Sandwich",
        "BBQ Chicken",
        "Fries",
        "Pancakes",
        "Brownie with Ice Cream",
        "Milkshake",
        "Hot Chocolate",
        "Cola",
    ],
    "Australian": [
        "Avocado Toast",
        "Grilled Seafood",
        "BBQ Meat",
        "Fresh Salads",
        "Smoothie Bowl",
        "Eggs & Toast",
        "Fresh Juice",
        "Coffee (Flat White)",
        "Grilled Chicken",
        "Healthy Wraps",
    ],
    "German": [
        "Sausages",
        "Grilled Meat",
        "Schnitzel",
        "Potato Dishes",
        "Bread & Cheese",
        "Soup",
        "Meat Platter",
        "Beer",
        "Coffee",
        "Pretzels",
    ],
    "French": [
        "Chicken Parmigiana (European style)",
        "Cream-based Pasta",
        "Mushroom Soup",
        "Bread & Cheese",
        "Croissant",
        "Pastries",
        "Cheesecake",
        "Coffee",
        "Wine",
        "Desserts",
    ],
    "Russian": [
        "Meat Stew",
        "Chicken Dishes",
        "Noodles",
        "Soup (Borscht-style)",
        "Bread Meals",
        "Dumplings",
        "Tea",
        "Coffee",
        "Potato Dishes",
        "Warm Desserts",
    ],
    "Canadian": [
        "Burgers",
        "Sandwiches",
        "Grilled Meat",
        "Fries",
        "Pancakes",
        "Pasta",
        "Desserts",
        "Coffee",
        "Juice",
        "Soft Drinks",
    ],
}

# Ensure every dish in nationality mapping exists in menu data.
_existing_menu_names = {n for names in MENU_CATEGORIES.values() for n in names}
_extra_menu_names = []
for _names in NATIONALITY_DISHES.values():
    for _name in _names:
        if _name not in _existing_menu_names:
            _extra_menu_names.append(_name)
            _existing_menu_names.add(_name)
if _extra_menu_names:
    MENU_CATEGORIES["International Specials"] = _extra_menu_names


def _infer_is_veg(category: str, name: str) -> bool:
    """Best-effort vegetarian flag for filtering."""
    low = name.lower()

    # Hard non-veg keywords first
    non_veg_tokens = [
        "chicken",
        "tuna",
        "prawn",
        "prawns",
        "fish",
        "sea fish",
        "seafood",
        "crab",
        "cuttlefish",
        "shawarma",
        "bolognese",
        "egg benedict",
        "burger",  # may still be veg, but overridden below
        "sandwich",  # may still be veg, but overridden below
    ]
    if any(tok in low for tok in non_veg_tokens):
        # Override some known veg dishes
        if category == "Burgers & Sandwiches" and name in ["Cheese Tomato Sandwich", "Mango Avocado Wrap"]:
            return True
        if name in ["Avocado Toast", "Sri Lankan Pancake", "Smoothie Bowl"]:
            return True
        if name in ["Bruschetta with Feta", "Green Salad", "Greek Salad", "Tomato Herbs Pasta"]:
            return True
        if name in ["Spring Rolls"]:
            return True
        if name in ["Caesar Salad", "Cream of Mushroom", "Tomato Soup", "Vegetable Rice", "Vegetable Noodles", "Cream Chicken Pasta"]:
            # Cream Chicken Pasta is non-veg normally, but keeping it veg would be wrong.
            # We'll rely on token rules for chicken; this branch is for safe overrides only.
            return False if "chicken" in low else True

        return False

    # Otherwise, assume veg for these categories unless name suggests otherwise
    veg_categories = {"Starters", "Soups", "Salads", "Pasta", "Breakfast", "Desserts", "Rice & Noodles"}
    if category == "Drinks":
        # Treat only non-alcohol drinks as vegetarian.
        low = name.lower()
        non_alcohol = ["juice", "cappuccino", "hot chocolate", "smoothie", "lime juice", "mango juice"]
        return any(x in low for x in non_alcohol)
    return category in veg_categories


def _infer_spice_level(category: str, name: str) -> str:
    low = name.lower()
    if "tom yum" in low:
        return "Hot"
    if "spicy" in low:
        return "Hot"
    if "red chicken curry" in low or "devilled chicken" in low:
        return "Hot"
    if "crab curry" in low or "hot butter cuttlefish" in low:
        return "Hot"
    if "thai prawn salad" in low:
        return "Hot"
    if "honey garlic" in low or "teriyaki" in low or "mojito" in low:
        return "Mild"
    if category in {"Seafood", "Chicken"}:
        return "Medium"
    if category in {"Soups", "Pasta"} and "seafood" in low:
        return "Medium"
    return "None"


def _base_price(category: str) -> float:
    base = {
        "Starters": 1200,
        "Soups": 900,
        "Salads": 1000,
        "Chicken": 1700,
        "Seafood": 2000,
        "Pasta": 1400,
        "Burgers & Sandwiches": 1500,
        "Rice & Noodles": 1100,
        "Breakfast": 1300,
        "Desserts": 900,
        "Drinks": 500,
    }.get(category, 1000)
    return float(base)


def _description_for(name: str) -> str:
    return f"{name} — a house favourite from Diana Beach Restaurant."


def _make_dish_docs() -> list[dict]:
    dishes: list[dict] = []
    now = datetime.utcnow()
    for category, names in MENU_CATEGORIES.items():
        for name in names:
            dishes.append(
                {
                    "name": name,
                    "description": _description_for(name),
                    "category": category,
                    "price": _base_price(category),
                    "image_url": _image_url_for_dish_name(name),
                    "is_veg": _infer_is_veg(category, name),
                    "spice_level": _infer_spice_level(category, name),
                    "is_top_seller": False,
                    "created_at": now,
                }
            )
    return dishes


def _make_reviews(dish_name_to_id: dict[str, str]) -> list[dict]:
    reviews: list[dict] = []

    # 3 reviews per nationality per dish, so `MIN_REVIEWS_FOR_CONFIDENCE=3` is satisfied.
    days_ago_seq = [5, 25, 60]
    ratings_seq = [5, 4, 5]

    for nationality, dish_names in NATIONALITY_DISHES.items():
        # De-dupe while keeping order
        seen = set()
        unique_dishes = []
        for dn in dish_names:
            if dn not in seen:
                unique_dishes.append(dn)
                seen.add(dn)

        for dish_name in unique_dishes:
            dish_id = dish_name_to_id.get(dish_name)
            if not dish_id:
                # If a dish name in NATIONALITY_DISHES doesn't exist in the menu list, skip it.
                continue
            for i in range(3):
                reviews.append(
                    {
                        "dish_id": dish_id,
                        "nationality": nationality,
                        "rating": ratings_seq[i],
                        "reviewer_name": f"{nationality} Guest {i+1}",
                        "comment": f"Great choice: {dish_name}.",
                        "created_at": datetime.utcnow() - timedelta(days=days_ago_seq[i]),
                    }
                )
    return reviews


def seed():
    db = get_db()

    # ── Admin user ───────────────────────────────────────────────────────────
    if not find_user_by_email(config.ADMIN_EMAIL):
        create_user("Admin", config.ADMIN_EMAIL, config.ADMIN_PASSWORD, role="admin")
        logger.info("Admin user created.")
    else:
        logger.info("Admin user already exists, skipping.")

    # ── Reset dishes + reviews (user requested fresh menu) ────────────────
    db.reviews.delete_many({})
    db.dishes.delete_many({})
    logger.info("Cleared existing dishes + reviews.")

    # ── Insert dishes ───────────────────────────────────────────────────────
    dish_docs = _make_dish_docs()
    result = db.dishes.insert_many(dish_docs)
    logger.info(f"Inserted {len(result.inserted_ids)} dishes.")

    dish_name_to_id = {doc["name"]: str(oid) for doc, oid in zip(dish_docs, result.inserted_ids)}

    # ── Insert reviews ───────────────────────────────────────────────────────
    review_docs = _make_reviews(dish_name_to_id)
    if review_docs:
        db.reviews.insert_many(review_docs)
        logger.info(f"Inserted {len(review_docs)} reviews.")
    else:
        logger.warning("No reviews were generated (check dish name mapping).")

    # ── MongoDB Indexes ─────────────────────────────────────────────────────
    db.reviews.create_index("nationality")
    db.reviews.create_index("dish_id")
    db.reviews.create_index("created_at")
    db.dishes.create_index("category")
    db.users.create_index("email", unique=True)

    logger.info("Seeding complete!")
    logger.info(f"Admin login → Email: {config.ADMIN_EMAIL}  Password: {config.ADMIN_PASSWORD}")


if __name__ == "__main__":
    seed()

