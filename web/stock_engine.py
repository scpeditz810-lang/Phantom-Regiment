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
    ("PRC", "⚡ [EXPANSION] Phantom Regiment opens 3 new tactical training grounds. Valuation upgraded."),
    ("TSC", "🏦 [BUYBACK] TS Clan treasury initiates strategic stock buyback program!"),
    ("VNG", "🛡️ [UPGRADE] Vanguard Armaments signs alliance defense pact with sovereign clans.")
]

class StockMarketEngine:
    def __init__(self, db, bot_loop=None, tick_interval: int = 25):
        self.db = db
        self.bot_loop = bot_loop
        self.tick_interval = tick_interval
        self._running = False
        self._thread = None
        self.tick_count = 0
        self.latest_news = "📈 Market Open: High-volume trading active across all 5 corporate equities."
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

        # Random catalyst event every 6-9 ticks (~3 minutes)
        catalyst_stock_symbol = None
        if self.tick_count % random.randint(6, 9) == 0:
            sym, news = random.choice(CATALYST_EVENTS)
            catalyst_stock_symbol = sym
            self.latest_news = news
            print(f"[Stock Market Catalyst] {news}", flush=True)

        for stock in stocks:
            old_price = stock["price"]

            if catalyst_stock_symbol and stock["symbol"] == catalyst_stock_symbol:
                # Big positive catalyst bump (+7% to +16%)
                change_percent = random.uniform(0.07, 0.16)
            else:
                # Normal market volatility: -3% to +4% with slight upward growth bias
                change_percent = random.uniform(-0.035, 0.042)

            diff = int(round(old_price * change_percent))
            if diff == 0:
                diff = random.choice([-1, 1, 2])

            new_price = max(10, old_price + diff)
            if new_price != old_price:
                await self.db.update_stock_price(stock["id"], new_price)

        # Distribute Dividends every 10 ticks (~4 minutes)
        if self.tick_count % 10 == 0:
            await self._distribute_dividends()

        # Cleanup old history (keep last 60 ticks per stock)
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
        """Distribute 2.0% passive dividend payout to all active shareholders."""
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
                # 2% dividend based on current share price per share
                div_per_share = max(1, int(round(h["price"] * 0.02)))
                total_div = div_per_share * h["shares"]
                if total_div > 0:
                    await self.db.add_medals(h["user_id"], 0, total_div)
                    total_paid += total_div

            self.last_dividend_time = time.time()
            if total_paid > 0:
                print(f"[Stock Market] Distributed {total_paid:,} Medals in passive dividends across {len(holders)} shareholders.", flush=True)
        except Exception as e:
            print(f"[Stock Market] Dividend distribution error: {e}", flush=True)
