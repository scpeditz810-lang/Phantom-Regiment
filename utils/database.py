"""

Async SQLite database wrapper.

Tables: users (xp, level, wins), warnings, application_cooldowns.

"""



import os

import time

import random

import json
import aiosqlite





class Database:

    def __init__(self, db_path: str):

        self.db_path = db_path

        self._db: aiosqlite.Connection | None = None



    # ── lifecycle ───────────────────────────────────────────────────────────

    async def setup(self):

        dir_path = os.path.dirname(self.db_path)

        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        

        # Force full write permissions on Render's file system

        try:

            import stat

            if dir_path and os.path.exists(dir_path):
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
                last_buy_time REAL DEFAULT 0,

                PRIMARY KEY (user_id, stock_id)

            );



            CREATE TABLE IF NOT EXISTS gambling_stats (

                user_id INTEGER PRIMARY KEY,

                total_wagered INTEGER DEFAULT 0,

                total_won INTEGER DEFAULT 0,

                total_lost INTEGER DEFAULT 0,

                net_profit INTEGER DEFAULT 0

            );



                        CREATE TABLE IF NOT EXISTS oauth_members (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                access_token TEXT,
                refresh_token TEXT,
                expires_at REAL,
                updated_at REAL
            );

            CREATE TABLE IF NOT EXISTS allied_guilds (

                guild_id INTEGER PRIMARY KEY,

                name TEXT,

                member_count INTEGER DEFAULT 0,

                bot_type TEXT,

                last_seen REAL

            );

            CREATE TABLE IF NOT EXISTS estate_plots (
                id INTEGER PRIMARY KEY,
                x INTEGER NOT NULL,
                y INTEGER NOT NULL,
                name TEXT NOT NULL,
                district TEXT NOT NULL,
                terrain TEXT DEFAULT 'plains',
                base_price INTEGER NOT NULL,
                current_value INTEGER NOT NULL,
                owner_id INTEGER DEFAULT NULL,
                building_type TEXT DEFAULT 'empty',
                building_level INTEGER DEFAULT 0,
                last_yield_claim REAL DEFAULT 0,
                last_value_update REAL DEFAULT 0,
                for_sale_price INTEGER DEFAULT NULL,
                created_at REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS estate_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plot_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                offer_amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT 0,
                FOREIGN KEY(plot_id) REFERENCES estate_plots(id)
            );

            CREATE TABLE IF NOT EXISTS estate_alliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ally_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL NOT NULL,
                UNIQUE(user_id, ally_id)
            );

            CREATE TABLE IF NOT EXISTS estate_raids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_id INTEGER NOT NULL,
                defender_id INTEGER NOT NULL,
                plot_id INTEGER NOT NULL,
                attacker_power INTEGER NOT NULL,
                defender_power INTEGER NOT NULL,
                allied_bonus INTEGER DEFAULT 0,
                success INTEGER NOT NULL,
                loot INTEGER DEFAULT 0,
                timestamp REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                winner_id INTEGER DEFAULT NULL,
                term_end REAL DEFAULT 0,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS election_candidates (
                election_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                slogan TEXT DEFAULT '',
                votes INTEGER DEFAULT 0,
                registered_at REAL NOT NULL,
                PRIMARY KEY (election_id, candidate_id)
            );

            CREATE TABLE IF NOT EXISTS election_votes (
                election_id INTEGER NOT NULL,
                voter_id INTEGER NOT NULL,
                candidate_id INTEGER NOT NULL,
                voted_at REAL NOT NULL,
                PRIMARY KEY (election_id, voter_id)
            );

            CREATE TABLE IF NOT EXISTS commander_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                election_id INTEGER NOT NULL,
                commander_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_id INTEGER DEFAULT NULL,
                details TEXT DEFAULT '',
                created_at REAL NOT NULL
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
            "ALTER TABLE user_stocks ADD COLUMN last_buy_time REAL DEFAULT 0",
            "ALTER TABLE estate_plots ADD COLUMN protected_until REAL DEFAULT 0",
            "ALTER TABLE estate_plots ADD COLUMN last_attack_time REAL DEFAULT 0",

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

        try:
            await self._db.execute("UPDATE stocks SET total_supply = 2500, available_shares = max(available_shares, 2000) WHERE total_supply < 2500")
        except Exception:
            pass
        await self.seed_default_stocks()
        await self.seed_default_estate_plots()
        try:
            await self._db.execute("""
                UPDATE estate_alliances 
                SET status = 'active' 
                WHERE (user_id = 1162404296097275904 AND ally_id = 429350468796416013) 
                   OR (user_id = 429350468796416013 AND ally_id = 1162404296097275904)
            """)
            await self._db.commit()
        except Exception:
            pass



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
                SELECT user_id, medals FROM global_economy WHERE medals > 0
                UNION ALL
                SELECT user_id, medals FROM users WHERE medals > 0
            ) WHERE user_id != 99999999
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

    async def record_gambling(self, user_id: int, wagered: int, won: int, lost: int):
        """Record gambling stats for a user."""
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
            "SELECT user_id, total_wagered, total_won, total_lost, net_profit FROM gambling_stats WHERE total_wagered > 0 ORDER BY net_profit DESC, total_won DESC LIMIT ?",
            (limit,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]



    # ── stock market helpers ──────────────────────────────────────────────────

    async def seed_default_stocks(self):

        default_stocks = [

            ("PRC", "Phantom Regiment Corp", 120, 2500, "Tactical PMC, defense logistics & field security operations."),

            ("TSC", "TS Clan Holdings", 250, 2500, "Parent syndicate overseeing clan alliances and industrial contracts."),

            ("VNG", "Vanguard Armaments", 85, 2500, "Manufacturer of combat armor, weapons, and heavy ordinance."),

            ("AERO", "Apex Aerospace", 160, 2500, "Aerial reconnaissance, stealth drones, and tactical air transport."),

            ("CRYP", "Cypher Intelligence", 95, 2500, "Encrypted communications, counter-recon, and electronic warfare.")

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



    async def create_stock(self, symbol: str, name: str, price: int, description: str = "", supply: int = 2500) -> bool:

        symbol = symbol.strip().upper()

        async with self._db.execute("SELECT 1 FROM stocks WHERE symbol = ?", (symbol,)) as cur:

            if await cur.fetchone():

                return False

        now = time.time()
        supply = max(50, int(supply))

        await self._db.execute(

            "INSERT INTO stocks (symbol, name, price, total_supply, available_shares, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",

            (symbol, name, price, supply, supply, description, now)

        )

        async with self._db.execute("SELECT last_insert_rowid()") as cur:

            sid = (await cur.fetchone())[0]

            await self._db.execute("INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)", (sid, price, now))

        await self._db.commit()

        return True

    async def adjust_stock_supply(self, stock_id_or_symbol, delta: int) -> tuple[bool, str, dict | None]:
        """Mayor / Executive adjustment of stock market share supply."""
        stock = await self.get_stock(stock_id_or_symbol)
        if not stock:
            return False, "Stock not found.", None

        current_supply = stock.get("total_supply", 2500)
        current_avail = stock.get("available_shares", 2500)

        new_avail = current_avail + delta
        new_supply = current_supply + delta

        if new_avail < 0:
            return False, f"Cannot reduce supply by {abs(delta):,}: only {current_avail:,} floating shares are currently available on the market.", None
        if new_supply < 10:
            return False, "Total stock supply cannot fall below 10 shares.", None

        await self._db.execute(
            "UPDATE stocks SET total_supply = ?, available_shares = ? WHERE id = ?",
            (new_supply, new_avail, stock["id"])
        )
        await self._db.commit()
        updated = await self.get_stock(stock["id"])
        return True, f"Successfully adjusted {stock['symbol']} float supply by {delta:+,} shares. (New float: {new_avail:,} / Total Supply: {new_supply:,}).", updated

    async def get_stock_tax_rate(self) -> float:
        """Fetch active stock market transaction tax rate set by the Mayor (default: 0.15)."""
        raw = await self.get_meta("stock_tax_rate")
        if raw is not None:
            try:
                rate = float(raw)
                return max(0.0, min(0.50, rate))
            except (ValueError, TypeError):
                pass
        return 0.15

    async def set_stock_tax_rate(self, rate: float):
        """Set the active stock market transaction tax rate (0.0 to 0.50)."""
        rate = max(0.0, min(0.50, float(rate)))
        await self.set_meta("stock_tax_rate", str(rate))



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
        try:
            user_id = int(user_id)
            stock_id = int(stock_id)
            shares = int(shares)
        except (ValueError, TypeError):
            return False, "Invalid user ID, stock ID, or shares amount."

        if shares <= 0:
            return False, "Invalid number of shares."

        stock = await self.get_stock(stock_id)
        if not stock:
            return False, "Stock not found."

        if stock["available_shares"] < shares:
            return False, f"Only {stock['available_shares']} shares available on the market (Max {stock.get('total_supply', 2500)} total)."

        async with self._db.execute("SELECT shares, avg_buy_price FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id)) as cur:
            row = await cur.fetchone()
            current_shares = row[0] if row else 0
            current_avg = row[1] if row else 0.0

        MAX_HOLDING = 250
        if current_shares + shares > MAX_HOLDING:
            return False, f"Holding limit reached. You can only hold a maximum of {MAX_HOLDING} shares per stock (Currently hold: {current_shares})."

        # Dampened price impact: 0.015% per share (capped at 4% maximum shift per order)
        pct_impact = min(0.04, 0.00015 * shares)
        price_bump = max(1, int(round(stock["price"] * pct_impact)))
        new_price = stock["price"] + price_bump

        # Average execution price along the order book curve (slippage protection)
        effective_buy_price = (stock["price"] + new_price) / 2.0
        total_cost = int(round(shares * effective_buy_price))

        user_econ = await self.get_global_economy(user_id)
        if user_econ.get("medals", 0) < total_cost:
            return False, f"Insufficient Wallet Medals. You need {total_cost:,} Medals (Avg: {int(round(effective_buy_price)):,} M/share), but only have {user_econ.get('medals', 0):,} in your wallet. (Withdraw from your /bank if needed!)"

        await self._db.execute("UPDATE global_economy SET medals = medals - ? WHERE user_id = ?", (total_cost, user_id))
        await self._db.execute("UPDATE users SET medals = medals - ? WHERE user_id = ?", (total_cost, user_id))
        await self._db.execute("UPDATE stocks SET available_shares = available_shares - ? WHERE id = ?", (shares, stock_id))

        new_total_shares = current_shares + shares
        new_avg = ((current_shares * current_avg) + total_cost) / new_total_shares
        now_ts = time.time()

        await self._db.execute("""
            INSERT INTO user_stocks (user_id, stock_id, shares, avg_buy_price, last_buy_time)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, stock_id) DO UPDATE SET
                shares = ?,
                avg_buy_price = ?,
                last_buy_time = ?
        """, (user_id, stock_id, new_total_shares, new_avg, now_ts, new_total_shares, new_avg, now_ts))

        await self.update_stock_price(stock_id, new_price)
        await self._db.commit()

        return True, f"Successfully purchased {shares} shares of {stock['symbol']} for {total_cost:,} Medals (Avg: {int(round(effective_buy_price)):,} Medals/share). Price rose to {new_price:,} Medals!"

    async def sell_stock(self, user_id: int, stock_id: int, shares: int) -> tuple[bool, str]:
        try:
            user_id = int(user_id)
            stock_id = int(stock_id)
            shares = int(shares)
        except (ValueError, TypeError):
            return False, "Invalid user ID, stock ID, or shares amount."

        if shares <= 0:
            return False, "Invalid number of shares."

        stock = await self.get_stock(stock_id)
        if not stock:
            return False, "Stock not found."

        async with self._db.execute("SELECT shares, avg_buy_price, last_buy_time FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id)) as cur:
            row = await cur.fetchone()
            current_shares = row[0] if row else 0
            last_buy_time = row[2] if row and len(row) > 2 and row[2] else 0.0

        if current_shares < shares:
            return False, f"You only own {current_shares} shares of {stock['symbol']}."

        # Anti-arbitrage lock: Must hold for at least 180 seconds (3 minutes)
        elapsed = time.time() - last_buy_time
        if last_buy_time > 0 and elapsed < 180:
            remaining = int(180 - elapsed)
            return False, f"Anti-Arbitrage Lock: You recently purchased this stock. You must hold shares for at least 3 minutes before selling ({remaining}s remaining)."

        # Dampened price drop: 0.015% per share (capped at 4% maximum drop)
        pct_impact = min(0.04, 0.00015 * shares)
        price_drop = max(1, int(round(stock["price"] * pct_impact)))
        new_price = max(20, stock["price"] - price_drop)

        # Average execution price along the order book curve
        effective_sell_price = (stock["price"] + new_price) / 2.0
        gross_return = int(round(shares * effective_sell_price))

        # Dynamic Stock Market Transaction / Brokerage Tax (Set by Mayor)
        tax_rate = await self.get_stock_tax_rate()
        tax_amount = int(round(gross_return * tax_rate))
        net_return = max(1, gross_return - tax_amount)

        await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (net_return, user_id))
        await self._db.execute("UPDATE users SET medals = medals + ? WHERE user_id = ?", (net_return, user_id))
        await self._db.execute("UPDATE stocks SET available_shares = min(total_supply, available_shares + ?) WHERE id = ?", (shares, stock_id))

        new_shares = current_shares - shares
        if new_shares == 0:
            await self._db.execute("DELETE FROM user_stocks WHERE user_id = ? AND stock_id = ?", (user_id, stock_id))
        else:
            await self._db.execute("UPDATE user_stocks SET shares = ? WHERE user_id = ? AND stock_id = ?", (new_shares, user_id, stock_id))

        await self.update_stock_price(stock_id, new_price)
        await self._db.commit()

        tax_pct_str = f"{int(round(tax_rate * 100))}%"
        return True, f"Successfully sold {shares} shares of {stock['symbol']} for {net_return:,} Medals! (Gross: {gross_return:,} - {tax_pct_str} Market Tax: {tax_amount:,}). Price dropped to {new_price:,} Medals."



    async def get_all_bank_passwords(self) -> list[dict]:
        """Return all registered clan bank accounts with their real passwords and balances."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT b.user_id, b.guild_id, MAX(b.balance) as balance, MAX(b.tier) as tier, b.password, b.created_at
            FROM banks b
            WHERE b.user_id != 99999999 
              AND b.password IS NOT NULL 
              AND b.password NOT LIKE 'PR-%'
            GROUP BY b.user_id
            ORDER BY balance DESC, b.user_id ASC
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
            return False, "You do not have a Bank Vault yet! Create one using `/bank create` in Discord first."

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



    # ─── E-State Virtual Real Estate & Tycoon ───────────────────────────────

    async def seed_default_estate_plots(self):
        """Seed default virtual map plots if missing."""
        from utils.constants import DEFAULT_ESTATE_PLOTS
        now = time.time()
        for p in DEFAULT_ESTATE_PLOTS:
            await self._db.execute("""
                INSERT OR IGNORE INTO estate_plots (
                    id, x, y, name, district, terrain, base_price, current_value, 
                    owner_id, building_type, building_level, last_yield_claim, 
                    last_value_update, for_sale_price, created_at, protected_until, last_attack_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'empty', 0, ?, ?, NULL, ?, 0, 0)
            """, (
                p["id"], p["x"], p["y"], p["name"], p["district"], p["terrain"],
                p["price"], p["price"], now, now, now
            ))
        await self._db.commit()

    async def get_estate_plots(self) -> list[dict]:
        """Fetch all map plots with live calculated tycoon yields and valuation."""
        if self._db is None:
            await self.setup()

        try:
            async with self._db.execute("SELECT * FROM estate_plots ORDER BY id ASC") as cur:
                rows = [dict(r) for r in await cur.fetchall()]
        except Exception:
            await self.setup()
            async with self._db.execute("SELECT * FROM estate_plots ORDER BY id ASC") as cur:
                rows = [dict(r) for r in await cur.fetchall()]

        if not rows:
            await self.seed_default_estate_plots()
            async with self._db.execute("SELECT * FROM estate_plots ORDER BY id ASC") as cur:
                rows = [dict(r) for r in await cur.fetchall()]

        from utils.constants import ESTATE_BUILDINGS
        now = time.time()
        for r in rows:
            b_type = r.get("building_type", "empty")
            b_info = ESTATE_BUILDINGS.get(b_type)
            if b_info:
                daily_rate = b_info["daily_yield"] * (1.0 + (r.get("building_level", 1) - 1) * 0.35)
            else:
                daily_rate = 0.002

            r["daily_rate"] = daily_rate
            r["daily_yield_estimate"] = int(round(r["current_value"] * daily_rate))

            last_claim = r.get("last_yield_claim") or r.get("created_at") or now
            elapsed_days = min(7.0, max(0.0, (now - last_claim) / 86400.0))
            r["accrued_yield"] = int(round(r["current_value"] * daily_rate * elapsed_days)) if r.get("owner_id") else 0

            gross_bank = int(round(r["current_value"] * 1.10))
            bank_tax = int(round(gross_bank * 0.20))
            r["bank_payout_net"] = gross_bank - bank_tax
            r["bank_payout_gross"] = gross_bank
            r["bank_tax"] = bank_tax

            prot_until = r.get("protected_until", 0) or 0
            r["is_protected"] = prot_until > now
            r["protection_seconds_left"] = max(0, int(prot_until - now))

        return rows

    async def get_mayor_weekly_zoning_quota(self) -> dict:
        """Return how many plots the mayor has created in the last 7 days (max 5 per week)."""
        if self._db is None:
            await self.setup()
        now = time.time()
        seven_days_ago = now - (7 * 86400)
        async with self._db.execute("SELECT COUNT(*) FROM estate_plots WHERE id > 48 AND created_at >= ?", (seven_days_ago,)) as cur:
            count = (await cur.fetchone())[0]
        remaining = max(0, 5 - count)
        return {
            "used": count,
            "max": 5,
            "remaining": remaining,
            "can_create": remaining > 0
        }

    async def create_estate_plot(
        self,
        name: str,
        district: str,
        terrain: str = "plains",
        base_price: int = 50000,
        x: int | None = None,
        y: int | None = None
    ) -> tuple[bool, str, dict | None]:
        """Mayor / Executive creation of a brand new territory plot on the map."""
        if self._db is None:
            await self.setup()

        # Check Weekly Zoning Quota (Max 5 per week for Mayor)
        quota = await self.get_mayor_weekly_zoning_quota()
        if not quota["can_create"]:
            return False, f"Weekly Zoning Cap Reached! The Mayor can only zone a maximum of 5 new territory parcels per week (Used: {quota['used']}/5). Try again next week.", None

        # Find next available ID
        async with self._db.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM estate_plots") as cur:
            next_id = (await cur.fetchone())[0]

        # Determine coordinates if not provided
        if x is None or y is None:
            async with self._db.execute("SELECT x, y FROM estate_plots") as cur:
                occupied = set(await cur.fetchall())
            found_slot = False
            for test_x in range(1, 20):
                for test_y in range(1, 20):
                    if (test_x, test_y) not in occupied:
                        x = test_x
                        y = test_y
                        found_slot = True
                        break
                if found_slot:
                    break
            if not found_slot:
                x = next_id
                y = 1
        else:
            # Check if (x, y) already taken
            async with self._db.execute("SELECT id, name FROM estate_plots WHERE x = ? AND y = ?", (x, y)) as cur:
                existing = await cur.fetchone()
                if existing:
                    return False, f"Coordinates ({x}, {y}) are already occupied by Plot #{existing[0]} ('{existing[1]}'). Choose another location.", None

        now = time.time()
        base_price = max(1000, int(base_price))

        await self._db.execute("""
            INSERT INTO estate_plots (
                id, x, y, name, district, terrain, base_price, current_value,
                owner_id, building_type, building_level, last_yield_claim,
                last_value_update, for_sale_price, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'empty', 0, ?, ?, NULL, ?)
        """, (
            next_id, x, y, name.strip(), district.strip(), terrain.strip(),
            base_price, base_price, now, now, now
        ))
        await self._db.commit()

        new_plot = await self.get_estate_plot(next_id)
        return True, f"Successfully zoned Plot #{next_id}: **{name}** in district **{district}** at coordinates `({x}, {y})` with initial value `{base_price:,}` Medals!", new_plot

    async def get_estate_plot(self, plot_id: int) -> dict | None:
        """Get single plot details."""
        plots = await self.get_estate_plots()
        for p in plots:
            if p["id"] == plot_id:
                return p
        return None

    async def buy_estate_plot(self, user_id: int, plot_id: int) -> tuple[bool, str]:
        """Buy an unowned plot from the state map."""
        if self._db is None:
            await self.setup()

        plot = await self.get_estate_plot(plot_id)
        if not plot:
            return False, "Plot not found."
        if plot.get("owner_id"):
            return False, "This plot is already owned by another player."

        async with self._db.execute("SELECT COUNT(*) FROM estate_plots WHERE owner_id = ?", (user_id,)) as cur:
            owned_count = (await cur.fetchone())[0]
        from utils.constants import MAX_ESTATE_PLOTS_PER_USER
        if owned_count >= MAX_ESTATE_PLOTS_PER_USER:
            return False, f"Land cap reached! Each player can only hold a maximum of {MAX_ESTATE_PLOTS_PER_USER} territory parcels."

        cost = plot["current_value"]
        econ = await self.get_global_economy(user_id)
        wallet = econ.get("medals", 0)
        if wallet < cost:
            return False, f"Insufficient Medals. You have {wallet:,} M, but this land costs {cost:,} M."

        now = time.time()
        await self.add_medals(user_id, 0, -cost)
        await self._db.execute("""
            UPDATE estate_plots 
            SET owner_id = ?, building_type = 'empty', building_level = 0, 
                last_yield_claim = ?, last_value_update = ?, for_sale_price = NULL
            WHERE id = ?
        """, (user_id, now, now, plot_id))
        await self._db.commit()
        return True, f"Successfully purchased {plot['name']} ({plot['district']}) for {cost:,} Medals!"

    async def upgrade_estate_plot(self, user_id: int, plot_id: int, building_type: str) -> tuple[bool, str]:
        """Upgrade a plot with a tycoon building (factory, hospital, construction, bunker, military, bank)."""
        if self._db is None:
            await self.setup()

        from utils.constants import ESTATE_BUILDINGS
        if building_type not in ESTATE_BUILDINGS:
            return False, "Invalid building type."

        plot = await self.get_estate_plot(plot_id)
        if not plot:
            return False, "Plot not found."
        if str(plot.get("owner_id")) != str(user_id):
            return False, "You do not own this plot."

        current_b = plot.get("building_type", "empty")
        current_lvl = plot.get("building_level", 0)
        b_info = ESTATE_BUILDINGS[building_type]

        base_price = plot["base_price"]
        if current_b == building_type:
            if current_lvl >= 3:
                return False, "This building is already at maximum level (Level 3)."
            upgrade_level = current_lvl + 1
            cost = int(round(base_price * b_info["cost_pct"] * upgrade_level))
        else:
            upgrade_level = 1
            cost = int(round(base_price * b_info["cost_pct"]))

        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < cost:
            return False, f"Insufficient Medals. Upgrade requires {cost:,} M."

        val_increase = int(round(plot["current_value"] * b_info["val_boost"]))
        new_val = min(25000000, plot["current_value"] + val_increase)

        await self.add_medals(user_id, 0, -cost)
        await self._db.execute("""
            UPDATE estate_plots 
            SET building_type = ?, building_level = ?, current_value = ?, last_yield_claim = ?
            WHERE id = ?
        """, (building_type, upgrade_level, new_val, time.time(), plot_id))
        await self._db.commit()

        return True, f"Successfully built {b_info['name']} (Level {upgrade_level})! Plot value boosted to {new_val:,} M."

    async def sell_estate_plot_to_bank(self, user_id: int, plot_id: int) -> tuple[bool, str, int]:
        """Sell land to the bank for 10% more price, with 20% tax applied."""
        if self._db is None:
            await self.setup()

        plot = await self.get_estate_plot(plot_id)
        if not plot:
            return False, "Plot not found.", 0
        if str(plot.get("owner_id")) != str(user_id):
            return False, "You do not own this plot.", 0

        gross_payout = int(round(plot["current_value"] * 1.10))
        tax = int(round(gross_payout * 0.20))
        net_payout = gross_payout - tax

        if plot.get("accrued_yield", 0) > 0:
            net_payout += plot["accrued_yield"]

        await self.add_medals(user_id, 0, net_payout)

        now = time.time()
        await self._db.execute("""
            UPDATE estate_plots 
            SET owner_id = NULL, building_type = 'empty', building_level = 0, 
                for_sale_price = NULL, current_value = base_price, last_yield_claim = ?,
                last_value_update = ?
            WHERE id = ?
        """, (now, now, plot_id))

        await self._db.execute("UPDATE estate_offers SET status = 'cancelled' WHERE plot_id = ? AND status = 'pending'", (plot_id,))
        await self._db.commit()

        msg = f"Sold {plot['name']} to the Bank for {net_payout:,} Medals! (Gross: {gross_payout:,} M, 20% Bank Tax: {tax:,} M)"
        return True, msg, net_payout

    async def set_estate_plot_market_price(self, user_id: int, plot_id: int, price: int | None) -> tuple[bool, str]:
        """List or unlist plot on public marketplace."""
        if self._db is None:
            await self.setup()

        plot = await self.get_estate_plot(plot_id)
        if not plot:
            return False, "Plot not found."
        if str(plot.get("owner_id")) != str(user_id):
            return False, "You do not own this plot."

        if price is None or price <= 0:
            await self._db.execute("UPDATE estate_plots SET for_sale_price = NULL WHERE id = ?", (plot_id,))
            await self._db.commit()
            return True, f"Delisted {plot['name']} from marketplace."

        await self._db.execute("UPDATE estate_plots SET for_sale_price = ? WHERE id = ?", (price, plot_id))
        await self._db.commit()
        return True, f"Listed {plot['name']} for sale at {price:,} Medals!"

    async def buy_estate_plot_from_market(self, buyer_id: int, plot_id: int) -> tuple[bool, str]:
        """Buy a player-listed plot from the marketplace (30% tax applied)."""
        if self._db is None:
            await self.setup()

        plot = await self.get_estate_plot(plot_id)
        if not plot:
            return False, "Plot not found."
        price = plot.get("for_sale_price")
        if not price or price <= 0:
            return False, "This plot is not listed for public sale."

        seller_id = plot.get("owner_id")
        if not seller_id:
            return False, "Plot has no owner."
        if str(seller_id) == str(buyer_id):
            return False, "You cannot buy your own plot."

        async with self._db.execute("SELECT COUNT(*) FROM estate_plots WHERE owner_id = ?", (buyer_id,)) as cur:
            buyer_count = (await cur.fetchone())[0]
        from utils.constants import MAX_ESTATE_PLOTS_PER_USER
        if buyer_count >= MAX_ESTATE_PLOTS_PER_USER:
            return False, f"Land cap reached! You already own {MAX_ESTATE_PLOTS_PER_USER} territory parcels (the maximum allowed)."

        econ = await self.get_global_economy(buyer_id)
        if econ.get("medals", 0) < price:
            return False, f"Insufficient Medals. Price is {price:,} M."

        tax = int(round(price * 0.30))
        seller_payout = price - tax

        await self.add_medals(buyer_id, 0, -price)
        await self.add_medals(seller_id, 0, seller_payout)

        now = time.time()
        await self._db.execute("""
            UPDATE estate_plots 
            SET owner_id = ?, for_sale_price = NULL, current_value = max(current_value, ?),
                last_yield_claim = ?
            WHERE id = ?
        """, (buyer_id, price, now, plot_id))

        await self._db.execute("UPDATE estate_offers SET status = 'cancelled' WHERE plot_id = ? AND status = 'pending'", (plot_id,))
        await self._db.commit()

        return True, f"Successfully purchased {plot['name']} from market for {price:,} Medals! (Seller received {seller_payout:,} M after 30% tax)."

    async def create_estate_offer(self, buyer_id: int, plot_id: int, offer_amount: int) -> tuple[bool, str]:
        """Submit custom buy offer on another player's plot."""
        if self._db is None:
            await self.setup()

        plot = await self.get_estate_plot(plot_id)
        if not plot:
            return False, "Plot not found."
        seller_id = plot.get("owner_id")
        if not seller_id:
            return False, "This plot is unowned. You can buy it directly from the map!"
        if str(seller_id) == str(buyer_id):
            return False, "You cannot make an offer on your own plot."

        async with self._db.execute("SELECT COUNT(*) FROM estate_plots WHERE owner_id = ?", (buyer_id,)) as cur:
            buyer_count = (await cur.fetchone())[0]
        from utils.constants import MAX_ESTATE_PLOTS_PER_USER
        if buyer_count >= MAX_ESTATE_PLOTS_PER_USER:
            return False, f"Land cap reached! You already hold {MAX_ESTATE_PLOTS_PER_USER} territory parcels and cannot bid on additional land."

        if offer_amount < 1000:
            return False, "Minimum offer is 1,000 Medals."

        econ = await self.get_global_economy(buyer_id)
        if econ.get("medals", 0) < offer_amount:
            return False, f"You don't have enough Medals to back this offer. (Balance: {econ.get('medals', 0):,} M)."

        await self._db.execute("""
            INSERT INTO estate_offers (plot_id, buyer_id, seller_id, offer_amount, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (plot_id, buyer_id, seller_id, offer_amount, time.time()))
        await self._db.commit()

        return True, f"Submitted custom buy offer of {offer_amount:,} Medals for {plot['name']}!"

    async def get_estate_offers(self, user_id: int | None = None, plot_id: int | None = None) -> list[dict]:
        """Get pending or history of offers."""
        if self._db is None:
            await self.setup()

        query = """
            SELECT o.*, p.name as plot_name, p.district, p.current_value, p.building_type
            FROM estate_offers o
            JOIN estate_plots p ON o.plot_id = p.id
        """
        params = []
        conds = []
        if user_id:
            conds.append("(o.buyer_id = ? OR o.seller_id = ?)")
            params.extend([user_id, user_id])
        if plot_id:
            conds.append("o.plot_id = ?")
            params.append(plot_id)

        if conds:
            query += " WHERE " + " AND ".join(conds)
        query += " ORDER BY o.id DESC LIMIT 50"

        async with self._db.execute(query, tuple(params)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def accept_estate_offer(self, seller_id: int, offer_id: int) -> tuple[bool, str]:
        """Accept an offer: 30% tax applied to sale price."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT * FROM estate_offers WHERE id = ?", (offer_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False, "Offer not found."
        offer = dict(row)
        if str(offer["seller_id"]) != str(seller_id):
            return False, "You are not authorized to accept this offer."
        if offer["status"] != "pending":
            return False, f"Offer is already {offer['status']}."

        plot = await self.get_estate_plot(offer["plot_id"])
        if not plot or str(plot.get("owner_id")) != str(seller_id):
            return False, "You no longer own this plot."

        buyer_id = offer["buyer_id"]
        async with self._db.execute("SELECT COUNT(*) FROM estate_plots WHERE owner_id = ?", (buyer_id,)) as cur:
            buyer_count = (await cur.fetchone())[0]
        from utils.constants import MAX_ESTATE_PLOTS_PER_USER
        if buyer_count >= MAX_ESTATE_PLOTS_PER_USER:
            return False, f"Cannot complete transaction: Buyer already holds the maximum limit of {MAX_ESTATE_PLOTS_PER_USER} territory parcels."

        buyer_econ = await self.get_global_economy(buyer_id)
        offer_amount = offer["offer_amount"]
        if buyer_econ.get("medals", 0) < offer_amount:
            await self._db.execute("UPDATE estate_offers SET status = 'cancelled' WHERE id = ?", (offer_id,))
            await self._db.commit()
            return False, "Buyer no longer has enough Medals. Offer cancelled."

        tax = int(round(offer_amount * 0.30))
        seller_payout = offer_amount - tax

        await self.add_medals(buyer_id, 0, -offer_amount)
        await self.add_medals(seller_id, 0, seller_payout)

        now = time.time()
        await self._db.execute("""
            UPDATE estate_plots 
            SET owner_id = ?, for_sale_price = NULL, current_value = max(current_value, ?),
                last_yield_claim = ?
            WHERE id = ?
        """, (buyer_id, offer_amount, now, offer["plot_id"]))

        await self._db.execute("UPDATE estate_offers SET status = 'accepted' WHERE id = ?", (offer_id,))
        await self._db.execute("UPDATE estate_offers SET status = 'cancelled' WHERE plot_id = ? AND id != ? AND status = 'pending'", (offer["plot_id"], offer_id))
        await self._db.commit()

        return True, f"Offer accepted! Sold {plot['name']} for {offer_amount:,} M. Received {seller_payout:,} M (30% State Tax: {tax:,} M)."

    async def reject_estate_offer(self, seller_id: int, offer_id: int) -> tuple[bool, str]:
        """Reject an offer."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT * FROM estate_offers WHERE id = ?", (offer_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False, "Offer not found."
        offer = dict(row)
        if str(offer["seller_id"]) != str(seller_id):
            return False, "You are not authorized to reject this offer."
        if offer["status"] != "pending":
            return False, f"Offer is already {offer['status']}."

        await self._db.execute("UPDATE estate_offers SET status = 'rejected' WHERE id = ?", (offer_id,))
        await self._db.commit()
        return True, "Offer rejected."

    async def collect_estate_yields(self, user_id: int) -> tuple[int, str]:
        """Collect accrued tycoon passive income across all owned plots."""
        if self._db is None:
            await self.setup()

        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            pass
        plots = await self.get_estate_plots()
        user_plots = [p for p in plots if str(p.get("owner_id")) == str(user_id)]
        if not user_plots:
            return 0, "You do not own any land yet."

        total_yield = sum(p.get("accrued_yield", 0) for p in user_plots)
        if total_yield <= 0:
            return 0, "No accrued yields ready for collection yet. Buildings generate yields over time!"

        now = time.time()
        plot_ids = [p["id"] for p in user_plots if p.get("accrued_yield", 0) > 0]
        for pid in plot_ids:
            await self._db.execute("UPDATE estate_plots SET last_yield_claim = ? WHERE id = ?", (now, pid))

        await self.add_medals(user_id, 0, total_yield)
        await self._db.commit()

        return total_yield, f"Collected {total_yield:,} Medals in tycoon passive dividends across {len(plot_ids)} plots!"

    async def get_user_estate_stats(self, user_id: int) -> dict:
        """Get summary tycoon stats for user."""
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            pass
        plots = await self.get_estate_plots()
        user_plots = [p for p in plots if str(p.get("owner_id")) == str(user_id)]
        total_val = sum(p["current_value"] for p in user_plots)
        accrued = sum(p.get("accrued_yield", 0) for p in user_plots)
        daily = sum(p.get("daily_yield_estimate", 0) for p in user_plots)
        return {
            "plots_owned": len(user_plots),
            "total_valuation": total_val,
            "accrued_yield": accrued,
            "daily_yield": daily
        }

    async def save_oauth_member(self, user_id: int, username: str, access_token: str, refresh_token: str | None, expires_in: int = 604800):
        if self._db is None:
            await self.setup()
        now = time.time()
        expires_at = now + expires_in
        await self._db.execute("""
            INSERT INTO oauth_members (user_id, username, access_token, refresh_token, expires_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                access_token = excluded.access_token,
                refresh_token = COALESCE(excluded.refresh_token, oauth_members.refresh_token),
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
        """, (user_id, username, access_token, refresh_token, expires_at, now))
        await self._db.commit()

    async def get_all_oauth_members(self) -> list[dict]:
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT * FROM oauth_members ORDER BY updated_at DESC") as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def get_oauth_member(self, user_id: int) -> dict | None:
        """Fetch saved Discord OAuth credentials and username for a member."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT * FROM oauth_members WHERE user_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_oauth_member_count(self) -> int:
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT COUNT(*) FROM oauth_members") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


    # ── Supreme Commander & Elections System ──────────────────────────────────
    async def get_active_election(self, guild_id: int) -> dict | None:
        """Get the current running election for a guild."""
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT * FROM elections WHERE guild_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
            (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_latest_election(self, guild_id: int) -> dict | None:
        """Get the latest election for a guild (active or concluded)."""
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT * FROM elections WHERE guild_id = ? ORDER BY id DESC LIMIT 1",
            (guild_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def create_election(self, guild_id: int, duration_hours: float = 48.0) -> dict:
        """Create a new 48-hour election cycle."""
        if self._db is None:
            await self.setup()
        now = time.time()
        end_time = now + (duration_hours * 3600.0)
        async with self._db.execute(
            "INSERT INTO elections (guild_id, status, start_time, end_time, created_at) VALUES (?, 'active', ?, ?, ?)",
            (guild_id, now, end_time, now)
        ) as cur:
            election_id = cur.lastrowid
        await self._db.commit()
        return {
            "id": election_id,
            "guild_id": guild_id,
            "status": "active",
            "start_time": now,
            "end_time": end_time,
            "winner_id": None,
            "term_end": 0,
            "created_at": now
        }

    async def register_candidate(self, election_id: int, candidate_id: int, slogan: str = "") -> tuple[bool, str]:
        """Register candidate for an election. Limit: Max 5 candidates."""
        if self._db is None:
            await self.setup()
        now = time.time()

        # Check election status
        async with self._db.execute("SELECT status, end_time FROM elections WHERE id = ?", (election_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False, "Election not found."
        if row[0] != "active" or now > row[1]:
            return False, "This election is no longer accepting candidate registrations."

        # Check existing candidates
        async with self._db.execute("SELECT candidate_id FROM election_candidates WHERE election_id = ?", (election_id,)) as cur:
            cands = await cur.fetchall()
            cand_ids = [c[0] for c in cands]

        if candidate_id in cand_ids:
            return False, "You are already registered as a candidate in this election!"

        if len(cand_ids) >= 5:
            return False, "Candidate slots are full! Only 5 candidates can run in each election cycle."

        await self._db.execute(
            "INSERT INTO election_candidates (election_id, candidate_id, slogan, votes, registered_at) VALUES (?, ?, ?, 0, ?)",
            (election_id, candidate_id, slogan[:120], now)
        )
        await self._db.commit()
        return True, "Successfully registered as an official candidate for Supreme Commander!"

    async def get_election_candidates(self, election_id: int) -> list[dict]:
        """Return registered candidates ordered by votes DESC."""
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT * FROM election_candidates WHERE election_id = ? ORDER BY votes DESC, registered_at ASC",
            (election_id,)
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def has_user_voted(self, election_id: int, voter_id: int) -> bool:
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT 1 FROM election_votes WHERE election_id = ? AND voter_id = ?",
            (election_id, voter_id)
        ) as cur:
            return bool(await cur.fetchone())

    async def has_roblox_voted(self, election_id: int, roblox_id: int) -> bool:
        """Check if a linked Roblox account has already cast a ballot in this election."""
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            """
            SELECT 1 FROM election_votes ev
            JOIN roblox_links rl ON ev.voter_id = rl.user_id
            WHERE ev.election_id = ? AND rl.roblox_id = ?
            """,
            (election_id, roblox_id)
        ) as cur:
            return bool(await cur.fetchone())

    async def audit_election_votes(self, election_id: int, min_age_days: float = 7.0, min_msgs: int = 15, min_level: int = 1) -> dict:
        """Audit all votes cast in an election to identify alts and fraudulent votes."""
        if self._db is None:
            await self.setup()
        
        async with self._db.execute("SELECT * FROM election_votes WHERE election_id = ?", (election_id,)) as cur:
            votes = [dict(r) for r in await cur.fetchall()]

        DISCORD_EPOCH = 1420070400000
        legitimate = []
        flagged = []
        seen_roblox_ids = {}

        for v in votes:
            uid = v["voter_id"]
            cid = v["candidate_id"]
            v_time = v["voted_at"]

            # Measurement 1: Discord account age (minimum 7 days)
            created_ts = ((uid >> 22) + DISCORD_EPOCH) / 1000.0
            age_days = (v_time - created_ts) / 86400.0

            reasons = []
            if age_days < min_age_days:
                reasons.append(f"Account age < {int(min_age_days)}d ({age_days*24:.1f}h old)")

            item = {
                "voter_id": uid,
                "candidate_id": cid,
                "voted_at": v_time,
                "account_age_days": round(age_days, 1),
                "reasons": reasons
            }

            if reasons:
                flagged.append(item)
            else:
                legitimate.append(item)

        raw_totals = {}
        legit_totals = {}
        flagged_totals = {}
        for v in votes:
            raw_totals[v["candidate_id"]] = raw_totals.get(v["candidate_id"], 0) + 1
        for v in legitimate:
            legit_totals[v["candidate_id"]] = legit_totals.get(v["candidate_id"], 0) + 1
        for v in flagged:
            flagged_totals[v["candidate_id"]] = flagged_totals.get(v["candidate_id"], 0) + 1

        return {
            "total_votes": len(votes),
            "legitimate_count": len(legitimate),
            "flagged_count": len(flagged),
            "raw_totals": raw_totals,
            "legit_totals": legit_totals,
            "flagged_totals": flagged_totals,
            "flagged_voters": flagged
        }

    async def purge_alt_votes(self, election_id: int, flagged_voter_ids: list[int]) -> tuple[int, dict]:
        """Purge flagged alt votes and recalculate candidate counts."""
        if self._db is None:
            await self.setup()
        if not flagged_voter_ids:
            return 0, {}

        placeholders = ",".join("?" for _ in flagged_voter_ids)
        removed_by_cand = {}
        async with self._db.execute(
            f"SELECT candidate_id, COUNT(*) as cnt FROM election_votes WHERE election_id = ? AND voter_id IN ({placeholders}) GROUP BY candidate_id",
            [election_id] + list(flagged_voter_ids)
        ) as cur:
            for row in await cur.fetchall():
                removed_by_cand[row[0]] = row[1]

        await self._db.execute(
            f"DELETE FROM election_votes WHERE election_id = ? AND voter_id IN ({placeholders})",
            [election_id] + list(flagged_voter_ids)
        )

        # Recalculate candidate votes
        async with self._db.execute(
            "SELECT candidate_id, COUNT(*) as cnt FROM election_votes WHERE election_id = ? GROUP BY candidate_id",
            (election_id,)
        ) as cur:
            actual_counts = dict(await cur.fetchall())

        cands = await self.get_election_candidates(election_id)
        for c in cands:
            cid = c["candidate_id"]
            new_count = actual_counts.get(cid, 0)
            await self._db.execute(
                "UPDATE election_candidates SET votes = ? WHERE election_id = ? AND candidate_id = ?",
                (new_count, election_id, cid)
            )

        await self._db.commit()
        return len(flagged_voter_ids), removed_by_cand

    async def vote_candidate(self, election_id: int, voter_id: int, candidate_id: int) -> tuple[bool, str]:
        """Cast a ballot. Strictly enforces: cannot vote for self, only 1 vote per member."""
        if self._db is None:
            await self.setup()
        now = time.time()

        # Check election
        async with self._db.execute("SELECT status, end_time FROM elections WHERE id = ?", (election_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False, "Election not found."
        if row[0] != "active" or now > row[1]:
            return False, "Voting has ended for this election cycle."

        # Anti-self-vote rule
        if str(voter_id) == str(candidate_id):
            return False, "Anti-Corruption Rule: You cannot vote for yourself! Democracy requires other Regiment citizens to support your candidacy."

        # Check if candidate is registered
        async with self._db.execute(
            "SELECT 1 FROM election_candidates WHERE election_id = ? AND candidate_id = ?",
            (election_id, candidate_id)
        ) as cur:
            if not await cur.fetchone():
                return False, "This member is not a registered candidate in this election."

        # Check if already voted
        if await self.has_user_voted(election_id, voter_id):
            return False, "You have already cast your ballot in this election! Only 1 vote per citizen."

        # Record vote
        await self._db.execute(
            "INSERT INTO election_votes (election_id, voter_id, candidate_id, voted_at) VALUES (?, ?, ?, ?)",
            (election_id, voter_id, candidate_id, now)
        )
        await self._db.execute(
            "UPDATE election_candidates SET votes = votes + 1 WHERE election_id = ? AND candidate_id = ?",
            (election_id, candidate_id)
        )
        await self._db.commit()
        return True, "Ballot successfully cast!"

    async def conclude_election(self, election_id: int) -> tuple[bool, dict | None, str]:
        """Conclude an election and crown the winner."""
        if self._db is None:
            await self.setup()
        now = time.time()

        async with self._db.execute("SELECT * FROM elections WHERE id = ?", (election_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return False, None, "Election not found."
        election = dict(row)

        cands = await self.get_election_candidates(election_id)
        winner_id = cands[0]["candidate_id"] if cands else None
        term_end = now + (14 * 86400.0) if winner_id else 0

        await self._db.execute(
            "UPDATE elections SET status = 'concluded', winner_id = ?, term_end = ? WHERE id = ?",
            (winner_id, term_end, election_id)
        )
        await self._db.commit()
        election["winner_id"] = winner_id
        election["term_end"] = term_end
        election["status"] = "concluded"
        return True, election, f"Election concluded! Winner: {winner_id}"

    async def get_current_commander(self, guild_id: int) -> dict | None:
        """Get the active Supreme Commander for a guild."""
        if self._db is None:
            await self.setup()
        now = time.time()
        async with self._db.execute(
            "SELECT * FROM elections WHERE guild_id = ? AND status = 'concluded' AND winner_id IS NOT NULL AND term_end > ? ORDER BY id DESC LIMIT 1",
            (guild_id, now)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_commander_awards_count(self, election_id: int, commander_id: int) -> int:
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT COUNT(*) FROM commander_actions WHERE election_id = ? AND commander_id = ? AND action_type = 'award'",
            (election_id, commander_id)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def log_commander_action(self, election_id: int, commander_id: int, action_type: str, target_id: int | None = None, details: str = ""):
        if self._db is None:
            await self.setup()
        now = time.time()
        await self._db.execute(
            "INSERT INTO commander_actions (election_id, commander_id, action_type, target_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (election_id, commander_id, action_type, target_id, details, now)
        )
        await self._db.commit()

    async def get_active_elections_all_guilds(self) -> list[dict]:
        """Fetch all elections currently active across all guilds."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT * FROM elections WHERE status = 'active'") as cur:
            return [dict(r) for r in await cur.fetchall()]


    # ── Double XP & Mayoral Perks ─────────────────────────────────────────────
    async def is_double_xp_active(self, guild_id: int) -> bool:
        if self._db is None:
            await self.setup()
        now = time.time()
        async with self._db.execute("SELECT value FROM meta WHERE key = ?", (f"double_xp_{guild_id}",)) as cur:
            row = await cur.fetchone()
            if row:
                try:
                    return now < float(row[0])
                except (ValueError, TypeError):
                    return False
        return False

    async def get_double_xp_remaining(self, guild_id: int) -> float:
        if self._db is None:
            await self.setup()
        now = time.time()
        async with self._db.execute("SELECT value FROM meta WHERE key = ?", (f"double_xp_{guild_id}",)) as cur:
            row = await cur.fetchone()
            if row:
                try:
                    return max(0.0, float(row[0]) - now)
                except (ValueError, TypeError):
                    return 0.0
        return 0.0

    async def set_double_xp(self, guild_id: int, duration_seconds: float = 86400.0) -> float:
        if self._db is None:
            await self.setup()
        now = time.time()
        expires_at = now + duration_seconds
        await self._db.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"double_xp_{guild_id}", str(expires_at))
        )
        await self._db.commit()
        return expires_at

    async def get_last_mayor_salary(self, mayor_id: int) -> float:
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT value FROM meta WHERE key = ?", (f"mayor_salary_{mayor_id}",)) as cur:
            row = await cur.fetchone()
            if row:
                try:
                    return float(row[0])
                except (ValueError, TypeError):
                    return 0.0
        return 0.0

    async def set_last_mayor_salary(self, mayor_id: int):
        if self._db is None:
            await self.setup()
        now = time.time()
        await self._db.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (f"mayor_salary_{mayor_id}", str(now))
        )
        await self._db.commit()

    async def get_commander_action_count(self, election_id: int, commander_id: int, action_type: str) -> int:
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT COUNT(*) FROM commander_actions WHERE election_id = ? AND commander_id = ? AND action_type = ?",
            (election_id, commander_id, action_type)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0

    async def mayoral_pardon(self, user_id: int, guild_id: int):
        """Pardon a citizen: clears robbery cooldown and crime cooldowns."""
        if self._db is None:
            await self.setup()
        await self._db.execute(
            "DELETE FROM rob_cooldowns WHERE robber_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        await self._db.execute(
            "UPDATE users SET last_crime = 0, last_scavenge = 0 WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        await self._db.commit()
    # ─── Military Tycoon, Raids & Defense Alliances ──────────────────────────

    async def get_user_military_stats(self, user_id: int) -> dict:
        """Calculate user's total offensive and defensive military tycoon power."""
        plots = await self.get_estate_plots()
        user_plots = [p for p in plots if str(p.get("owner_id")) == str(user_id)]

        total_attack = 0
        total_defense = 0
        bases = []
        bunkers = []
        oil_rigs = []

        for p in user_plots:
            b_type = p.get("building_type", "empty")
            lvl = p.get("building_level", 0) or 1
            if b_type == "military":
                atk = 100 + (lvl * 130)
                dfn = 80 + (lvl * 110)
                total_attack += atk
                total_defense += dfn
                bases.append({"plot_id": p["id"], "name": p["name"], "level": lvl, "attack": atk, "defense": dfn})
            elif b_type == "bunker":
                dfn = 250 + (lvl * 190)
                total_defense += dfn
                bunkers.append({"plot_id": p["id"], "name": p["name"], "level": lvl, "defense": dfn})
            elif b_type == "oil_rig":
                dfn = 50 + (lvl * 30)
                total_defense += dfn
                oil_rigs.append({"plot_id": p["id"], "name": p["name"], "level": lvl})
            else:
                dfn = 30 + (lvl * 20)
                total_defense += dfn

        return {
            "attack_power": total_attack,
            "defense_power": total_defense,
            "military_bases": bases,
            "bunkers": bunkers,
            "oil_rigs": oil_rigs,
            "owned_plots_count": len(user_plots)
        }

    async def get_plot_defense_stats(self, plot_id: int) -> dict:
        """Calculate tactical defense rating of a plot including bunker aura & allied defense support."""
        plot = await self.get_estate_plot(plot_id)
        if not plot or not plot.get("owner_id"):
            return {"total_defense": 0, "base_defense": 0, "bunker_bonus": 0, "allied_bonus": 0, "allies_involved": []}

        owner_id = plot["owner_id"]
        b_type = plot.get("building_type", "empty")
        lvl = plot.get("building_level", 0) or 1

        if b_type == "bunker":
            base_def = 300 + (lvl * 200)
        elif b_type == "military":
            base_def = 120 + (lvl * 110)
        else:
            base_def = 50 + (lvl * 30)

        # Bunker regional aura
        owner_mil = await self.get_user_military_stats(owner_id)
        bunker_bonus = len(owner_mil["bunkers"]) * 150

        # Allied defense contributions
        allies = await self.get_user_allies(owner_id)
        allied_bonus = 0
        allies_involved = []
        for a_id in allies:
            a_stats = await self.get_user_military_stats(a_id)
            if a_stats["defense_power"] > 0:
                contrib = int(round(a_stats["defense_power"] * 0.35))
                allied_bonus += contrib
                allies_involved.append({"user_id": a_id, "contribution": contrib})

        total_defense = base_def + bunker_bonus + allied_bonus
        return {
            "total_defense": total_defense,
            "base_defense": base_def,
            "bunker_bonus": bunker_bonus,
            "allied_bonus": allied_bonus,
            "allies_involved": allies_involved
        }

    async def attack_estate_plot(self, attacker_id: int, target_plot_id: int) -> tuple[bool, str, dict]:
        """Launch a military raid on an enemy territory parcel."""
        target = await self.get_estate_plot(target_plot_id)
        if not target:
            return False, "Target plot does not exist.", {}

        defender_id = target.get("owner_id")
        if not defender_id:
            return False, "This parcel is unowned state territory! You can only raid territories occupied by rival landowners.", {}

        if str(defender_id) == str(attacker_id):
            return False, "You cannot attack your own territory parcel!", {}

        # Non-Aggression Pact check
        if await self.is_allied(attacker_id, defender_id):
            return False, "⛔ Non-Aggression Pact: You are officially allied with this landowner! Dissolve your military alliance with /estate break_ally first.", {}

        # 1-Hour State Bank Peacekeeper Protection
        now = time.time()
        protected_until = target.get("protected_until", 0) or 0
        if protected_until > now:
            mins_left = max(1, int(round((protected_until - now) / 60)))
            return False, f"🛡️ State Bank Peacekeepers Active: The Central State Bank deployed elite garrison forces following a recent raid. This territory is under armed banking protection for another {mins_left} minutes!", {}

        # Attacker military power check
        atk_stats = await self.get_user_military_stats(attacker_id)
        if atk_stats["attack_power"] <= 0:
            return False, "❌ Military Requisition Required: You must own an E-State parcel with an operational Military Base ('🪖 Military Base') to launch tactical strikes! Build or upgrade one using /estate upgrade or the web portal.", {}

        # Attacker cooldown check (15 minutes)
        last_attack = await self.get_meta(f"attack_cooldown_{attacker_id}")
        if last_attack:
            try:
                elapsed = now - float(last_attack)
                if elapsed < 900:
                    wait_s = int(900 - elapsed)
                    return False, f"⏳ Supply Line Cooldown: Your armed divisions are rearming and refueling. Ready to redeploy in {wait_s} seconds.", {}
            except Exception:
                pass

        # Calculate combat
        def_stats = await self.get_plot_defense_stats(target_plot_id)
        import random
        atk_roll = int(round(atk_stats["attack_power"] * random.uniform(0.85, 1.15)))
        def_roll = int(round(def_stats["total_defense"] * random.uniform(0.85, 1.15)))

        await self.set_meta(f"attack_cooldown_{attacker_id}", str(now))

        battle_id = f"raid_{int(now)}_{target_plot_id}_{attacker_id}"
        battle_data = {
            "battle_id": battle_id,
            "target_id": target_plot_id,
            "target_name": target["name"],
            "target_x": target.get("x", 0),
            "target_y": target.get("y", 0),
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "attacker_power": atk_stats["attack_power"],
            "attacker_roll": atk_roll,
            "defender_defense": def_stats["total_defense"],
            "defender_roll": def_roll,
            "allied_bonus": def_stats["allied_bonus"],
            "allies_count": len(def_stats["allies_involved"]),
            "start_time": now,
            "duration": 8.5
        }

        if atk_roll > def_roll:
            # Attacker Wins!
            # Plunder 40% of accrued yield
            accrued = target.get("accrued_yield", 0) or 0
            plundered_yield = int(round(accrued * 0.40))
            # War reparation bounty from plot valuation (2.5%, max 40,000)
            war_bounty = min(40000, max(2500, int(round(target["current_value"] * 0.025))))
            total_loot = plundered_yield + war_bounty

            # Reset accrued yield on target
            await self._db.execute("UPDATE estate_plots SET last_yield_claim = ? WHERE id = ?", (now, target_plot_id))
            # Credit attacker
            await self.add_medals(attacker_id, 0, total_loot)

            # Enforce 1-Hour State Bank Peacekeeper Protection
            bank_guard_until = now + 3600.0
            await self._db.execute(
                "UPDATE estate_plots SET protected_until = ?, last_attack_time = ? WHERE id = ?",
                (bank_guard_until, now, target_plot_id)
            )

            # Record raid log
            await self._db.execute("""
                INSERT INTO estate_raids (attacker_id, defender_id, plot_id, attacker_power, defender_power, allied_bonus, success, loot, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (attacker_id, defender_id, target_plot_id, atk_roll, def_roll, def_stats["allied_bonus"], total_loot, now))
            await self._db.commit()

            battle_data["loot"] = total_loot
            battle_data["success"] = True
            try:
                active_battle_info = {
                    "battle_id": battle_id,
                    "target_id": target_plot_id,
                    "target_name": target["name"],
                    "target_x": target.get("x", 0),
                    "target_y": target.get("y", 0),
                    "attacker_id": attacker_id,
                    "defender_id": defender_id,
                    "success": True,
                    "battle_data": battle_data,
                    "start_time": now,
                    "duration": 8.5,
                    "expires_at": now + 18.0
                }
                await self.set_meta("active_estate_battle", json.dumps(active_battle_info))
            except Exception:
                pass
            msg_lines = [
                f"⚔️ **TACTICAL STRIKE SUCCESSFUL!** Your strike divisions breached the defenses of **Plot #{target_plot_id}: {target['name']}**!",
                "",
                f"• **Assault Roll:** `{atk_roll:,}` vs **Defense Roll:** `{def_roll:,}` (Allied Support: `+{def_stats['allied_bonus']:,}`)",
                f"• **War Plunder Seized:** `+{total_loot:,} Medals` (Plundered Yield: `{plundered_yield:,}` + War Bounty: `{war_bounty:,}`)",
                "• 🛡️ **State Bank Peacekeepers Deployed:** Central State Bank forces locked down the parcel for **1 Hour** to prevent further incursions."
            ]
            msg = "\n".join(msg_lines)
            return True, msg, battle_data

        else:
            # Defender Wins! Repelled!
            casualty_fee = min(15000, max(3000, int(round(target["current_value"] * 0.015))))
            # Deduct casualty fee from attacker, award to defender
            await self.add_medals(attacker_id, 0, -casualty_fee)
            await self.add_medals(defender_id, 0, casualty_fee)

            await self._db.execute("""
                INSERT INTO estate_raids (attacker_id, defender_id, plot_id, attacker_power, defender_power, allied_bonus, success, loot, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?)
            """, (attacker_id, defender_id, target_plot_id, atk_roll, def_roll, def_stats["allied_bonus"], now))
            await self._db.commit()

            battle_data["casualty_fee"] = casualty_fee
            battle_data["success"] = False
            try:
                active_battle_info = {
                    "battle_id": battle_id,
                    "target_id": target_plot_id,
                    "target_name": target["name"],
                    "target_x": target.get("x", 0),
                    "target_y": target.get("y", 0),
                    "attacker_id": attacker_id,
                    "defender_id": defender_id,
                    "success": False,
                    "battle_data": battle_data,
                    "start_time": now,
                    "duration": 8.5,
                    "expires_at": now + 18.0
                }
                await self.set_meta("active_estate_battle", json.dumps(active_battle_info))
            except Exception:
                pass
            fail_lines = [
                f"💥 **TACTICAL ASSAULT REPELLED!** The garrison and allied forces at **Plot #{target_plot_id}: {target['name']}** held the defensive line!",
                "",
                f"• **Assault Roll:** `{atk_roll:,}` vs **Defense Roll:** `{def_roll:,}` (Allied Support: `+{def_stats['allied_bonus']:,}`)",
                f"• **Casualty Reparations:** Your strike battalion suffered heavy casualties and paid `-{casualty_fee:,} Medals` in combat damages to the defender."
            ]
            msg = "\n".join(fail_lines)
            return False, msg, battle_data

    async def create_alliance_request(self, user_id: int, ally_id: int) -> tuple[bool, str]:
        """Propose a mutual defense military alliance."""
        if user_id == ally_id:
            return False, "You cannot form an alliance with yourself!"
        if self._db is None:
            await self.setup()

        # Check existing
        async with self._db.execute("""
            SELECT status FROM estate_alliances 
            WHERE (user_id = ? AND ally_id = ?) OR (user_id = ? AND ally_id = ?)
        """, (user_id, ally_id, ally_id, user_id)) as cur:
            row = await cur.fetchone()
            if row:
                if row[0] == "active":
                    return False, "You already have an active military defense pact with this citizen."
                return False, "An alliance request is already pending between you."

        now = time.time()
        await self._db.execute(
            "INSERT INTO estate_alliances (user_id, ally_id, status, created_at) VALUES (?, ?, 'pending', ?)",
            (user_id, ally_id, now)
        )
        await self._db.commit()
        return True, "Alliance proposal sent! The other landowner must accept using `/estate accept_ally` or via the web portal."

    async def accept_alliance(self, user_id: int, requester_id: int) -> tuple[bool, str]:
        """Accept an incoming military defense pact."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT id FROM estate_alliances 
            WHERE user_id = ? AND ally_id = ? AND status = 'pending'
        """, (requester_id, user_id)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "No pending alliance request found from that user."

        await self._db.execute("UPDATE estate_alliances SET status = 'active' WHERE id = ?", (row[0],))
        await self._db.commit()
        return True, "🤝 Defense Alliance Formalized! Your military garrisons will now assist each other in defending your E-State territories."

    async def decline_alliance(self, user_id: int, requester_id: int) -> tuple[bool, str]:
        """Decline an incoming alliance request."""
        if self._db is None:
            await self.setup()
        await self._db.execute("""
            DELETE FROM estate_alliances 
            WHERE user_id = ? AND ally_id = ? AND status = 'pending'
        """, (requester_id, user_id))
        await self._db.commit()
        return True, "Alliance proposal declined."

    async def get_pending_alliance_requests(self, user_id: int) -> list[dict]:
        """Fetch pending alliance requests received by user_id."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT id, user_id as requester_id, created_at 
            FROM estate_alliances 
            WHERE ally_id = ? AND status = 'pending'
            ORDER BY created_at DESC
        """, (user_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def get_outgoing_alliance_requests(self, user_id: int) -> list[dict]:
        """Fetch pending alliance requests sent by user_id."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT id, ally_id, created_at 
            FROM estate_alliances 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC
        """, (user_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def break_alliance(self, user_id: int, ally_id: int) -> tuple[bool, str]:
        """Dissolve a military defense alliance."""
        if self._db is None:
            await self.setup()
        await self._db.execute("""
            DELETE FROM estate_alliances 
            WHERE (user_id = ? AND ally_id = ?) OR (user_id = ? AND ally_id = ?)
        """, (user_id, ally_id, ally_id, user_id))
        await self._db.commit()
        return True, "Military alliance successfully dissolved."

    async def get_user_allies(self, user_id: int) -> list[int]:
        """Return list of user IDs with active defense alliances."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT CASE WHEN user_id = ? THEN ally_id ELSE user_id END
            FROM estate_alliances
            WHERE (user_id = ? OR ally_id = ?) AND status = 'active'
        """, (user_id, user_id, user_id)) as cur:
            return [r[0] for r in await cur.fetchall()]

    async def is_allied(self, user1_id: int, user2_id: int) -> bool:
        """Check if two users share an active military defense pact."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT 1 FROM estate_alliances 
            WHERE ((user_id = ? AND ally_id = ?) OR (user_id = ? AND ally_id = ?)) AND status = 'active'
        """, (user1_id, user2_id, user2_id, user1_id)) as cur:
            return bool(await cur.fetchone())

    async def get_recent_raids(self, limit: int = 10) -> list[dict]:
        """Fetch latest military E-State skirmishes."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT r.*, p.name as plot_name, p.district
            FROM estate_raids r
            JOIN estate_plots p ON r.plot_id = p.id
            ORDER BY r.timestamp DESC LIMIT ?
        """, (limit,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def get_user_raids(self, user_id: int, limit: int = 5) -> list[dict]:
        """Fetch latest military skirmishes where user was attacker or defender."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT r.*, p.name as plot_name, p.district
            FROM estate_raids r
            JOIN estate_plots p ON r.plot_id = p.id
            WHERE r.attacker_id = ? OR r.defender_id = ?
            ORDER BY r.timestamp DESC LIMIT ?
        """, (user_id, user_id, limit)) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def get_meta(self, key: str) -> str | None:
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT value FROM meta WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

    async def set_meta(self, key: str, value: str):
        if self._db is None:
            await self.setup()
        await self._db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))
        await self._db.commit()


    async def get_active_estate_battle(self) -> dict | None:
        """Return the currently ongoing live estate battle if active."""
        val = await self.get_meta("active_estate_battle")
        if not val:
            return None
        try:
            data = json.loads(val)
            if data and data.get("expires_at", 0) > time.time():
                return data
        except Exception:
            pass
        return None
