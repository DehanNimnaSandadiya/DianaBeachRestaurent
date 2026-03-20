/* ============================================================
   Diana Beach Restaurant — main.js
   Shared utilities, auth helpers, API calls
   ============================================================ */
// When deployed together with the backend on the same domain, use relative API paths.
// For local dev, open the site via `http://127.0.0.1:5000/` (not file://) so this works too.
const API = '/api';

// ─── Navbar ───────────────────────────────────────────────
const navbar = document.querySelector('.navbar');
if (navbar) {
  window.addEventListener('scroll', () => navbar.classList.toggle('scrolled', scrollY > 50));
  // always scrolled on inner pages
  if (!document.querySelector('.hero')) navbar.classList.add('scrolled');
}
const navToggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');
if (navToggle) navToggle.addEventListener('click', () => navLinks.classList.toggle('open'));

// ─── Auth Token Helpers ────────────────────────────────────
const Auth = {
  getToken: () => localStorage.getItem('diana_token'),
  getUser:  () => { try { return JSON.parse(localStorage.getItem('diana_user')); } catch { return null; } },
  isAdmin:  () => { const u = Auth.getUser(); return u && u.role === 'admin'; },
  isLoggedIn: () => !!Auth.getToken(),
  save: (token, user) => { localStorage.setItem('diana_token', token); localStorage.setItem('diana_user', JSON.stringify(user)); },
  clear: () => { localStorage.removeItem('diana_token'); localStorage.removeItem('diana_user'); },
};

// Update nav based on auth state
(function updateNav() {
  const page = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === page) a.classList.add('active');
  });
  // Inject auth links dynamically
  const nl = document.querySelector('.nav-links');
  if (!nl) return;
  const existing = nl.querySelector('.nav-auth');
  if (existing) existing.remove();
  const li = document.createElement('li');
  li.className = 'nav-auth';
  if (Auth.isLoggedIn()) {
    const user = Auth.getUser();
    li.innerHTML = Auth.isAdmin()
      ? `<a href="admin/dashboard.html">⚙️ Admin</a>`
      : `<span style="color:rgba(255,255,255,.6);font-size:.82rem;">Hi, ${user.name.split(' ')[0]}</span>`;
    const logoutLi = document.createElement('li');
    logoutLi.innerHTML = `<a href="#" id="logout-btn" style="color:var(--coral-light)!important;">Sign Out</a>`;
    nl.appendChild(li);
    nl.appendChild(logoutLi);
    document.getElementById('logout-btn').addEventListener('click', e => {
      e.preventDefault(); Auth.clear(); location.href = 'index.html';
    });
  } else {
    li.innerHTML = `<a href="login.html" class="nav-cta">Sign In</a>`;
    nl.appendChild(li);
  }
})();

// ─── Cart (No Checkout) ─────────────────────────────────────────────
const CART_STORAGE_KEY = 'diana_cart_v1';

function CartLoad() {
  try {
    return JSON.parse(localStorage.getItem(CART_STORAGE_KEY)) || [];
  } catch {
    return [];
  }
}

function CartSave(items) {
  localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
}

function CartTotalQty(items) {
  return items.reduce((sum, it) => sum + (it.qty || 0), 0);
}

function CartTotalPrice(items) {
  return items.reduce((sum, it) => sum + (Number(it.price) || 0) * (it.qty || 0), 0);
}

function escAttr(s) {
  return String(s ?? '').replace(/"/g, '&quot;');
}

function CartAddFromBtn(btn) {
  const dishId = btn.dataset.dishId;
  const name = btn.dataset.dishName || '';
  const price = Number(btn.dataset.dishPrice || 0);
  const imageUrl = btn.dataset.dishImage ? decodeURIComponent(btn.dataset.dishImage) : '';

  const items = CartLoad();
  const existing = items.find(x => String(x.dishId) === String(dishId));
  if (existing) {
    existing.qty = (existing.qty || 0) + 1;
  } else {
    items.push({ dishId, name, price, imageUrl, qty: 1 });
  }
  CartSave(items);
  updateCartBadge();
  openCartModal();
}

function updateCartBadge() {
  const badge = document.getElementById('cart-count');
  if (!badge) return;
  const items = CartLoad();
  badge.textContent = String(CartTotalQty(items));
}

function ensureCartModal() {
  if (document.getElementById('cart-modal-overlay')) return;

  const overlay = document.createElement('div');
  overlay.id = 'cart-modal-overlay';
  overlay.className = 'site-modal-overlay';
  overlay.innerHTML = `
    <div class="site-modal cart-modal" role="dialog" aria-modal="true" aria-labelledby="cart-title">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;">
        <div>
          <h2 id="cart-title" style="font-size:1.5rem;margin-bottom:.25rem;">Your Cart</h2>
          <p id="cart-subtitle" style="color:var(--text-mid);font-size:.95rem;margin-bottom:1.25rem;">Add dishes from Menu or Recommendations.</p>
        </div>
        <button type="button" id="cart-close-btn" class="modal-close" aria-label="Close">✕</button>
      </div>

      <div id="cart-items" style="margin-bottom:1.25rem;"></div>

      <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
        <div style="font-weight:700;color:var(--text-dark);">Total: <span id="cart-total-price">LKR 0</span></div>
        <div style="display:flex;gap:1rem;flex-wrap:wrap;">
          <button type="button" id="cart-clear-btn" class="btn btn-outline">Clear</button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeCartModal();
  });
  overlay.querySelector('#cart-close-btn').addEventListener('click', closeCartModal);
  overlay.querySelector('#cart-clear-btn').addEventListener('click', () => {
    CartSave([]);
    renderCartItems();
    updateCartBadge();
  });

  overlay.querySelector('#cart-items').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    const action = btn.dataset.action;
    const dishId = btn.dataset.dishId;
    if (!action || !dishId) return;

    const items = CartLoad();
    const it = items.find(x => String(x.dishId) === String(dishId));
    if (!it) return;

    if (action === 'plus') it.qty = (it.qty || 0) + 1;
    if (action === 'minus') it.qty = (it.qty || 0) - 1;
    if (action === 'remove') it.qty = 0;

    const next = items.filter(x => (x.qty || 0) > 0);
    CartSave(next);
    updateCartBadge();
    renderCartItems();
  });
}

function renderCartItems() {
  const container = document.getElementById('cart-items');
  const total = document.getElementById('cart-total-price');
  if (!container || !total) return;

  const items = CartLoad();
  if (!items.length) {
    container.innerHTML = `
      <div class="empty-state" style="padding:0;">
        <div class="empty-icon">🛒</div>
        <h3 style="margin-bottom:.5rem;">Cart is empty</h3>
        <p>Choose a dish to add it here.</p>
      </div>`;
    total.textContent = 'LKR 0';
    return;
  }

  total.textContent = `LKR ${CartTotalPrice(items).toLocaleString()}`;

  container.innerHTML = items.map(it => {
    const thumb = it.imageUrl ? `<img src="${it.imageUrl}" alt="${escAttr(it.name)}" class="cart-thumb" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">` : `<div class="cart-thumb cart-thumb-empty">🍽️</div>`;
    return `
      <div class="cart-item-row">
        <div class="cart-item-left">
          ${thumb}
          <div>
            <div class="cart-item-name">${escAttr(it.name)}</div>
            <div class="cart-item-price">LKR ${(Number(it.price) || 0).toLocaleString()}</div>
          </div>
        </div>
        <div class="cart-item-right">
          <div class="cart-qty-controls">
            <button type="button" class="cart-qty-btn" data-action="minus" data-dish-id="${it.dishId}" aria-label="Decrease">−</button>
            <span class="cart-qty">${it.qty || 0}</span>
            <button type="button" class="cart-qty-btn" data-action="plus" data-dish-id="${it.dishId}" aria-label="Increase">+</button>
          </div>
          <button type="button" class="btn btn-danger btn-sm" style="padding:.45rem 1rem;margin-left:1rem;" data-action="remove" data-dish-id="${it.dishId}">Remove</button>
        </div>
      </div>
    `;
  }).join('');
}

function openCartModal() {
  ensureCartModal();
  renderCartItems();
  updateCartBadge();
  const overlay = document.getElementById('cart-modal-overlay');
  overlay.classList.add('open');
}

function closeCartModal() {
  const overlay = document.getElementById('cart-modal-overlay');
  if (!overlay) return;
  overlay.classList.remove('open');
}

function ensureCartButton() {
  const navLinks = document.querySelector('.nav-links');
  if (!navLinks) return;
  if (document.getElementById('cart-open-btn')) return;

  const li = document.createElement('li');
  li.className = 'nav-cart';
  li.innerHTML = `<a href="#" id="cart-open-btn" class="nav-cart-link">🛒 Cart (<span id="cart-count">0</span>)</a>`;
  navLinks.appendChild(li);

  li.querySelector('#cart-open-btn').addEventListener('click', (e) => {
    e.preventDefault();
    openCartModal();
  });

  updateCartBadge();
}

// ─── Landing Recommendations Popup ───────────────────────────────────
function initRecommendationsPopup() {
  const overlay = document.getElementById('recommendations-popup-overlay');
  if (!overlay) return;

  function open() {
    overlay.style.display = 'flex';
    overlay.classList.add('open');
  }
  function close() {
    overlay.classList.remove('open');
    overlay.style.display = 'none';
  }

  const closeBtn = document.getElementById('recommendations-popup-close');
  const cancelBtn = document.getElementById('recommendations-popup-cancel');
  const goBtn = document.getElementById('recommendations-popup-go');

  if (closeBtn) closeBtn.addEventListener('click', close);
  if (cancelBtn) cancelBtn.addEventListener('click', close);
  if (goBtn) goBtn.addEventListener('click', () => {
    window.location.href = 'recommendations.html';
  });

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });

  // Always show immediately on landing page load.
  setTimeout(open, 50);
}

// Init cart UI on pages that have the navbar
ensureCartButton();
initRecommendationsPopup();
updateCartBadge();

// ─── API Helpers ──────────────────────────────────────────
async function apiGet(endpoint) {
  const headers = {};
  const token = Auth.getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${endpoint}`, { headers });
  if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.error || `HTTP ${res.status}`); }
  return res.json();
}

async function apiPost(endpoint, data) {
  const headers = { 'Content-Type': 'application/json' };
  const token = Auth.getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API}${endpoint}`, { method: 'POST', headers, body: JSON.stringify(data) });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

async function apiPut(endpoint, data) {
  const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${Auth.getToken()}` };
  const res = await fetch(`${API}${endpoint}`, { method: 'PUT', headers, body: JSON.stringify(data) });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

async function apiDelete(endpoint) {
  const res = await fetch(`${API}${endpoint}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${Auth.getToken()}` } });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

// ─── Toast ────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  let t = document.querySelector('.toast');
  if (!t) { t = document.createElement('div'); t.className = 'toast'; document.body.appendChild(t); }
  t.textContent = msg; t.className = `toast ${type}`;
  requestAnimationFrame(() => { t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 3500); });
}

// ─── Render Helpers ───────────────────────────────────────
function renderStars(r) { return '★'.repeat(Math.round(r)) + '☆'.repeat(5 - Math.round(r)); }
function dishEmoji(c) {
  return {
    'Starters': '🍤',
    'Soups': '🍲',
    'Salads': '🥗',
    'Chicken': '🍗',
    'Seafood': '🦐',
    'Pasta': '🍝',
    'Burgers & Sandwiches': '🍔',
    'Rice & Noodles': '🍜',
    'Breakfast': '🍳',
    'Desserts': '🍮',
    'Drinks': '🥤'
  }[c] || '🍽️';
}
function spiceBadge(l) {
  const cls = {'None':'spice-none','Mild':'spice-mild','Medium':'spice-medium','Hot':'spice-hot'}[l] || 'spice-mild';
  return `<span class="spice-badge ${cls}">${l==='None'?'🌿 No Spice':'🌶️ '+l}</span>`;
}
function formatPrice(p) { return `LKR ${Number(p).toLocaleString()}`; }

function renderDishCard(dish, showScore = false, score = null) {
  const emoji = dishEmoji(dish.category);
  const veg = dish.is_veg ? '<span class="dish-badge">🌿 Veg</span>' : '';
  const top = dish.is_top_seller ? '<span class="dish-badge dish-badge-top">🔥 Top Seller</span>' : '';
  const stars = renderStars(dish.avg_rating || 0);
  // In recommendation UI, show the real average rating from reviews (never the internal algorithm score).
  const showRealRating = showScore && Number(dish.review_count || 0) > 0;
  const displayRating = Math.min(5, Math.max(0, Number(dish.avg_rating || 0)));
  const displayRatingText = Number.isInteger(displayRating) ? String(displayRating) : displayRating.toFixed(1);
  const scoreHTML = showRealRating
    ? `<div style="padding:.5rem 1.25rem;border-top:1px solid var(--sand-dark);font-size:.8rem;color:var(--ocean-dark);font-weight:600;">⭐ ${displayRatingText}/5 (${dish.review_count} reviews)</div>`
    : '';
  const hasImg = dish.image_url && String(dish.image_url).trim().length > 0;
  const imgUrl = hasImg ? String(dish.image_url).trim() : '';

  const dishNameAttr = escAttr(dish.name);
  const dishImgAttr = encodeURIComponent(dish.image_url || '');

  return `<div class="dish-card" onclick="window.location='reviews.html?dish=${dish.id}'">
    <div class="dish-card-img ${hasImg ? 'has-photo' : ''}">
      ${hasImg ? `<img class="dish-photo" src="${imgUrl}" alt="${dish.name || 'Dish'}" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove();this.closest('.dish-card-img').classList.remove('has-photo');this.closest('.dish-card-img').insertAdjacentHTML('afterbegin','${emoji}');">` : emoji}
      <div class="dish-photo-overlay"></div>
      ${veg}${top}
    </div>
    <div class="dish-card-body">
      <div class="dish-card-meta"><span class="dish-category">${dish.category}</span><span class="dish-stars">${stars} <small>(${dish.review_count||0})</small></span></div>
      <h3>${dish.name}</h3><p>${dish.description}</p>
      <div class="dish-card-footer"><div class="dish-price">${formatPrice(dish.price)} <span>/ serving</span></div>${spiceBadge(dish.spice_level)}</div>
      <div class="dish-card-actions">
        <button type="button" class="btn btn-ocean btn-sm cart-add-btn"
          onclick="event.stopPropagation();CartAddFromBtn(this)"
          data-dish-id="${dish.id}"
          data-dish-name="${dishNameAttr}"
          data-dish-price="${Number(dish.price) || 0}"
          data-dish-image="${dishImgAttr}">
          + Add to Cart
        </button>
      </div>
    </div>${scoreHTML}</div>`;
}

// ─── Load Homepage Stats ──────────────────────────────────
async function loadStats() {
  try {
    const s = await apiGet('/stats');
    ['stat-dishes','stat-reviews','stat-nations'].forEach((id, i) => {
      const el = document.getElementById(id);
      if (el) el.textContent = [s.total_dishes, s.total_reviews, s.nationalities_served][i];
    });
  } catch {}
}
if (document.getElementById('stat-dishes')) loadStats();
