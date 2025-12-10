// Micro‑animations pour les champs de formulaire NetExpress
// Accentue l'effet de glow lorsque l'utilisateur se concentre
// sur un champ sans tomber dans un style "gamer".

(function () {
  const fields = document.querySelectorAll('.devis-form .input,\
                                      .devis-form .textarea,\
                                      .form-card input,\
                                      .form-card textarea,\
                                      .form-card select,\
                                      .hero-input');

  fields.forEach((el) => {
    el.addEventListener('focus', () => {
      el.style.boxShadow = '0 0 12px rgba(11,93,70,0.35)';
    });
    el.addEventListener('blur', () => {
      el.style.boxShadow = '0 2px 8px rgba(0,0,0,0.05)';
    });
  });
})();
