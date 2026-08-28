// quote_admin.js — édition structurée des lignes de devis NetExpress.

function parseNumber(value) {
  const normalized = String(value || "").replace(/\s/g, "").replace(",", ".");
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

function rowIsDeleted(row) {
  const deleteField = row.querySelector("input[type='checkbox'][name$='-DELETE']");
  return Boolean(deleteField?.checked);
}

function recalcTotals() {
  const rows = document.querySelectorAll("tr.quote-item-row");
  let totalHt = 0;
  let totalTva = 0;

  rows.forEach((row) => {
    if (rowIsDeleted(row)) return;

    const qtyInput = row.querySelector(".js-quantity");
    const unitInput = row.querySelector(".js-unit-price");
    const taxInput = row.querySelector(".js-tax-rate");
    const cellTotalHt = row.querySelector(".cell-total-ht");

    if (!qtyInput || !unitInput || !taxInput || !cellTotalHt) return;

    const quantity = parseNumber(qtyInput.value);
    const unitPrice = parseNumber(unitInput.value);
    const taxRate = parseNumber(taxInput.value);
    const lineHt = quantity * unitPrice;
    const lineTva = lineHt * (taxRate / 100);

    totalHt += lineHt;
    totalTva += lineTva;
    cellTotalHt.textContent = formatCurrency(lineHt);
  });

  const totalTtc = totalHt + totalTva;
  const htDisplay = document.getElementById("total-ht-display");
  const tvaDisplay = document.getElementById("total-tva-display");
  const ttcDisplay = document.getElementById("total-ttc-display");

  if (htDisplay) htDisplay.textContent = formatCurrency(totalHt);
  if (tvaDisplay) tvaDisplay.textContent = formatCurrency(totalTva);
  if (ttcDisplay) ttcDisplay.textContent = formatCurrency(totalTtc);
}

function attachRowEvents(row) {
  const qtyInput = row.querySelector(".js-quantity");
  const unitInput = row.querySelector(".js-unit-price");
  const taxInput = row.querySelector(".js-tax-rate");
  const removeBtn = row.querySelector(".js-remove-row");
  const serviceSelect = row.querySelector(".js-service");
  const descriptionInput = row.querySelector(".js-description");

  [qtyInput, unitInput, taxInput].forEach((input) => {
    if (!input) return;
    input.addEventListener("input", recalcTotals);
    input.addEventListener("change", recalcTotals);
  });

  if (removeBtn) {
    removeBtn.addEventListener("click", () => {
      const deleteField = row.querySelector("input[type='checkbox'][name$='-DELETE']");
      if (deleteField) {
        deleteField.checked = true;
        row.hidden = true;
      } else {
        row.remove();
      }
      recalcTotals();
    });
  }

  if (serviceSelect && descriptionInput) {
    serviceSelect.addEventListener("change", () => {
      const serviceId = serviceSelect.value;
      if (!serviceId) return;

      const table = document.getElementById("quote-items-table");
      const baseUrl = table?.getAttribute("data-service-info-url");
      if (!baseUrl) return;

      const url = baseUrl.replace(/0\/?$/, `${serviceId}/`);
      fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((response) => (response.ok ? response.json() : null))
        .then((data) => {
          if (data && !descriptionInput.value) {
            descriptionInput.value = data.title || "";
          }
        })
        .catch(() => {
          // Le préremplissage est une aide : une panne réseau ne bloque pas la saisie.
        });
    });
  }
}

function buildRowFromTemplate(formIndex) {
  const template = document.getElementById("quote-item-template");
  if (!(template instanceof HTMLTemplateElement)) return null;

  const fragment = template.content.cloneNode(true);
  const row = fragment.querySelector("tr.quote-item-row");
  if (!row) return null;

  row.querySelectorAll("input, select, textarea, label").forEach((element) => {
    ["name", "id", "for"].forEach((attribute) => {
      const value = element.getAttribute(attribute);
      if (value) {
        element.setAttribute(attribute, value.replace(/__prefix__/g, String(formIndex)));
      }
    });
  });

  const deleteField = row.querySelector("input[type='checkbox'][name$='-DELETE']");
  if (deleteField) deleteField.checked = false;
  return row;
}

function setupAddLineButton() {
  const addBtn = document.getElementById("add-line-btn");
  const tbody = document.getElementById("quote-items-body");
  const totalFormsInput = document.querySelector("input[name$='-TOTAL_FORMS']");
  if (!addBtn || !tbody || !totalFormsInput) return;

  const managementPrefix = totalFormsInput.name.replace("-TOTAL_FORMS", "");

  addBtn.addEventListener("click", () => {
    const maxFormsInput = document.querySelector(`input[name='${managementPrefix}-MAX_NUM_FORMS']`);
    const totalForms = parseInt(totalFormsInput.value, 10) || 0;
    const maxForms = maxFormsInput ? parseInt(maxFormsInput.value, 10) || 1000 : 1000;

    if (totalForms >= maxForms) {
      alert("Nombre maximal de lignes atteint.");
      return;
    }

    const newRow = buildRowFromTemplate(totalForms);
    if (!newRow) return;

    document.getElementById("quote-empty-state")?.remove();
    tbody.appendChild(newRow);
    attachRowEvents(newRow);
    totalFormsInput.value = String(totalForms + 1);
    recalcTotals();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("tr.quote-item-row").forEach((row) => attachRowEvents(row));
  setupAddLineButton();
  recalcTotals();
});

export {};
