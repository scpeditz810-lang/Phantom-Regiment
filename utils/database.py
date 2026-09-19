"""
Async SQLite database wrapper.
Tables: users (xp, level, wins), warnings, application_cooldowns.
"""

import os
import time
import aiosqlite


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    # ── lifecycle ───────────────────────────────────────────────────────────
    async def setup(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER,
                guild_id  INTEGER,
                xp        INTEGER DEFAULT 0,
                level     INTEGER DEFAULT 0,
                wins      INTEGER DEFAULT 0,
                messages  INTEGER DEFAULT 0,
                last_xp   REAL    DEFAULT 0,
                medals    INTEGER DEFAULT 0,
                last_daily REAL   DEFAULT 0,
                active_banner TEXT DEFAULT NULL,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS inventory (
                user_id   INTEGER,
                guild_id  INTEGER,
                item_id   TEXT,
                PRIMARY KEY (user_id, guild_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER,
                guild_id  INTEGER,
                mod_id    INTEGER,
                reason    TEXT,
                timestamp REAL
            );

            CREATE TABLE IF NOT EXISTS app_cooldowns (
                user_id   INTEGER PRIMARY KEY,
                denied_at REAL
            );
        """)

        # Safely migrate existing databases by adding new columns if they don't exist
        try:
            await self._db.execute("ALTER TABLE users ADD COLUMN medals INTEGER DEFAULT 0")
            await self._db.execute("ALTER TABLE users ADD COLUMN last_daily REAL DEFAULT 0")
            await self._db.execute("ALTER TABLE users ADD COLUMN active_banner TEXT DEFAULT NULL")
        except aiosqlite.OperationalError:
            pass  # Columns already exist

        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()

    # ── user helpers ────────────────────────────────────────────────────────
    async def get_user(self, user_id: int, guild_id: int) -> dict | None:
        async with self._db.execute(
            "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def ensure_user(self, user_id: int, guild_id: int) -> dict:
        user = await self.get_user(user_id, guild_id)
        if not user:
            await self._db.execute(
                "INSERT INTO users (user_id, guild_id) VALUES (?, ?)",
                (user_id, guild_id),
            )
            await self._db.commit()
            return await self.get_user(user_id, guild_id)
        return user

    async def add_xp(self, user_id: int, guild_id: int, xp: int):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            """UPDATE users
               SET xp = xp + ?, messages = messages + 1, last_xp = ?
               WHERE user_id = ? AND guild_id = ?""",
            (xp, time.time(), user_id, guild_id),
        )
        await self._db.commit()

    async def set_level(self, user_id: int, guild_id: int, level: int):
        await self._db.execute(
            "UPDATE users SET level = ? WHERE user_id = ? AND guild_id = ?",
            (level, user_id, guild_id),
        )
        await self._db.commit()

    async def set_xp(self, user_id: int, guild_id: int, xp: int):
        await self._db.execute(
            "UPDATE users SET xp = ? WHERE user_id = ? AND guild_id = ?",
            (xp, user_id, guild_id),
        )
        await self._db.commit()

    async def set_wins(self, user_id: int, guild_id: int, wins: int):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET wins = ? WHERE user_id = ? AND guild_id = ?",
            (wins, user_id, guild_id),
        )
        await self._db.commit()

    # ── economy helpers ─────────────────────────────────────────────────────

    async def add_medals(self, user_id: int, guild_id: int, amount: int):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET medals = medals + ? WHERE user_id = ? AND guild_id = ?",
            (amount, user_id, guild_id)
        )
        await self._db.commit()

    async def set_last_daily(self, user_id: int, guild_id: int, timestamp: float):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET last_daily = ? WHERE user_id = ? AND guild_id = ?",
            (timestamp, user_id, guild_id)
        )
        await self._db.commit()

    async def add_inventory(self, user_id: int, guild_id: int, item_id: str):
        await self._db.execute(
            "INSERT OR IGNORE INTO inventory (user_id, guild_id, item_id) VALUES (?, ?, ?)",
            (user_id, guild_id, item_id)
        )
        await self._db.commit()

    async def has_item(self, user_id: int, guild_id: int, item_id: str) -> bool:
        async with self._db.execute(
            "SELECT 1 FROM inventory WHERE user_id = ? AND guild_id = ? AND item_id = ?",
            (user_id, guild_id, item_id)
        ) as cur:
            return await cur.fetchone() is not None

    async def get_inventory(self, user_id: int, guild_id: int) -> list[str]:
        async with self._db.execute(
            "SELECT item_id FROM inventory WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cur:
            rows = await cur.fetchall()
            return [row["item_id"] for row in rows]

    async def set_active_banner(self, user_id: int, guild_id: int, banner: str | None):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET active_banner = ? WHERE user_id = ? AND guild_id = ?",
            (banner, user_id, guild_id)
        )
        await self._db.commit()

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list[dict]:
        async with self._db.execute(
            """SELECT user_id, xp, level, wins, messages
               FROM users WHERE guild_id = ?
               ORDER BY level DESC, xp DESC
               LIMIT ?""",
            (guild_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def get_rank(self, user_id: int, guild_id: int) -> int:
        """Return 1-based leaderboard position."""
        async with self._db.execute(
            """SELECT COUNT(*) + 1 FROM users
               WHERE guild_id = ?
                 AND (level > (SELECT level FROM users WHERE user_id = ? AND guild_id = ?)
                      OR (level = (SELECT level FROM users WHERE user_id = ? AND guild_id = ?)
                          AND xp > (SELECT xp FROM users WHERE user_id = ? AND guild_id = ?)))""",
            (guild_id, user_id, guild_id, user_id, guild_id, user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 1

    # ── warnings ────────────────────────────────────────────────────────────
    async def add_warning(self, user_id: int, guild_id: int, mod_id: int, reason: str):
        await self._db.execute(
            "INSERT INTO warnings (user_id, guild_id, mod_id, reason, timestamp) VALUES (?,?,?,?,?)",
            (user_id, guild_id, mod_id, reason, time.time()),
        )
        await self._db.commit()

    async def get_warnings(self, user_id: int, guild_id: int) -> list[dict]:
        async with self._db.execute(
            "SELECT * FROM warnings WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC",
            (user_id, guild_id),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def clear_warnings(self, user_id: int, guild_id: int):
        await self._db.execute(
            "DELETE FROM warnings WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        )
        await self._db.commit()

    # ── application cooldowns ───────────────────────────────────────────────
    async def set_app_cooldown(self, user_id: int):
        await self._db.execute(
            "INSERT OR REPLACE INTO app_cooldowns (user_id, denied_at) VALUES (?, ?)",
            (user_id, time.time()),
        )
        await self._db.commit()

    async def get_app_cooldown(self, user_id: int) -> float | None:
        """Return the unix timestamp of last denial, or None."""
        async with self._db.execute(
            "SELECT denied_at FROM app_cooldowns WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def clear_app_cooldown(self, user_id: int):
        await self._db.execute(
            "DELETE FROM app_cooldowns WHERE user_id = ?", (user_id,)
        )
        await self._db.commit()
