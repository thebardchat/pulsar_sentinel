/**
 * PULSAR SENTINEL - Wallet Management Scripts
 */

// Wallet State
const walletState = {
    balances: {
        pls: 2450.00,
        matic: 125.50,
        staked: 500.00,
        rewards: 48.50
    },
    transactions: []
};

// Initialize Wallet Page
document.addEventListener('DOMContentLoaded', () => {
    initWalletPage();
});

function initWalletPage() {
    // Check authentication
    if (!window.walletManager?.isAuthenticated()) {
        notifications.warning('Please connect your wallet first');
    }

    // Load wallet data
    loadWalletData();

    // Update wallet address display
    updateWalletDisplay();

    // Initialize transaction filter
    const txFilter = document.getElementById('tx-filter');
    if (txFilter) {
        txFilter.addEventListener('change', filterTransactions);
    }

    // Initialize staking tier selection
    initStakingTiers();
}

async function loadWalletData() {
    try {
        // In production, fetch from API
        // const response = await walletManager.apiRequest('/api/v1/wallet/balance');

        // Update balance displays
        updateBalanceDisplays();

    } catch (error) {
        console.error('Failed to load wallet data:', error);
    }
}

function updateWalletDisplay() {
    const addressElement = document.getElementById('wallet-address');
    if (addressElement && window.walletManager?.account) {
        addressElement.textContent = window.walletManager.account;
    }
}

function updateBalanceDisplays() {
    const plsBalance = document.getElementById('pls-balance');
    if (plsBalance) {
        plsBalance.textContent = walletState.balances.pls.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}

// Copy Address Functions
function copyAddress() {
    const address = window.walletManager?.account;
    if (address) {
        navigator.clipboard.writeText(address);
        notifications.success('Address copied to clipboard!');
    }
}

function copyReceiveAddress() {
    copyAddress();
}

// Modal Functions
function showSendModal() {
    const modal = document.getElementById('send-modal');
    if (modal) {
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('show'), 10);
    }
}

function hideSendModal() {
    const modal = document.getElementById('send-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

function showReceiveModal() {
    const modal = document.getElementById('receive-modal');
    if (modal) {
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('show'), 10);

        // Update QR code and address
        const addressDisplay = document.getElementById('receive-address');
        if (addressDisplay && window.walletManager?.account) {
            addressDisplay.textContent = window.walletManager.account;
        }
    }
}

function hideReceiveModal() {
    const modal = document.getElementById('receive-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

function showSwapModal() {
    notifications.info('Token swap feature coming soon!');
}

// Send Functions
function setSendMax() {
    const amountInput = document.getElementById('send-amount');
    if (amountInput) {
        amountInput.value = walletState.balances.pls.toFixed(2);
        updateSendTotal();
    }
}

function updateSendTotal() {
    const amountInput = document.getElementById('send-amount');
    const totalDisplay = document.getElementById('send-total');

    if (amountInput && totalDisplay) {
        const amount = parseFloat(amountInput.value) || 0;
        totalDisplay.textContent = `${amount.toFixed(2)} PLS`;
    }
}

async function confirmSend() {
    const recipient = document.getElementById('send-recipient')?.value;
    const amount = parseFloat(document.getElementById('send-amount')?.value) || 0;

    // Validation
    if (!recipient || !recipient.startsWith('0x') || recipient.length !== 42) {
        notifications.error('Please enter a valid wallet address');
        return;
    }

    if (amount <= 0) {
        notifications.error('Please enter a valid amount');
        return;
    }

    if (amount > walletState.balances.pls) {
        notifications.error('Insufficient balance');
        return;
    }

    // Confirm transaction
    const confirmed = await notifications.confirm(
        `Send ${amount.toFixed(2)} PLS to ${recipient.slice(0, 6)}...${recipient.slice(-4)}?`,
        { title: 'Confirm Transaction' }
    );

    if (!confirmed) return;

    const loading = notifications.loading('Processing transaction...');

    try {
        // Simulate transaction
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Update balance
        walletState.balances.pls -= amount;
        updateBalanceDisplays();

        loading.success('Transaction sent successfully!');
        hideSendModal();

        // Clear form
        document.getElementById('send-recipient').value = '';
        document.getElementById('send-amount').value = '';

    } catch (error) {
        loading.error('Transaction failed');
        console.error('Send error:', error);
    }
}

// Reward Claiming
async function claimRewards() {
    if (walletState.balances.rewards <= 0) {
        notifications.warning('No rewards to claim');
        return;
    }

    const confirmed = await notifications.confirm(
        `Claim ${walletState.balances.rewards.toFixed(2)} PLS rewards?`,
        { title: 'Claim Rewards' }
    );

    if (!confirmed) return;

    const loading = notifications.loading('Claiming rewards...');

    try {
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Add to balance
        walletState.balances.pls += walletState.balances.rewards;
        walletState.balances.rewards = 0;

        updateBalanceDisplays();
        loading.success('Rewards claimed successfully!');

    } catch (error) {
        loading.error('Failed to claim rewards');
    }
}

// Staking Functions
function initStakingTiers() {
    const tierOptions = document.querySelectorAll('.tier-option input');

    tierOptions.forEach(option => {
        option.addEventListener('change', () => {
            // Update UI
            document.querySelectorAll('.tier-option').forEach(opt => {
                opt.classList.remove('selected');
            });
            option.closest('.tier-option').classList.add('selected');

            // Update preview
            updateStakingPreview();
        });
    });

    // Amount input listener
    const stakeAmount = document.getElementById('stake-amount');
    if (stakeAmount) {
        stakeAmount.addEventListener('input', updateStakingPreview);
    }
}

function setMaxStake() {
    const amountInput = document.getElementById('stake-amount');
    if (amountInput) {
        const available = walletState.balances.pls - walletState.balances.staked;
        amountInput.value = available.toFixed(2);
        updateStakingPreview();
    }
}

function updateStakingPreview() {
    const amount = parseFloat(document.getElementById('stake-amount')?.value) || 0;
    const selectedTier = document.querySelector('input[name="stake-tier"]:checked');
    const duration = parseInt(selectedTier?.value) || 90;

    // Calculate APY based on duration
    const apyRates = { 30: 0.08, 60: 0.10, 90: 0.125 };
    const apy = apyRates[duration] || 0.125;

    // Calculate estimated rewards
    const dailyRate = apy / 365;
    const estimatedRewards = amount * dailyRate * duration;

    // Update preview
    const rewardsDisplay = document.querySelector('.staking-preview .preview-value');
    if (rewardsDisplay) {
        rewardsDisplay.textContent = `+${estimatedRewards.toFixed(2)} PLS`;
    }

    // Update unlock date
    const unlockDate = new Date();
    unlockDate.setDate(unlockDate.getDate() + duration);
    const dateDisplay = document.querySelectorAll('.staking-preview .preview-value')[1];
    if (dateDisplay) {
        dateDisplay.textContent = unlockDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
}

async function stakeTokens() {
    const amount = parseFloat(document.getElementById('stake-amount')?.value) || 0;
    const available = walletState.balances.pls - walletState.balances.staked;

    if (amount <= 0) {
        notifications.error('Please enter an amount to stake');
        return;
    }

    if (amount > available) {
        notifications.error('Insufficient available balance');
        return;
    }

    const confirmed = await notifications.confirm(
        `Stake ${amount.toFixed(2)} PLS? This will lock your tokens for the selected period.`,
        { title: 'Confirm Staking' }
    );

    if (!confirmed) return;

    const loading = notifications.loading('Staking tokens...');

    try {
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Update balances
        walletState.balances.staked += amount;

        updateBalanceDisplays();
        loading.success('Tokens staked successfully!');

        // Clear input
        document.getElementById('stake-amount').value = '';

    } catch (error) {
        loading.error('Staking failed');
        console.error('Staking error:', error);
    }
}

// Transaction Filtering
function filterTransactions() {
    const filter = document.getElementById('tx-filter')?.value || 'all';
    const items = document.querySelectorAll('.transaction-item');

    items.forEach(item => {
        const type = item.querySelector('.tx-icon')?.classList;

        if (filter === 'all') {
            item.style.display = '';
        } else if (filter === 'send' && type?.contains('send')) {
            item.style.display = '';
        } else if (filter === 'receive' && type?.contains('receive')) {
            item.style.display = '';
        } else if (filter === 'mining' && item.querySelector('.tx-main h4')?.textContent.includes('Mining')) {
            item.style.display = '';
        } else if (filter === 'stake' && type?.contains('stake')) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

// Initialize amount input listeners
document.addEventListener('DOMContentLoaded', () => {
    const sendAmount = document.getElementById('send-amount');
    if (sendAmount) {
        sendAmount.addEventListener('input', updateSendTotal);
    }
});
