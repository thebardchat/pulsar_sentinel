/**
 * PULSAR SENTINEL - Notification System
 * Handles toast notifications and alerts
 */

class NotificationManager {
    constructor() {
        this.container = document.getElementById('notification-container');
        this.notifications = [];
        this.defaultDuration = 5000;

        if (!this.container) {
            this.createContainer();
        }
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = this.defaultDuration) {
        const notification = this.createNotification(message, type);
        this.container.appendChild(notification);
        this.notifications.push(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => this.dismiss(notification), duration);
        }

        return notification;
    }

    createNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;

        const icon = this.getIcon(type);

        notification.innerHTML = `
            <div class="notification-icon">
                <i class="${icon}"></i>
            </div>
            <div class="notification-content">
                <p class="notification-message">${message}</p>
            </div>
            <button class="notification-close" onclick="notifications.dismissThis(this)">
                <i class="fas fa-times"></i>
            </button>
            <div class="notification-progress">
                <div class="notification-progress-bar"></div>
            </div>
        `;

        return notification;
    }

    getIcon(type) {
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        return icons[type] || icons.info;
    }

    dismiss(notification) {
        notification.classList.remove('show');
        notification.classList.add('hide');

        setTimeout(() => {
            notification.remove();
            this.notifications = this.notifications.filter(n => n !== notification);
        }, 300);
    }

    dismissThis(button) {
        const notification = button.closest('.notification');
        this.dismiss(notification);
    }

    dismissAll() {
        this.notifications.forEach(n => this.dismiss(n));
    }

    // Convenience methods
    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }

    // Persistent notification (won't auto-dismiss)
    persistent(message, type = 'info') {
        return this.show(message, type, 0);
    }

    // Confirmation dialog
    async confirm(message, options = {}) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay confirm-modal';
            modal.innerHTML = `
                <div class="modal-content card">
                    <div class="modal-header">
                        <h3><i class="fas fa-question-circle"></i> ${options.title || 'Confirm'}</h3>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary cancel-btn">
                            ${options.cancelText || 'Cancel'}
                        </button>
                        <button class="btn btn-primary confirm-btn">
                            ${options.confirmText || 'Confirm'}
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);
            setTimeout(() => modal.classList.add('show'), 10);

            const cleanup = (result) => {
                modal.classList.remove('show');
                setTimeout(() => modal.remove(), 300);
                resolve(result);
            };

            modal.querySelector('.cancel-btn').onclick = () => cleanup(false);
            modal.querySelector('.confirm-btn').onclick = () => cleanup(true);
            modal.onclick = (e) => {
                if (e.target === modal) cleanup(false);
            };
        });
    }

    // Loading indicator
    loading(message = 'Loading...') {
        const notification = document.createElement('div');
        notification.className = 'notification notification-loading show';
        notification.innerHTML = `
            <div class="notification-icon">
                <div class="spinner-quantum small"></div>
            </div>
            <div class="notification-content">
                <p class="notification-message">${message}</p>
            </div>
        `;

        this.container.appendChild(notification);

        return {
            update: (newMessage) => {
                notification.querySelector('.notification-message').textContent = newMessage;
            },
            success: (message) => {
                this.dismiss(notification);
                this.success(message);
            },
            error: (message) => {
                this.dismiss(notification);
                this.error(message);
            },
            dismiss: () => {
                this.dismiss(notification);
            }
        };
    }
}

// Create global instance
window.notifications = new NotificationManager();

// Export for use in other modules
window.NotificationManager = NotificationManager;
