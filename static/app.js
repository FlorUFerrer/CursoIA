/**
 * TCG Trade — SPA móvil conectada a FastAPI
 * Flujo: Inicio → Escanear → Resultado | Colección | Mercado | Perfil / Auth
 */

const API = "/api";
const TOKEN_KEY = "tcg_token";
const USER_KEY = "tcg_user";

const NAV_ITEMS = [
  { id: "home", label: "Inicio", icon: "home" },
  { id: "scan", label: "Escanear", icon: "scan-line" },
  { id: "catalog", label: "Catálogo", icon: "book-open" },
  { id: "torneos", label: "Torneos", icon: "trophy" },
  { id: "market", label: "Mercado", icon: "shopping-bag" },
  { id: "profile", label: "Perfil", icon: "user" },
];

const state = {
  screen: "home",
  scanPhase: "idle",
  activeCard: null,
  scanMethod: null,
  recentScans: [],
  collection: null,
  listings: [],
  tournaments: [],
  stats: null,
  authMode: "login",
  selectedFile: null,
  previewUrl: null,
  toastTimer: null,
  loading: false,
  catalogSets: null,
  catalogSetId: null,
  catalogCardsSetId: null,
  catalogCards: null,
  catalogLoading: false,
  scanSearchSetId: null,
  scanSearchQuery: "",
  scanSearchCards: null,
  scanSearchLoading: false,
  myTournaments: null,
  tournamentsView: "all",
  cameraStream: null,
  pendingScanCard: null,
  marketQuery: "",
  marketTypeFilter: "",
  myRegistrationIds: [],
  myRegisteredTournaments: [],
  tournamentsUserView: "all",
  tournamentQuery: "",
  chatListingId: null,
  chatListing: null,
  chatMessages: [],
  chatWs: null,
  notifyWs: null,
  unreadByListing: {},
  marketView: "all",
  myChats: null,
};

const app = document.getElementById("app");
const bottomNav = document.getElementById("bottom-nav");
const topBar = document.getElementById("top-bar");

function icon(name, cls) {
  return `<i data-lucide="${name}"${cls ? ` class="${cls}"` : ""}></i>`;
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

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

function fieldHtml(f) {
  if (f.type === "info") {
    return `<p style="font-size:0.88rem;color:var(--text-muted);margin:0.25rem 0 0.75rem">${f.label}</p>`;
  }
  if (f.type === "select") {
    const opts = (f.options || [])
      .map((o) => `<option value="${o.value}"${o.value === f.value ? " selected" : ""}>${o.label}</option>`)
      .join("");
    return `
      <label class="auth-label">${f.label}
        <select class="auth-input" name="${f.name}">${opts}</select>
      </label>`;
  }
  if (f.type === "checkbox") {
    return `
      <label class="auth-label" style="flex-direction:row;align-items:center;gap:0.5rem;cursor:pointer">
        <input type="checkbox" name="${f.name}" value="1" ${f.checked ? "checked" : ""} style="width:auto;accent-color:var(--accent)" />
        ${f.label}
      </label>`;
  }
  if (f.type === "textarea") {
    return `
      <label class="auth-label">${f.label}
        <textarea
          class="auth-input"
          name="${f.name}"
          placeholder="${f.placeholder || ""}"
          rows="3"
          style="resize:vertical"
          ${f.required ? "required" : ""}
        >${f.value != null ? f.value : ""}</textarea>
      </label>`;
  }
  return `
    <label class="auth-label">${f.label}
      <input
        class="auth-input"
        name="${f.name}"
        type="${f.type || "text"}"
        placeholder="${f.placeholder || ""}"
        value="${f.value != null ? f.value : ""}"
        ${f.min != null ? `min="${f.min}"` : ""}
        ${f.required ? "required" : ""}
      />
    </label>`;
}

/** Modal genérico en reemplazo de prompt()/alert(). Devuelve una Promise con
 * los valores del form (por nombre de campo) o null si se cancela. */
function openModal({ title, fields, confirmLabel = "Confirmar", cancelLabel = "Cancelar" }) {
  return new Promise((resolve) => {
    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML = `
      <div class="modal-card" role="dialog" aria-modal="true" aria-label="${title}">
        <h3 class="modal-title">${title}</h3>
        <form class="modal-form">
          ${fields.map(fieldHtml).join("")}
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" data-modal-cancel>${cancelLabel}</button>
            <button type="submit" class="btn btn-primary" data-modal-confirm>${confirmLabel}</button>
          </div>
        </form>
      </div>
    `;
    document.body.appendChild(overlay);

    const onKeydown = (e) => {
      if (e.key === "Escape") close(null);
    };
    document.addEventListener("keydown", onKeydown);

    function close(result) {
      document.removeEventListener("keydown", onKeydown);
      overlay.remove();
      resolve(result);
    }

    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close(null);
    });
    overlay.querySelector("[data-modal-cancel]").addEventListener("click", () => close(null));
    overlay.querySelector(".modal-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const result = {};
      fields.forEach((f) => {
        if (f.type === "checkbox") result[f.name] = e.target.querySelector(`[name="${f.name}"]`)?.checked || false;
        else if (f.type === "info") result[f.name] = null;
        else result[f.name] = fd.get(f.name);
      });
      close(result);
    });

    overlay.querySelector(".auth-input")?.focus();
  });
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
  return icon("layers", "thumb-icon");
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
          ${icon("scan-line", "btn-icon")}
          <span class="btn-title">Escanear carta</span>
          <span class="btn-sub">Gratis · sin registro</span>
        </button>
        <div class="tile-grid">
          <div class="tile" data-go="collection" role="button" tabindex="0">
            ${icon("layers", "tile-icon")}
            <div class="tile-title">Mi colección</div>
            <div class="tile-sub">${count} cartas</div>
          </div>
          <div class="tile" data-go="market" role="button" tabindex="0">
            ${icon("shopping-bag", "tile-icon")}
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

function renderScanSearch() {
  const sets = state.catalogSets || [];
  const setOptions = sets
    .map(
      (s) =>
        `<option value="${s.set_id}"${s.set_id === state.scanSearchSetId ? " selected" : ""}>${s.set_id} · ${s.name}</option>`
    )
    .join("");

  const query = (state.scanSearchQuery || "").toLowerCase();
  const filtered = (state.scanSearchCards || []).filter(
    (c) => !query || c.name.toLowerCase().includes(query) || c.rarity.toLowerCase().includes(query)
  );

  let listHtml;
  if (!state.scanSearchSetId) {
    listHtml = '<li class="empty-state">Seleccioná una temporada para ver las cartas.</li>';
  } else if (state.scanSearchLoading) {
    listHtml = '<li class="empty-state">Cargando cartas…</li>';
  } else if (!filtered.length) {
    listHtml = '<li class="empty-state">Sin resultados. Probá otro nombre.</li>';
  } else {
    listHtml = filtered.map(scanItemHtml).join("");
  }

  return `
    <div class="action-row" style="margin-bottom:0.75rem">
      <button class="btn btn-outline btn-action-row" id="btn-search-back">
        ${icon("arrow-left", "btn-icon")}
        Volver
      </button>
    </div>
    <h2 class="page-title">Buscar carta</h2>
    <p class="page-sub">Elegí la temporada y buscá por nombre</p>
    <label class="auth-label" style="display:block;margin-bottom:0.5rem">Temporada / Set
      <select class="auth-input" id="scan-search-set">
        <option value="">— Seleccioná una temporada —</option>
        ${setOptions}
      </select>
    </label>
    <div class="search-box" style="margin-bottom:0.75rem">
      ${icon("search", "search-icon")}
      <input class="auth-input search-input" id="scan-search-input"
             placeholder="Nombre de la carta…"
             value="${state.scanSearchQuery || ""}" />
    </div>
    <ul class="scan-list" id="scan-search-list">${listHtml}</ul>
  `;
}

function stopCameraStream() {
  if (state.cameraStream) {
    state.cameraStream.getTracks().forEach((t) => t.stop());
    state.cameraStream = null;
  }
}

function closeChatWs() {
  if (state.chatWs) {
    state.chatWs.close();
    state.chatWs = null;
  }
}

function playNotifySound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.setValueAtTime(660, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch (_) {}
}

function totalUnread() {
  return Object.values(state.unreadByListing).reduce((a, b) => a + b.count, 0);
}

function updateNotifBadge() {
  const total = totalUnread();
  const badge = document.getElementById("nav-market-badge");
  if (badge) {
    badge.textContent = total > 9 ? "9+" : String(total);
    badge.style.display = total > 0 ? "inline-flex" : "none";
  }
}

function openNotifyWs() {
  if (!isLoggedIn()) return;
  if (state.notifyWs && state.notifyWs.readyState <= 1) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/notify?token=${encodeURIComponent(getToken())}`);
  state.notifyWs = ws;
  ws.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type !== "new_message") return;
    // Ignore if user is already viewing that exact chat
    if (state.screen === "chat" && state.chatListingId === data.listing_id) return;
    const lid = data.listing_id;
    if (!state.unreadByListing[lid]) {
      state.unreadByListing[lid] = {
        count: 0,
        card_name: data.card_name,
        seller_id: data.seller_id,
        seller_username: data.seller_username,
        listing_type: data.listing_type,
      };
    }
    state.unreadByListing[lid].count += 1;
    updateNotifBadge();
    playNotifySound();
  };
  ws.onclose = () => {
    state.notifyWs = null;
    if (isLoggedIn()) setTimeout(openNotifyWs, 5000);
  };
}

function closeNotifyWs() {
  if (state.notifyWs) {
    state.notifyWs.onclose = null; // prevent auto-reconnect
    state.notifyWs.close();
    state.notifyWs = null;
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderScanCamera() {
  return `
    <h2 class="page-title">Escanear carta</h2>
    <p class="page-sub">Apuntá la cámara a la carta y capturá</p>
    <div class="viewfinder" id="viewfinder">
      <div class="viewfinder-corner tl"></div>
      <div class="viewfinder-corner tr"></div>
      <div class="viewfinder-corner bl"></div>
      <div class="viewfinder-corner br"></div>
      <video id="scan-video" autoplay playsinline style="width:100%;height:100%;object-fit:cover;border-radius:inherit"></video>
    </div>
    <div class="action-row" style="margin-bottom:0.75rem">
      <button class="btn btn-primary btn-action-row" id="btn-capture">
        ${icon("camera", "btn-icon")}
        Capturar
      </button>
      <button class="btn btn-outline btn-action-row" id="btn-cancel-camera">
        ${icon("x", "btn-icon")}
        Cancelar
      </button>
    </div>
  `;
}

function renderScanIdle() {
  const preview = state.previewUrl
    ? `<img src="${state.previewUrl}" alt="Vista previa" class="scan-preview" />`
    : `<div class="viewfinder-hint">${icon("camera", "hint-icon")}Apuntá la cámara a la carta</div>`;
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
    <input type="file" id="scan-file-gallery" accept="image/*" hidden />
    <div class="action-row" style="margin-bottom:0.75rem">
      <button class="btn btn-primary btn-action-row" id="btn-run-scan">
        ${icon("scan-line", "btn-icon")}
        Escanear
      </button>
      <button class="btn btn-outline btn-action-row" id="btn-upload-image">
        ${icon("image", "btn-icon")}
        Subir imagen
      </button>
      <button class="btn btn-outline btn-action-row" id="btn-open-search">
        ${icon("search", "btn-icon")}
        Buscar
      </button>
    </div>
    <p class="page-sub" style="font-size:0.75rem;margin:0">
      Sin API key de IA configurada el backend identifica por simulación sobre la base local.
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
        ${icon("layers", "hint-icon")}
        Carta identificada${state.scanMethod ? ` · ${state.scanMethod}` : ""}
      </div>
    </div>
    <div class="action-row" style="margin-bottom:1rem">
      <button class="btn btn-outline btn-action-row" id="btn-save">
        ${icon("bookmark", "btn-icon")}
        Guardar
      </button>
      <button class="btn btn-primary btn-action-row" id="btn-publish">
        ${icon("tag", "btn-icon")}
        Publicar
      </button>
      <button class="btn btn-outline btn-action-row" id="btn-new-scan">
        ${icon("scan-line", "btn-icon")}
        Nueva
      </button>
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
  `;
}

function renderScan() {
  if (state.scanPhase === "search") return renderScanSearch();
  if (state.scanPhase === "camera") return renderScanCamera();
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
        <div class="empty-icon">${icon("lock")}</div>
        <p>Necesitás una cuenta para usar la colección.</p>
        <button class="btn btn-primary" id="btn-go-auth" style="margin-top:1rem;padding:0.75rem 1.25rem">Iniciar sesión</button>
      </div>
    `;
  }
  const items = state.collection?.items || [];
  const list = items.length
    ? `<ul class="scan-list">${items.map((i) => scanItemHtml(i.card)).join("")}</ul>`
    : `<div class="empty-state"><div class="empty-icon">${icon("layers")}</div><p>Todavía no guardaste cartas.<br>Escaneá una y tocá <strong>Guardar</strong>.</p></div>`;
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

function catalogListHtml(cards) {
  if (!cards.length) return '<li class="empty-state">No se encontraron cartas.</li>';
  return cards.map(scanItemHtml).join("");
}

function renderCatalog() {
  const cards = state.catalogCards || [];
  const sets = state.catalogSets || [];
  const options = sets
    .map(
      (s) =>
        `<option value="${s.set_id}"${s.set_id === state.catalogSetId ? " selected" : ""}>${s.set_name} (${s.set_id})</option>`
    )
    .join("");
  const listHtml = state.catalogLoading
    ? '<li class="empty-state">Cargando cartas del set…</li>'
    : catalogListHtml(cards);
  return `
    <h2 class="page-title">Catálogo</h2>
    <p class="page-sub">${state.catalogLoading ? "Cargando…" : `${cards.length} cartas`}</p>
    <select class="auth-input" id="catalog-set-select" style="width:100%;margin-bottom:0.5rem">${options}</select>
    <div class="search-box">
      ${icon("search", "search-icon")}
      <input class="auth-input search-input" id="catalog-search" placeholder="Buscar por nombre, set o rareza..." />
    </div>
    <ul class="scan-list" id="catalog-list">${listHtml}</ul>
  `;
}

function tournamentCardHtml(t, showEdit = false) {
  const isCancelled = t.status === "cancelled";
  const user = getUser();
  const isOrganizer = user && t.organizer_id === user.id;
  const isRegistered = state.myRegistrationIds.includes(t.id);
  const isFull = t.max_participants != null && t.participants_count >= t.max_participants;
  const registerBtn =
    !showEdit && !isCancelled && isLoggedIn() && !isOrganizer
      ? isRegistered
        ? `<button class="btn btn-outline btn-mini" style="color:#f87171;border-color:#f87171" data-unregister-tournament="${t.id}">Desanotarme</button>`
        : isFull
          ? `<span class="scan-set" style="font-size:0.8rem;color:#f87171">Cupo lleno</span>`
          : `<button class="btn btn-primary btn-mini" data-register-tournament="${t.id}">Inscribirme</button>`
      : "";
  const editBtns = showEdit && !isCancelled
    ? `<div class="market-actions" style="margin-top:0.5rem">
        <button class="btn btn-outline btn-mini" data-edit-tournament="${t.id}">Editar</button>
        <button class="btn btn-mini" style="background:#7f1d1d;color:#fca5a5;border:1px solid #991b1b" data-cancel-tournament="${t.id}">Cancelar torneo</button>
      </div>`
    : "";
  const cancelledBadge = isCancelled
    ? `<span class="market-badge" style="background:#7f1d1d;color:#fca5a5">Cancelado</span>`
    : "";
  const idBadge = `<span class="market-badge" style="background:#1e3a5f;color:#93c5fd;font-size:0.7rem;margin-left:0.3rem">#${t.id}</span>`;
  const cancelReason = isCancelled && t.cancellation_reason
    ? `<div class="scan-set" style="margin-top:0.3rem;font-size:0.78rem;color:#fca5a5">${icon("alert-circle", "icon-inline")} Motivo: ${t.cancellation_reason}</div>`
    : "";
  const borderColor = isCancelled ? "#7f1d1d" : "#f59e0b33";
  const titleColor = isCancelled ? "#fca5a5" : "#f59e0b";
  return `
    <div class="market-card" style="background:linear-gradient(135deg,#1a1a2e,#16213e);border:1px solid ${borderColor}">
      <div class="scan-info" style="flex:1">
        <div class="scan-name" style="color:${titleColor}${showEdit ? ";cursor:pointer" : ""}" ${showEdit ? `data-tournament-detail="${t.id}"` : ""}>${t.title} ${cancelledBadge}${idBadge}</div>
        <div class="scan-set">${icon("store", "icon-inline")} ${t.organizer_username}${t.event_date ? ` · ${icon("calendar", "icon-inline")} ${t.event_date}` : ""}</div>
        ${t.location ? `<div class="scan-set">${icon("map-pin", "icon-inline")} ${t.location}</div>` : ""}
        ${t.description ? `<div class="scan-set" style="margin-top:0.3rem;font-size:0.78rem;opacity:0.85">${t.description}</div>` : ""}
        ${(() => {
          const count = t.participants_count || 0;
          const max = t.max_participants;
          if (!max) return count > 0 ? `<div class="scan-set">${icon("users", "icon-inline")} ${count} inscripto${count !== 1 ? "s" : ""}</div>` : "";
          const full = count >= max;
          return `<div class="scan-set" style="${full ? "color:#f87171" : ""}">${icon("users", "icon-inline")} ${count}/${max} inscriptos${full ? " · Cupo lleno" : ""}</div>`;
        })()}
        ${cancelReason}
        ${registerBtn || editBtns}
      </div>
    </div>`;
}

async function openChat(listingId, preloadedListing = null) {
  if (!(await requireAuth("chatear"))) return;
  const listing = preloadedListing || (state.listings || []).find((l) => l.id === listingId);
  if (!listing) { showToast("Publicación no encontrada"); return; }
  closeChatWs();
  delete state.unreadByListing[listingId];
  updateNotifBadge();
  state.chatListingId = listingId;
  state.chatListing = listing;
  state.chatMessages = [];
  try {
    state.chatMessages = await api(`/messages/${listingId}`);
  } catch {
    state.chatMessages = [];
  }
  state.screen = "chat";
  render();
}

function marketCardHtml(l) {
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
      ${isLoggedIn() ? `<div class="market-actions"><button class="btn btn-outline btn-mini" data-chat="${l.id}">${icon("message-circle", "icon-inline")} Chat</button></div>` : ""}
    </div>
    <div class="scan-price-col">
      <div class="scan-price">${priceText}</div>
    </div>
  </div>`;
}

function filterMarketListings() {
  const q = state.marketQuery.toLowerCase();
  const type = state.marketTypeFilter;
  return (state.listings || []).filter((l) => {
    const c = l.card;
    const matchType = !type || l.listing_type === type;
    const matchQ =
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.set_name.toLowerCase().includes(q) ||
      c.code.toLowerCase().includes(q) ||
      c.rarity.toLowerCase().includes(q) ||
      l.seller_username.toLowerCase().includes(q) ||
      (l.wants || "").toLowerCase().includes(q);
    return matchType && matchQ;
  });
}

function chatSummaryHtml(chat) {
  const time = new Date(chat.last_at).toLocaleString("es-AR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const preview = chat.last_content.length > 60
    ? chat.last_content.slice(0, 60) + "…"
    : chat.last_content;
  const unread = state.unreadByListing[chat.listing_id];
  const unreadBadge = unread && unread.count > 0
    ? `<span class="notif-badge" style="position:static;margin-left:auto;flex-shrink:0">${unread.count > 9 ? "9+" : unread.count}</span>`
    : "";
  const bold = unread && unread.count > 0 ? "font-weight:600;" : "";
  return `
    <div class="market-card" style="cursor:pointer" data-open-chat="${chat.listing_id}"
         data-chat-card="${escapeHtml(chat.card_name)}"
         data-chat-seller="${escapeHtml(chat.seller_username)}"
         data-chat-seller-id="${chat.seller_id}"
         data-chat-type="${chat.listing_type}">
      <div class="scan-info" style="flex:1;min-width:0">
        <div class="scan-name" style="${bold}display:flex;align-items:center;gap:0.4rem">
          ${escapeHtml(chat.card_name)}${unreadBadge}
        </div>
        <div class="scan-set">${icon("store", "icon-inline")} ${escapeHtml(chat.seller_username)}</div>
        <div class="scan-set" style="margin-top:0.3rem;font-style:italic;opacity:0.85">"${escapeHtml(preview)}"</div>
        <div class="scan-set" style="font-size:0.7rem;margin-top:0.15rem">
          ${icon("clock", "icon-inline")} ${time} · ${escapeHtml(chat.last_sender)}
        </div>
      </div>
      <div style="align-self:center;padding-left:0.5rem">${icon("chevron-right", "icon-inline")}</div>
    </div>`;
}

function renderMarket() {
  const showChats = isLoggedIn() && state.marketView === "mychats";

  const tabs = isLoggedIn()
    ? `<div class="action-row" style="margin-bottom:1rem">
        <button class="btn ${state.marketView === "all" ? "btn-primary" : "btn-outline"} btn-action-row" data-market-view="all">Publicaciones</button>
        <button class="btn ${state.marketView === "mychats" ? "btn-primary" : "btn-outline"} btn-action-row" data-market-view="mychats">${icon("message-circle", "icon-inline")} Mis chats</button>
      </div>`
    : "";

  if (showChats) {
    const chats = [...(state.myChats || [])].sort((a, b) => {
      const aU = (state.unreadByListing[a.listing_id]?.count || 0) > 0;
      const bU = (state.unreadByListing[b.listing_id]?.count || 0) > 0;
      if (aU !== bU) return aU ? -1 : 1;
      return new Date(b.last_at) - new Date(a.last_at);
    });
    const listHtml = chats.length
      ? `<div class="market-grid">${chats.map(chatSummaryHtml).join("")}</div>`
      : `<div class="empty-state"><div class="empty-icon">${icon("message-circle")}</div><p>Todavía no tenés conversaciones.</p></div>`;
    return `
      <h2 class="page-title">Mercado</h2>
      <p class="page-sub">Tus conversaciones activas</p>
      ${tabs}
      ${listHtml}
    `;
  }

  const filtered = filterMarketListings();
  const listHtml = filtered.length
    ? filtered.map(marketCardHtml).join("")
    : `<div class="empty-state"><div class="empty-icon">${icon("shopping-bag")}</div><p>No hay publicaciones que coincidan.</p></div>`;

  return `
    <h2 class="page-title">Mercado</h2>
    <p class="page-sub">Reservas · Ofertas · Negociación</p>
    ${tabs}
    <div class="search-box">
      ${icon("search", "search-icon")}
      <input class="auth-input search-input" id="market-search" placeholder="Buscar por carta, vendedor, set..." />
    </div>
    <select class="auth-input" id="market-type-filter" style="width:100%;margin-bottom:0.75rem">
      <option value="">Todos los tipos</option>
      <option value="sale"${state.marketTypeFilter === "sale" ? " selected" : ""}>Venta</option>
      <option value="trade"${state.marketTypeFilter === "trade" ? " selected" : ""}>Intercambio</option>
      <option value="negotiable"${state.marketTypeFilter === "negotiable" ? " selected" : ""}>Negociable</option>
      <option value="combo"${state.marketTypeFilter === "combo" ? " selected" : ""}>Combo</option>
    </select>
    <div class="market-grid" id="market-grid">${listHtml}</div>
    <p class="page-sub" style="margin-top:1rem;font-size:0.75rem">
      Publicá cartas desde el resultado del escaneo con el botón <strong>Publicar</strong>.
    </p>
  `;
}

function renderTorneos() {
  const user = getUser();
  const isStore = Boolean(user?.is_store);
  const isLoggedInUser = isLoggedIn() && !isStore;

  const showMine = isStore && state.tournamentsView === "mine";
  const showRegistered = isLoggedInUser && state.tournamentsUserView === "registered";

  let tournaments, emptyMsg, subtitle;
  if (showMine) {
    tournaments = state.myTournaments || [];
    emptyMsg = "Todavía no publicaste ningún torneo.";
    subtitle = "Torneos que publicaste como tienda";
  } else if (showRegistered) {
    tournaments = state.myRegisteredTournaments || [];
    emptyMsg = "Todavía no te inscribiste a ningún torneo.";
    subtitle = "Torneos en los que estás anotado";
  } else {
    tournaments = state.tournaments || [];
    emptyMsg = "No hay torneos activos por ahora.";
    subtitle = "Torneos activos de tiendas asociadas";
  }

  const tabsHtml = isStore
    ? `<div class="action-row" style="margin-bottom:1rem">
        <button class="btn ${state.tournamentsView === "all" ? "btn-primary" : "btn-outline"} btn-action-row" data-tournaments-view="all">Todos</button>
        <button class="btn ${state.tournamentsView === "mine" ? "btn-primary" : "btn-outline"} btn-action-row" data-tournaments-view="mine">Mis Torneos</button>
        <button class="btn btn-outline btn-action-row" data-action="publish-tournament">${icon("plus", "btn-icon")} Crear torneo</button>
      </div>`
    : isLoggedInUser
    ? `<div class="action-row" style="margin-bottom:1rem">
        <button class="btn ${state.tournamentsUserView === "all" ? "btn-primary" : "btn-outline"} btn-action-row" data-tournaments-user-view="all">Todos</button>
        <button class="btn ${state.tournamentsUserView === "registered" ? "btn-primary" : "btn-outline"} btn-action-row" data-tournaments-user-view="registered">Mis inscripciones</button>
      </div>`
    : "";

  const searchBox = !showRegistered
    ? `<div class="search-box">
        ${icon("search", "search-icon")}
        <input class="auth-input search-input" id="tournament-search" placeholder="Buscar por nombre, tienda, lugar o #ID..." />
      </div>`
    : "";

  const filtered = state.tournamentQuery
    ? tournaments.filter((t) => {
        const q = state.tournamentQuery.toLowerCase().replace(/^#/, "");
        return (
          t.title.toLowerCase().includes(q) ||
          t.organizer_username.toLowerCase().includes(q) ||
          (t.location || "").toLowerCase().includes(q) ||
          String(t.id).includes(q)
        );
      })
    : tournaments;

  const list = filtered.length
    ? `<div class="market-grid" id="tournament-grid">${filtered.map((t) => tournamentCardHtml(t, showMine)).join("")}</div>`
    : `<div class="empty-state"><div class="empty-icon">${icon("trophy")}</div><p>${tournaments.length ? "Sin resultados." : emptyMsg}</p></div>`;

  return `
    <h2 class="page-title">Torneos</h2>
    <p class="page-sub">${subtitle}</p>
    ${tabsHtml}
    ${searchBox}
    ${list}
  `;
}

function renderChat() {
  const l = state.chatListing;
  if (!l) return `<p class="page-sub">Error: no hay chat activo.</p>`;
  const me = getUser();
  const msgs = state.chatMessages || [];
  const msgsHtml = msgs.length
    ? msgs
        .map((m) => {
          const isMe = me && m.sender_id === me.id;
          const time = new Date(m.created_at).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
          return `<div class="chat-msg ${isMe ? "chat-msg-me" : "chat-msg-other"}">
            ${!isMe ? `<div class="chat-sender">${escapeHtml(m.sender_username)}</div>` : ""}
            <div class="chat-bubble">${escapeHtml(m.content)}</div>
            <div class="chat-time">${time}</div>
          </div>`;
        })
        .join("")
    : `<div class="chat-empty">Todavía no hay mensajes. ¡Sé el primero en escribir!</div>`;
  return `
    <div class="chat-header">
      <button class="btn btn-outline btn-mini" data-go="market">${icon("arrow-left", "icon-inline")} Volver</button>
      <div class="chat-header-info">
        <div class="scan-name" style="font-size:0.95rem">${escapeHtml(l.card.name)}</div>
        <div class="scan-set">${icon("store", "icon-inline")} ${escapeHtml(l.seller_username)}</div>
      </div>
    </div>
    <div class="chat-messages" id="chat-messages">${msgsHtml}</div>
    <div class="chat-input-row">
      <input class="auth-input chat-input-field" id="chat-input" placeholder="Escribí un mensaje..." autocomplete="off" />
      <button class="btn btn-primary chat-send-btn" id="chat-send">${icon("send", "icon-inline")}</button>
    </div>
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
    <p class="page-sub" style="font-size:0.75rem;text-align:center">
      Demo: <strong>usuario</strong> / <strong>usuario123</strong> (premium) ·
      <strong>tienda</strong> / <strong>tienda123</strong> (tienda) ·
      <strong>otrousuario</strong> / <strong>otrousuario123</strong>
    </p>
  `;
}

function renderProfile() {
  if (!isLoggedIn()) return renderAuth();
  const user = getUser();
  const stats = state.stats || { scans_count: 0, collection_count: 0, collection_value: 0 };
  const isPremium = user?.is_premium;
  const isStore = user?.is_store;

  const premiumBlock = isPremium
    ? `<div class="premium-banner" style="background:linear-gradient(135deg,#065f46,#064e3b);border:1px solid #34d39966">
        <h3>${icon("crown", "icon-inline")} Premium activo</h3>
        <p>Tenés acceso a alertas de precio · Análisis avanzado de mazo · Historial extendido</p>
       </div>`
    : `<div class="premium-banner">
        <h3>${icon("crown", "icon-inline")} Premium</h3>
        <p>Alertas de precio · Análisis avanzado de mazo · Historial extendido</p>
        <button class="btn btn-primary" id="btn-premium" style="padding:0.6rem 1.25rem;font-size:0.85rem">
          Conocer planes
        </button>
       </div>`;

  const storeMenuItem = isStore
    ? `<li class="menu-item" data-action="publish-tournament">
        <div class="menu-icon">${icon("trophy")}</div>
        <div class="menu-text">
          <div class="menu-title">Publicar Torneo</div>
          <div class="menu-desc">Crear un torneo visible para todos los usuarios</div>
        </div>
        ${icon("chevron-right", "menu-arrow")}
       </li>`
    : "";

  const alertsItem = isPremium
    ? `<li class="menu-item" data-action="alerts">
        <div class="menu-icon">${icon("bell")}</div>
        <div class="menu-text">
          <div class="menu-title">Alertas de precio</div>
          <div class="menu-desc">Avisos cuando sube o baja una carta</div>
        </div>
        ${icon("chevron-right", "menu-arrow")}
       </li>`
    : "";

  const deckItem = isPremium
    ? `<li class="menu-item" data-action="deck">
        <div class="menu-icon">${icon("bar-chart-3")}</div>
        <div class="menu-text">
          <div class="menu-title">Análisis de mazo</div>
          <div class="menu-desc">Cartas que faltan · Meta</div>
        </div>
        ${icon("chevron-right", "menu-arrow")}
       </li>`
    : "";

  const subtitleTag = [isStore ? "Tienda" : "", isPremium ? `${icon("crown", "icon-inline")} Premium` : ""]
    .filter(Boolean)
    .join(" · ");

  return `
    <h2 class="page-title">Perfil</h2>
    <p class="page-sub">@${user?.username || "jugador"}${subtitleTag ? ` · ${subtitleTag}` : ""}</p>
    <div class="stat-grid">
      <div class="stat-card" style="cursor:pointer" data-go="scan">
        <div class="stat-value">${stats.scans_count}</div>
        <div class="stat-label">Escaneos</div>
      </div>
      <div class="stat-card" style="cursor:pointer" data-go="collection">
        <div class="stat-value">${stats.collection_count}</div>
        <div class="stat-label">En colección</div>
      </div>
    </div>
    <div class="premium-banner" style="margin-bottom:1rem">
      <h3 style="margin-bottom:0.6rem">${icon("user", "icon-inline")} Datos personales</h3>
      <div style="font-size:0.88rem;color:var(--text-muted);margin-bottom:0.75rem">
        ${user.first_name || user.last_name ? `<div>${user.first_name || ""} ${user.last_name || ""}</div>` : ""}
        ${user.dni ? `<div>DNI: ${user.dni}</div>` : `<div style="color:#f87171">DNI no cargado — necesario para inscribirse a torneos</div>`}
      </div>
      <button class="btn btn-outline" id="btn-edit-profile" style="padding:0.5rem 1rem;font-size:0.85rem">Editar datos</button>
    </div>
    ${premiumBlock}
    <ul class="menu-list">
      ${storeMenuItem}
      ${alertsItem}
      ${deckItem}
    </ul>
  `;
}

function renderNav() {
  const total = totalUnread();
  const items = NAV_ITEMS.map((item) => {
    const active = state.screen === item.id;
    const badge = item.id === "market" && total > 0
      ? `<span id="nav-market-badge" class="nav-badge">${total > 9 ? "9+" : total}</span>`
      : item.id === "market"
        ? `<span id="nav-market-badge" class="nav-badge" style="display:none">0</span>`
        : "";
    return `
    <button class="nav-item${active ? " active" : ""}" data-nav="${item.id}" aria-label="${item.label}" aria-current="${active ? "page" : "false"}" style="position:relative">
      ${icon(item.icon, "nav-icon")}
      <span>${item.label}</span>
      ${badge}
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

function renderTopBar() {
  const user = getUser();
  if (!isLoggedIn() || !user) return "";
  return `
    <span class="top-bar-user">@${user.username}</span>
    <button class="top-bar-logout" id="btn-logout-top" aria-label="Cerrar sesión" title="Cerrar sesión">
      ${icon("log-out")}
    </button>
  `;
}

function bindTopBarEvents() {
  document.getElementById("btn-logout-top")?.addEventListener("click", performLogout);
}

function performLogout() {
  closeNotifyWs();
  closeChatWs();
  clearAuth();
  state.collection = null;
  state.stats = null;
  state.unreadByListing = {};
  showToast("Sesión cerrada");
  navigate("profile");
}

function render() {
  const screens = {
    home: renderHome,
    scan: renderScan,
    catalog: renderCatalog,
    collection: renderCollection,
    market: renderMarket,
    torneos: renderTorneos,
    profile: renderProfile,
    auth: renderAuth,
    chat: renderChat,
  };
  const renderer = screens[state.screen] || renderHome;
  app.innerHTML = renderer();
  renderNav();
  topBar.innerHTML = renderTopBar();
  bindTopBarEvents();
  bindEvents();
  refreshIcons();
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

async function loadCatalogSets() {
  if (state.catalogSets) return;
  try {
    const data = await api("/catalog/sets");
    state.catalogSets = data.sets || [];
    state.catalogSetId = data.default_set_id;
  } catch (e) {
    state.catalogSets = [];
    showToast(e.message);
  }
}

async function loadCatalogCards(setId) {
  state.catalogLoading = true;
  try {
    state.catalogCards = await api(`/cards?set_id=${encodeURIComponent(setId)}`);
    state.catalogCardsSetId = setId;
  } catch (e) {
    state.catalogCards = [];
    showToast(e.message);
  }
  state.catalogLoading = false;
}

async function loadMarket() {
  try {
    state.listings = await api("/market/listings");
  } catch {
    state.listings = [];
  }
}

async function loadMyTournaments() {
  if (!isLoggedIn()) return;
  try {
    state.myTournaments = await api("/tournaments/mine");
  } catch {
    state.myTournaments = [];
  }
}

async function loadTorneos() {
  try {
    state.tournaments = await api("/tournaments");
  } catch {
    state.tournaments = [];
  }
  const user = getUser();
  if (user?.is_store) {
    await loadMyTournaments();
  }
  if (isLoggedIn()) {
    try {
      const registered = await api("/tournaments/mine-registered");
      state.myRegistrationIds = registered.map((t) => t.id);
      state.myRegisteredTournaments = registered;
    } catch {
      state.myRegistrationIds = [];
      state.myRegisteredTournaments = [];
    }
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
  if (screen !== "chat") closeChatWs();
  if (screen !== "scan") stopCameraStream();
  state.screen = screen;
  if (screen !== "scan") {
    state.scanPhase = "idle";
    state.activeCard = null;
    state.scanSearchSetId = null;
    state.scanSearchCards = null;
    state.scanSearchQuery = "";
  }
  try {
    if (screen === "home") await loadHomeData();
    if (screen === "catalog") {
      await loadCatalogSets();
      if (state.catalogSetId && state.catalogCardsSetId !== state.catalogSetId) {
        await loadCatalogCards(state.catalogSetId);
      }
    }
    if (screen === "market") await loadMarket();
    if (screen === "torneos") await loadTorneos();
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

async function openCardDetail(cardId) {
  try {
    const card = await api(`/cards/${cardId}`);
    state.screen = "scan";
    state.activeCard = card;
    state.scanPhase = "result";
    state.scanMethod = "catalog";
    render();
  } catch (e) {
    showToast(e.message);
  }
}

async function requireAuth(actionLabel) {
  if (isLoggedIn()) return true;
  showToast(`Iniciá sesión para ${actionLabel}`);
  if (state.activeCard) state.pendingScanCard = state.activeCard;
  state.authMode = "login";
  await navigate("profile");
  return false;
}

function bindMarketCardEvents() {
  document.querySelectorAll("[data-chat]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      await openChat(Number(el.dataset.chat));
    });
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
      const result = await openModal({
        title: "Hacer una oferta",
        confirmLabel: "Ofertar",
        fields: [
          { name: "money", label: "Oferta en dinero (ARS)", type: "number", placeholder: "Opcional" },
          { name: "cardsOffer", label: "Cartas a ofrecer", type: "text", placeholder: "Opcional" },
        ],
      });
      if (!result) return;
      try {
        await api(`/market/listings/${el.dataset.offer}/offers`, {
          method: "POST",
          json: {
            money_offer: result.money ? Number(result.money) : null,
            cards_offer: result.cardsOffer || null,
          },
        });
        showToast("Oferta enviada");
      } catch (e) {
        showToast(e.message);
      }
    });
  });
}

function bindEvents() {
  document.getElementById("btn-scan-hero")?.addEventListener("click", () => {
    state.screen = "scan";
    state.scanPhase = "idle";
    render();
  });

  document.getElementById("btn-open-search")?.addEventListener("click", async () => {
    state.scanPhase = "search";
    state.scanSearchQuery = "";
    render();
    if (!state.catalogSets) await loadCatalogSets();
    render();
  });

  document.getElementById("btn-search-back")?.addEventListener("click", () => {
    state.scanPhase = "idle";
    render();
  });

  document.getElementById("scan-search-set")?.addEventListener("change", async (e) => {
    const setId = e.target.value;
    state.scanSearchSetId = setId || null;
    state.scanSearchQuery = "";
    state.scanSearchCards = null;
    if (!setId) { render(); return; }
    state.scanSearchLoading = true;
    render();
    try {
      state.scanSearchCards = await api(`/cards?set_id=${encodeURIComponent(setId)}`);
    } catch {
      state.scanSearchCards = [];
    }
    state.scanSearchLoading = false;
    render();
  });

  document.getElementById("scan-search-input")?.addEventListener("input", (e) => {
    state.scanSearchQuery = e.target.value;
    const query = state.scanSearchQuery.toLowerCase();
    const filtered = (state.scanSearchCards || []).filter(
      (c) => !query || c.name.toLowerCase().includes(query) || c.rarity.toLowerCase().includes(query)
    );
    const list = document.getElementById("scan-search-list");
    if (!list) return;
    list.innerHTML = filtered.length
      ? filtered.map(scanItemHtml).join("")
      : '<li class="empty-state">Sin resultados. Probá otro nombre.</li>';
    list.querySelectorAll(".scan-item[data-card-id]").forEach((el) => {
      el.addEventListener("click", () => openCardDetail(el.dataset.cardId));
    });
    refreshIcons();
  });

  document.getElementById("scan-search-list")?.querySelectorAll(".scan-item[data-card-id]").forEach((el) => {
    el.addEventListener("click", () => openCardDetail(el.dataset.cardId));
  });

  document.getElementById("btn-run-scan")?.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      state.cameraStream = stream;
      state.scanPhase = "camera";
      render();
      const video = document.getElementById("scan-video");
      if (video) video.srcObject = stream;
    } catch {
      showToast("No se pudo acceder a la cámara");
    }
  });

  document.getElementById("btn-capture")?.addEventListener("click", () => {
    const video = document.getElementById("scan-video");
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    stopCameraStream();
    canvas.toBlob((blob) => {
      const file = new File([blob], "capture.jpg", { type: "image/jpeg" });
      state.selectedFile = file;
      if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
      state.previewUrl = URL.createObjectURL(blob);
      runScan();
    }, "image/jpeg");
  });

  document.getElementById("btn-cancel-camera")?.addEventListener("click", () => {
    stopCameraStream();
    state.scanPhase = "idle";
    render();
  });

  document.getElementById("btn-upload-image")?.addEventListener("click", () => {
    document.getElementById("scan-file-gallery")?.click();
  });

  document.getElementById("scan-file-gallery")?.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    state.selectedFile = file;
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = URL.createObjectURL(file);
    runScan();
  });

  document.getElementById("btn-save")?.addEventListener("click", async () => {
    if (!(await requireAuth("guardar"))) return;
    try {
      await api(`/collection/${state.activeCard.id}`, { method: "POST" });
      showToast("Carta guardada en tu colección");
      await loadCollection();
      state.scanPhase = "idle";
      state.activeCard = null;
      state.scanMethod = null;
      render();
    } catch (e) {
      showToast(e.message);
    }
  });

  document.getElementById("btn-publish")?.addEventListener("click", async () => {
    if (!(await requireAuth("publicar"))) return;
    const result = await openModal({
      title: "Publicar carta",
      confirmLabel: "Publicar",
      fields: [
        {
          name: "type",
          label: "Tipo de publicación",
          type: "select",
          value: "sale",
          options: [
            { value: "sale", label: "Venta" },
            { value: "trade", label: "Intercambio" },
            { value: "negotiable", label: "Negociable" },
            { value: "combo", label: "Combo" },
          ],
        },
        {
          name: "wants",
          label: "Cartas que buscás a cambio",
          type: "text",
          placeholder: "Opcional · solo para intercambio o combo",
        },
      ],
    });
    if (!result) return;
    try {
      const wants = result.type === "trade" || result.type === "combo" ? result.wants || null : null;
      await api("/market/listings", {
        method: "POST",
        json: {
          card_id: state.activeCard.id,
          listing_type: result.type,
          price: state.activeCard.price,
          wants,
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

  document.getElementById("btn-edit-profile")?.addEventListener("click", async () => {
    const user = getUser();
    const result = await openModal({
      title: "Datos personales",
      confirmLabel: "Guardar",
      fields: [
        { name: "first_name", label: "Nombre", type: "text", placeholder: "Opcional", value: user?.first_name || "" },
        { name: "last_name", label: "Apellido", type: "text", placeholder: "Opcional", value: user?.last_name || "" },
        { name: "dni", label: "DNI", type: "text", placeholder: "Requerido para torneos", required: true, value: user?.dni || "" },
      ],
    });
    if (!result) return;
    try {
      const updated = await api("/users/me", {
        method: "PATCH",
        json: { first_name: result.first_name || null, last_name: result.last_name || null, dni: result.dni || null },
      });
      setAuth(getToken(), updated);
      showToast("Datos guardados");
      render();
    } catch (e) {
      showToast(e.message);
    }
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
      openNotifyWs();
      showToast(`Hola, ${data.user.username}`);
      await loadStats();
      await loadCollection();
      if (state.pendingScanCard) {
        const card = state.pendingScanCard;
        state.pendingScanCard = null;
        try {
          await api(`/collection/${card.id}`, { method: "POST" });
          showToast(`"${card.name}" guardada en tu colección`);
          await loadCollection();
        } catch {}
        if (!state.recentScans.find((c) => c.id === card.id)) state.recentScans.unshift(card);
        state.screen = "scan";
        state.activeCard = card;
        state.scanPhase = "result";
        state.scanMethod = card.scanMethod || null;
      }
      render();
    } catch (err) {
      showToast(err.message);
    }
  });

  document.querySelectorAll("[data-go]").forEach((el) => {
    el.addEventListener("click", () => navigate(el.dataset.go));
  });

  document.querySelectorAll(".scan-item[data-card-id]").forEach((el) => {
    el.addEventListener("click", () => openCardDetail(el.dataset.cardId));
  });

  document.getElementById("catalog-set-select")?.addEventListener("change", async (e) => {
    state.catalogSetId = e.target.value;
    state.catalogLoading = true;
    render();
    await loadCatalogCards(state.catalogSetId);
    if (state.screen === "catalog") render();
  });

  document.getElementById("catalog-search")?.addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    const filtered = (state.catalogCards || []).filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.set_name.toLowerCase().includes(q) ||
        c.rarity.toLowerCase().includes(q)
    );
    const list = document.getElementById("catalog-list");
    if (!list) return;
    list.innerHTML = catalogListHtml(filtered);
    list.querySelectorAll(".scan-item[data-card-id]").forEach((el) => {
      el.addEventListener("click", () => openCardDetail(el.dataset.cardId));
    });
    refreshIcons();
  });

  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", async () => {
      const screen = el.dataset.nav;
      if (screen === "market" && totalUnread() > 0) {
        state.marketView = "mychats";
        try { state.myChats = await api("/messages/mine"); } catch { state.myChats = []; }
      }
      await navigate(screen);
    });
  });

  document.querySelectorAll("[data-tournaments-view]").forEach((el) => {
    el.addEventListener("click", async () => {
      state.tournamentsView = el.dataset.tournamentsView;
      state.tournamentQuery = "";
      if (state.tournamentsView === "mine" && !state.myTournaments) {
        await loadMyTournaments();
      }
      render();
    });
  });

  document.querySelectorAll("[data-tournaments-user-view]").forEach((el) => {
    el.addEventListener("click", () => {
      state.tournamentsUserView = el.dataset.tournamentsUserView;
      state.tournamentQuery = "";
      render();
    });
  });

  document.getElementById("tournament-search")?.addEventListener("input", (e) => {
    state.tournamentQuery = e.target.value.trim();
    render();
  });

  document.querySelectorAll("[data-market-view]").forEach((el) => {
    el.addEventListener("click", async () => {
      state.marketView = el.dataset.marketView;
      if (state.marketView === "mychats") {
        try {
          state.myChats = await api("/messages/mine");
        } catch {
          state.myChats = [];
        }
      }
      render();
    });
  });

  document.querySelectorAll("[data-open-chat]").forEach((el) => {
    el.addEventListener("click", async () => {
      const listingId = Number(el.dataset.openChat);
      const fakeListing = {
        id: listingId,
        card: { name: el.dataset.chatCard },
        seller_id: Number(el.dataset.chatSellerId),
        seller_username: el.dataset.chatSeller,
        listing_type: el.dataset.chatType,
      };
      await openChat(listingId, fakeListing);
    });
  });

  bindMarketCardEvents();

  document.getElementById("market-search")?.addEventListener("input", (e) => {
    state.marketQuery = e.target.value.trim();
    const grid = document.getElementById("market-grid");
    if (!grid) return;
    const filtered = filterMarketListings();
    grid.innerHTML = filtered.length
      ? filtered.map(marketCardHtml).join("")
      : `<div class="empty-state"><div class="empty-icon"></div><p>No hay publicaciones que coincidan.</p></div>`;
    bindMarketCardEvents();
    refreshIcons();
  });

  document.getElementById("market-type-filter")?.addEventListener("change", (e) => {
    state.marketTypeFilter = e.target.value;
    const grid = document.getElementById("market-grid");
    if (!grid) return;
    const filtered = filterMarketListings();
    grid.innerHTML = filtered.length
      ? filtered.map(marketCardHtml).join("")
      : `<div class="empty-state"><div class="empty-icon"></div><p>No hay publicaciones que coincidan.</p></div>`;
    bindMarketCardEvents();
    refreshIcons();
  });

  document.querySelectorAll("[data-action]").forEach((el) => {
    el.addEventListener("click", async () => {
      const action = el.dataset.action;
      if (action === "publish-tournament") {
        const result = await openModal({
          title: "Publicar torneo",
          confirmLabel: "Publicar",
          fields: [
            { name: "title", label: "Nombre del torneo", type: "text", required: true },
            { name: "description", label: "Descripción", type: "textarea", placeholder: "Opcional" },
            { name: "event_date", label: "Fecha del evento", type: "date", min: new Date().toISOString().slice(0, 10) },
            { name: "location", label: "Lugar", type: "text", placeholder: "Opcional" },
            { name: "max_participants", label: "Cupo máximo (opcional)", type: "number", placeholder: "Sin límite" },
          ],
        });
        if (!result) return;
        try {
          await api("/tournaments", {
            method: "POST",
            json: {
              title: result.title,
              description: result.description || null,
              event_date: result.event_date || null,
              location: result.location || null,
              max_participants: result.max_participants ? Number(result.max_participants) : null,
            },
          });
          showToast("¡Torneo publicado! Ya aparece en la pestaña Torneos para todos los usuarios.");
          state.tournamentsView = "mine";
          await navigate("torneos");
        } catch (e) {
          showToast(e.message);
        }
        return;
      }
      const labels = {
        alerts: "Alertas de precio: configurá notificaciones desde la app móvil",
        deck: "Análisis de mazo: próximamente disponible",
      };
      showToast(labels[action] || "Próximamente");
    });
  });

  document.querySelectorAll("[data-tournament-detail]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const id = Number(el.dataset.tournamentDetail);
      const t = (state.myTournaments || []).find((x) => x.id === id);
      if (!t) return;
      let registrantsHtml = "<p style='color:var(--text-muted);font-size:0.88rem'>Cargando inscriptos…</p>";

      // Crear overlay del modal manualmente para poder actualizar contenido
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      const cupo = t.max_participants ? `${t.participants_count}/${t.max_participants}` : `${t.participants_count}`;
      overlay.innerHTML = `
        <div class="modal-card" role="dialog" style="max-width:480px;max-height:80vh;overflow-y:auto">
          <h3 class="modal-title">${t.title}</h3>
          ${t.event_date ? `<p style="font-size:0.85rem;color:var(--text-muted);margin:0 0 0.25rem">${icon("calendar","icon-inline")} ${t.event_date}</p>` : ""}
          ${t.location ? `<p style="font-size:0.85rem;color:var(--text-muted);margin:0 0 0.25rem">${icon("map-pin","icon-inline")} ${t.location}</p>` : ""}
          ${t.description ? `<p style="font-size:0.85rem;margin:0.5rem 0">${t.description}</p>` : ""}
          <p style="font-size:0.85rem;margin:0.5rem 0">${icon("users","icon-inline")} <strong>${cupo}</strong> inscripto${t.participants_count !== 1 ? "s" : ""}</p>
          <hr style="border-color:var(--border);margin:0.75rem 0" />
          <div id="modal-registrants">${registrantsHtml}</div>
          <div class="modal-actions" style="margin-top:1rem">
            <button type="button" class="btn btn-primary" data-modal-close>Cerrar</button>
          </div>
        </div>`;
      document.body.appendChild(overlay);
      overlay.querySelector("[data-modal-close]").addEventListener("click", () => overlay.remove());
      overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });

      try {
        const regs = await api(`/tournaments/${id}/registrations`);
        const div = overlay.querySelector("#modal-registrants");
        if (!regs.length) {
          div.innerHTML = "<p style='color:var(--text-muted);font-size:0.88rem'>Nadie inscripto todavía.</p>";
        } else {
          div.innerHTML = `<ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:0.5rem">
            ${regs.map((r) => `
              <li style="background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:0.6rem 0.75rem;font-size:0.85rem">
                <strong>${r.username}</strong>${r.first_name || r.last_name ? ` — ${[r.first_name, r.last_name].filter(Boolean).join(" ")}` : ""}
                <br><span style="color:var(--text-muted)">DNI: ${r.dni_used || "no informado"}</span>
              </li>`).join("")}
          </ul>`;
        }
        refreshIcons();
      } catch (e) {
        overlay.querySelector("#modal-registrants").innerHTML = `<p style="color:#f87171;font-size:0.88rem">${e.message}</p>`;
      }
    });
  });

  document.querySelectorAll("[data-register-tournament]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!(await requireAuth("inscribirte"))) return;
      const user = getUser();
      let dni = user?.dni || "";
      let firstName = user?.first_name || "";
      let lastName = user?.last_name || "";
      let saveToProfile = false;

      if (!dni) {
        const result = await openModal({
          title: "Datos para la inscripción",
          confirmLabel: "Inscribirme",
          fields: [
            { name: "_info", label: "Tu DNI es requerido para completar la inscripción.", type: "info" },
            { name: "first_name", label: "Nombre", type: "text", placeholder: "Opcional", value: firstName },
            { name: "last_name", label: "Apellido", type: "text", placeholder: "Opcional", value: lastName },
            { name: "dni", label: "DNI", type: "text", required: true, placeholder: "Ej: 12345678" },
            { name: "save_to_profile", label: "Guardar en mi perfil para los próximos torneos", type: "checkbox", checked: true },
          ],
        });
        if (!result) return;
        dni = result.dni;
        firstName = result.first_name || "";
        lastName = result.last_name || "";
        saveToProfile = result.save_to_profile;
      }

      try {
        await api(`/tournaments/${el.dataset.registerTournament}/register`, {
          method: "POST",
          json: { dni, first_name: firstName || null, last_name: lastName || null, save_to_profile: saveToProfile },
        });
        if (saveToProfile) {
          const updated = await api("/users/me");
          setAuth(getToken(), updated);
        }
        showToast("¡Inscripción confirmada!");
        await loadTorneos();
        render();
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  document.querySelectorAll("[data-unregister-tournament]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const confirmed = await openModal({
        title: "¿Desanotarte del torneo?",
        confirmLabel: "Sí, desanotarme",
        cancelLabel: "Cancelar",
        fields: [
          { name: "_info", label: "Tu plaza quedará libre y otro jugador podrá ocuparla. Esta acción no se puede deshacer.", type: "info" },
        ],
      });
      if (!confirmed) return;
      try {
        await api(`/tournaments/${el.dataset.unregisterTournament}/register`, { method: "DELETE" });
        showToast("Te desanotaste del torneo");
        await loadTorneos();
        render();
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  document.querySelectorAll("[data-cancel-tournament]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const id = Number(el.dataset.cancelTournament);
      const result = await openModal({
        title: "Cancelar torneo",
        confirmLabel: "Confirmar cancelación",
        fields: [
          { name: "reason", label: "Motivo de cancelación", type: "text", required: true, placeholder: "Ej: falta de inscriptos, problema de local..." },
        ],
      });
      if (!result) return;
      try {
        await api(`/tournaments/${id}/cancel`, { method: "POST", json: { reason: result.reason } });
        showToast("Torneo cancelado");
        await navigate("torneos");
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  document.querySelectorAll("[data-edit-tournament]").forEach((el) => {
    el.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const id = Number(el.dataset.editTournament);
      const t = (state.myTournaments || []).find((x) => x.id === id);
      if (!t) return;
      const result = await openModal({
        title: "Editar torneo",
        confirmLabel: "Guardar",
        fields: [
          { name: "title", label: "Nombre del torneo", type: "text", required: true, value: t.title },
          { name: "description", label: "Descripción", type: "textarea", placeholder: "Opcional", value: t.description || "" },
          { name: "event_date", label: "Fecha del evento", type: "date", value: t.event_date || "", min: new Date().toISOString().slice(0, 10) },
          { name: "location", label: "Lugar", type: "text", placeholder: "Opcional", value: t.location || "" },
          { name: "max_participants", label: "Cupo máximo (opcional)", type: "number", placeholder: "Sin límite", value: t.max_participants || "" },
        ],
      });
      if (!result) return;
      try {
        await api(`/tournaments/${id}`, {
          method: "PATCH",
          json: {
            title: result.title || undefined,
            description: result.description || null,
            event_date: result.event_date || null,
            location: result.location || null,
            max_participants: result.max_participants ? Number(result.max_participants) : null,
          },
        });
        showToast("Torneo actualizado");
        await navigate("torneos");
      } catch (e) {
        showToast(e.message);
      }
    });
  });

  // Chat screen: WebSocket connection + send events
  if (state.screen === "chat" && state.chatListingId && isLoggedIn()) {
    if (!state.chatWs || state.chatWs.readyState > 1) {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const ws = new WebSocket(
        `${proto}://${location.host}/ws/chat/${state.chatListingId}?token=${encodeURIComponent(getToken())}`
      );
      state.chatWs = ws;
      ws.onmessage = (ev) => {
        const msg = JSON.parse(ev.data);
        if (!state.chatMessages.find((m) => m.id === msg.id)) {
          state.chatMessages.push(msg);
        }
        const container = document.getElementById("chat-messages");
        if (container) {
          const me = getUser();
          const isMe = me && msg.sender_id === me.id;
          const time = new Date(msg.created_at).toLocaleTimeString("es-AR", {
            hour: "2-digit",
            minute: "2-digit",
          });
          const div = document.createElement("div");
          div.className = `chat-msg ${isMe ? "chat-msg-me" : "chat-msg-other"}`;
          div.innerHTML = `
            ${!isMe ? `<div class="chat-sender">${escapeHtml(msg.sender_username)}</div>` : ""}
            <div class="chat-bubble">${escapeHtml(msg.content)}</div>
            <div class="chat-time">${time}</div>
          `;
          // Remove empty state if present
          const empty = container.querySelector(".chat-empty");
          if (empty) empty.remove();
          container.appendChild(div);
          container.scrollTop = container.scrollHeight;
        }
      };
      ws.onerror = () => showToast("Error de conexión al chat");
    }

    const chatInput = document.getElementById("chat-input");
    const chatSend = document.getElementById("chat-send");
    const container = document.getElementById("chat-messages");
    if (container) container.scrollTop = container.scrollHeight;

    function sendChatMsg() {
      const content = chatInput?.value?.trim();
      if (!content || !state.chatWs || state.chatWs.readyState !== 1) return;
      state.chatWs.send(JSON.stringify({ content }));
      if (chatInput) chatInput.value = "";
    }
    chatSend?.addEventListener("click", sendChatMsg);
    chatInput?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendChatMsg();
    });
  }
}

(async function init() {
  await loadHomeData();
  openNotifyWs(); // reconnect notify WS if already logged in (page refresh)
  render();

  // Precarga el set por defecto del catálogo en segundo plano, para que el
  // buscador de Escanear tenga datos sin obligar a pasar por la pestaña Catálogo.
  loadCatalogSets()
    .then(() => {
      if (state.catalogSetId && state.catalogCardsSetId !== state.catalogSetId) {
        return loadCatalogCards(state.catalogSetId);
      }
    })
    .then(() => {
      if (state.screen === "scan" || state.screen === "catalog") render();
    })
    .catch(() => {});
})();
