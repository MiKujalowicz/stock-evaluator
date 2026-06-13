let stockChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    const form = document.getElementById('predict-form');
    const toggleConsole = document.getElementById('toggle-console');
    const logsSection = document.getElementById('logs-section');
    
    // Form submission
    form.addEventListener('submit', handleFormSubmit);
    
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
}

// Submit action
async def handleFormSubmit(event) {
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
    
    try {
        const response = await fetch('/api/predict/stream', {
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
    
    const dates = marketData.map(d => d.date);
    const prices = marketData.map(d => d.close);
    
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
            borderColor: prediction.direction === "UP" ? 'rgba(74, 222, 128, 1)' : 'rgba(248, 113, 113, 1)',
            borderDash: [5, 5],
            borderWidth: 2.5,
            fill: false,
            pointRadius: [].concat(Array(prices.length - 1).fill(0)).concat([2, 5]),
            pointBackgroundColor: prediction.direction === "UP" ? '#4ade80' : '#f87171'
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
    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.25)');
    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');
    
    const datasets = [
        {
            label: `${ticker} Price History`,
            data: prices,
            borderColor: '#3b82f6',
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
                    backgroundColor: 'rgba(15, 23, 42, 0.95)',
                    titleColor: '#f8fafc',
                    bodyColor: '#cbd5e1',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.03)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.4)',
                        maxTicksLimit: 8,
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.03)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.4)',
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
    if (fundamentals && stockChart) {
        renderChart(fundamentals.ticker, stockChart.data.datasets[0].data.map((v, i) => ({
            date: stockChart.data.labels[i],
            close: v
        })), p);
    }
}

// Load and populate sidebar history
async def loadHistory() {
    try {
        const response = await fetch('/api/history');
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
            const changeClass = item.change_percent > 0 ? 'change-up' : (item.change_percent < 0 ? 'change-down' : 'change-flat');
            const arrow = item.direction === 'UP' ? '↗' : (item.direction === 'DOWN' ? '↘' : '→');
            
            el.innerHTML = `
                <div class="history-top">
                    <div class="history-ticker-group">
                        <span class="history-ticker">${item.ticker}</span>
                        <span class="history-price">${formatCurrency(item.price)}</span>
                    </div>
                    <span class="history-rating rating-${ratingClass.includes('buy') ? 'buy' : (ratingClass.includes('sell') ? 'sell' : 'hold')}">${item.rating}</span>
                </div>
                <div class="history-bottom">
                    <span class="history-change ${changeClass}">${arrow} ${item.change_percent > 0 ? '+' : ''}${item.change_percent.toFixed(2)}%</span>
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
    
    // Set headers
    document.getElementById('header-stock-name').textContent = item.company_name;
    document.getElementById('header-stock-meta').textContent = `Historical record from ${item.timestamp}`;
    document.getElementById('ticker-auto-badge').textContent = 'HISTORICAL';
    document.getElementById('ticker-auto-badge').className = 'ticker-badge';
    
    // Logs Console update
    const consoleOutput = document.getElementById('console-output');
    consoleOutput.innerHTML = `<div class="log-line success">Loaded historical analysis run for ${item.ticker} from database.</div>`;
    document.getElementById('console-pulse').className = 'pulse-indicator';
    
    // Timeline steps reset to completed
    document.querySelectorAll('.timeline-step').forEach(step => {
        step.className = 'timeline-step completed';
    });
    
    // Update fundamentals
    document.getElementById('metrics-price').textContent = formatCurrency(item.price);
    document.getElementById('price-badge-container').style.display = 'flex';
    document.getElementById('metrics-pe').textContent = item.pe_ratio !== null && item.pe_ratio !== undefined ? item.pe_ratio.toFixed(2) : 'N/A';
    document.getElementById('metrics-eps').textContent = item.eps !== null && item.eps !== undefined ? formatCurrency(item.eps) : 'N/A';
    document.getElementById('metrics-cap').textContent = 'N/A'; // not saved in history to save space
    document.getElementById('metrics-sector').textContent = 'Loaded Historical';
    
    // Bul/Bear cards (Note: full debate is not saved in history index, so we generate mock panels or display summaries)
    document.getElementById('bull-thesis-output').innerHTML = `<p><em>Bullish thesis loaded. Refer to synthesis report below for summarized advocate consensus.</em></p>`;
    document.getElementById('bear-thesis-output').innerHTML = `<p><em>Bearish thesis loaded. Refer to synthesis report below for summarized challenger criticisms.</em></p>`;
    
    // Predictions
    const ratingBadge = document.getElementById('prediction-rating');
    ratingBadge.textContent = item.rating;
    ratingBadge.className = 'rating-badge';
    const ratingClass = item.rating.toLowerCase().replace(' ', '-');
    ratingBadge.classList.add(ratingClass);
    
    const dirEl = document.getElementById('pred-direction');
    const direction = item.direction;
    dirEl.className = `pred-display ${direction.toLowerCase()}`;
    if (direction === 'UP') {
        dirEl.innerHTML = '<i class="fa-solid fa-circle-up"></i> <span>BULLISH</span>';
    } else if (direction === 'DOWN') {
        dirEl.innerHTML = '<i class="fa-solid fa-circle-down"></i> <span>BEARISH</span>';
    } else {
        dirEl.innerHTML = '<i class="fa-solid fa-circle"></i> <span>SIDEWAYS</span>';
    }
    
    const changeEl = document.getElementById('pred-change');
    const change = item.change_percent;
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
    
    document.getElementById('synthesis-report-output').innerHTML = marked.parse(item.synthesis_report);
    
    // Render static charts from history
    // Since we don't have historical points, generate chart with mock history and a projection line
    const mockHist = [];
    let basePrice = item.price;
    const now = new Date();
    for (let i = 30; i > 0; i--) {
        const d = new Date(now);
        d.setDate(now.getDate() - i);
        mockHist.push({
            date: d.toISOString().split('T')[0],
            close: Number((basePrice - (i * 0.4) + Math.random() * 2).toFixed(2))
        });
    }
    // Make last element exact
    mockHist.push({
        date: now.toISOString().split('T')[0],
        close: item.price
    });
    
    renderChart(item.ticker, mockHist, item);
}
