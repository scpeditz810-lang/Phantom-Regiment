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

            CREATE TABLE IF NOT EXISTS earth_countries (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                flag TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                owner_id INTEGER DEFAULT NULL,
                gdp INTEGER NOT NULL,
                treasury INTEGER DEFAULT 1000000,
                stability INTEGER DEFAULT 80,
                unrest INTEGER DEFAULT 15,
                is_coastal INTEGER DEFAULT 1,
                tax_rate INTEGER DEFAULT 10,
                economic_doctrine TEXT DEFAULT 'free_market',
                military_doctrine TEXT DEFAULT 'volunteer',
                diplomatic_stance TEXT DEFAULT 'neutral',
                for_sale_price INTEGER DEFAULT NULL,
                last_yield_claim REAL DEFAULT 0,
                last_riot_check REAL DEFAULT 0,
                alliance_id INTEGER DEFAULT NULL,
                capital TEXT DEFAULT '',
                desc TEXT DEFAULT '',
                created_at REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS earth_buildings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                building_type TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                is_sabotaged INTEGER DEFAULT 0,
                sabotaged_until REAL DEFAULT 0,
                created_at REAL DEFAULT 0,
                UNIQUE(country_id, building_type),
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_cabinet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                appointed_at REAL NOT NULL,
                UNIQUE(country_id, role),
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_cabinet_invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                president_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL NOT NULL,
                responded_at REAL DEFAULT 0,
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_citizens (
                user_id INTEGER PRIMARY KEY,
                country_id INTEGER NOT NULL,
                joined_at REAL NOT NULL,
                reputation INTEGER DEFAULT 100,
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                tool_key TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                purchased_at REAL NOT NULL,
                UNIQUE(country_id, tool_key),
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_spies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_country_id INTEGER NOT NULL,
                codename TEXT NOT NULL,
                skill_level INTEGER DEFAULT 1,
                status TEXT DEFAULT 'idle',
                target_country_id INTEGER DEFAULT NULL,
                mission TEXT DEFAULT NULL,
                mission_end_time REAL DEFAULT 0,
                created_at REAL DEFAULT 0,
                FOREIGN KEY(owner_country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_intelligence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gatherer_country_id INTEGER NOT NULL,
                target_country_id INTEGER NOT NULL,
                intel_type TEXT NOT NULL,
                intel_data TEXT NOT NULL,
                expires_at REAL NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS earth_un_resolutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    target_country_id INTEGER,
    war_id INTEGER,
    sponsor_id INTEGER,
    details TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS earth_alliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                creator_country_id INTEGER NOT NULL,
                banner_color TEXT DEFAULT '#3b82f6',
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS earth_wars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_country_id INTEGER NOT NULL,
                defender_country_id INTEGER NOT NULL,
                scale TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                attacker_power INTEGER NOT NULL,
                defender_power INTEGER NOT NULL,
                attacker_divisions INTEGER DEFAULT 10,
                defender_divisions INTEGER DEFAULT 10,
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                reparations INTEGER DEFAULT 0,
                winner_country_id INTEGER DEFAULT NULL,
                FOREIGN KEY(attacker_country_id) REFERENCES earth_countries(id),
                FOREIGN KEY(defender_country_id) REFERENCES earth_countries(id)
            );

            CREATE TABLE IF NOT EXISTS earth_trade_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_a_id INTEGER NOT NULL,
                country_b_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                daily_tariff INTEGER DEFAULT 50000,
                created_at REAL NOT NULL,
                UNIQUE(country_a_id, country_b_id)
            );

            CREATE TABLE IF NOT EXISTS earth_country_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                offer_amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT 0,
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
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

            "ALTER TABLE earth_countries ADD COLUMN last_growth_tick REAL DEFAULT 0",
            "ALTER TABLE earth_cabinet ADD COLUMN username TEXT DEFAULT NULL",
            "ALTER TABLE earth_cabinet_invites ADD COLUMN username TEXT DEFAULT NULL",
            "ALTER TABLE earth_countries ADD COLUMN is_sanctioned INTEGER DEFAULT 0",
            "ALTER TABLE earth_countries ADD COLUMN sanction_reason TEXT DEFAULT NULL",
            "ALTER TABLE earth_countries ADD COLUMN sanction_expires REAL DEFAULT 0",
            "ALTER TABLE earth_country_offers ADD COLUMN offer_scope TEXT DEFAULT 'state'",
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

        await self.reset_virtual_economy_once()

        try:
            await self._db.execute("UPDATE stocks SET total_supply = 2500, available_shares = max(available_shares, 2000) WHERE total_supply < 2500")
        except Exception:
            pass
        await self.seed_default_stocks()
        await self.sanitize_stock_exploit()
        await self.seed_default_estate_plots()
        await self.seed_default_earth_countries()
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




    # ─── UNITED NATIONS & MAYOR PEACEKEEPING SYSTEM ───

    async def get_earth_un_status(self) -> dict:
        """Get UN Security Council status, presiding Mayor/Secretary-General, active wars, sanctions, and fund."""
        if self._db is None:
            await self.setup()

        # Look up current Mayor from elections table or fallback to server sovereign
        mayor_id = None
        mayor_name = "UN Security Council (Vacant - Run in /elections)"
        try:
            async with self._db.execute("SELECT winner_id FROM elections WHERE winner_id IS NOT NULL ORDER BY id DESC LIMIT 1") as cur:
                row = await cur.fetchone()
                if row and row[0]:
                    mayor_id = row[0]
                    async with self._db.execute("SELECT username FROM users WHERE user_id = ?", (mayor_id,)) as ucur:
                        urow = await ucur.fetchone()
                        if urow and urow[0]:
                            mayor_name = f"UN Secretary-General {urow[0]}"
                        else:
                            mayor_name = f"UN Secretary-General (ID: {mayor_id})"
        except Exception:
            pass

        # Calculate UN peacekeeping fund (starts at 500,000 Medals + 5% of global customs)
        un_fund = 500000
        try:
            async with self._db.execute("SELECT SUM(daily_tariff) FROM earth_trade_routes") as cur:
                crow = await cur.fetchone()
                if crow and crow[0]:
                    un_fund += int(crow[0] * 5)
        except Exception:
            pass

        # Active wars
        wars = await self.get_active_earth_wars()

        # Sanctioned countries
        sanctioned = []
        async with self._db.execute("SELECT id, name, flag, sanction_reason, sanction_expires FROM earth_countries WHERE is_sanctioned = 1") as cur:
            for r in await cur.fetchall():
                sanctioned.append({
                    "id": r[0],
                    "name": r[1],
                    "flag": r[2],
                    "sanction_reason": r[3],
                    "sanction_expires": r[4]
                })

        # Recent resolutions
        resolutions = []
        try:
            async with self._db.execute("SELECT id, resolution_type, target_country_id, war_id, mayor_id, details, created_at FROM earth_un_resolutions ORDER BY id DESC LIMIT 10") as cur:
                for r in await cur.fetchall():
                    resolutions.append({
                        "id": r[0],
                        "action": r[1],
                        "resolution_type": r[1],
                        "target_country_id": r[2],
                        "war_id": r[3],
                        "sponsor_id": r[4],
                        "mayor_id": r[4],
                        "details": r[5],
                        "created_at": r[6]
                    })
        except Exception:
            pass

        return {
            "mayor_id": mayor_id,
            "mayor_name": mayor_name,
            "un_fund": un_fund,
            "active_wars": wars,
            "sanctioned_countries": sanctioned,
            "recent_resolutions": resolutions
        }

    async def un_issue_ceasefire(self, mayor_id: int, war_id: int) -> tuple[bool, str]:
        """UN Secretary-General (Mayor) enforces an emergency ceasefire, immediately concluding an active war."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT id, attacker_id, defender_id, war_scale, is_active FROM earth_wars WHERE id = ?", (war_id,)) as cur:
            war = await cur.fetchone()

        if not war:
            return False, "War record not found."
        if not war[4]:
            return False, "This war has already concluded."

        now = time.time()
        # Conclude war with un_ceasefire status
        await self._db.execute("""
            UPDATE earth_wars
            SET is_active = 0, outcome = 'un_ceasefire', ended_at = ?
            WHERE id = ?
        """, (now, war_id))

        # Record resolution
        details = f"UN Security Council Resolution passed: Ceasefire enforced on War #{war_id} between Country #{war[1]} and #{war[2]}."
        await self._db.execute("""
            INSERT INTO earth_un_resolutions (resolution_type, war_id, mayor_id, details, created_at)
            VALUES ('CEASEFIRE', ?, ?, ?, ?)
        """, (war_id, mayor_id, details, now))

        await self._db.commit()
        return True, f"🕊️ UN Resolution Ratified: Emergency Ceasefire enforced on War #{war_id}! All combat operations halted immediately."

    async def un_impose_sanctions(self, mayor_id: int, country_id: int, reason: str, duration_hours: int = 48) -> tuple[bool, str]:
        """UN Secretary-General (Mayor) imposes binding economic sanctions on a rogue nation."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT id, name, flag FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            country = await cur.fetchone()

        if not country:
            return False, "Target country not found."

        now = time.time()
        expires = now + (duration_hours * 3600)

        await self._db.execute("""
            UPDATE earth_countries
            SET is_sanctioned = 1, sanction_reason = ?, sanction_expires = ?
            WHERE id = ?
        """, (reason, expires, country_id))

        details = f"UN Economic Sanctions imposed on {country[2]} {country[1]} for {duration_hours}h. Reason: {reason}."
        await self._db.execute("""
            INSERT INTO earth_un_resolutions (resolution_type, target_country_id, mayor_id, details, created_at, expires_at)
            VALUES ('SANCTION', ?, ?, ?, ?, ?)
        """, (country_id, mayor_id, details, now, expires))

        await self._db.commit()
        return True, f"🚫 UN Security Council Sanction Passed: Embargo imposed on {country[2]} **{country[1]}** for {duration_hours} hours! Yields halved, offensive warfare barred."

    async def un_lift_sanctions(self, mayor_id: int, country_id: int) -> tuple[bool, str]:
        """UN Secretary-General (Mayor) lifts economic sanctions from a country."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT id, name, flag, is_sanctioned FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            country = await cur.fetchone()

        if not country:
            return False, "Target country not found."
        if not country[3]:
            return False, f"{country[2]} {country[1]} is not currently under UN sanctions."

        now = time.time()
        await self._db.execute("""
            UPDATE earth_countries
            SET is_sanctioned = 0, sanction_reason = NULL, sanction_expires = 0
            WHERE id = ?
        """, (country_id,))

        details = f"UN Sanctions lifted from {country[2]} {country[1]} by order of UN Secretary-General."
        await self._db.execute("""
            INSERT INTO earth_un_resolutions (resolution_type, target_country_id, mayor_id, details, created_at)
            VALUES ('LIFT_SANCTION', ?, ?, ?, ?)
        """, (country_id, mayor_id, details, now))

        await self._db.commit()
        return True, f"🕊️ Sanctions Lifted: Trade restrictions and embargo removed from {country[2]} **{country[1]}**."

    async def un_send_humanitarian_aid(self, mayor_id: int, country_id: int, amount: int = 50000) -> tuple[bool, str]:
        """UN Secretary-General dispatches emergency relief grant from UN fund to calm severe unrest."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT id, name, flag, unrest, stability FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            country = await cur.fetchone()

        if not country:
            return False, "Target country not found."

        new_unrest = max(0, country[3] - 35)
        new_stability = min(100, country[4] + 20)
        now = time.time()

        await self._db.execute("""
            UPDATE earth_countries
            SET unrest = ?, stability = ?, treasury = treasury + ?
            WHERE id = ?
        """, (new_unrest, new_stability, amount, country_id))

        details = f"UN Humanitarian Relief Package of {amount:,} Medals dispatched to {country[2]} {country[1]} to quelled riots."
        await self._db.execute("""
            INSERT INTO earth_un_resolutions (resolution_type, target_country_id, mayor_id, details, created_at)
            VALUES ('AID', ?, ?, ?, ?)
        """, (country_id, mayor_id, details, now))

        await self._db.commit()
        return True, f"🏥 UN Humanitarian Relief Dispatched: Granted {amount:,} Medals to {country[2]} **{country[1]}**! Unrest lowered to {new_unrest}%, stability restored to {new_stability}%."


    async def siphon_earth_treasury(self, user_id: int, country_id: int, amount: int) -> tuple[bool, str, dict]:
        """Sovereign withdraws funds from the national treasury into personal wallet with corruption loss and severe civil unrest penalty."""
        if self._db is None:
            await self.setup()

        # Permission check: Only President
        async with self._db.execute("SELECT id, name, flag, owner_id, treasury, unrest, stability FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            c = await cur.fetchone()

        if not c:
            return False, "Country not found.", {}
        if str(c[3]) != str(user_id):
            return False, "⛔ Sovereign Privilege Required: Only the sitting President can access national treasury reserves!", {}

        current_treasury = c[4] or 0
        if current_treasury < 10000:
            return False, "State treasury reserves are depleted (minimum 10,000 M required).", {}

        amount = int(amount)
        if amount <= 0:
            return False, "Please enter a valid positive withdrawal amount.", {}

        # Max withdrawal limit: 20% of treasury at a time
        max_allowed = int(current_treasury * 0.20)
        if amount > max_allowed:
            return False, f"⛔ Treasury Protection Limit: You can withdraw at most 20% of national reserves at once (Max: {max_allowed:,} Medals)!", {}

        if amount > current_treasury:
            return False, "Insufficient treasury reserves.", {}

        # 25% Corruption Leakage Loss
        loss_fee = int(amount * 0.25)
        payout = amount - loss_fee

        # Civil Unrest and Stability Penalties
        unrest_spike = 20
        stab_drop = 15
        new_unrest = min(100, (c[5] or 0) + unrest_spike)
        new_stab = max(10, (c[6] or 80) - stab_drop)
        new_treasury = current_treasury - amount

        await self._db.execute("""
            UPDATE earth_countries
            SET treasury = ?, unrest = ?, stability = ?
            WHERE id = ?
        """, (new_treasury, new_unrest, new_stab, country_id))

        # Credit net payout to player
        await self.add_medals(user_id, payout)
        await self._db.commit()

        riot_warning = ""
        if new_unrest >= 85:
            riot_warning = " 🚨 IMMINENT REVOLUTION RISK! Citizens are preparing to storm the presidential palace!"
        elif new_unrest >= 60:
            riot_warning = " 🔥 Severe urban riots erupted across the capital!"

        msg = (
            f"💸 Treasury Withdrawn: Disbursed {amount:,} Medals from {c[2]} {c[1]} reserves. "
            f"Net received: +{payout:,} Medals (-{loss_fee:,} M corruption leakage). "
            f"⚠️ Penalty: +{unrest_spike}% Civil Unrest (Now {new_unrest}%), -{stab_drop}% Stability (Now {new_stab}%).{riot_warning}"
        )

        return True, msg, {
            "amount": amount,
            "payout": payout,
            "loss_fee": loss_fee,
            "new_treasury": new_treasury,
            "new_unrest": new_unrest,
            "new_stability": new_stab
        }

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



    async def subtract_medals(self, user_id: int, amount: int):
        await self.add_medals(user_id, 0, -abs(int(amount)))

    async def add_medals(self, user_id: int, guild_id: int = 0, amount: int | None = None):
        if amount is None:
            amount = int(guild_id)
            guild_id = 0
        else:
            amount = int(amount)
            guild_id = int(guild_id) if guild_id else 0

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



    async def sanitize_stock_exploit(self):
        """Safety check to ensure stock prices never exceed the maximum ceiling."""
        try:
            async with self._db.execute("SELECT count(*) FROM stocks WHERE price > 300000") as cur:
                has_runaway_stocks = (await cur.fetchone())[0] > 0

            if not has_runaway_stocks:
                return

            print("[Safety] Clamping runaway stock prices to ceiling...", flush=True)
            stock_ceilings = {
                "PRC": 120000,
                "TSC": 250000,
                "VNG": 45000,
                "AERO": 65000,
                "CRYP": 95000,
                "TSLA": 250000,
                "PANDA": 35000
            }
            for sym, ceiling in stock_ceilings.items():
                await self._db.execute("UPDATE stocks SET price = min(price, ?) WHERE symbol = ?", (ceiling, sym))

            await self._db.execute("DELETE FROM stock_history WHERE price > 350000")
            await self._db.commit()
        except Exception as e:
            print(f"[Sanitizer Notice] {e}", flush=True)


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
        """, (user_id,)) as cur:
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


    # ═══════════════════════════════════════════════════════════════════════════
    # 🌍 VIRTUAL EARTH: 3D GEOPOLITICS SIMULATION DATABASE LAYER
    # ═══════════════════════════════════════════════════════════════════════════

    async def reset_virtual_economy_once(self):
        """Start a clean economy season once, preserving non-economy member data."""
        reset_key = "virtual_economy_reset_2026_10"
        if await self.get_meta(reset_key) == "complete":
            return False

        await self._db.execute("BEGIN IMMEDIATE")
        try:
            # Player currency, bank accounts, loans, insurance, and economy cooldowns.
            await self._db.execute("""
                UPDATE users SET medals = 0, last_daily = 0, last_work = 0,
                    last_weekly = 0, last_crime = 0, last_scavenge = 0, last_trivia = 0
            """)
            await self._db.execute("""
                UPDATE global_economy SET medals = 0, last_daily = 0, last_work = 0,
                    last_weekly = 0, last_crime = 0, last_scavenge = 0, last_trivia = 0
            """)
            for table in ("banks", "bank_loans", "player_loans", "bank_insurance", "streaks", "role_purchases"):
                await self._db.execute(f"DELETE FROM {table}")

            # Shares and trading history are reseeded from the default catalogue.
            for table in ("user_stocks", "stock_history", "stocks"):
                await self._db.execute(f"DELETE FROM {table}")
            await self._db.execute("DELETE FROM meta WHERE key = 'stock_tax_rate'")

            # Estate market: clear player plots, ownership, offers, alliances, and raids.
            for table in ("estate_raids", "estate_offers", "estate_alliances", "estate_plots"):
                await self._db.execute(f"DELETE FROM {table}")

            # Virtual Earth: reset the map and all player-created state to the base roster.
            for table in (
                "earth_country_offers", "earth_trade_routes", "earth_wars", "earth_alliances",
                "earth_intelligence", "earth_spies", "earth_tools", "earth_citizens",
                "earth_cabinet_invites", "earth_cabinet", "earth_buildings",
                "earth_un_resolutions", "earth_countries"
            ):
                await self._db.execute(f"DELETE FROM {table}")

            await self._db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (reset_key, "complete"))
            await self._db.commit()
            return True
        except Exception:
            await self._db.rollback()
            raise


    async def seed_default_earth_countries(self):
        """Seed the 42 sovereign Earth countries and migrate top E-State landowners."""
        from utils.constants import EARTH_COUNTRIES, EARTH_BUILDINGS
        
        async with self._db.execute("SELECT COUNT(*) FROM earth_countries") as cur:
            row = await cur.fetchone()
            count = row[0] if row else 0

        now = time.time()
        for c in EARTH_COUNTRIES:
            await self._db.execute("""
                INSERT OR IGNORE INTO earth_countries (
                    id, code, name, flag, lat, lng, owner_id, gdp, treasury, stability, unrest, is_coastal, capital, desc, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"], c["code"], c["name"], c["flag"], c["lat"], c["lng"],
                c.get("initial_owner_id"), c["gdp"], int(c["gdp"] * 0.15), 85, 12,
                c["is_coastal"], c.get("capital", ""), c.get("desc", ""), now
            ))
        await self._db.commit()

        # All base countries begin unclaimed; player ownership is earned in game.
        await self._db.commit()

        # Seed starter buildings for all sovereign nations that have owners
        async with self._db.execute("SELECT id, is_coastal FROM earth_countries WHERE owner_id IS NOT NULL") as cur:
            owned = [dict(r) for r in await cur.fetchall()]

        starter_types = ["school", "hospital", "heavy_factory", "bunker", "gold_mine"]
        for o in owned:
            cid = o["id"]
            for btype in starter_types:
                await self._db.execute("""
                    INSERT OR IGNORE INTO earth_buildings (country_id, building_type, level, created_at)
                    VALUES (?, ?, 1, ?)
                """, (cid, btype, now))
            if o.get("is_coastal"):
                await self._db.execute("""
                    INSERT OR IGNORE INTO earth_buildings (country_id, building_type, level, created_at)
                    VALUES (?, 'naval_port', 1, ?)
                """, (cid, now))
                await self._db.execute("""
                    INSERT OR IGNORE INTO earth_buildings (country_id, building_type, level, created_at)
                    VALUES (?, 'oil_rig', 1, ?)
                """, (cid, now))
        await self._db.commit()


    async def get_earth_countries(self) -> list[dict]:
        """Fetch all 42 countries with owner profiles, stats, active wars, and stability."""
        if self._db is None:
            await self.setup()

        # Trigger auto check for riots and revolutions
        try:
            await self.check_earth_riots_and_revolutions()
        except Exception:
            pass

        async with self._db.execute("""
            SELECT c.*, 
                   COALESCE(om.username, 'Citizen Sovereign') as owner_username,
                   NULL as owner_avatar,
                   al.name as alliance_name,
                   al.banner_color as alliance_color,
                   (SELECT COUNT(*) FROM earth_buildings b WHERE b.country_id = c.id) as building_count,
                   (SELECT COUNT(*) FROM earth_cabinet cab WHERE cab.country_id = c.id) as cabinet_count,
                   (SELECT COUNT(*) FROM earth_wars w WHERE (w.attacker_country_id = c.id OR w.defender_country_id = c.id) AND w.status = 'active') as active_war_count
            FROM earth_countries c
            LEFT JOIN oauth_members om ON c.owner_id = om.user_id
            LEFT JOIN earth_alliances al ON c.alliance_id = al.id
            ORDER BY c.gdp DESC
        """) as cur:
            rows = await cur.fetchall()
            result = []
            for r in rows:
                item = dict(r)
                item["is_rioting"] = (item.get("unrest", 0) >= 60)
                item["is_revolution_risk"] = (item.get("unrest", 0) >= 85)
                # Compute total defense power
                item["military_power"] = 50 + (item.get("building_count", 0) * 15)
                result.append(item)
            return result

    async def get_earth_country(self, country_id: int) -> dict | None:
        """Fetch full deep details of a country including buildings, cabinet, spies, and treaties."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("""
            SELECT c.*,
                   COALESCE(om.username, 'Citizen Sovereign') as owner_username,
                   NULL as owner_avatar,
                   al.name as alliance_name,
                   al.banner_color as alliance_color
            FROM earth_countries c
            LEFT JOIN oauth_members om ON c.owner_id = om.user_id
            LEFT JOIN earth_alliances al ON c.alliance_id = al.id
            WHERE c.id = ?
        """, (country_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            country = dict(row)

        country["buildings"] = await self.get_country_buildings(country_id)
        country["cabinet"] = await self.get_earth_cabinet(country_id)
        country["trade_routes"] = await self.get_earth_trade_routes(country_id)
        country["spies"] = await self.get_earth_spies(country_id)
        country["intelligence"] = await self.get_earth_intelligence(country_id)

        country["tools"] = await self.get_country_tools(country_id)

        # Calculate combat power
        mil_power = 20
        def_power = 30
        for b in country["buildings"]:
            mil_power += b.get("military_power", 0) * b.get("level", 1)
            def_power += b.get("defense_power", 0) * b.get("level", 1)

        for t in country["tools"]:
            mil_power += t.get("military_power", 0) * t.get("level", 1)
            def_power += t.get("defense_power", 0) * t.get("level", 1)

        doc = country.get("military_doctrine", "volunteer")
        from utils.constants import EARTH_DOCTRINES
        doc_info = EARTH_DOCTRINES.get("military", {}).get(doc, {})
        mult = doc_info.get("power_mult", 1.0)
        country["total_military_power"] = int(round(mil_power * mult))
        country["total_defense_power"] = int(round(def_power * mult))

        # Apply slow organic growth if country has a ruler
        if country.get("owner_id"):
            country = await self.apply_organic_growth(country)
            # Imperial commonwealth & conquered state metadata
            async with self._db.execute("SELECT id, name, flag, gdp FROM earth_countries WHERE owner_id = ? ORDER BY gdp DESC, id ASC", (country["owner_id"],)) as cur:
                empire_rows = await cur.fetchall()
            country["total_states_owned"] = len(empire_rows)
            if empire_rows and len(empire_rows) > 1:
                prim = empire_rows[0]
                if prim[0] != country_id:
                    country["is_annexed_state"] = True
                    country["motherland_id"] = prim[0]
                    country["motherland_name"] = prim[1]
                    country["motherland_flag"] = prim[2]
                    country["conquered_states_count"] = len(empire_rows) - 1
                else:
                    country["is_annexed_state"] = False
                    country["motherland_id"] = prim[0]
                    country["motherland_name"] = prim[1]
                    country["motherland_flag"] = prim[2]
                    country["conquered_states_count"] = len(empire_rows) - 1
            else:
                country["is_annexed_state"] = False
                country["conquered_states_count"] = 0
        else:
            country["total_states_owned"] = 0
            country["is_annexed_state"] = False
            country["conquered_states_count"] = 0

        return country

    async def get_earth_country_by_code(self, code: str) -> dict | None:
        """Fetch country by 3-letter code (e.g. RUS, IND, USA)."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT id FROM earth_countries WHERE UPPER(code) = UPPER(?)", (code,)) as cur:
            row = await cur.fetchone()
            if row:
                return await self.get_earth_country(row[0])
        return None

    async def get_user_earth_country(self, user_id: int) -> dict | None:
        """Fetch the country where the user is President/PM or a Cabinet Minister."""
        if self._db is None:
            await self.setup()

        # 1. Check if President
        async with self._db.execute("""
            SELECT id FROM earth_countries 
            WHERE owner_id = ?
            ORDER BY gdp DESC, id ASC
        """, (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                c = await self.get_earth_country(row[0])
                c["user_role"] = "president"
                c["role_title"] = "President & Supreme Sovereign"
                async with self._db.execute("SELECT id, name, flag, code, gdp FROM earth_countries WHERE owner_id = ? AND id != ?", (c.get("owner_id"), c["id"])) as cur2:
                    c["empire_states"] = [dict(s) for s in await cur2.fetchall()]
                return c

        # 2. Check if Cabinet Minister
        async with self._db.execute("""
            SELECT country_id, role FROM earth_cabinet 
            WHERE user_id = ?
        """, (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                c = await self.get_earth_country(row[0])
                c["user_role"] = row[1]
                from utils.constants import EARTH_CABINET_ROLES
                c["role_title"] = EARTH_CABINET_ROLES.get(row[1], {}).get("title", "Cabinet Minister")
                return c

        # 3. Check if Registered Citizen
        async with self._db.execute("""
            SELECT country_id FROM earth_citizens 
            WHERE user_id = ?
        """, (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                c = await self.get_earth_country(row[0])
                c["user_role"] = "citizen"
                c["role_title"] = "Citizen & Resident"
                return c

        return None

    async def get_country_buildings(self, country_id: int) -> list[dict]:
        """Get all constructed buildings for a country enriched with constants metadata."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_BUILDINGS

        async with self._db.execute("SELECT * FROM earth_buildings WHERE country_id = ? ORDER BY level DESC", (country_id,)) as cur:
            rows = await cur.fetchall()
            results = []
            now = time.time()
            for r in rows:
                b = dict(r)
                btype = b["building_type"]
                meta = EARTH_BUILDINGS.get(btype, {})
                b["name"] = meta.get("name", btype.title())
                b["emoji"] = meta.get("emoji", "🏗️")
                b["desc"] = meta.get("desc", "")
                b["hourly_yield"] = meta.get("hourly_yield", 0) * b["level"]
                b["military_power"] = meta.get("military_power", 0) * b["level"]
                b["defense_power"] = meta.get("defense_power", 0) * b["level"]
                cost_mult = meta.get("cost_multiplier", 1.5)
                b["upgrade_cost"] = int(meta.get("base_cost", 100000) * (cost_mult ** b["level"]))
                if b.get("sabotaged_until", 0) > now:
                    b["is_sabotaged"] = 1
                    b["sabotage_mins_left"] = int((b["sabotaged_until"] - now) / 60)
                else:
                    b["is_sabotaged"] = 0
                results.append(b)
            return results

    async def has_earth_cabinet_permission(self, user_id: int, country_id: int, required_role: str) -> bool:
        """Check if user is President (who can manage everything) OR appointed to required cabinet role."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT owner_id FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if row and str(row[0]) == str(user_id):
                return True

        async with self._db.execute("SELECT user_id FROM earth_cabinet WHERE country_id = ? AND role = ?", (country_id, required_role)) as cur:
            row = await cur.fetchone()
            if row and str(row[0]) == str(user_id):
                return True

        # Check if caller is minister in this country OR any country owned by the same sovereign (imperial commonwealth inheritance)
        async with self._db.execute("""
            SELECT cab.user_id FROM earth_cabinet cab
            JOIN earth_countries c ON cab.country_id = c.id
            WHERE cab.role = ? AND cab.user_id = ?
              AND c.owner_id = (SELECT owner_id FROM earth_countries WHERE id = ?)
        """, (required_role, user_id, country_id)) as cur:
            if await cur.fetchone():
                return True
        return False

    async def build_earth_infrastructure(self, user_id: int, country_id: int, building_type: str) -> tuple[bool, str, int]:
        """Construct or upgrade a national building (schools, hospitals, mines, oil rigs, factories, bunkers, ports)."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_BUILDINGS

        if building_type not in EARTH_BUILDINGS:
            return False, f"Invalid infrastructure type: {building_type}", 0

        # Permission check: President or Minister of Economy
        can_build = await self.has_earth_cabinet_permission(user_id, country_id, "economy")
        if not can_build:
            return False, "⛔ Authorization Denied: Only the President or the appointed Minister of Economy can commission national infrastructure!", 0

        meta = EARTH_BUILDINGS[building_type]
        base_cost = meta["base_cost"]
        cost_mult = meta["cost_multiplier"]

        # Check existing level
        async with self._db.execute("SELECT level FROM earth_buildings WHERE country_id = ? AND building_type = ?", (country_id, building_type)) as cur:
            row = await cur.fetchone()
            current_lvl = row[0] if row else 0

        cost = int(base_cost * (cost_mult ** current_lvl))

        # Check user medals
        user_econ = await self.get_global_economy(user_id)
        if user_econ.get("medals", 0) < cost:
            return False, f"Insufficient Medals: This project requires {cost:,} Medals (You have {user_econ.get('medals', 0):,}).", 0

        # Coastal check for naval port
        if building_type == "naval_port":
            async with self._db.execute("SELECT is_coastal FROM earth_countries WHERE id = ?", (country_id,)) as cur:
                c_row = await cur.fetchone()
                if not c_row or not c_row[0]:
                    return False, "⛔ Landlocked Territory: Deepwater Naval Ports can only be constructed in coastal sovereign nations!", 0

        # Deduct medals
        await self.subtract_medals(user_id, cost)

        now = time.time()
        new_level = current_lvl + 1
        if current_lvl > 0:
            await self._db.execute("UPDATE earth_buildings SET level = level + 1 WHERE country_id = ? AND building_type = ?", (country_id, building_type))
        else:
            await self._db.execute("INSERT INTO earth_buildings (country_id, building_type, level, created_at) VALUES (?, ?, 1, ?)", (country_id, building_type, now))

        # Boost country stats
        stab_boost = meta.get("stability_bonus", 0)
        unrest_drop = meta.get("unrest_reduction", 0)
        await self._db.execute("""
            UPDATE earth_countries
            SET stability = min(100, stability + ?),
                unrest = max(0, unrest - ?)
            WHERE id = ?
        """, (stab_boost, unrest_drop, country_id))
        await self._db.commit()

        return True, f"🏗️ Commissioned! {meta['emoji']} {meta['name']} upgraded to Level {new_level} (-{cost:,} Medals).", cost

    async def get_earth_cabinet(self, country_id: int) -> dict:
        """Get all appointed cabinet ministers with user names, roblox avatars, and imperial inheritance across annexed realms."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES

        result = {}
        for role_key, role_meta in EARTH_CABINET_ROLES.items():
            result[role_key] = {
                "role": role_key,
                "title": role_meta["title"],
                "short_title": role_meta["short_title"],
                "emoji": role_meta["emoji"],
                "desc": role_meta["desc"],
                "icon": role_meta["icon"],
                "user_id": None,
                "username": "Vacant (Managed by President)",
                "avatar": None,
                "appointed_at": 0,
                "is_imperial_inherit": False
            }

        # Query local cabinet appointees
        async with self._db.execute("""
            SELECT cab.role, cab.user_id, cab.appointed_at,
                   COALESCE(cab.username, rl.roblox_display, om.username) as resolved_name,
                   rl.roblox_id
            FROM earth_cabinet cab
            LEFT JOIN oauth_members om ON cab.user_id = om.user_id
            LEFT JOIN roblox_links rl ON (cab.user_id = rl.user_id OR rl.user_id BETWEEN cab.user_id - 250 AND cab.user_id + 250)
            WHERE cab.country_id = ?
        """, (country_id,)) as cur:
            for r in await cur.fetchall():
                rk = r[0]
                if rk in result:
                    uid = r[1]
                    name = r[3]
                    if not name or name.strip() == "":
                        name = f"Citizen @{uid}"
                    result[rk]["user_id"] = uid
                    result[rk]["appointed_at"] = r[2]
                    result[rk]["username"] = name
                    if r[4]:
                        result[rk]["avatar"] = f"https://www.roblox.com/headshot-thumbnail/image?userId={r[4]}&width=150&height=150&format=png"

        # Annexation Imperial Commonwealth Inheritance:
        # If any minister role is vacant, inherit from the supreme owner's primary country (e.g. Russia -> Japan)
        async with self._db.execute("SELECT id, name, flag, owner_id FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            c_row = await cur.fetchone()
            owner_id = c_row[3] if c_row else None

        if owner_id:
            async with self._db.execute("""
                SELECT id, name, flag FROM earth_countries
                WHERE owner_id = ? AND id != ?
                ORDER BY gdp DESC, id ASC LIMIT 1
            """, (owner_id, country_id)) as cur:
                prim_row = await cur.fetchone()

            if prim_row:
                prim_id, prim_name, prim_flag = prim_row[0], prim_row[1], prim_row[2]
                async with self._db.execute("""
                    SELECT cab.role, cab.user_id, cab.appointed_at,
                           COALESCE(cab.username, rl.roblox_display, om.username) as resolved_name,
                           rl.roblox_id
                    FROM earth_cabinet cab
                    LEFT JOIN oauth_members om ON cab.user_id = om.user_id
                    LEFT JOIN roblox_links rl ON (cab.user_id = rl.user_id OR rl.user_id BETWEEN cab.user_id - 250 AND cab.user_id + 250)
                    WHERE cab.country_id = ?
                """, (prim_id,)) as cur:
                    for pr in await cur.fetchall():
                        rk = pr[0]
                        # If vacant in the annexed realm, imperial command applies
                        if rk in result and result[rk]["user_id"] is None:
                            p_uid = pr[1]
                            p_name = pr[3] or f"Citizen @{p_uid}"
                            result[rk]["user_id"] = p_uid
                            result[rk]["appointed_at"] = pr[2]
                            result[rk]["username"] = f"{p_name} ({prim_flag} Imperial High Command)"
                            result[rk]["is_imperial_inherit"] = True
                            result[rk]["inherited_from"] = prim_name
                            if pr[4]:
                                result[rk]["avatar"] = f"https://www.roblox.com/headshot-thumbnail/image?userId={pr[4]}&width=150&height=150&format=png"

        # Attach pending nominations for vacant portfolios
        async with self._db.execute("""
            SELECT inv.id, inv.role, inv.user_id, inv.created_at,
                   COALESCE(inv.username, rl.roblox_display, om.username) as username
            FROM earth_cabinet_invites inv
            LEFT JOIN oauth_members om ON inv.user_id = om.user_id
            LEFT JOIN roblox_links rl ON (inv.user_id = rl.user_id OR rl.user_id BETWEEN inv.user_id - 250 AND inv.user_id + 250)
            WHERE inv.country_id = ? AND inv.status = 'pending'
            ORDER BY inv.id DESC
        """, (country_id,)) as cur:
            for r in await cur.fetchall():
                rk = r[1]
                if rk in result and result[rk]["user_id"] is None and "pending_invite" not in result[rk]:
                    uname = r[4] or f"Candidate {str(r[2])[-4:]}"
                    result[rk]["pending_invite"] = {
                        "invite_id": r[0],
                        "user_id": r[2],
                        "created_at": r[3],
                        "username": uname
                    }
        return result

    async def appoint_earth_cabinet(self, president_id: int, country_id: int, role: str, target_user_id: int, target_username: str = None) -> tuple[bool, str, dict]:
        """President nominates a player to a cabinet minister post. Requires nominee acceptance before taking office."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES

        if role not in EARTH_CABINET_ROLES:
            return False, f"Invalid cabinet role: {role}", {}

        role_info = EARTH_CABINET_ROLES[role]

        # Resolve nominee username if not provided
        if not target_username:
            if target_user_id in (1162404296097275904, 1162404296097276000):
                target_username = "TS_Aryan"
            else:
                async with self._db.execute("SELECT roblox_display, roblox_username FROM roblox_links WHERE user_id = ?", (target_user_id,)) as cur:
                    r_row = await cur.fetchone()
                    if r_row:
                        target_username = r_row[0] or r_row[1]
                if not target_username:
                    async with self._db.execute("SELECT username FROM oauth_members WHERE user_id = ?", (target_user_id,)) as cur:
                        m_row = await cur.fetchone()
                        if m_row:
                            target_username = m_row[0]

        # President check
        async with self._db.execute("SELECT owner_id, name, flag FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row or str(row[0]) != str(president_id):
                return False, "⛔ Sovereign Privilege Required: Only the President/PM of this nation can appoint Cabinet Ministers!", {}
            c_name = row[1]
            c_flag = row[2]

        # Self-appointment by sitting President auto-accepts
        if str(president_id) == str(target_user_id):
            now = time.time()
            await self._db.execute("""
                INSERT OR REPLACE INTO earth_cabinet (country_id, role, user_id, appointed_at, username)
                VALUES (?, ?, ?, ?, ?)
            """, (country_id, role, target_user_id, now, target_username))
            await self._db.commit()
            return True, f"🏛️ Decree Issued: You have directly assumed executive charge of {role_info['emoji']} **{role_info['title']}**!", {
                "auto_accepted": True,
                "country_id": country_id,
                "country_name": c_name,
                "country_flag": c_flag,
                "role": role,
                "role_title": role_info['title']
            }

        # Check if target is already President of another country
        async with self._db.execute("SELECT id, name FROM earth_countries WHERE owner_id = ? AND id != ?", (target_user_id, country_id)) as cur:
            pres_row = await cur.fetchone()
            if pres_row:
                return False, f"⛔ Candidate Conflict: <@{target_user_id}> is the sitting sovereign ruler of {pres_row[1]} and cannot serve as a foreign minister!", {}

        # Check if target is already active in this exact role
        async with self._db.execute("SELECT 1 FROM earth_cabinet WHERE country_id = ? AND role = ? AND user_id = ?", (country_id, role, target_user_id)) as cur:
            if await cur.fetchone():
                return False, f"⚠️ <@{target_user_id}> is already active as {role_info['title']} of {c_name}!!", {}

        # Cancel any previous pending invite for this specific portfolio
        await self._db.execute("UPDATE earth_cabinet_invites SET status = 'cancelled' WHERE country_id = ? AND role = ? AND status = 'pending'", (country_id, role))

        now = time.time()
        cur = await self._db.execute("""
            INSERT INTO earth_cabinet_invites (country_id, president_id, user_id, role, status, created_at, username)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (country_id, president_id, target_user_id, role, now, target_username))
        invite_id = cur.lastrowid
        await self._db.commit()

        display_target = target_username or f"<@{target_user_id}>"
        return True, f"📜 Presidential Decree Issued: Nominated {display_target} for {role_info['emoji']} **{role_info['title']}**! Candidate must formally accept the decree to take office.", {
            "invite_id": invite_id,
            "pending": True,
            "country_id": country_id,
            "country_name": c_name,
            "country_flag": c_flag,
            "role": role,
            "role_title": role_info['title'],
            "role_emoji": role_info['emoji'],
            "target_user_id": target_user_id,
            "target_username": target_username,
            "president_id": president_id
        }

    async def respond_earth_cabinet_invite(self, user_id: int, invite_id: int, accept: bool) -> tuple[bool, str]:
        """Candidate accepts or declines a ministerial cabinet nomination."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES

        async with self._db.execute("""
            SELECT inv.id, inv.country_id, inv.president_id, inv.user_id, inv.role, inv.status,
                   c.name, c.flag, c.owner_id, inv.username
            FROM earth_cabinet_invites inv
            JOIN earth_countries c ON inv.country_id = c.id
            WHERE inv.id = ?
        """, (invite_id,)) as cur:
            row = await cur.fetchone()

        if not row:
            return False, "Appointment decree not found or expired."

        if str(row[3]) != str(user_id):
            return False, "⛔ Unauthorized: This cabinet decree was issued to another player."

        if row[5] != "pending":
            return False, f"This decree is no longer pending (current status: {row[5]})."

        if str(row[2]) != str(row[8]):
            return False, "This decree is void: the issuing President no longer leads this nation."

        role_info = EARTH_CABINET_ROLES.get(row[4], {"title": row[4], "emoji": "🏛️"})
        now = time.time()

        if accept:
            inv_username = row[9]
            if not inv_username:
                if user_id in (1162404296097275904, 1162404296097276000):
                    inv_username = "TS_Aryan"
                else:
                    async with self._db.execute("SELECT roblox_display, roblox_username FROM roblox_links WHERE user_id = ?", (user_id,)) as cur:
                        r_row = await cur.fetchone()
                        if r_row:
                            inv_username = r_row[0] or r_row[1]
                    if not inv_username:
                        async with self._db.execute("SELECT username FROM oauth_members WHERE user_id = ?", (user_id,)) as cur:
                            m_row = await cur.fetchone()
                            if m_row:
                                inv_username = m_row[0]

            await self._db.execute("UPDATE earth_cabinet_invites SET status = 'accepted', responded_at = ? WHERE id = ?", (now, invite_id))
            # Vacate any other foreign cabinet positions held by the user
            await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (user_id,))
            # Appoint to the country's cabinet portfolio
            await self._db.execute("""
                INSERT OR REPLACE INTO earth_cabinet (country_id, role, user_id, appointed_at, username)
                VALUES (?, ?, ?, ?, ?)
            """, (row[1], row[4], user_id, now, inv_username))
            # Ensure citizen of this nation
            await self._db.execute("""
                INSERT OR REPLACE INTO earth_citizens (user_id, country_id, joined_at, reputation)
                VALUES (?, ?, ?, 100)
            """, (user_id, row[1], now))
            await self._db.commit()
            return True, f"🎉 Oath of Office Sworn: You have officially accepted the appointment as {role_info['emoji']} **{role_info['title']}** of {row[7]} {row[6]}!"
        else:
            await self._db.execute("UPDATE earth_cabinet_invites SET status = 'declined', responded_at = ? WHERE id = ?", (now, invite_id))
            await self._db.commit()
            return True, f"Decree declined. You turned down the appointment for {role_info['title']} of {row[7]} {row[6]}."

    async def cancel_earth_cabinet_invite(self, president_id: int, invite_id: int) -> tuple[bool, str]:
        """President rescinds an appointment decree before candidate accepts."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("SELECT id, president_id, country_id, status FROM earth_cabinet_invites WHERE id = ?", (invite_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Decree offer not found."
            if str(row[1]) != str(president_id):
                return False, "⛔ Only the appointing President can cancel this decree."
            if row[3] != "pending":
                return False, f"Decree is not pending (status: {row[3]})."

        await self._db.execute("UPDATE earth_cabinet_invites SET status = 'cancelled' WHERE id = ?", (invite_id,))
        await self._db.commit()
        return True, "Nomination decree cancelled."

    async def resign_earth_cabinet(self, user_id: int, country_id: int = None) -> tuple[bool, str]:
        """A minister resigns from their cabinet portfolio."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES
        sql = "SELECT country_id, role FROM earth_cabinet WHERE user_id = ?"
        params = [user_id, user_id, user_id]
        if country_id:
            sql += " AND country_id = ?"
            params.append(country_id)
        async with self._db.execute(sql, tuple(params)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "You do not currently hold any active ministerial cabinet portfolio."
            cid, role = row[0], row[1]

        await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ? AND country_id = ?", (user_id, cid))
        await self._db.commit()
        role_info = EARTH_CABINET_ROLES.get(role, {"title": role})
        return True, f"Resignation tendered. You have stepped down as **{role_info.get('title', role)}**. Portfolio duties have reverted to the President."

    async def get_user_pending_cabinet_invites(self, user_id: int) -> list[dict]:
        """Get all pending cabinet appointment offers sent to a user."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES
        async with self._db.execute("""
            SELECT inv.id, inv.country_id, inv.president_id, inv.role, inv.created_at,
                   c.name, c.flag,
                   COALESCE(om.username, 'President ' || inv.president_id) as president_name
            FROM earth_cabinet_invites inv
            JOIN earth_countries c ON inv.country_id = c.id
            LEFT JOIN oauth_members om ON inv.president_id = om.user_id
            WHERE inv.user_id = ? AND inv.status = 'pending'
            ORDER BY inv.id DESC
        """, (user_id,)) as cur:
            rows = await cur.fetchall()
            res = []
            for r in rows:
                rm = EARTH_CABINET_ROLES.get(r[3], {})
                res.append({
                    "id": r[0],
                    "country_id": r[1],
                    "president_id": r[2],
                    "role": r[3],
                    "created_at": r[4],
                    "country_name": r[5],
                    "country_flag": r[6],
                    "president_name": r[7],
                    "role_title": rm.get("title", r[3]),
                    "short_title": rm.get("short_title", r[3]),
                    "role_emoji": rm.get("emoji", "🏛️")
                })
            return res

    async def get_country_pending_cabinet_invites(self, country_id: int) -> list[dict]:
        """Get all pending outgoing cabinet decrees issued by a nation."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES
        async with self._db.execute("""
            SELECT inv.id, inv.user_id, inv.role, inv.created_at,
                   COALESCE(inv.username, om.username, 'Candidate ' || inv.user_id) as candidate_name
            FROM earth_cabinet_invites inv
            LEFT JOIN oauth_members om ON inv.user_id = om.user_id
            WHERE inv.country_id = ? AND inv.status = 'pending'
            ORDER BY inv.id DESC
        """, (country_id,)) as cur:
            rows = await cur.fetchall()
            res = []
            for r in rows:
                rm = EARTH_CABINET_ROLES.get(r[2], {})
                res.append({
                    "id": r[0],
                    "user_id": r[1],
                    "role": r[2],
                    "created_at": r[3],
                    "candidate_name": r[4],
                    "role_title": rm.get("title", r[2]),
                    "short_title": rm.get("short_title", r[2]),
                    "role_emoji": rm.get("emoji", "🏛️")
                })
            return res

    async def dismiss_earth_cabinet(self, president_id: int, country_id: int, role: str) -> tuple[bool, str]:
        """President dismisses a minister from cabinet portfolio."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_CABINET_ROLES

        async with self._db.execute("SELECT owner_id, name FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row or str(row[0]) != str(president_id):
                return False, "⛔ Sovereign Privilege Required: Only the President/PM can dismiss ministers from office!"
            c_name = row[1]

        await self._db.execute("DELETE FROM earth_cabinet WHERE country_id = ? AND role = ?", (country_id, role))
        await self._db.commit()

        role_info = EARTH_CABINET_ROLES.get(role, {"title": role})
        return True, f"Dismissed minister from {role_info.get('title')}. Authority returned directly to the President."

    async def buy_earth_country(self, user_id: int, country_id: int, offer: int = 0) -> tuple[bool, str]:
        """Purchase an unowned sovereign nation from the State Trust with Medals for any offered amount (0-inf, no tax)."""
        if self._db is None:
            await self.setup()

        # Check if user already owns a country
        async with self._db.execute("SELECT id, name FROM earth_countries WHERE owner_id = ?", (user_id,)) as cur:
            existing = await cur.fetchone()
            if existing:
                return False, f"? One Sovereign Rule: You already govern {existing[1]}! You cannot lead multiple nations simultaneously."

        async with self._db.execute("SELECT * FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Country not found."
            c = dict(row)

        if c.get("owner_id"):
            return False, f"This nation is already governed by <@{c['owner_id']}>. Make a diplomatic buyout offer instead!"

        # Offer amount (0 to infinity, no tax applied)
        try:
            offer = max(0, int(offer))
        except (ValueError, TypeError):
            offer = 0

        if offer > 0:
            econ = await self.get_global_economy(user_id)
            if econ.get("medals", 0) < offer:
                return False, f"Insufficient Capital: You offered {offer:,} Medals, but only have {econ.get('medals', 0):,} Medals in your wallet."

        now = time.time()
        # Conditional write prevents a stale request or a second ruler from winning.
        new_treasury = max(1000000, c.get("treasury", 1000000) + offer)
        async with self._db.execute("""
            UPDATE earth_countries
            SET owner_id = ?, stability = 80, unrest = 15, treasury = ?, last_yield_claim = ?, last_growth_tick = ?
            WHERE id = ? AND owner_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM earth_countries WHERE owner_id = ?)
        """, (user_id, new_treasury, now, now, country_id, user_id)) as cur:
            if cur.rowcount != 1:
                return False, "This nation was just claimed, or you already govern a country."

        if offer > 0:
            await self.subtract_medals(user_id, offer)
        
        # Relieve user from any prior ministerial cabinet post so they can rule independently
        await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (user_id,))

        # Register user as citizen/ruler of this country
        await self._db.execute("""
            INSERT OR REPLACE INTO earth_citizens (user_id, country_id, joined_at)
            VALUES (?, ?, ?)
        """, (user_id, country_id, now))
        await self._db.commit()

        # Pre-seed starter buildings
        starter_types = ["school", "hospital", "heavy_factory", "bunker", "gold_mine"]
        for btype in starter_types:
            await self._db.execute("""
                INSERT OR IGNORE INTO earth_buildings (country_id, building_type, level, created_at)
                VALUES (?, ?, 1, ?)
            """, (country_id, btype, now))
        if c.get("is_coastal"):
            await self._db.execute("""
                INSERT OR IGNORE INTO earth_buildings (country_id, building_type, level, created_at)
                VALUES (?, 'naval_port', 1, ?)
            """, (country_id, now))
        await self._db.commit()

        if offer == 0:
            return True, f"?? Sovereign Proclamation Signed! You have claimed the vacant nation of {c['flag']} **{c['name']}** completely for **FREE (0 Medals)**! Welcome, Supreme Sovereign!"
        return True, f"?? Proclamation Signed! You are now the official President and Sovereign Leader of {c['flag']} **{c['name']}** for {offer:,} Medals (0% Tax applied)!"

    async def create_custom_country(
        self,
        user_id: int,
        name: str,
        flag: str = "???",
        capital: str = "Capital City",
        lat: float = None,
        lng: float = None,
        offered_medals: int = 0,
        desc: str = "",
        replace_current: bool = False
    ) -> tuple[bool, str, dict | None]:
        """Found and charter a brand new custom sovereign nation for any medal offer (0 to infinity, no tax applied)."""
        if self._db is None:
            await self.setup()

        name = (name or "").strip()
        if len(name) < 2 or len(name) > 40:
            return False, "Country name must be between 2 and 40 characters.", None

        flag = (flag or "").strip() or "???"
        capital = (capital or "").strip() or "Capital City"
        desc = (desc or "").strip() or f"Sovereign nation of {name} founded by supreme decree."

        # Validate funding before relinquishing any existing country.
        async with self._db.execute("SELECT id, name FROM earth_countries WHERE owner_id = ? ORDER BY gdp DESC LIMIT 1", (user_id,)) as cur:
            existing = await cur.fetchone()
            if existing and not replace_current:
                return False, f"You already govern **{existing[1]}**! Choose the replace option only if you intend to abdicate.", None

        try:
            offered_medals = max(0, int(offered_medals))
        except (ValueError, TypeError):
            offered_medals = 0

        if offered_medals > 0:
            econ = await self.get_global_economy(user_id)
            if econ.get("medals", 0) < offered_medals:
                return False, f"Insufficient funds: You offered {offered_medals:,} Medals, but only have {econ.get('medals', 0):,} Medals in your wallet.", None

        if existing:
            await self._db.execute("""
                DELETE FROM earth_cabinet
                WHERE country_id IN (SELECT id FROM earth_countries WHERE owner_id = ?)
            """, (user_id,))
            await self._db.execute("UPDATE earth_countries SET owner_id = NULL WHERE owner_id = ?", (user_id,))

        if offered_medals > 0:
            await self.subtract_medals(user_id, offered_medals)

        # Relieve user from any prior ministerial cabinet post so they can found their own nation freely
        await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (user_id,))

        # Generate unique 3-4 letter code
        clean_code = "".join(ch for ch in name.upper() if ch.isalnum())
        if len(clean_code) >= 3:
            base_code = clean_code[:3]
        else:
            base_code = (clean_code + "X12")[:3]

        code = base_code
        suffix = 1
        while True:
            async with self._db.execute("SELECT 1 FROM earth_countries WHERE UPPER(code) = UPPER(?)", (code,)) as cur:
                if not await cur.fetchone():
                    break
            code = f"{base_code[:2]}{suffix}"
            suffix += 1
            if suffix > 99:
                import random
                code = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))

        # Coordinates
        if lat is None or lng is None:
            import random
            preset_locations = [
                (25.0, -40.0),    # Atlantis Mid-Atlantic
                (14.5, -140.0),   # Pacific Sanctuary
                (-8.5, 72.0),     # Chagos Indian Ocean
                (-17.5, -149.5),  # Polynesia Haven
                (21.5, -72.0),    # Caribbean Atoll
                (35.0, 18.0),     # Mediterranean Isle
                (-20.0, 57.5),    # Mauritius East
                (64.0, -20.0),    # North Atlantic Isle
                (-12.0, 96.8),    # Cocos Haven
                (0.5, -30.0)      # Equatorial Atlantic
            ]
            lat, lng = random.choice(preset_locations)
            lat = round(lat + random.uniform(-1.5, 1.5), 2)
            lng = round(lng + random.uniform(-1.5, 1.5), 2)
        else:
            lat = max(-80.0, min(80.0, float(lat)))
            lng = max(-180.0, min(180.0, float(lng)))

        now = time.time()
        # Initial stats: Offer directly seeds national treasury (0% tax!)
        initial_treasury = max(1000000, offered_medals)
        initial_gdp = max(10000000, 10000000 + (offered_medals * 2))

        async with self._db.execute("""
            INSERT INTO earth_countries (
                code, name, flag, lat, lng, owner_id, gdp, treasury,
                stability, unrest, is_coastal, tax_rate,
                economic_doctrine, military_doctrine, diplomatic_stance,
                capital, desc, created_at, last_yield_claim
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 85, 10, 1, 10, 'free_market', 'volunteer', 'neutral', ?, ?, ?, ?)
        """, (code, name, flag, lat, lng, user_id, initial_gdp, initial_treasury, capital, desc, now, now)) as cur:
            new_country_id = cur.lastrowid

        await self._db.commit()

        # Seed starter buildings
        starter_types = ["school", "hospital", "heavy_factory", "bunker", "gold_mine", "naval_port"]
        for btype in starter_types:
            await self._db.execute("""
                INSERT OR IGNORE INTO earth_buildings (country_id, building_type, level, created_at)
                VALUES (?, ?, 1, ?)
            """, (new_country_id, btype, now))
        await self._db.commit()

        country_data = {
            "id": new_country_id,
            "code": code,
            "name": name,
            "flag": flag,
            "capital": capital,
            "lat": lat,
            "lng": lng,
            "gdp": initial_gdp,
            "treasury": initial_treasury,
            "owner_id": user_id
        }

        return True, f"?? Sovereign Charter Proclaimed! {flag} **{name}** ({code}) has been founded! Your offer of {offered_medals:,} Medals has been deposited directly into the National Treasury (0% Tax applied).", country_data

    async def collect_earth_yield(self, user_id: int) -> tuple[int, str]:
        """Harvest hourly passive dividends from all national mines, rigs, schools, and ocean trade."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_DOCTRINES

        async with self._db.execute("SELECT * FROM earth_countries WHERE owner_id = ?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                c = dict(row)
                is_ruler = True
            else:
                is_ruler = False

        if not is_ruler:
            user_country = await self.get_user_earth_country(user_id)
            if not user_country:
                return 0, "You do not belong to a sovereign nation! You can buy/found a country or join an existing one as a citizen."
            c = user_country
            stipend = 3500 if c.get("user_role") == "citizen" else 8500
            await self.add_medals(user_id, stipend)
            return stipend, f"?? National Citizen Stipend Harvested! Received +{stipend:,} Medals from {c['flag']} {c['name']}." 

        now = time.time()
        last_claim = c.get("last_yield_claim", 0) or 0
        if last_claim == 0:
            last_claim = now - 3600

        elapsed_hours = min(24.0, max(0.01, (now - last_claim) / 3600.0))
        if elapsed_hours < (5.0 / 60.0): # 5 min cooldown
            return 0, "Dividends compound hourly. Please check back shortly!"

        # Sum building yields
        buildings = await self.get_country_buildings(c["id"])
        hourly_yield = sum(b.get("hourly_yield", 0) for b in buildings if not b.get("is_sabotaged"))

        # Add trade route tariffs
        trade_routes = await self.get_earth_trade_routes(c["id"])
        hourly_yield += len(trade_routes) * 3500

        # Apply economic doctrine multiplier
        doc = c.get("economic_doctrine", "free_market")
        doc_mult = EARTH_DOCTRINES.get("economic", {}).get(doc, {}).get("yield_mult", 1.0)
        hourly_yield = int(round(hourly_yield * doc_mult))

        # Check unrest penalty
        unrest = c.get("unrest", 0)
        riot_penalty = 1.0
        riot_warning = ""
        if unrest >= 60:
            riot_penalty = 0.50 # 50% loss due to riots!
            riot_warning = " ⚠️ (50% dividend loss due to active urban riots!)"
        elif unrest >= 30:
            riot_penalty = 0.85 # 15% loss due to civil strikes
            riot_warning = " (15% loss due to civil strikes)"

        total_payout = int(round(hourly_yield * elapsed_hours * riot_penalty))
        if total_payout <= 0:
            total_payout = 500

        # Credit player medals
        await self.add_medals(user_id, total_payout)
        # Credit 20% into national treasury
        treasury_deposit = int(total_payout * 0.20)
        await self._db.execute("""
            UPDATE earth_countries 
            SET last_yield_claim = ?, treasury = treasury + ?
            WHERE id = ?
        """, (now, treasury_deposit, c["id"]))
        await self._db.commit()

        return total_payout, f"⚡ Harvested +{total_payout:,} Medals from national infrastructure! (+{treasury_deposit:,} deposited into Treasury){riot_warning}"

    async def update_earth_policies(self, user_id: int, country_id: int, economic: str, military: str, diplomatic: str, tax_rate: int) -> tuple[bool, str]:
        """Update national doctrines and tax rate."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_DOCTRINES

        # Check permission: Owner or cabinet
        async with self._db.execute("SELECT owner_id FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row or str(row[0]) != str(user_id):
                return False, "⛔ Sovereign Privilege Required: Only the President can enact structural policy reforms!"

        tax_rate = max(0, min(50, int(tax_rate)))
        unrest_add = 0
        if tax_rate > 25:
            unrest_add += 15
        elif tax_rate > 15:
            unrest_add += 5

        await self._db.execute("""
            UPDATE earth_countries
            SET economic_doctrine = ?,
                military_doctrine = ?,
                diplomatic_stance = ?,
                tax_rate = ?,
                unrest = min(100, unrest + ?)
            WHERE id = ?
        """, (economic, military, diplomatic, tax_rate, unrest_add, country_id))
        await self._db.commit()

        return True, f"📜 National Policy Reform Enacted! Tax Rate set to {tax_rate}%. Economic: {economic.replace('_', ' ').title()}."

    async def quell_earth_unrest(self, user_id: int, country_id: int, method: str) -> tuple[bool, str]:
        """Deploy state resources to quell unrest and suppress riots."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "defense")
        if not can_manage:
            can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "economy")
        if not can_manage:
            return False, "⛔ Authorization Denied: Only the President or Defense/Economy Ministers can enact unrest relief measures!"

        econ = await self.get_global_economy(user_id)

        if method == "relief":
            cost = 150000
            if econ.get("medals", 0) < cost:
                return False, f"Requires {cost:,} Medals for civilian emergency stimulus."
            await self.subtract_medals(user_id, cost)
            await self._db.execute("""
                UPDATE earth_countries 
                SET unrest = max(0, unrest - 25), stability = min(100, stability + 15)
                WHERE id = ?
            """, (country_id,))
            await self._db.commit()
            return True, "🏥 Civilian Emergency Stimulus deployed: -25% Unrest, +15% Stability!"

        elif method == "police":
            cost = 80000
            if econ.get("medals", 0) < cost:
                return False, f"Requires {cost:,} Medals for tactical police suppression."
            await self.subtract_medals(user_id, cost)
            await self._db.execute("""
                UPDATE earth_countries 
                SET unrest = max(0, unrest - 35), stability = max(20, stability - 8)
                WHERE id = ?
            """, (country_id,))
            await self._db.commit()
            return True, "🛡️ Tactical Police Suppression deployed: -35% Unrest, -8% Civil Liberty."

        elif method == "festival":
            cost = 60000
            if econ.get("medals", 0) < cost:
                return False, f"Requires {cost:,} Medals to host a National Sovereign Jubilee."
            await self.subtract_medals(user_id, cost)
            await self._db.execute("""
                UPDATE earth_countries 
                SET unrest = max(0, unrest - 15), stability = min(100, stability + 20)
                WHERE id = ?
            """, (country_id,))
            await self._db.commit()
            return True, "🎉 National Sovereign Jubilee celebrated: -15% Unrest, +20% Stability!"

        return False, "Unknown pacification method."

    async def check_earth_riots_and_revolutions(self) -> list[dict]:
        """Scan countries for severe unrest and trigger regime changes / revolutions."""
        if self._db is None:
            await self.setup()

        events = []
        now = time.time()
        async with self._db.execute("SELECT id, name, flag, owner_id, unrest, stability, tax_rate FROM earth_countries WHERE owner_id IS NOT NULL") as cur:
            countries = [dict(r) for r in await cur.fetchall()]

        for c in countries:
            unrest = c.get("unrest", 0)
            cid = c["id"]

            # Tax rate pressure
            if c.get("tax_rate", 10) > 20:
                unrest = min(100, unrest + 2)

            # Massive Revolution / Regime Change (Unrest >= 85%)
            if unrest >= 85:
                old_leader = c["owner_id"]
                # Oust leader!
                await self._db.execute("""
                    UPDATE earth_countries 
                    SET owner_id = NULL, stability = 50, unrest = 25 
                    WHERE id = ?
                """, (cid,))
                await self._db.execute("DELETE FROM earth_cabinet WHERE country_id = ?", (cid,))
                await self._db.commit()
                events.append({
                    "type": "revolution",
                    "country_id": cid,
                    "name": c["name"],
                    "flag": c["flag"],
                    "ousted_leader_id": old_leader,
                    "message": f"🚨 MASSIVE REVOLUTION: Due to unchecked unrest ({unrest}%), the citizens of {c['flag']} {c['name']} stormed the Presidential Palace and ousted the government! The nation has returned to the Sovereign Trust."
                })

        return events

    # ─── Espionage & Intelligence System ──────────────────────────────────────

    async def get_earth_spies(self, country_id: int) -> list[dict]:
        """Fetch all secret agents in the nation's intelligence bureau."""
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT s.*, tc.name as target_country_name, tc.flag as target_country_flag
            FROM earth_spies s
            LEFT JOIN earth_countries tc ON s.target_country_id = tc.id
            WHERE s.owner_country_id = ?
            ORDER BY s.id DESC
        """, (country_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def recruit_earth_spy(self, user_id: int, country_id: int, codename: str) -> tuple[bool, str]:
        """Recruit a secret field operative for the nation's intelligence bureau."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "⛔ Authorization Denied: Only the President or the Director of Intelligence can recruit secret agents!"

        # Max 6 spies per country
        async with self._db.execute("SELECT COUNT(*) FROM earth_spies WHERE owner_country_id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if row and row[0] >= 6:
                return False, "Max operative capacity reached (6 Agents maximum per nation)."

        cost = 120000
        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < cost:
            return False, f"Recruiting an operative requires {cost:,} Medals."

        await self.subtract_medals(user_id, cost)
        now = time.time()
        await self._db.execute("""
            INSERT INTO earth_spies (owner_country_id, codename, skill_level, status, created_at)
            VALUES (?, ?, 1, 'idle', ?)
        """, (country_id, codename.strip(), now))
        await self._db.commit()

        return True, f"🕵️ Field Operative **Agent '{codename}'** inducted into Secret Intelligence Bureau (-{cost:,} Medals)."

    async def dispatch_earth_spy(self, user_id: int, country_id: int, spy_id: int, target_country_id: int, mission: str) -> tuple[bool, str, dict]:
        """Dispatch a secret agent to infiltrate a foreign sovereign nation."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_SPY_MISSIONS

        if mission not in EARTH_SPY_MISSIONS:
            return False, f"Invalid mission: {mission}", {}

        if country_id == target_country_id:
            return False, "You cannot dispatch espionage agents against your own nation!", {}

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "⛔ Authorization Denied: Only the President or Director of Intelligence can issue covert espionage orders!", {}

        # Fetch spy
        async with self._db.execute("SELECT * FROM earth_spies WHERE id = ? AND owner_country_id = ?", (spy_id, country_id)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Secret agent not found.", {}
            spy = dict(row)

        if spy.get("status") != "idle":
            return False, f"Agent '{spy['codename']}' is currently unavailable (Status: {spy.get('status')}).", {}

        meta = EARTH_SPY_MISSIONS[mission]
        target_country = await self.get_earth_country(target_country_id)
        if not target_country:
            return False, "Target sovereign country does not exist.", {}

        # Calculate capture risk
        target_bunkers = sum(b.get("level", 1) for b in target_country.get("buildings", []) if b["building_type"] == "bunker")
        capture_risk = meta["capture_risk"] + (target_bunkers * 0.03) - (spy["skill_level"] * 0.05)
        capture_risk = max(0.10, min(0.75, capture_risk))

        now = time.time()
        roll = random.random()

        if roll < capture_risk:
            # SPY CAUGHT!
            await self._db.execute("UPDATE earth_spies SET status = 'captured', target_country_id = ? WHERE id = ?", (target_country_id, spy_id))
            await self._db.commit()

            # Victim receives urgent security bulletin with Casus Belli
            intel_alert = {
                "alert": "agent_captured",
                "caught_codename": spy["codename"],
                "origin_country_id": country_id,
                "timestamp": now
            }
            await self._db.execute("""
                INSERT INTO earth_intelligence (gatherer_country_id, target_country_id, intel_type, intel_data, expires_at, created_at)
                VALUES (?, ?, 'incident', ?, ?, ?)
            """, (target_country_id, country_id, json.dumps(intel_alert), now + 604800, now))
            await self._db.commit()

            return False, f"🚨 COMPROMISED: Agent '{spy['codename']}' was detected and CAPTURED by {target_country['name']} counter-intelligence! The host nation has declared an International Diplomatic Incident.", {"captured": True}

        # SPY SUCCEEDED!
        mission_result = {}
        if mission == "intel":
            intel_dossier = {
                "target_name": target_country["name"],
                "flag": target_country["flag"],
                "gdp": target_country["gdp"],
                "treasury": target_country["treasury"],
                "stability": target_country["stability"],
                "unrest": target_country["unrest"],
                "total_military_power": target_country.get("total_military_power", 50),
                "total_defense_power": target_country.get("total_defense_power", 50),
                "buildings": [{"type": b["building_type"], "level": b["level"]} for b in target_country.get("buildings", [])],
                "alliances": target_country.get("alliance_name"),
                "gathered_at": now
            }
            await self._db.execute("""
                INSERT INTO earth_intelligence (gatherer_country_id, target_country_id, intel_type, intel_data, expires_at, created_at)
                VALUES (?, ?, 'full_dossier', ?, ?, ?)
            """, (country_id, target_country_id, json.dumps(intel_dossier), now + 86400, now))
            mission_result = intel_dossier

        elif mission == "sabotage":
            # Sabotage a building
            async with self._db.execute("SELECT id, building_type FROM earth_buildings WHERE country_id = ? AND is_sabotaged = 0 ORDER BY RANDOM() LIMIT 1", (target_country_id,)) as cur:
                target_b = await cur.fetchone()
                if target_b:
                    b_id, b_type = target_b
                    sab_until = now + 43200 # 12 hours
                    await self._db.execute("UPDATE earth_buildings SET is_sabotaged = 1, sabotaged_until = ? WHERE id = ?", (sab_until, b_id))
                    mission_result = {"sabotaged_building": b_type}

        elif mission == "incite_riot":
            # Spike unrest by +25%
            await self._db.execute("""
                UPDATE earth_countries 
                SET unrest = min(100, unrest + 25), stability = max(0, stability - 15)
                WHERE id = ?
            """, (target_country_id,))
            mission_result = {"unrest_added": 25}

        # Promote spy skill level
        await self._db.execute("UPDATE earth_spies SET skill_level = min(5, skill_level + 1) WHERE id = ?", (spy_id,))
        await self._db.commit()

        return True, f"🛰️ Espionage Mission Succeeded! Agent '{spy['codename']}' executed {meta['name']} in {target_country['name']} without detection.", mission_result

    async def get_earth_intelligence(self, country_id: int) -> list[dict]:
        """Fetch all stolen foreign state intelligence dossiers and security alerts."""
        if self._db is None:
            await self.setup()
        now = time.time()
        async with self._db.execute("""
            SELECT i.*, tc.name as target_name, tc.flag as target_flag
            FROM earth_intelligence i
            LEFT JOIN earth_countries tc ON i.target_country_id = tc.id
            WHERE i.gatherer_country_id = ? AND i.expires_at > ?
            ORDER BY i.created_at DESC
        """, (country_id, now)) as cur:
            rows = await cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                try:
                    item["data"] = json.loads(item["intel_data"])
                except Exception:
                    item["data"] = {}
                results.append(item)
            return results

    # ─── Multi-Day Conquest & Warfare System ──────────────────────────────────

    async def declare_earth_war(self, user_id: int, attacker_country_id: int, defender_country_id: int, scale: str) -> tuple[bool, str, dict]:
        """Declare a multi-day military conquest campaign (1 to 5 days)."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_WAR_SCALES

        if scale not in EARTH_WAR_SCALES:
            return False, f"Invalid war scale: {scale}", {}

        if attacker_country_id == defender_country_id:
            return False, "You cannot declare war upon yourself!", {}

        # Permission check: President or Army Commander
        can_command = await self.has_earth_cabinet_permission(user_id, attacker_country_id, "defense")
        if not can_command:
            return False, "⛔ Authorization Denied: Only the President or the Supreme Army Commander can declare military conquests!", {}

        meta = EARTH_WAR_SCALES[scale]
        atk = await self.get_earth_country(attacker_country_id)
        dfn = await self.get_earth_country(defender_country_id)
        if not atk or not dfn:
            return False, "Sovereign country not found.", {}

        # Check existing active war
        async with self._db.execute("""
            SELECT id FROM earth_wars 
            WHERE status = 'active' AND (
                (attacker_country_id = ? AND defender_country_id = ?) OR
                (attacker_country_id = ? AND defender_country_id = ?)
            )
        """, (attacker_country_id, defender_country_id, defender_country_id, attacker_country_id)) as cur:
            if await cur.fetchone():
                return False, "An active military campaign is already ongoing between these two sovereign powers!", {}

        # Alliance check: Cannot attack ally
        if atk.get("alliance_id") and dfn.get("alliance_id") and atk["alliance_id"] == dfn["alliance_id"]:
            return False, "⛔ Treaty Violation: You cannot declare war on a fellow member of your sovereign alliance!", {}

        # Imperial Expansion Cap: Max 4 conquered states (5 territories total)
        atk_owner = atk.get("owner_id")
        if atk_owner:
            async with self._db.execute("SELECT COUNT(*) FROM earth_countries WHERE owner_id = ?", (atk_owner,)) as cur:
                owned_count = (await cur.fetchone())[0]
            if owned_count >= 5:
                return False, "⛔ Imperial Expansion Limit Reached: Your empire already governs the maximum of 4 conquered states (5 territories total). Grant independence or sell an imperial state before waging new wars!", {}

        now = time.time()
        duration_s = meta["duration_seconds"]
        end_time = now + duration_s

        atk_power = atk.get("total_military_power", 50)
        dfn_power = dfn.get("total_defense_power", 50)

        # Apply allied defense bonus if defender has alliance
        if dfn.get("alliance_id"):
            async with self._db.execute("SELECT COUNT(*) FROM earth_countries WHERE alliance_id = ? AND id != ?", (dfn["alliance_id"], defender_country_id)) as cur:
                ally_count = (await cur.fetchone())[0]
                dfn_power += ally_count * 25 # +25 defense power per ally

        async with self._db.execute("""
            INSERT INTO earth_wars (
                attacker_country_id, defender_country_id, scale, status,
                attacker_power, defender_power, attacker_divisions, defender_divisions,
                start_time, end_time, reparations
            ) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
        """, (
            attacker_country_id, defender_country_id, scale,
            atk_power, dfn_power, meta["min_divisions"], meta["min_divisions"],
            now, end_time, meta["reparations"]
        )) as cur:
            war_id = cur.lastrowid
        await self._db.commit()

        war_data = {
            "war_id": war_id,
            "attacker_name": atk["name"],
            "attacker_flag": atk["flag"],
            "defender_name": dfn["name"],
            "defender_flag": dfn["flag"],
            "scale": scale,
            "scale_name": meta["name"],
            "duration_hours": meta["duration_hours"],
            "start_time": now,
            "end_time": end_time
        }
        return True, f"⚔️ WAR DECLARED! {atk['flag']} {atk['name']} launched a {meta['duration_hours']}-Hour {meta['name']} against {dfn['flag']} {dfn['name']}!", war_data

    async def get_active_earth_wars(self) -> list[dict]:
        """Fetch all ongoing multi-day global wars with progress percentages and 3D coordinates."""
        if self._db is None:
            await self.setup()

        # Conclude any expired wars
        try:
            await self.resolve_concluded_earth_wars()
        except Exception:
            pass

        now = time.time()
        async with self._db.execute("""
            SELECT w.*, 
                   ac.name as attacker_name, ac.flag as attacker_flag, ac.lat as atk_lat, ac.lng as atk_lng,
                   dc.name as defender_name, dc.flag as defender_flag, dc.lat as dfn_lat, dc.lng as dfn_lng
            FROM earth_wars w
            JOIN earth_countries ac ON w.attacker_country_id = ac.id
            JOIN earth_countries dc ON w.defender_country_id = dc.id
            WHERE w.status = 'active'
            ORDER BY w.start_time DESC
        """) as cur:
            rows = await cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                total_duration = max(1, item["end_time"] - item["start_time"])
                elapsed = max(0, now - item["start_time"])
                item["progress_pct"] = min(100.0, round((elapsed / total_duration) * 100.0, 1))
                item["hours_remaining"] = max(0.1, round((item["end_time"] - now) / 3600.0, 1))
                results.append(item)
            return results

    async def reinforce_earth_war(self, user_id: int, war_id: int, divisions: int) -> tuple[bool, str]:
        """Mobilize division reinforcements into an active war theater."""
        if self._db is None:
            await self.setup()

        divisions = max(1, min(50, divisions))
        cost = divisions * 25000

        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < cost:
            return False, f"Mobilizing {divisions} divisions requires {cost:,} Medals."

        async with self._db.execute("SELECT * FROM earth_wars WHERE id = ? AND status = 'active'", (war_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Active war campaign not found."
            war = dict(row)

        # Check which side user belongs to
        user_c = await self.get_user_earth_country(user_id)
        if not user_c:
            return False, "You do not govern a sovereign nation."

        cid = user_c["id"]
        is_attacker = (cid == war["attacker_country_id"])
        is_defender = (cid == war["defender_country_id"])

        if not is_attacker and not is_defender:
            return False, "Your nation is not directly involved in this military campaign."

        await self.subtract_medals(user_id, cost)
        if is_attacker:
            await self._db.execute("UPDATE earth_wars SET attacker_divisions = attacker_divisions + ?, attacker_power = attacker_power + ? WHERE id = ?", (divisions, divisions * 5, war_id))
        else:
            await self._db.execute("UPDATE earth_wars SET defender_divisions = defender_divisions + ?, defender_power = defender_power + ? WHERE id = ?", (divisions, divisions * 5, war_id))
        await self._db.commit()

        side_name = "Assault divisions" if is_attacker else "Defensive garrison divisions"
        return True, f"🪖 Mobilized +{divisions} {side_name} to the front line (-{cost:,} Medals)!"

    async def resolve_concluded_earth_wars(self) -> list[dict]:
        """Conclude wars that have elapsed their 1 to 5 day timeline."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_WAR_SCALES

        now = time.time()
        concluded = []
        async with self._db.execute("SELECT * FROM earth_wars WHERE status = 'active' AND end_time <= ?", (now,)) as cur:
            wars = [dict(r) for r in await cur.fetchall()]

        for w in wars:
            wid = w["id"]
            atk_score = w["attacker_power"] + (w["attacker_divisions"] * 3) + random.randint(10, 50)
            dfn_score = w["defender_power"] + (w["defender_divisions"] * 3) + random.randint(10, 50)

            scale_meta = EARTH_WAR_SCALES.get(w["scale"], {})
            plunder_pct = scale_meta.get("treasury_plunder_pct", 0.25)

            if atk_score > dfn_score:
                # Attacker won
                winner_id = w["attacker_country_id"]
                status = "attacker_won"
                # Plunder defender treasury
                async with self._db.execute("SELECT treasury, owner_id FROM earth_countries WHERE id = ?", (w["defender_country_id"],)) as cur:
                    dfn_row = await cur.fetchone()
                    dfn_treasury = dfn_row[0] if dfn_row else 1000000
                    loot = int(dfn_treasury * plunder_pct) + w.get("reparations", 100000)

                await self._db.execute("UPDATE earth_countries SET treasury = max(0, treasury - ?), unrest = min(100, unrest + 20) WHERE id = ?", (loot, w["defender_country_id"]))
                await self._db.execute("UPDATE earth_countries SET treasury = treasury + ? WHERE id = ?", (loot, w["attacker_country_id"]))

                # Imperial Annexation: If campaign scale is annexation or total world war
                if w.get("scale") in ("annexation", "world_war"):
                    async with self._db.execute("SELECT owner_id FROM earth_countries WHERE id = ?", (w["attacker_country_id"],)) as cur:
                        atk_owner_row = await cur.fetchone()
                        atk_owner = atk_owner_row[0] if atk_owner_row else None

                    if atk_owner:
                        async with self._db.execute("SELECT COUNT(*) FROM earth_countries WHERE owner_id = ?", (atk_owner,)) as cur:
                            owned_count = (await cur.fetchone())[0]

                        if owned_count < 5:  # Max 4 conquered states + 1 motherland = 5 total
                            await self._db.execute("""
                                UPDATE earth_countries 
                                SET owner_id = ?, unrest = 35, stability = 50 
                                WHERE id = ?
                            """, (atk_owner, w["defender_country_id"]))
                            await self._db.execute("DELETE FROM earth_cabinet WHERE country_id = ?", (w["defender_country_id"],))
            else:
                # Defender held the line
                winner_id = w["defender_country_id"]
                status = "defender_won"
                loot = w.get("reparations", 100000)
                await self._db.execute("UPDATE earth_countries SET treasury = treasury + ? WHERE id = ?", (loot, w["defender_country_id"]))

            await self._db.execute("UPDATE earth_wars SET status = ?, winner_country_id = ? WHERE id = ?", (status, winner_id, wid))
            await self._db.commit()
            concluded.append({"war_id": wid, "status": status, "winner_id": winner_id})

        return concluded

    async def expedition_attack_unclaimed(self, user_id: int, attacker_country_id: int, target_country_id: int, divisions: int = 10) -> tuple[bool, str, dict]:
        """Launch an armed military expedition to conquer an unclaimed frontier country (Max 4 conquered states)."""
        if self._db is None:
            await self.setup()

        # Permission check: President or Army Commander
        can_command = await self.has_earth_cabinet_permission(user_id, attacker_country_id, "defense")
        if not can_command:
            return False, "⛔ Authorization Denied: Only the President or Supreme Army Commander can launch military frontier expeditions!", {}

        atk = await self.get_earth_country(attacker_country_id)
        tgt = await self.get_earth_country(target_country_id)
        if not atk or not tgt:
            return False, "Sovereign country not found.", {}

        if tgt.get("owner_id"):
            return False, f"⛔ Frontier Claim Denied: {tgt['flag']} {tgt['name']} is already claimed by a sovereign ruler! Declare a formal war campaign instead of an unclaimed expedition.", {}

        atk_owner = atk.get("owner_id")
        if not atk_owner:
            return False, "Attacking nation has no sovereign ruler to register imperial territory under.", {}

        # Imperial Expansion Cap: Max 4 conquered states (5 territories total)
        async with self._db.execute("SELECT COUNT(*) FROM earth_countries WHERE owner_id = ?", (atk_owner,)) as cur:
            owned_count = (await cur.fetchone())[0]
        if owned_count >= 5:
            return False, "⛔ Imperial Expansion Limit Reached: Your empire already governs the maximum of 4 conquered states (5 territories total). Grant independence or sell an imperial state before expanding!", {}

        divisions = max(5, min(50, int(divisions)))
        cost = divisions * 20000
        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < cost:
            return False, f"Expedition mobilization of {divisions} divisions requires {cost:,} Medals (Current balance: {econ.get('medals', 0):,}).", {}

        await self.subtract_medals(user_id, cost)

        # Garrison resistance battle calculation
        garrison_resistance = tgt.get("total_defense_power", 50) + random.randint(15, 45)
        assault_power = atk.get("total_military_power", 50) + (divisions * 6) + random.randint(20, 60)

        if assault_power > garrison_resistance:
            # Conquest Successful: Annex country to sovereign
            await self._db.execute("""
                UPDATE earth_countries 
                SET owner_id = ?, unrest = 35, stability = 60, treasury = treasury + 50000
                WHERE id = ?
            """, (atk_owner, target_country_id))
            await self._db.commit()

            conquered_count = owned_count # now owned_count + 1 total, so conquered = owned_count
            return True, (
                f"🚩 **TERRITORIAL CONQUEST VICTORY!**\n\n"
                f"Your expeditionary force of **{divisions} divisions** smashed all frontier militia resistance "
                f"(Assault Power: `{assault_power}` vs Frontier Defense: `{garrison_resistance}`).\n\n"
                f"**{tgt['flag']} {tgt['name']}** has been annexed into the sovereign empire of **{atk['flag']} {atk['name']}**!\n"
                f"👑 Imperial Status: `{conquered_count}/4 Conquered States` governed."
            ), {
                "success": True,
                "target_name": tgt["name"],
                "target_flag": tgt["flag"],
                "conquered_count": conquered_count,
                "divisions": divisions
            }
        else:
            return False, (
                f"💥 **EXPEDITION REPELLED!**\n\n"
                f"Frontier defenders repelled the invasion force (Frontier Defense: `{garrison_resistance}` vs Assault Power: `{assault_power}`). "
                f"Lost {divisions} assault divisions (-{cost:,} Medals). Reorganize your troops and strike again!"
            ), {
                "success": False,
                "target_name": tgt["name"]
            }

    # ─── Ocean Trade Routes & Bilateral Commerce ──────────────────────────────

    async def propose_trade_route(self, user_id: int, from_country_id: int, to_country_id: int) -> tuple[bool, str]:
        """Inaugurate a bilateral maritime ocean trade shipping route."""
        if self._db is None:
            await self.setup()

        if from_country_id == to_country_id:
            return False, "Cannot establish ocean trade with yourself!"

        can_trade = await self.has_earth_cabinet_permission(user_id, from_country_id, "diplomat")
        if not can_trade:
            can_trade = await self.has_earth_cabinet_permission(user_id, from_country_id, "economy")
        if not can_trade:
            return False, "⛔ Authorization Denied: Only the President, Chief Diplomat, or Finance Minister can sign Ocean Trade Treaties!"

        c_a = await self.get_earth_country(from_country_id)
        c_b = await self.get_earth_country(to_country_id)
        if not c_a or not c_b:
            return False, "Country not found."

        if not c_a.get("is_coastal") or not c_b.get("is_coastal"):
            return False, "⛔ Maritime Access Required: Both countries must possess open oceanic coastlines to establish Maritime Shipping Lanes!"

        # Check naval ports
        has_port = any(b["building_type"] == "naval_port" for b in c_a.get("buildings", [])) or \
                   any(b["building_type"] == "naval_port" for b in c_b.get("buildings", []))
        if not has_port:
            return False, "⚓ Deepwater Naval Port Required: At least one nation must construct a Level 1 Deepwater Naval Port to operate cargo shipping lanes!"

        # Check existing route
        c1, c2 = min(from_country_id, to_country_id), max(from_country_id, to_country_id)
        async with self._db.execute("SELECT id FROM earth_trade_routes WHERE country_a_id = ? AND country_b_id = ?", (c1, c2)) as cur:
            if await cur.fetchone():
                return False, "An active Ocean Trade Route already exists between these two sovereign powers!"

        now = time.time()
        await self._db.execute("""
            INSERT INTO earth_trade_routes (country_a_id, country_b_id, status, daily_tariff, created_at)
            VALUES (?, ?, 'active', 85000, ?)
        """, (c1, c2, now))
        await self._db.commit()

        return True, f"🚢 Maritime Treaty Ratified! Ocean Trade Shipping Route active between {c_a['flag']} {c_a['name']} and {c_b['flag']} {c_b['name']} (+85k daily tariffs)!"

    async def get_earth_trade_routes(self, country_id: int | None = None) -> list[dict]:
        """Fetch active ocean trade routes with origin/destination lat/lng for 3D arcs."""
        if self._db is None:
            await self.setup()

        query = """
            SELECT tr.*, 
                   ca.name as a_name, ca.flag as a_flag, ca.lat as a_lat, ca.lng as a_lng,
                   cb.name as b_name, cb.flag as b_flag, cb.lat as b_lat, cb.lng as b_lng
            FROM earth_trade_routes tr
            JOIN earth_countries ca ON tr.country_a_id = ca.id
            JOIN earth_countries cb ON tr.country_b_id = cb.id
            WHERE tr.status = 'active'
        """
        params = ()
        if country_id is not None:
            query += " AND (tr.country_a_id = ? OR tr.country_b_id = ?)"
            params = (country_id, country_id)

        async with self._db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ─── Custom Global Alliances & Coalitions ──────────────────────────────────

    async def create_earth_alliance(self, user_id: int, country_id: int, name: str, banner_color: str = "#3b82f6") -> tuple[bool, str, int]:
        """Establish a new named global sovereign coalition/alliance."""
        if self._db is None:
            await self.setup()

        can_lead = await self.has_earth_cabinet_permission(user_id, country_id, "diplomat")
        if not can_lead:
            return False, "⛔ Authorization Denied: Only the President or Chief Diplomat can charter international coalitions!", 0

        name = name.strip()
        if len(name) < 3 or len(name) > 32:
            return False, "Alliance name must be between 3 and 32 characters.", 0

        cost = 500000
        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < cost:
            return False, f"Chartering a global alliance requires {cost:,} Medals.", 0

        now = time.time()
        try:
            async with self._db.execute("""
                INSERT INTO earth_alliances (name, creator_country_id, banner_color, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, country_id, banner_color, now)) as cur:
                alliance_id = cur.lastrowid
            await self._db.execute("UPDATE earth_countries SET alliance_id = ? WHERE id = ?", (alliance_id, country_id))
            await self._db.commit()
            await self.subtract_medals(user_id, cost)
            return True, f"🌐 Treaty Established! Custom Coalition **'{name}'** officially chartered! Member nations gain mutual defensive pacts.", alliance_id
        except Exception as e:
            return False, f"Alliance name already taken or invalid: {e}", 0

    async def join_earth_alliance(self, user_id: int, country_id: int, alliance_id: int) -> tuple[bool, str]:
        """Join an existing international sovereign coalition."""
        if self._db is None:
            await self.setup()

        can_lead = await self.has_earth_cabinet_permission(user_id, country_id, "diplomat")
        if not can_lead:
            return False, "⛔ Authorization Denied: Only the President or Chief Diplomat can sign alliance accession protocols!"

        async with self._db.execute("SELECT name FROM earth_alliances WHERE id = ?", (alliance_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Coalition treaty not found."
            al_name = row[0]

        await self._db.execute("UPDATE earth_countries SET alliance_id = ? WHERE id = ?", (alliance_id, country_id))
        await self._db.commit()
        return True, f"🤝 Acceded to **{al_name}**! Your nation is now under collective defense guarantees."

    async def leave_earth_alliance(self, user_id: int, country_id: int) -> tuple[bool, str]:
        """Withdraw from your current international coalition."""
        if self._db is None:
            await self.setup()

        can_lead = await self.has_earth_cabinet_permission(user_id, country_id, "diplomat")
        if not can_lead:
            return False, "⛔ Authorization Denied: Only the President or Chief Diplomat can renounce alliance membership!"

        await self._db.execute("UPDATE earth_countries SET alliance_id = NULL WHERE id = ?", (country_id,))
        await self._db.commit()
        return True, "Withdrew from alliance. Your nation is now non-aligned."

    async def get_earth_alliances(self) -> list[dict]:
        """Fetch all custom global coalitions with member lists and statistics."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT * FROM earth_alliances ORDER BY id DESC") as cur:
            alliances = [dict(r) for r in await cur.fetchall()]

        for al in alliances:
            alid = al["id"]
            async with self._db.execute("SELECT id, name, flag, gdp, owner_id FROM earth_countries WHERE alliance_id = ?", (alid,)) as cur:
                members = [dict(m) for m in await cur.fetchall()]
            al["members"] = members
            al["member_count"] = len(members)
            al["total_gdp"] = sum(m.get("gdp", 0) for m in members)

        return alliances

    # ─── Land Trading & Global Diplomatic Exchange ────────────────────────────

    async def set_country_market_price(self, user_id: int, country_id: int, price: int | None) -> tuple[bool, str]:
        """List or delist a sovereign country on the Global Diplomatic Exchange."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT owner_id, name FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row or str(row[0]) != str(user_id):
                return False, "You do not govern this country."
            c_name = row[1]

        if price is not None and price <= 0:
            price = None

        await self._db.execute("UPDATE earth_countries SET for_sale_price = ? WHERE id = ?", (price, country_id))
        await self._db.commit()

        if price:
            return True, f"Listed {c_name} for sale on the Global Diplomatic Exchange for {price:,} Medals!"
        return True, f"Delisted {c_name} from the Global Diplomatic Exchange."

    async def create_country_offer(self, buyer_id: int, country_id: int, amount: int, offer_scope: str = "state") -> tuple[bool, str]:
        """Make a bilateral buyout offer for an individual state or the entire sovereign empire (0% tax applied)."""
        if self._db is None:
            await self.setup()

        try:
            amount = max(0, int(amount))
        except (ValueError, TypeError):
            amount = 0

        offer_scope = "whole_country" if offer_scope in ("whole_country", "empire") else "state"

        if amount > 0:
            econ = await self.get_global_economy(buyer_id)
            if econ.get("medals", 0) < amount:
                return False, f"Insufficient funds: You only have {econ.get('medals', 0):,} Medals."

        async with self._db.execute("SELECT owner_id, name FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return False, "This country has no active ruler to receive offers. Purchase it directly from the State Trust!"
            seller_id = row[0]
            c_name = row[1]

        if str(seller_id) == str(buyer_id):
            return False, "You cannot make a buyout offer on your own country!"

        now = time.time()
        await self._db.execute("""
            INSERT INTO earth_country_offers (country_id, buyer_id, seller_id, offer_amount, status, created_at, offer_scope)
            VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """, (country_id, buyer_id, seller_id, amount, now, offer_scope))
        await self._db.commit()

        target_desc = f"the Entire Sovereign Empire of {c_name}" if offer_scope == "whole_country" else f"the State of {c_name}"
        return True, f"Diplomatic Buyout Offer of {amount:,} Medals submitted for {target_desc} (0% Treaty Tax applied)!"

    async def accept_country_offer(self, seller_id: int, offer_id: int) -> tuple[bool, str]:
        """Accept a buyout offer and transfer sovereign ownership (0% tax applied)."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT * FROM earth_country_offers WHERE id = ? AND status = 'pending'", (offer_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Offer not found or already processed."
            offer = dict(row)

        if str(offer["seller_id"]) != str(seller_id):
            return False, "You are not authorized to accept this offer."

        cid = offer["country_id"]
        bid = offer["buyer_id"]
        amt = max(0, int(offer["offer_amount"]))

        # Check buyer funds if amt > 0
        if amt > 0:
            b_econ = await self.get_global_economy(bid)
            if b_econ.get("medals", 0) < amt:
                await self._db.execute("UPDATE earth_country_offers SET status = 'cancelled' WHERE id = ?", (offer_id,))
                await self._db.commit()
                return False, "The buyer no longer possesses sufficient Medals for this buyout."

            # Deduct from buyer and credit seller - NO TAX APPLIED (0% tax!)
            await self.subtract_medals(bid, amt)
            await self.add_medals(seller_id, amt)

        # Transfer country ownership based on offer scope (state vs whole country/empire)
        scope = offer.get("offer_scope", "state")
        if scope in ("whole_country", "empire"):
            # Transfer entire sovereign empire (all countries governed by seller)
            await self._db.execute("UPDATE earth_countries SET owner_id = ?, for_sale_price = NULL WHERE owner_id = ?", (bid, seller_id))
            await self._db.execute("DELETE FROM earth_cabinet WHERE country_id IN (SELECT id FROM earth_countries WHERE owner_id = ?)", (bid,))
        else:
            # Transfer individual state
            await self._db.execute("UPDATE earth_countries SET owner_id = ?, for_sale_price = NULL WHERE id = ?", (bid, cid))
            await self._db.execute("DELETE FROM earth_cabinet WHERE country_id = ?", (cid,))

        # Resign buyer from any prior ministerial posts
        await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (bid,))
        await self._db.execute("UPDATE earth_country_offers SET status = 'accepted' WHERE id = ?", (offer_id,))
        await self._db.commit()

        return True, f"Deal finalized! Sovereignty transferred to <@{bid}>. You received +{amt:,} Medals (0% Treaty Tax applied ? full payout)."

    async def reject_country_offer(self, seller_id: int, offer_id: int) -> tuple[bool, str]:
        """Decline a sovereign buyout offer."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT * FROM earth_country_offers WHERE id = ? AND status = 'pending'", (offer_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Offer not found."
            offer = dict(row)

        if str(offer["seller_id"]) != str(seller_id):
            return False, "You are not authorized to reject this offer."

        await self._db.execute("UPDATE earth_country_offers SET status = 'rejected' WHERE id = ?", (offer_id,))
        await self._db.commit()
        return True, "Diplomatic Buyout Offer declined."

    async def get_country_offers(self, user_id: int) -> list[dict]:
        """Fetch all incoming and outgoing country buyout offers."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("""
            SELECT o.*, c.name as country_name, c.flag as country_flag,
                   COALESCE(omb.username, 'Commander ' || o.buyer_id) as buyer_name,
                   COALESCE(oms.username, 'Commander ' || o.seller_id) as seller_name
            FROM earth_country_offers o
            JOIN earth_countries c ON o.country_id = c.id
            LEFT JOIN oauth_members omb ON o.buyer_id = omb.user_id
            LEFT JOIN oauth_members oms ON o.seller_id = oms.user_id
            WHERE o.buyer_id = ? OR o.seller_id = ?
            ORDER BY o.created_at DESC
        """, (user_id, user_id)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ??? Citizenship & Allegiance ?????????????????????????????????????????????

    async def join_earth_country(self, user_id: int, country_id: int) -> tuple[bool, str]:
        """Pledge allegiance and join an existing sovereign nation as an official citizen."""
        if self._db is None:
            await self.setup()

        # Check if already President
        async with self._db.execute("SELECT id, name FROM earth_countries WHERE owner_id = ?", (user_id,)) as cur:
            r = await cur.fetchone()
            if r:
                return False, f"? You are the Supreme Sovereign of {r[1]}! You must abdicate or sell your country before pledging allegiance to another realm."

        # Fetch target country
        async with self._db.execute("SELECT id, name, flag, owner_id FROM earth_countries WHERE id = ?", (country_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Target sovereign country not found."
            c_name = row[1]
            c_flag = row[2]

        now = time.time()
        await self._db.execute("""
            INSERT OR REPLACE INTO earth_citizens (user_id, country_id, joined_at)
            VALUES (?, ?, ?)
        """, (user_id, country_id, now))
        # Remove from cabinet of any other country
        await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ? AND country_id != ?", (user_id, country_id))
        await self._db.commit()

        return True, f"??? Allegiance Pledged! You are now an official citizen of {c_flag} **{c_name}**. The President can appoint you as Prime Minister, Defense General, Diplomat, or Economy Director!"

    async def leave_earth_country(self, user_id: int) -> tuple[bool, str]:
        """Renounce citizenship and become a stateless leader/free agent."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("SELECT id, name FROM earth_countries WHERE owner_id = ?", (user_id,)) as cur:
            if await cur.fetchone():
                return False, "You are the Supreme Sovereign of this country! To leave, list it on the market, accept a buyout, or relinquish rule."

        await self._db.execute("DELETE FROM earth_citizens WHERE user_id = ?", (user_id,))
        await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (user_id,))
        await self._db.commit()
        return True, "You have renounced your allegiance and are now a stateless free agent. You can buy a new country or join another!"

    async def get_earth_country_citizens(self, country_id: int) -> list[dict]:
        """Fetch all registered citizens of a nation."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("""
            SELECT cz.user_id, cz.joined_at, cz.reputation,
                   COALESCE(m.username, 'Citizen ' || cz.user_id) as username,
                   cab.role as cabinet_role
            FROM earth_citizens cz
            LEFT JOIN oauth_members m ON cz.user_id = m.user_id
            LEFT JOIN earth_cabinet cab ON cz.user_id = cab.user_id AND cz.country_id = cab.country_id
            WHERE cz.country_id = ?
            ORDER BY cz.joined_at ASC
        """, (country_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    # ??? Counter-Intelligence & Spy Detention ?????????????????????????????????

    async def get_captured_foreign_spies(self, country_id: int) -> list[dict]:
        """Fetch foreign spies captured and held in military detention facilities."""
        if self._db is None:
            await self.setup()

        async with self._db.execute("""
            SELECT s.*, c.name as origin_country_name, c.flag as origin_country_flag
            FROM earth_spies s
            JOIN earth_countries c ON s.owner_country_id = c.id
            WHERE s.status = 'captured' AND s.target_country_id = ?
            ORDER BY s.created_at DESC
        """, (country_id,)) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def interrogate_captured_spy(self, user_id: int, country_id: int, spy_id: int) -> tuple[bool, str, dict]:
        """Interrogate a captured foreign agent to extract confessions and enemy intelligence."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "? Only the President or Director of Intelligence can interrogate foreign prisoners of war!", {}

        async with self._db.execute("""
            SELECT s.*, c.name as origin_country_name, c.flag as origin_country_flag, c.treasury as origin_treasury, c.gdp as origin_gdp
            FROM earth_spies s
            JOIN earth_countries c ON s.owner_country_id = c.id
            WHERE s.id = ? AND s.status = 'captured' AND s.target_country_id = ?
        """, (spy_id, country_id)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Captured agent not found in your detention facilities.", {}
            s = dict(row)

        intel = {
            "codename": s["codename"],
            "origin_country": s["origin_country_name"],
            "origin_flag": s["origin_country_flag"],
            "origin_treasury": s["origin_treasury"],
            "origin_gdp": s["origin_gdp"],
            "mission": s.get("mission", "covert_infiltration")
        }

        # Interrogation awards +5 national stability and full enemy dossier
        await self._db.execute("UPDATE earth_countries SET stability = min(100, stability + 5) WHERE id = ?", (country_id,))
        await self._db.commit()

        return True, f"??? Interrogation Successful! Agent '{s['codename']}' cracked under questioning! Confessed they were commissioned by {s['origin_country_flag']} **{s['origin_country_name']}**! National Stability +5%.", intel

    async def execute_captured_spy(self, user_id: int, country_id: int, spy_id: int) -> tuple[bool, str]:
        """Execute a convicted foreign spy for treasonous espionage."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "defense")
        if not can_manage:
            can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "? Only the Supreme Sovereign or Minister of Defense can sign execution warrants."

        async with self._db.execute("""
            SELECT s.codename, c.name FROM earth_spies s
            JOIN earth_countries c ON s.owner_country_id = c.id
            WHERE s.id = ? AND s.status = 'captured' AND s.target_country_id = ?
        """, (spy_id, country_id)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Detained spy not found."
            cname, origin_country = row[0], row[1]

        await self._db.execute("DELETE FROM earth_spies WHERE id = ?", (spy_id,))
        # Lowers civil unrest by -5%
        await self._db.execute("UPDATE earth_countries SET unrest = max(0, unrest - 5) WHERE id = ?", (country_id,))
        await self._db.commit()

        return True, f"?? Military Tribunal Concluded: Foreign Agent '{cname}' from {origin_country} has been executed! National Unrest decreased by 5%."

    async def counter_intel_sweep(self, user_id: int, country_id: int) -> tuple[bool, str, dict]:
        """Conduct a nationwide security sweep to detect and intercept hostile foreign operatives."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "? Only the President or Director of Intelligence can authorize security sweeps.", {}

        # Fetch bunkers level
        target_country = await self.get_earth_country(country_id)
        bunkers = sum(b.get("level", 1) for b in target_country.get("buildings", []) if b["building_type"] == "bunker")
        detained = await self.get_captured_foreign_spies(country_id)

        # Base detection chance
        detection_rating = 65 + (bunkers * 5)
        sweep_result = {
            "bunkers_count": bunkers,
            "counter_intel_rating": f"{min(98, detection_rating)}%",
            "detained_spies_count": len(detained),
            "detained_spies": detained
        }

        return True, f"??? Counter-Intelligence Sweep Complete! Defense grid operating at {sweep_result['counter_intel_rating']} efficiency with {bunkers} Bunker installations. {len(detained)} hostile agents currently held in military detention.", sweep_result

    # ??? Organic Slow Growth & Advanced Military Tools ??????????????????????????

    async def train_earth_spy(self, user_id: int, country_id: int, spy_id: int, target_level: int) -> tuple[bool, str, dict]:
        """Enroll an operative in the National Intelligence Academy to increase rank and mission effectiveness."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "⛔ Only the President or Director of Intelligence can authorize spy training.", {}

        COURSES = {
            2: {"title": "Field Infiltration Tradecraft", "cost": 20000, "rank": "Field Operative"},
            3: {"title": "Sabotage & Demolition Specialization", "cost": 45000, "rank": "Sabotage Specialist"},
            4: {"title": "Cyber Warfare & Cipher Infiltration", "cost": 80000, "rank": "Cyber Infiltrator"},
            5: {"title": "Master Phantom Ghost Infiltration", "cost": 130000, "rank": "Phantom Ghost"}
        }

        if target_level not in COURSES:
            return False, f"Invalid training course level: {target_level}. Must be 2-5.", {}

        course = COURSES[target_level]

        # Verify spy exists and is idle
        async with self._db.execute("SELECT id, codename, skill_level, status FROM earth_spies WHERE id = ? AND owner_country_id = ?", (spy_id, country_id)) as cur:
            row = await cur.fetchone()
            if not row:
                return False, "Operative not found in your intelligence bureau.", {}
            s_id, codename, current_level, status = row[0], row[1], row[2], row[3]

        if status != "idle":
            return False, f"Agent '{codename}' is currently {status.upper()} and cannot undergo academy training until idle.", {}

        if current_level >= target_level:
            return False, f"Agent '{codename}' has already completed this training level (Current Level: {current_level}).", {}

        if current_level < target_level - 1:
            return False, f"Agent '{codename}' must complete Level {target_level - 1} before qualifying for Level {target_level}.", {}

        cost = course["cost"]
        econ = await self.get_global_economy(user_id)
        user_medals = econ.get("medals", 0)

        country = await self.get_earth_country(country_id)
        treasury = country.get("treasury", 0)

        if user_medals >= cost:
            await self.add_medals(user_id, -cost)
        elif treasury >= cost:
            await self._db.execute("UPDATE earth_countries SET treasury = treasury - ? WHERE id = ?", (cost, country_id))
        else:
            return False, f"Insufficient funds for Academy training. Course cost: {cost:,} Medals (Wallet: {user_medals:,} M, Treasury: {treasury:,} M).", {}

        # Upgrade spy
        await self._db.execute("UPDATE earth_spies SET skill_level = ? WHERE id = ?", (target_level, spy_id))
        await self._db.commit()

        return True, f"🎓 Training Complete! Agent '{codename}' graduated from {course['title']} and is now a **{course['rank']}** (Skill Level {target_level}/5)!", {
            "spy_id": spy_id,
            "codename": codename,
            "new_level": target_level,
            "rank_title": course["rank"]
        }

    async def buy_earth_intel_dossier(self, user_id: int, country_id: int, target_country_id: int, intel_type: str) -> tuple[bool, str, dict]:
        """Procure classified intelligence dossiers on a foreign nation from intelligence brokers."""
        if self._db is None:
            await self.setup()

        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "⛔ Only the President or Director of Intelligence can purchase intelligence dossiers.", {}

        INTEL_PACKAGES = {
            "covert_history": {"title": "Covert Operations & Sabotage History", "cost": 35000},
            "military_readiness": {"title": "Military Arsenal & Tool Readiness", "cost": 50000},
            "economic_vault": {"title": "Treasury Reserves & Yield Audit", "cost": 25000}
        }

        if intel_type not in INTEL_PACKAGES:
            return False, f"Invalid intelligence package: {intel_type}.", {}

        pkg = INTEL_PACKAGES[intel_type]
        cost = pkg["cost"]

        econ = await self.get_global_economy(user_id)
        user_medals = econ.get("medals", 0)
        country = await self.get_earth_country(country_id)
        treasury = country.get("treasury", 0)

        if user_medals >= cost:
            await self.add_medals(user_id, -cost)
        elif treasury >= cost:
            await self._db.execute("UPDATE earth_countries SET treasury = treasury - ? WHERE id = ?", (cost, country_id))
        else:
            return False, f"Insufficient funds for Intelligence Briefing. Cost: {cost:,} Medals (Wallet: {user_medals:,} M, Treasury: {treasury:,} M).", {}

        target_country = await self.get_earth_country(target_country_id)
        if not target_country:
            return False, "Target nation not found.", {}

        now = time.time()
        dossier_data = {}

        if intel_type == "covert_history":
            async with self._db.execute("""
                SELECT s.codename, c.name as sponsor_nation, s.status, s.mission, s.created_at
                FROM earth_spies s
                JOIN earth_countries c ON s.owner_country_id = c.id
                WHERE s.target_country_id = ?
                ORDER BY s.created_at DESC LIMIT 5
            """, (target_country_id,)) as cur:
                recent_incursions = [dict(r) for r in await cur.fetchall()]

            dossier_data = {
                "category": "Covert Operations Audit",
                "target_name": target_country["name"],
                "target_flag": target_country["flag"],
                "foreign_incursions": recent_incursions,
                "unrest": target_country.get("unrest", 0),
                "is_rioting": bool(target_country.get("is_rioting", 0)),
                "summary": f"Decrypted {len(recent_incursions)} foreign spy operations targeting {target_country['name']}."
            }

        elif intel_type == "military_readiness":
            tools = await self.get_country_tools(target_country_id)
            dossier_data = {
                "category": "Military & Arsenal Blueprint",
                "target_name": target_country["name"],
                "target_flag": target_country["flag"],
                "active_wars": target_country.get("active_war_count", 0),
                "installed_arsenal": [t.get("name", t.get("tool_key", "Tool")) for t in tools],
                "bunker_defense": sum(b["level"] for b in target_country.get("buildings", []) if b["building_type"] == "bunker"),
                "summary": f"Verified {len(tools)} advanced military systems and {target_country.get('active_war_count', 0)} active combat theaters."
            }

        elif intel_type == "economic_vault":
            dossier_data = {
                "category": "Treasury & Economic Audit",
                "target_name": target_country["name"],
                "target_flag": target_country["flag"],
                "treasury": target_country.get("treasury", 0),
                "gdp": target_country.get("gdp", 0),
                "tax_rate": f"{target_country.get('tax_rate', 10)}%",
                "gold_mines": sum(b["level"] for b in target_country.get("buildings", []) if b["building_type"] == "gold_mine"),
                "oil_rigs": sum(b["level"] for b in target_country.get("buildings", []) if b["building_type"] == "oil_rig"),
                "summary": f"Confirmed treasury vault balance of {target_country.get('treasury', 0):,} Medals and GDP of {target_country.get('gdp', 0):,} Medals."
            }

        import json
        await self._db.execute("""
            INSERT INTO earth_intelligence (gatherer_country_id, target_country_id, intel_type, intel_data, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (country_id, target_country_id, intel_type, json.dumps(dossier_data), now + 86400 * 7, now))
        await self._db.commit()

        return True, f"📑 Intelligence Purchased! Decrypted {pkg['title']} on {target_country['flag']} **{target_country['name']}**!", dossier_data

    async def apply_organic_growth(self, country: dict) -> dict:
        """Process slow, natural growth of national GDP, stability, and treasury over time."""
        now = time.time()
        last_tick = country.get("last_growth_tick") or country.get("created_at") or now
        if last_tick == 0:
            last_tick = now - 3600
        
        elapsed_hours = (now - last_tick) / 3600.0
        # Only tick if at least 15 minutes (0.25 hrs) have elapsed
        if elapsed_hours >= 0.25:
            capped_hours = min(48.0, elapsed_hours)
            stab_factor = max(0.4, (country.get("stability", 80)) / 100.0)
            
            # Organic GDP growth: ~0.3% compound per hour of peace
            gdp_growth = int(country["gdp"] * 0.0001 * capped_hours * stab_factor)
            # Organic civic treasury yield: based on tax rate & stability
            tax_rate = country.get("tax_rate", 10)
            treasury_gain = int(tax_rate * 250 * capped_hours * stab_factor)
            # Unrest cooling: -1 unrest per 3 hours of peace
            unrest_cool = min(10, int(capped_hours * 0.33))
            
            new_gdp = country["gdp"] + gdp_growth
            new_treasury = country["treasury"] + treasury_gain
            new_unrest = max(0, country.get("unrest", 10) - unrest_cool)
            
            await self._db.execute("""
                UPDATE earth_countries
                SET gdp = ?, treasury = ?, unrest = ?, last_growth_tick = ?
                WHERE id = ?
            """, (new_gdp, new_treasury, new_unrest, now, country["id"]))
            await self._db.commit()
            
            country["gdp"] = new_gdp
            country["treasury"] = new_treasury
            country["unrest"] = new_unrest
            country["last_growth_tick"] = now
            country["recent_gdp_growth"] = gdp_growth
        return country

    async def get_country_tools(self, country_id: int) -> list[dict]:
        """Fetch all advanced military, defense, and economic tools owned by a country."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_ADVANCED_TOOLS

        async with self._db.execute("""
            SELECT * FROM earth_tools WHERE country_id = ? ORDER BY purchased_at ASC
        """, (country_id,)) as cur:
            rows = await cur.fetchall()

        tools = []
        for r in rows:
            d = dict(r)
            meta = EARTH_ADVANCED_TOOLS.get(d["tool_key"], {})
            tools.append({
                **d,
                "name": meta.get("name", d["tool_key"]),
                "emoji": meta.get("emoji", "??"),
                "desc": meta.get("desc", ""),
                "category": meta.get("category", "military"),
                "military_power": meta.get("military_power", 0),
                "defense_power": meta.get("defense_power", 0),
                "hourly_yield": meta.get("hourly_yield", 0),
                "perk": meta.get("perk", "")
            })
        return tools

    async def buy_country_tool(self, user_id: int, country_id: int, tool_key: str) -> tuple[bool, str, dict]:
        """Purchase advanced high-tech military tools, missile shields, or drone swarms for Medals."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_ADVANCED_TOOLS

        if tool_key not in EARTH_ADVANCED_TOOLS:
            return False, "Invalid advanced tool selected.", {}

        # Authorization check: president or defense minister
        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "defense")
        if not can_manage:
            can_manage = await self.has_earth_cabinet_permission(user_id, country_id, "intelligence")
        if not can_manage:
            return False, "? Authorization Denied: Only the Supreme Sovereign or Minister of Defense can procure advanced military assets!", {}

        meta = EARTH_ADVANCED_TOOLS[tool_key]
        price = meta["price"]

        # Check existing tool
        async with self._db.execute("""
            SELECT level FROM earth_tools WHERE country_id = ? AND tool_key = ?
        """, (country_id, tool_key)) as cur:
            row = await cur.fetchone()
            if row:
                return False, f"Your forces already deployed the {meta['emoji']} **{meta['name']}**!", {}

        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < price:
            return False, f"Insufficient Medals: Procuring {meta['name']} requires {price:,} Medals (You have {econ.get('medals', 0):,}).", {}

        # Deduct medals
        await self.subtract_medals(user_id, price)
        now = time.time()

        await self._db.execute("""
            INSERT INTO earth_tools (country_id, tool_key, level, purchased_at)
            VALUES (?, ?, 1, ?)
        """, (country_id, tool_key, now))
        
        # If economic core, immediately boost GDP
        if tool_key == "industrial_core":
            await self._db.execute("""
                UPDATE earth_countries SET gdp = gdp + 15000000 WHERE id = ?
            """, (country_id,))
        
        await self._db.commit()

        updated_country = await self.get_earth_country(country_id)
        return True, f"?? Advanced Asset Procured! Deployed {meta['emoji']} **{meta['name']}** to your national forces! (+{meta['military_power']} Atk, +{meta['defense_power']} Def).", {
            "tool": meta,
            "wallet": econ.get("medals", 0) - price,
            "country": updated_country
        }
