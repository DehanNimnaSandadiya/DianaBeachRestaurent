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

### Recommended setup (fixes most `404: NOT_FOUND`)

Vercel works most reliably when it deploys the **whole Git repo** and uses the root `vercel.json` + root `index.html` entry.

1. Vercel → **Add New** → **Project** → import **`DianaBeachRestaurentSys`** (same GitHub repo).
2. **Settings → General**:
   - **Framework Preset**: **Other**
   - **Root Directory**: **leave empty** (delete `frontend` — leave the field blank)
   - **Build Command**: **empty**
   - **Output Directory**: **empty** (must not be `public`, `dist`, or `build`)
   - **Install Command**: **empty**
3. **Save** → **Deployments** → **Redeploy**.

What happens:

- Visiting **`/`** loads repo-root **`index.html`**, which redirects the browser to **`/frontend/index.html`** so all relative links (`menu.html`, `css/...`) resolve correctly.
- **`vercel.json`** (repo root) rewrites paths like **`/menu.html`** → **`/frontend/menu.html`** for old bookmarks.

### If you insist on Root Directory = `frontend`

You can set **Root Directory** to **`frontend`**, but then:

- The repo-root **`vercel.json` is ignored** (Vercel only reads `frontend/vercel.json`).
- **Framework must be Other**, and **Build / Output / Install** must all be **empty**.

### “No logs” on Vercel

Static sites have almost nothing under **Runtime** / **Functions** logs. Always open the deployment → **Building** (build log). If the build log is empty or the deploy fails instantly, you may be on the wrong project, wrong Git branch, or a domain that is not attached to this project.

### Point the UI at your API

`frontend/js/main.js` picks the API URL automatically:

- On **Vercel** (or any host that is not `localhost:5000`), it uses the Render URL **fallback** inside `main.js` (update this to your real Render URL after deploy).  
- **Or** inject before `main.js` on every page:

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
- [ ] Vercel **Root Directory** **empty** (recommended) **or** `frontend` with Other + empty build/output.
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
| Vercel `404: NOT_FOUND` | Prefer **Root Directory empty** + redeploy. Clear **Output Directory**. Read **Build** logs (not Runtime). |
| Vercel `404` right after setting Root to `frontend` | **Framework Preset** must be **Other**; **Build / Output / Install** all **empty**. Or switch to **Root Directory empty** (recommended). |

### Vercel `404: NOT_FOUND` — quick fix (most common)

1. **Project → Settings → General**
2. **Root Directory**: **empty** (recommended) **or** `frontend` only if you keep Framework Other and empty commands.
3. **Framework Preset**: **Other**
4. **Build Command**: *empty*
5. **Output Directory**: *empty* (not `public`, not `dist`, not `build`)
6. **Install Command**: *empty*
7. **Save** → **Deployments** → **⋯** on latest → **Redeploy**

After deploy, test in this order:

1. **`https://YOUR-PROJECT.vercel.app/frontend/index.html`** — if this **404s**, the deployment is not publishing the repo (wrong Root Directory, wrong repo/branch, or Git not connected). Fix that first.
2. **`https://YOUR-PROJECT.vercel.app/`** — should **302** to `/frontend/index.html` via `vercel.json` (or show the small root `index.html` redirect).

If Vercel still shows `404` for **`/`** and **`/index.html`**, open the latest deployment → **Building** log. If you see **`npm run build`** or **`Installing dependencies`** for a plain HTML site, your project is using a **Node** preset — set **Framework Preset** to **Other** and clear **Install Command** / **Build Command** / **Output Directory**, then redeploy.
