(() => {
  'use strict';

  const formatBytes = (bytes) => {
    if (!Number.isFinite(bytes) || bytes <= 0) return '';
    if (bytes < 1024) return `${bytes} o`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
  };

  const syncFileZone = (zone, input) => {
    const selected = zone.querySelector('[data-file-selected]');
    const file = input.files && input.files[0];
    if (selected) {
      selected.textContent = file ? `${file.name} · ${formatBytes(file.size)}` : 'Aucun fichier sélectionné';
    }
    if (!file) return;

    const form = zone.closest('form');
    const titleInput = form && form.querySelector('input[name="document_title"]');
    if (titleInput && !titleInput.value.trim()) {
      titleInput.value = file.name.replace(/\.[^.]+$/, '').slice(0, 200);
    }
  };

  document.querySelectorAll('[data-upload-zone]').forEach((zone) => {
    const input = zone.querySelector('input[type="file"]');
    if (!input) return;

    zone.addEventListener('click', (event) => {
      if (event.target !== input) input.click();
    });
    zone.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        input.click();
      }
    });
    ['dragenter', 'dragover'].forEach((name) => {
      zone.addEventListener(name, (event) => {
        event.preventDefault();
        zone.classList.add('is-dragover');
      });
    });
    ['dragleave', 'drop'].forEach((name) => {
      zone.addEventListener(name, (event) => {
        event.preventDefault();
        zone.classList.remove('is-dragover');
      });
    });
    zone.addEventListener('drop', (event) => {
      if (!event.dataTransfer || !event.dataTransfer.files.length) return;
      const transfer = new DataTransfer();
      transfer.items.add(event.dataTransfer.files[0]);
      input.files = transfer.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    input.addEventListener('change', () => syncFileZone(zone, input));
    syncFileZone(zone, input);
  });

  document.querySelectorAll('[data-counter-for]').forEach((counter) => {
    const target = document.getElementById(counter.dataset.counterFor);
    if (!target) return;
    const max = Number(target.getAttribute('maxlength') || target.dataset.characterCounter || 4000);
    const update = () => {
      const length = target.value.length;
      counter.textContent = `${length} / ${max}`;
      counter.classList.toggle('is-near-limit', length > max * 0.9);
    };
    target.addEventListener('input', update);
    update();
  });
})();
