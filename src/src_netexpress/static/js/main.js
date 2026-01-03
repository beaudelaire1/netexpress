/*
  Script utilitaire (2025) :
  Gere le defilement doux vers les ancres internes et ignore les clics
  sur les liens qui ne correspondent pas a un ID valide.  Ce fichier
  peut etre etendu pour ajouter d'autres interactions (par exemple, un
  menu mobile ou la gestion d'affichage de messages flash).
*/

// Smooth scroll for internal anchors
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[href^="#"]');
  if (!a) return;
  const id = a.getAttribute('href').slice(1);
  if (!id) return;
  const el = document.getElementById(id);
  if (el) {
    e.preventDefault();
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});

// Gestion du menu mobile hamburger
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('primary-navigation');
  
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', (!expanded).toString());
      // Toggle classe 'open' pour CSS + attribut hidden pour accessibilite
      nav.classList.toggle('open');
      nav.hidden = !nav.classList.contains('open');
    });
  }

  // ------------------------------------------------------------------
  // Tabs (Home - Expertises)
  // ------------------------------------------------------------------
  const tabButtons = document.querySelectorAll('.tabs-header .tab-btn[data-tab-target]');
  const tabPanels = document.querySelectorAll('.tab-content');
  if (tabButtons.length && tabPanels.length) {
    const activate = (btn) => {
      const targetSel = btn.getAttribute('data-tab-target');
      const target = targetSel ? document.querySelector(targetSel) : null;
      if (!target) return;

      tabButtons.forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      tabPanels.forEach(p => {
        p.classList.remove('active');
        p.setAttribute('hidden', '');
      });

      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      target.classList.add('active');
      target.removeAttribute('hidden');
    };

    tabButtons.forEach(btn => btn.addEventListener('click', () => activate(btn)));
  }

  // ------------------------------------------------------------------
  // Service selector (Home - devis rapide)
  // ------------------------------------------------------------------
  const selector = document.querySelector('[data-service-selector]');
  const hiddenSelect = document.getElementById('qq_service_type');
  if (selector && hiddenSelect) {
    const opts = selector.querySelectorAll('.option[data-service-value]');
    opts.forEach(opt => {
      opt.addEventListener('click', () => {
        opts.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        const val = opt.getAttribute('data-service-value');
        if (val) hiddenSelect.value = val;
      });
    });
  }

  // ------------------------------------------------------------------
  // Range sliders (surface)
  // ------------------------------------------------------------------
  const ranges = document.querySelectorAll('input[type="range"][data-range-output]');
  ranges.forEach(range => {
    const outSel = range.getAttribute('data-range-output');
    const output = outSel ? document.querySelector(outSel) : null;
    const hiddenSel = range.getAttribute('data-range-hidden');
    const hidden = hiddenSel ? document.querySelector(hiddenSel) : null;
    const suffix = range.getAttribute('data-range-suffix') || ' m2';

    if (hidden && hidden.value) {
      range.value = hidden.value;
    }

    const update = () => {
      if (!output) return;
      output.textContent = range.value + suffix;
      if (hidden) hidden.value = range.value;
    };
    range.addEventListener('input', update);
    update();
  });

  // ------------------------------------------------------------------
  // Realisations: filtre + lightbox (page /realisations/)
  // ------------------------------------------------------------------
  const gallery = document.getElementById('gallery');
  const lightbox = document.getElementById('lightbox');
  if (gallery && lightbox) {
    const buttons = document.querySelectorAll('.filter-btn[data-category]');
    const items = gallery.querySelectorAll('.gallery-item[data-category]');
    const lightboxImg = lightbox.querySelector('img');
    const caption = lightbox.querySelector('.caption');

    buttons.forEach(btn => {
      btn.addEventListener('click', () => {
        buttons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.getAttribute('data-category');
        items.forEach(item => {
          const itemCat = item.getAttribute('data-category');
          item.style.display = (!cat || cat === 'all' || itemCat === cat) ? '' : 'none';
        });
      });
    });

    items.forEach(item => {
      item.addEventListener('click', () => {
        const img = item.querySelector('img');
        const titleEl = item.querySelector('.title');
        if (!img || !lightboxImg) return;
        lightboxImg.src = img.getAttribute('src') || '';
        if (caption && titleEl) caption.textContent = titleEl.textContent || '';
        lightbox.style.display = 'flex';
      });
    });
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) lightbox.style.display = 'none';
    });
  }
});

// --- CSRF helpers (Django) ---
function getCookie(name) {
  const value = '; ' + document.cookie;
  const parts = value.split('; ' + name + '=');
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}

// Wrapper fetch qui ajoute automatiquement le token CSRF pour les requetes mutables
async function safeFetch(url, options = {}) {
  const opts = { credentials: "same-origin", ...options };
  const method = (opts.method || "GET").toUpperCase();
  const needsCsrf = !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method);

  if (needsCsrf) {
    const csrftoken = getCookie("csrftoken");
    opts.headers = { ...(opts.headers || {}), "X-CSRFToken": csrftoken };
  }
  return fetch(url, opts);
}

window.safeFetch = safeFetch;
