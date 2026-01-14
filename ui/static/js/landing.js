/**
 * PULSAR SENTINEL - Landing Page Scripts
 */

// Modal Functions
function showDeployModal() {
    const modal = document.getElementById('deploy-modal');
    if (modal) {
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('show'), 10);
    }
}

function hideDeployModal() {
    const modal = document.getElementById('deploy-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

// Download Platform
function downloadPlatform(platform) {
    const downloads = {
        windows: '/downloads/pulsar-sentinel-windows.zip',
        macos: '/downloads/pulsar-sentinel-macos.dmg',
        linux: '/downloads/pulsar-sentinel-linux.tar.gz',
        docker: 'docker pull angelcloud/pulsar-sentinel:latest'
    };

    if (platform === 'docker') {
        // Copy docker command to clipboard
        navigator.clipboard.writeText(downloads.docker);
        notifications.success('Docker command copied to clipboard!');
    } else {
        // Simulate download (in production, this would be actual download)
        notifications.info(`Preparing ${platform} download...`);

        // Track download event
        if (window.walletManager && window.walletManager.isConnected) {
            trackDownload(platform);
        }

        // In production, redirect to actual download
        // window.location.href = downloads[platform];

        setTimeout(() => {
            notifications.success(`${platform.charAt(0).toUpperCase() + platform.slice(1)} download started!`);
        }, 1000);
    }
}

// Track download for analytics
async function trackDownload(platform) {
    try {
        await fetch('/api/v1/analytics/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: platform,
                wallet: window.walletManager?.account || 'anonymous',
                timestamp: new Date().toISOString()
            })
        });
    } catch (error) {
        console.error('Failed to track download:', error);
    }
}

// Select Pricing Tier
function selectTier(tier) {
    if (!window.walletManager?.isConnected) {
        notifications.warning('Please connect your wallet first');
        window.walletManager?.connect();
        return;
    }

    const tierInfo = {
        sentinel_core: { name: 'Sentinel Core', price: 16.99 },
        legacy_builder: { name: 'Legacy Builder', price: 10.99 },
        autonomous_guild: { name: 'Autonomous Guild', price: 29.99 }
    };

    const selected = tierInfo[tier];
    notifications.info(`Selected ${selected.name} - $${selected.price}/month`);

    // Redirect to checkout or show subscription modal
    // In production, this would integrate with payment processing
    showSubscriptionModal(tier, selected);
}

// Show Subscription Modal
function showSubscriptionModal(tierId, tierInfo) {
    const modalContainer = document.getElementById('modal-container');
    if (!modalContainer) return;

    modalContainer.innerHTML = `
        <div class="modal-overlay show" id="subscription-modal">
            <div class="modal-content card">
                <button class="modal-close" onclick="hideSubscriptionModal()">
                    <i class="fas fa-times"></i>
                </button>
                <div class="modal-header">
                    <h3><i class="fas fa-shopping-cart"></i> Subscribe to ${tierInfo.name}</h3>
                </div>
                <div class="modal-body">
                    <div class="subscription-summary">
                        <div class="summary-row">
                            <span>Plan</span>
                            <span>${tierInfo.name}</span>
                        </div>
                        <div class="summary-row">
                            <span>Billing</span>
                            <span>Monthly</span>
                        </div>
                        <div class="summary-row total">
                            <span>Total</span>
                            <span>$${tierInfo.price}/month</span>
                        </div>
                    </div>
                    <div class="payment-options">
                        <h4>Payment Method</h4>
                        <div class="payment-grid">
                            <button class="payment-btn" onclick="payWithCrypto('${tierId}', 'MATIC')">
                                <i class="fab fa-ethereum"></i>
                                <span>MATIC</span>
                            </button>
                            <button class="payment-btn" onclick="payWithCrypto('${tierId}', 'PLS')">
                                <span class="pls-icon">P</span>
                                <span>PULSAR</span>
                            </button>
                            <button class="payment-btn" onclick="payWithCrypto('${tierId}', 'USDC')">
                                <i class="fas fa-dollar-sign"></i>
                                <span>USDC</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function hideSubscriptionModal() {
    const modal = document.getElementById('subscription-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.remove(), 300);
    }
}

// Pay with Crypto
async function payWithCrypto(tierId, currency) {
    const loading = notifications.loading(`Processing ${currency} payment...`);

    try {
        // In production, this would create a blockchain transaction
        // For demo, simulate processing
        await new Promise(resolve => setTimeout(resolve, 2000));

        loading.success(`Payment successful! Welcome to ${tierId.replace('_', ' ')}!`);
        hideSubscriptionModal();

        // Redirect to dashboard
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 1500);

    } catch (error) {
        loading.error('Payment failed. Please try again.');
        console.error('Payment error:', error);
    }
}

// Animate Stats on Scroll
function animateStatsOnScroll() {
    const stats = document.querySelectorAll('.hero-stats .stat-value');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const text = element.textContent;

                // Extract number and suffix
                const match = text.match(/^([\d,\.]+)(.*)$/);
                if (match) {
                    const value = parseFloat(match[1].replace(/,/g, ''));
                    const suffix = match[2];

                    animateNumber(element, value, suffix);
                }

                observer.unobserve(element);
            }
        });
    }, { threshold: 0.5 });

    stats.forEach(stat => observer.observe(stat));
}

function animateNumber(element, target, suffix, duration = 2000) {
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out cubic
        const eased = 1 - Math.pow(1 - progress, 3);
        const current = target * eased;

        if (target >= 1000000) {
            element.textContent = (current / 1000000).toFixed(1) + 'M' + suffix;
        } else if (target >= 1000) {
            element.textContent = (current / 1000).toFixed(1) + 'K' + suffix;
        } else if (suffix === '%') {
            element.textContent = current.toFixed(2) + suffix;
        } else {
            element.textContent = Math.floor(current).toLocaleString() + suffix;
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// Parallax Effect for Hero
function initParallax() {
    const hero = document.querySelector('.hero-section');
    const orb = document.querySelector('.quantum-orb');

    if (!hero || !orb) return;

    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const rate = scrolled * 0.3;

        orb.style.transform = `translateY(${rate}px)`;
    });
}

// Feature Cards Hover Effect
function initFeatureCards() {
    const cards = document.querySelectorAll('.feature-card');

    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

// Close modal on outside click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('show');
        setTimeout(() => e.target.style.display = 'none', 300);
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal-overlay.show');
        modals.forEach(modal => {
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        });
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    animateStatsOnScroll();
    initParallax();
    initFeatureCards();

    // Add loading animation to buttons
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (this.classList.contains('btn-glow')) {
                this.classList.add('clicked');
                setTimeout(() => this.classList.remove('clicked'), 300);
            }
        });
    });
});
