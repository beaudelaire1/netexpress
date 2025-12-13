/*
  Script utilitaire (2025) :
  Gère le défilement doux vers les ancres internes et ignore les clics
  sur les liens qui ne correspondent pas à un ID valide.  Ce fichier
  peut être étendu pour ajouter d’autres interactions (par exemple, un
  menu mobile ou la gestion d’affichage de messages flash).
*/

// Smooth scroll for internal anchors
// Défilement doux pour les ancres internes
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

// Gestion du menu mobile : afficher/masquer la navigation lorsqu'on clique
// sur le bouton burger (voir base.html et base.css).  On attend que le DOM
// soit prêt pour garantir que les éléments existent.
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('primary-navigation');
  if (toggle && nav) {
    // Initialise the hidden state based on aria‑expanded
    const updateState = () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      nav.hidden = !expanded;
    };
    updateState();
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', (!expanded).toString());
      updateState();
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
    const suffix = range.getAttribute('data-range-suffix') || ' m²';

    // Si un champ caché est présent et déjà pré-rempli (ex: via initial Django),
    // on synchronise le slider au chargement.
    if (hidden && hidden.value) {
      range.value = hidden.value;
    }

    const update = () => {
      if (!output) return;
      output.textContent = `${range.value}${suffix}`;
      if (hidden) hidden.value = range.value;
    };
    range.addEventListener('input', update);
    update();
  });

  // ------------------------------------------------------------------
  // Réalisations: filtre + lightbox (page /realisations/)
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