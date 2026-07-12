/**
 * TCG Trade — SPA móvil
 * Flujo: Inicio → Escanear → Resultado | Colección | Mercado | Perfil
 * Basado en wireframes y diagrama de lógica del proyecto.
 */

const CARDS = {
  luffy: {
    id: 'luffy',
    name: 'Monkey D. Luffy',
    game: 'One Piece',
    set: 'OP-01',
    code: 'OP-01-001',
    rarity: 'Super Rare',
    price: 4200,
    trend: 12,
    trendDir: 'up',
    history: [
      { label: 'may 1', value: 62 },
      { label: 'may 15', value: 78 },
      { label: 'jun 1', value: 85 },
      { label: 'hoy', value: 100, today: true },
    ],
  },
  zoro: {
    id: 'zoro',
    name: 'Zoro Promo',
    game: 'One Piece',
    set: 'OP-02',
    code: 'OP-02-P01',
    rarity: 'Promo',
    price: 8500,
    trend: -5,
    trendDir: 'down',
    history: [
      { label: 'may 1', value: 100 },
      { label: 'may 15', value: 92 },
      { label: 'jun 1', value: 88 },
      { label: 'hoy', value: 82, today: true },
    ],
  },
};

const NAV_ITEMS = [
  { id: 'home', label: 'Inicio', icon: '🏠' },
  { id: 'scan', label: 'Escanear', icon: '⊞' },
  { id: 'market', label: 'Mercado', icon: '🛍' },
  { id: 'profile', label: 'Perfil', icon: '👤' },
];

const MARKET_LISTINGS = [
  { cardId: 'luffy', seller: 'ColeccionAR', type: 'Venta', price: 4000, featured: true },
  { cardId: 'zoro', seller: 'TCG_BA', type: 'Intercambio', price: null, featured: false },
];

const state = {
  screen: 'home',
  scanPhase: 'idle',
  activeCard: null,
  recentScans: ['luffy', 'zoro'],
  collection: [],
  toastTimer: null,
};

const app = document.getElementById('app');
const bottomNav = document.getElementById('bottom-nav');

function formatPrice(n) {
  return n.toLocaleString('es-AR');
}

function trendHtml(card, asBadge = false) {
  const sign = card.trendDir === 'up' ? '↑' : card.trendDir === 'down' ? '↓' : '→';
  const text = `${sign} ${card.trend > 0 ? '+' : ''}${card.trend}%`;
  if (asBadge) {
    return `<span class="trend-badge ${card.trendDir}">${text}</span>`;
  }
  return `<span class="trend trend-${card.trendDir}">${text}</span>`;
}

function showToast(msg) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => toast.classList.remove('show'), 2500);
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
  const bars = history
    .map(
      (h) => `
      <div class="chart-bar-wrap">
        <div class="chart-bar ${h.today ? 'today' : ''}" style="height:${h.value}%"></div>
        <span class="chart-label">${h.label}</span>
      </div>`
    )
    .join('');
  return `
    <p class="chart-title">Últimos 30 días</p>
    <div class="chart-bars" role="img" aria-label="Gráfico de precio últimos 30 días">${bars}</div>
  `;
}

function scanItemHtml(cardId) {
  const c = CARDS[cardId];
  if (!c) return '';
  return `
    <li class="scan-item" data-card="${cardId}" role="button" tabindex="0" aria-label="${c.name}, ${formatPrice(c.price)} pesos">
      <div class="scan-thumb">🃏</div>
      <div class="scan-info">
        <div class="scan-name">${c.name}</div>
        <div class="scan-set">${c.game} - ${c.set}</div>
      </div>
      <div class="scan-price-col">
        <div class="scan-price">$${formatPrice(c.price)}</div>
        ${trendHtml(c)}
      </div>
    </li>
  `;
}

function renderHome() {
  const collectionCount = state.collection.length;
  return `
    ${logoHtml()}
    <button class="btn btn-primary btn-scan-hero" id="btn-scan-hero" aria-label="Escanear carta gratis sin registro">
      <span class="btn-icon">⊞</span>
      <span class="btn-title">Escanear carta</span>
      <span class="btn-sub">Gratis · sin registro</span>
    </button>
    <div class="tile-grid">
      <div class="tile" data-go="collection" role="button" tabindex="0">
        <span class="tile-icon">🃏</span>
        <div class="tile-title">Mi colección</div>
        <div class="tile-sub">${collectionCount || 32} cartas</div>
      </div>
      <div class="tile" data-go="market" role="button" tabindex="0">
        <span class="tile-icon">🛍</span>
        <div class="tile-title">Mercado</div>
        <div class="tile-sub">Ver ofertas</div>
      </div>
    </div>
    <p class="section-label">Últimos escaneos</p>
    <ul class="scan-list">
      ${state.recentScans.map(scanItemHtml).join('')}
    </ul>
  `;
}

function renderScanIdle() {
  return `
    <h2 class="page-title">Escanear carta</h2>
    <p class="page-sub">IA de visión · Gratis · Sin registro</p>
    <div class="viewfinder" id="viewfinder">
      <div class="viewfinder-corner tl"></div>
      <div class="viewfinder-corner tr"></div>
      <div class="viewfinder-corner bl"></div>
      <div class="viewfinder-corner br"></div>
      <div class="viewfinder-hint">
        <span class="hint-icon">📷</span>
        Apuntá la cámara a la carta
      </div>
    </div>
    <button class="btn btn-primary" id="btn-simulate-scan" style="width:100%;padding:1rem;border-radius:var(--radius-lg)">
      Simular escaneo
    </button>
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
        Carta identificada
      </div>
    </div>
    <div class="result-card">
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
  if (state.scanPhase === 'result' && state.activeCard) {
    return renderScanResult(CARDS[state.activeCard]);
  }
  if (state.scanPhase === 'scanning') {
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
  const items = state.collection.length
    ? state.collection.map((id) => scanItemHtml(id)).join('')
    : `<div class="empty-state">
        <div class="empty-icon">🃏</div>
        <p>Todavía no guardaste cartas.<br>Escaneá una y tocá <strong>Guardar</strong>.</p>
      </div>`;

  const totalValue = state.collection.reduce((sum, id) => sum + (CARDS[id]?.price || 0), 0);

  return `
    <h2 class="page-title">Mi colección</h2>
    <p class="page-sub">Historial · Valor total estimado</p>
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">${state.collection.length || 32}</div>
        <div class="stat-label">Cartas</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">$${formatPrice(totalValue || 12700)}</div>
        <div class="stat-label">Valor estimado</div>
      </div>
    </div>
    ${state.collection.length ? `<ul class="scan-list">${items}</ul>` : items}
  `;
}

function renderMarket() {
  const listings = MARKET_LISTINGS.map((l) => {
    const c = CARDS[l.cardId];
    const priceText = l.price ? `$${formatPrice(l.price)}` : 'Solo intercambio';
    return `
      <div class="market-card">
        <div class="scan-thumb">🃏</div>
        <div class="scan-info">
          <div class="scan-name">${c.name}</div>
          <div class="scan-set">${l.seller} · ${l.type}</div>
          ${l.featured ? '<span class="market-badge">Destacada</span>' : ''}
        </div>
        <div class="scan-price-col">
          <div class="scan-price">${priceText}</div>
        </div>
      </div>
    `;
  }).join('');

  return `
    <h2 class="page-title">Mercado</h2>
    <p class="page-sub">Reservas · Ofertas · Negociación</p>
    ${listings}
    <p class="page-sub" style="margin-top:1rem;font-size:0.75rem">
      Publicá cartas desde el resultado del escaneo con el botón <strong>Publicar</strong>.
    </p>
  `;
}

function renderProfile() {
  return `
    <h2 class="page-title">Perfil</h2>
    <p class="page-sub">Jugador / Coleccionista TCG</p>
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-value">${state.recentScans.length}</div>
        <div class="stat-label">Escaneos</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">${state.collection.length || 32}</div>
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
      <li class="menu-item" data-action="history">
        <div class="menu-icon">📜</div>
        <div class="menu-text">
          <div class="menu-title">Historial de escaneos</div>
          <div class="menu-desc">Todas tus consultas recientes</div>
        </div>
        <span class="menu-arrow">›</span>
      </li>
    </ul>
  `;
}

function renderNav() {
  bottomNav.innerHTML = NAV_ITEMS.map(
    (item) => `
    <button
      class="nav-item${state.screen === item.id ? ' active' : ''}"
      data-nav="${item.id}"
      aria-label="${item.label}"
      aria-current="${state.screen === item.id ? 'page' : 'false'}"
    >
      <span class="nav-icon">${item.icon}</span>
      <span>${item.label}</span>
    </button>`
  ).join('');
}

function render() {
  const screens = {
    home: renderHome,
    scan: renderScan,
    collection: renderCollection,
    market: renderMarket,
    profile: renderProfile,
  };

  const renderer = screens[state.screen] || renderHome;
  app.innerHTML = renderer();
  renderNav();
  bindEvents();
}

function navigate(screen) {
  if (screen === 'scan') {
    state.scanPhase = state.scanPhase === 'result' ? state.scanPhase : 'idle';
  } else if (screen !== 'scan') {
    state.scanPhase = 'idle';
    state.activeCard = null;
  }
  state.screen = screen;
  render();
}

function startScan(cardId = 'luffy') {
  state.scanPhase = 'scanning';
  state.activeCard = cardId;
  render();

  setTimeout(() => {
    state.scanPhase = 'result';
    if (!state.recentScans.includes(cardId)) {
      state.recentScans.unshift(cardId);
    }
    render();
  }, 1500);
}

function bindEvents() {
  document.getElementById('btn-scan-hero')?.addEventListener('click', () => {
    state.screen = 'scan';
    state.scanPhase = 'idle';
    render();
  });

  document.getElementById('btn-simulate-scan')?.addEventListener('click', () => startScan('luffy'));

  document.getElementById('btn-save')?.addEventListener('click', () => {
    if (state.activeCard && !state.collection.includes(state.activeCard)) {
      state.collection.push(state.activeCard);
      showToast('Carta guardada en tu colección');
    } else {
      showToast('Esta carta ya está en tu colección');
    }
  });

  document.getElementById('btn-publish')?.addEventListener('click', () => {
    showToast('Carta publicada en el mercado (simulado)');
    setTimeout(() => navigate('market'), 800);
  });

  document.getElementById('btn-new-scan')?.addEventListener('click', () => {
    state.scanPhase = 'idle';
    state.activeCard = null;
    render();
  });

  document.getElementById('btn-premium')?.addEventListener('click', () => {
    showToast('Premium: alertas, análisis de mazo e historial extendido');
  });

  document.querySelectorAll('[data-go]').forEach((el) => {
    el.addEventListener('click', () => navigate(el.dataset.go));
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        navigate(el.dataset.go);
      }
    });
  });

  document.querySelectorAll('.scan-item').forEach((el) => {
    const open = () => {
      state.screen = 'scan';
      startScan(el.dataset.card);
    };
    el.addEventListener('click', open);
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        open();
      }
    });
  });

  document.querySelectorAll('[data-nav]').forEach((el) => {
    el.addEventListener('click', () => navigate(el.dataset.nav));
  });

  document.querySelectorAll('[data-action]').forEach((el) => {
    el.addEventListener('click', () => {
      const labels = {
        alerts: 'Alertas de precio (función premium)',
        deck: 'Análisis de mazo: cartas que faltan y meta',
        tournaments: 'Torneos de tiendas asociadas',
        history: 'Historial de escaneos',
      };
      showToast(labels[el.dataset.action] || 'Próximamente');
    });
  });
}

render();
