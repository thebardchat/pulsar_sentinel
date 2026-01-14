/**
 * PULSAR SENTINEL - SHANEBRAIN AI Scripts
 */

// AI State
const aiState = {
    messages: [],
    isProcessing: false,
    currentPanel: null
};

// Initialize SHANEBRAIN Page
document.addEventListener('DOMContentLoaded', () => {
    initShanebrain();
});

function initShanebrain() {
    // Check authentication and tier
    checkAIAccess();

    // Initialize chat
    initChat();

    // Initialize analytics period selector
    initAnalyticsPeriod();
}

function checkAIAccess() {
    // SHANEBRAIN is available for Autonomous Guild tier
    // In production, check user's subscription tier
    const haAccess = true; // Demo: always grant access

    if (!haAccess) {
        notifications.warning('SHANEBRAIN AI requires Autonomous Guild subscription');
    }
}

function initChat() {
    const chatInput = document.getElementById('chat-input');

    if (chatInput) {
        // Auto-resize textarea
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        });

        // Send on Enter (but not Shift+Enter)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
}

function initAnalyticsPeriod() {
    const periodSelect = document.getElementById('analytics-period');
    if (periodSelect) {
        periodSelect.addEventListener('change', (e) => {
            loadAnalytics(e.target.value);
        });
    }
}

async function loadAnalytics(period) {
    // In production, fetch analytics data for the selected period
    notifications.info(`Loading ${period} analytics...`);
}

// Chat Functions
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input?.value.trim();

    if (!message || aiState.isProcessing) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Add user message
    addMessage(message, 'user');

    // Process with AI
    await processAIResponse(message);
}

function sendQuickMessage(message) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = message;
    }
    sendMessage();
}

function addMessage(content, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

    // Remove quick actions if they exist
    const quickActions = messagesContainer.querySelector('.quick-actions');
    if (quickActions) {
        quickActions.remove();
    }

    const message = document.createElement('div');
    message.className = `message ${sender}`;

    const avatar = sender === 'user'
        ? '<i class="fas fa-user"></i>'
        : '<i class="fas fa-brain"></i>';

    const senderName = sender === 'user' ? 'You' : 'SHANEBRAIN';
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    message.innerHTML = `
        <div class="message-avatar">
            ${avatar}
        </div>
        <div class="message-content">
            <div class="message-header">
                <span class="sender">${senderName}</span>
                <span class="time">${time}</span>
            </div>
            <div class="message-text">
                ${formatMessageContent(content)}
            </div>
        </div>
    `;

    messagesContainer.appendChild(message);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Store message
    aiState.messages.push({ sender, content, timestamp: new Date() });
}

function formatMessageContent(content) {
    // Convert markdown-like formatting
    let formatted = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');

    return `<p>${formatted}</p>`;
}

async function processAIResponse(userMessage) {
    aiState.isProcessing = true;

    // Show typing indicator
    const typingIndicator = showTypingIndicator();

    try {
        // Simulate AI processing time
        await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 1500));

        // Remove typing indicator
        typingIndicator.remove();

        // Generate response based on user message
        const response = generateAIResponse(userMessage);

        // Add AI message
        addMessage(response, 'ai');

    } catch (error) {
        typingIndicator.remove();
        notifications.error('Failed to get AI response');
        console.error('AI error:', error);
    } finally {
        aiState.isProcessing = false;
    }
}

function showTypingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');

    const indicator = document.createElement('div');
    indicator.className = 'message ai typing-indicator';
    indicator.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-brain"></i>
        </div>
        <div class="message-content">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    messagesContainer.appendChild(indicator);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return indicator;
}

function generateAIResponse(userMessage) {
    const lowerMessage = userMessage.toLowerCase();

    // Threat Score Analysis
    if (lowerMessage.includes('threat score') || lowerMessage.includes('pts')) {
        return `**Threat Score Analysis Complete**

Your current PTS (Points Toward Threat Score) is **32**, which places you in the **SAFE** tier.

**Breakdown:**
- Quantum Risk Factor: 2 (5%)
- Access Violations: 18 (20%)
- Rate Limit Violations: 8 (10%)
- Signature Failures: 4 (4%)

**Recommendations:**
1. Your quantum risk is minimal - great job using PQC encryption!
2. Consider reviewing the 18 access violations from the past 24 hours
3. Your signature chain is intact with 99.6% success rate

Would you like me to analyze specific security events in detail?`;
    }

    // PQC Status Check
    if (lowerMessage.includes('pqc') || lowerMessage.includes('quantum') || lowerMessage.includes('encryption')) {
        return `**Post-Quantum Cryptography Status**

Your system is currently protected by **ML-KEM-768** (NIST Level 3 security).

**Current Configuration:**
- Primary Encryption: ML-KEM-768 + AES-256-GCM (Hybrid)
- Key Rotation: Every 90 days
- Last Rotation: 23 days ago
- Next Rotation: In 67 days

**Quantum Threat Assessment:**
Based on current quantum computing advancement projections, your encryption will remain secure until approximately **2045** at minimum.

**Recommendation:** Your current security level is excellent for most use cases. If you're protecting highly sensitive long-term data, consider upgrading to ML-KEM-1024 (NIST Level 5).

Would you like me to initiate an upgrade to ML-KEM-1024?`;
    }

    // Mining Optimization
    if (lowerMessage.includes('mining') || lowerMessage.includes('optimize')) {
        return `**Mining Optimization Analysis**

I've analyzed your current mining configuration:

**Current Setup:**
- Hashrate: 42 TH/s
- CPU Threads: 4/16 utilized
- Mining Intensity: 75%
- Efficiency: 82%

**Optimization Recommendations:**
1. **Increase thread count** to 8 for ~40% hashrate boost
2. **Adjust intensity** to 85% during off-peak hours
3. **Enable auto-tune** for dynamic optimization

**Projected Improvements:**
- Estimated new hashrate: 58-65 TH/s
- Daily earnings increase: ~35%
- Power efficiency: +12%

Shall I apply these optimizations automatically?`;
    }

    // NFT Art Generation
    if (lowerMessage.includes('art') || lowerMessage.includes('nft') || lowerMessage.includes('generate')) {
        return `**QuantumArt Generator Ready**

I can create unique quantum-inspired artwork for your NFT collection. Here are the available styles:

**Art Styles:**
1. **Quantum Flux** - Abstract particle visualizations
2. **Neural Dreams** - AI-generated surreal landscapes
3. **Cyber Sentinel** - Futuristic guardian figures
4. **Lattice Patterns** - Mathematical beauty from PQC

**Creation Options:**
- Resolution: Up to 4K (3840x3840)
- Format: PNG, JPG, or animated GIF
- PQC Signature: Included for authenticity

To generate art, describe what you'd like to create. For example:
*"Generate a Quantum Flux style image with cyan and magenta colors representing data encryption"*

What would you like me to create?`;
    }

    // Help / General
    if (lowerMessage.includes('help') || lowerMessage.includes('what can you')) {
        return `**SHANEBRAIN Capabilities**

I'm your quantum-enhanced AI assistant for the PULSAR SENTINEL ecosystem. Here's how I can help:

**Security Analysis:**
- Real-time threat detection and scoring
- PQC encryption status monitoring
- Security event investigation
- Vulnerability scanning

**Smart Contract Auditing:**
- Automated code review
- Best practice verification
- Gas optimization suggestions

**Mining Assistance:**
- Performance optimization
- Hardware monitoring
- Pool selection advice
- Earnings projections

**NFT Creation:**
- AI-generated artwork
- Collection management
- Metadata optimization

**General Support:**
- Configuration guidance
- Troubleshooting
- Documentation lookup
- Feature explanations

What would you like help with today?`;
    }

    // Default response
    return `I understand you're asking about "${userMessage.slice(0, 50)}${userMessage.length > 50 ? '...' : ''}".

Let me help you with that. Based on my analysis of the PULSAR SENTINEL ecosystem:

**Quick Insights:**
- Your system status is **healthy**
- No critical security alerts
- All services are operational

Could you provide more details about what you'd like to accomplish? I can help with:
- Security analysis and threat scoring
- PQC encryption configuration
- Mining optimization
- NFT creation and marketplace assistance

Just let me know what you need!`;
}

// Panel Functions
function openAIPanel(panelType) {
    aiState.currentPanel = panelType;

    const panelMessages = {
        threat: 'Opening threat analysis panel. Analyze my current threat score.',
        code: 'Opening security audit panel. How do I scan a smart contract for vulnerabilities?',
        art: 'Opening art generator. What styles of NFT art can you create?',
        chat: 'Hello! How can you help me today?'
    };

    sendQuickMessage(panelMessages[panelType] || panelMessages.chat);
}

// Chat Management
function clearChat() {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;

    // Clear messages
    aiState.messages = [];

    // Reset to welcome state
    messagesContainer.innerHTML = `
        <div class="message ai">
            <div class="message-avatar">
                <i class="fas fa-brain"></i>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender">SHANEBRAIN</span>
                    <span class="time">Just now</span>
                </div>
                <div class="message-text">
                    <p>Chat cleared. How can I assist you today?</p>
                </div>
            </div>
        </div>
        <div class="quick-actions">
            <button class="quick-btn" onclick="sendQuickMessage('Analyze my threat score')">
                <i class="fas fa-chart-line"></i> Analyze Threat Score
            </button>
            <button class="quick-btn" onclick="sendQuickMessage('Check my PQC status')">
                <i class="fas fa-shield-alt"></i> Check PQC Status
            </button>
            <button class="quick-btn" onclick="sendQuickMessage('Optimize my mining settings')">
                <i class="fas fa-microchip"></i> Optimize Mining
            </button>
            <button class="quick-btn" onclick="sendQuickMessage('Generate NFT art')">
                <i class="fas fa-palette"></i> Create Art
            </button>
        </div>
    `;

    notifications.info('Chat cleared');
}

function exportChat() {
    if (aiState.messages.length === 0) {
        notifications.warning('No messages to export');
        return;
    }

    // Create export content
    let exportContent = 'SHANEBRAIN Chat Export\n';
    exportContent += '='.repeat(50) + '\n';
    exportContent += `Exported: ${new Date().toISOString()}\n\n`;

    aiState.messages.forEach(msg => {
        const sender = msg.sender === 'user' ? 'You' : 'SHANEBRAIN';
        const time = msg.timestamp.toLocaleString();
        exportContent += `[${time}] ${sender}:\n${msg.content}\n\n`;
    });

    // Download as file
    const blob = new Blob([exportContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `shanebrain-chat-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);

    notifications.success('Chat exported successfully!');
}

// Add CSS for typing indicator
const style = document.createElement('style');
style.textContent = `
    .typing-dots {
        display: flex;
        gap: 4px;
        padding: 8px 0;
    }

    .typing-dots span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--quantum-cyan);
        animation: typing-bounce 1.4s infinite ease-in-out;
    }

    .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
    .typing-dots span:nth-child(2) { animation-delay: -0.16s; }

    @keyframes typing-bounce {
        0%, 80%, 100% {
            transform: scale(0.6);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }

    .message.user .message-avatar {
        background: linear-gradient(135deg, var(--pulsar-magenta), var(--quantum-cyan));
    }
`;
document.head.appendChild(style);
