<<<<<<< HEAD
# Diana Beach Restaurant
### Personalised Nationality-Based Food Recommendation System
**Final Year Project — BSc Computing Science in Software Engineering**
Kingston University London | Student: H.S.V.R Nimsara | ID: E180768

---

## 📁 Project Structure

```
diana-beach-restaurant/
├── backend/
│   ├── app.py                    ← Flask REST API (all endpoints)
│   ├── recommendation_engine.py  ← Weighted Bayesian algorithm (core component)
│   ├── auth.py                   ← JWT authentication + bcrypt password hashing
│   ├── database.py               ← MongoDB Atlas connection singleton
│   ├── config.py                 ← Environment variable configuration
│   ├── seed_data.py              ← Database seeder (dishes + sample reviews)
│   ├── requirements.txt          ← Python dependencies
│   ├── .env.example              ← Environment variable template
│   ├── API_DOCS.md               ← Full API documentation
│   └── tests/
│       └── test_api.py           ← 28 unit/integration tests (pytest)
└── frontend/
    ├── index.html                ← Home page
    ├── menu.html                 ← Full menu with filters
    ├── recommendations.html      ← Nationality-based recommendations
    ├── reviews.html              ← Submit + view reviews
    ├── about.html                ← About page
    ├── login.html                ← Login + Register
    ├── css/style.css             ← Complete stylesheet
    ├── js/main.js                ← Shared utilities + auth
    └── admin/
        └── dashboard.html        ← Admin dashboard (analytics + CRUD)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, JavaScript (ES6+) |
| Backend | Python 3.9+, Flask 3.0 |
| Database | MongoDB Atlas (free M0 tier) |
| Auth | JWT (Flask-JWT-Extended) + bcrypt |
| Charts | Chart.js (CDN) |
| Testing | pytest |

---

## ⚙️ Setup Instructions

### Step 1 — Get MongoDB Atlas (FREE, no credit card)

1. Go to **https://www.mongodb.com/atlas/database**
2. Click **Try Free** → Sign up with Google or email
3. Choose **M0 FREE** tier → Select any region (e.g. AWS / Singapore)
4. Create a cluster (takes ~2 minutes)
5. When prompted:
   - **Create a database user**: set a username and password (remember these!)
   - **Network Access**: click **Add IP Address** → **Allow Access From Anywhere** (0.0.0.0/0)
6. Click **Connect** → **Drivers** → Choose **Python** → Copy the connection string

It looks like:
```
mongodb+srv://youruser:yourpassword@cluster0.abc123.mongodb.net/
```

---

### Step 2 — Configure Environment

```bash
cd diana-beach-restaurant/backend
copy .env.example .env       # Windows
```

Open `.env` in Notepad and fill in:
```
MONGO_URI=mongodb+srv://youruser:yourpassword@cluster0.abc123.mongodb.net/diana_beach?retryWrites=true&w=majority
DB_NAME=diana_beach
JWT_SECRET_KEY=any-long-random-string-here
ADMIN_EMAIL=admin@dianabeach.lk
ADMIN_PASSWORD=Admin@Diana2025
```

---

### Step 3 — Install Python Dependencies

```bash
cd diana-beach-restaurant/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

### Step 4 — Seed the Database

```bash
python seed_data.py
```

This creates:
- ✅ 1 admin user account
- ✅ 19 dishes across 5 categories
- ✅ 38 sample reviews across 8 nationalities

---

### Step 5 — Start the Backend

```bash
python app.py
```

Server starts at: **http://127.0.0.1:5000**
Health check: **http://127.0.0.1:5000/api/health**

---

### Step 6 — Open the Frontend

Open `frontend/index.html` in your browser.

**Recommended:** Use VS Code / Cursor's **Live Server** extension for best experience.

---

### Step 7 — Access Admin Dashboard

- Go to `frontend/login.html`
- Login with:
  - Email: `admin@dianabeach.lk`
  - Password: `Admin@Diana2025`
- You'll be redirected to the admin dashboard

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/test_api.py -v
```

Expected: **28 passed**

---

## 🔬 The Recommendation Algorithm

The recommendation engine uses a **Weighted Bayesian Score** with recency decay:

```
score = (bayesian_avg × confidence_weight) + recency_bonus
```

Where:
- **bayesian_avg** = `(n × avg + m × C) / (n + m)`
  - `n` = number of reviews for this dish/nationality
  - `avg` = raw average rating
  - `m` = minimum confidence threshold (3)
  - `C` = global mean rating
- **confidence_weight** = `min(n / m, 1.0)` — grows from 0→1 as reviews accumulate
- **recency_bonus** = exponential decay weight (reviews from last 6 months score higher)

This prevents dishes with a single 5-star review from dominating over well-reviewed dishes.
*Reference: Same approach as IMDb's Top 250 Bayesian ranking formula.*

---

## 🌐 API Overview

See `backend/API_DOCS.md` for full documentation.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/auth/register | — | Register user |
| POST | /api/auth/login | — | Login, get token |
| GET | /api/dishes | — | List all dishes |
| POST | /api/dishes | Admin | Create dish |
| PUT | /api/dishes/:id | Admin | Update dish |
| DELETE | /api/dishes/:id | Admin | Delete dish |
| GET | /api/reviews | — | List reviews |
| POST | /api/reviews | — | Submit review |
| DELETE | /api/reviews/:id | Admin | Delete review |
| GET | /api/recommendations | — | Get recommendations |
| GET | /api/stats | — | Public stats |
| GET | /api/admin/stats | Admin | Full analytics |
| GET | /api/health | — | Health check |

---

## 🔒 Security

- Passwords hashed with **bcrypt** (12 rounds salt)
- JWT tokens expire after **24 hours**
- Admin routes protected by role-based JWT claims
- Input validation on all POST/PUT endpoints
- CORS configured for frontend-backend separation
- Environment variables used for all secrets (never hardcoded)

---

## ⚠️ Limitations & Future Work

- SQLite would be simpler for local dev; MongoDB Atlas adds real-world cloud experience
- Image upload functionality not implemented (placeholder emoji used)
- Collaborative filtering could further improve recommendations
- Mobile app version could use the same REST API
=======
# DianaBeachRestaurent
This Web Solution is made for Diana Beach Restaurant Located In Polhena, Matara.
>>>>>>> b9aed6f1cd17b827e6676d36497c2c543425f1d9
