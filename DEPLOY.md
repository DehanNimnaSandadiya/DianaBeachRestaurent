# Deploy: Render (backend) + Vercel (frontend)

This app is split: **Flask API + static HTML** on [Render](https://render.com), **static site** on [Vercel](https://vercel.com). The frontend calls your Render URL for `/api` and `/images`.

---

## 1. MongoDB Atlas

1. Create a free cluster at [MongoDB Atlas](https://www.mongodb.com/atlas).
2. **Database Access** → create a user (save username + password).
3. **Network Access** → allow **0.0.0.0/0** (required for Render’s servers), or Render’s egress IPs if you prefer.
4. **Connect** → Drivers → copy the **Python** connection string.
5. Replace `<password>` with your user’s password (URL-encode special characters if needed).
6. Append a database name, e.g. `...mongodb.net/diana_beach?retryWrites=true&w=majority`.

---

## 2. Backend on Render

### Create a Web Service

1. Render Dashboard → **New** → **Web Service**.
2. Connect the GitHub repo that contains this project (`backend/` folder at repo root).
3. Optional: If you use Blueprint deploy, Render can read `render.yaml` from repo root.

### Settings

| Field | Value |
|--------|--------|
| **Root Directory** | `backend` |
| **Runtime** | Python |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |

Alternative if you leave **Root Directory** empty (repo root):

- **Start Command** | `gunicorn backend.app:app`  
- **Build Command** | `pip install -r backend/requirements.txt`  

`backend/runtime.txt` pins **Python 3.12.8** when Render detects the file under the service root (use `backend` as root so it is picked up).

### Environment variables (Render → Environment)

Add these (use **strong secrets** in production):

| Key | Example / notes |
|-----|------------------|
| `MONGO_URI` | Your Atlas SRV string (with DB name + query params). |
| `DB_NAME` | `diana_beach` (must match the DB in the URI if you use one). |
| `JWT_SECRET_KEY` | Long random string (e.g. 32+ chars). |
| `FLASK_ENV` | `production` |
| `ADMIN_EMAIL` | Your admin login email. |
| `ADMIN_PASSWORD` | Your admin password. |

Do **not** commit real secrets; only set them in Render.

### After first deploy

1. Open `https://YOUR-SERVICE.onrender.com/api/health` — should return JSON with `"status":"ok"`.
2. **Seed the database** (one-time or when you reset menu data):  
   Render shell or local with the same `MONGO_URI`:

   ```bash
   cd backend
   pip install -r requirements.txt
   python seed_data.py
   ```

3. Cold starts: free Render services sleep; the first request may take ~30–60s.

### CORS

The backend already sends CORS headers for browser calls from your Vercel domain. No extra CORS env var is required for a typical setup.

---

## 3. Frontend on Vercel

### Import project

1. Vercel → **Add New** → **Project** → import the same GitHub repo.

### Critical setting: Root Directory

| Field | Value |
|--------|--------|
| **Root Directory** | `frontend` |

Do **not** use `diana-v2/frontend` — the repo root already contains `frontend/`.

**If you see `404: NOT_FOUND` on Vercel:** the project is almost always pointed at the **wrong folder**.

1. Vercel → your project → **Settings** → **General** → **Root Directory** → set to **`frontend`** → Save → **Redeploy** (Deployments → … → Redeploy).
2. **Or** leave Root Directory as **empty** (repo root): the repo now includes a root **`vercel.json`** that rewrites `/` and all paths into `/frontend/…` so the site still loads.

When Root Directory is **`frontend`**, Vercel uses `frontend/vercel.json` only; the root `vercel.json` is ignored (that is correct).

### Framework

- **Framework Preset**: **Other** (static HTML/CSS/JS).
- **Build Command**: leave **empty**.
- **Output Directory**: leave **empty** or `.` (files are served from `frontend/` root).

### Static assets

- `frontend/public/LandingImage.jpg` is served as `/LandingImage.jpg` (hero background).

### Point the UI at your API

`frontend/js/main.js` picks the API URL automatically:

- On **Vercel** (or any host that is not `localhost:5000`), it uses the Render URL **fallback** inside `main.js` (currently `https://dianabeachrestaurent-1.onrender.com`).  
- **Change that fallback** to your real Render hostname if it differs, **or** inject before `main.js` on every page:

  ```html
  <script>window.DIANA_API_BASE = 'https://YOUR-SERVICE.onrender.com';</script>
  <script src="js/main.js"></script>
  ```

  (No trailing slash; with or without `/api` is normalised.)

- When you run **Flask** and open `http://127.0.0.1:5000/`, the same `main.js` uses **relative** `/api` and your current origin for images.

### Custom domains

After you add a Vercel custom domain, you do **not** need to change Render for CORS if the API allows your frontend origin (current `app.py` reflects the request `Origin`).

---

## 4. Checklist

- [ ] Atlas network allows Render.
- [ ] Render: `MONGO_URI`, `JWT_SECRET_KEY`, `FLASK_ENV=production`, admin vars set.
- [ ] `/api/health` OK on Render.
- [ ] `seed_data.py` run against that cluster (menu + reviews).
- [ ] Vercel **Root Directory** = `frontend`.
- [ ] `main.js` fallback or `window.DIANA_API_BASE` matches your Render URL.
- [ ] Open Vercel site → Menu / Recommendations load without console network errors to `/api/...`.

---

## 5. Troubleshooting

| Problem | What to check |
|--------|----------------|
| `ModuleNotFoundError: auth` | Use **Root Directory** `backend` + `gunicorn app:app`, or latest `app.py` with the `sys.path` fix + `gunicorn backend.app:app`. |
| API 502 / timeout on first hit | Free tier cold start; wait and retry. |
| CORS errors | Confirm frontend uses the **https** Render URL; check browser Network tab for blocked preflight. |
| Images missing | Dish images come from Render `/images/...`; `main.js` prefixes with the same API host. Ensure `FoodImages` exists on the server repo and deploy includes it. |
| Wrong Python on Render | `backend/runtime.txt` should be inside the service root (set Render root to `backend`). |
| Vercel `404: NOT_FOUND` | Set **Root Directory** to `frontend` and redeploy, or leave root empty and rely on repo-root `vercel.json` rewrites into `/frontend`. |
| Vercel `404` right after “I set Root to `frontend`` | Open **Settings → General** and clear **Output Directory** (must be **empty** / default). If it is `public`, `dist`, or `build`, Vercel deploys **only that folder** — you will have **no** root `index.html` → **`/` returns 404**. Also set **Framework Preset** to **Other** and **Build Command** empty. |

### Vercel `404: NOT_FOUND` — quick fix (most common)

1. **Project → Settings → General**
2. **Root Directory**: `frontend` (when using the GitHub monorepo).
3. **Framework Preset**: **Other**
4. **Build Command**: *empty*
5. **Output Directory**: *empty* (not `public`, not `.next`, not `dist`)
6. **Install Command**: *empty*
7. **Save** → **Deployments** → **⋯** on latest → **Redeploy**

If Vercel still shows `404` for **`/`** and **`/index.html`**, open the latest deployment → **Building** log. If you see **`npm run build`** or **`Installing dependencies`** for a plain HTML site, your project is using a **Node** preset — set **Framework Preset** to **Other** and clear **Install Command** / **Build Command** / **Output Directory**, then redeploy.

After deploy, open **`https://YOUR-PROJECT.vercel.app/index.html`** — if that loads but **`/`** does not, say so (we can add an explicit rewrite in `frontend/vercel.json`).
