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

function accountingChartData() {
  const source = document.getElementById('accounting-financial-series');
  if (!source) return [];
  try {
    const parsed = JSON.parse(source.textContent || '[]');
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Données graphiques comptables invalides.', error);
    return [];
  }
}

function compactEuro(value) {
  const absolute = Math.abs(value);
  if (absolute >= 1000000) return (value / 1000000).toLocaleString('fr-FR', {maximumFractionDigits: 1}) + ' M€';
  if (absolute >= 1000) return (value / 1000).toLocaleString('fr-FR', {maximumFractionDigits: 1}) + ' k€';
  return value.toLocaleString('fr-FR', {maximumFractionDigits: 0}) + ' €';
}

function drawAccountingChart(canvas, data) {
  if (!canvas || !data.length) return;

  const primaryKey = canvas.dataset.primaryKey;
  const secondaryKey = canvas.dataset.secondaryKey;
  if (!primaryKey || !secondaryKey) return;

  const shell = canvas.closest('.chart-shell');
  if (shell) shell.classList.add('has-data');

  const css = getComputedStyle(document.documentElement);
  const primaryColor = css.getPropertyValue('--chart-primary').trim() || '#176a52';
  const secondaryColor = css.getPropertyValue('--chart-secondary').trim() || '#78a98f';
  const gridColor = css.getPropertyValue('--chart-grid').trim() || '#e4ebe6';
  const textColor = css.getPropertyValue('--chart-text').trim() || '#6b7b73';
  const zeroColor = css.getPropertyValue('--chart-zero').trim() || '#c4d0c8';

  const bounds = canvas.getBoundingClientRect();
  const cssWidth = Math.max(bounds.width, 320);
  const cssHeight = canvas.classList.contains('chart-small') ? 220 : 270;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(cssWidth * dpr);
  canvas.height = Math.round(cssHeight * dpr);
  canvas.style.height = cssHeight + 'px';

  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssWidth, cssHeight);

  const values = data.flatMap((row) => [Number(row[primaryKey]) || 0, Number(row[secondaryKey]) || 0]);
  let minValue = Math.min(0, ...values);
  let maxValue = Math.max(0, ...values);
  if (minValue === maxValue) maxValue = minValue + 1;
  const range = maxValue - minValue;

  const padding = {top: 14, right: 14, bottom: 42, left: 58};
  const plotWidth = cssWidth - padding.left - padding.right;
  const plotHeight = cssHeight - padding.top - padding.bottom;
  const yFor = (value) => padding.top + ((maxValue - value) / range) * plotHeight;
  const zeroY = yFor(0);

  ctx.font = '10px Inter, system-ui, sans-serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'right';

  const gridLines = 4;
  for (let i = 0; i <= gridLines; i += 1) {
    const value = maxValue - (range * i / gridLines);
    const y = padding.top + (plotHeight * i / gridLines);
    ctx.strokeStyle = Math.abs(value) < range / 1000 ? zeroColor : gridColor;
    ctx.lineWidth = Math.abs(value) < range / 1000 ? 1.2 : 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(cssWidth - padding.right, y);
    ctx.stroke();
    ctx.fillStyle = textColor;
    ctx.fillText(compactEuro(value), padding.left - 9, y);
  }

  const groupWidth = plotWidth / data.length;
  const barWidth = Math.max(4, Math.min(18, groupWidth * 0.28));
  const gap = Math.max(2, Math.min(5, groupWidth * 0.08));

  data.forEach((row, index) => {
    const center = padding.left + groupWidth * index + groupWidth / 2;
    const entries = [
      {value: Number(row[primaryKey]) || 0, color: primaryColor, x: center - barWidth - gap / 2},
      {value: Number(row[secondaryKey]) || 0, color: secondaryColor, x: center + gap / 2},
    ];

    entries.forEach(({value, color, x}) => {
      const valueY = yFor(value);
      const top = Math.min(valueY, zeroY);
      const height = Math.max(Math.abs(zeroY - valueY), value === 0 ? 1 : 2);
      ctx.fillStyle = color;
      ctx.fillRect(x, top, barWidth, height);
    });
  });

  const maxLabels = Math.max(3, Math.floor(plotWidth / 78));
  const labelStep = Math.max(1, Math.ceil(data.length / maxLabels));
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillStyle = textColor;
  data.forEach((row, index) => {
    if (index % labelStep !== 0 && index !== data.length - 1) return;
    const x = padding.left + groupWidth * index + groupWidth / 2;
    const label = String(row.label || '');
    ctx.fillText(label.length > 14 ? label.slice(0, 13) + '…' : label, x, cssHeight - padding.bottom + 13);
  });
}

const accountingCharts = Array.from(document.querySelectorAll('[data-accounting-chart]'));
if (accountingCharts.length) {
  const data = accountingChartData();
  const render = () => accountingCharts.forEach((canvas) => drawAccountingChart(canvas, data));
  render();

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(render, 120);
  });
}
