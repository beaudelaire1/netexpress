// quote_admin.js — logique d'édition des devis (back-office)
// Module ES6 chargé sur la page d'édition des devis.
//
// Responsabilités :
// - Calculer les totaux HT / TVA / TTC en temps réel.
// - Gérer l'ajout / suppression de lignes de devis.
// - Pré-remplir la description lorsqu'un service est sélectionné via fetch JSON.

function parseNumber(value) {
  const v = String(value || "").replace(/\s/g, "").replace(",", ".");
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function formatCurrency(value) {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
  }).format(value);
}

function recalcTotals() {
  const rows = document.querySelectorAll("tr.quote-item-row");
  let totalHt = 0;
  let totalTva = 0;

  rows.forEach((row) => {
    const qtyInput = row.querySelector(".js-quantity");
    const unitInput = row.querySelector(".js-unit-price");
    const taxInput = row.querySelector(".js-tax-rate");
    const cellTotalHt = row.querySelector(".cell-total-ht");

    if (!qtyInput || !unitInput || !taxInput || !cellTotalHt) return;

    const qty = parseNumber(qtyInput.value);
    const unit = parseNumber(unitInput.value);
    const tax = parseNumber(taxInput.value);

    const lineHt = qty * unit;
    const lineTva = lineHt * (tax / 100);

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
    ["input", "change"].forEach((evt) => {
      input.addEventListener(evt, recalcTotals);
    });
  });

  if (removeBtn) {
    removeBtn.addEventListener("click", () => {
      const deleteField = row.querySelector("input[type='checkbox'][name$='-DELETE']");
      if (deleteField) {
        deleteField.checked = true;
        row.style.display = "none";
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

      // L'URL est de la forme /devis/service/0/ — on remplace 0 par l'id
      const url = baseUrl.replace(/0\/?$/, String(serviceId) + "/");

      fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((resp) => (resp.ok ? resp.json() : null))
        .then((data) => {
          if (!data) return;
          if (!descriptionInput.value) {
            descriptionInput.value = data.title || "";
          }
        })
        .catch(() => {
          // En cas d'erreur, on ne bloque pas l'utilisateur.
        });
    });
  }
}

function setupAddLineButton() {
  const addBtn = document.getElementById("add-line-btn");
  const tbody = document.getElementById("quote-items-body");
  const totalFormsInput = tbody?.querySelector("input[name$='-TOTAL_FORMS']");
  if (!addBtn || !tbody || !totalFormsInput) return;

  const managementPrefix = totalFormsInput.name.replace("-TOTAL_FORMS", "");

  addBtn.addEventListener("click", () => {
    const maxFormsInput = document.querySelector(
      `input[name='${managementPrefix}-MAX_NUM_FORMS']`
    );

    const totalForms = parseInt(totalFormsInput.value, 10) || 0;
    const maxForms = maxFormsInput ? parseInt(maxFormsInput.value, 10) || 1000 : 1000;

    if (totalForms >= maxForms) {
      alert("Nombre maximal de lignes atteint.");
      return;
    }

    const templateRow = tbody.querySelector("tr.quote-item-row");
    if (!templateRow) return;

    const newRow = templateRow.cloneNode(true);
    const regex = new RegExp(`${managementPrefix}-(\\d+)-`, "g");

    newRow.querySelectorAll("input, select").forEach((el) => {
      if (!(el instanceof HTMLInputElement || el instanceof HTMLSelectElement)) return;
      if (el.name) {
        el.name = el.name.replace(regex, `${managementPrefix}-${totalForms}-`);
      }
      if (el.id) {
        el.id = el.id.replace(regex, `${managementPrefix}-${totalForms}-`);
      }

      if (el.type === "checkbox") {
        el.checked = false;
      } else {
        el.value = "";
      }
    });

    // Les champs cachés DELETE doivent être décochés
    const deleteField = newRow.querySelector("input[type='checkbox'][name$='-DELETE']");
    if (deleteField) {
      deleteField.checked = false;
    }

    tbody.appendChild(newRow);
    attachRowEvents(newRow);
    totalFormsInput.value = String(totalForms + 1);
    recalcTotals();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("tr.quote-item-row").forEach((row) => {
    attachRowEvents(row);
  });
  setupAddLineButton();
  recalcTotals();
});

// Export vide pour que le fichier soit traité comme module sans polluer le scope global.
export {};
