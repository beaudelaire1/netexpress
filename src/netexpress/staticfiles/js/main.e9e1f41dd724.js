/*
  Script utilitaire (2025) :
  Gère le défilement doux vers les ancres internes et ignore les clics
  sur les liens qui ne correspondent pas à un ID valide.  Ce fichier
  peut être étendu pour ajouter d’autres interactions (par exemple, un
  menu mobile ou la gestion d’affichage de messages flash).
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