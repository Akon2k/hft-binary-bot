const chartContainer = document.getElementById('chart-container');
const chart = LightweightCharts.createChart(chartContainer, {
    layout: {
        backgroundColor: 'transparent',
        textColor: '#848e9c',
    },
    grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
        timeVisible: true,
    },
});

const candleSeries = chart.addCandlestickSeries({
    upColor: '#0ecb81',
    downColor: '#f6465d',
    borderVisible: false,
    wickUpColor: '#0ecb81',
    wickDownColor: '#f6465d',
});

// WebSocket connection to backend
const ws = new WebSocket(`ws://${window.location.host}/ws`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'candle') {
        candleSeries.update(data.payload);
    } else if (data.type === 'trade') {
        addTradeToHistory(data.payload);
    } else if (data.type === 'stats') {
        updateStats(data.payload);
    }
};

function addTradeToHistory(trade) {
    const historyList = document.getElementById('history-list');
    const card = document.createElement('div');
    card.className = `trade-card ${trade.side}`;
    card.innerHTML = `
        <div class="header">
            <span>${trade.symbol}</span>
            <span>${new Date().toLocaleTimeString()}</span>
        </div>
        <div class="monto">$${trade.amount.toFixed(2)} ${trade.side}</div>
        <div class="status ${trade.result}">${trade.result}</div>
    `;
    historyList.prepend(card);
}

function updateStats(stats) {
    document.getElementById('balance').innerText = `$${stats.balance.toFixed(2)}`;
    const profitEl = document.getElementById('profit');
    profitEl.innerText = `${stats.profit >= 0 ? '+' : ''}$${stats.profit.toFixed(2)}`;
    profitEl.className = `value ${stats.profit >= 0 ? 'positive' : 'negative'}`;
}

// Resize chart on window resize
window.addEventListener('resize', () => {
    chart.applyOptions({ width: chartContainer.clientWidth, height: chartContainer.clientHeight });
});
