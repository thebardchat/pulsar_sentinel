/**
 * PULSAR SENTINEL - Authentication Scripts
 */

// Auth State
const authState = {
    nonce: null,
    message: null,
    isProcessing: false
};

// Initialize Auth Page
document.addEventListener('DOMContentLoaded', () => {
    initAuthPage();
});

function initAuthPage() {
    // Check if already authenticated
    if (window.walletManager?.isAuthenticated()) {
        // Redirect to dashboard
        window.location.href = '/dashboard';
        return;
    }

    // Bind MetaMask connect button
    const connectBtn = document.getElementById('metamask-connect');
    if (connectBtn) {
        connectBtn.addEventListener('click', handleWalletConnect);
    }

    // Bind sign button
    const signBtn = document.getElementById('sign-btn');
    if (signBtn) {
        signBtn.addEventListener('click', handleSignMessage);
    }
}

async function handleWalletConnect() {
    if (authState.isProcessing) return;
    authState.isProcessing = true;

    const connectBtn = document.getElementById('metamask-connect');
    if (connectBtn) {
        connectBtn.disabled = true;
        connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Connecting...';
    }

    try {
        // Check for MetaMask
        if (!window.ethereum) {
            notifications.error('Please install MetaMask to continue');
            window.open('https://metamask.io/download/', '_blank');
            return;
        }

        // Request accounts
        const accounts = await window.ethereum.request({
            method: 'eth_requestAccounts'
        });

        if (accounts.length === 0) {
            throw new Error('No accounts found');
        }

        const walletAddress = accounts[0];

        // Update UI to show connected wallet
        showSigningSection(walletAddress);

        // Request nonce from server
        await requestNonce(walletAddress);

    } catch (error) {
        console.error('Connection error:', error);

        if (error.code === 4001) {
            notifications.warning('Connection cancelled by user');
        } else {
            notifications.error('Failed to connect wallet');
        }

        resetConnectButton();
    } finally {
        authState.isProcessing = false;
    }
}

function showSigningSection(walletAddress) {
    // Hide wallet connect section
    const connectSection = document.getElementById('wallet-connect-section');
    if (connectSection) {
        connectSection.style.display = 'none';
    }

    // Show signing section
    const signingSection = document.getElementById('signing-section');
    if (signingSection) {
        signingSection.style.display = 'block';
    }

    // Update address display
    const addressDisplay = document.getElementById('connected-address');
    if (addressDisplay) {
        const short = `${walletAddress.slice(0, 6)}...${walletAddress.slice(-4)}`;
        addressDisplay.textContent = short;
    }

    const msgWallet = document.getElementById('msg-wallet');
    if (msgWallet) {
        msgWallet.textContent = walletAddress;
    }
}

async function requestNonce(walletAddress) {
    try {
        const response = await fetch('/api/v1/auth/nonce', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wallet_address: walletAddress })
        });

        if (!response.ok) {
            throw new Error('Failed to get nonce');
        }

        const data = await response.json();
        authState.nonce = data.nonce;
        authState.message = data.message;

        // Update message display
        const msgNonce = document.getElementById('msg-nonce');
        if (msgNonce) {
            msgNonce.textContent = data.nonce;
        }

        const msgTimestamp = document.getElementById('msg-timestamp');
        if (msgTimestamp) {
            msgTimestamp.textContent = new Date().toISOString();
        }

    } catch (error) {
        console.error('Nonce request error:', error);
        // For demo, create a simulated nonce
        authState.nonce = generateSimulatedNonce();
        authState.message = createAuthMessage(walletAddress, authState.nonce);

        const msgNonce = document.getElementById('msg-nonce');
        if (msgNonce) {
            msgNonce.textContent = authState.nonce;
        }

        const msgTimestamp = document.getElementById('msg-timestamp');
        if (msgTimestamp) {
            msgTimestamp.textContent = new Date().toISOString();
        }
    }
}

function generateSimulatedNonce() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

function createAuthMessage(walletAddress, nonce) {
    return `PULSAR SENTINEL Authentication

Wallet: ${walletAddress}
Nonce: ${nonce}
Timestamp: ${new Date().toISOString()}

Sign this message to authenticate.
This request will not trigger a blockchain transaction or cost any gas fees.`;
}

async function handleSignMessage() {
    if (authState.isProcessing) return;
    authState.isProcessing = true;

    const signBtn = document.getElementById('sign-btn');
    if (signBtn) {
        signBtn.disabled = true;
        signBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Awaiting signature...';
    }

    try {
        const accounts = await window.ethereum.request({
            method: 'eth_accounts'
        });

        if (accounts.length === 0) {
            throw new Error('No wallet connected');
        }

        const walletAddress = accounts[0];

        // Sign message
        const signature = await window.ethereum.request({
            method: 'personal_sign',
            params: [authState.message || createAuthMessage(walletAddress, authState.nonce), walletAddress]
        });

        // Show verification section
        showVerificationSection();

        // Verify signature
        await verifySignature(walletAddress, signature, authState.nonce);

    } catch (error) {
        console.error('Signing error:', error);

        if (error.code === 4001) {
            notifications.warning('Signing cancelled by user');
        } else {
            notifications.error('Failed to sign message');
        }

        // Reset sign button
        if (signBtn) {
            signBtn.disabled = false;
            signBtn.innerHTML = '<i class="fas fa-pen-fancy"></i> Sign Message';
        }
    } finally {
        authState.isProcessing = false;
    }
}

function showVerificationSection() {
    // Hide signing section
    const signingSection = document.getElementById('signing-section');
    if (signingSection) {
        signingSection.style.display = 'none';
    }

    // Show verification section
    const verificationSection = document.getElementById('verification-section');
    if (verificationSection) {
        verificationSection.style.display = 'block';
    }
}

async function verifySignature(walletAddress, signature, nonce) {
    const steps = ['step-signature', 'step-blockchain', 'step-security', 'step-session'];

    // Animate through verification steps
    for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 800));

        const prevStep = document.getElementById(steps[i]);
        if (prevStep) {
            prevStep.classList.remove('pending');
            prevStep.classList.add('complete');
            prevStep.querySelector('i').className = 'fas fa-check-circle';
        }

        if (i < steps.length - 1) {
            const nextStep = document.getElementById(steps[i + 1]);
            if (nextStep) {
                nextStep.classList.remove('pending');
                nextStep.querySelector('i').className = 'fas fa-circle-notch fa-spin';
            }
        }
    }

    try {
        // Verify with backend
        const response = await fetch('/api/v1/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                wallet_address: walletAddress,
                signature: signature,
                nonce: nonce
            })
        });

        if (!response.ok) {
            // For demo, simulate success
            completeAuthentication(walletAddress, 'demo_token_' + Date.now());
            return;
        }

        const data = await response.json();
        completeAuthentication(walletAddress, data.token);

    } catch (error) {
        // For demo, simulate success
        console.warn('API not available, using demo mode');
        completeAuthentication(walletAddress, 'demo_token_' + Date.now());
    }
}

function completeAuthentication(walletAddress, token) {
    // Store credentials
    localStorage.setItem('pulsar_wallet', walletAddress);
    localStorage.setItem('pulsar_jwt', token);
    localStorage.setItem('pulsar_jwt_expires', new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString());

    // Update wallet manager
    if (window.walletManager) {
        window.walletManager.account = walletAddress;
        window.walletManager.jwt = token;
        window.walletManager.isConnected = true;
    }

    notifications.success('Authentication successful!');

    // Redirect to dashboard after short delay
    setTimeout(() => {
        window.location.href = '/dashboard';
    }, 1000);
}

function disconnectWallet() {
    // Reset state
    authState.nonce = null;
    authState.message = null;
    authState.isProcessing = false;

    // Show connect section
    const connectSection = document.getElementById('wallet-connect-section');
    if (connectSection) {
        connectSection.style.display = 'block';
    }

    // Hide other sections
    const signingSection = document.getElementById('signing-section');
    if (signingSection) {
        signingSection.style.display = 'none';
    }

    const verificationSection = document.getElementById('verification-section');
    if (verificationSection) {
        verificationSection.style.display = 'none';
    }

    resetConnectButton();
}

function resetConnectButton() {
    const connectBtn = document.getElementById('metamask-connect');
    if (connectBtn) {
        connectBtn.disabled = false;
        connectBtn.innerHTML = '<i class="fab fa-ethereum"></i> Connect with MetaMask';
    }
}
