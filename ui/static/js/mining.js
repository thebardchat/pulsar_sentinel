/**
 * PULSAR SENTINEL - Mining Scripts
 */

// Mining State
const miningState = {
    isActive: false,
    hashrate: 0,
    shares: { valid: 0, rejected: 0 },
    earnings: { today: 0, total: 48.50 },
    interval: null,
    consoleInterval: null
};

// Initialize Mining Page
document.addEventListener('DOMContentLoaded', () => {
    initMiningPage();
});

function initMiningPage() {
    // Initialize slider listeners
    initSliders();

    // Initialize chart period buttons
    initChartControls();

    // Load mining data
    loadMiningData();
}

function initSliders() {
    const threadsSlider = document.getElementById('cpu-threads');
    const intensitySlider = document.getElementById('mining-intensity');

    if (threadsSlider) {
        threadsSlider.addEventListener('input', (e) => {
            document.getElementById('threads-value').textContent = e.target.value;
        });
    }

    if (intensitySlider) {
        intensitySlider.addEventListener('input', (e) => {
            document.getElementById('intensity-value').textContent = e.target.value + '%';
        });
    }
}

function initChartControls() {
    const chartBtns = document.querySelectorAll('.chart-controls .btn');

    chartBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            chartBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            // In production, update chart data based on period
        });
    });
}

async function loadMiningData() {
    // In production, fetch from API
    updateMiningStats();
}

function updateMiningStats() {
    document.getElementById('current-hashrate').textContent =
        miningState.hashrate.toFixed(2) + ' TH/s';
    document.getElementById('valid-shares').textContent =
        miningState.shares.valid.toLocaleString();
    document.getElementById('rejected-shares').textContent =
        miningState.shares.rejected + ' rejected';
    document.getElementById('today-earnings').textContent =
        miningState.earnings.today.toFixed(2) + ' PLS';
    document.getElementById('today-usd').textContent =
        (miningState.earnings.today * 2).toFixed(2);
    document.getElementById('total-mined').textContent =
        miningState.earnings.total.toFixed(2) + ' PLS';
}

// Mining Control
function toggleMining() {
    if (miningState.isActive) {
        stopMining();
    } else {
        startMining();
    }
}

function startMining() {
    if (!window.walletManager?.isAuthenticated()) {
        notifications.warning('Please connect your wallet first');
        return;
    }

    miningState.isActive = true;

    // Update button
    const btn = document.getElementById('mining-start-btn');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-stop"></i> Stop Mining';
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-danger');
    }

    // Update indicator
    const indicator = document.getElementById('hashrate-indicator');
    if (indicator) {
        indicator.classList.remove('inactive');
        indicator.classList.add('active');
    }

    // Start simulation
    simulateMining();
    addConsoleLog('[MINER] Mining started', 'success');
    addConsoleLog('[MINER] Connecting to pool.pulsar.cloud:3333...', 'info');

    setTimeout(() => {
        addConsoleLog('[MINER] Connected to pool successfully', 'success');
        addConsoleLog('[MINER] Authorized worker: ' + getWorkerName(), 'info');
    }, 1000);

    notifications.success('Mining started!');
}

function stopMining() {
    miningState.isActive = false;

    // Clear intervals
    if (miningState.interval) {
        clearInterval(miningState.interval);
        miningState.interval = null;
    }

    // Update button
    const btn = document.getElementById('mining-start-btn');
    if (btn) {
        btn.innerHTML = '<i class="fas fa-play"></i> Start Mining';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-primary');
    }

    // Update indicator
    const indicator = document.getElementById('hashrate-indicator');
    if (indicator) {
        indicator.classList.remove('active');
        indicator.classList.add('inactive');
    }

    // Reset hashrate
    miningState.hashrate = 0;
    updateMiningStats();

    addConsoleLog('[MINER] Mining stopped', 'warning');
    notifications.info('Mining stopped');
}

function simulateMining() {
    // Simulate hashrate ramp-up
    let targetHashrate = 40 + Math.random() * 10;
    let currentHashrate = 0;

    miningState.interval = setInterval(() => {
        if (!miningState.isActive) return;

        // Ramp up hashrate
        if (currentHashrate < targetHashrate) {
            currentHashrate += targetHashrate * 0.1;
            if (currentHashrate > targetHashrate) currentHashrate = targetHashrate;
        }

        // Add some variance
        miningState.hashrate = currentHashrate + (Math.random() - 0.5) * 2;

        // Simulate shares
        if (Math.random() < 0.3) {
            miningState.shares.valid++;
            if (Math.random() < 0.02) {
                miningState.shares.rejected++;
            }
        }

        // Simulate earnings
        miningState.earnings.today += Math.random() * 0.001;
        miningState.earnings.total += Math.random() * 0.001;

        // Update hardware stats
        updateHardwareStats();

        // Update UI
        updateMiningStats();

        // Occasional console logs
        if (Math.random() < 0.05) {
            addShareLog();
        }

    }, 1000);
}

function updateHardwareStats() {
    const cpuUsage = 40 + Math.random() * 20;
    const memUsage = 55 + Math.random() * 15;
    const cpuTemp = 48 + Math.random() * 10;
    const powerDraw = 80 + Math.random() * 20;

    document.getElementById('cpu-usage')?.style.setProperty('width', cpuUsage + '%');
    document.getElementById('memory-usage')?.style.setProperty('width', memUsage + '%');
    document.getElementById('cpu-temp')?.style.setProperty('width', cpuTemp + '%');
    document.getElementById('power-draw')?.style.setProperty('width', (powerDraw / 250 * 100) + '%');
}

function addShareLog() {
    const shareNum = miningState.shares.valid;
    const hashrate = miningState.hashrate.toFixed(2);
    const messages = [
        `[SHARE] Accepted share #${shareNum} (${hashrate} TH/s)`,
        `[POOL] Job received from pool`,
        `[MINER] New block template received`,
    ];

    const msg = messages[Math.floor(Math.random() * messages.length)];
    addConsoleLog(msg, 'info');
}

// Console Functions
function addConsoleLog(message, type = 'info') {
    const console = document.getElementById('mining-console');
    if (!console) return;

    const line = document.createElement('div');
    line.className = `console-line ${type}`;
    line.textContent = message;

    console.appendChild(line);
    console.scrollTop = console.scrollHeight;

    // Limit console lines
    while (console.children.length > 100) {
        console.removeChild(console.firstChild);
    }
}

function clearConsole() {
    const console = document.getElementById('mining-console');
    if (console) {
        console.innerHTML = `
            <div class="console-line info">[SYSTEM] Console cleared</div>
            <div class="console-line info">[SYSTEM] PULSAR Mining Engine v1.0.0</div>
        `;
    }
}

function getWorkerName() {
    return document.getElementById('worker-name')?.value || 'pulsar-miner-01';
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (miningState.interval) {
        clearInterval(miningState.interval);
    }
});
