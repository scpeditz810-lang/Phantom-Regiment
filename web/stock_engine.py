# -*- coding: utf-8 -*-
"""
Phantom Regiment Stock Market Engine
Features:
- Realistic Multi-Regime Dynamics: Green Zones (Bull Rallies), Stock Crashes (Bear Markets), and Sideways Consolidation
- Real-life Catalyst Events: Positive contract blowouts & Negative catastrophic crashes / scandals
- Valuation Gravity & Profit-Taking: Prevents runaway infinite inflation
- Passive Dividends with safety caps
"""

import time
import random
import threading
import asyncio

BULL_CATALYSTS = [
    ("PRC", "🚀 [GREEN ZONE SURGE] Phantom Regiment Corp secures 50M sovereign defense contract! Bull rally surging.", (0.12, 0.24)),
    ("TSC", "🚀 [GREEN ZONE SURGE] TS Clan Holdings smashes consensus profits! Heavy institutional buying.", (0.10, 0.22)),
    ("VNG", "⚔️ [GREEN ZONE SURGE] Vanguard Armaments unveils next-gen kinetic titan armor! Global demand peaks.", (0.12, 0.25)),
    ("AERO", "🛰️ [GREEN ZONE SURGE] Apex Aerospace launches orbital defense constellation! Stock price surging.", (0.10, 0.20)),
    ("CRYP", "💎 [GREEN ZONE SURGE] Cypher Intelligence cracks foreign sovereign ledger! Quantum rally initiated.", (0.12, 0.24)),
    ("TSLA", "⚡ [GREEN ZONE SURGE] Tesla autonomous defense units deployed across all clans! Massive bull run.", (0.12, 0.26)),
    ("PANDA", "🍜 [GREEN ZONE SURGE] PandaPo signs continental ration logistics monopoly! Record volume buying.", (0.12, 0.25)),
    ("PRC", "🔥 [SHORT SQUEEZE] Massive short squeeze on Phantom Regiment Corp! Short sellers forced to liquidate.", (0.15, 0.32)),
    ("TSLA", "🚀 [MEGA BREAKOUT] Tesla announces fusion micro-reactor prototype! Valuation skyrockets.", (0.15, 0.30)),
    ("TSC", "🏦 [INSTITUTIONAL INFLOW] TS Clan sovereign treasury announces 20M strategic buyback!", (0.10, 0.20))
]

CRASH_CATALYSTS = [
    ("PRC", "💥 [STOCK CRASH] Phantom Regiment Corp hit with federal whistleblower audit! Panic selling ensues.", (-0.18, -0.32)),
    ("TSC", "📉 [STOCK CRASH] TS Clan Holdings quarterly earnings miss! Institutional investors dump massive blocks.", (-0.15, -0.28)),
    ("VNG", "💥 [RECALL CRASH] Vanguard Armaments issues catastrophic kinetic armor recall! Shares plummet.", (-0.20, -0.35)),
    ("AERO", "📉 [CRASH ALERT] Apex Aerospace orbital satellite explodes during launch! Stock value collapses.", (-0.16, -0.30)),
    ("CRYP", "💥 [SECURITY BREACH] Cypher Intelligence reports critical zero-day network breach! Mass liquidation.", (-0.18, -0.32)),
    ("TSLA", "📉 [STOCK CRASH] Tesla slapped with sweeping antitrust monopoly sanctions! Heavy margin call dumps.", (-0.20, -0.36)),
    ("PANDA", "💥 [SUPPLY SHOCK] PandaPo supply warehouses hit with catastrophic trade embargo! Shares dump.", (-0.15, -0.28)),
    ("PRC", "📉 [PROFIT TAKING CRASH] Hedge funds orchestrate coordinated dump on Phantom Regiment Corp!", (-0.16, -0.28)),
    ("GLOBAL", "🚨 [MARKET-WIDE FLASH CRASH] Global trade dispute triggers market bloodbath! All equities plunging.", (-0.14, -0.26)),
    ("GLOBAL", "💥 [BLACK SWAN CRASH] Exchange liquidity crisis! Algorithmic cascading stop-loss liquidations.", (-0.16, -0.30))
]


class StockMarketEngine:
    def __init__(self, db, bot_loop=None, tick_interval: int = 55):
        self.db = db
        self.bot_loop = bot_loop
        self.tick_interval = tick_interval
        self._running = False
        self._thread = None
        self.tick_count = 0
        self.market_regime = "SIDEWAYS"  # 'BULL_RALLY', 'BEAR_CRASH', 'SIDEWAYS'
        self.regime_ticks_left = 20
        self.latest_news = "📈 Market Open: High-volume trading active across corporate equities."
        self.last_dividend_time = time.time()

    def get_regime_display_name(self) -> str:
        if self.market_regime == "BULL_RALLY":
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
        print("[Stock Market Engine] Started background price fluctuation ticker with Green Zones, Crashes & Valuations.", flush=True)

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

        # Rotate Market Regime when cycle expires (every 15 to 30 ticks ~15 to 30 mins)
        if self.regime_ticks_left <= 0:
            regimes = ["SIDEWAYS", "BULL_RALLY", "BEAR_CRASH"]
            weights = [0.45, 0.275, 0.275]  # 45% sideways, 27.5% Green Zone, 27.5% Crash Zone
            self.market_regime = random.choices(regimes, weights=weights)[0]
            self.regime_ticks_left = random.randint(15, 30)

            if self.market_regime == "BULL_RALLY":
                self.latest_news = "🟢 [GREEN ZONE ACTIVATED] Global Bull Run! Strong institutional liquidity surging into corporate equities!"
                print(f"[Stock Market] {self.latest_news}", flush=True)
            elif self.market_regime == "BEAR_CRASH":
                self.latest_news = "🔴 [MARKET CRASH IN PROGRESS] Heavy Panic Selling! Cascading liquidations and margin calls dragging equities downward!"
                print(f"[Stock Market] {self.latest_news}", flush=True)
            else:
                self.latest_news = "⚪ [MARKET CONSOLIDATION] Equilibrium trading active. Equities oscillating around fair valuation."

        stocks = await self.db.get_all_stocks()
        if not stocks:
            return

        # Catalyst Events: 1 in 18 chance per tick
        catalyst_symbol = None
        catalyst_multiplier = 0.0

        if self.tick_count % random.randint(16, 24) == 0:
            # Pick Bull catalyst if in Bull Rally, Crash catalyst if in Bear Crash, or random in Sideways
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

            # 1. Catalyst Override
            if catalyst_symbol == sym or catalyst_symbol == "GLOBAL":
                change_percent = catalyst_multiplier

            # 2. Market Regime Fluctuation
            elif self.market_regime == "BULL_RALLY":
                # Green Zone: 68% green ticks, 32% red pullbacks
                if random.random() < 0.68:
                    change_percent = random.uniform(0.012, 0.038)
                else:
                    change_percent = random.uniform(-0.016, -0.005)

            elif self.market_regime == "BEAR_CRASH":
                # Crash Zone: 68% red drops, 32% green dead-cat bounces
                if random.random() < 0.68:
                    change_percent = random.uniform(-0.038, -0.012)
                else:
                    change_percent = random.uniform(0.005, 0.016)

            else:
                # Sideways Normal Market: Perfectly balanced symmetrical zero-drift random walk
                change_percent = random.uniform(-0.014, 0.014)

            # 3. Valuation Gravity / Profit-Taking Damping (Prevents 40M runaway inflation!)
            # When stock price is hugely inflated (e.g. > 10,000 Medals), natural institutional profit taking exerts downward pressure
            if old_price > 5000:
                drag = min(0.025, 0.004 * (old_price / 10000.0))
                change_percent -= drag

            # 4. Support Wall for Low Stocks
            if old_price <= 30 and change_percent < 0:
                # Value investors buy the floor
                change_percent = random.uniform(0.02, 0.06)

            diff = int(round(old_price * change_percent))
            if diff == 0:
                diff = random.choice([-1, 0, 1])

            # Hard Floor of 15 Medals (stocks never go to 0)
            new_price = max(15, old_price + diff)
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
        """Distribute passive dividend payouts with safety caps."""
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
                # 0.25% dividend yield based on current share price
                div_per_share = max(1, int(round(h["price"] * 0.0025)))
                # Capped at max 350 Medals per stock position to prevent infinite AFK printing
                total_div = min(350, div_per_share * h["shares"])
                if total_div > 0:
                    await self.db.add_medals(h["user_id"], 0, total_div)
                    total_paid += total_div

            self.last_dividend_time = time.time()
            if total_paid > 0:
                print(f"[Stock Market] Distributed {total_paid:,} Medals in dividends across {len(holders)} positions.", flush=True)
        except Exception as e:
            print(f"[Stock Market] Dividend error: {e}", flush=True)
