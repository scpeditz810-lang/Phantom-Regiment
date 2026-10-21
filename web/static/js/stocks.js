/**
 * Phantom Regiment - Stock Market & Banking Interactive Engine
 */

let allStocks = [];
let activeStockId = null;
let stockChart = null;
let currentBankAction = 'deposit';

document.addEventListener("DOMContentLoaded", () => {
    initMarket();
    loadLeaderboards();
    if (document.getElementById("portfolio-body")) {
        loadPortfolio();
    }
});

async function initMarket() {
    await loadStocks();
    // Auto-refresh ticker and chart every 25 seconds
    setInterval(() => {
        loadStocks(true);
        if (activeStockId) {
            loadChart(activeStockId);
        }
    }, 25000);
}

// ── Stock Loading & Rendering ────────────────────────────────────────────────
async function loadStocks(silent = false) {
    try {
        const res = await fetch("/api/stocks");
        if (!res.ok) return;
        allStocks = await res.json();

        renderStockCards();
        populateSelectDropdown();

        if (!activeStockId && allStocks.length > 0) {
            selectStock(allStocks[0].id);
        } else if (activeStockId) {
            const current = allStocks.find(s => s.id === activeStockId);
            if (current) {
                updateHeaderInfo(current);
            }
        }
    } catch (e) {
        if (!silent) console.error("Error loading stocks:", e);
    }
}

function renderStockCards() {
    const container = document.getElementById("stocks-container");
    if (!container) return;

    if (!allStocks.length) {
        container.innerHTML = '<div class="text-muted p-4">No active stocks listed on the exchange.</div>';
        return;
    }

    container.innerHTML = allStocks.map(s => {
        const isUp = s.is_up;
        const sign = s.change_pct >= 0 ? "+" : "";
        const isActive = s.id === activeStockId ? "active" : "";

        return `
            <div class="stock-card ${isActive}" id="stock-card-${s.id}" onclick="selectStock(${s.id})">
                <div class="stock-card-top">
                    <div>
                        <div class="stock-symbol">${s.symbol}</div>
                        <div class="stock-company">${s.name}</div>
                    </div>
                    <span class="${isUp ? 'tag-up' : 'tag-down'}">
                        ${sign}${s.change_pct}%
                    </span>
                </div>
                <div class="stock-price text-orange">${s.price.toLocaleString()} Medals</div>
                <div class="stock-footer">
                    <span>Avail: ${s.available_shares} / ${s.total_supply}</span>
                    <span>Max: 10/usr</span>
                </div>
            </div>
        `;
    }).join("");
}

function populateSelectDropdown() {
    const select = document.getElementById("trade-stock-select");
    if (!select) return;

    const currentVal = select.value;
    select.innerHTML = allStocks.map(s => `
        <option value="${s.id}" ${s.id == activeStockId ? 'selected' : ''}>
            ${s.symbol} - ${s.name} (${s.price.toLocaleString()} Medals)
        </option>
    `).join("");

    if (currentVal && allStocks.some(s => s.id == currentVal)) {
        select.value = currentVal;
    }
}

function onStockSelectChange() {
    const select = document.getElementById("trade-stock-select");
    if (!select) return;
    const selectedId = parseInt(select.value);
    if (selectedId) {
        selectStock(selectedId);
    }
}

function selectStock(stockId) {
    activeStockId = stockId;
    const stock = allStocks.find(s => s.id === stockId);
    if (!stock) return;

    // Update active card styling
    document.querySelectorAll(".stock-card").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById(`stock-card-${stockId}`);
    if (activeEl) activeEl.classList.add("active");

    // Update select dropdown
    const select = document.getElementById("trade-stock-select");
    if (select && select.value != stockId) {
        select.value = stockId;
    }

    updateHeaderInfo(stock);
    updateTradeTotal();
    loadChart(stockId);
}

function updateHeaderInfo(stock) {
    const symEl = document.getElementById("chart-active-symbol");
    const nameEl = document.getElementById("chart-active-name");
    const priceEl = document.getElementById("chart-active-price");
    const pctEl = document.getElementById("chart-active-pct");

    if (symEl) symEl.innerText = stock.symbol;
    if (nameEl) nameEl.innerText = stock.name;
    if (priceEl) priceEl.innerText = `${stock.price.toLocaleString()} Medals`;

    if (pctEl) {
        const sign = stock.change_pct >= 0 ? "+" : "";
        pctEl.innerText = `${sign}${stock.change_pct}%`;
        pctEl.className = stock.is_up ? "chart-pct tag-up" : "chart-pct tag-down";
    }
}

// ── Chart.js Engine ─────────────────────────────────────────────────────────
async function loadChart(stockId) {
    try {
        const res = await fetch(`/api/stocks/${stockId}/history`);
        if (!res.ok) return;
        const data = await res.json();

        const canvas = document.getElementById("stockChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const currentStock = allStocks.find(s => s.id === stockId);
        const isUp = currentStock ? currentStock.is_up : true;

        const lineColor = isUp ? "#10b981" : "#ef4444";
        const bgColor = isUp ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)";

        if (stockChart) {
            stockChart.data.labels = data.labels;
            stockChart.data.datasets[0].data = data.prices;
            stockChart.data.datasets[0].borderColor = lineColor;
            stockChart.data.datasets[0].backgroundColor = bgColor;
            stockChart.data.datasets[0].label = currentStock ? `${currentStock.symbol} Price` : 'Price';
            stockChart.update('none'); // Update smoothly without re-animating
        } else {
            stockChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: currentStock ? `${currentStock.symbol} Price` : 'Price',
                        data: data.prices,
                        borderColor: lineColor,
                        backgroundColor: bgColor,
                        fill: true,
                        tension: 0.35,
                        borderWidth: 2,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        pointBackgroundColor: lineColor
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 600
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#111827',
                            borderColor: '#374151',
                            borderWidth: 1,
                            titleColor: '#f3f4f6',
                            bodyColor: '#f59e0b',
                            callbacks: {
                                label: function(context) {
                                    return ` ${context.parsed.y.toLocaleString()} Medals`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#6b7280',
                                font: { size: 10 }
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.05)'
                            },
                            ticks: {
                                color: '#9ca3af',
                                callback: function(val) {
                                    return val.toLocaleString() + ' M';
                                }
                            }
                        }
                    }
                }
            });
        }
    } catch (e) {
        console.error("Error loading chart data:", e);
    }
}

// ── Trade Controls ──────────────────────────────────────────────────────────
function adjustQty(delta) {
    const input = document.getElementById("trade-qty");
    if (!input) return;
    let val = parseInt(input.value) || 1;
    val = Math.max(1, Math.min(10, val + delta));
    input.value = val;
    updateTradeTotal();
}

function updateTradeTotal() {
    const input = document.getElementById("trade-qty");
    const totalEl = document.getElementById("trade-calc-total");
    if (!input || !totalEl) return;

    let qty = parseInt(input.value) || 1;
    qty = Math.max(1, Math.min(10, qty));

    const currentStock = allStocks.find(s => s.id === activeStockId);
    if (currentStock) {
        const total = qty * currentStock.price;
        totalEl.innerText = `${total.toLocaleString()} Medals`;
    } else {
        totalEl.innerText = "-- Medals";
    }
}

async function executeTrade(action) {
    if (!activeStockId) return showToast("Select a stock first.", true);

    const input = document.getElementById("trade-qty");
    const shares = parseInt(input.value) || 1;

    try {
        const res = await fetch(`/api/${action}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ stock_id: activeStockId, shares })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message);
            // Refresh stock info, chart, and portfolio
            loadStocks(true);
            loadPortfolio();
            // Reload page in 1.2s to refresh wallet balance display cleanly
            setTimeout(() => { window.location.reload(); }, 1200);
        } else {
            showToast(data.message, true);
        }
    } catch (err) {
        showToast(`Failed to execute ${action}.`, true);
    }
}

// ── User Portfolio ──────────────────────────────────────────────────────────
async function loadPortfolio() {
    const body = document.getElementById("portfolio-body");
    if (!body) return;

    try {
        const res = await fetch("/api/portfolio");
        if (!res.ok) return;
        const data = await res.json();
        const holdings = data.holdings || [];

        if (!holdings.length) {
            body.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted" style="padding: 1.5rem;">
                        No active stock holdings. Select an equity above to build your portfolio.
                    </td>
                </tr>
            `;
            return;
        }

        body.innerHTML = holdings.map(h => {
            const isProfit = h.profit >= 0;
            const sign = isProfit ? "+" : "";
            const profitClass = isProfit ? "text-emerald" : "text-crimson";

            return `
                <tr>
                    <td>
                        <strong>${h.symbol}</strong><br>
                        <small class="text-muted">${h.name}</small>
                    </td>
                    <td>
                        <strong>${h.shares}</strong> / 10
                    </td>
                    <td>${h.avg_buy_price.toLocaleString()} Medals</td>
                    <td><strong class="text-orange">${h.current_price.toLocaleString()}</strong> Medals</td>
                    <td>${h.current_value.toLocaleString()} Medals</td>
                    <td class="${profitClass}">
                        <strong>${sign}${h.profit.toLocaleString()}</strong> (${sign}${h.profit_pct}%)
                    </td>
                </tr>
            `;
        }).join("");
    } catch (e) {
        console.error("Error loading portfolio:", e);
    }
}

// ── Dual Leaderboards ───────────────────────────────────────────────────────
async function loadLeaderboards() {
    try {
        const res = await fetch("/api/leaderboards");
        if (!res.ok) return;
        const data = await res.json();

        // 1. Most Medals Globally
        const medalsContainer = document.getElementById("lb-medals-list");
        if (medalsContainer && data.medals) {
            if (!data.medals.length) {
                medalsContainer.innerHTML = '<div class="text-center text-muted p-3">No ranked users yet.</div>';
            } else {
                medalsContainer.innerHTML = data.medals.map(u => {
                    const rankMedal = u.rank === 1 ? '🥇' : u.rank === 2 ? '🥈' : u.rank === 3 ? '🥉' : `#${u.rank}`;
                    return `
                        <div class="lb-row ${u.rank === 1 ? 'top-1' : ''}">
                            <div class="lb-user">
                                <span class="lb-rank">${rankMedal}</span>
                                <img src="${u.avatar}" class="lb-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                                <span class="lb-name">${u.name}</span>
                            </div>
                            <div class="lb-val">
                                <strong class="text-orange">${u.medals.toLocaleString()}</strong>
                                <small class="text-muted">Medals</small>
                            </div>
                        </div>
                    `;
                }).join("");
            }
        }

        // 2. Best Gambler (Net Medals Won)
        const gambleContainer = document.getElementById("lb-gambling-list");
        if (gambleContainer && data.gambling) {
            if (!data.gambling.length) {
                gambleContainer.innerHTML = '<div class="text-center text-muted p-3">No recorded casino bets yet.</div>';
            } else {
                gambleContainer.innerHTML = data.gambling.map(u => {
                    const rankMedal = u.rank === 1 ? '🥇' : u.rank === 2 ? '🥈' : u.rank === 3 ? '🥉' : `#${u.rank}`;
                    const isProfit = u.net_profit >= 0;
                    const sign = isProfit ? "+" : "";
                    const profitClass = isProfit ? "text-emerald" : "text-crimson";

                    return `
                        <div class="lb-row ${u.rank === 1 ? 'top-1' : ''}">
                            <div class="lb-user">
                                <span class="lb-rank">${rankMedal}</span>
                                <img src="${u.avatar}" class="lb-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                                <div>
                                    <span class="lb-name">${u.name}</span>
                                    <div style="font-size: 0.72rem; color: var(--text-muted);">
                                        Won: ${u.total_won.toLocaleString()} | Lost: ${u.total_lost.toLocaleString()}
                                    </div>
                                </div>
                            </div>
                            <div class="lb-val">
                                <strong class="${profitClass}">${sign}${u.net_profit.toLocaleString()}</strong>
                                <small class="text-muted">Net Medals</small>
                            </div>
                        </div>
                    `;
                }).join("");
            }
        }
    } catch (e) {
        console.error("Error loading leaderboards:", e);
    }
}

// ── Web Banking Modals ──────────────────────────────────────────────────────
function openBankModal(action) {
    currentBankAction = action;
    const modal = document.getElementById("bank-modal");
    const title = document.getElementById("bank-modal-title");
    const sub = document.getElementById("bank-modal-sub");
    const btn = document.getElementById("bank-modal-submit-btn");
    const input = document.getElementById("bank-modal-amount");

    if (!modal) return;

    if (action === "deposit") {
        title.innerText = "Vault Deposit";
        sub.innerText = "Deposit medals from your active wallet into your secure bank vault.";
        btn.innerText = "Confirm Deposit";
    } else {
        title.innerText = "Vault Withdrawal";
        sub.innerText = "Withdraw medals from your bank vault back to your active wallet.";
        btn.innerText = "Confirm Withdrawal";
    }

    if (input) input.value = "";
    modal.style.display = "flex";
}

function closeBankModal() {
    const modal = document.getElementById("bank-modal");
    if (modal) modal.style.display = "none";
}

async function submitBankAction() {
    const input = document.getElementById("bank-modal-amount");
    const amount = parseInt(input.value);

    if (!amount || amount <= 0) {
        return showToast("Please enter a valid medals amount.", true);
    }

    try {
        const endpoint = currentBankAction === "deposit" ? "/api/bank/deposit" : "/api/bank/withdraw";
        const res = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message);
            closeBankModal();
            setTimeout(() => { window.location.reload(); }, 1000);
        } else {
            showToast(data.message, true);
        }
    } catch (err) {
        showToast("Banking transaction failed.", true);
    }
}
