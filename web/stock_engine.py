import time
import random
import threading
import asyncio

class StockMarketEngine:
    def __init__(self, db, bot_loop=None, tick_interval: int = 25):
        self.db = db
        self.bot_loop = bot_loop
        self.tick_interval = tick_interval
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("[Stock Market Engine] Started background price fluctuation ticker.", flush=True)

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
        stocks = await self.db.get_all_stocks()
        if not stocks:
            return

        for stock in stocks:
            old_price = stock["price"]
            # Volatility: -3% to +3% with a slight positive bias for active trading
            change_percent = random.uniform(-0.035, 0.038)
            diff = int(round(old_price * change_percent))
            if diff == 0:
                diff = random.choice([-1, 1])

            new_price = max(5, old_price + diff)
            if new_price != old_price:
                await self.db.update_stock_price(stock["id"], new_price)

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
