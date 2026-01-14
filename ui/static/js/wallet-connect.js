/**
 * PULSAR SENTINEL - MetaMask Wallet Connection
 * Handles wallet connection, authentication, and session management
 */

class WalletManager {
    constructor() {
        this.web3 = null;
        this.account = null;
        this.chainId = null;
        this.isConnected = false;
        this.jwt = null;

        // Polygon network config
        this.polygonChainId = '0x89'; // 137 in hex
        this.polygonConfig = {
            chainId: '0x89',
            chainName: 'Polygon Mainnet',
            nativeCurrency: {
                name: 'MATIC',
                symbol: 'MATIC',
                decimals: 18
            },
            rpcUrls: ['https://polygon-rpc.com/'],
            blockExplorerUrls: ['https://polygonscan.com/']
        };

        this.init();
    }

    async init() {
        // Check if already connected
        const savedAccount = localStorage.getItem('pulsar_wallet');
        const savedJwt = localStorage.getItem('pulsar_jwt');

        if (savedAccount && savedJwt) {
            this.account = savedAccount;
            this.jwt = savedJwt;
            this.isConnected = true;
            this.updateUI();
        }

        // Listen for account changes
        if (window.ethereum) {
            window.ethereum.on('accountsChanged', (accounts) => {
                if (accounts.length === 0) {
                    this.disconnect();
                } else {
                    this.account = accounts[0];
                    this.updateUI();
                }
            });

            window.ethereum.on('chainChanged', (chainId) => {
                this.chainId = chainId;
                if (chainId !== this.polygonChainId) {
                    this.showNetworkWarning();
                }
            });
        }

        // Bind connect button
        const connectBtn = document.getElementById('connect-wallet-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.connect());
        }
    }

    async connect() {
        if (!window.ethereum) {
            this.showNotification('Please install MetaMask to continue', 'error');
            window.open('https://metamask.io/download/', '_blank');
            return;
        }

        try {
            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length > 0) {
                this.account = accounts[0];
                this.web3 = new Web3(window.ethereum);

                // Check network
                this.chainId = await window.ethereum.request({ method: 'eth_chainId' });
                if (this.chainId !== this.polygonChainId) {
                    await this.switchToPolygon();
                }

                // Authenticate with backend
                await this.authenticate();

                this.isConnected = true;
                this.updateUI();
                this.showNotification('Wallet connected successfully!', 'success');
            }
        } catch (error) {
            console.error('Connection error:', error);
            this.showNotification('Failed to connect wallet', 'error');
        }
    }

    async switchToPolygon() {
        try {
            await window.ethereum.request({
                method: 'wallet_switchEthereumChain',
                params: [{ chainId: this.polygonChainId }]
            });
        } catch (switchError) {
            // Chain not added, add it
            if (switchError.code === 4902) {
                try {
                    await window.ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [this.polygonConfig]
                    });
                } catch (addError) {
                    throw new Error('Failed to add Polygon network');
                }
            } else {
                throw switchError;
            }
        }
    }

    async authenticate() {
        try {
            // Step 1: Get nonce from server
            const nonceResponse = await fetch('/api/v1/auth/nonce', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet_address: this.account })
            });

            if (!nonceResponse.ok) {
                throw new Error('Failed to get authentication nonce');
            }

            const { nonce, message } = await nonceResponse.json();

            // Step 2: Sign message with MetaMask
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, this.account]
            });

            // Step 3: Verify signature and get JWT
            const verifyResponse = await fetch('/api/v1/auth/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    wallet_address: this.account,
                    signature: signature,
                    nonce: nonce
                })
            });

            if (!verifyResponse.ok) {
                throw new Error('Signature verification failed');
            }

            const { token, expires_at } = await verifyResponse.json();

            // Store JWT
            this.jwt = token;
            localStorage.setItem('pulsar_jwt', token);
            localStorage.setItem('pulsar_wallet', this.account);
            localStorage.setItem('pulsar_jwt_expires', expires_at);

        } catch (error) {
            console.error('Authentication error:', error);
            throw error;
        }
    }

    disconnect() {
        this.account = null;
        this.jwt = null;
        this.isConnected = false;

        localStorage.removeItem('pulsar_wallet');
        localStorage.removeItem('pulsar_jwt');
        localStorage.removeItem('pulsar_jwt_expires');

        this.updateUI();
        this.showNotification('Wallet disconnected', 'info');
    }

    updateUI() {
        const walletStatus = document.getElementById('wallet-status');
        const connectBtn = document.getElementById('connect-wallet-btn');

        if (this.isConnected && this.account) {
            if (walletStatus) {
                walletStatus.className = 'wallet-status connected';
                walletStatus.innerHTML = `
                    <i class="fas fa-check-circle"></i>
                    <span>${this.shortenAddress(this.account)}</span>
                `;
            }

            if (connectBtn) {
                connectBtn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Disconnect';
                connectBtn.onclick = () => this.disconnect();
            }
        } else {
            if (walletStatus) {
                walletStatus.className = 'wallet-status disconnected';
                walletStatus.innerHTML = `
                    <i class="fas fa-plug"></i>
                    <span>Not Connected</span>
                `;
            }

            if (connectBtn) {
                connectBtn.innerHTML = '<i class="fab fa-ethereum"></i> Connect Wallet';
                connectBtn.onclick = () => this.connect();
            }
        }
    }

    shortenAddress(address) {
        return `${address.slice(0, 6)}...${address.slice(-4)}`;
    }

    showNotification(message, type = 'info') {
        if (window.notifications) {
            window.notifications.show(message, type);
        } else {
            alert(message);
        }
    }

    showNetworkWarning() {
        this.showNotification('Please switch to Polygon network', 'warning');
    }

    // Get authenticated headers for API calls
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.jwt}`,
            'Content-Type': 'application/json'
        };
    }

    // Check if JWT is valid
    isAuthenticated() {
        if (!this.jwt) return false;

        const expires = localStorage.getItem('pulsar_jwt_expires');
        if (expires && new Date(expires) < new Date()) {
            this.disconnect();
            return false;
        }

        return true;
    }

    // Make authenticated API request
    async apiRequest(endpoint, options = {}) {
        if (!this.isAuthenticated()) {
            throw new Error('Not authenticated');
        }

        const response = await fetch(endpoint, {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            }
        });

        if (response.status === 401) {
            this.disconnect();
            throw new Error('Session expired');
        }

        return response;
    }

    // Get wallet balance
    async getBalance() {
        if (!this.web3 || !this.account) return null;

        const balance = await this.web3.eth.getBalance(this.account);
        return this.web3.utils.fromWei(balance, 'ether');
    }

    // Sign a transaction
    async signTransaction(txData) {
        if (!this.account) {
            throw new Error('Wallet not connected');
        }

        return await window.ethereum.request({
            method: 'eth_sendTransaction',
            params: [{
                from: this.account,
                ...txData
            }]
        });
    }
}

// Create global instance
window.walletManager = new WalletManager();

// Export for use in other modules
window.WalletManager = WalletManager;
