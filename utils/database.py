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
        dir_path = os.path.dirname(self.db_path)
        os.makedirs(dir_path, exist_ok=True)
        
        # Force full write permissions on Render's file system
        try:
            import stat
            os.chmod(dir_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except Exception as e:
            print(f"⚠️ Could not change DB permissions: {e}", flush=True)

        self._db = await aiosqlite.connect(self.db_path, timeout=20.0)
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
                in_game_level INTEGER DEFAULT 0,
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

            CREATE TABLE IF NOT EXISTS invites (
                user_id   INTEGER,
                guild_id  INTEGER,
                invite_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS invite_history (
                joined_user_id INTEGER PRIMARY KEY,
                inviter_user_id INTEGER,
                guild_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                message_id  INTEGER PRIMARY KEY,
                channel_id  INTEGER,
                guild_id    INTEGER,
                prize       TEXT,
                winners     INTEGER DEFAULT 1,
                end_time    REAL,
                ended       INTEGER DEFAULT 0,
                host_id     INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS giveaway_entries (
                message_id  INTEGER,
                user_id     INTEGER,
                PRIMARY KEY (message_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS roblox_links (
                user_id           INTEGER PRIMARY KEY,
                roblox_username   TEXT,
                roblox_id         INTEGER,
                roblox_display    TEXT
            );

            CREATE TABLE IF NOT EXISTS starboard (
                original_msg_id   INTEGER PRIMARY KEY,
                starboard_msg_id  INTEGER
            );

            CREATE TABLE IF NOT EXISTS squad_cooldowns (
                user_id INTEGER,
                squad_idx INTEGER,
                denied_at REAL,
                PRIMARY KEY (user_id, squad_idx)
            );

            CREATE TABLE IF NOT EXISTS banks (
                user_id INTEGER,
                guild_id INTEGER,
                balance INTEGER DEFAULT 0,
                created_at REAL,
                PRIMARY KEY (user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS bank_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                guild_id INTEGER,
                principal INTEGER,
                interest INTEGER,
                total_owed INTEGER,
                due_at REAL,
                created_at REAL,
                repaid INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS player_loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lender_id INTEGER,
                borrower_id INTEGER,
                guild_id INTEGER,
                principal INTEGER,
                interest INTEGER,
                total_owed INTEGER,
                due_at REAL,
                created_at REAL,
                status TEXT DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS role_purchases (
                user_id INTEGER,
                guild_id INTEGER,
                role_key TEXT,
                PRIMARY KEY (user_id, guild_id, role_key)
            );

            CREATE TABLE IF NOT EXISTS streaks (
                user_id INTEGER,
                guild_id INTEGER,
                streak INTEGER DEFAULT 0,
                last_claim REAL DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            );
        """)

        # Safely migrate existing databases by adding new columns if they don't exist
        for query in [
            "ALTER TABLE users ADD COLUMN medals INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_daily REAL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN active_banner TEXT DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN last_work REAL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_weekly REAL DEFAULT 0"
        ]:
            try:
                await self._db.execute(query)
            except aiosqlite.OperationalError:
                pass  # Column already exists

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

    async def set_stats(self, user_id: int, guild_id: int, wins: int, in_game_level: int):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET wins = ?, in_game_level = ? WHERE user_id = ? AND guild_id = ?",
            (wins, in_game_level, user_id, guild_id),
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

    async def set_last_work(self, user_id: int, guild_id: int, timestamp: float):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET last_work = ? WHERE user_id = ? AND guild_id = ?",
            (timestamp, user_id, guild_id)
        )
        await self._db.commit()

    async def set_last_weekly(self, user_id: int, guild_id: int, timestamp: float):
        await self.ensure_user(user_id, guild_id)
        await self._db.execute(
            "UPDATE users SET last_weekly = ? WHERE user_id = ? AND guild_id = ?",
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

    # ── giveaway helpers ────────────────────────────────────────────────────
    async def create_giveaway(
        self, message_id: int, channel_id: int, guild_id: int,
        prize: str, winners: int, end_time: float, host_id: int = 0,
    ):
        await self._db.execute(
            """INSERT INTO giveaways
               (message_id, channel_id, guild_id, prize, winners, end_time, host_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message_id, channel_id, guild_id, prize, winners, end_time, host_id),
        )
        await self._db.commit()

    async def get_giveaway(self, message_id: int) -> dict | None:
        async with self._db.execute(
            "SELECT * FROM giveaways WHERE message_id = ?", (message_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_active_giveaways(self) -> list[dict]:
        """Return giveaways that have not ended and whose end_time has passed."""
        async with self._db.execute(
            "SELECT * FROM giveaways WHERE ended = 0 AND end_time <= ?",
            (time.time(),),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def end_giveaway(self, message_id: int):
        await self._db.execute(
            "UPDATE giveaways SET ended = 1 WHERE message_id = ?",
            (message_id,),
        )
        await self._db.commit()

    async def add_giveaway_entry(self, message_id: int, user_id: int):
        await self._db.execute(
            "INSERT OR IGNORE INTO giveaway_entries (message_id, user_id) VALUES (?, ?)",
            (message_id, user_id),
        )
        await self._db.commit()

    async def has_giveaway_entry(self, message_id: int, user_id: int) -> bool:
        async with self._db.execute(
            "SELECT 1 FROM giveaway_entries WHERE message_id = ? AND user_id = ?",
            (message_id, user_id),
        ) as cur:
            return await cur.fetchone() is not None

    async def count_giveaway_entries(self, message_id: int) -> int:
        async with self._db.execute(
            "SELECT COUNT(*) FROM giveaway_entries WHERE message_id = ?",
            (message_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def get_giveaway_entries(self, message_id: int) -> list[int]:
        """Return a list of user IDs that entered the giveaway."""
        async with self._db.execute(
            "SELECT user_id FROM giveaway_entries WHERE message_id = ?",
            (message_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]

    # ── invite tracking ──────────────────────────────────────────────────────

    async def add_invite(self, inviter_id: int, joined_id: int, guild_id: int):
        """Record who invited whom and increment count."""
        # Record history
        await self._db.execute(
            "INSERT OR REPLACE INTO invite_history (joined_user_id, inviter_user_id, guild_id) VALUES (?, ?, ?)",
            (joined_id, inviter_id, guild_id)
        )
        # Increment count
        await self._db.execute(
            "INSERT INTO invites (user_id, guild_id, invite_count) VALUES (?, ?, 1) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET invite_count = invite_count + 1",
            (inviter_id, guild_id),
        )
        await self._db.commit()

    async def remove_invite(self, joined_id: int, guild_id: int):
        """Remove the invite history and decrement the inviter's count."""
        async with self._db.execute(
            "SELECT inviter_user_id FROM invite_history WHERE joined_user_id = ? AND guild_id = ?",
            (joined_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return
            inviter_id = row[0]

        # Delete history
        await self._db.execute("DELETE FROM invite_history WHERE joined_user_id = ?", (joined_id,))
        
        # Decrement count
        await self._db.execute(
            "UPDATE invites SET invite_count = MAX(0, invite_count - 1) WHERE user_id = ? AND guild_id = ?",
            (inviter_id, guild_id)
        )
        await self._db.commit()

    async def get_invited_users(self, inviter_id: int, guild_id: int) -> list[int]:
        """Get a list of user IDs that were invited by this person."""
        async with self._db.execute(
            "SELECT joined_user_id FROM invite_history WHERE inviter_user_id = ? AND guild_id = ?",
            (inviter_id, guild_id)
        ) as cur:
            rows = await cur.fetchall()
            return [row[0] for row in rows]

    async def get_invites(self, user_id: int, guild_id: int) -> int:
        async with self._db.execute(
            "SELECT invite_count FROM invites WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def get_invite_leaderboard(self, guild_id: int, limit: int = 10) -> list[dict]:
        async with self._db.execute(
            "SELECT user_id, invite_count FROM invites WHERE guild_id = ? "
            "ORDER BY invite_count DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ── roblox links ─────────────────────────────────────────────────────────

    async def link_roblox(self, user_id: int, username: str, roblox_id: int, display_name: str):
        await self._db.execute(
            "INSERT OR REPLACE INTO roblox_links (user_id, roblox_username, roblox_id, roblox_display) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, roblox_id, display_name),
        )
        await self._db.commit()

    async def get_roblox_link(self, user_id: int) -> dict | None:
        async with self._db.execute(
            "SELECT * FROM roblox_links WHERE user_id = ?", (user_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    # ── starboard ────────────────────────────────────────────────────────────

    async def get_starboard_msg(self, original_msg_id: int) -> int | None:
        async with self._db.execute(
            "SELECT starboard_msg_id FROM starboard WHERE original_msg_id = ?",
            (original_msg_id,),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def link_starboard_msg(self, original_msg_id: int, starboard_msg_id: int):
        await self._db.execute(
            "INSERT OR REPLACE INTO starboard (original_msg_id, starboard_msg_id) VALUES (?, ?)",
            (original_msg_id, starboard_msg_id),
        )
        await self._db.commit()

    # ── economy system (bank & loans & roles & streaks) ─────────────────────

    async def create_bank(self, user_id: int, guild_id: int) -> bool:
        """Create a bank account if it doesn't exist. Returns True if created."""
        async with self._db.execute("SELECT 1 FROM banks WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cur:
            if await cur.fetchone():
                return False
        await self._db.execute(
            "INSERT INTO banks (user_id, guild_id, balance, created_at) VALUES (?, ?, 0, ?)",
            (user_id, guild_id, time.time())
        )
        await self._db.commit()
        return True

    async def get_bank(self, user_id: int, guild_id: int) -> dict | None:
        async with self._db.execute("SELECT * FROM banks WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def deposit_bank(self, user_id: int, guild_id: int, amount: int):
        await self._db.execute(
            "UPDATE banks SET balance = balance + ? WHERE user_id = ? AND guild_id = ?",
            (amount, user_id, guild_id)
        )
        await self._db.commit()

    async def withdraw_bank(self, user_id: int, guild_id: int, amount: int) -> bool:
        """Returns True if successful, False if insufficient balance."""
        bank = await self.get_bank(user_id, guild_id)
        if bank and bank["balance"] >= amount:
            await self._db.execute(
                "UPDATE banks SET balance = balance - ? WHERE user_id = ? AND guild_id = ?",
                (amount, user_id, guild_id)
            )
            await self._db.commit()
            return True
        return False

    async def create_bank_loan(self, user_id: int, guild_id: int, principal: int, interest: int, due_at: float):
        await self._db.execute(
            "INSERT INTO bank_loans (user_id, guild_id, principal, interest, total_owed, due_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, guild_id, principal, interest, principal + interest, due_at, time.time())
        )
        await self._db.commit()

    async def get_active_bank_loan(self, user_id: int, guild_id: int) -> dict | None:
        async with self._db.execute(
            "SELECT * FROM bank_loans WHERE user_id = ? AND guild_id = ? AND repaid < total_owed ORDER BY id DESC LIMIT 1",
            (user_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def repay_bank_loan(self, loan_id: int, amount: int):
        await self._db.execute(
            "UPDATE bank_loans SET repaid = repaid + ? WHERE id = ?",
            (amount, loan_id)
        )
        await self._db.commit()

    async def create_player_loan(self, lender_id: int, borrower_id: int, guild_id: int, principal: int, interest: int, due_at: float) -> int:
        await self._db.execute(
            "INSERT INTO player_loans (lender_id, borrower_id, guild_id, principal, interest, total_owed, due_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (lender_id, borrower_id, guild_id, principal, interest, principal + interest, due_at, time.time())
        )
        await self._db.commit()
        async with self._db.execute("SELECT last_insert_rowid()") as cur:
            row = await cur.fetchone()
            return row[0]

    async def accept_player_loan(self, loan_id: int):
        await self._db.execute(
            "UPDATE player_loans SET status = 'active' WHERE id = ?",
            (loan_id,)
        )
        await self._db.commit()

    async def repay_player_loan(self, loan_id: int):
        await self._db.execute(
            "UPDATE player_loans SET status = 'repaid' WHERE id = ?",
            (loan_id,)
        )
        await self._db.commit()

    async def get_all_player_loans(self, user_id: int, guild_id: int) -> list[dict]:
        async with self._db.execute(
            "SELECT * FROM player_loans WHERE (lender_id = ? OR borrower_id = ?) AND guild_id = ? AND status = 'active'",
            (user_id, user_id, guild_id)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def add_role_purchase(self, user_id: int, guild_id: int, role_key: str):
        await self._db.execute(
            "INSERT OR IGNORE INTO role_purchases (user_id, guild_id, role_key) VALUES (?, ?, ?)",
            (user_id, guild_id, role_key)
        )
        await self._db.commit()

    async def has_role_purchase(self, user_id: int, guild_id: int, role_key: str) -> bool:
        async with self._db.execute(
            "SELECT 1 FROM role_purchases WHERE user_id = ? AND guild_id = ? AND role_key = ?",
            (user_id, guild_id, role_key)
        ) as cur:
            return await cur.fetchone() is not None

    async def get_streak(self, user_id: int, guild_id: int) -> dict:
        async with self._db.execute(
            "SELECT streak, last_claim FROM streaks WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"streak": 0, "last_claim": 0}

    async def update_streak(self, user_id: int, guild_id: int, streak: int):
        await self._db.execute(
            "INSERT INTO streaks (user_id, guild_id, streak, last_claim) VALUES (?, ?, ?, ?) ON CONFLICT(user_id, guild_id) DO UPDATE SET streak = ?, last_claim = ?",
            (user_id, guild_id, streak, time.time(), streak, time.time())
        )
        await self._db.commit()

    async def get_top_medals(self, guild_id: int, limit: int = 10) -> list[dict]:
        async with self._db.execute(
            "SELECT user_id, medals FROM users WHERE guild_id = ? AND medals > 0 ORDER BY medals DESC LIMIT ?",
            (guild_id, limit)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

