# Diana Beach Restaurant — API Documentation

Base URL: `http://127.0.0.1:5000/api`

All responses are JSON. Authenticated endpoints require a Bearer JWT token in the `Authorization` header.

---

## Authentication

### POST `/auth/register`
Register a new user account.

**Request Body:**
```json
{ "name": "John Smith", "email": "john@example.com", "password": "MyPass123" }
```
**Response 201:**
```json
{ "message": "Registration successful.", "token": "<JWT>", "user": { "name": "John Smith", "email": "john@example.com", "role": "user" } }
```
**Errors:** `400` missing fields | `400` password < 8 chars | `409` email already registered

---

### POST `/auth/login`
Authenticate and receive a JWT token.

**Request Body:**
```json
{ "email": "admin@dianabeach.lk", "password": "Admin@Diana2025" }
```
**Response 200:**
```json
{ "message": "Login successful.", "token": "<JWT>", "user": { "name": "Admin", "role": "admin" } }
```
**Errors:** `400` missing fields | `401` invalid credentials

---

## Dishes

### GET `/dishes`
List all dishes. Optional query param: `?category=Seafood`

**Response 200:** Array of dish objects.
```json
[
  {
    "id": "6654abc123...",
    "name": "Grilled Prawn Platter",
    "description": "Fresh tiger prawns...",
    "category": "Seafood",
    "price": 2200,
    "image_url": "",
    "is_veg": false,
    "spice_level": "Medium",
    "avg_rating": 4.8,
    "review_count": 12
  }
]
```

---

### GET `/dishes/<id>`
Get a single dish by its MongoDB ID.

**Response 200:** Single dish object.
**Error:** `404` dish not found.

---

### GET `/categories`
List all distinct dish categories.

**Response 200:** `["Beverages", "Desserts", "Rice & Curry", "Seafood", "Starters"]`

---

### POST `/dishes` _(Admin JWT required)_
Create a new dish.

**Headers:** `Authorization: Bearer <token>`
**Request Body:**
```json
{ "name": "New Dish", "description": "Description here", "category": "Seafood", "price": 1500, "spice_level": "Mild", "is_veg": false }
```
**Response 201:** Created dish object.
**Errors:** `400` missing fields | `401` no token | `403` not admin

---

### PUT `/dishes/<id>` _(Admin JWT required)_
Update an existing dish. Send only the fields you want to change.

**Response 200:** Updated dish object.
**Errors:** `404` not found | `403` not admin

---

### DELETE `/dishes/<id>` _(Admin JWT required)_
Delete a dish and all associated reviews.

**Response 200:** `{ "message": "Dish deleted." }`
**Errors:** `404` not found | `403` not admin

---

## Reviews

### GET `/reviews`
List reviews. Optional query params: `?dish_id=<id>` or `?nationality=British`

**Response 200:** Array of review objects.
```json
[
  {
    "id": "6654def456...",
    "dish_id": "6654abc123...",
    "dish_name": "Grilled Prawn Platter",
    "nationality": "British",
    "rating": 5,
    "comment": "Best crab I've ever had!",
    "reviewer_name": "James Thompson",
    "created_at": "2025-06-01 14:23"
  }
]
```

---

### POST `/reviews`
Submit a new guest review. No authentication required.

**Request Body:**
```json
{ "dish_id": "6654abc123...", "nationality": "British", "rating": 5, "reviewer_name": "James", "comment": "Excellent!" }
```
**Response 201:** `{ "message": "Review submitted.", "review": { ... } }`
**Errors:** `400` missing/invalid fields | `404` dish not found

---

### DELETE `/reviews/<id>` _(Admin JWT required)_
Delete a review.

**Response 200:** `{ "message": "Review deleted." }`
**Errors:** `404` not found | `403` not admin

---

## Recommendations

### GET `/recommendations?nationality=<value>`
Get personalised dish recommendations using the weighted Bayesian algorithm.

**Query Params:** `nationality` (required) — e.g. `British`, `Indian`, `German`

**Response 200:**
```json
{
  "nationality": "British",
  "has_nationality_data": true,
  "recommendations": [
    {
      "dish": { "id": "...", "name": "Butter Garlic Crab", ... },
      "score": 4.87,
      "review_count": 6,
      "source": "nationality",
      "breakdown": {
        "raw_avg": 5.0,
        "bayesian_avg": 4.62,
        "confidence_weight": 1.0,
        "recency_bonus": 0.25,
        "final_score": 4.87
      }
    }
  ],
  "algorithm_info": {
    "mode": "weighted_bayesian",
    "global_mean": 4.52,
    "min_confidence_threshold": 3,
    "total_reviews_used": 12,
    "dishes_evaluated": 6
  }
}
```

**When `has_nationality_data` is `false`:** Falls back to global top-rated dishes.
**Error:** `400` missing nationality parameter

---

## Statistics

### GET `/stats`
Public summary statistics for the homepage.

**Response 200:**
```json
{ "total_dishes": 19, "total_reviews": 38, "nationalities_served": 8 }
```

---

### GET `/admin/stats` _(Admin JWT required)_
Detailed analytics for the admin dashboard.

**Response 200:**
```json
{
  "summary": { "total_dishes": 19, "total_reviews": 38, "total_users": 3, "nationalities_served": 8 },
  "top_dishes": [ { "name": "Butter Garlic Crab", "avg_rating": 5.0, "review_count": 6 } ],
  "reviews_by_nationality": [ { "nationality": "British", "count": 6 } ],
  "reviews_timeline": [ { "date": "2025-05-15", "count": 2 } ],
  "dishes_by_category": [ { "category": "Seafood", "count": 5 } ]
}
```

---

### GET `/nationalities`
List all nationalities that have submitted at least one review.

**Response 200:** `["Australian", "British", "Chinese", "French", "German", "Indian", "Japanese", "Russian"]`

---

## Health Check

### GET `/health`
Verify server and database connectivity.

**Response 200:** `{ "status": "ok", "database": "connected" }`
**Response 500:** `{ "status": "error", "database": "..." }`

---

## Error Format

All error responses follow this format:
```json
{ "error": "Human-readable error message." }
```

## HTTP Status Codes Used

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (missing/invalid fields) |
| 401 | Unauthorized (no/invalid JWT) |
| 403 | Forbidden (insufficient role) |
| 404 | Not Found |
| 409 | Conflict (e.g. duplicate email) |
| 500 | Internal Server Error |
