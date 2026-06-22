let stockChart = null;
let currentChartTicker = null;
let currentMarketData = [];
let currentPrediction = null;
let conversationTurns = [];
let selectedConversationOrder = null;

const THEME_STORAGE_KEY = 'aura-theme';

const API_BASE_URL = (() => {
    if (window.AURA_API_BASE_URL) {
        return window.AURA_API_BASE_URL.replace(/\/$/, '');
    }

    const localHosts = ['localhost', '127.0.0.1', '::1'];
    const isLocalPreview = window.location.protocol === 'file:' ||
        (localHosts.includes(window.location.hostname) && window.location.port && window.location.port !== '8000');

    return isLocalPreview ? 'http://localhost:8000' : '';
})();

function apiUrl(path) {
    return `${API_BASE_URL}${path}`;
}

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    const form = document.getElementById('predict-form');
    const toggleConsole = document.getElementById('toggle-console');
    const logsSection = document.getElementById('logs-section');
    const configurationToggle = document.getElementById('configuration-toggle');
    const configurationSection = document.querySelector('.configuration-section');
    
    initTheme();

    // Form submission
    form.addEventListener('submit', handleFormSubmit);

    configurationToggle.addEventListener('click', () => {
        const isCollapsed = configurationSection.classList.toggle('collapsed');
        configurationToggle.setAttribute('aria-expanded', String(!isCollapsed));
    });
    
    // Toggle logs console expansion
    toggleConsole.addEventListener('click', () => {
        logsSection.classList.toggle('collapsed');
        const chevron = document.getElementById('console-chevron');
        if (logsSection.classList.contains('collapsed')) {
            chevron.className = 'fa-solid fa-chevron-down toggle-icon';
        } else {
            chevron.className = 'fa-solid fa-chevron-up toggle-icon';
        }
    });

    // Load history list on startup
    loadHistory();
    resetConversationPanel();
}

function getCssVar(name) {
    return getComputedStyle(document.body).getPropertyValue(name).trim();
}

function initTheme() {
    const storedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    const systemTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    applyTheme(storedTheme || systemTheme, false);

    document.querySelectorAll('.theme-option').forEach(button => {
        button.addEventListener('click', () => {
            applyTheme(button.dataset.theme, true);
        });
    });
}

function applyTheme(theme, persist) {
    const normalizedTheme = theme === 'light' ? 'light' : 'dark';
    document.body.dataset.theme = normalizedTheme;
    document.querySelectorAll('.theme-option').forEach(button => {
        const isActive = button.dataset.theme === normalizedTheme;
        button.classList.toggle('active', isActive);
        button.setAttribute('aria-pressed', String(isActive));
    });

    if (persist) {
        localStorage.setItem(THEME_STORAGE_KEY, normalizedTheme);
    }

    if (currentChartTicker && currentMarketData.length > 0) {
        renderChart(currentChartTicker, currentMarketData, currentPrediction);
    }
}

// Format currency
function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) return 'N/A';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

// Format big market cap numbers
function formatMarketCap(value) {
    if (!value || isNaN(value)) return 'N/A';
    if (value >= 1e12) return (value / 1e12).toFixed(2) + 'T';
    if (value >= 1e9) return (value / 1e9).toFixed(2) + 'B';
    if (value >= 1e6) return (value / 1e6).toFixed(2) + 'M';
    return value.toLocaleString();
}

// Clear all outputs before a new run
function resetDashboardUI(ticker) {
    // Header
    document.getElementById('header-stock-name').textContent = `Analyzing ${ticker.toUpperCase()}...`;
    document.getElementById('header-stock-meta').textContent = 'Workflow in progress';
    document.getElementById('ticker-auto-badge').textContent = 'RUNNING';
    document.getElementById('ticker-auto-badge').className = 'ticker-badge active';
    
    // Timeline steps reset
    document.querySelectorAll('.timeline-step').forEach(step => {
        step.className = 'timeline-step';
    });
    
    // Logs Console reset & expansion
    const consoleOutput = document.getElementById('console-output');
    consoleOutput.innerHTML = '<div class="log-line system">Console initialized. Connecting to prediction engine...</div>';
    document.getElementById('logs-section').classList.remove('collapsed');
    document.getElementById('console-chevron').className = 'fa-solid fa-chevron-up toggle-icon';
    document.getElementById('console-pulse').className = 'pulse-indicator active';
    
    // Fundamentals
    document.getElementById('metrics-price').textContent = '$0.00';
    document.getElementById('price-badge-container').style.display = 'none';
    document.getElementById('metrics-pe').textContent = 'N/A';
    document.getElementById('metrics-eps').textContent = 'N/A';
    document.getElementById('metrics-cap').textContent = 'N/A';
    document.getElementById('metrics-sector').textContent = 'N/A';
    updateUserInputReview('');
    resetConversationPanel();
    
    // Bul/Bear cards
    document.getElementById('bull-thesis-output').innerHTML = `
        <div class="agent-placeholder">
            <i class="fa-solid fa-circle-nodes placeholder-icon fa-spin"></i>
            <p>Bullish Analyst is reviewing fundamentals...</p>
        </div>`;
    document.getElementById('bear-thesis-output').innerHTML = `
        <div class="agent-placeholder">
            <i class="fa-solid fa-triangle-exclamation placeholder-icon"></i>
            <p>Bearish Challenger is standing by...</p>
        </div>`;
        
    // Prediction Card
    document.getElementById('prediction-rating').textContent = 'ANALYZING';
    document.getElementById('prediction-rating').className = 'rating-badge';
    
    document.getElementById('pred-direction').className = 'pred-display stable';
    document.getElementById('pred-direction').innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> <span>ANALYZING</span>';
    
    document.getElementById('pred-change').textContent = '0.00%';
    document.getElementById('pred-change').className = 'pred-value';
    
    document.getElementById('pred-confidence-fill').style.width = '0%';
    document.getElementById('pred-confidence-value').textContent = '0%';
    
    document.getElementById('synthesis-report-output').innerHTML = `
        <div class="report-placeholder">
            <i class="fa-solid fa-gavel placeholder-icon fa-fade"></i>
            <p>Moderator is waiting for debate transcripts...</p>
        </div>`;
        
    // Destroy existing chart instance
    if (stockChart) {
        stockChart.destroy();
        stockChart = null;
    }
    currentChartTicker = null;
    currentMarketData = [];
    currentPrediction = null;
}

function updateUserInputReview(text) {
    const review = document.getElementById('user-input-review');
    const content = document.getElementById('user-input-content');
    if (!text) {
        review.classList.add('hidden');
        content.textContent = '';
        return;
    }

    content.textContent = text;
    review.classList.remove('hidden');
}

function resetConversationPanel() {
    conversationTurns = [];
    selectedConversationOrder = null;
    document.getElementById('conversation-status').textContent = 'Awaiting debate';
    renderConversationList();
    renderConversationDetail(null);
}

function normalizeTurn(turn, index) {
    return {
        step: turn.step || 'unknown',
        role: turn.role || 'system',
        label: turn.label || 'Expert',
        iteration: Number.isFinite(Number(turn.iteration)) ? Number(turn.iteration) : 0,
        content: turn.content || '',
        order: Number.isFinite(Number(turn.order)) ? Number(turn.order) : index + 1
    };
}

function setConversationTurns(turns, statusText = null) {
    conversationTurns = (turns || [])
        .filter(turn => turn && turn.content)
        .map((turn, index) => normalizeTurn(turn, index))
        .sort((a, b) => a.order - b.order);

    selectedConversationOrder = conversationTurns.length ? conversationTurns[conversationTurns.length - 1].order : null;
    document.getElementById('conversation-status').textContent = statusText ||
        (conversationTurns.length ? `${conversationTurns.length} turns available` : 'Awaiting debate');
    renderConversationList();
    renderConversationDetail(conversationTurns.find(turn => turn.order === selectedConversationOrder));
}

function addConversationTurn(turn) {
    if (!turn || !turn.content) return;

    const normalizedTurn = normalizeTurn(turn, conversationTurns.length);
    conversationTurns.push(normalizedTurn);
    selectedConversationOrder = normalizedTurn.order;
    document.getElementById('conversation-status').textContent = `${conversationTurns.length} turns recorded`;
    renderConversationList();
    renderConversationDetail(normalizedTurn);
}

function plainTextFromMarkdown(text) {
    const div = document.createElement('div');
    div.innerHTML = marked.parse(text || '');
    return div.textContent.replace(/\s+/g, ' ').trim();
}

function renderConversationList() {
    const list = document.getElementById('conversation-list');
    if (!conversationTurns.length) {
        list.innerHTML = '<div class="conversation-empty">No expert turns yet.</div>';
        return;
    }

    list.innerHTML = '';
    conversationTurns.forEach(turn => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `conversation-turn ${turn.role}`;
        if (turn.order === selectedConversationOrder) {
            button.classList.add('active');
        }
        button.innerHTML = `
            <div class="turn-top">
                <span class="turn-label">${turn.label}</span>
                <span class="turn-order">#${turn.order}</span>
            </div>
            <div class="turn-summary">${plainTextFromMarkdown(turn.content) || 'No content available.'}</div>
        `;
        button.addEventListener('click', () => {
            selectedConversationOrder = turn.order;
            renderConversationList();
            renderConversationDetail(turn);
        });
        list.appendChild(button);
    });
}

function renderConversationDetail(turn) {
    const meta = document.getElementById('conversation-detail-meta');
    const content = document.getElementById('conversation-detail-content');
    if (!turn) {
        meta.textContent = 'Select a turn to review the agent position.';
        content.innerHTML = `
            <div class="agent-placeholder inline-placeholder">
                <i class="fa-solid fa-comments placeholder-icon"></i>
                <p>The expert debate transcript will appear here as agents respond.</p>
            </div>`;
        return;
    }

    const iterationLabel = turn.iteration > 0 ? `Iteration ${turn.iteration}` : 'Final';
    meta.textContent = `${turn.label} // ${iterationLabel} // Turn ${turn.order}`;
    content.innerHTML = marked.parse(turn.content);
}

function buildLegacyConversation(item) {
    if (!item || !item.synthesis_report) return [];
    return [{
        step: 'moderator',
        role: 'moderator',
        label: 'Moderator',
        iteration: 0,
        content: `${item.synthesis_report}\n\n*Full bull/bear transcript unavailable for this older record.*`,
        order: 1
    }];
}

// Submit action
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const tickerInput = document.getElementById('ticker');
    const pressReleaseInput = document.getElementById('press-release');
    const btnSubmit = document.getElementById('btn-submit');
    
    const ticker = tickerInput.value.trim().toUpperCase();
    const pressRelease = pressReleaseInput.value.trim();
    
    if (!ticker || !pressRelease) return;
    
    // Disable inputs
    tickerInput.disabled = true;
    pressReleaseInput.disabled = true;
    btnSubmit.disabled = true;
    
    resetDashboardUI(ticker);
    updateUserInputReview(pressRelease);
    
    try {
        const response = await fetch(apiUrl('/api/predict/stream'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ticker, press_release: pressRelease })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let currentEvent = '';
        
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Hold onto partial line
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) continue;
                
                if (trimmed.startsWith('event:')) {
                    currentEvent = trimmed.replace('event:', '').trim();
                } else if (trimmed.startsWith('data:')) {
                    const rawData = trimmed.replace('data:', '').trim();
                    try {
                        const payload = JSON.parse(rawData);
                        handleSSEUpdate(currentEvent, payload);
                    } catch (e) {
                        console.error("Error parsing JSON payload:", rawData, e);
                    }
                }
            }
        }
        
        // Final completion steps
        document.getElementById('console-pulse').className = 'pulse-indicator';
        appendLogLine("Done.", "success");
        loadHistory();
        
    } catch (error) {
        console.error("Prediction execution failed:", error);
        document.getElementById('console-pulse').className = 'pulse-indicator';
        appendLogLine(`Execution Error: ${error.message}`, "error");
        
        document.getElementById('prediction-rating').textContent = 'ERROR';
        document.getElementById('prediction-rating').className = 'rating-badge';
        document.getElementById('ticker-auto-badge').textContent = 'FAILED';
        document.getElementById('ticker-auto-badge').className = 'ticker-badge';
        
    } finally {
        tickerInput.disabled = false;
        pressReleaseInput.disabled = false;
        btnSubmit.disabled = false;
    }
}

// Log updater
function appendLogLine(text, type = "system") {
    const consoleOutput = document.getElementById('console-output');
    const line = document.createElement('div');
    line.className = `log-line ${type}`;
    line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
    consoleOutput.appendChild(line);
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// Handle incoming SSE updates
function handleSSEUpdate(event, data) {
    if (event === 'error') {
        const logs = data.logs || [data.error];
        logs.forEach(log => appendLogLine(log, "error"));
        return;
    }
    
    if (event === 'done') {
        appendLogLine("LangGraph workflow executed successfully.", "success");
        document.getElementById('conversation-status').textContent = conversationTurns.length
            ? `${conversationTurns.length} turns complete`
            : 'No transcript captured';
        document.getElementById('ticker-auto-badge').textContent = 'IDLE';
        document.getElementById('ticker-auto-badge').className = 'ticker-badge';
        return;
    }
    
    const step = data.step;
    
    // Render step logs
    if (data.logs && data.logs.length > 0) {
        const lastLog = data.logs[data.logs.length - 1];
        appendLogLine(lastLog, "system");
    }

    if (data.conversation_turn) {
        addConversationTurn(data.conversation_turn);
    }
    
    // Update timeline visual indicators
    if (step && step !== 'init') {
        // Set all prior steps to completed
        let foundCurrent = false;
        const steps = ['fetch_data', 'bullish_analyst', 'bearish_analyst', 'moderator'];
        
        steps.forEach(s => {
            const el = document.getElementById(`step-${s}`);
            if (!el) return;
            
            if (s === step) {
                el.className = 'timeline-step active';
                foundCurrent = true;
            } else if (!foundCurrent) {
                el.className = 'timeline-step completed';
            } else {
                el.className = 'timeline-step';
            }
        });
    }
    
    // Node specific data updates
    if (step === 'fetch_data' && data.fundamentals) {
        updateFundamentals(data.fundamentals);
        if (data.market_data) {
            renderChart(data.fundamentals.ticker, data.market_data);
        }
    }
    
    if (step === 'bullish_analyst' && data.bullish_thesis) {
        document.getElementById('bull-thesis-output').innerHTML = marked.parse(data.bullish_thesis);
        document.getElementById('bear-thesis-output').innerHTML = `
            <div class="agent-placeholder">
                <i class="fa-solid fa-triangle-exclamation placeholder-icon fa-fade"></i>
                <p>Bearish Analyst is reviewing the bullish case and fundamentals...</p>
            </div>`;
    }
    
    if (step === 'bearish_analyst' && data.bearish_thesis) {
        document.getElementById('bear-thesis-output').innerHTML = marked.parse(data.bearish_thesis);
    }
    
    if (step === 'moderator' && data.prediction) {
        updatePrediction(data.prediction, data.synthesis_report, data.fundamentals);
    }
}

// Update Fundamentals metrics
function updateFundamentals(f) {
    document.getElementById('header-stock-name').textContent = f.name || f.ticker;
    document.getElementById('header-stock-meta').textContent = `${f.sector} // ${f.industry}`;
    
    document.getElementById('metrics-price').textContent = formatCurrency(f.price);
    document.getElementById('price-badge-container').style.display = 'flex';
    
    document.getElementById('metrics-pe').textContent = f.pe_ratio !== null && f.pe_ratio !== undefined ? f.pe_ratio.toFixed(2) : 'N/A';
    document.getElementById('metrics-eps').textContent = f.eps !== null && f.eps !== undefined ? formatCurrency(f.eps) : 'N/A';
    document.getElementById('metrics-cap').textContent = formatMarketCap(f.market_cap);
    document.getElementById('metrics-sector').textContent = f.sector || 'N/A';
}

// Draw chart using Chart.js
function renderChart(ticker, marketData, prediction = null) {
    const ctx = document.getElementById('stockChart').getContext('2d');
    currentChartTicker = ticker;
    currentMarketData = marketData;
    currentPrediction = prediction;
    
    const dates = marketData.map(d => d.date);
    const prices = marketData.map(d => d.close);
    const chartLine = getCssVar('--chart-line') || '#3b82f6';
    const chartFill = getCssVar('--chart-fill') || 'rgba(59, 130, 246, 0.25)';
    const chartGrid = getCssVar('--chart-grid') || 'rgba(255, 255, 255, 0.03)';
    const chartTick = getCssVar('--chart-tick') || 'rgba(255, 255, 255, 0.4)';
    const bullColor = getCssVar('--accent-bull') || '#4ade80';
    const bearColor = getCssVar('--accent-bear') || '#f87171';
    
    // Setup projection variables
    let finalDates = [...dates];
    let finalPrices = [...prices];
    let forecastDataset = null;
    
    if (prediction && prediction.direction !== "STABLE") {
        const lastDate = new Date(dates[dates.length - 1]);
        const lastPrice = prices[prices.length - 1];
        
        // Generate projected dates and prices (30 days out)
        const projDate = new Date(lastDate);
        projDate.setDate(projDate.getDate() + 30);
        const projDateStr = projDate.toISOString().split('T')[0];
        
        const changeMult = 1 + (prediction.change_percent / 100);
        const projPrice = lastPrice * changeMult;
        
        // Add dotted forecast dataset
        forecastDataset = {
            label: `${ticker} Projection`,
            data: Array(prices.length - 1).fill(null).concat([lastPrice, projPrice]),
            borderColor: prediction.direction === "UP" ? bullColor : bearColor,
            borderDash: [5, 5],
            borderWidth: 2.5,
            fill: false,
            pointRadius: [].concat(Array(prices.length - 1).fill(0)).concat([2, 5]),
            pointBackgroundColor: prediction.direction === "UP" ? bullColor : bearColor
        };
        
        // Append projection labels
        for(let i=1; i<=30; i++) {
            // just to pad the axis
        }
        finalDates.push(projDateStr);
    }
    
    if (stockChart) {
        stockChart.destroy();
    }
    
    // Gradient fill for main chart
    const gradient = ctx.createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, chartFill);
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
    
    const datasets = [
        {
            label: `${ticker} Price History`,
            data: prices,
            borderColor: chartLine,
            borderWidth: 2,
            backgroundColor: gradient,
            fill: true,
            tension: 0.1,
            pointRadius: 1,
            pointHoverRadius: 5
        }
    ];
    
    if (forecastDataset) {
        datasets.push(forecastDataset);
    }
    
    stockChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: finalDates,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: getCssVar('--bg-console') || 'rgba(15, 23, 42, 0.95)',
                    titleColor: getCssVar('--text-primary') || '#f8fafc',
                    bodyColor: getCssVar('--text-secondary') || '#cbd5e1',
                    borderColor: getCssVar('--border-color') || 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: chartGrid
                    },
                    ticks: {
                        color: chartTick,
                        maxTicksLimit: 8,
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    grid: {
                        color: chartGrid
                    },
                    ticks: {
                        color: chartTick,
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

// Update prediction panel
function updatePrediction(p, report, fundamentals) {
    // Rating badge styling
    const ratingBadge = document.getElementById('prediction-rating');
    ratingBadge.textContent = p.rating || 'HOLD';
    ratingBadge.className = 'rating-badge';
    
    const ratingClass = p.rating.toLowerCase().replace(' ', '-');
    ratingBadge.classList.add(ratingClass);
    
    // Direction Badge
    const dirEl = document.getElementById('pred-direction');
    const direction = p.direction || 'STABLE';
    dirEl.className = `pred-display ${direction.toLowerCase()}`;
    
    if (direction === 'UP') {
        dirEl.innerHTML = '<i class="fa-solid fa-circle-up"></i> <span>BULLISH</span>';
    } else if (direction === 'DOWN') {
        dirEl.innerHTML = '<i class="fa-solid fa-circle-down"></i> <span>BEARISH</span>';
    } else {
        dirEl.innerHTML = '<i class="fa-solid fa-circle"></i> <span>SIDEWAYS</span>';
    }
    
    // Percentage Change
    const changeEl = document.getElementById('pred-change');
    const change = p.change_percent || 0.0;
    changeEl.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
    if (change > 0) {
        changeEl.className = 'pred-value change-up';
    } else if (change < 0) {
        changeEl.className = 'pred-value change-down';
    } else {
        changeEl.className = 'pred-value change-flat';
    }
    
    // Confidence meter
    const confidence = p.confidence || 0.5;
    const confPercent = Math.round(confidence * 100);
    document.getElementById('pred-confidence-fill').style.width = `${confPercent}%`;
    document.getElementById('pred-confidence-value').textContent = `${confPercent}%`;
    
    // Report text
    document.getElementById('synthesis-report-output').innerHTML = marked.parse(report);
    
    // Re-render chart incorporating projections
    if (fundamentals && stockChart && currentMarketData.length > 0) {
        renderChart(fundamentals.ticker, currentMarketData, p);
    }
}

// Load and populate sidebar history
async function loadHistory() {
    try {
        const response = await fetch(apiUrl('/api/history'));
        if (!response.ok) return;
        
        const history = await response.json();
        const container = document.getElementById('history-container');
        
        if (history.length === 0) {
            container.innerHTML = '<div class="empty-history">No past analyses found.</div>';
            return;
        }
        
        container.innerHTML = '';
        history.forEach(item => {
            const el = document.createElement('div');
            el.className = 'history-item';
            
            const ratingClass = (item.rating || 'HOLD').toLowerCase().replace(' ', '-');
            const change = Number(item.change_percent || 0);
            const changeClass = change > 0 ? 'change-up' : (change < 0 ? 'change-down' : 'change-flat');
            const arrow = item.direction === 'UP' ? 'UP' : (item.direction === 'DOWN' ? 'DOWN' : 'FLAT');
            
            el.innerHTML = `
                <div class="history-top">
                    <div class="history-ticker-group">
                        <span class="history-ticker">${item.ticker}</span>
                        <span class="history-price">${formatCurrency(item.price)}</span>
                    </div>
                    <span class="history-rating rating-${ratingClass.includes('buy') ? 'buy' : (ratingClass.includes('sell') ? 'sell' : 'hold')}">${item.rating}</span>
                </div>
                <div class="history-bottom">
                    <span class="history-change ${changeClass}">${arrow} ${change > 0 ? '+' : ''}${change.toFixed(2)}%</span>
                    <span class="history-time">${item.timestamp}</span>
                </div>
            `;
            
            el.addEventListener('click', () => loadHistoricalRecord(item));
            container.appendChild(el);
        });
    } catch (e) {
        console.error("Error loading history list:", e);
    }
}

// Restore a historical record on click
function loadHistoricalRecord(item) {
    document.getElementById('ticker').value = item.ticker;
    const fundamentals = item.fundamentals || {};
    const price = item.price ?? fundamentals.price ?? 0;
    const rating = item.rating || 'HOLD';
    const direction = item.direction || 'STABLE';
    const change = Number(item.change_percent || 0);
    const turns = Array.isArray(item.conversation) && item.conversation.length > 0
        ? item.conversation
        : buildLegacyConversation(item);
    const latestBullTurn = [...turns].reverse().find(turn => turn.role === 'bullish');
    const latestBearTurn = [...turns].reverse().find(turn => turn.role === 'bearish');
    
    // Set headers
    document.getElementById('header-stock-name').textContent = item.company_name || fundamentals.name || item.ticker;
    document.getElementById('header-stock-meta').textContent = `Historical record from ${item.timestamp}`;
    document.getElementById('ticker-auto-badge').textContent = 'HISTORICAL';
    document.getElementById('ticker-auto-badge').className = 'ticker-badge';
    updateUserInputReview(item.press_release || '');
    setConversationTurns(
        turns,
        Array.isArray(item.conversation) && item.conversation.length > 0
            ? `${turns.length} historical turns`
            : 'Legacy record: transcript unavailable'
    );
    
    // Logs Console update
    const consoleOutput = document.getElementById('console-output');
    consoleOutput.innerHTML = `<div class="log-line success">Loaded historical analysis run for ${item.ticker} from database.</div>`;
    document.getElementById('console-pulse').className = 'pulse-indicator';
    
    // Timeline steps reset to completed
    document.querySelectorAll('.timeline-step').forEach(step => {
        step.className = 'timeline-step completed';
    });
    
    // Update fundamentals
    document.getElementById('metrics-price').textContent = formatCurrency(price);
    document.getElementById('price-badge-container').style.display = 'flex';
    document.getElementById('metrics-pe').textContent = item.pe_ratio !== null && item.pe_ratio !== undefined ? item.pe_ratio.toFixed(2) : 'N/A';
    document.getElementById('metrics-eps').textContent = item.eps !== null && item.eps !== undefined ? formatCurrency(item.eps) : 'N/A';
    document.getElementById('metrics-cap').textContent = formatMarketCap(fundamentals.market_cap);
    document.getElementById('metrics-sector').textContent = fundamentals.sector || 'Loaded Historical';
    
    document.getElementById('bull-thesis-output').innerHTML = latestBullTurn
        ? marked.parse(latestBullTurn.content)
        : `<p><em>Bullish transcript unavailable for this older record.</em></p>`;
    document.getElementById('bear-thesis-output').innerHTML = latestBearTurn
        ? marked.parse(latestBearTurn.content)
        : `<p><em>Bearish transcript unavailable for this older record.</em></p>`;
    
    // Predictions
    const ratingBadge = document.getElementById('prediction-rating');
    ratingBadge.textContent = rating;
    ratingBadge.className = 'rating-badge';
    const ratingClass = rating.toLowerCase().replace(' ', '-');
    ratingBadge.classList.add(ratingClass);
    
    const dirEl = document.getElementById('pred-direction');
    dirEl.className = `pred-display ${direction.toLowerCase()}`;
    if (direction === 'UP') {
        dirEl.innerHTML = '<i class="fa-solid fa-circle-up"></i> <span>BULLISH</span>';
    } else if (direction === 'DOWN') {
        dirEl.innerHTML = '<i class="fa-solid fa-circle-down"></i> <span>BEARISH</span>';
    } else {
        dirEl.innerHTML = '<i class="fa-solid fa-circle"></i> <span>SIDEWAYS</span>';
    }
    
    const changeEl = document.getElementById('pred-change');
    changeEl.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)}%`;
    if (change > 0) {
        changeEl.className = 'pred-value change-up';
    } else if (change < 0) {
        changeEl.className = 'pred-value change-down';
    } else {
        changeEl.className = 'pred-value change-flat';
    }
    
    const confidence = item.confidence || 0.5;
    const confPercent = Math.round(confidence * 100);
    document.getElementById('pred-confidence-fill').style.width = `${confPercent}%`;
    document.getElementById('pred-confidence-value').textContent = `${confPercent}%`;
    
    document.getElementById('synthesis-report-output').innerHTML = marked.parse(item.synthesis_report || '');
    
    let chartData = Array.isArray(item.market_data) && item.market_data.length > 0 ? item.market_data : [];
    if (chartData.length === 0) {
        chartData = [];
        let basePrice = price;
        const now = new Date();
        for (let i = 30; i > 0; i--) {
            const d = new Date(now);
            d.setDate(now.getDate() - i);
            chartData.push({
                date: d.toISOString().split('T')[0],
                close: Number((basePrice - (i * 0.4) + Math.random() * 2).toFixed(2))
            });
        }
        chartData.push({
            date: now.toISOString().split('T')[0],
            close: price
        });
    }
    
    renderChart(item.ticker, chartData, {
        direction,
        change_percent: change,
        rating,
        confidence: item.confidence || 0.5
    });
}
