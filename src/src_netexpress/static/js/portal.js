/**
 * NetExpress v2 Portal JavaScript
 * Handles HTMX interactions, notifications, and portal-specific functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize portal functionality
    initializePortal();
    initializeNotifications();
    initializeHTMXHandlers();
});

/**
 * Initialize portal-specific functionality
 */
function initializePortal() {
    // Mobile menu toggle
    const mobileMenuButton = document.querySelector('.mobile-menu-button');
    const mobileMenu = document.querySelector('.mobile-menu');
    
    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            const isExpanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
            mobileMenuButton.setAttribute('aria-expanded', !isExpanded);
            mobileMenu.hidden = isExpanded;
        });
    }

    // Auto-hide messages after 5 seconds
    const messages = document.querySelectorAll('.notification');
    messages.forEach(message => {
        setTimeout(() => {
            if (message.parentElement) {
                message.style.transition = 'opacity 0.3s ease-out';
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            }
        }, 5000);
    });

    // Initialize tooltips
    initializeTooltips();
}

/**
 * Initialize notification system
 */
function initializeNotifications() {
    // Create notification container if it doesn't exist
    if (!document.getElementById('notification-container')) {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
    }
}

/**
 * Show a notification to the user
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning, info)
 * @param {number} duration - How long to show the notification (ms)
 */
function showNotification(message, type = 'info', duration = 5000) {
    const container = document.getElementById('notification-container');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type} transform transition-all duration-300 translate-x-full`;
    
    const iconMap = {
        success: 'fa-check-circle text-green-600',
        error: 'fa-exclamation-circle text-red-600',
        warning: 'fa-exclamation-triangle text-yellow-600',
        info: 'fa-info-circle text-blue-600'
    };

    notification.innerHTML = `
        <div class="p-4 max-w-sm">
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <i class="fas ${iconMap[type] || iconMap.info} mr-2"></i>
                    <span class="text-sm font-medium">${message}</span>
                </div>
                <button onclick="removeNotification(this)" class="text-gray-400 hover:text-gray-600 ml-4">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        </div>
    `;

    container.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.classList.remove('translate-x-full');
    }, 10);

    // Auto-remove after duration
    setTimeout(() => {
        removeNotification(notification.querySelector('button'));
    }, duration);
}

/**
 * Remove a notification
 * @param {HTMLElement} button - The close button element
 */
function removeNotification(button) {
    const notification = button.closest('.notification');
    if (notification) {
        notification.classList.add('translate-x-full');
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 300);
    }
}

/**
 * Initialize HTMX event handlers
 */
function initializeHTMXHandlers() {
    // Show loading indicator
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        const indicator = document.getElementById('htmx-indicator');
        if (indicator) {
            indicator.classList.add('htmx-request');
        }
        
        // Add loading state to the triggering element
        const target = evt.detail.elt;
        if (target) {
            target.classList.add('htmx-loading');
            target.disabled = true;
        }
    });

    // Hide loading indicator
    document.body.addEventListener('htmx:afterRequest', function(evt) {
        const indicator = document.getElementById('htmx-indicator');
        if (indicator) {
            indicator.classList.remove('htmx-request');
        }
        
        // Remove loading state from the triggering element
        const target = evt.detail.elt;
        if (target) {
            target.classList.remove('htmx-loading');
            target.disabled = false;
        }
    });

    // Handle successful requests
    document.body.addEventListener('htmx:afterSwap', function(evt) {
        // Re-initialize any new elements that were swapped in
        initializeTooltips();
        
        // Show success notification if data attribute is present
        const target = evt.detail.elt;
        const successMessage = target.getAttribute('data-success-message');
        if (successMessage) {
            showNotification(successMessage, 'success');
        }
    });

    // Handle errors
    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX Error:', evt.detail);
        
        const target = evt.detail.elt;
        const errorMessage = target.getAttribute('data-error-message') || 
                           'Une erreur est survenue. Veuillez réessayer.';
        
        showNotification(errorMessage, 'error');
    });

    // Handle network errors
    document.body.addEventListener('htmx:sendError', function(evt) {
        console.error('HTMX Network Error:', evt.detail);
        showNotification('Erreur de connexion. Vérifiez votre connexion internet.', 'error');
    });
}

/**
 * Initialize tooltips for elements with data-tooltip attribute
 */
function initializeTooltips() {
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(element => {
        if (element.hasAttribute('data-tooltip-initialized')) return;
        
        element.setAttribute('data-tooltip-initialized', 'true');
        
        let tooltip = null;
        
        element.addEventListener('mouseenter', function() {
            const text = this.getAttribute('data-tooltip');
            if (!text) return;
            
            tooltip = document.createElement('div');
            tooltip.className = 'absolute z-50 px-2 py-1 text-xs text-white bg-gray-900 rounded shadow-lg pointer-events-none';
            tooltip.textContent = text;
            
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + 'px';
        });
        
        element.addEventListener('mouseleave', function() {
            if (tooltip) {
                tooltip.remove();
                tooltip = null;
            }
        });
    });
}

/**
 * Utility function to format dates
 * @param {string|Date} date - The date to format
 * @param {string} locale - The locale to use (default: 'fr-FR')
 * @returns {string} Formatted date string
 */
function formatDate(date, locale = 'fr-FR') {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Utility function to format currency
 * @param {number} amount - The amount to format
 * @param {string} currency - The currency code (default: 'EUR')
 * @param {string} locale - The locale to use (default: 'fr-FR')
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount, currency = 'EUR', locale = 'fr-FR') {
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency
    }).format(amount);
}

/**
 * Debounce function for search inputs
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to delay
 * @returns {Function} The debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global use
window.NetExpress = {
    showNotification,
    removeNotification,
    formatDate,
    formatCurrency,
    debounce
};