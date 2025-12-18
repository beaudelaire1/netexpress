(() => {
  const qs = (sel, el = document) => el.querySelector(sel);
  const qsa = (sel, el = document) => Array.from(el.querySelectorAll(sel));

  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ------------------------------------------------------------------
  // Gallery filters + lightbox
  // ------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    const gallery = qs("#gallery");
    const lightbox = qs("#lightbox");
    if (!gallery) return;

    const items = qsa(".gallery-item", gallery);
    const filterButtons = qsa(".filter-btn");
    const lightboxImg = lightbox ? qs("img", lightbox) : null;
    const caption = lightbox ? qs(".caption", lightbox) : null;

    // Helper: animate in
    const reveal = () => {
      if (prefersReduced) return;
      items.forEach((it, i) => {
        it.style.opacity = "0";
        it.style.transform = "translateY(14px)";
        it.style.transition = "opacity 520ms ease, transform 520ms ease";
        it.style.transitionDelay = `${Math.min(i * 35, 260)}ms`;
        requestAnimationFrame(() => {
          it.style.opacity = "1";
          it.style.transform = "translateY(0)";
        });
      });
    };

    // Filter
    const applyFilter = (category) => {
      const normalized = (category || "all").toLowerCase();
      items.forEach((it) => {
        const itCat = (it.getAttribute("data-category") || "all").toLowerCase();
        const show = normalized === "all" || itCat === normalized;
        it.style.display = show ? "" : "none";
      });
      // reset transitions for visible items
      reveal();
    };

    if (filterButtons.length) {
      filterButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
          filterButtons.forEach((b) => b.classList.remove("active"));
          btn.classList.add("active");
          applyFilter(btn.getAttribute("data-category"));
        });
      });
    }

    // Lightbox
    if (lightbox && lightboxImg) {
      items.forEach((item) => {
        item.addEventListener("click", () => {
          const img = qs("img", item);
          const title = qs(".title", item);
          if (!img) return;

          lightboxImg.src = img.src;
          if (caption) caption.textContent = title ? title.textContent : "";
          lightbox.setAttribute("aria-hidden", "false");
          lightbox.style.display = "flex";
          document.body.style.overflow = "hidden";
        });
      });

      const close = () => {
        lightbox.style.display = "none";
        lightbox.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
      };

      lightbox.addEventListener("click", close);
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && lightbox.style.display === "flex") close();
      });
    }

    // First paint
    applyFilter(qs(".filter-btn.active")?.getAttribute("data-category") || "all");

    // ------------------------------------------------------------------
    // Premium micro-interactions (subtle tilt + sheen)
    // ------------------------------------------------------------------
    if (!prefersReduced) {
      items.forEach((card) => {
        card.style.willChange = "transform";
        card.addEventListener("mousemove", (e) => {
          const r = card.getBoundingClientRect();
          const px = (e.clientX - r.left) / r.width - 0.5;
          const py = (e.clientY - r.top) / r.height - 0.5;
          const rx = (-py * 4).toFixed(2);
          const ry = (px * 6).toFixed(2);
          card.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-2px)`;
        });

        card.addEventListener("mouseleave", () => {
          card.style.transform = "";
        });
      });
    }
  });
})();
