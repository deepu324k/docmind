/**
 * DocuMind — Client-side JavaScript
 * Handles file upload, chat interaction, and session management.
 */

// ════════════════════════════════════════════════════════════════
// State
// ════════════════════════════════════════════════════════════════

const state = {
    sessionId: null,
    docNames: [],
    selectedFiles: [],
    isUploading: false,
    isSending: false
};

// ════════════════════════════════════════════════════════════════
// DOM Elements
// ════════════════════════════════════════════════════════════════

const $ = id => document.getElementById(id);

const dom = {
    // Panels
    uploadPanel: $('uploadPanel'),
    chatPanel: $('chatPanel'),

    // Upload
    dropZone: $('dropZone'),
    fileInput: $('fileInput'),
    fileList: $('fileList'),
    btnUpload: $('btnUpload'),
    uploadProgress: $('uploadProgress'),
    progressFill: $('progressFill'),
    progressText: $('progressText'),

    // Chat
    chatMessages: $('chatMessages'),
    chatInput: $('chatInput'),
    btnSend: $('btnSend'),

    // Data card
    dataCard: $('dataCard'),
    dataCardBody: $('dataCardBody'),
    btnCloseCard: $('btnCloseCard'),

    // Session
    sessionInfo: $('sessionInfo'),
    sessionsList: $('sessionsList'),
    btnNewSession: $('btnNewSession'),

    // Sidebar
    sidebar: $('sidebar'),
    btnToggleSidebar: $('btnToggleSidebar'),

    // Loading
    loadingOverlay: $('loadingOverlay'),
    loadingText: $('loadingText'),

    // Suggestions
    suggestionChips: $('suggestionChips')
};

// ════════════════════════════════════════════════════════════════
// Initialize
// ════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    setupDropZone();
    setupChatInput();
    setupSidebar();
    setupSuggestions();
    loadSessions();
});

// ════════════════════════════════════════════════════════════════
// Drop Zone & File Upload
// ════════════════════════════════════════════════════════════════

function setupDropZone() {
    const dz = dom.dropZone;

    // Click to browse
    dz.addEventListener('click', () => dom.fileInput.click());

    // Drag events
    dz.addEventListener('dragover', e => {
        e.preventDefault();
        dz.classList.add('drag-over');
    });

    dz.addEventListener('dragleave', () => {
        dz.classList.remove('drag-over');
    });

    dz.addEventListener('drop', e => {
        e.preventDefault();
        dz.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    // File input change
    dom.fileInput.addEventListener('change', e => {
        handleFiles(e.target.files);
    });

    // Upload button
    dom.btnUpload.addEventListener('click', uploadFiles);
}

function handleFiles(fileList) {
    const newFiles = Array.from(fileList).filter(f =>
        f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
    );

    if (newFiles.length === 0) {
        showToast('Please select PDF files only.', 'error');
        return;
    }

    state.selectedFiles = [...state.selectedFiles, ...newFiles];
    renderFileList();
    dom.btnUpload.disabled = false;
}

function renderFileList() {
    if (state.selectedFiles.length === 0) {
        dom.fileList.style.display = 'none';
        dom.btnUpload.disabled = true;
        return;
    }

    dom.fileList.style.display = 'flex';
    dom.fileList.innerHTML = state.selectedFiles.map((file, i) => `
        <div class="file-item">
            <div class="file-icon">PDF</div>
            <div class="file-details">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
            </div>
            <button class="file-remove" onclick="removeFile(${i})" title="Remove">×</button>
        </div>
    `).join('');
}

function removeFile(index) {
    state.selectedFiles.splice(index, 1);
    renderFileList();
}

async function uploadFiles() {
    if (state.selectedFiles.length === 0 || state.isUploading) return;

    state.isUploading = true;
    dom.btnUpload.disabled = true;
    dom.uploadProgress.style.display = 'block';
    dom.progressFill.style.width = '20%';
    dom.progressText.textContent = 'Uploading and parsing documents...';

    const formData = new FormData();
    state.selectedFiles.forEach(file => formData.append('files', file));

    if (state.sessionId) {
        formData.append('session_id', state.sessionId);
    }

    try {
        dom.progressFill.style.width = '50%';
        dom.progressText.textContent = 'Generating embeddings and building index...';

        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Upload failed');
        }

        dom.progressFill.style.width = '100%';
        dom.progressText.textContent = data.message;

        // Update state
        state.sessionId = data.session_id;
        state.docNames = data.doc_names;
        state.selectedFiles = [];

        // Show table data if available
        if (data.table_data) {
            showDataCard(data.table_data);
        }

        // Switch to chat view
        setTimeout(() => {
            showChatPanel();
            loadSessions();
        }, 800);

    } catch (err) {
        showToast(err.message, 'error');
        dom.progressFill.style.width = '0%';
        dom.uploadProgress.style.display = 'none';
        dom.btnUpload.disabled = false;
    } finally {
        state.isUploading = false;
    }
}

// ════════════════════════════════════════════════════════════════
// Chat
// ════════════════════════════════════════════════════════════════

function setupChatInput() {
    const input = dom.chatInput;

    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        dom.btnSend.disabled = input.value.trim() === '';
    });

    // Enter to send (Shift+Enter for newline)
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    dom.btnSend.addEventListener('click', sendMessage);
}

function setupSuggestions() {
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.dataset.question;
            dom.chatInput.value = question;
            dom.btnSend.disabled = false;
            sendMessage();
        });
    });
}

async function sendMessage() {
    const question = dom.chatInput.value.trim();
    if (!question || state.isSending || !state.sessionId) return;

    state.isSending = true;
    dom.btnSend.disabled = true;

    // Clear welcome message
    const welcome = dom.chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();

    // Add user message
    addMessage('user', question);

    // Clear input
    dom.chatInput.value = '';
    dom.chatInput.style.height = 'auto';

    // Show typing indicator
    const typingId = showTyping();

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                question: question
            })
        });

        const data = await response.json();
        removeTyping(typingId);

        if (!response.ok) {
            throw new Error(data.error || 'Failed to get answer');
        }

        addMessage('assistant', data.answer, data.sources);

    } catch (err) {
        removeTyping(typingId);
        addMessage('assistant', `Sorry, an error occurred: ${err.message}`);
        showToast(err.message, 'error');
    } finally {
        state.isSending = false;
        dom.btnSend.disabled = dom.chatInput.value.trim() === '';
    }
}

function addMessage(role, content, sources = []) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const avatarText = role === 'user' ? 'U' : '✦';
    const formattedContent = formatMarkdown(content);

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                ${sources.map(s => `
                    <span class="source-badge">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                        </svg>
                        ${escapeHtml(s.doc)} · p.${s.page}
                    </span>
                `).join('')}
            </div>
        `;
    }

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatarText}</div>
        <div class="message-content">
            <div class="message-bubble">${formattedContent}</div>
            ${sourcesHtml}
        </div>
    `;

    dom.chatMessages.appendChild(msgDiv);
    scrollToBottom();
}

function showTyping() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = id;
    div.innerHTML = `
        <div class="message-avatar">✦</div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    dom.chatMessages.appendChild(div);
    scrollToBottom();
    return id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function scrollToBottom() {
    dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

// ════════════════════════════════════════════════════════════════
// Data Card (Structured Extraction)
// ════════════════════════════════════════════════════════════════

function showDataCard(tableData) {
    let html = '';

    for (const [docName, data] of Object.entries(tableData)) {
        if (data.structured_fields) {
            html += `<div style="margin-bottom:12px; font-size:0.8rem; font-weight:600; color:var(--success);">${escapeHtml(docName)}</div>`;
            for (const [key, value] of Object.entries(data.structured_fields)) {
                html += `
                    <div class="data-field">
                        <span class="data-field-label">${escapeHtml(key)}</span>
                        <span class="data-field-value">${escapeHtml(value)}</span>
                    </div>
                `;
            }
        }
    }

    if (html) {
        dom.dataCardBody.innerHTML = html;
        dom.dataCard.style.display = 'block';
    }

    dom.btnCloseCard.addEventListener('click', () => {
        dom.dataCard.style.display = 'none';
    });
}

// ════════════════════════════════════════════════════════════════
// Session Management
// ════════════════════════════════════════════════════════════════

function showChatPanel() {
    dom.uploadPanel.style.display = 'none';
    dom.chatPanel.style.display = 'flex';

    // Update session info
    dom.sessionInfo.innerHTML = `
        <span class="session-label">Session active</span>
        <div class="session-docs">
            ${state.docNames.map(n => `<span class="doc-badge">${escapeHtml(n)}</span>`).join('')}
        </div>
    `;

    dom.chatInput.focus();
}

function showUploadPanel() {
    dom.uploadPanel.style.display = 'flex';
    dom.chatPanel.style.display = 'none';
    dom.uploadProgress.style.display = 'none';
    dom.progressFill.style.width = '0%';
    dom.fileList.style.display = 'none';
    dom.btnUpload.disabled = true;
    state.selectedFiles = [];

    dom.sessionInfo.innerHTML = '<span class="session-label">No documents loaded</span>';
}

dom.btnNewSession.addEventListener('click', () => {
    state.sessionId = null;
    state.docNames = [];
    showUploadPanel();

    // Reset chat
    dom.chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 16v-4"/>
                    <path d="M12 8h.01"/>
                </svg>
            </div>
            <h2>Documents loaded!</h2>
            <p>Ask any question about your uploaded documents. I'll find the relevant sections and provide cited answers.</p>
            <div class="suggestion-chips" id="suggestionChips">
                <button class="chip" data-question="What is this document about?">What is this document about?</button>
                <button class="chip" data-question="Summarize the key points">Summarize the key points</button>
                <button class="chip" data-question="What are the main conclusions?">What are the main conclusions?</button>
            </div>
        </div>
    `;
    setupSuggestions();
    dom.dataCard.style.display = 'none';
});

async function loadSessions() {
    try {
        const res = await fetch('/sessions');
        const data = await res.json();

        const listEl = dom.sessionsList;
        // Keep label, clear sessions
        const label = listEl.querySelector('.sessions-label');
        listEl.innerHTML = '';
        listEl.appendChild(label);

        if (data.sessions && data.sessions.length > 0) {
            data.sessions.forEach(session => {
                const item = document.createElement('div');
                item.className = 'session-item' + (session.id === state.sessionId ? ' active' : '');
                item.innerHTML = `
                    <div class="session-item-name">${escapeHtml(session.doc_names.join(', '))}</div>
                    <div class="session-item-date">${formatDate(session.created_at)}</div>
                `;
                item.addEventListener('click', () => loadSession(session.id));
                listEl.appendChild(item);
            });
        }
    } catch (err) {
        console.error('Failed to load sessions:', err);
    }
}

async function loadSession(sessionId) {
    try {
        showLoading('Loading session...');

        const res = await fetch(`/history/${sessionId}`);
        const data = await res.json();

        if (!res.ok) throw new Error(data.error);

        state.sessionId = sessionId;
        state.docNames = data.session.doc_names;

        // Show chat panel
        showChatPanel();

        // Clear and re-populate messages
        dom.chatMessages.innerHTML = '';

        if (data.history.length === 0) {
            dom.chatMessages.innerHTML = `
                <div class="welcome-message">
                    <div class="welcome-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
                        </svg>
                    </div>
                    <h2>Documents loaded!</h2>
                    <p>Ask any question about your uploaded documents.</p>
                    <div class="suggestion-chips">
                        <button class="chip" data-question="What is this document about?">What is this document about?</button>
                        <button class="chip" data-question="Summarize the key points">Summarize the key points</button>
                    </div>
                </div>
            `;
            setupSuggestions();
        } else {
            data.history.forEach(msg => {
                addMessage('user', msg.question);
                addMessage('assistant', msg.answer, msg.sources);
            });
        }

        // Show data card if available
        if (data.session.table_data) {
            showDataCard(data.session.table_data);
        }

        // Update sidebar active state
        document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
        hideLoading();

        loadSessions();

    } catch (err) {
        hideLoading();
        showToast(err.message, 'error');
    }
}

// ════════════════════════════════════════════════════════════════
// Sidebar
// ════════════════════════════════════════════════════════════════

function setupSidebar() {
    dom.btnToggleSidebar.addEventListener('click', () => {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            dom.sidebar.classList.toggle('open');
        } else {
            dom.sidebar.classList.toggle('collapsed');
        }
    });

    // Close sidebar on mobile when clicking outside
    document.addEventListener('click', e => {
        if (window.innerWidth <= 768 && dom.sidebar.classList.contains('open')) {
            if (!dom.sidebar.contains(e.target) && !dom.btnToggleSidebar.contains(e.target)) {
                dom.sidebar.classList.remove('open');
            }
        }
    });
}

// ════════════════════════════════════════════════════════════════
// Utilities
// ════════════════════════════════════════════════════════════════

function formatMarkdown(text) {
    if (!text) return '';

    // Basic markdown rendering
    let html = escapeHtml(text);

    // Bold: **text** or __text__
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');

    // Italic: *text* or _text_
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Code: `text`
    html = html.replace(/`(.*?)`/g, '<code style="background:rgba(108,92,231,0.15);padding:2px 6px;border-radius:4px;font-size:0.85em;">$1</code>');

    // Line breaks
    html = html.replace(/\n/g, '<br>');

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateStr) {
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;

        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
        if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
        return date.toLocaleDateString();
    } catch {
        return dateStr || '';
    }
}

function showLoading(text = 'Processing...') {
    dom.loadingText.textContent = text;
    dom.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    dom.loadingOverlay.style.display = 'none';
}

function showToast(message, type = 'error') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
