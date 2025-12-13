// 1. Gestion du Slider (Mise à jour valeur)
const slider = document.getElementById("myRange");
const output = document.getElementById("surfaceValue");

if (slider && output) {
    slider.oninput = function () {
        output.innerHTML = this.value + " m²";
        // Change la couleur du texte quand on bouge
        output.style.color = "#104130";
    }
}

// 2. Gestion des Cartes de Services (Bordure verte au clic)
function selectOption(element) {
    // Retire la classe 'active' de tous
    let options = document.querySelectorAll('.option');
    options.forEach(opt => opt.classList.remove('active'));

    // Ajoute au cliqué
    element.classList.add('active');
}

// 3. Gestion des Onglets
function openTab(evt, tabName) {
    // Réinitialise les onglets : retire la classe active de tous les boutons
    let tabLinks = document.getElementsByClassName("tab-btn");
    for (let i = 0; i < tabLinks.length; i++) {
        tabLinks[i].classList.remove("active");
    }
    // Active le bouton cliqué
    evt.currentTarget.classList.add("active");
    // Cette fonction pourrait être étendue pour afficher différents contenus selon l'onglet
}