// Audio player management
let currentAudio = null;
let currentPage = 1;
const itemsPerPage = 20;
let totalItems = 0;
let currentUser = null;
let userAnnotations = {};
let lexiconWords = [];

// User management
function setUserName() {
    const nameInput = document.getElementById('user-name-input');
    const name = nameInput.value.trim();
    
    if (!name) {
        alert('Please enter your name');
        return;
    }
    
    currentUser = name;
    localStorage.setItem('annotator_name', name);
    
    document.getElementById('user-login').style.display = 'none';
    document.getElementById('user-info').style.display = 'flex';
    document.getElementById('current-user').textContent = name;
    
    loadUserAnnotations();
}

function logoutUser() {
    currentUser = null;
    userAnnotations = {};
    localStorage.removeItem('annotator_name');
    
    document.getElementById('user-login').style.display = 'flex';
    document.getElementById('user-info').style.display = 'none';
    document.getElementById('user-name-input').value = '';
    
    loadCandidates();
}

async function loadUserAnnotations() {
    if (!currentUser) return;
    
    try {
        const response = await fetch(`/api/annotations/${encodeURIComponent(currentUser)}`);
        userAnnotations = await response.json();
        document.getElementById('user-annotation-count').textContent = Object.keys(userAnnotations).length;
        loadCandidates();
    } catch (error) {
        console.error('Error loading annotations:', error);
    }
}

function exportAnnotations() {
    if (!currentUser) {
        alert('Please log in first');
        return;
    }
    window.location.href = `/api/export-annotations/${encodeURIComponent(currentUser)}`;
}

async function saveAnnotation(candidateId, doc, aSentId, bSentId, vote) {
    if (!currentUser) {
        alert('Please enter your name first to start annotating');
        return;
    }
    
    try {
        const response = await fetch('/api/annotate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_name: currentUser,
                candidate_id: candidateId,
                doc: doc,
                a_sent_id: aSentId,
                b_sent_id: bSentId,
                vote: vote
            })
        });
        
        if (response.ok) {
            userAnnotations[candidateId] = vote;
            document.getElementById('user-annotation-count').textContent = Object.keys(userAnnotations).length;
            loadCandidates();
        }
    } catch (error) {
        console.error('Error saving annotation:', error);
        alert('Failed to save annotation');
    }
}

function playAudio(url, button) {
    // Stop current audio if playing
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    // Create and play new audio
    currentAudio = new Audio(url);
    
    // Update button while playing
    const originalText = button.textContent;
    button.textContent = '⏸';
    button.style.background = '#ef4444';

    currentAudio.play();

    // Reset button when finished
    currentAudio.onended = () => {
        button.textContent = originalText;
        button.style.background = '';
        currentAudio = null;
    };

    // Handle errors
    currentAudio.onerror = () => {
        button.textContent = '✗';
        button.style.background = '#6b7280';
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = '';
        }, 2000);
        currentAudio = null;
    };
}

function createCandidateCard(candidate) {
    const card = document.createElement('div');
    card.className = `candidate-card confidence-${candidate.confidence}`;
    
    // Create warning flags
    const warnings = [];
    if (candidate.B_has_content === '1') {
        warnings.push('<span class="warning-flag flag-content">Has content</span>');
    }
    if (candidate.B_is_question === '1') {
        warnings.push('<span class="warning-flag flag-question">Is question</span>');
    }
    if (candidate.B_after_question === '1') {
        warnings.push('<span class="warning-flag flag-after-q">After question</span>');
    }
    if (candidate.A_looks_like_backchannel === '1') {
        warnings.push('<span class="warning-flag flag-a-backchannel">A is backchannel</span>');
    }
    
    const warningsHtml = warnings.length > 0 
        ? `<div class="warnings">${warnings.join('')}</div>` 
        : '';
    
    // Highlight attachment point in A's text
    let aTextDisplay = candidate.A_text;
    if (candidate.attach_word && candidate.A_tokens && candidate.attach_token_id) {
        const tokens = candidate.A_tokens.split(' ');
        const tokenIdx = parseInt(candidate.attach_token_id) - 1;
        
        if (tokenIdx >= 0 && tokenIdx < tokens.length) {
            const attachWord = tokens[tokenIdx];
            // Escape special regex characters and match word with optional punctuation
            const escapedWord = attachWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            // Match the word even if it has punctuation attached
            aTextDisplay = candidate.A_text.replace(
                new RegExp(`(${escapedWord})`, 'gi'),
                `<strong class="attach-word">$1</strong>`
            );
        }
    }
    
    card.innerHTML = `
        <div class="card-header">
            <span class="confidence-badge confidence-${candidate.confidence}">${candidate.confidence}</span>
            <span class="score-badge">Score: ${candidate.confidence_score}</span>
        </div>
        
        <div class="utterance">
            <div class="utterance-label">A (Speaker: ${candidate.A_speaker})</div>
            <div class="utterance-content">
                <button class="play-btn" onclick="playAudio('${candidate.A_sound_url}', this)" title="Play A">▶</button>
                <div class="utterance-text">${aTextDisplay}</div>
            </div>
        </div>
        
        <div class="utterance">
            <div class="utterance-label">B (Speaker: ${candidate.B_speaker}) - CANDIDATE BACKCHANNEL</div>
            <div class="utterance-content">
                <button class="play-btn" onclick="playAudio('${candidate.B_sound_url}', this)" title="Play B">▶</button>
                <div class="utterance-text main">${candidate.B_text}</div>
            </div>
        </div>
        
        ${warningsHtml}
        
        <div class="metadata">
            <div class="meta-item">
                <strong>Tokens:</strong> ${candidate.B_token_count}
            </div>
            <div class="meta-item">
                <strong>Doc:</strong> ${candidate.doc}
            </div>
            <div class="meta-item" style="flex: 1 1 100%;">
                <strong>Why:</strong> ${candidate.why_candidate}
            </div>
        </div>
    `;
    
    // Add annotation buttons if user is logged in
    if (currentUser) {
        const candidateId = `${candidate.doc}_${candidate.A_sent_id}_${candidate.B_sent_id}`;
        const userVote = userAnnotations[candidateId];
        
        const annotationSection = document.createElement('div');
        annotationSection.className = 'annotation-section';
        annotationSection.innerHTML = `
            <div class="annotation-buttons">
                <button class="annotation-btn annotation-yes ${userVote === 'yes' ? 'active' : ''}" 
                        onclick="saveAnnotation('${candidateId}', '${candidate.doc}', '${candidate.A_sent_id}', '${candidate.B_sent_id}', 'yes')"
                        title="Mark as backchannel">
                    ✓
                </button>
                <button class="annotation-btn annotation-no ${userVote === 'no' ? 'active' : ''}" 
                        onclick="saveAnnotation('${candidateId}', '${candidate.doc}', '${candidate.A_sent_id}', '${candidate.B_sent_id}', 'no')"
                        title="Not a backchannel">
                    ✗
                </button>
            </div>
        `;
        card.appendChild(annotationSection);
    }
    
    return card;
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        document.getElementById('stat-total').textContent = stats.total;
        document.getElementById('stat-high').textContent = stats.HIGH;
        document.getElementById('stat-medium').textContent = stats.MEDIUM;
        document.getElementById('stat-low').textContent = stats.LOW;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadDocuments() {
    try {
        const response = await fetch('/api/documents');
        const docs = await response.json();
        
        const select = document.getElementById('filter-doc');
        // Keep the "All" option and add documents
        docs.forEach(doc => {
            const option = document.createElement('option');
            option.value = doc;
            option.textContent = doc;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

async function loadLexicon() {
    try {
        const response = await fetch('/api/lexicon');
        lexiconWords = await response.json();
        
        // Populate lexicon select
        const select = document.getElementById('filter-lexicon');
        select.innerHTML = '<option value="">Lexicon word: All</option>';
        lexiconWords.forEach(word => {
            const option = document.createElement('option');
            option.value = word;
            option.textContent = word;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading lexicon:', error);
    }
}

function getFilterParams() {
    const params = new URLSearchParams();
    
    const confidence = document.getElementById('filter-confidence').value;
    const sort = document.getElementById('filter-sort') ? document.getElementById('filter-sort').value : '';
    const minTokens = document.getElementById('filter-min-tokens').value;
    const maxTokens = document.getElementById('filter-max-tokens').value;
    const minScore = document.getElementById('filter-min-score').value;
    const maxScore = document.getElementById('filter-max-score').value;
    const search = document.getElementById('filter-search').value;
    const doc = document.getElementById('filter-doc').value;
    const continuation = document.getElementById('filter-continuation').value;
    const hasContent = document.getElementById('filter-has-content').value;
    const isQuestion = document.getElementById('filter-is-question').value;
    const afterQuestion = document.getElementById('filter-after-question').value;
    const aBackchannel = document.getElementById('filter-a-backchannel').value;
    const lexicon = document.getElementById('filter-lexicon').value;
    
    if (confidence) params.append('confidence', confidence);
    if (sort) params.append('sort', sort);
    if (minTokens) params.append('min_tokens', minTokens);
    if (maxTokens) params.append('max_tokens', maxTokens);
    if (minScore) params.append('min_score', minScore);
    if (maxScore) params.append('max_score', maxScore);
    if (search) params.append('search', search);
    if (doc) params.append('doc', doc);
    if (continuation) params.append('continuation', continuation);
    if (hasContent) params.append('has_content', hasContent);
    if (isQuestion) params.append('is_question', isQuestion);
    if (afterQuestion) params.append('after_question', afterQuestion);
    if (aBackchannel) params.append('a_backchannel', aBackchannel);
    if (lexicon) params.append('lexicon', lexicon);
    
    return params;
}

async function loadCandidates() {
    const container = document.getElementById('candidates-list');
    container.classList.add('empty');
    container.innerHTML = '<div class="loading">Loading candidates...</div>';
    
    // Build query string
    const params = getFilterParams();
    params.append('page', currentPage);
    params.append('per_page', itemsPerPage);
    
    try {
        const response = await fetch(`/api/candidates?${params}`);
        const data = await response.json();
        
        container.innerHTML = '';
        
        if (data.candidates.length === 0) {
            container.classList.add('empty');
            document.getElementById('results-count').textContent = 'No results';
            document.getElementById('pagination').style.display = 'none';
            return;
        }
        
        container.classList.remove('empty');
        totalItems = data.total;
        const totalPages = Math.ceil(totalItems / itemsPerPage);
        
        data.candidates.forEach(candidate => {
            const card = createCandidateCard(candidate);
            container.appendChild(card);
        });
        
        // Update pagination
        document.getElementById('current-page').textContent = currentPage;
        document.getElementById('total-pages').textContent = totalPages;
        document.getElementById('btn-first').disabled = currentPage === 1;
        document.getElementById('btn-prev').disabled = currentPage === 1;
        document.getElementById('btn-next').disabled = currentPage === totalPages;
        document.getElementById('btn-last').disabled = currentPage === totalPages;
        document.getElementById('pagination').style.display = 'flex';
        
        const start = (currentPage - 1) * itemsPerPage + 1;
        const end = Math.min(currentPage * itemsPerPage, totalItems);
        document.getElementById('results-count').textContent = 
            `Showing ${start}-${end} of ${totalItems} candidate${totalItems !== 1 ? 's' : ''}`;
            
    } catch (error) {
        console.error('Error loading candidates:', error);
        container.innerHTML = '<div class="empty-state"><h2>Error loading candidates</h2></div>';
    }
}

function resetFilters() {
    document.getElementById('filter-confidence').value = '';
    if (document.getElementById('filter-sort')) document.getElementById('filter-sort').value = '';
    document.getElementById('filter-min-tokens').value = '';
    document.getElementById('filter-max-tokens').value = '';
    document.getElementById('filter-min-score').value = '';
    document.getElementById('filter-max-score').value = '';
    document.getElementById('filter-search').value = '';
    document.getElementById('filter-doc').value = '';
    document.getElementById('filter-continuation').value = '';
    document.getElementById('filter-has-content').value = '';
    document.getElementById('filter-is-question').value = '';
    document.getElementById('filter-after-question').value = '';
    document.getElementById('filter-a-backchannel').value = '';
    document.getElementById('filter-lexicon').value = '';
    currentPage = 1;
    loadCandidates();
}

function firstPage() {
    if (currentPage !== 1) {
        currentPage = 1;
        loadCandidates();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        loadCandidates();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function nextPage() {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        loadCandidates();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function lastPage() {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    if (currentPage !== totalPages) {
        currentPage = totalPages;
        loadCandidates();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function exportToCSV() {
    const params = getFilterParams();
    window.location.href = `/api/export?${params}`;
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is already logged in
    const savedUser = localStorage.getItem('annotator_name');
    if (savedUser) {
        currentUser = savedUser;
        document.getElementById('user-login').style.display = 'none';
        document.getElementById('user-info').style.display = 'flex';
        document.getElementById('current-user').textContent = savedUser;
        loadUserAnnotations();
    }
    
    loadStats();
    loadDocuments();
    loadLexicon();
    loadCandidates();
    
    // Filter change listeners - reset to page 1 when filters change
    const resetPageAndLoad = () => {
        currentPage = 1;
        loadCandidates();
    };
    
    document.getElementById('filter-confidence').addEventListener('change', resetPageAndLoad);
    if (document.getElementById('filter-sort')) {
        document.getElementById('filter-sort').addEventListener('change', resetPageAndLoad);
    }
    document.getElementById('filter-min-tokens').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-max-tokens').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-min-score').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-max-score').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-continuation').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-has-content').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-is-question').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-after-question').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-a-backchannel').addEventListener('change', resetPageAndLoad);
    document.getElementById('filter-lexicon').addEventListener('change', resetPageAndLoad);
    
    // Search with debounce
    let searchTimeout;
    document.getElementById('filter-search').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentPage = 1;
            loadCandidates();
        }, 500);
    });
    
    document.getElementById('filter-doc').addEventListener('change', resetPageAndLoad);
    
    document.getElementById('btn-reset').addEventListener('click', resetFilters);
    document.getElementById('btn-export').addEventListener('click', exportToCSV);
});
