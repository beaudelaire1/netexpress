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
  const nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      nav.classList.toggle('open');
    });
  }
});