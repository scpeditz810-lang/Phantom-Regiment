import time
import random
import threading
import asyncio

CATALYST_EVENTS = [
    ("PRC", "📈 [CONTRACT] Phantom Regiment Corp secures 50M defense logistics contract! Bull rally initiated."),
    ("TSC", "🚀 [EARNINGS] TS Clan Holdings posts record clan dividend yields! Heavy institutional buying."),
    ("VNG", "⚔️ [WEAPONS] Vanguard Armaments unveils next-gen kinetic armor plating! Demand surges."),
    ("AERO", "🛰️ [SURVEILLANCE] Apex Aerospace successfully launches sub-orbital stealth drone constellation!"),
    ("CRYP", "💎 [TECH] Cypher Intelligence intercepts high-value encrypted network ledger! Breakthrough rally."),
    ("TSLA", "⚡ [INNOVATION] Tesla automated defense units deployed across clan strongholds! Rally surging."),
    ("PANDA", "🍜 [MERGER] PandaPo signs multi-district tactical ration supply pact! Stock value climbing."),
    ("PRC", "⚡ [EXPANSION] Phantom Regiment opens 3 new tactical training grounds. Valuation upgraded."),
    ("TSC", "🏦 [BUYBACK] TS Clan treasury initiates strategic stock buyback program!"),
    ("VNG", "🛡️ [UPGRADE] Vanguard Armaments signs alliance defense pact with sovereign clans.")
]

class StockMarketEngine:
    def __init__(self, db, bot_loop=None, tick_interval: int = 45):
        self.db = db
        self.bot_loop = bot_loop
        self.tick_interval = tick_interval
        self._running = False
        self._thread = None
        self.tick_count = 0
        self.latest_news = "📈 Market Open: High-volume trading active across corporate equities."
        self.last_dividend_time = time.time()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Stock Market Engine] Started background price fluctuation ticker with dividends & catalysts.", flush=True)

    def stop(self):
        self._running = False

    def _run_loop(self):
        while self._running:
            try:
                time.sleep(self.tick_interval)
                if self.bot_loop and self.bot_loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(self._tick(), self.bot_loop)
                    future.result(timeout=15)
                else:
                    asyncio.run(self._tick())
            except Exception as e:
                print(f"[Stock Market Engine] Tick error: {e}")

    async def _tick(self):
        self.tick_count += 1
        stocks = await self.db.get_all_stocks()
        if not stocks:
            return

        # Random catalyst event every 20-30 ticks (~15-22 minutes)
        catalyst_stock_symbol = None
        if self.tick_count % random.randint(20, 30) == 0:
            sym, news = random.choice(CATALYST_EVENTS)
            catalyst_stock_symbol = sym
            self.latest_news = news
            print(f"[Stock Market Catalyst] {news}", flush=True)

        for stock in stocks:
            old_price = stock["price"]

            if catalyst_stock_symbol and stock["symbol"] == catalyst_stock_symbol:
                # Moderate catalyst bump (+4% to +8%)
                change_percent = random.uniform(0.04, 0.08)
            elif old_price <= 25:
                # Automatic Support Bounce: Moderate recovery buying (+4% to +7%)
                change_percent = random.uniform(0.04, 0.07)
                self.latest_news = f"🛡️ [SUPPORT BOUNCE] Institutional buy-wall activated for {stock['symbol']}! Rebound in progress."
            else:
                # Balanced market volatility: -2.0% to +2.2%
                change_percent = random.uniform(-0.020, 0.022)

            diff = int(round(old_price * change_percent))
            if diff == 0:
                diff = random.choice([-1, 0, 1])

            # Strong floor of 20 Medals - stocks never crash below 20
            new_price = max(20, old_price + diff)
            if new_price != old_price:
                await self.db.update_stock_price(stock["id"], new_price)

        # Distribute Dividends every 20 ticks (~15 minutes)
        if self.tick_count % 20 == 0:
            await self._distribute_dividends()

        # Cleanup old history (keep last 300 records)
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
        """Distribute 0.4% passive dividend payout (capped at 250 Medals/stock) every 15 minutes."""
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
                # 0.4% dividend based on current share price per share
                div_per_share = max(1, int(round(h["price"] * 0.004)))
                # Capped at max 250 Medals per stock payout to prevent excessive AFK generation
                total_div = min(250, div_per_share * h["shares"])
                if total_div > 0:
                    await self.db.add_medals(h["user_id"], 0, total_div)
                    total_paid += total_div

            self.last_dividend_time = time.time()
            if total_paid > 0:
                print(f"[Stock Market] Distributed {total_paid:,} Medals in passive dividends across {len(holders)} shareholders.", flush=True)
        except Exception as e:
            print(f"[Stock Market] Dividend distribution error: {e}", flush=True)
