document.addEventListener("DOMContentLoaded", () => {
    // 1. Sticky Navigation Bar
    const header = document.querySelector("header");
    window.addEventListener("scroll", () => {
        if (window.scrollY > 50) {
            header.style.boxShadow = "0 4px 6px rgba(0, 0, 0, 0.1)";
        } else {
            header.style.boxShadow = "none";
        }
    });

    // 2. Service Cards Animation on Scroll
    const serviceCards = document.querySelectorAll(".service-card");
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.style.transform = "translateY(0)";
                entry.target.style.opacity = "1";
            } else {
                entry.target.style.transform = "translateY(20px)";
                entry.target.style.opacity = "0";
            }
        });
    }, { threshold: 0.5 });

    serviceCards.forEach((card) => {
        card.style.transition = "transform 0.3s ease, opacity 0.3s ease";
        card.style.transform = "translateY(20px)";
        card.style.opacity = "0";
        observer.observe(card);
    });

    // 3. Form Validation
    const contactForm = document.querySelector("#contact-form form");
    if (contactForm) {
        contactForm.addEventListener("submit", (event) => {
            const nameField = contactForm.querySelector("input[name='nom']");
            const emailField = contactForm.querySelector("input[name='email']");
            const messageField = contactForm.querySelector("textarea[name='message']");
            let isValid = true;

            // Clear previous errors
            contactForm.querySelectorAll(".error").forEach((el) => el.remove());

            // Validate name
            if (nameField.value.trim() === "") {
                isValid = false;
                displayError(nameField, "Veuillez entrer votre nom.");
            }

            // Validate email
            if (!validateEmail(emailField.value)) {
                isValid = false;
                displayError(emailField, "Veuillez entrer une adresse email valide.");
            }

            // Validate message
            if (messageField.value.trim() === "") {
                isValid = false;
                displayError(messageField, "Veuillez entrer votre message.");
            }

            if (!isValid) {
                event.preventDefault(); // Prevent form submission
            }
        });
    }

    function displayError(input, message) {
        const error = document.createElement("small");
        error.textContent = message;
        error.className = "error";
        error.style.color = "red";
        input.parentElement.appendChild(error);
    }

    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    // 4. Back-to-top Button
    const backToTop = document.createElement("button");
    backToTop.textContent = "↑";
    backToTop.style.position = "fixed";
    backToTop.style.bottom = "20px";
    backToTop.style.right = "20px";
    backToTop.style.padding = "10px 15px";
    backToTop.style.backgroundColor = "var(--secondary-color)";
    backToTop.style.color = "var(--white)";
    backToTop.style.border = "none";
    backToTop.style.borderRadius = "50%";
    backToTop.style.boxShadow = "var(--shadow-light)";
    backToTop.style.cursor = "pointer";
    backToTop.style.display = "none"; // Hidden by default
    backToTop.style.zIndex = "1000";

    document.body.appendChild(backToTop);

    window.addEventListener("scroll", () => {
        if (window.scrollY > 200) {
            backToTop.style.display = "block";
        } else {
            backToTop.style.display = "none";
        }
    });

    backToTop.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
});
