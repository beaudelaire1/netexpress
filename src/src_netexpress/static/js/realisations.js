document.addEventListener("DOMContentLoaded", () => {
  console.log("🎯 realisations.js chargé");

  const gallery = document.getElementById("gallery");
  const lightbox = document.getElementById("lightbox");

  if (!gallery || !lightbox) {
    console.warn("❌ Galerie ou lightbox absente");
    return;
  }

  const items = gallery.querySelectorAll(".gallery-item");
  const lightboxImg = lightbox.querySelector("img");
  const caption = lightbox.querySelector(".caption");

  // Filtres
  const buttons = document.querySelectorAll(".filter-btn[data-category]");
  buttons.forEach(btn => {
    btn.addEventListener("click", () => {
      buttons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const cat = btn.dataset.category;
      items.forEach(item => {
        item.style.display =
          cat === "all" || item.dataset.category === cat ? "" : "none";
      });
    });
  });

  // Lightbox
  items.forEach(item => {
    item.addEventListener("click", () => {
      const img = item.querySelector("img");
      const title = item.querySelector(".title");

      if (!img) return;

      lightboxImg.src = img.src;
      if (caption && title) caption.textContent = title.textContent;

      lightbox.style.display = "flex";
    });
  });

  lightbox.addEventListener("click", () => {
    lightbox.style.display = "none";
  });
});
