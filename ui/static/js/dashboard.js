/**
 * PULSAR SENTINEL - Dashboard Scripts
 */

// Dashboard State
const dashboardState = {
    refreshInterval: null,
    charts: {},
    data: {
        securityScore: 98.5,
        encryptedToday: 1247,
        pulsarBalance: 2450,
        ptsScore: 32
    }
};

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    initSidebarNavigation();
    startAutoRefresh();
});

function initDashboard() {
    // Check authentication
    if (!window.walletManager?.isAuthenticated()) {
        notifications.warning('Please connect your wallet to view dashboard');
    }

    // Load initial data
    loadDashboardData();

    // Initialize charts
    initCharts();

    // Set user address
    updateUserAddress();
}

async function loadDashboardData() {
    try {
        // In production, fetch from API
        // const response = await walletManager.apiRequest('/api/v1/dashboard');
        // const data = await response.json();

        // For demo, use simulated data
        updateStats(dashboardState.data);

    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function updateStats(data) {
    animateValue('security-score', data.securityScore, '%');
    animateValue('encrypted-today', data.encryptedToday);
    animateValue('pulsar-balance', data.pulsarBalance, '', 2);
    animateValue('pts-score', data.ptsScore);
}

function animateValue(elementId, value, suffix = '', decimals = 0) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const current = parseFloat(element.textContent.replace(/[^0-9.-]/g, '')) || 0;
    const duration = 1000;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);

        const currentValue = current + (value - current) * eased;

        if (decimals > 0) {
            element.textContent = currentValue.toFixed(decimals) + suffix;
        } else {
            element.textContent = Math.floor(currentValue).toLocaleString() + suffix;
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

function initCharts() {
    // PTS Gauge
    const ptsGauge = document.querySelector('.gauge-fill');
    if (ptsGauge) {
        const ptsValue = dashboardState.data.ptsScore;
        // Calculate stroke offset (max 150 for critical)
        const percentage = Math.min(ptsValue / 150, 1);
        const offset = 283 - (283 * percentage);
        ptsGauge.style.strokeDashoffset = offset;

        // Update class based on tier
        if (ptsValue < 50) {
            ptsGauge.classList.add('safe');
        } else if (ptsValue < 150) {
            ptsGauge.classList.add('warning');
        } else {
            ptsGauge.classList.add('critical');
        }
    }
}

function initSidebarNavigation() {
    const links = document.querySelectorAll('.sidebar-link');

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            // Update active state
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Scroll to section
            const targetId = link.getAttribute('href').replace('#', '');
            const target = document.getElementById(targetId);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

function startAutoRefresh() {
    dashboardState.refreshInterval = setInterval(() => {
        // Simulate real-time updates
        simulateDataUpdate();
    }, 30000); // Update every 30 seconds
}

function stopAutoRefresh() {
    if (dashboardState.refreshInterval) {
        clearInterval(dashboardState.refreshInterval);
    }
}

function simulateDataUpdate() {
    // Simulate minor fluctuations
    dashboardState.data.encryptedToday += Math.floor(Math.random() * 10);
    dashboardState.data.pulsarBalance += Math.random() * 0.5;

    updateStats(dashboardState.data);
}

function refreshDashboard() {
    const btn = event?.target;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
    }

    loadDashboardData().then(() => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
        }
        notifications.success('Dashboard refreshed');
    });
}

function updateUserAddress() {
    const addressElement = document.getElementById('user-wallet-address');
    if (addressElement && window.walletManager?.account) {
        const addr = window.walletManager.account;
        addressElement.textContent = `${addr.slice(0, 6)}...${addr.slice(-4)}`;
    }
}

// Deployment Management
function showDeployModal() {
    // Use the landing page modal or create a new one
    const existingModal = document.getElementById('deploy-modal');
    if (existingModal) {
        existingModal.style.display = 'flex';
        setTimeout(() => existingModal.classList.add('show'), 10);
    } else {
        // Create modal dynamically
        createDeployModal();
    }
}

function createDeployModal() {
    const modal = document.createElement('div');
    modal.id = 'deploy-modal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content card">
            <button class="modal-close" onclick="hideDeployModal()">
                <i class="fas fa-times"></i>
            </button>
            <div class="modal-header">
                <h3><i class="fas fa-plus"></i> New Deployment</h3>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>Deployment Name</label>
                    <input type="text" class="form-input" id="deploy-name" placeholder="my-sentinel-node">
                </div>
                <div class="form-group">
                    <label>Node Type</label>
                    <select class="form-select" id="deploy-type">
                        <option value="sentinel">Sentinel Node</option>
                        <option value="mining">Mining Node</option>
                        <option value="validator">Validator Node</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Security Level</label>
                    <select class="form-select" id="deploy-security">
                        <option value="768">ML-KEM-768 (Recommended)</option>
                        <option value="1024">ML-KEM-1024 (Maximum)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" checked>
                        <span>Enable automatic updates</span>
                    </label>
                </div>
                <button class="btn btn-primary btn-glow btn-block" onclick="createDeployment()">
                    <i class="fas fa-rocket"></i> Deploy Node
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    setTimeout(() => modal.classList.add('show'), 10);
}

function hideDeployModal() {
    const modal = document.getElementById('deploy-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

async function createDeployment() {
    const name = document.getElementById('deploy-name')?.value || 'sentinel-node';
    const type = document.getElementById('deploy-type')?.value || 'sentinel';
    const security = document.getElementById('deploy-security')?.value || '768';

    const loading = notifications.loading('Creating deployment...');

    try {
        // Simulate deployment creation
        await new Promise(resolve => setTimeout(resolve, 2000));

        loading.success(`Deployment "${name}" created successfully!`);
        hideDeployModal();

        // Refresh dashboard
        loadDashboardData();

    } catch (error) {
        loading.error('Failed to create deployment');
        console.error('Deployment error:', error);
    }
}

// ASR Log Filtering
function filterASRLogs() {
    const filter = document.getElementById('asr-filter')?.value || 'all';
    const rows = document.querySelectorAll('.data-table tbody tr');

    rows.forEach(row => {
        const action = row.querySelector('td:nth-child(3)')?.textContent || '';

        if (filter === 'all') {
            row.style.display = '';
        } else if (filter === 'encrypt' && action.includes('encrypt')) {
            row.style.display = '';
        } else if (filter === 'auth' && action.includes('auth')) {
            row.style.display = '';
        } else if (filter === 'violation' && (action.includes('violation') || action.includes('warn'))) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

// Initialize filter listener
document.addEventListener('DOMContentLoaded', () => {
    const asrFilter = document.getElementById('asr-filter');
    if (asrFilter) {
        asrFilter.addEventListener('change', filterASRLogs);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});
