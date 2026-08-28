const accountMenu = document.querySelector('.account-menu');
if (accountMenu) {
  document.addEventListener('click', (event) => {
    if (!accountMenu.contains(event.target)) accountMenu.open = false;
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && accountMenu.open) {
      accountMenu.open = false;
      accountMenu.querySelector('summary').focus();
    }
  });
}

document.querySelectorAll('[data-upload-form]').forEach((form) => {
  const input = form.querySelector('input[type="file"]');
  const status = form.querySelector('[data-file-selection]');
  const submit = form.querySelector('button[type="submit"]');
  if (input) input.addEventListener('change', () => {
    const file = input.files[0];
    const tooLarge = file && file.size > 10 * 1024 * 1024;
    input.setCustomValidity(tooLarge ? 'Le fichier doit faire 10 Mo maximum.' : '');
    if (status) {
      const size = file && file.size >= 1024 * 1024
        ? (file.size / 1024 / 1024).toLocaleString('fr-FR', {maximumFractionDigits: 2}) + ' Mo'
        : (file ? Math.ceil(file.size / 1024) : 0) + ' Ko';
      status.textContent = file ? file.name + ' · ' + size : '';
    }
  });
  form.addEventListener('invalid', (event) => {
    const details = event.target.closest('details');
    if (details) details.open = true;
  }, true);
  form.addEventListener('submit', () => {
    if (submit) { submit.disabled = true; submit.setAttribute('aria-busy', 'true'); }
  });
  window.addEventListener('pageshow', () => {
    if (submit) { submit.disabled = false; submit.removeAttribute('aria-busy'); }
  });
});
