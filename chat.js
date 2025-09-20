// Health Mitra Chatbot JavaScript

class HealthChatbot {
    constructor() {
        this.chatContainer = document.getElementById('chatContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.chatModal = document.getElementById('chatModal');
        this.currentLanguage = 'en';
        
        this.init();
    }
    
    init() {
        // Add event listeners
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendMessage());
        }
        
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }
        
        // Add quick action buttons to initial bot message
        this.addQuickActions();
    }
    
    addQuickActions() {
        const quickActionsHtml = `
            <div class="quick-actions mt-3">
                <button class="quick-action-btn" onclick="chatbot.sendQuickMessage('What are the symptoms of dengue?')">
                    <i class="fas fa-thermometer-half me-1"></i>Dengue Symptoms
                </button>
                <button class="quick-action-btn" onclick="chatbot.sendQuickMessage('vaccination schedule for children')">
                    <i class="fas fa-syringe me-1"></i>Vaccination Schedule
                </button>
                <button class="quick-action-btn" onclick="chatbot.sendQuickMessage('current health alerts')">
                    <i class="fas fa-exclamation-triangle me-1"></i>Health Alerts
                </button>
                <button class="quick-action-btn" onclick="chatbot.sendQuickMessage('how to prevent malaria?')">
                    <i class="fas fa-shield-alt me-1"></i>Prevention Tips
                </button>
            </div>
        `;
        
        // Add to the first bot message
        const firstBotMessage = document.querySelector('.bot-message .message-content');
        if (firstBotMessage) {
            firstBotMessage.insertAdjacentHTML('beforeend', quickActionsHtml);
        }
    }
    
    sendQuickMessage(message) {
        // Open chat modal if not already open
        if (!this.chatModal.classList.contains('show')) {
            const modal = new bootstrap.Modal(this.chatModal);
            modal.show();
        }
        
        // Set message and send
        setTimeout(() => {
            this.messageInput.value = message;
            this.sendMessage();
        }, 300);
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;
        
        // Disable input while processing
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        
        // Show loading indicator
        this.showLoading();
        
        try {
            // Send message to backend with language preference
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message: message,
                    preferred_language: this.currentLanguage 
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Add bot response to chat
            this.addMessage(data.response, 'bot', data.detected_language);
            
        } catch (error) {
            console.error('Error:', error);
            const errorMessage = `मुझे खुशी होगी आपकी मदद करने में, लेकिन अभी तकनीकी समस्या है। कृपया फिर कोशिश करें।\n\nI'd be happy to help you, but I'm experiencing a technical issue. Please try again.`;
            this.addMessage(errorMessage, 'bot');
        } finally {
            // Hide loading and re-enable input
            this.hideLoading();
            this.messageInput.disabled = false;
            this.sendButton.disabled = false;
            this.messageInput.focus();
        }
    }
    
    addMessage(content, sender, language = 'en') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}-message`;
        
        const timestamp = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        
        let messageHtml;
        if (sender === 'bot') {
            messageHtml = `
                <div class="message-content ${language === 'hi' ? 'hindi-text' : ''}">
                    <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-robot text-primary me-2"></i>
                        <strong>Health Mitra</strong>
                        <small class="text-muted ms-auto">${timestamp}</small>
                    </div>
                    <div>${this.formatMessage(content)}</div>
                </div>
            `;
        } else {
            messageHtml = `
                <div class="message-content">
                    <div class="d-flex align-items-center mb-2">
                        <i class="fas fa-user text-white me-2"></i>
                        <strong>You</strong>
                        <small class="text-white-50 ms-auto">${timestamp}</small>
                    </div>
                    <div>${content}</div>
                </div>
            `;
        }
        
        messageDiv.innerHTML = messageHtml;
        this.chatContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    formatMessage(content) {
        // Convert newlines to HTML breaks
        content = content.replace(/\n/g, '<br>');
        
        // Format lists
        content = content.replace(/^• (.+)$/gm, '<li>$1</li>');
        content = content.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Format alerts
        if (content.includes('⚠️')) {
            content = content.replace(/(⚠️.*?(?=⚠️|$))/gs, '<div class="health-alert">$1</div>');
        }
        
        return content;
    }
    
    showLoading() {
        this.loadingIndicator.classList.remove('d-none');
        this.scrollToBottom();
    }
    
    hideLoading() {
        this.loadingIndicator.classList.add('d-none');
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        }, 100);
    }
}

// Global functions for UI interactions
function selectCategory(category) {
    const modal = new bootstrap.Modal(document.getElementById('chatModal'));
    modal.show();
    
    let message = '';
    switch(category) {
        case 'vaccination':
            message = 'Show me the vaccination schedule for children';
            break;
        case 'alerts':
            message = 'What are the current health alerts and outbreaks?';
            break;
        case 'diseases':
            message = 'Tell me about common diseases and their symptoms';
            break;
    }
    
    // Send message after modal is shown
    setTimeout(() => {
        if (chatbot && message) {
            chatbot.messageInput.value = message;
            chatbot.sendMessage();
        }
    }, 300);
}

function toggleLanguage() {
    if (chatbot) {
        chatbot.currentLanguage = chatbot.currentLanguage === 'en' ? 'hi' : 'en';
        console.log('Language switched to:', chatbot.currentLanguage);
        
        // Update UI to show current language
        const langBtn = document.querySelector('[onclick="toggleLanguage()"]');
        if (langBtn) {
            langBtn.innerHTML = chatbot.currentLanguage === 'hi' ? 
                '<i class="fas fa-language me-1"></i>English' : 
                '<i class="fas fa-language me-1"></i>हिंदी';
        }
    }
}

function toggleVoice() {
    if (!chatbot) return;
    
    // Check if browser supports speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        alert('आपका ब्राउज़र वॉइस फीचर को सपोर्ट नहीं करता। / Your browser does not support voice feature.');
        return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.lang = chatbot.currentLanguage === 'hi' ? 'hi-IN' : 'en-IN';
    recognition.continuous = false;
    recognition.interimResults = false;
    
    // Update button to show recording
    const voiceBtn = document.querySelector('[onclick="toggleVoice()"]');
    const originalContent = voiceBtn.innerHTML;
    voiceBtn.innerHTML = '<i class="fas fa-stop-circle me-1 text-danger"></i>Recording...';
    voiceBtn.disabled = true;
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatbot.messageInput.value = transcript;
        
        // Restore button
        voiceBtn.innerHTML = originalContent;
        voiceBtn.disabled = false;
        
        // Auto-send the message
        setTimeout(() => {
            chatbot.sendMessage();
        }, 500);
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        voiceBtn.innerHTML = originalContent;
        voiceBtn.disabled = false;
        
        let errorMessage = 'वॉइस पहचान में त्रुटि। / Voice recognition error.';
        if (event.error === 'not-allowed') {
            errorMessage = 'माइक्रोफ़ोन की अनुमति दें। / Please allow microphone access.';
        }
        alert(errorMessage);
    };
    
    recognition.onend = () => {
        voiceBtn.innerHTML = originalContent;
        voiceBtn.disabled = false;
    };
    
    try {
        recognition.start();
    } catch (error) {
        console.error('Failed to start recognition:', error);
        voiceBtn.innerHTML = originalContent;
        voiceBtn.disabled = false;
        alert('वॉइस फीचर शुरू नहीं हो सका। / Could not start voice feature.');
    }
}

// Initialize chatbot when page loads
let chatbot;
document.addEventListener('DOMContentLoaded', function() {
    chatbot = new HealthChatbot();
    
    // Check backend health
    fetch('/health')
        .then(response => response.json())
        .then(data => {
            console.log('Backend health check:', data);
        })
        .catch(error => {
            console.warn('Backend health check failed:', error);
        });
    
    // Add modal event listeners
    const chatModal = document.getElementById('chatModal');
    if (chatModal) {
        chatModal.addEventListener('shown.bs.modal', function () {
            // Focus on input when modal is shown
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                messageInput.focus();
            }
        });
    }
});