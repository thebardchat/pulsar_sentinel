/**
 * PULSAR SENTINEL - Marketplace Scripts
 */

// Marketplace State
const marketplaceState = {
    items: [],
    filters: {
        category: '',
        sort: 'recent',
        price: ''
    },
    cart: []
};

// Initialize Marketplace
document.addEventListener('DOMContentLoaded', () => {
    initMarketplace();
});

function initMarketplace() {
    // Initialize tab navigation
    initTabs();

    // Initialize filters
    initFilters();

    // Initialize search
    initSearch();

    // Load marketplace data
    loadMarketplaceData();
}

function initTabs() {
    const tabs = document.querySelectorAll('.tab-btn');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            const tabType = this.dataset.tab;
            filterByTab(tabType);
        });
    });
}

function initFilters() {
    const categorySelect = document.getElementById('filter-category');
    const sortSelect = document.getElementById('filter-sort');
    const priceSelect = document.getElementById('filter-price');

    [categorySelect, sortSelect, priceSelect].forEach(select => {
        if (select) {
            select.addEventListener('change', applyFilters);
        }
    });
}

function initSearch() {
    const searchInput = document.getElementById('marketplace-search');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchItems(e.target.value);
            }, 300);
        });
    }
}

async function loadMarketplaceData() {
    // In production, fetch from API
    // const response = await fetch('/api/v1/marketplace/items');
}

function filterByTab(tabType) {
    const cards = document.querySelectorAll('.nft-card');

    cards.forEach(card => {
        if (tabType === 'all') {
            card.style.display = '';
        } else {
            // Filter based on badge or collection
            const badges = card.querySelectorAll('.badge');
            let matches = false;

            badges.forEach(badge => {
                const text = badge.textContent.toLowerCase();
                if (tabType === 'nfts' && text.includes('pqc')) matches = true;
                if (tabType === 'mints' && text.includes('mint')) matches = true;
                if (tabType === 'security' && text.includes('security')) matches = true;
                if (tabType === 'domains' && text.includes('domain')) matches = true;
            });

            card.style.display = matches ? '' : 'none';
        }
    });
}

function applyFilters() {
    marketplaceState.filters.category = document.getElementById('filter-category')?.value || '';
    marketplaceState.filters.sort = document.getElementById('filter-sort')?.value || 'recent';
    marketplaceState.filters.price = document.getElementById('filter-price')?.value || '';

    // In production, re-fetch with filters or sort client-side
    notifications.info('Filters applied');
}

function searchItems(query) {
    if (!query) {
        document.querySelectorAll('.nft-card').forEach(card => {
            card.style.display = '';
        });
        return;
    }

    const lowerQuery = query.toLowerCase();
    document.querySelectorAll('.nft-card').forEach(card => {
        const name = card.querySelector('.nft-name')?.textContent.toLowerCase() || '';
        const collection = card.querySelector('.nft-collection')?.textContent.toLowerCase() || '';

        if (name.includes(lowerQuery) || collection.includes(lowerQuery)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

// View Functions
function viewCollection(collectionId) {
    notifications.info(`Viewing collection: ${collectionId}`);
    // In production, navigate to collection page
}

function viewNFT(nftId) {
    notifications.info(`Viewing NFT: ${nftId}`);
    // In production, show NFT detail modal or navigate to page
}

// Create Modal Functions
function showCreateModal() {
    if (!window.walletManager?.isAuthenticated()) {
        notifications.warning('Please connect your wallet first');
        return;
    }

    const modal = document.getElementById('create-modal');
    if (modal) {
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('show'), 10);
    }

    // Initialize create tabs
    initCreateTabs();

    // Initialize upload zone
    initUploadZone();
}

function hideCreateModal() {
    const modal = document.getElementById('create-modal');
    if (modal) {
        modal.classList.remove('show');
        setTimeout(() => modal.style.display = 'none', 300);
    }
}

function initCreateTabs() {
    const tabs = document.querySelectorAll('.create-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Update form based on type
            const type = this.dataset.type;
            updateCreateForm(type);
        });
    });
}

function updateCreateForm(type) {
    // Adjust form based on NFT, MINT, or Collection type
    const royaltiesGroup = document.querySelector('.form-group:has(#nft-royalties)');

    if (type === 'collection') {
        if (royaltiesGroup) royaltiesGroup.style.display = 'none';
    } else {
        if (royaltiesGroup) royaltiesGroup.style.display = '';
    }
}

function initUploadZone() {
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('nft-file');

    if (!uploadZone || !fileInput) return;

    uploadZone.addEventListener('click', () => fileInput.click());

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });
}

function handleFileUpload(file) {
    // Validate file
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = ['image/png', 'image/jpeg', 'image/gif', 'video/mp4'];

    if (!allowedTypes.includes(file.type)) {
        notifications.error('Invalid file type. Please upload PNG, JPG, GIF, or MP4.');
        return;
    }

    if (file.size > maxSize) {
        notifications.error('File too large. Maximum size is 100MB.');
        return;
    }

    // Update upload zone
    const uploadZone = document.getElementById('upload-zone');
    if (uploadZone) {
        uploadZone.innerHTML = `
            <i class="fas fa-check-circle" style="color: var(--matrix-green);"></i>
            <p>${file.name}</p>
            <span>${(file.size / 1024 / 1024).toFixed(2)} MB</span>
        `;
    }

    notifications.success('File uploaded successfully!');
}

async function createNFT() {
    // Gather form data
    const name = document.getElementById('nft-name')?.value;
    const description = document.getElementById('nft-description')?.value;
    const price = document.getElementById('nft-price')?.value;
    const collection = document.getElementById('nft-collection')?.value;
    const category = document.getElementById('nft-category')?.value;
    const royalties = document.getElementById('nft-royalties')?.value || 10;
    const pqcSign = document.getElementById('pqc-sign')?.checked ?? true;

    // Validation
    if (!name) {
        notifications.error('Please enter a name for your item');
        return;
    }

    if (!price || parseFloat(price) <= 0) {
        notifications.error('Please enter a valid price');
        return;
    }

    const loading = notifications.loading('Creating your NFT...');

    try {
        // Simulate NFT creation
        await new Promise(resolve => setTimeout(resolve, 2000));

        if (pqcSign) {
            loading.update('Signing with ML-KEM-768...');
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        loading.update('Minting on blockchain...');
        await new Promise(resolve => setTimeout(resolve, 1500));

        loading.success('NFT created successfully!');
        hideCreateModal();

        // Clear form
        document.getElementById('nft-name').value = '';
        document.getElementById('nft-description').value = '';
        document.getElementById('nft-price').value = '';

    } catch (error) {
        loading.error('Failed to create NFT');
        console.error('NFT creation error:', error);
    }
}

// Buy NFT
async function buyNFT(nftId, price) {
    if (!window.walletManager?.isAuthenticated()) {
        notifications.warning('Please connect your wallet first');
        return;
    }

    const confirmed = await notifications.confirm(
        `Purchase this item for ${price} PLS?`,
        { title: 'Confirm Purchase' }
    );

    if (!confirmed) return;

    const loading = notifications.loading('Processing purchase...');

    try {
        await new Promise(resolve => setTimeout(resolve, 2000));

        loading.success('Purchase successful! NFT added to your collection.');

    } catch (error) {
        loading.error('Purchase failed');
        console.error('Purchase error:', error);
    }
}

// Handle Buy Now button clicks
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('btn-buy') || e.target.closest('.btn-buy')) {
        e.stopPropagation();

        const card = e.target.closest('.nft-card');
        if (card) {
            const priceText = card.querySelector('.price-value')?.textContent || '0';
            const price = parseFloat(priceText.replace(/[^0-9.]/g, ''));
            const name = card.querySelector('.nft-name')?.textContent || 'NFT';

            buyNFT(name, price);
        }
    }
});
