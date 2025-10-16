// SmartSupport v2.2.0 - Minimalist

let originalResponse = '';
let currentQuery = ''; // Для feedback

// =============================================================================
// INITIALIZATION
// =============================================================================

window.onload = async function() {
    try {
        const response = await fetch('/api/version');
        const data = await response.json();
        document.getElementById('appVersion').textContent = `v${data.version}`;
    } catch (error) {
        console.error('Failed to load version:', error);
        document.getElementById('appVersion').textContent = 'v2.2.0';
    }
    
    // Enter key to submit
    document.getElementById('ticketInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            processTicket();
        }
    });
    
    // Глобальные горячие клавиши
    document.addEventListener('keydown', handleGlobalHotkeys);
};

async function initializeSystem() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    
    if (!apiKey) {
        showError('Введите API ключ', 'initError');
        return;
    }
    
    document.getElementById('initLoading').classList.add('active');
    document.getElementById('initBtn').disabled = true;
    document.getElementById('initError').textContent = '';
    
    try {
        const response = await fetch('/api/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка инициализации');
        }
        
        document.getElementById('articlesCount').textContent = data.message;
        document.getElementById('initSuccess').style.display = 'block';
        
        setTimeout(() => {
            document.getElementById('apiModal').classList.remove('active');
        }, 1500);
        
    } catch (error) {
        showError(error.message, 'initError');
        document.getElementById('initBtn').disabled = false;
    } finally {
        document.getElementById('initLoading').classList.remove('active');
    }
}

// =============================================================================
// HOTKEYS
// =============================================================================

function handleGlobalHotkeys(e) {
    // Проверяем, что мы не в поле ввода API ключа
    if (document.getElementById('apiModal').classList.contains('active')) {
        return;
    }
    
    // Ctrl+V - вставка в поле вопроса
    if (e.ctrlKey && e.key === 'v' && !e.shiftKey && !e.altKey) {
        // Проверяем, что фокус не на поле ответа
        const activeElement = document.activeElement;
        if (activeElement && activeElement.id === 'suggestedResponse') {
            return; // Не перехватываем, если фокус на поле ответа
        }
        
        e.preventDefault();
        pasteToQuestion();
        return;
    }
    
    // Ctrl+C - копирование ответа
    if (e.ctrlKey && e.key === 'c' && !e.shiftKey && !e.altKey) {
        // Проверяем, что фокус не на поле ответа (там своя логика копирования)
        const activeElement = document.activeElement;
        if (activeElement && activeElement.id === 'suggestedResponse') {
            return; // Не перехватываем, если фокус на поле ответа
        }
        
        e.preventDefault();
        copyResponse();
        return;
    }
    
    // Ctrl+Enter - обработка тикета
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        processTicket();
        return;
    }
}

async function pasteToQuestion() {
    try {
        const text = await navigator.clipboard.readText();
        if (text.trim()) {
            const ticketInput = document.getElementById('ticketInput');
            ticketInput.value = text.trim();
            ticketInput.focus();
            showSuccess('Текст вставлен в поле вопроса');
        } else {
            showError('Буфер обмена пуст');
        }
    } catch (err) {
        showError('Не удалось прочитать буфер обмена');
    }
}

// =============================================================================
// MAIN PROCESSING
// =============================================================================

async function processTicket() {
    const ticketText = document.getElementById('ticketInput').value.trim();
    
    if (!ticketText) {
        showError('Введите текст обращения');
        return;
    }
    
    document.getElementById('loading').classList.add('active');
    document.getElementById('processBtn').disabled = true;
    document.getElementById('errorMessage').classList.remove('active');
    
    try {
        const response = await fetch('/api/process_ticket', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticket_text: ticketText })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            if (response.status === 429 || data.error === 'rate_limit') {
                throw new Error(`API перегружен. Попытка ${data.attempts || 1}. Подождите минуту.`);
            }
            throw new Error(data.error || 'Ошибка обработки');
        }
        
        // Сохраняем текущий запрос для feedback
        currentQuery = ticketText;
        
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        document.getElementById('loading').classList.remove('active');
        document.getElementById('processBtn').disabled = false;
    }
}

// =============================================================================
// DISPLAY RESULTS
// =============================================================================

function displayResults(data) {
    // Classification
    document.getElementById('category').textContent = data.classification.category;
    document.getElementById('classConfidence').textContent = data.classification.confidence;
    document.getElementById('classConfidence').className = 'badge ' + getConfidenceClass(data.classification.confidence);
    
    // Subcategory
    const subcategoryContainer = document.getElementById('subcategory');
    if (data.classification.subcategories && data.classification.subcategories.length > 0) {
        // Показываем список подкатегорий одна под другой
        subcategoryContainer.innerHTML = '';
        subcategoryContainer.className = 'subcategories-list';
        data.classification.subcategories.forEach(subcat => {
            const subcatItem = document.createElement('div');
            subcatItem.className = 'subcategory-item';
            subcatItem.textContent = subcat;
            subcategoryContainer.appendChild(subcatItem);
        });
    } else if (data.classification.subcategory && data.classification.subcategory !== 'nan' && data.classification.subcategory !== '') {
        subcategoryContainer.className = 'subcategories-list';
        subcategoryContainer.innerHTML = `<div class="subcategory-item">${data.classification.subcategory}</div>`;
    } else {
        subcategoryContainer.className = 'subcategories-list empty';
        subcategoryContainer.innerHTML = '<span class="badge">—</span>';
    }
    
    // Key Info
    document.getElementById('mainIssue').textContent = data.key_info.main_issue;
    document.getElementById('urgency').textContent = data.key_info.urgency;
    document.getElementById('urgency').className = 'badge ' + getPriorityClass(data.key_info.urgency);
    document.getElementById('sentiment').textContent = data.key_info.sentiment;
    document.getElementById('confidence').textContent = data.confidence;
    
    // Response
    originalResponse = data.suggested_response;
    document.getElementById('suggestedResponse').value = data.suggested_response;
    
    // Sources
    if (data.search_results && data.search_results.length > 0) {
        displaySources(data.search_results);
        document.getElementById('sourcesCard').style.display = 'block';
        document.getElementById('sourcesCount').textContent = data.search_results.length;
    }
}

function displaySources(results) {
    const sourcesList = document.getElementById('sourcesList');
    sourcesList.innerHTML = '';
    
    results.forEach((result, index) => {
        const article = result.article;
        const similarity = Math.round(result.similarity * 100);
        const question = article.example_question || article.problem || '';
        const answer = article.template_answer || article.solution || '';
        const articleId = result.article_id || '';
        const feedbackStats = result.feedback_stats || {helpful: 0, total: 0, rate: 0};
        const feedbackBonus = result.feedback_bonus || 0;
        
        const sourceItem = document.createElement('div');
        sourceItem.className = 'source-item';
        
        // Обертка для контента (клик выбирает ответ)
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'source-content';
        contentWrapper.onclick = () => selectSource(answer);
        contentWrapper.title = 'Нажмите, чтобы использовать этот ответ';
        
        contentWrapper.innerHTML = `
            <div class="source-similarity">
                ${similarity}%
                ${feedbackBonus > 0 ? `<span class="feedback-indicator" title="Бонус от отзывов: +${Math.round(feedbackBonus*100)}%">⭐</span>` : ''}
            </div>
            <div class="source-question">${question}</div>
            <div class="source-answer">${answer.substring(0, 100)}${answer.length > 100 ? '...' : ''}</div>
            ${feedbackStats.total > 0 ? `<div class="source-feedback-stats">👍 ${feedbackStats.helpful}/${feedbackStats.total} (${Math.round(feedbackStats.rate*100)}%)</div>` : ''}
        `;
        
        // Кнопка "Полезно"
        const feedbackBtn = document.createElement('button');
        feedbackBtn.className = 'feedback-btn';
        feedbackBtn.innerHTML = '👍 Полезно';
        feedbackBtn.onclick = (e) => {
            e.stopPropagation(); // Не вызывать selectSource
            sendFeedback(articleId, true, feedbackBtn);
        };
        
        sourceItem.appendChild(contentWrapper);
        sourceItem.appendChild(feedbackBtn);
        sourcesList.appendChild(sourceItem);
    });
}

function selectSource(answer) {
    document.getElementById('suggestedResponse').value = answer;
    originalResponse = answer;
    showSuccess('Ответ загружен!');
}

// =============================================================================
// ACTIONS
// =============================================================================

async function copyResponse() {
    const text = document.getElementById('suggestedResponse').value;
    
    try {
        await navigator.clipboard.writeText(text);
        showSuccess('Скопировано!');
    } catch (err) {
        showError('Не удалось скопировать');
    }
}

function resetResponse() {
    if (originalResponse) {
        document.getElementById('suggestedResponse').value = originalResponse;
        showSuccess('Восстановлено!');
    }
}

// =============================================================================
// HELPERS
// =============================================================================

function getConfidenceClass(confidence) {
    const c = confidence.toLowerCase();
    if (c.includes('высок')) return 'high';
    if (c.includes('средн')) return 'medium';
    return 'low';
}

function getPriorityClass(priority) {
    const p = priority.toLowerCase();
    if (p.includes('срочн') || p.includes('высок')) return 'high';
    if (p.includes('средн') || p.includes('обычн')) return 'medium';
    return 'low';
}

async function sendFeedback(articleId, isHelpful, buttonElement) {
    if (!articleId || !currentQuery) {
        showError('Невозможно отправить отзыв');
        return;
    }
    
    // Отключаем кнопку
    buttonElement.disabled = true;
    buttonElement.innerHTML = '⏳';
    
    try {
        const response = await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                article_id: articleId,
                query: currentQuery,
                is_helpful: isHelpful
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Ошибка отправки отзыва');
        }
        
        // Меняем кнопку на "Отмечено"
        buttonElement.innerHTML = '✅ Отмечено';
        buttonElement.classList.add('feedback-sent');
        showSuccess('Спасибо за обратную связь!');
        
    } catch (error) {
        showError(error.message);
        // Восстанавливаем кнопку
        buttonElement.disabled = false;
        buttonElement.innerHTML = '👍 Полезно';
    }
}

function showError(message, elementId = 'errorMessage') {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.classList.add('active');
    setTimeout(() => el.classList.remove('active'), 5000);
}

function showSuccess(message) {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--success);
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 9999;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 2000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);
