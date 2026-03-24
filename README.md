# Diana Beach Restaurent

Restaurant web app with:
- Flask backend API (`backend/`)
- Static frontend (`frontend/`)
- MongoDB Atlas data store
- Nationality-based food recommendations

## Run Locally

1. Configure `backend/.env` from `backend/.env.example`.
2. Install backend dependencies:
   - `cd backend`
   - `python -m venv venv`
   - `venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
3. Optional DB seed:
   - `python seed_data.py`
4. Start backend:
   - `python app.py`
5. Open:
   - `http://127.0.0.1:5000/`

## Deploy

- Render + Vercel guide: `DEPLOY.md`
- Render blueprint file: `render.yaml`
- Vercel configs:
  - repo root `vercel.json` (fallback rewrites to `frontend/`)
  - `frontend/vercel.json` (frontend-root deployment)
