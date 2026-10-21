"""

Async SQLite database wrapper.

Tables: users (xp, level, wins), warnings, application_cooldowns.

"""



import os

import time

import random

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



            CREATE TABLE IF NOT EXISTS rob_cooldowns (

                robber_id INTEGER,

                target_id INTEGER,

                guild_id INTEGER,

                last_attempt REAL DEFAULT 0,

                PRIMARY KEY (robber_id, target_id, guild_id)

            );



            CREATE TABLE IF NOT EXISTS meta (

                key TEXT PRIMARY KEY,

                value TEXT

            );



            CREATE TABLE IF NOT EXISTS bank_insurance (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                guild_id INTEGER,

                daily_amount INTEGER,

                days_remaining INTEGER DEFAULT 7,

                last_payout REAL,

                created_at REAL

            );



            CREATE TABLE IF NOT EXISTS global_economy (

                user_id INTEGER PRIMARY KEY,

                medals INTEGER DEFAULT 0,

                last_daily REAL DEFAULT 0,

                last_work REAL DEFAULT 0,

                last_weekly REAL DEFAULT 0,

                last_crime REAL DEFAULT 0,

                last_scavenge REAL DEFAULT 0,

                last_trivia REAL DEFAULT 0,

                active_banner TEXT DEFAULT NULL

            );



            CREATE TABLE IF NOT EXISTS stocks (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                symbol TEXT UNIQUE,

                name TEXT,

                price INTEGER,

                total_supply INTEGER DEFAULT 150,

                available_shares INTEGER DEFAULT 150,

                description TEXT,

                created_at REAL

            );



            CREATE TABLE IF NOT EXISTS stock_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                stock_id INTEGER,

                price INTEGER,

                timestamp REAL

            );



            CREATE TABLE IF NOT EXISTS user_stocks (

                user_id INTEGER,

                stock_id INTEGER,

                shares INTEGER DEFAULT 0,

                avg_buy_price REAL DEFAULT 0,

                PRIMARY KEY (user_id, stock_id)

            );



            CREATE TABLE IF NOT EXISTS gambling_stats (

                user_id INTEGER PRIMARY KEY,

                total_wagered INTEGER DEFAULT 0,

                total_won INTEGER DEFAULT 0,

                total_lost INTEGER DEFAULT 0,

                net_profit INTEGER DEFAULT 0

            );



            CREATE TABLE IF NOT EXISTS allied_guilds (

                guild_id INTEGER PRIMARY KEY,

                name TEXT,

                member_count INTEGER DEFAULT 0,

                bot_type TEXT,

                last_seen REAL

            );

        """)



        # Safely migrate existing databases by adding new columns if they don't exist

        for query in [

            "ALTER TABLE users ADD COLUMN medals INTEGER DEFAULT 0",

            "ALTER TABLE users ADD COLUMN last_daily REAL DEFAULT 0",

            "ALTER TABLE users ADD COLUMN active_banner TEXT DEFAULT NULL",

            "ALTER TABLE users ADD COLUMN last_work REAL DEFAULT 0",

            "ALTER TABLE users ADD COLUMN last_weekly REAL DEFAULT 0",

            "ALTER TABLE player_loans ADD COLUMN repaid INTEGER DEFAULT 0",

            "ALTER TABLE player_loans ADD COLUMN late_fee_applied INTEGER DEFAULT 0",

            "ALTER TABLE bank_loans ADD COLUMN late_fee_applied INTEGER DEFAULT 0",

            "ALTER TABLE banks ADD COLUMN last_interest REAL DEFAULT 0",

            "ALTER TABLE banks ADD COLUMN password_hash TEXT DEFAULT NULL",

            "ALTER TABLE banks ADD COLUMN password TEXT DEFAULT NULL",

            "ALTER TABLE banks ADD COLUMN tier INTEGER DEFAULT 1",

            "ALTER TABLE users ADD COLUMN last_crime REAL DEFAULT 0",

            "ALTER TABLE users ADD COLUMN last_scavenge REAL DEFAULT 0",

            "ALTER TABLE users ADD COLUMN last_trivia REAL DEFAULT 0",

            "PRAGMA journal_mode=WAL"

        ]:

            try:

                await self._db.execute(query)

            except aiosqlite.OperationalError:

                pass  # Column already exists



        # Migrate existing users economy data into global_economy — always take the higher value

        await self._db.execute("""

            INSERT INTO global_economy (user_id, medals, last_daily, last_work, last_weekly, last_crime, last_scavenge, last_trivia, active_banner)

            SELECT user_id, MAX(medals), MAX(last_daily), MAX(last_work), MAX(last_weekly), MAX(last_crime), MAX(last_scavenge), MAX(last_trivia), active_banner

            FROM users

            GROUP BY user_id

            ON CONFLICT(user_id) DO UPDATE SET

                medals = MAX(global_economy.medals, excluded.medals),

                last_daily = MAX(global_economy.last_daily, excluded.last_daily),

                last_work = MAX(global_economy.last_work, excluded.last_work),

                last_weekly = MAX(global_economy.last_weekly, excluded.last_weekly),

                last_crime = MAX(global_economy.last_crime, excluded.last_crime),

                last_scavenge = MAX(global_economy.last_scavenge, excluded.last_scavenge),

                last_trivia = MAX(global_economy.last_trivia, excluded.last_trivia)

        """)



        # Sync all per-guild users rows to match the global_economy medal count

        # This ensures every server sees the same balance immediately

        await self._db.execute("""

            UPDATE users SET

                medals = COALESCE((SELECT medals FROM global_economy WHERE global_economy.user_id = users.user_id), users.medals),

                last_daily = COALESCE((SELECT last_daily FROM global_economy WHERE global_economy.user_id = users.user_id), users.last_daily),

                last_work = COALESCE((SELECT last_work FROM global_economy WHERE global_economy.user_id = users.user_id), users.last_work),

                last_weekly = COALESCE((SELECT last_weekly FROM global_economy WHERE global_economy.user_id = users.user_id), users.last_weekly),

                last_crime = COALESCE((SELECT last_crime FROM global_economy WHERE global_economy.user_id = users.user_id), users.last_crime),

                last_scavenge = COALESCE((SELECT last_scavenge FROM global_economy WHERE global_economy.user_id = users.user_id), users.last_scavenge),

                last_trivia = COALESCE((SELECT last_trivia FROM global_economy WHERE global_economy.user_id = users.user_id), users.last_trivia)

        """)



        # Pre-seed Phantom Regiment guild into allied_guilds if not present

        await self._db.execute("""

            INSERT OR IGNORE INTO allied_guilds (guild_id, name, member_count, bot_type, last_seen)

            VALUES (1550544659217125467, 'Phantom Regiment', 0, 'Phantom Regiment', ?)

        """, (time.time(),))



        await self._db.commit()

        await self.seed_default_stocks()



    async def close(self):

        if self._db:

            await self._db.close()



    # ── user & global economy helpers ───────────────────────────────────────

    async def get_global_economy(self, user_id: int) -> dict:

        async with self._db.execute("SELECT * FROM global_economy WHERE user_id = ?", (user_id,)) as cur:

            row = await cur.fetchone()

            if row:

                return dict(row)

        # Row doesn't exist yet — seed it from the highest values across all guilds in users table

        async with self._db.execute(

            "SELECT MAX(medals) as medals, MAX(last_daily) as last_daily, MAX(last_work) as last_work, "

            "MAX(last_weekly) as last_weekly, MAX(last_crime) as last_crime, MAX(last_scavenge) as last_scavenge, "

            "MAX(last_trivia) as last_trivia, active_banner FROM users WHERE user_id = ?",

            (user_id,)

        ) as cur:

            seed = await cur.fetchone()

        seed_medals = (seed[0] or 0) if seed else 0

        seed_daily = (seed[1] or 0) if seed else 0

        seed_work = (seed[2] or 0) if seed else 0

        seed_weekly = (seed[3] or 0) if seed else 0

        seed_crime = (seed[4] or 0) if seed else 0

        seed_scavenge = (seed[5] or 0) if seed else 0

        seed_trivia = (seed[6] or 0) if seed else 0

        seed_banner = seed[7] if seed else None

        await self._db.execute(

            "INSERT OR IGNORE INTO global_economy (user_id, medals, last_daily, last_work, last_weekly, last_crime, last_scavenge, last_trivia, active_banner) "

            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",

            (user_id, seed_medals, seed_daily, seed_work, seed_weekly, seed_crime, seed_scavenge, seed_trivia, seed_banner)

        )

        await self._db.commit()

        async with self._db.execute("SELECT * FROM global_economy WHERE user_id = ?", (user_id,)) as cur:

            row = await cur.fetchone()

            return dict(row) if row else {"user_id": user_id, "medals": 0}



    async def get_user(self, user_id: int, guild_id: int) -> dict | None:

        async with self._db.execute(

            "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",

            (user_id, guild_id),

        ) as cur:

            row = await cur.fetchone()

            if not row:

                return None

            d = dict(row)

            g_econ = await self.get_global_economy(user_id)

            for k in ["medals", "last_daily", "last_work", "last_weekly", "last_crime", "last_scavenge", "last_trivia", "active_banner"]:

                if k in g_econ and g_econ[k] is not None:

                    d[k] = g_econ[k]

            return d



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

        

        if amount > 0:

            # 1. Divert to overdue Bank Loans (checked across all servers for user_id)

            async with self._db.execute("SELECT id, total_owed, repaid FROM bank_loans WHERE user_id = ? AND repaid < total_owed AND due_at < ?", (user_id, time.time())) as cur:

                bank_loan = await cur.fetchone()

                

            if bank_loan and amount > 0:

                loan_id, owed, repaid = bank_loan

                rem = owed - repaid

                take = min(amount, rem)

                amount -= take

                await self._db.execute("UPDATE bank_loans SET repaid = repaid + ? WHERE id = ?", (take, loan_id))

                

            # 2. Divert to overdue Player Loans (checked across all servers for borrower_id)

            async with self._db.execute("SELECT id, total_owed, repaid, lender_id FROM player_loans WHERE borrower_id = ? AND status = 'active' AND due_at < ?", (user_id, time.time())) as cur:

                player_loan = await cur.fetchone()

                

            if player_loan and amount > 0:

                loan_id, owed, repaid, lender_id = player_loan

                rem = owed - repaid

                take = min(amount, rem)

                amount -= take

                await self._db.execute("UPDATE player_loans SET repaid = repaid + ? WHERE id = ?", (take, loan_id))

                await self.add_medals(lender_id, guild_id, take)

                if repaid + take >= owed:

                    await self._db.execute("UPDATE player_loans SET status = 'repaid' WHERE id = ?", (loan_id,))



        if amount != 0:

            await self._db.execute(

                "UPDATE global_economy SET medals = medals + ? WHERE user_id = ?",

                (amount, user_id)

            )

            await self._db.execute(

                "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?",

                (user_id, user_id)

            )

        await self._db.commit()



    async def set_last_daily(self, user_id: int, guild_id: int, timestamp: float):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET last_daily = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.commit()



    async def set_last_work(self, user_id: int, guild_id: int, timestamp: float):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET last_work = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.execute("UPDATE users SET last_work = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.commit()



    async def set_last_weekly(self, user_id: int, guild_id: int, timestamp: float):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET last_weekly = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.execute("UPDATE users SET last_weekly = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.commit()



    async def set_last_crime(self, user_id: int, guild_id: int, timestamp: float):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET last_crime = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.execute("UPDATE users SET last_crime = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.commit()



    async def set_last_scavenge(self, user_id: int, guild_id: int, timestamp: float):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET last_scavenge = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.execute("UPDATE users SET last_scavenge = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.commit()



    async def set_last_trivia(self, user_id: int, guild_id: int, timestamp: float):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET last_trivia = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.execute("UPDATE users SET last_trivia = ? WHERE user_id = ?", (timestamp, user_id))

        await self._db.commit()



    async def add_inventory(self, user_id: int, guild_id: int, item_id: str):

        await self._db.execute(

            "INSERT OR IGNORE INTO inventory (user_id, guild_id, item_id) VALUES (?, ?, ?)",

            (user_id, guild_id, item_id)

        )

        await self._db.commit()



    async def has_item(self, user_id: int, guild_id: int, item_id: str) -> bool:

        async with self._db.execute(

            "SELECT 1 FROM inventory WHERE user_id = ? AND item_id = ?",

            (user_id, item_id)

        ) as cur:

            return await cur.fetchone() is not None



    async def get_inventory(self, user_id: int, guild_id: int) -> list[str]:

        async with self._db.execute(

            "SELECT DISTINCT item_id FROM inventory WHERE user_id = ?",

            (user_id,)

        ) as cur:

            rows = await cur.fetchall()

            return [row["item_id"] for row in rows]



    async def set_active_banner(self, user_id: int, guild_id: int, banner: str | None):

        await self.ensure_user(user_id, guild_id)

        await self._db.execute("UPDATE global_economy SET active_banner = ? WHERE user_id = ?", (banner, user_id))

        await self._db.execute("UPDATE users SET active_banner = ? WHERE user_id = ?", (banner, user_id))

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



    async def create_bank(self, user_id: int, guild_id: int, password_hash: str = None, password: str = None) -> bool:

        """Create a bank account if it doesn't exist across the alliance. Returns True if created."""

        existing = await self.get_bank(user_id, guild_id)

        if existing:

            return False

        await self._db.execute(

            "INSERT INTO banks (user_id, guild_id, balance, created_at, password_hash, tier, password) VALUES (?, ?, 0, ?, ?, 1, ?)",

            (user_id, guild_id, time.time(), password_hash, password)

        )

        await self._db.commit()

        return True



    async def upgrade_bank_tier(self, user_id: int, guild_id: int, new_tier: int):

        await self._db.execute(

            "UPDATE banks SET tier = ? WHERE user_id = ?",

            (new_tier, user_id)

        )

        await self._db.commit()



    async def hard_reset_all_banks(self):

        await self._db.execute("UPDATE users SET medals = 0")

        await self._db.execute("UPDATE global_economy SET medals = 0")

        await self._db.execute("DELETE FROM banks")

        await self._db.execute("DELETE FROM bank_loans")

        await self._db.execute("DELETE FROM player_loans")

        await self._db.execute("DELETE FROM streaks")

        await self._db.execute("DELETE FROM bank_insurance")

        await self._db.commit()



    async def get_bank(self, user_id: int, guild_id: int = None) -> dict | None:

        async with self._db.execute("SELECT * FROM banks WHERE user_id = ? ORDER BY balance DESC, tier DESC LIMIT 1", (user_id,)) as cur:

            row = await cur.fetchone()

            return dict(row) if row else None



    async def deposit_bank(self, user_id: int, guild_id: int, amount: int):

        await self._db.execute(

            "UPDATE banks SET balance = balance + ? WHERE user_id = ?",

            (amount, user_id)

        )

        await self._db.commit()



    async def withdraw_bank(self, user_id: int, guild_id: int, amount: int) -> bool:

        """Returns True if successful, False if insufficient balance."""

        bank = await self.get_bank(user_id, guild_id)

        if bank and bank["balance"] >= amount:

            await self._db.execute(

                "UPDATE banks SET balance = balance - ? WHERE user_id = ?",

                (amount, user_id)

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

            "SELECT * FROM bank_loans WHERE user_id = ? AND repaid < total_owed ORDER BY id DESC LIMIT 1",

            (user_id,)

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

            "UPDATE player_loans SET status = 'active', due_at = (due_at - created_at) + ? WHERE id = ?",

            (time.time(), loan_id)

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

            "SELECT * FROM player_loans WHERE (lender_id = ? OR borrower_id = ?) AND status = 'active'",

            (user_id, user_id)

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

            "SELECT 1 FROM role_purchases WHERE user_id = ? AND role_key = ?",

            (user_id, role_key)

        ) as cur:

            return await cur.fetchone() is not None



    async def get_streak(self, user_id: int, guild_id: int = None) -> dict:

        async with self._db.execute(

            "SELECT streak, last_claim FROM streaks WHERE user_id = ? ORDER BY streak DESC LIMIT 1",

            (user_id,)

        ) as cur:

            row = await cur.fetchone()

            return dict(row) if row else {"streak": 0, "last_claim": 0}



    async def update_streak(self, user_id: int, guild_id: int, streak: int):

        now = time.time()

        existing = await self.get_streak(user_id, guild_id)

        if existing.get("last_claim", 0) > 0:

            await self._db.execute(

                "UPDATE streaks SET streak = ?, last_claim = ? WHERE user_id = ?",

                (streak, now, user_id)

            )

        else:

            await self._db.execute(

                "INSERT INTO streaks (user_id, guild_id, streak, last_claim) VALUES (?, ?, ?, ?)",

                (user_id, guild_id, streak, now)

            )

        await self._db.commit()



    async def get_top_medals(self, guild_id: int, limit: int = 10) -> list[dict]:

        async with self._db.execute(

            """SELECT u.user_id, COALESCE(g.medals, u.medals) as medals

               FROM users u

               LEFT JOIN global_economy g ON u.user_id = g.user_id

               WHERE u.guild_id = ? AND COALESCE(g.medals, u.medals) > 0

               ORDER BY medals DESC LIMIT ?""",

            (guild_id, limit)

        ) as cur:

            return [dict(r) for r in await cur.fetchall()]



    async def set_bank_password(self, user_id: int, guild_id: int, password_hash: str, password: str = None):

        await self._db.execute(

            "UPDATE banks SET password_hash = ?, password = ? WHERE user_id = ?",

            (password_hash, password, user_id)

        )

        await self._db.commit()



    async def create_bank_insurance(self, user_id: int, guild_id: int, daily_amount: int, days: int = 7):

        now = time.time()

        await self._db.execute(

            "INSERT INTO bank_insurance (user_id, guild_id, daily_amount, days_remaining, last_payout, created_at) VALUES (?, ?, ?, ?, ?, ?)",

            (user_id, guild_id, daily_amount, days, now, now)

        )

        await self._db.commit()



    async def get_rob_cooldown(self, robber_id: int, target_id: int, guild_id: int) -> float:

        async with self._db.execute(

            "SELECT last_attempt FROM rob_cooldowns WHERE robber_id = ? AND target_id = ? AND guild_id = ?",

            (robber_id, target_id, guild_id)

        ) as cur:

            row = await cur.fetchone()

            return row[0] if row else 0



    async def set_rob_cooldown(self, robber_id: int, target_id: int, guild_id: int):

        await self._db.execute(

            "INSERT OR REPLACE INTO rob_cooldowns (robber_id, target_id, guild_id, last_attempt) VALUES (?, ?, ?, ?)",

            (robber_id, target_id, guild_id, time.time())

        )

        await self._db.commit()



    async def get_global_leaderboard(self, limit: int = 10) -> list[dict]:

        """Get top users across ALL guilds by medals."""

        async with self._db.execute("""
            SELECT user_id, MAX(medals) as total_medals FROM (
                SELECT user_id, medals FROM global_economy
                UNION ALL
                SELECT user_id, medals FROM users
            ) WHERE user_id != 99999999 AND medals > 0
            GROUP BY user_id
            ORDER BY total_medals DESC
            LIMIT ?
        """, (limit,)) as cur:

            return [dict(row) for row in await cur.fetchall()]



    # ── allied guilds helpers ────────────────────────────────────────────────

    async def register_guild(self, guild_id: int, name: str, member_count: int, bot_type: str = "Phantom Regiment"):

        await self._db.execute(

            """INSERT INTO allied_guilds (guild_id, name, member_count, bot_type, last_seen)

               VALUES (?, ?, ?, ?, ?)

               ON CONFLICT(guild_id) DO UPDATE SET

                   name = excluded.name,

                   member_count = excluded.member_count,

                   bot_type = excluded.bot_type,

                   last_seen = excluded.last_seen""",

            (guild_id, name, member_count, bot_type, time.time())

        )

        await self._db.commit()



    async def get_allied_guilds(self) -> list[dict]:

        async with self._db.execute("SELECT * FROM allied_guilds ORDER BY member_count DESC") as cur:

            return [dict(row) for row in await cur.fetchall()]



    # ── gambling stats helpers ────────────────────────────────────────────────

    async def record_gambling(self, user_id: int, wagered: int, won: int, lost: int):

        profit = won - lost

        await self._db.execute("""

            INSERT INTO gambling_stats (user_id, total_wagered, total_won, total_lost, net_profit)

            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(user_id) DO UPDATE SET

                total_wagered = total_wagered + excluded.total_wagered,

                total_won = total_won + excluded.total_won,

                total_lost = total_lost + excluded.total_lost,

                net_profit = net_profit + excluded.net_profit

        """, (user_id, wagered, won, lost, profit))

        await self._db.commit()



    async def get_best_gamblers(self, limit: int = 10) -> list[dict]:

        async with self._db.execute(

            "SELECT user_id, total_wagered, total_won, total_lost, net_profit FROM gambling_stats ORDER BY net_profit DESC LIMIT ?",

            (limit,)

        ) as cur:

            return [dict(row) for row in await cur.fetchall()]



    # ── stock market helpers ──────────────────────────────────────────────────

    async def seed_default_stocks(self):

        default_stocks = [

            ("PRC", "Phantom Regiment Corp", 120, 150, "Tactical PMC, defense logistics & field security operations."),

            ("TSC", "TS Clan Holdings", 250, 150, "Parent syndicate overseeing clan alliances and industrial contracts."),

            ("VNG", "Vanguard Armaments", 85, 150, "Manufacturer of combat armor, weapons, and heavy ordinance."),

            ("AERO", "Apex Aerospace", 160, 150, "Aerial reconnaissance, stealth drones, and tactical air transport."),

            ("CRYP", "Cypher Intelligence", 95, 150, "Encrypted communications, counter-recon, and electronic warfare.")

        ]

        now = time.time()

        for symbol, name, price, supply, desc in default_stocks:

            async with self._db.execute("SELECT id FROM stocks WHERE symbol = ?", (symbol,)) as cur:

                if not await cur.fetchone():

                    await self._db.execute(

                        "INSERT INTO stocks (symbol, name, price, total_supply, available_shares, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",

                        (symbol, name, price, supply, supply, desc, now)

                    )

                    async with self._db.execute("SELECT last_insert_rowid()") as id_cur:

                        sid = (await id_cur.fetchone())[0]

                        for i in range(10, 0, -1):

                            variation = random.randint(-4, 4)

                            hist_price = max(10, price + variation)

                            await self._db.execute(

                                "INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)",

                                (sid, hist_price, now - (i * 60))

                            )

        await self._db.commit()



    async def get_all_stocks(self) -> list[dict]:

        async with self._db.execute("SELECT * FROM stocks ORDER BY id ASC") as cur:

            return [dict(row) for row in await cur.fetchall()]



    async def get_stock(self, stock_id_or_symbol) -> dict | None:

        if isinstance(stock_id_or_symbol, int) or (isinstance(stock_id_or_symbol, str) and str(stock_id_or_symbol).isdigit()):

            query = "SELECT * FROM stocks WHERE id = ?"

            param = int(stock_id_or_symbol)

        else:

            query = "SELECT * FROM stocks WHERE UPPER(symbol) = UPPER(?)"

            param = str(stock_id_or_symbol)

        async with self._db.execute(query, (param,)) as cur:

            row = await cur.fetchone()

            return dict(row) if row else None



    async def create_stock(self, symbol: str, name: str, price: int, description: str = "") -> bool:

        symbol = symbol.strip().upper()

        async with self._db.execute("SELECT 1 FROM stocks WHERE symbol = ?", (symbol,)) as cur:

            if await cur.fetchone():

                return False

        now = time.time()

        await self._db.execute(

            "INSERT INTO stocks (symbol, name, price, total_supply, available_shares, description, created_at) VALUES (?, ?, ?, 150, 150, ?, ?)",

            (symbol, name, price, description, now)

        )

        async with self._db.execute("SELECT last_insert_rowid()") as cur:

            sid = (await cur.fetchone())[0]

            await self._db.execute("INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)", (sid, price, now))

        await self._db.commit()

        return True



    async def update_stock_price(self, stock_id: int, new_price: int):

        new_price = max(1, new_price)

        await self._db.execute("UPDATE stocks SET price = ? WHERE id = ?", (new_price, stock_id))

        await self._db.execute("INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)", (stock_id, new_price, time.time()))

        await self._db.commit()



    async def delete_stock(self, stock_id: int):

        stock = await self.get_stock(stock_id)

        if stock:

            current_price = stock["price"]

            async with self._db.execute("SELECT user_id, shares FROM user_stocks WHERE stock_id = ? AND shares > 0", (stock_id,)) as cur:

                rows = await cur.fetchall()

                for uid, shares in rows:

                    refund = shares * current_price

                    await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (refund, uid))

                    await self._db.execute("UPDATE users SET medals = medals + ? WHERE user_id = ?", (refund, uid))

            await self._db.execute("DELETE FROM user_stocks WHERE stock_id = ?", (stock_id,))

            await self._db.execute("DELETE FROM stock_history WHERE stock_id = ?", (stock_id,))

            await self._db.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))

            await self._db.commit()



    async def get_stock_history(self, stock_id: int, limit: int = 30) -> list[dict]:

        async with self._db.execute(

            "SELECT price, timestamp FROM stock_history WHERE stock_id = ? ORDER BY timestamp DESC LIMIT ?",

            (stock_id, limit)

        ) as cur:

            rows = await cur.fetchall()

            return [dict(r) for r in reversed(rows)]



    async def get_user_stocks(self, user_id: int) -> list[dict]:

        async with self._db.execute("""

            SELECT us.stock_id, us.shares, us.avg_buy_price, s.symbol, s.name, s.price as current_price

            FROM user_stocks us

            JOIN stocks s ON us.stock_id = s.id

            WHERE us.user_id = ? AND us.shares > 0

        """, (user_id,)) as cur:

            return [dict(row) for row in await cur.fetchall()]



    async def buy_stock(self, user_id: int, stock_id: int, shares: int) -> tuple[bool, str]:

        if shares <= 0:

            return False, "Invalid number of shares."

        stock = await self.get_stock(stock_id)

        if not stock:

            return False, "Stock not found."

        if stock["available_shares"] < shares:

            return False, f"Only {stock['available_shares']} shares available on the market (Max 150 total)."



        async with self._db.execute("SELECT shares, avg_buy_price FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id)) as cur:

            row = await cur.fetchone()

            current_shares = row[0] if row else 0

            current_avg = row[1] if row else 0.0



        if current_shares + shares > 10:

            return False, f"Holding limit reached. You can only hold a maximum of 10 shares per stock (Currently hold: {current_shares})."



        total_cost = shares * stock["price"]

        user_econ = await self.get_global_economy(user_id)

        if user_econ.get("medals", 0) < total_cost:

            return False, f"Insufficient Medals. You need {total_cost:,} Medals, but only have {user_econ.get('medals', 0):,}."



        await self._db.execute("UPDATE global_economy SET medals = medals - ? WHERE user_id = ?", (total_cost, user_id))

        await self._db.execute("UPDATE users SET medals = medals - ? WHERE user_id = ?", (total_cost, user_id))

        await self._db.execute("UPDATE stocks SET available_shares = available_shares - ? WHERE id = ?", (shares, stock_id))



        new_total_shares = current_shares + shares

        new_avg = ((current_shares * current_avg) + total_cost) / new_total_shares

        await self._db.execute("""

            INSERT INTO user_stocks (user_id, stock_id, shares, avg_buy_price)

            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id, stock_id) DO UPDATE SET

                shares = ?,

                avg_buy_price = ?

        """, (user_id, stock_id, new_total_shares, new_avg, new_total_shares, new_avg))



        price_bump = max(1, int(round(stock["price"] * (0.02 * shares))))

        new_price = stock["price"] + price_bump

        await self.update_stock_price(stock_id, new_price)

        await self._db.commit()

        return True, f"Successfully purchased {shares} shares of {stock['symbol']} for {total_cost:,} Medals. Price rose to {new_price:,} Medals!"



    async def sell_stock(self, user_id: int, stock_id: int, shares: int) -> tuple[bool, str]:

        if shares <= 0:

            return False, "Invalid number of shares."

        stock = await self.get_stock(stock_id)

        if not stock:

            return False, "Stock not found."



        async with self._db.execute("SELECT shares, avg_buy_price FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id)) as cur:

            row = await cur.fetchone()

            current_shares = row[0] if row else 0



        if current_shares < shares:

            return False, f"You only own {current_shares} shares of {stock['symbol']}."



        total_return = shares * stock["price"]

        await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (total_return, user_id))

        await self._db.execute("UPDATE users SET medals = medals + ? WHERE user_id = ?", (total_return, user_id))

        await self._db.execute("UPDATE stocks SET available_shares = min(total_supply, available_shares + ?) WHERE id = ?", (shares, stock_id))



        new_shares = current_shares - shares

        if new_shares == 0:

            await self._db.execute("DELETE FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id))

        else:

            await self._db.execute("UPDATE user_stocks SET shares = ? WHERE user_id = ? AND stock_id = ?", (new_shares, user_id, stock_id))



        price_drop = max(1, int(round(stock["price"] * (0.02 * shares))))

        new_price = max(5, stock["price"] - price_drop)

        await self.update_stock_price(stock_id, new_price)

        await self._db.commit()

        return True, f"Successfully sold {shares} shares of {stock['symbol']} for {total_return:,} Medals. Price dropped to {new_price:,} Medals."



    async def get_all_bank_passwords(self) -> list[dict]:

        async with self._db.execute("""

            SELECT 

                u.user_id,

                COALESCE(b.guild_id, u.guild_id) as guild_id,

                COALESCE(b.balance, 0) as balance,

                COALESCE(b.tier, 1) as tier,

                b.password,

                COALESCE(b.created_at, 0) as created_at

            FROM (SELECT DISTINCT user_id, guild_id FROM users) u

            LEFT JOIN banks b ON u.user_id = b.user_id

            UNION

            SELECT 

                b.user_id,

                b.guild_id,

                b.balance,

                b.tier,

                b.password,

                COALESCE(b.created_at, 0) as created_at

            FROM banks b

            WHERE b.user_id NOT IN (SELECT DISTINCT user_id FROM users)

            ORDER BY balance DESC, user_id ASC

        """) as cur:

            return [dict(row) for row in await cur.fetchall()]



    async def web_deposit_bank(self, user_id: int, amount: int) -> tuple[bool, str]:

        if amount <= 0:

            return False, "Deposit amount must be positive."

        user = await self.get_global_economy(user_id)

        if user.get("medals", 0) < amount:

            return False, "Not enough medals in your wallet."



        bank = await self.get_bank(user_id)

        if not bank:

            await self.create_bank(user_id, 1550544659217125467, password="PR-" + str(user_id)[-4:])

            bank = await self.get_bank(user_id)



        from utils.constants import BANK_TIERS

        tier = bank.get("tier", 1)

        cap = BANK_TIERS.get(tier, {}).get("cap", 1000)

        current_bal = bank.get("balance", 0)

        if current_bal + amount > cap:

            return False, f"Deposit exceeds vault cap ({cap:,} Medals at Tier {tier}). Upgrade your vault to store more!"



        await self.add_medals(user_id, 0, -amount)

        await self.deposit_bank(user_id, 0, amount)

        return True, f"Deposited {amount:,} Medals into your vault."



    async def web_withdraw_bank(self, user_id: int, amount: int) -> tuple[bool, str]:

        if amount <= 0:

            return False, "Withdraw amount must be positive."

        bank = await self.get_bank(user_id)

        if not bank:

            return False, "You do not have a bank vault."

        if bank.get("balance", 0) < amount:

            return False, "Not enough medals in your vault."



        await self.withdraw_bank(user_id, 0, amount)

        await self.add_medals(user_id, 0, amount)

        return True, f"Withdrew {amount:,} Medals from your vault."

