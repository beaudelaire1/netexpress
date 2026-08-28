// Éditeur de lignes de devis NetExpress.
// Le DOM est construit à partir de formset.empty_form : aucun clonage de ligne
// existante, donc les identifiants Django et les index restent cohérents.

function parseNumber(value) {
  const normalized = String(value ?? "").replace(/\s/g, "").replace(",", ".");
  const number = Number(normalized);
  return Number.isFinite(number) ? number : 0;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
  }).format(value);
}

function field(row, suffix) {
  return row.querySelector(`[name$='-${suffix}']`);
}

function isDeleted(row) {
  const deleteInput = field(row, "DELETE");
  return Boolean(deleteInput && deleteInput.checked);
}

function recalcTotals() {
  let totalHt = 0;
  let totalTva = 0;

  document.querySelectorAll("tr.quote-item-row").forEach((row) => {
    if (isDeleted(row)) return;

    const quantityInput = field(row, "quantity");
    const unitPriceInput = field(row, "unit_price");
    const taxRateInput = field(row, "tax_rate");
    const lineTotalCell = row.querySelector(".cell-total-ht");
    if (!quantityInput || !unitPriceInput || !taxRateInput || !lineTotalCell) return;

    const quantity = parseNumber(quantityInput.value);
    const unitPrice = parseNumber(unitPriceInput.value);
    const taxRate = parseNumber(taxRateInput.value);
    const lineHt = quantity * unitPrice;
    const lineTva = lineHt * (taxRate / 100);

    totalHt += lineHt;
    totalTva += lineTva;
    lineTotalCell.textContent = formatCurrency(lineHt);
  });

  const ht = document.getElementById("total-ht-display");
  const tva = document.getElementById("total-tva-display");
  const ttc = document.getElementById("total-ttc-display");
  if (ht) ht.textContent = formatCurrency(totalHt);
  if (tva) tva.textContent = formatCurrency(totalTva);
  if (ttc) ttc.textContent = formatCurrency(totalHt + totalTva);
}

function showNotification(message, type = "warning") {
  if (window.NetExpress?.showNotification) {
    window.NetExpress.showNotification(message, type, 3000);
    return;
  }
  if (type === "error") console.error(message);
  else console.warn(message);
}

function attachServiceLookup(row) {
  const serviceSelect = field(row, "service");
  const descriptionInput = field(row, "description");
  if (!serviceSelect || !descriptionInput) return;

  serviceSelect.addEventListener("change", async () => {
    const serviceId = serviceSelect.value;
    if (!serviceId) return;

    const table = document.getElementById("quote-items-table");
    const baseUrl = table?.dataset.serviceInfoUrl;
    if (!baseUrl) return;

    const url = baseUrl.replace(/0\/?$/, `${serviceId}/`);
    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();

      if (!descriptionInput.value.trim()) {
        descriptionInput.value = data.title || data.description || "";
      }

      const taxInput = field(row, "tax_rate");
      if (taxInput && !String(taxInput.value).trim() && data.tax_rate !== "") {
        taxInput.value = data.tax_rate;
      }

      const unitInput = field(row, "unit_price");
      if (unitInput && !String(unitInput.value).trim() && data.base_price !== "") {
        unitInput.value = data.base_price;
      }
      recalcTotals();
    } catch (error) {
      console.warn("Chargement du service impossible", error);
      showNotification("Impossible de charger les informations du service.");
    }
  });
}

function attachRowEvents(row) {
  ["quantity", "unit_price", "tax_rate"].forEach((suffix) => {
    const input = field(row, suffix);
    if (!input) return;
    input.addEventListener("input", recalcTotals);
    input.addEventListener("change", recalcTotals);
  });

  const removeButton = row.querySelector(".js-remove-row");
  if (removeButton) {
    removeButton.addEventListener("click", () => {
      const deleteInput = field(row, "DELETE");
      if (deleteInput) deleteInput.checked = true;
      row.classList.add("is-deleted");
      recalcTotals();
    });
  }

  attachServiceLookup(row);
}

function addLine() {
  const totalFormsInput = document.querySelector("input[name$='-TOTAL_FORMS']");
  const maxFormsInput = document.querySelector("input[name$='-MAX_NUM_FORMS']");
  const template = document.getElementById("quote-item-empty-form");
  const tbody = document.getElementById("quote-items-body");
  if (!totalFormsInput || !template || !tbody) return;

  const index = parseInt(totalFormsInput.value, 10) || 0;
  const maxForms = maxFormsInput ? parseInt(maxFormsInput.value, 10) : 1000;
  if (Number.isFinite(maxForms) && index >= maxForms) {
    showNotification("Nombre maximal de prestations atteint.");
    return;
  }

  const html = template.innerHTML.replaceAll("__prefix__", String(index)).trim();
  const holder = document.createElement("tbody");
  holder.innerHTML = html;
  const row = holder.firstElementChild;
  if (!row) return;

  tbody.appendChild(row);
  totalFormsInput.value = String(index + 1);
  attachRowEvents(row);
  recalcTotals();

  const firstField = row.querySelector("select, input:not([type='hidden'])");
  firstField?.focus();
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("tr.quote-item-row").forEach(attachRowEvents);
  document.getElementById("add-line-btn")?.addEventListener("click", addLine);
  recalcTotals();
});

export {};
