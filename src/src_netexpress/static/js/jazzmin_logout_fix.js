/**
 * Fix for Django 5.x logout in Jazzmin
 * Django 5.0+ requires POST for logout, but Jazzmin uses GET links
 */
(function() {
    // Helper function to get CSRF token from cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function setupLogoutLinks() {
        // Find all logout links in the admin
        const logoutLinks = document.querySelectorAll('a[href$="/logout/"], a[href*="/logout"]');
        
        logoutLinks.forEach(function(link) {
            // Skip if already processed
            if (link.dataset.logoutFixed) return;
            link.dataset.logoutFixed = 'true';
            
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Create a form and submit it as POST
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = link.href;
                form.style.display = 'none';
                
                // Get CSRF token from cookie
                const csrfToken = getCookie('csrftoken');
                
                if (csrfToken) {
                    const csrfInput = document.createElement('input');
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrfmiddlewaretoken';
                    csrfInput.value = csrfToken;
                    form.appendChild(csrfInput);
                }
                
                document.body.appendChild(form);
                form.submit();
            });
        });
    }

    // Run on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupLogoutLinks);
    } else {
        setupLogoutLinks();
    }
})();

