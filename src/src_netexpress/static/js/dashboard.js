(() => {
  const qsa = (sel, el=document) => Array.from(el.querySelectorAll(sel));
  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  document.addEventListener("DOMContentLoaded", () => {
    // Active link in sidebar
    const current = window.location.pathname;
    qsa(".sidebar-nav a").forEach(a => {
      try{
        const href = a.getAttribute("href") || "";
        if (href && current.startsWith(href) && href !== "/") a.classList.add("is-active");
      }catch(_){}
    });

    // Cards reveal
    if (prefersReduced) return;
    const cards = qsa(".dcard");
    if (!cards.length) return;

    const obs = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });

    cards.forEach(c => obs.observe(c));
  });
})();