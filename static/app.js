/**
 * TCG Trade — SPA móvil conectada a FastAPI
 * Flujo: Inicio → Escanear → Resultado | Colección | Mercado | Perfil / Auth
 */

const API = "/api";
const TOKEN_KEY = "tcg_token";
const USER_KEY = "tcg_user";

const NAV_ITEMS = [
  { id: "home", label: "Inicio", icon: "🏠" },
  { id: "scan", label: "Escanear", icon: "⊞" },
  { id: "market", label: "Mercado", icon: "🛍" },
  { id: "profile", label: "Perfil", icon: "👤" },
];

const state = {
  screen: "home",
  scanPhase: "idle",
  activeCard: null,
  scanMethod: null,
  recentScans: [],
  collection: null,
  listings: [],
  stats: null,
  authMode: "login",
  selectedFile: null,
  previewUrl: null,
  toastTimer: null,
  loading: false,
};

const app = document.getElementById("app");
const bottomNav = document.getElementById("bottom-nav");

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    return null;
  }
}

function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function isLoggedIn() {
  return Boolean(getToken());
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.json) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.json);
    delete options.json;
  }
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail[0]?.msg : "Error de API";
    throw new Error(msg || `Error ${res.status}`);
  }
  return data;
}

function formatPrice(n) {
  return Number(n || 0).toLocaleString("es-AR");
}

function trendHtml(card, asBadge = false) {
  const dir = card.trend_dir || "stable";
  const sign = dir === "up" ? "↑" : dir === "down" ? "↓" : "→";
  const trend = card.trend || 0;
  const text = `${sign} ${trend > 0 ? "+" : ""}${trend}%`;
  if (asBadge) return `<span class="trend-badge ${dir}">${text}</span>`;
  return `<span class="trend trend-${dir}">${text}</span>`;
}

function showToast(msg) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove("show"), 2500);
}

function logoHtml() {
  return `
    <div class="screen-header">
      <h1 class="logo"><span class="logo-tcg">TCG</span><span class="logo-trade">Trade</span></h1>
      <p class="tagline">Sabé lo que vale en segundos</p>
    </div>
  `;
}

function chartHtml(history) {
  const bars = (history || [])
    .map(
      (h) => `
      <div class="chart-bar-wrap">
        <div class="chart-bar ${h.is_today ? "today" : ""}" style="height:${h.value}%"></div>
        <span class="chart-label">${h.label}</span>
      </div>`
    )
    .join("");
  return `
    <p class="chart-title">Últimos 30 días</p>
    <div class="chart-bars" role="img" aria-label="Gráfico de precio últimos 30 días">${bars}</div>
  `;
}

function thumbHtml(card) {
  if (card.image_url) return `<img src="${card.image_url}" alt="${card.name}" loading="lazy" />`;
  return "🃏";
}

function scanItemHtml(card) {
  if (!card) return "";
  return `
    <li class="scan-item" data-card-id="${card.id}" role="button" tabindex="0" aria-label="${card.name}, ${formatPrice(card.price)} pesos">
      <div class="scan-thumb">${thumbHtml(card)}</div>
      <div class="scan-info">
        <div class="scan-name">${card.name}</div>
        <div class="scan-set">${card.game} - ${card.set_name}</div>
      </div>
      <div class="scan-price-col">
        <div class="scan-price">$${formatPrice(card.price)}</div>
        ${trendHtml(card)}
      </div>
    </li>
  `;
}

function typeLabel(t) {
  return { sale: "Venta", trade: "Intercambio", negotiable: "Negociable", combo: "Combo" }[t] || t;
}

function renderHome() {
  const count = state.collection?.count ?? "—";
  return `
    ${logoHtml()}
    <div class="home-layout">
      <div class="home-primary">
        <button class="btn btn-primary btn-scan-hero" id="btn-scan-hero" aria-label="Escanear carta gratis sin registro">
          <span class="btn-icon">⊞</span>
          <span class="btn-title">Escanear carta</span>
          <span class="btn-sub">Gratis · sin registro</span>
        </button>
        <div class="tile-grid">
          <div class="tile" data-go="collection" role="button" tabindex="0">
            <span class="tile-icon">🃏</span>
            <div class="tile-title">Mi colección</div>
            <div class="tile-sub">${count} cartas</div>
          </div>
          <div class="tile" data-go="market" role="button" tabindex="0">
            <span class="tile-icon">🛍</span>
            <div class="tile-title">Mercado</div>
            <div class="tile-sub">Ver ofertas</div>
          </div>
        </div>
      </div>
      <div class="home-side">
        <p class="section-label">Últimos escaneos</p>
        <ul class="scan-list">
          ${state.recentScans.length ? state.recentScans.map(scanItemHtml).join("") : '<li class="empty-state">Todavía no hay escaneos. Tocá Escanear.</li>'}
        </ul>
      </div>
    </div>
  `;
}

function renderScanIdle() {
  const preview = state.previewUrl
    ? `<img src="${state.previewUrl}" alt="Vista previa" class="scan-preview" />`
    : `<div class="viewfinder-hint"><span class="hint-icon">📷</span>Apuntá la cámara a la carta</div>`;
  return `
    <h2 class="page-title">Escanear carta</h2>
    <p class="page-sub">IA de visión · Gratis · Sin registro</p>
    <div class="viewfinder" id="viewfinder">
      <div class="viewfinder-corner tl"></div>
      <div class="viewfinder-corner tr"></div>
      <div class="viewfinder-corner bl"></div>
      <div class="viewfinder-corner br"></div>
      ${preview}
    </div>
    <input type="file" id="scan-file" accept="image/*" capture="environment" hidden />
    <div class="action-row" style="margin-bottom:0.75rem">
      <button class="btn btn-outline btn-action-row" id="btn-pick-photo">
        <span class="btn-icon">📷</span>
        Foto / Cámara
      </button>
      <button class="btn btn-primary btn-action-row" id="btn-run-scan">
        <span class="btn-icon">⊞</span>
        Escanear
      </button>
    </div>
    <p class="page-sub" style="font-size:0.75rem;margin:0">
      Sin API key de OpenAI el backend identifica por simulación sobre la base local.
    </p>
  `;
}

function renderScanResult(card) {
  return `
    <div class="viewfinder" style="margin-bottom:0.75rem">
      <div class="viewfinder-corner tl"></div>
      <div class="viewfinder-corner tr"></div>
      <div class="viewfinder-corner bl"></div>
      <div class="viewfinder-corner br"></div>
      <div class="viewfinder-hint">
        <span class="hint-icon">🃏</span>
        Carta identificada${state.scanMethod ? ` · ${state.scanMethod}` : ""}
      </div>
    </div>
    <div class="result-card">
      ${card.image_url ? `<img src="${card.image_url}" alt="${card.name}" class="result-image" loading="lazy" />` : ""}
      <div class="result-name">${card.name}</div>
      <div class="result-meta">${card.game} - ${card.code} - ${card.rarity}</div>
      <div class="price-row">
        <div>
          <span class="price-currency">ARS</span>
          <span class="price-main">$${formatPrice(card.price)}</span>
        </div>
        ${trendHtml(card, true)}
      </div>
      ${chartHtml(card.history)}
    </div>
    <div class="action-row">
      <button class="btn btn-outline btn-action-row" id="btn-save">
        <span class="btn-icon">🔖</span>
        Guardar
      </button>
      <button class="btn btn-primary btn-action-row" id="btn-publish">
        <span class="btn-icon">🏷</span>
        Publicar
      </button>
      <button class="btn btn-outline btn-action-row" id="btn-new-scan">
        <span class="btn-icon">⊞</span>
        Nueva
      </button>
    </div>
  `;
}

function renderScan() {
  if (state.scanPhase === "result" && state.activeCard) return renderScanResult(state.activeCard);
  if (state.scanPhase === "scanning") {
    return `
      <h2 class="page-title scanning-pulse">Identificando carta…</h2>
      <div class="viewfinder">
        <div class="viewfinder-overlay"></div>
        <div class="viewfinder-hint scanning-pulse">Analizando con IA de visión</div>
      </div>
    `;
  }
  return renderScanIdle();
}

function renderCollection() {
  if (!isLoggedIn()) {
    return `
      <h2 class="page-title">Mi colección</h2>
      <p class="page-sub">Iniciá sesión para guardar cartas</p>
      <div class="empty-state">
        <div class="empty-icon">🔒</div>
        <p>Necesitás una cuenta para usar la colección.</p>
        <button class="btn btn-primary" id="btn-go-auth" style="margin-top:1rem;padding:0.75rem 1.25rem">Iniciar sesión</button>
      </div>
    `;
  }
  const items = state.collection?.items || [];
  const list = items.length
    ? `<ul class="scan-list">${items.map((i) => scanItemHtml(i.card)).join("")}</ul>`
    : `<div class="empty-state"><div class="empty-icon">🃏</div><p>Todavía no guardaste cartas.<br>Escaneá una y tocá <strong>Guardar</strong>.</p></div>`;
  return `
    <div class="collection-layout">
      <h2 class="page-title">Mi colección</h2>
      <p class="page-sub">Historial · Valor total estimado</p>
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">${state.collection?.count ?? 0}</div>
          <div class="stat-label">Cartas</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">$${formatPrice(state.collection?.total_value ?? 0)}</div>
          <div class="stat-label">Valor estimado</div>
        </div>
      </div>
      ${list}
    </div>
  `;
}

function renderMarket() {
  const listings = (state.listings || [])
    .map((l) => {
      const c = l.card;
      const priceText =
        l.listing_type === "trade" || l.price == null ? "Solo intercambio" : `$${formatPrice(l.price)}`;
      return `
      <div class="market-card" data-listing-id="${l.id}">
        <div class="scan-thumb">${thumbHtml(c)}</div>
        <div class="scan-info">
          <div class="scan-name">${c.name}</div>
          <div class="scan-set">${l.seller_username} · ${typeLabel(l.listing_type)}</div>
          ${l.wants ? `<div class="scan-set">Busca: ${l.wants}</div>` : ""}
          ${l.featured ? '<span class="market-badge">Destacada</span>' : ""}
          <div class="market-actions">
            <button class="btn btn-outline btn-mini" data-reserve="${l.id}">Reservar</button>
            <button class="btn btn-primary btn-mini" data-offer="${l.id}">Ofertar</button>
          </div>
        </div>
        <div class="scan-price-col">
          <div class="scan-price">${priceText}</div>
        </div>
      </div>`;
    })
    .join("");

  return `
    <h2 class="page-title">Mercado</h2>
    <p class="page-sub">Reservas · Ofertas · Negociación</p>
    <div class="market-grid">
      ${listings || '<div class="empty-state"><div class="empty-icon">🛍</div><p>No hay publicaciones aún.</p></div>'}
    </div>
    <p class="page-sub" style="margin-top:1rem;font-size:0.75rem">
      Publicá cartas desde el resultado del escaneo con el botón <strong>Publicar</strong>.
    </p>
  `;
}

function renderAuth() {
  const isLogin = state.authMode === "login";
  return `
    <h2 class="page-title">${isLogin ? "Iniciar sesión" : "Crear cuenta"}</h2>
    <p class="page-sub">Necesario para colección y mercado</p>
    <form class="auth-form" id="auth-form">
      <label class="auth-label">Usuario
        <input class="auth-input" name="username" autocomplete="username" required minlength="3" />
      </label>
      <label class="auth-label">Contraseña
        <input class="auth-input" name="password" type="password" autocomplete="${isLogin ? "current-password" : "new-password"}" required minlength="4" />
      </label>
      <button class="btn btn-primary" type="submit" style="width:100%;padding:0.9rem;margin-top:0.5rem">
        ${isLogin ? "Entrar" : "Registrarme"}
      </button>
    </form>
    <p class="page-sub" style="margin-top:1rem;text-align:center">
      ${isLogin ? '¿No tenés cuenta?' : "¿Ya tenés cuenta?"}
      <button class="link-btn" id="btn-toggle-auth" type="button">${isLogin ? "Registrate" : "Iniciá sesión"}</button>
    </p>
    <p class="page-sub" style="font-size:0.75rem;text-align:center">Demo: usuario <strong>demo</strong> / <strong>demo123</strong></p>
  `;
}

function renderProfile() {
  if (!isLoggedIn()) return renderAuth();
  const user = getUser();
  const stats = state.stats || { scans_count: 0, collection_count: 0, collection_value: 0 };
  return `
    <h2 class="page-title">Perfil</h2>
    <p class="page-sub">@${user?.username || "jugador"}</p>
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">${stats.scans_count}</div>
        <div class="stat-label">Escaneos</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${stats.collection_count}</div>
        <div class="stat-label">En colección</div>
      </div>
    </div>
    <div class="premium-banner">
      <h3>⭐ Premium</h3>
      <p>Alertas de precio · Análisis avanzado de mazo · Historial extendido</p>
      <button class="btn btn-primary" id="btn-premium" style="padding:0.6rem 1.25rem;font-size:0.85rem">
        Conocer planes
      </button>
    </div>
    <ul class="menu-list">
      <li class="menu-item" data-action="alerts">
        <div class="menu-icon">🔔</div>
        <div class="menu-text">
          <div class="menu-title">Alertas de precio</div>
          <div class="menu-desc">Avisos cuando sube o baja una carta</div>
        </div>
        <span class="menu-arrow">›</span>
      </li>
      <li class="menu-item" data-action="deck">
        <div class="menu-icon">📊</div>
        <div class="menu-text">
          <div class="menu-title">Análisis de mazo</div>
          <div class="menu-desc">Cartas que faltan · Meta</div>
        </div>
        <span class="menu-arrow">›</span>
      </li>
      <li class="menu-item" data-action="tournaments">
        <div class="menu-icon">🏆</div>
        <div class="menu-text">
          <div class="menu-title">Torneos</div>
          <div class="menu-desc">Notificaciones · Inscripción</div>
        </div>
        <span class="menu-arrow">›</span>
      </li>
      <li class="menu-item" data-action="logout">
        <div class="menu-icon">🚪</div>
        <div class="menu-text">
          <div class="menu-title">Cerrar sesión</div>
          <div class="menu-desc">Salir de ${user?.username || "la cuenta"}</div>
        </div>
        <span class="menu-arrow">›</span>
      </li>
    </ul>
  `;
}

function renderNav() {
  const items = NAV_ITEMS.map((item) => {
    const active = state.screen === item.id;
    return `
    <button class="nav-item${active ? " active" : ""}" data-nav="${item.id}" aria-label="${item.label}" aria-current="${active ? "page" : "false"}">
      <span class="nav-icon">${item.icon}</span>
      <span>${item.label}</span>
    </button>`;
  }).join("");

  bottomNav.innerHTML = `
    <div class="desktop-brand">
      <div class="logo"><span class="logo-tcg">TCG</span><span class="logo-trade">Trade</span></div>
      <p class="tagline">Scan & Value</p>
    </div>
    ${items}
  `;
}

function render() {
  const screens = {
    home: renderHome,
    scan: renderScan,
    collection: renderCollection,
    market: renderMarket,
    profile: renderProfile,
    auth: renderAuth,
  };
  const renderer = screens[state.screen] || renderHome;
  app.innerHTML = renderer();
  renderNav();
  bindEvents();
}

async function loadHomeData() {
  try {
    state.recentScans = await api("/scans/recent?limit=8");
  } catch {
    state.recentScans = [];
  }
  if (isLoggedIn()) {
    try {
      state.collection = await api("/collection");
    } catch {
      state.collection = null;
    }
  }
}

async function loadMarket() {
  try {
    state.listings = await api("/market/listings");
  } catch {
    state.listings = [];
  }
}

async function loadCollection() {
  if (!isLoggedIn()) return;
  state.collection = await api("/collection");
}

async function loadStats() {
  if (!isLoggedIn()) return;
  try {
    state.stats = await api("/users/me/stats");
  } catch {
    state.stats = null;
  }
}

async function navigate(screen) {
  state.screen = screen;
  if (screen !== "scan") {
    state.scanPhase = "idle";
    if (screen !== "scan") state.activeCard = null;
  }
  try {
    if (screen === "home") await loadHomeData();
    if (screen === "market") await loadMarket();
    if (screen === "collection") await loadCollection();
    if (screen === "profile" && isLoggedIn()) await loadStats();
  } catch (e) {
    showToast(e.message);
  }
  render();
}

async function runScan() {
  state.scanPhase = "scanning";
  render();
  try {
    const form = new FormData();
    if (state.selectedFile) form.append("file", state.selectedFile);
    const headers = {};
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
    const res = await fetch(`${API}/scan`, { method: "POST", body: form, headers });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Error al escanear");
    state.activeCard = data.card;
    state.scanMethod = data.method;
    state.scanPhase = "result";
    state.selectedFile = null;
    if (state.previewUrl) {
      URL.revokeObjectURL(state.previewUrl);
      state.previewUrl = null;
    }
    const exists = state.recentScans.find((c) => c.id === data.card.id);
    if (!exists) state.recentScans.unshift(data.card);
  } catch (e) {
    state.scanPhase = "idle";
    showToast(e.message);
  }
  render();
}

async function requireAuth(actionLabel) {
  if (isLoggedIn()) return true;
  showToast(`Iniciá sesión para ${actionLabel}`);
  state.authMode = "login";
  await navigate("profile");
  return false;
}

function bindEvents() {
  document.getElementById("btn-scan-hero")?.addEventListener("click", () => {
    state.screen = "scan";
    state.scanPhase = "idle";
    render();
  });

  document.getElementById("btn-pick-photo")?.addEventListener("click", () => {
    document.getElementById("scan-file")?.click();
  });

  document.getElementById("scan-file")?.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    state.selectedFile = file;
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = URL.createObjectURL(file);
    render();
  });

  document.getElementById("btn-run-scan")?.addEventListener("click", () => runScan());

  document.getElementById("btn-save")?.addEventListener("click", async () => {
    if (!(await requireAuth("guardar"))) return;
    try {
      await api(`/collection/${state.activeCard.id}`, { method: "POST" });
      showToast("Carta guardada en tu colección");
      await loadCollection();
    } catch (e) {
      showToast(e.message);
    }
  });

  document.getElementById("btn-publish")?.addEventListener("click", async () => {
    if (!(await requireAuth("publicar"))) return;
    try {
      const type = prompt("Tipo: sale / trade / negotiable / combo", "sale") || "sale";
      const wants = type === "trade" || type === "combo" ? prompt("¿Qué cartas buscás a cambio?", "") : null;
      await api("/market/listings", {
        method: "POST",
        json: {
          card_id: state.activeCard.id,
          listing_type: type,
          price: state.activeCard.price,
          wants: wants || null,
          featured: false,
        },
      });
      showToast("Carta publicada en el mercado");
      setTimeout(() => navigate("market"), 600);
    } catch (e) {
      showToast(e.message);
    }
  });

  document.getElementById("btn-new-scan")?.addEventListener("click", () => {
    state.scanPhase = "idle";
    state.activeCard = null;
    state.scanMethod = null;
    render();
  });

  document.getElementById("btn-premium")?.addEventListener("click", () => {
    showToast("Premium: alertas, análisis de mazo e historial extendido");
  });

  document.getElementById("btn-go-auth")?.addEventListener("click", () => navigate("profile"));

  document.getElementById("btn-toggle-auth")?.addEventListener("click", () => {
    state.authMode = state.authMode === "login" ? "register" : "login";
    render();
  });

  document.getElementById("auth-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const username = String(fd.get("username") || "").trim();
    const password = String(fd.get("password") || "");
    const path = state.authMode === "login" ? "/users/login" : "/users/register";
    try {
      const data = await api(path, { method: "POST", json: { username, password } });
      setAuth(data.access_token, data.user);
      showToast(`Hola, ${data.user.username}`);
      await loadStats();
      await loadCollection();
      render();
    } catch (err) {
      showToast(err.message);
    }
  });

  document.querySelectorAll("[data-go]").forEach((el) => {
    el.addEventListener("click", () => navigate(el.dataset.go));
  });

  document.querySelectorAll(".scan-item[data-card-id]").forEach((el) => {
    el.addEventListener("click", async () => {
      try {
        const card = await api(`/cards/${el.dataset.cardId}`);
        state.screen = "scan";
        state.activeCard = card;
        state.scanPhase = "result";
        state.scanMethod = "catalog";
        render();
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", () => navigate(el.dataset.nav));
  });

  document.querySelectorAll("[data-reserve]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!(await requireAuth("reservar"))) return;
      try {
        await api(`/market/listings/${el.dataset.reserve}/reserve`, { method: "POST" });
        showToast("Reserva creada");
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  document.querySelectorAll("[data-offer]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!(await requireAuth("ofertar"))) return;
      const money = prompt("Oferta en dinero (ARS, opcional)", "");
      const cardsOffer = prompt("Cartas a ofrecer (texto, opcional)", "");
      try {
        await api(`/market/listings/${el.dataset.offer}/offers`, {
          method: "POST",
          json: {
            money_offer: money ? Number(money) : null,
            cards_offer: cardsOffer || null,
          },
        });
        showToast("Oferta enviada");
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  document.querySelectorAll("[data-action]").forEach((el) => {
    el.addEventListener("click", async () => {
      const action = el.dataset.action;
      if (action === "logout") {
        clearAuth();
        state.collection = null;
        state.stats = null;
        showToast("Sesión cerrada");
        render();
        return;
      }
      const labels = {
        alerts: "Alertas de precio (función premium)",
        deck: "Análisis de mazo: cartas que faltan y meta",
        tournaments: "Torneos de tiendas asociadas",
      };
      showToast(labels[action] || "Próximamente");
    });
  });
}

(async function init() {
  await loadHomeData();
  render();
})();
