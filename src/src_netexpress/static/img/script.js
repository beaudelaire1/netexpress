document.addEventListener("DOMContentLoaded", function () {

    /* ============================
       1. Slider surface
    ============================ */
    const slider = document.getElementById("myRange");
    const output = document.getElementById("surfaceValue");

    if (slider && output) {
        output.innerHTML = slider.value + " m²";

        slider.addEventListener("input", function () {
            output.innerHTML = this.value + " m²";
            output.style.color = "#104130";
        });
    }

    /* ============================
       2. Cartes de services
    ============================ */
    window.selectOption = function (element) {
        const options = document.querySelectorAll(".option");
        options.forEach(opt => opt.classList.remove("active"));
        element.classList.add("active");
    };

    /* ============================
       3. Onglets
    ============================ */
    window.openTab = function (evt, tabName) {
        const tabLinks = document.getElementsByClassName("tab-btn");
        for (let i = 0; i < tabLinks.length; i++) {
            tabLinks[i].classList.remove("active");
        }
        evt.currentTarget.classList.add("active");
    };

    console.log("✅ JS REALISATION chargé correctement");
});
