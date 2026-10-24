/**
 * Phantom Regiment - Stock Market & Banking Interactive Engine
 */

let allStocks = [];
let activeStockId = null;
let stockChart = null;
let currentBankAction = 'deposit';

document.addEventListener("DOMContentLoaded", () => {
    initMarket();
    initPlayerCompanyForm();
    loadLeaderboards();
    if (document.getElementById("portfolio-body")) {
        loadPortfolio();
    }
    // Live Auto-Refresh Leaderboards every 5 seconds
    setInterval(() => {
        loadLeaderboards();
    }, 5000);
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

async function initPlayerCompanyForm() {
    const form = document.getElementById("player-company-form");
    if (!form) return;
    const status = document.getElementById("company-owner-status");
    try {
        const response = await fetch("/api/companies/mine");
        if (!response.ok) return;
        const data = await response.json();
        if (!data.company) return;
        status.innerText = data.company.name + " (" + data.company.symbol + ") is listed at " +
            Number(data.company.price).toLocaleString() + " Medals per share. AI review: " + data.company.ai_status +
            ". Company treasury: " + Number(data.company.treasury || 0).toLocaleString() + " Medals.";
        form.hidden = true;
    } catch (error) {
        status.innerText = "Your company listing could not be loaded.";
    }
}

async function submitPlayerCompany(event) {
    event.preventDefault();
    const form = document.getElementById("player-company-form");
    const status = document.getElementById("company-owner-status");
    const button = document.getElementById("company-submit");
    if (!form || !status || !button) return;
    button.disabled = true;
    status.innerText = "Submitting the company and checking the reported figures...";
    const payload = {
        name: document.getElementById("company-name").value.trim(),
        symbol: document.getElementById("company-symbol").value.trim().toUpperCase(),
        sector: document.getElementById("company-sector").value,
        valuation: document.getElementById("company-valuation").value,
        annual_revenue: document.getElementById("company-revenue").value,
        annual_profit: document.getElementById("company-profit").value,
        debt: document.getElementById("company-debt").value,
        description: document.getElementById("company-description").value.trim()
    };
    try {
        const response = await fetch("/api/companies/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        status.innerText = data.message || "Company submission failed.";
        if (response.ok && data.success) {
            form.hidden = true;
            await loadStocks(true);
        } else {
            button.disabled = false;
        }
    } catch (error) {
        status.innerText = "Company submission failed. Please try again.";
        button.disabled = false;
    }
}

// ── Stock Loading & Rendering ────────────────────────────────────────────────
async function loadStocks(silent = false) {
    try {
        const res = await fetch("/api/stocks");
        if (!res.ok) return;
        allStocks = await res.json();

        if (allStocks.length > 0) {
            const first = allStocks[0];
            const newsEl = document.getElementById("stock-news-text");
            const bannerEl = document.getElementById("stock-news-banner");
            if (newsEl && first.market_news) {
                newsEl.innerText = first.market_news;
            }
            if (bannerEl && first.market_regime) {
                if (first.market_regime === "BULL_RALLY") {
                    bannerEl.style.background = "linear-gradient(90deg, rgba(34, 197, 94, 0.25) 0%, rgba(16, 185, 129, 0.1) 100%)";
                    bannerEl.style.borderColor = "#22c55e";
                    bannerEl.style.boxShadow = "0 0 15px rgba(34, 197, 94, 0.3)";
                } else if (first.market_regime === "BEAR_CRASH") {
                    bannerEl.style.background = "linear-gradient(90deg, rgba(239, 68, 68, 0.25) 0%, rgba(220, 38, 38, 0.1) 100%)";
                    bannerEl.style.borderColor = "#ef4444";
                    bannerEl.style.boxShadow = "0 0 15px rgba(239, 68, 68, 0.35)";
                } else {
                    bannerEl.style.background = "rgba(56, 189, 248, 0.1)";
                    bannerEl.style.borderColor = "var(--border-blue)";
                    bannerEl.style.boxShadow = "none";
                }
            }
        }

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
                        ${s.company_owner_id ? `<div style="font-size:0.68rem;color:#94a3b8;">${s.company_sector || "Player company"}</div>` : ""}
                    </div>
                    <span class="${isUp ? 'tag-up' : 'tag-down'}">
                        ${sign}${s.change_pct}%
                    </span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="stock-price text-blue">${s.price.toLocaleString()} Medals</div>
                    <span style="color:#22c55e; font-size:0.68rem; font-weight:800; background:rgba(34,197,94,0.12); padding:0.15rem 0.4rem; border-radius:4px;">💰 +2% Div</span>
                </div>
                <div class="stock-footer">
                    <span>Avail: ${s.available_shares} / ${s.total_supply}</span>
                    <span>Max: 250/usr</span>
                </div>
                ${s.company_owner_id ? `<div style="font-size:0.68rem;margin-top:0.35rem;color:${s.ai_status === "approved" ? "#86efac" : "#fca5a5"};">AI review: ${s.ai_status === "approved" ? "approved" : "crash-adjusted"} • fair value ${Number(s.fair_value || 0).toLocaleString()} M • treasury ${Number(s.company_treasury || 0).toLocaleString()} M</div>` : ""}
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
    stockId = parseInt(stockId) || stockId;
    activeStockId = stockId;
    const stock = allStocks.find(s => s.id == stockId);
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

        const lineColor = isUp ? "#38bdf8" : "#ef4444";
        const bgColor = isUp ? "rgba(56, 189, 248, 0.08)" : "rgba(239, 68, 68, 0.08)";

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
                        duration: 400
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#0f1930',
                            borderColor: '#1e293b',
                            borderWidth: 1,
                            titleColor: '#f8fafc',
                            bodyColor: '#38bdf8',
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
                                color: 'rgba(56, 189, 248, 0.04)'
                            },
                            ticks: {
                                color: '#64748b',
                                font: { size: 10 }
                            }
                        },
                        y: {
                            grid: {
                                color: 'rgba(56, 189, 248, 0.04)'
                            },
                            ticks: {
                                color: '#94a3b8',
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
function setQty(val) {
    const input = document.getElementById("trade-qty");
    if (!input) return;
    input.value = Math.max(1, Math.min(250, parseInt(val) || 1));
    updateTradeTotal();
}

function adjustQty(delta) {
    const input = document.getElementById("trade-qty");
    if (!input) return;
    let val = parseInt(input.value) || 1;
    val = Math.max(1, Math.min(250, val + delta));
    input.value = val;
    updateTradeTotal();
}

function updateTradeTotal() {
    const input = document.getElementById("trade-qty");
    const totalEl = document.getElementById("trade-calc-total");
    if (!input || !totalEl) return;

    let qty = parseInt(input.value) || 1;
    qty = Math.max(1, Math.min(250, qty));

    const currentStock = allStocks.find(s => s.id == activeStockId);
    if (currentStock) {
        const estGross = qty * currentStock.price;
        const estTax = Math.round(estGross * 0.15);
        const estNetSell = Math.max(1, estGross - estTax);
        const estDiv = Math.min(250, Math.max(1, Math.round(estGross * 0.004)));
        totalEl.innerHTML = `
            <div><strong>Buy Est:</strong> ${estGross.toLocaleString()} Medals</div>
            <div style="font-size:0.74rem; color:#94a3b8; margin-top:2px;">
                <strong>Sell Est:</strong> ${estNetSell.toLocaleString()} M <span style="color:#ef4444;">(-15% Market Tax: ${estTax.toLocaleString()} M)</span>
            </div>
            <div style="font-size:0.72rem; color:#22c55e; margin-top:2px;">
                💰 +${estDiv.toLocaleString()} M / Div Cycle
            </div>
        `;
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
        let data;
        try {
            data = await res.json();
        } catch (jsonErr) {
            return showToast(`Server error (${res.status}). Please try again.`, true);
        }

        if (data.success) {
            showToast(data.message);

            // Update live wallet balance immediately if returned
            if (data.wallet !== undefined) {
                const walletEl = document.getElementById("user-wallet-val");
                if (walletEl) walletEl.innerText = Number(data.wallet).toLocaleString();
            }

            // Immediately refresh stock ticker, active chart, and portfolio table
            await loadStocks(true);
            if (activeStockId) {
                await loadChart(activeStockId);
            }
            if (document.getElementById("portfolio-body")) {
                loadPortfolio();
            }
            loadLeaderboards();
        } else {
            showToast(data.message, true);
        }
    } catch (err) {
        showToast(`Network error executing ${action}.`, true);
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
                        No active stock holdings. Select a stock above to start trading.
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
                        <strong>${h.shares}</strong> / 250
                    </td>
                    <td>${h.avg_buy_price.toLocaleString()} Medals</td>
                    <td><strong class="text-blue">${h.current_price.toLocaleString()}</strong> Medals</td>
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

// ── Dual Leaderboards (Live Auto-Updating) ──────────────────────────────────
let _lastMedalsJson = "";
let _lastGamblingJson = "";

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function renderCombatChampions(champions) {
    const container = document.getElementById("combat-champions-podium");
    if (!container || !champions) return;

    const ranks = [
        { key: 'top_1', tier: 'tier-1', badge: '👑 🥇 RANK #1 SUPREME CHAMPION', title: 'Top 1 Contributor • Highest Wins & Kills' },
        { key: 'top_2', tier: 'tier-2', badge: '⚔️ 🥈 RANK #2 MASTER TACTICIAN', title: 'Top 2 Contributor • Frontline Dominance' },
        { key: 'top_3', tier: 'tier-3', badge: '🛡️ 🥉 RANK #3 VANGUARD ELITE', title: 'Top 3 Contributor • Heavy Assault' }
    ];

    container.innerHTML = ranks.map(r => {
        const members = champions[r.key] || [];
        if (members.length === 0) {
            return `
                <div class="combat-card ${r.tier}">
                    <div class="combat-badge-pill">${r.badge}</div>
                    <div class="combat-pfp-wrap">
                        <img src="https://cdn.discordapp.com/embed/avatars/0.png" class="combat-pfp">
                    </div>
                    <div class="combat-big-name" style="color:var(--text-muted); font-size:1.2rem;">Vacant Rank</div>
                    <div class="combat-sub-desc">${r.title}</div>
                </div>
            `;
        }

        return members.map(m => `
            <div class="combat-card ${r.tier}">
                <div class="combat-badge-pill">${r.badge}</div>
                <div class="combat-pfp-wrap">
                    <img src="${m.avatar}" class="combat-pfp" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                </div>
                <div class="combat-big-name">${escapeHtml(m.name)}</div>
                <div style="font-size: 0.75rem; color: var(--blue-primary); font-family: var(--font-mono); font-weight: 700; margin-bottom: 0.25rem;">@${escapeHtml(m.username)}</div>
                <div class="combat-sub-desc">${r.title}</div>
            </div>
        `).join("");
    }).join("");
}

async function loadLeaderboards() {
    try {
        const res = await fetch("/api/leaderboards");
        if (!res.ok) return;
        const data = await res.json();

        // 0. Combat Champions Podium (Command an Army)
        const combatContainer = document.getElementById("combat-champions-podium");
        if (combatContainer && data.combat_champions) {
            renderCombatChampions(data.combat_champions);
        }

        // 1. Most Medals Globally (Live)
        const medalsContainer = document.getElementById("lb-medals-list");
        if (medalsContainer && data.medals) {
            const currentStr = JSON.stringify(data.medals);
            if (currentStr !== _lastMedalsJson) {
                _lastMedalsJson = currentStr;
                if (!data.medals.length) {
                    medalsContainer.innerHTML = '<div class="text-center text-muted p-3">No ranked users yet.</div>';
                } else {
                    medalsContainer.innerHTML = data.medals.map(u => {
                        const rankMedal = u.rank === 1 ? '🥇' : u.rank === 2 ? '🥈' : u.rank === 3 ? '🥉' : `#${u.rank}`;
                        const rowClass = u.rank === 1 ? 'top-1' : u.rank === 2 ? 'top-2' : u.rank === 3 ? 'top-3' : '';
                        return `
                            <div class="lb-row ${rowClass}">
                                <div class="lb-user">
                                    <span class="lb-rank">${rankMedal}</span>
                                    <img src="${u.avatar}" class="lb-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                                    <span class="lb-name">${u.name}</span>
                                </div>
                                <div class="lb-val">
                                    <strong class="text-blue">${u.medals.toLocaleString()}</strong>
                                    <small class="text-muted">Medals</small>
                                </div>
                            </div>
                        `;
                    }).join("");
                }
            }
        }

        // 2. Best Gambler (Live Net Medals Won)
        const gambleContainer = document.getElementById("lb-gambling-list");
        if (gambleContainer && data.gambling) {
            const gambleStr = JSON.stringify(data.gambling);
            if (gambleStr !== _lastGamblingJson) {
                _lastGamblingJson = gambleStr;
                if (!data.gambling.length) {
                    gambleContainer.innerHTML = `
                        <div class="lb-empty-box">
                            <div style="font-size: 1.8rem; margin-bottom: 0.35rem;">🎰</div>
                            <div style="font-weight: 700; color: var(--text-white); margin-bottom: 0.25rem;">Season 1 Casino Live!</div>
                            <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.45;">
                                Play <code>/coinflip</code>, <code>/blackjack</code>, <code>/roulette</code>, or <code>/crash</code> in Discord to compete for #1!
                            </div>
                        </div>
                    `;
                } else {
                    gambleContainer.innerHTML = data.gambling.map(u => {
                        const rankMedal = u.rank === 1 ? '🥇' : u.rank === 2 ? '🥈' : u.rank === 3 ? '🥉' : `#${u.rank}`;
                        const rowClass = u.rank === 1 ? 'top-1' : u.rank === 2 ? 'top-2' : u.rank === 3 ? 'top-3' : '';
                        const isProfit = u.net_profit >= 0;
                        const sign = isProfit ? "+" : "";
                        const profitClass = isProfit ? "text-emerald" : "text-crimson";

                        return `
                            <div class="lb-row ${rowClass}">
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
        sub.innerText = "Deposit medals from your wallet into your vault.";
        btn.innerText = "Confirm Deposit";
    } else {
        title.innerText = "Vault Withdrawal";
        sub.innerText = "Withdraw medals from your vault back to your wallet.";
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

            // Update live balances immediately if returned
            if (data.wallet !== undefined) {
                const walletEl = document.getElementById("user-wallet-val");
                if (walletEl) walletEl.innerText = Number(data.wallet).toLocaleString();
            }
            if (data.vault !== undefined) {
                const vaultEl = document.getElementById("user-vault-val");
                if (vaultEl) vaultEl.innerText = Number(data.vault).toLocaleString();
            }
            loadLeaderboards();
        } else {
            showToast(data.message, true);
        }
    } catch (err) {
        showToast("Banking transaction failed.", true);
    }
}
