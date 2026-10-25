# -*- coding: utf-8 -*-
"""
Phantom Regiment Stock Market Engine
Features:
- Realistic Multi-Regime Dynamics: Green Zones (Bull Rallies), Stock Crashes (Bear Markets), and Sideways Consolidation
- Real-life Catalyst Events: Positive contract blowouts & Negative crashes / scandals
- High-Value Equities: Realistic trading in the 5,000 - 250,000 Medals range
- Strict Upper Ceilings: Prevents runaway hyper-inflation past max brackets
- Mean-Reversion Valuation Gravity: Pulls over-extended stocks back to baseline
- Passive Dividends with safety caps (max 1,500 Medals/position)
"""

import time
import random
import threading
import asyncio

DEFAULT_STOCK_BOUNDS = {
    "PRC": {"base": 42000, "min": 15000, "max": 120000},
    "TSC": {"base": 120000, "min": 35000, "max": 250000},
    "VNG": {"base": 5000, "min": 1200, "max": 45000},
    "AERO": {"base": 15000, "min": 3500, "max": 65000},
    "CRYP": {"base": 28000, "min": 7500, "max": 95000},
    "TSLA": {"base": 115000, "min": 35000, "max": 250000},
    "PANDA": {"base": 9000, "min": 2500, "max": 35000},
}

BULL_CATALYSTS = [
    ("VNG", "⚔️ [WARTIME PROCUREMENT] Vanguard Armaments awarded emergency munitions contract for active Earth conflict!", (0.08, 0.16)),
    ("AERO", "🛰️ [COMBAT SATELLITE DEMAND] Apex Aerospace orbital recon contracted by combatant powers! Stock breaking out.", (0.07, 0.15)),
    ("PRC", "🛡️ [TACTICAL PMC CONTRACT] Phantom Regiment Corp deploys defensive battalions to active war theater!", (0.06, 0.14)),
    ("GLOBAL", "⚔️ [GLOBAL WAR MOBILIZATION] Virtual Earth military escalations trigger defense sector rally!", (0.05, 0.12)),
    ("PRC", "🚀 [GREEN ZONE SURGE] Phantom Regiment Corp secures sovereign defense contract! Bull rally surging.", (0.06, 0.13)),
    ("TSC", "🚀 [GREEN ZONE SURGE] TS Clan Holdings smashes consensus profits! Heavy institutional buying.", (0.05, 0.12)),
    ("VNG", "⚔️ [GREEN ZONE SURGE] Vanguard Armaments unveils next-gen kinetic armor! Global demand peaks.", (0.06, 0.14)),
    ("AERO", "🛰️ [GREEN ZONE SURGE] Apex Aerospace launches orbital defense constellation! Stock price surging.", (0.05, 0.12)),
    ("CRYP", "💎 [GREEN ZONE SURGE] Cypher Intelligence cracks foreign sovereign ledger! Quantum rally initiated.", (0.06, 0.13)),
    ("TSLA", "⚡ [GREEN ZONE SURGE] Tesla autonomous defense units deployed across all clans! Bull run active.", (0.06, 0.14)),
    ("PANDA", "🍜 [GREEN ZONE SURGE] PandaPo signs continental ration logistics contract! Record volume buying.", (0.06, 0.13)),
    ("PRC", "🔥 [SHORT SQUEEZE] Short squeeze on Phantom Regiment Corp! Short sellers forced to liquidate.", (0.07, 0.16)),
    ("TSLA", "🚀 [MEGA BREAKOUT] Tesla announces fusion micro-reactor prototype! Valuation climbs.", (0.07, 0.15)),
    ("TSC", "🏦 [INSTITUTIONAL INFLOW] TS Clan sovereign treasury announces strategic buyback!", (0.05, 0.12))
]

CRASH_CATALYSTS = [
    ("PANDA", "🚢 [STRAIT BLOCKADE] Commercial shipping corridors blocked by active naval warfare! PandaPo logistics delayed.", (-0.08, -0.16)),
    ("PRC", "💥 [STOCK CRASH] Phantom Regiment Corp hit with federal whistleblower audit! Panic selling ensues.", (-0.09, -0.18)),
    ("TSC", "📉 [STOCK CRASH] TS Clan Holdings quarterly earnings miss! Institutional investors dump blocks.", (-0.08, -0.16)),
    ("VNG", "💥 [RECALL CRASH] Vanguard Armaments issues kinetic armor recall! Shares pull back.", (-0.10, -0.18)),
    ("AERO", "📉 [CRASH ALERT] Apex Aerospace test satellite anomaly during launch! Stock value drops.", (-0.08, -0.16)),
    ("CRYP", "💥 [SECURITY BREACH] Cypher Intelligence reports network breach! Profit-taking liquidations.", (-0.09, -0.18)),
    ("TSLA", "📉 [STOCK CRASH] Tesla slapped with regulatory scrutiny! Margin call dumps.", (-0.10, -0.18)),
    ("PANDA", "💥 [SUPPLY SHOCK] PandaPo supply warehouses hit with regional embargo! Shares drop.", (-0.08, -0.16)),
    ("PRC", "📉 [PROFIT TAKING CRASH] Institutional funds orchestrate planned profit-taking on Phantom Regiment Corp!", (-0.08, -0.16)),
    ("GLOBAL", "🚨 [MARKET-WIDE PULLBACK] Global trade tensions trigger market-wide equity pullback.", (-0.07, -0.14)),
    ("GLOBAL", "💥 [FLASH CORRECTION] Market-wide technical correction! Cascading stop-loss triggers.", (-0.08, -0.16))
]


class StockMarketEngine:
    def __init__(self, db, bot_loop=None, tick_interval: int = 55):
        self.db = db
        self.bot_loop = bot_loop
        self.tick_interval = tick_interval
        self._running = False
        self._thread = None
        self.tick_count = 0
        self.market_regime = "SIDEWAYS"  # 'BULL_RALLY', 'BEAR_CRASH', 'SIDEWAYS', 'WARTIME_ECONOMY'
        self.regime_ticks_left = 20
        self.latest_news = "📈 Market Open: High-volume trading active across corporate equities."
        self.last_dividend_time = time.time()

    def get_regime_display_name(self) -> str:
        if self.market_regime == "WARTIME_ECONOMY":
            return "⚔️ Wartime Economy (Defense Active)"
        elif self.market_regime == "BULL_RALLY":
            return "🟢 Green Zone (Bull Market)"
        elif self.market_regime == "BEAR_CRASH":
            return "🔴 Market Crash (Bear Market)"
        return "⚪ Sideways (Consolidation)"

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Stock Market Engine] Started background price fluctuation ticker with natural brackets & valuation gravity.", flush=True)

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            try:
                time.sleep(self.tick_interval)
                if self.bot_loop and self.bot_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self._tick(), self.bot_loop)
                    future.result(timeout=20)
                else:
                    asyncio.run(self._tick())
            except Exception as e:
                print(f"[Stock Market Engine] Tick error: {e}", flush=True)

    async def _tick(self):
        self.tick_count += 1
        self.regime_ticks_left -= 1

        # ── Virtual Earth Active War Integration ──
        active_wars = []
        try:
            active_wars = await self.db.get_active_earth_wars()
        except Exception:
            active_wars = []

        war_count = len(active_wars)

        if war_count > 0:
            self.market_regime = "WARTIME_ECONOMY"
            first_war = active_wars[0]
            atk_n = first_war.get("attacker_name", "Attacker")
            dfn_n = first_war.get("defender_name", "Defender")
            if self.tick_count % 3 == 0:
                self.latest_news = f"⚔️ [WARTIME MOBILIZATION] {war_count} Active War(s) on Virtual Earth ({atk_n} vs {dfn_n})! Defense contractors (VNG, AERO, PRC) in focus."
        elif self.regime_ticks_left <= 0:
            # Rotate Market Regime when cycle expires (every 15 to 30 ticks)
            regimes = ["SIDEWAYS", "BULL_RALLY", "BEAR_CRASH"]
            weights = [0.45, 0.275, 0.275]  # 45% sideways, 27.5% Green Zone, 27.5% Crash Zone
            self.market_regime = random.choices(regimes, weights=weights)[0]
            self.regime_ticks_left = random.randint(15, 30)

            if self.market_regime == "BULL_RALLY":
                self.latest_news = "🟢 [GREEN ZONE ACTIVATED] Global Bull Run! Strong institutional liquidity surging into corporate equities!"
            elif self.market_regime == "BEAR_CRASH":
                self.latest_news = "🔴 [MARKET CORRECTION] Profit Taking Underway! Orderly pullbacks across corporate equities."
            else:
                self.latest_news = "⚪ [MARKET CONSOLIDATION] Equilibrium trading active. Equities oscillating around fair valuation."

        stocks = await self.db.get_all_stocks()
        if not stocks:
            return

        # Catalyst Events: 1 in 18 chance per tick
        catalyst_symbol = None
        catalyst_multiplier = 0.0

        if self.tick_count % random.randint(16, 24) == 0:
            if self.market_regime == "BULL_RALLY":
                pool = BULL_CATALYSTS
            elif self.market_regime == "BEAR_CRASH":
                pool = CRASH_CATALYSTS
            else:
                pool = random.choice([BULL_CATALYSTS, CRASH_CATALYSTS])

            sym, news, (min_pct, max_pct) = random.choice(pool)
            catalyst_symbol = sym
            catalyst_multiplier = random.uniform(min_pct, max_pct)
            self.latest_news = news
            print(f"[Stock Market Catalyst] {news} ({catalyst_multiplier*100:+.1f}%)", flush=True)

        for stock in stocks:
            old_price = stock["price"]
            sym = stock["symbol"]
            bounds = DEFAULT_STOCK_BOUNDS.get(sym, {"base": 30000, "min": 5000, "max": 150000})
            # Player companies use their reviewed fair value rather than the
            # generic market brackets, preventing runaway valuation bubbles.
            is_company_stock = bool(stock.get("company_owner_id"))
            if is_company_stock:
                fair_value = max(100_000, int(stock.get("fair_value") or 0))
                supply = max(1, int(stock.get("total_supply") or 2500))
                # The exchange has a 2,000–80,000 price range. The old
                # company calculation produced fair shares such as 40 M
                # (100,000 valuation / 2,500 shares), then every update was
                # clamped back to 2,000, making the stock permanently stuck.
                fair_share = max(2_000, min(80_000, fair_value / supply))
                bounds = {
                    "base": int(round(fair_share)),
                    "min": max(2_000, int(round(fair_share * 0.25))),
                    "max": min(80_000, max(2_000, int(round(fair_share * 2.5)))),
                }
            base_p = bounds["base"]
            min_p = bounds["min"]
            max_p = bounds["max"]

            # Safety check: if existing DB price is runaway past ceiling, clamp immediately
            if old_price > max_p:
                old_price = max_p
                await self.db.update_stock_price(stock["id"], max_p)

            # 1. Catalyst Override
            if catalyst_symbol == sym or catalyst_symbol == "GLOBAL":
                change_percent = catalyst_multiplier

            # 2. Market Regime Fluctuation
            elif self.market_regime == "WARTIME_ECONOMY":
                # Wartime Dynamics: Defense contractors gain with realistic profit-taking pullbacks
                if sym in {"VNG", "AERO", "PRC"}:
                    if random.random() < 0.58:
                        change_percent = random.uniform(0.015, 0.035)
                    else:
                        change_percent = -random.uniform(0.010, 0.022)
                elif sym in {"PANDA"}:
                    change_percent = -random.uniform(0.010, 0.022)
                elif sym in {"CRYP"}:
                    change_percent = random.uniform(-0.020, 0.025)
                else:
                    change_percent = random.uniform(-0.012, 0.015)

            elif self.market_regime == "BULL_RALLY":
                # Green Zone: 60% green ticks, 40% red pullbacks
                if random.random() < 0.60:
                    change_percent = random.uniform(0.012, 0.028)
                else:
                    change_percent = -random.uniform(0.010, 0.020)

            elif self.market_regime == "BEAR_CRASH":
                # Crash Zone: 60% red drops, 40% green dead-cat bounces
                if random.random() < 0.60:
                    change_percent = -random.uniform(0.015, 0.032)
                else:
                    change_percent = random.uniform(0.008, 0.018)

            else:
                # Sideways Normal Market: balanced zero-drift random walk
                change_percent = random.uniform(-0.014, 0.014)

            # 3. Valuation Gravity / Mean-Reversion Pull
            # If stock is trading significantly above fair base value, profit taking pulls it down
            if old_price > base_p * 1.35:
                overval_ratio = (old_price - base_p * 1.35) / float(base_p)
                drag = min(0.06, 0.025 * overval_ratio)
                change_percent -= drag
            elif old_price < base_p * 0.70 and change_percent < 0:
                # Value support floor
                change_percent = random.uniform(0.015, 0.035)

            # Company circuit breaker: a single market tick cannot move a
            # player-company share more than 0.75% in either direction.
            if is_company_stock:
                change_percent = max(-0.0075, min(0.0075, change_percent))

            diff = int(round(old_price * change_percent))
            if diff == 0:
                diff = random.choice([-1, 0, 1])

            # HARD CLAMP: Enforce strict min and max bounds (absolutely impossible to exceed max ceiling)
            new_price = max(min_p, min(max_p, old_price + diff))
            if new_price != old_price:
                await self.db.update_stock_price(stock["id"], new_price)

        # Distribute Dividends every 20 ticks (~18 minutes)
        if self.tick_count % 20 == 0:
            await self._distribute_dividends()

        # Prune ancient history (keep last 300 data points)
        try:
            await self.db._db.execute("""
                DELETE FROM stock_history WHERE id NOT IN (
                    SELECT id FROM stock_history
                    ORDER BY timestamp DESC
                    LIMIT 300
                )
            """)
            await self.db._db.commit()
        except Exception:
            pass

    async def _distribute_dividends(self):
        """Distribute passive dividend payouts with natural safety caps."""
        try:
            async with self.db._db.execute("""
                SELECT us.user_id, us.stock_id, us.shares, s.price, s.symbol
                FROM user_stocks us
                JOIN stocks s ON us.stock_id = s.id
                WHERE us.shares > 0
            """) as cur:
                holders = [dict(r) for r in await cur.fetchall()]

            if not holders:
                return

            total_paid = 0
            for h in holders:
                # Conservative 0.05% dividend yield based on current share price
                div_per_share = max(1, int(round(h["price"] * 0.0005)))
                # Capped at 250 Medals per stock position per payout cycle
                total_div = min(250, div_per_share * h["shares"])
                if total_div > 0:
                    await self.db.add_medals(h["user_id"], 0, total_div)
                    total_paid += total_div

            self.last_dividend_time = time.time()
            if total_paid > 0:
                print(f"[Stock Market] Distributed {total_paid:,} Medals in dividends across {len(holders)} positions.", flush=True)
        except Exception as e:
            print(f"[Stock Market] Dividend error: {e}", flush=True)
