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



            CREATE TABLE IF NOT EXISTS medal_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                old_medals INTEGER NOT NULL,
                new_medals INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TRIGGER IF NOT EXISTS prevent_negative_global_medals
            BEFORE UPDATE OF medals ON global_economy
            WHEN NEW.medals < 0
            BEGIN
                SELECT RAISE(ABORT, 'wallet balance cannot be negative');
            END;

            CREATE TRIGGER IF NOT EXISTS audit_global_medal_changes
            AFTER UPDATE OF medals ON global_economy
            WHEN OLD.medals != NEW.medals
            BEGIN
                INSERT INTO medal_audit(user_id, old_medals, new_medals, delta, created_at)
                VALUES (OLD.user_id, OLD.medals, NEW.medals, NEW.medals - OLD.medals, strftime('%s','now'));
            END;

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
                government_type TEXT DEFAULT 'democracy',
                last_policy_review REAL DEFAULT 0,
                population INTEGER NOT NULL DEFAULT 100,
                army_divisions INTEGER NOT NULL DEFAULT 10,
                tanks INTEGER NOT NULL DEFAULT 1,
                jets INTEGER NOT NULL DEFAULT 1,
                ships INTEGER NOT NULL DEFAULT 1,
                population_last_growth REAL DEFAULT 0,
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

            CREATE TABLE IF NOT EXISTS earth_claim_fingerprints (
                fingerprint TEXT PRIMARY KEY,
                first_user_id INTEGER NOT NULL,
                claimed_at REAL NOT NULL
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

            CREATE TABLE IF NOT EXISTS earth_military_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, country_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
                action TEXT NOT NULL, unit_type TEXT NOT NULL, amount INTEGER NOT NULL, created_at REAL NOT NULL,
                FOREIGN KEY(country_id) REFERENCES earth_countries(id)
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


            CREATE TABLE IF NOT EXISTS earth_alliance_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alliance_id INTEGER NOT NULL,
                country_id INTEGER NOT NULL,
                requester_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                UNIQUE(alliance_id, country_id, status)
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
                war_domain TEXT NOT NULL DEFAULT 'land',
                attacker_tanks INTEGER NOT NULL DEFAULT 0,
                defender_tanks INTEGER NOT NULL DEFAULT 0,
                attacker_jets INTEGER NOT NULL DEFAULT 0,
                defender_jets INTEGER NOT NULL DEFAULT 0,
                attacker_ships INTEGER NOT NULL DEFAULT 0,
                defender_ships INTEGER NOT NULL DEFAULT 0,
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

        # Remove legacy property data tables during migration.
        for table in ("estate_offers", "estate_raids", "estate_alliances", "estate_plots"):
            await self._db.execute(f"DROP TABLE IF EXISTS {table}")

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS player_companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL UNIQUE,
                name TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL UNIQUE,
                sector TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                claimed_valuation INTEGER NOT NULL,
                annual_revenue INTEGER NOT NULL DEFAULT 0,
                annual_profit INTEGER NOT NULL DEFAULT 0,
                debt INTEGER NOT NULL DEFAULT 0,
                fair_value INTEGER NOT NULL,
                treasury INTEGER NOT NULL DEFAULT 0,
                aid_received INTEGER NOT NULL DEFAULT 0,
                ai_status TEXT NOT NULL,
                ai_report TEXT NOT NULL,
                stock_id INTEGER NOT NULL UNIQUE,
                created_at REAL NOT NULL,
                FOREIGN KEY(stock_id) REFERENCES stocks(id)
            );
            CREATE TABLE IF NOT EXISTS player_company_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                seller_id INTEGER NOT NULL,
                buyer_id INTEGER NOT NULL,
                gross_price INTEGER NOT NULL CHECK(gross_price > 0),
                status TEXT NOT NULL DEFAULT 'pending',
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                FOREIGN KEY(company_id) REFERENCES player_companies(id)
            );
            CREATE INDEX IF NOT EXISTS idx_company_offers_buyer_status
                ON player_company_offers(buyer_id, status, expires_at);
            CREATE TABLE IF NOT EXISTS earth_nuclear_strikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                war_id INTEGER NOT NULL,
                source_country_id INTEGER NOT NULL,
                target_country_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                gdp_damage INTEGER NOT NULL DEFAULT 0,
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

            "ALTER TABLE earth_countries ADD COLUMN last_growth_tick REAL DEFAULT 0",
            "ALTER TABLE earth_cabinet ADD COLUMN username TEXT DEFAULT NULL",
            "ALTER TABLE earth_cabinet_invites ADD COLUMN username TEXT DEFAULT NULL",
            "ALTER TABLE earth_countries ADD COLUMN is_sanctioned INTEGER DEFAULT 0",
            "ALTER TABLE earth_countries ADD COLUMN sanction_reason TEXT DEFAULT NULL",
            "ALTER TABLE earth_countries ADD COLUMN sanction_expires REAL DEFAULT 0",
            "ALTER TABLE earth_countries ADD COLUMN government_type TEXT DEFAULT 'democracy'",
            "ALTER TABLE earth_countries ADD COLUMN last_policy_review REAL DEFAULT 0",
            "ALTER TABLE earth_countries ADD COLUMN population INTEGER NOT NULL DEFAULT 100",
            "ALTER TABLE earth_countries ADD COLUMN army_divisions INTEGER NOT NULL DEFAULT 10",
            "ALTER TABLE earth_countries ADD COLUMN tanks INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE earth_countries ADD COLUMN jets INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE earth_countries ADD COLUMN ships INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE earth_countries ADD COLUMN population_last_growth REAL DEFAULT 0",
            "ALTER TABLE player_companies ADD COLUMN treasury INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE player_companies ADD COLUMN aid_received INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE earth_country_offers ADD COLUMN offer_scope TEXT DEFAULT 'state'",
            "ALTER TABLE earth_wars ADD COLUMN war_domain TEXT NOT NULL DEFAULT 'land'",
            "ALTER TABLE earth_wars ADD COLUMN attacker_tanks INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE earth_wars ADD COLUMN defender_tanks INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE earth_wars ADD COLUMN attacker_jets INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE earth_wars ADD COLUMN defender_jets INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE earth_wars ADD COLUMN attacker_ships INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE earth_wars ADD COLUMN defender_ships INTEGER NOT NULL DEFAULT 0",
            "PRAGMA journal_mode=WAL"

        ]:

            try:

                await self._db.execute(query)

            except aiosqlite.OperationalError:

                pass  # Column already exists



        # Repair legacy snapshots created before wallet deductions were guarded.
        # A negative canonical balance must never prevent the service from booting.
        await self._db.execute("UPDATE global_economy SET medals = 0 WHERE medals < 0")
        await self._db.execute("UPDATE users SET medals = 0 WHERE medals < 0")

        # Migrate existing users economy data into global_economy — always take the higher value

        await self._db.execute("""

            INSERT INTO global_economy (user_id, medals, last_daily, last_work, last_weekly, last_crime, last_scavenge, last_trivia, active_banner)

            SELECT user_id, MAX(medals), MAX(last_daily), MAX(last_work), MAX(last_weekly), MAX(last_crime), MAX(last_scavenge), MAX(last_trivia), active_banner

            FROM users

            GROUP BY user_id

            ON CONFLICT(user_id) DO UPDATE SET

                medals = MAX(0, global_economy.medals, excluded.medals),

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
        await self.seed_default_earth_countries()
        await self.reset_earth_world_to_zero_once()
        await self.release_user_earth_claims_once(1147451922459136070, "IRN")




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

        # Calculate UN peacekeeping fund from active country trade tariffs.
        un_fund = 0
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
            async with self._db.execute("SELECT id, action AS resolution_type, target_country_id, war_id, sponsor_id AS mayor_id, details, created_at FROM earth_un_resolutions ORDER BY id DESC LIMIT 10") as cur:
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
        """UN Secretary-General (Mayor) ends an active war with a ceasefire."""
        if self._db is None:
            await self.setup()
        async with self._db.execute(
            "SELECT attacker_country_id, defender_country_id, attacker_divisions, defender_divisions FROM earth_wars WHERE id = ? AND status = 'active'",
            (war_id,),
        ) as cur:
            war = await cur.fetchone()
        if not war:
            return False, "Active war record not found."
        now = time.time()
        details = f"UN ceasefire enforced on War #{war_id} between Country #{war[0]} and #{war[1]}."
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT id FROM earth_wars WHERE id = ? AND status = 'active'", (war_id,)
            ) as cur:
                if not await cur.fetchone():
                    await self._db.rollback()
                    return False, "This war has already concluded."
            await self._db.execute("UPDATE earth_wars SET status = 'ceasefire' WHERE id = ?", (war_id,))
            for country_id, divisions in ((war[0], war[2]), (war[1], war[3])):
                await self._db.execute(
                    "UPDATE earth_countries SET army_divisions=MIN(MAX(0,population/5),army_divisions+?) WHERE id=?",
                    (max(0, int(divisions or 0)), country_id),
                )
            await self._db.execute(
                "INSERT INTO earth_un_resolutions (action, war_id, sponsor_id, details, created_at) VALUES ('CEASEFIRE', ?, ?, ?, ?)",
                (war_id, mayor_id, details, now),
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise
        return True, f"UN ceasefire enforced on War #{war_id}; deployed forces are released."

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
            INSERT INTO earth_un_resolutions (action, target_country_id, sponsor_id, details, created_at)
            VALUES ('SANCTION', ?, ?, ?, ?)
        """, (country_id, mayor_id, details, now))

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
            INSERT INTO earth_un_resolutions (action, target_country_id, sponsor_id, details, created_at)
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
            INSERT INTO earth_un_resolutions (action, target_country_id, sponsor_id, details, created_at)
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
                # global_economy is the canonical wallet, but older bot paths may have
                # written only the users mirror. Reconcile to the highest persisted value
                # so a 5-second web refresh can never make Medals disappear.
                current_medals = int(row["medals"] or 0)
                async with self._db.execute(
                    "SELECT MAX(medals) FROM users WHERE user_id = ?", (user_id,)
                ) as mirror_cur:
                    mirror_row = await mirror_cur.fetchone()
                mirror_medals = int(mirror_row[0] or 0) if mirror_row else 0
                canonical_medals = max(0, current_medals, mirror_medals)
                if current_medals != canonical_medals or mirror_medals != canonical_medals:
                    await self._db.execute(
                        "UPDATE global_economy SET medals = ? WHERE user_id = ?",
                        (canonical_medals, user_id)
                    )
                    await self._db.execute(
                        "UPDATE users SET medals = ? WHERE user_id = ?",
                        (canonical_medals, user_id)
                    )
                    await self._db.commit()
                result = dict(row)
                result["medals"] = canonical_medals
                return result

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

        

        # Loan repayment is explicit via /bank repay or /loan repay. Rewards and
        # transfers must never disappear silently when a debt is overdue.

        if amount != 0:
            # Guard deductions at the database boundary. A stale command
            # response or two simultaneous spends must fail cleanly instead
            # of tripping the negative-wallet trigger and crashing the bot.
            if amount < 0:
                debit = -amount
                cur = await self._db.execute(
                    "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                    (debit, user_id, debit)
                )
                if cur.rowcount != 1:
                    await self._db.rollback()
                    return False
            else:
                await self._db.execute(
                    "UPDATE global_economy SET medals = medals + ? WHERE user_id = ?",
                    (amount, user_id)
                )

            await self._db.execute(
                "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?",
                (user_id, user_id)
            )

        await self._db.commit()
        return True



    async def transfer_medals(self, sender_id: int, recipient_id: int, amount: int, tax_rate: float = 0.30) -> tuple[bool, int]:
        """Atomically transfer wallet medals and return the recipient amount."""
        amount = int(amount)
        if amount <= 0 or sender_id == recipient_id:
            return False, 0
        tax = max(0, min(amount, int(amount * float(tax_rate))))
        recipient_amount = amount - tax
        await self.get_global_economy(sender_id)
        await self.get_global_economy(recipient_id)
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            debit = await self._db.execute(
                "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                (amount, sender_id, amount)
            )
            if debit.rowcount != 1:
                await self._db.rollback()
                return False, 0
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (sender_id, sender_id))
            credit = await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (recipient_amount, recipient_id))
            if credit.rowcount != 1:
                await self._db.rollback()
                return False, 0
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (recipient_id, recipient_id))
            await self._db.commit()
            return True, recipient_amount
        except Exception:
            await self._db.rollback()
            raise

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
        if guild_id is None:
            query = "SELECT * FROM banks WHERE user_id = ? ORDER BY balance DESC, tier DESC LIMIT 1"
            params = (user_id,)
        else:
            query = "SELECT * FROM banks WHERE user_id = ? AND guild_id = ? LIMIT 1"
            params = (user_id, guild_id)
        async with self._db.execute(query, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


    async def deposit_bank(self, user_id: int, guild_id: int, amount: int) -> bool:
        """Atomically move medals from the canonical wallet into the bank."""
        amount = int(amount)
        if amount <= 0:
            return False
        await self.get_global_economy(user_id)
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            cur = await self._db.execute(
                "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                (amount, user_id, amount)
            )
            if cur.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.execute(
                "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?",
                (user_id, user_id)
            )
            bank_cur = await self._db.execute(
                "UPDATE banks SET balance = balance + ? WHERE user_id = ? AND guild_id = ?",
                (amount, user_id, guild_id)
            )
            if bank_cur.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.commit()
            return True
        except Exception:
            await self._db.rollback()
            raise

    async def withdraw_bank(self, user_id: int, guild_id: int, amount: int) -> bool:
        """Atomically move medals from the bank into the canonical wallet."""
        amount = int(amount)
        if amount <= 0:
            return False
        await self.get_global_economy(user_id)
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            cur = await self._db.execute(
                "UPDATE banks SET balance = balance - ? WHERE user_id = ? AND guild_id = ? AND balance >= ?",
                (amount, user_id, guild_id, amount)
            )
            if cur.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (amount, user_id))
            await self._db.execute(
                "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?",
                (user_id, user_id)
            )
            await self._db.commit()
            return True
        except Exception:
            await self._db.rollback()
            raise

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



    async def settle_bank_loan(self, user_id: int, loan_id: int, amount: int) -> bool:
        """Atomically debit the borrower and advance a bank loan repayment."""
        await self.get_global_economy(user_id)
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("SELECT total_owed, repaid FROM bank_loans WHERE id = ? AND user_id = ?", (loan_id, user_id)) as cur:
                row = await cur.fetchone()
            if not row:
                await self._db.rollback()
                return False
            owed = max(0, int(row[0] or 0) - int(row[1] or 0))
            pay = min(int(amount), owed)
            if pay <= 0:
                await self._db.rollback()
                return False
            debit = await self._db.execute(
                "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                (pay, user_id, pay)
            )
            if debit.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (user_id, user_id))
            updated = await self._db.execute(
                "UPDATE bank_loans SET repaid = repaid + ? WHERE id = ? AND user_id = ? AND repaid = ?",
                (pay, loan_id, user_id, int(row[1] or 0))
            )
            if updated.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.commit()
            return True
        except Exception:
            await self._db.rollback()
            raise

    async def settle_player_loan(self, borrower_id: int, loan_id: int) -> bool:
        """Atomically debit borrower, credit lender, and close a player loan once."""
        await self.get_global_economy(borrower_id)
        async with self._db.execute("SELECT 1 FROM global_economy WHERE user_id = ? AND medals >= 0", (borrower_id,)) as cur:
            if not await cur.fetchone():
                await self._db.rollback()
                return False
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT lender_id, total_owed FROM player_loans WHERE id = ? AND borrower_id = ? AND status = 'active'",
                (loan_id, borrower_id)
            ) as cur:
                row = await cur.fetchone()
            if not row:
                await self._db.rollback()
                return False
            lender_id, owed = int(row[0]), int(row[1] or 0)
            debit = await self._db.execute(
                "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                (owed, borrower_id, owed)
            )
            if debit.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (borrower_id, borrower_id))
            credit = await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (owed, lender_id))
            if credit.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (lender_id, lender_id))
            updated = await self._db.execute(
                "UPDATE player_loans SET status = 'repaid' WHERE id = ? AND borrower_id = ? AND status = 'active'",
                (loan_id, borrower_id)
            )
            if updated.rowcount != 1:
                await self._db.rollback()
                return False
            await self._db.commit()
            return True
        except Exception:
            await self._db.rollback()
            raise

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

            price = max(2_000, min(80_000, int(price)))

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

                            hist_price = max(2_000, min(80_000, price + variation))

                            await self._db.execute(

                                "INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)",

                                (sid, hist_price, now - (i * 60))

                            )

        await self._db.commit()



    async def sanitize_stock_exploit(self):
        """Safety check to ensure stock prices never exceed the maximum ceiling."""
        try:
            # Keep every listing inside a predictable, affordable trading band.
            # This prevents compounding buy pressure from making one company
            # dominate the entire Medal economy.
            async with self._db.execute("SELECT count(*) FROM stocks WHERE price > 80000 OR price < 2000") as cur:
                has_runaway_stocks = (await cur.fetchone())[0] > 0

            if not has_runaway_stocks:
                return

            print("[Safety] Clamping runaway stock prices to ceiling...", flush=True)
            stock_ceilings = {
                "PRC": 80000, "TSC": 80000, "VNG": 80000,
                "AERO": 80000, "CRYP": 80000, "TSLA": 80000, "PANDA": 80000
            }
            for sym, ceiling in stock_ceilings.items():
                await self._db.execute(
                    "UPDATE stocks SET price = min(80000, max(2000, price)) WHERE symbol = ?",
                    (sym,)
                )

            await self._db.execute("UPDATE stocks SET price = min(80000, max(2000, price))")
            await self._db.execute("DELETE FROM stock_history WHERE price > 80000 OR price < 2000")
            await self._db.commit()
        except Exception as e:
            print(f"[Sanitizer Notice] {e}", flush=True)


    async def get_all_stocks(self) -> list[dict]:
        async with self._db.execute("""
            SELECT s.*, pc.owner_id AS company_owner_id, pc.sector AS company_sector,
                   pc.claimed_valuation, pc.annual_revenue, pc.annual_profit, pc.debt,
                   pc.fair_value, pc.treasury AS company_treasury, pc.aid_received, pc.ai_status, pc.ai_report
            FROM stocks s LEFT JOIN player_companies pc ON pc.stock_id = s.id
            ORDER BY s.id ASC
        """) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def get_stock(self, stock_id_or_symbol) -> dict | None:
        if isinstance(stock_id_or_symbol, int) or (isinstance(stock_id_or_symbol, str) and str(stock_id_or_symbol).isdigit()):
            predicate, param = "s.id = ?", int(stock_id_or_symbol)
        else:
            predicate, param = "UPPER(s.symbol) = UPPER(?)", str(stock_id_or_symbol)
        async with self._db.execute(f"""
            SELECT s.*, pc.owner_id AS company_owner_id, pc.sector AS company_sector,
                   pc.claimed_valuation, pc.annual_revenue, pc.annual_profit, pc.debt,
                   pc.fair_value, pc.treasury AS company_treasury, pc.aid_received, pc.ai_status, pc.ai_report
            FROM stocks s LEFT JOIN player_companies pc ON pc.stock_id = s.id
            WHERE {predicate}
        """, (param,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def create_stock(self, symbol: str, name: str, price: int, description: str = "", supply: int = 2500) -> bool:

        symbol = symbol.strip().upper()
        price = max(2_000, min(80_000, int(price)))

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

    async def create_company_sale_offer(self, seller_id: int, buyer_username: str, gross_price: int) -> tuple[bool, str, dict | None]:
        """Create a direct purchase offer. Buyer must accept before any balance or ownership changes."""
        if self._db is None:
            await self.setup()
        seller_id = int(seller_id)
        buyer_username = " ".join(str(buyer_username).strip().split())[:80]
        try:
            gross_price = int(gross_price)
        except (TypeError, ValueError):
            return False, "Enter a whole Medal amount.", None
        if seller_id <= 0 or not buyer_username or not 1 <= gross_price <= 2_000_000_000:
            return False, "Enter a valid buyer and sale price (1–2,000,000,000 Medals).", None

        async with self._db.execute(
            "SELECT user_id, username FROM oauth_members WHERE LOWER(username) = LOWER(?) LIMIT 1",
            (buyer_username,)
        ) as cur:
            buyer = await cur.fetchone()
        if not buyer:
            return False, "That player has not signed into the web app yet.", None
        buyer_id = int(buyer["user_id"])
        if buyer_id == seller_id:
            return False, "You cannot sell the company to yourself.", None
        async with self._db.execute("""SELECT pc.id, pc.name, pc.symbol, pc.fair_value, s.price, s.total_supply
            FROM player_companies pc JOIN stocks s ON s.id = pc.stock_id WHERE pc.owner_id = ?""", (seller_id,)) as cur:
            company = await cur.fetchone()
        if not company:
            return False, "You do not own a listed company.", None
        reviewed_value = int(company["fair_value"] or 0)
        market_value = int(company["price"] or 0) * int(company["total_supply"] or 0)
        max_player_price = max(25_000, min(reviewed_value or 25_000, market_value or reviewed_value or 25_000))
        if gross_price > max_player_price:
            return False, f"Player sale price is capped at {max_player_price:,} Medals by the reviewed valuation and current market cap.", None

        now = time.time()
        await self.get_global_economy(seller_id)
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT 1 FROM player_companies WHERE id = ? AND owner_id = ?",
                (company["id"], seller_id)
            ) as cur:
                if not await cur.fetchone():
                    await self._db.rollback()
                    return False, "You no longer own this company.", None
            async with self._db.execute(
                "SELECT 1 FROM player_company_offers WHERE company_id = ? AND buyer_id = ? AND status = 'pending' AND expires_at > ?",
                (company["id"], buyer_id, now)
            ) as cur:
                if await cur.fetchone():
                    await self._db.rollback()
                    return False, "You already have a pending offer with that player.", None
            await self._db.execute("""
                INSERT INTO player_company_offers
                    (company_id, seller_id, buyer_id, gross_price, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (company["id"], seller_id, buyer_id, gross_price, now, now + 7 * 24 * 60 * 60))
            await self._db.commit()
            return True, f"Purchase offer sent to {buyer['username']}. They must accept it; the price includes tax.", {
                "company_id": int(company["id"]), "company_name": company["name"],
                "symbol": company["symbol"], "buyer_username": buyer["username"],
                "gross_price": gross_price, "expires_at": now + 7 * 24 * 60 * 60
            }
        except Exception:
            await self._db.rollback()
            raise

    async def get_company_sale_offers(self, buyer_id: int) -> list[dict]:
        if self._db is None:
            await self.setup()
        now = time.time()
        async with self._db.execute("""
            SELECT o.id, o.company_id, o.seller_id, o.buyer_id, o.gross_price, o.created_at, o.expires_at,
                   pc.name AS company_name, pc.symbol, om.username AS seller_username
            FROM player_company_offers o
            JOIN player_companies pc ON pc.id = o.company_id
            LEFT JOIN oauth_members om ON om.user_id = o.seller_id
            WHERE o.buyer_id = ? AND o.status = 'pending' AND o.expires_at > ?
              AND pc.owner_id = o.seller_id
            ORDER BY o.created_at DESC
        """, (int(buyer_id), now)) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def accept_company_sale_offer(self, buyer_id: int, offer_id: int) -> tuple[bool, str]:
        if self._db is None:
            await self.setup()
        buyer_id, offer_id = int(buyer_id), int(offer_id)
        await self.get_global_economy(buyer_id)
        async with self._db.execute(
            "SELECT seller_id FROM player_company_offers WHERE id = ? AND buyer_id = ? AND status = 'pending'",
            (offer_id, buyer_id)
        ) as cur:
            seller_row = await cur.fetchone()
        if seller_row:
            await self.get_global_economy(int(seller_row["seller_id"]))
        now = time.time()
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("""
                SELECT o.*, pc.owner_id AS current_owner, pc.name AS company_name
                FROM player_company_offers o JOIN player_companies pc ON pc.id = o.company_id
                WHERE o.id = ? AND o.buyer_id = ? AND o.status = 'pending'
            """, (offer_id, buyer_id)) as cur:
                offer = await cur.fetchone()
            if not offer or offer["expires_at"] <= now or offer["current_owner"] != offer["seller_id"]:
                await self._db.rollback()
                return False, "This company offer expired or is no longer valid."
            async with self._db.execute(
                "SELECT 1 FROM player_companies WHERE owner_id = ?",
                (buyer_id,)
            ) as cur:
                if await cur.fetchone():
                    await self._db.rollback()
                    return False, "You must sell your existing company before buying another."
            async with self._db.execute("SELECT medals FROM global_economy WHERE user_id = ?", (buyer_id,)) as cur:
                buyer_wallet = await cur.fetchone()
            gross = int(offer["gross_price"])
            if not buyer_wallet or int(buyer_wallet[0] or 0) < gross:
                await self._db.rollback()
                return False, f"Not enough wallet Medals. The purchase costs {gross:,} including tax."
            tax_rate = await self.get_stock_tax_rate()
            tax = min(gross, int(round(gross * tax_rate)))
            net = gross - tax
            debit = await self._db.execute("UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?", (gross, buyer_id, gross))
            if debit.rowcount != 1:
                await self._db.rollback()
                return False, "Buyer wallet changed before the company purchase completed."
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (buyer_id, buyer_id))
            await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (net, offer["seller_id"]))
            await self._db.execute("UPDATE users SET medals = medals + ? WHERE user_id = ?", (net, offer["seller_id"]))
            await self._credit_company_market_balance(tax)
            await self._db.execute("UPDATE player_companies SET owner_id = ? WHERE id = ?", (buyer_id, offer["company_id"]))
            await self._db.execute(
                "UPDATE player_company_offers SET status = CASE WHEN id = ? THEN 'accepted' ELSE 'cancelled' END WHERE company_id = ? AND status = 'pending'",
                (offer_id, offer["company_id"])
            )
            await self._db.commit()
            return True, f"You bought {offer['company_name']} for {gross:,} Medals. Seller received {net:,}; {tax:,} ({int(round(tax_rate * 100))}%) tax went to the market bank."
        except Exception:
            await self._db.rollback()
            raise

    async def reject_company_sale_offer(self, buyer_id: int, offer_id: int) -> tuple[bool, str]:
        if self._db is None:
            await self.setup()
        cur = await self._db.execute("""
            UPDATE player_company_offers SET status = 'rejected'
            WHERE id = ? AND buyer_id = ? AND status = 'pending'
        """, (int(offer_id), int(buyer_id)))
        await self._db.commit()
        if cur.rowcount:
            return True, "Company purchase offer declined."
        return False, "Offer not found or already closed."

    async def sell_company_to_bank(self, seller_id: int, gross_price: int) -> tuple[bool, str]:
        """Sell control to the finite, tax-funded market bank; no Medals are minted."""
        if self._db is None:
            await self.setup()
        seller_id = int(seller_id)
        try:
            gross_price = int(gross_price)
        except (TypeError, ValueError):
            return False, "Enter a whole Medal amount."
        if seller_id <= 0 or not 1 <= gross_price <= 2_000_000_000:
            return False, "Enter a valid sale price (1–2,000,000,000 Medals)."
        await self.get_global_economy(seller_id)
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("SELECT id, name FROM player_companies WHERE owner_id = ?", (seller_id,)) as cur:
                company = await cur.fetchone()
            if not company:
                await self._db.rollback()
                return False, "You do not own a listed company."
            async with self._db.execute("""
                SELECT pc.fair_value, s.price, s.total_supply
                FROM player_companies pc JOIN stocks s ON s.id = pc.stock_id
                WHERE pc.id = ?
            """, (company["id"],)) as cur:
                valuation_row = await cur.fetchone()
            reviewed_value = int(valuation_row[0] or 0) if valuation_row else 0
            market_value = int(valuation_row[1] or 0) * int(valuation_row[2] or 0) if valuation_row else 0
            max_bank_price = max(25_000, min(reviewed_value or 25_000, market_value or reviewed_value or 25_000))
            if gross_price > max_bank_price:
                await self._db.rollback()
                return False, f"Bank buyout is capped at {max_bank_price:,} Medals by the reviewed valuation and current market cap."
            async with self._db.execute("SELECT value FROM meta WHERE key = 'company_market_balance'") as cur:
                row = await cur.fetchone()
            bank_balance = max(0, int(row[0])) if row and str(row[0]).isdigit() else 0
            if bank_balance < gross_price:
                await self._db.rollback()
                return False, f"The market bank has {bank_balance:,} Medals available, less than your {gross_price:,} asking price."
            tax_rate = await self.get_stock_tax_rate()
            tax = min(gross_price, int(round(gross_price * tax_rate)))
            net = gross_price - tax
            await self._db.execute("UPDATE global_economy SET medals = medals + ? WHERE user_id = ?", (net, seller_id))
            await self._db.execute("UPDATE users SET medals = medals + ? WHERE user_id = ?", (net, seller_id))
            await self._db.execute(
                "UPDATE meta SET value = CAST(CAST(value AS INTEGER) - ? + ? AS TEXT) WHERE key = 'company_market_balance'",
                (gross_price, tax)
            )
            await self._db.execute("UPDATE player_companies SET owner_id = ? WHERE id = ?", (-int(company["id"]), company["id"]))
            await self._db.execute(
                "UPDATE player_company_offers SET status = 'cancelled' WHERE company_id = ? AND status = 'pending'",
                (company["id"],)
            )
            await self._db.commit()
            return True, f"Sold {company['name']} to the market bank. You received {net:,} Medals after {int(round(tax_rate * 100))}% tax ({tax:,})."
        except Exception:
            await self._db.rollback()
            raise

    async def get_player_company(self, user_id: int) -> dict | None:
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT pc.*, s.price, s.available_shares, s.total_supply
            FROM player_companies pc JOIN stocks s ON s.id = pc.stock_id
            WHERE pc.owner_id = ?
        """, (int(user_id),)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_all_player_companies(self) -> list[dict]:
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT pc.*, s.price, s.available_shares, s.total_supply
            FROM player_companies pc JOIN stocks s ON s.id = pc.stock_id
            ORDER BY pc.created_at DESC
        """) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def grant_player_company_aid(self, mayor_id: int, company_id: int) -> tuple[bool, str, dict | None]:
        """Transfer a fixed grant from the Mayor wallet into a capped company treasury."""
        if self._db is None:
            await self.setup()
        from utils.constants import COMPANY_AID_GRANT, COMPANY_TREASURY_CAP

        mayor_id, company_id = int(mayor_id), int(company_id)
        await self.get_global_economy(mayor_id)
        try:
            await self._db.execute("BEGIN IMMEDIATE")
            async with self._db.execute(
                "SELECT id, name, treasury, aid_received FROM player_companies WHERE id = ?",
                (company_id,)
            ) as cur:
                company = await cur.fetchone()
            if not company:
                await self._db.rollback()
                return False, "Player company not found.", None
            remaining = COMPANY_TREASURY_CAP - int(company[2] or 0)
            grant = min(COMPANY_AID_GRANT, remaining)
            if grant <= 0:
                await self._db.rollback()
                return False, f"{company[1]}'s treasury reached its {COMPANY_TREASURY_CAP:,} Medal cap.", None
            async with self._db.execute(
                "SELECT medals FROM global_economy WHERE user_id = ?", (mayor_id,)
            ) as cur:
                wallet = await cur.fetchone()
            if not wallet or int(wallet[0] or 0) < grant:
                await self._db.rollback()
                return False, f"Mayor needs {grant:,} wallet Medals to fund this grant.", None

            debit = await self._db.execute(
                "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?", (grant, mayor_id, grant)
            )
            if debit.rowcount != 1:
                await self._db.rollback()
                return False, "Mayor wallet changed before the company grant completed.", None
            await self._db.execute(
                "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (mayor_id, mayor_id)
            )
            await self._db.execute("""
                UPDATE player_companies
                SET treasury = treasury + ?,
                    aid_received = aid_received + ?,
                    fair_value = min(2000000000, fair_value + ?)
                WHERE id = ?
            """, (grant, grant, grant, company_id))
            await self._db.commit()
            updated = next((row for row in await self.get_all_player_companies() if row["id"] == company_id), None)
            return True, f"Transferred {grant:,} Medals from the Mayor wallet into {company[1]}'s company treasury. Treasury: {int(company[2] or 0) + grant:,}/{COMPANY_TREASURY_CAP:,}.", updated
        except Exception:
            await self._db.rollback()
            raise

    async def create_player_company(self, user_id: int, name: str, symbol: str, sector: str,
                                    valuation: int, annual_revenue: int, annual_profit: int,
                                    debt: int, description: str = "") -> tuple[bool, str, dict | None]:
        """Create a Medal-funded company and submit its IPO to the simulated market reviewers."""
        if self._db is None:
            await self.setup()
        from utils.constants import PLAYER_COMPANY_SECTORS

        user_id = int(user_id)
        name = " ".join(str(name).split())[:48]
        symbol = str(symbol).strip().upper()
        sector = str(sector).strip().lower()
        description = " ".join(str(description).split())[:240]
        try:
            valuation, annual_revenue = int(valuation), int(annual_revenue)
            annual_profit, debt = int(annual_profit), int(debt)
        except (ValueError, TypeError):
            return False, "Company figures must be whole Medal amounts.", None
        if not (2 <= len(symbol) <= 6 and symbol.isalnum()):
            return False, "Ticker must be 2–6 letters or numbers.", None
        if not name or sector not in PLAYER_COMPANY_SECTORS:
            return False, "Enter a company name and choose a valid sector.", None
        if not (250_000 <= valuation <= 2_000_000_000):
            return False, "Claimed valuation must be between 250,000 and 2,000,000,000 Medals.", None
        if not (0 <= annual_revenue <= 2_000_000_000 and -2_000_000_000 <= annual_profit <= 2_000_000_000 and 0 <= debt <= 2_000_000_000):
            return False, "Revenue, profit, or debt is outside the allowed range.", None

        fee = 25000
        fair_value = max(100_000, annual_revenue + max(0, annual_profit) * 6 - debt)
        fair_value = min(2_000_000_000, fair_value)
        plausible = valuation <= fair_value * 2
        # Plausible claims have exactly a 50/50 approve/crash review; inflated claims fail the fundamentals review.
        approved = plausible and random.random() < 0.5
        # A company may be valuable, but no single share can become an
        # economy-breaking reserve asset.
        claim_price = max(2_000, min(80_000, int(round(valuation / 2500))))
        fair_price = max(2_000, min(80_000, int(round(fair_value / 2500))))
        if approved:
            opening_price = min(claim_price, fair_price * 2)
            ai_status = "approved"
            ai_report = f"AI analysts reviewed the reported revenue, profit, and debt. Modeled fair value: {fair_value:,} Medals. The IPO was approved."
        else:
            opening_price = max(2_000, min(int(claim_price * 0.20), fair_price))
            ai_status = "crashed"
            reason = "Claimed valuation exceeded twice the modeled fair value." if not plausible else "The 50/50 AI market review rejected the IPO."
            ai_report = f"{reason} Modeled fair value: {fair_value:,} Medals. The share price opened after an 80% crash adjustment."

        await self.get_global_economy(user_id)
        now = time.time()
        try:
            await self._db.execute("BEGIN IMMEDIATE")
            async with self._db.execute("SELECT 1 FROM player_companies WHERE owner_id = ?", (user_id,)) as cur:
                if await cur.fetchone():
                    await self._db.rollback()
                    return False, "Each player can found one listed company.", None
            async with self._db.execute("SELECT 1 FROM stocks WHERE UPPER(symbol) = UPPER(?)", (symbol,)) as cur:
                if await cur.fetchone():
                    await self._db.rollback()
                    return False, f"Ticker {symbol} is already listed.", None
            async with self._db.execute("SELECT medals FROM global_economy WHERE user_id = ?", (user_id,)) as cur:
                wallet = await cur.fetchone()
            if not wallet or int(wallet[0] or 0) < fee:
                await self._db.rollback()
                return False, f"Founding a company costs {fee:,} Medals.", None

            debit = await self._db.execute("UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?", (fee, user_id, fee))
            if debit.rowcount != 1:
                await self._db.rollback()
                return False, "Your wallet changed before the company founding completed.", None
            await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (user_id, user_id))
            supply = 2500
            await self._db.execute(
                "INSERT INTO stocks (symbol, name, price, total_supply, available_shares, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (symbol, name, opening_price, supply, supply, description, now)
            )
            async with self._db.execute("SELECT last_insert_rowid()") as cur:
                stock_id = int((await cur.fetchone())[0])
            await self._db.execute(
                "INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)",
                (stock_id, opening_price, now)
            )
            await self._db.execute("""
                INSERT INTO player_companies
                    (owner_id, name, symbol, sector, description, claimed_valuation,
                     annual_revenue, annual_profit, debt, fair_value, treasury, aid_received,
                     ai_status, ai_report, stock_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?)
            """, (user_id, name, symbol, sector, description, valuation,
                  annual_revenue, annual_profit, debt, fair_value, ai_status,
                  ai_report, stock_id, now))
            await self._db.commit()
            company = await self.get_player_company(user_id)
            result_text = "AI review approved." if approved else "AI review rejected the valuation and the stock crashed."
            return True, f"{result_text} {ai_report} {symbol} is now listed and open to buy. Founding fee: {fee:,} Medals.", company
        except Exception:
            await self._db.rollback()
            raise

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

        new_price = max(2_000, min(80_000, int(new_price)))

        await self._db.execute("UPDATE stocks SET price = ? WHERE id = ?", (new_price, stock_id))

        await self._db.execute("INSERT INTO stock_history (stock_id, price, timestamp) VALUES (?, ?, ?)", (stock_id, new_price, time.time()))

        await self._db.commit()



    async def delete_stock(self, stock_id: int) -> tuple[bool, str]:
        """Delist an empty stock only; never liquidate holders implicitly."""
        stock = await self.get_stock(stock_id)
        if not stock:
            return False, "Stock not found."

        async with self._db.execute(
            "SELECT COUNT(*) FROM user_stocks WHERE stock_id = ? AND shares > 0",
            (stock_id,)
        ) as cur:
            holders = int((await cur.fetchone())[0] or 0)
        if holders:
            return False, "Cannot delist a stock while shareholders still hold shares. Require explicit shareholder settlement first."

        await self._db.execute("DELETE FROM stock_history WHERE stock_id = ?", (stock_id,))
        await self._db.execute("DELETE FROM stocks WHERE id = ?", (stock_id,))
        await self._db.commit()
        return True, f"{stock['symbol']} was delisted."



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

        MAX_HOLDING = 100
        if current_shares + shares > MAX_HOLDING:
            return False, f"Holding limit reached. You can only hold a maximum of {MAX_HOLDING} shares per stock (Currently hold: {current_shares})."

        # Bounded price impact: no order can move a listing more than 0.5%.
        pct_impact = min(0.005, 0.00002 * shares)
        price_bump = max(1, int(round(stock["price"] * pct_impact)))
        new_price = min(80_000, max(2_000, stock["price"] + price_bump))

        # Average execution price along the order book curve (slippage protection)
        effective_buy_price = (stock["price"] + new_price) / 2.0
        gross_cost = int(round(shares * effective_buy_price))
        tax_rate = await self.get_stock_tax_rate()
        tax_amount = int(round(gross_cost * tax_rate))
        total_cost = gross_cost + tax_amount

        user_econ = await self.get_global_economy(user_id)
        if user_econ.get("medals", 0) < total_cost:
            return False, f"Insufficient Wallet Medals. You need {total_cost:,} Medals including {int(round(tax_rate * 100))}% market fee ({tax_amount:,} Medals; shares cost {gross_cost:,}), but only have {user_econ.get('medals', 0):,} in your wallet. (Withdraw from your /bank if needed!)"

        debit = await self._db.execute("UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?", (total_cost, user_id, total_cost))
        if debit.rowcount != 1:
            return False, "Your wallet changed before the stock purchase completed."
        await self._db.execute("UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?", (user_id, user_id))
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

        await self._credit_company_market_balance(tax_amount)
        await self.update_stock_price(stock_id, new_price)
        await self._db.commit()

        return True, f"Successfully purchased {shares} shares of {stock['symbol']} for {total_cost:,} Medals (shares: {gross_cost:,} + {int(round(tax_rate * 100))}% fee: {tax_amount:,}). Price rose to {new_price:,} Medals!"

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

        # Anti-arbitrage lock: Must hold for at least 10 minutes.
        elapsed = time.time() - last_buy_time
        if last_buy_time > 0 and elapsed < 600:
            remaining = int(600 - elapsed)
            return False, f"Anti-Arbitrage Lock: You recently purchased this stock. You must hold shares for at least 3 minutes before selling ({remaining}s remaining)."

        # Bounded price impact: no order can move a listing more than 0.5%.
        pct_impact = min(0.005, 0.00002 * shares)
        price_drop = max(1, int(round(stock["price"] * pct_impact)))
        new_price = max(2_000, min(80_000, stock["price"] - price_drop))

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

        await self._credit_company_market_balance(tax_amount)
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

    async def _credit_company_market_balance(self, amount: int):
        amount = max(0, int(amount))
        if amount:
            await self._db.execute("""
                INSERT INTO meta (key, value) VALUES ('company_market_balance', ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = CAST(CAST(meta.value AS INTEGER) + CAST(excluded.value AS INTEGER) AS TEXT)
            """, (str(amount),))

    async def get_company_market_balance(self) -> int:
        raw = await self.get_meta("company_market_balance")
        try:
            return max(0, int(raw or 0))
        except (ValueError, TypeError):
            return 0

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


    async def reset_virtual_economy_once(self):
        """Start a clean economy season once, preserving non-economy member data."""
        reset_key = "virtual_economy_reset_2026_10"
        if await self.get_meta(reset_key) == "complete":
            return False

        await self._db.execute("BEGIN IMMEDIATE")
        try:
            # Startup migrations are preservation-only. Wallets, banks, loans, and
            # gambling balances are live player data and must never be reset because
            # a legacy database is missing the migration marker.
            # Stock portfolios and player companies are persistent season assets.
            # Never delete them from a startup migration: a missing/reset marker must
            # not erase holdings or unexpectedly refund shareholders.
            await self._db.execute(
                "DELETE FROM player_company_offers WHERE status IN ('expired', 'rejected', 'cancelled')"
            )

            # Virtual Earth: reset the map and all player-created state to the base roster.
            for table in (
                "earth_country_offers", "earth_trade_routes", "earth_wars", "earth_alliances",
                "earth_intelligence", "earth_spies", "earth_tools", "earth_nuclear_strikes", "earth_military_log", "earth_citizens",
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


    async def reset_earth_world_to_zero_once(self) -> bool:
        """Reset every country's economy and ownership once for the zero-start season."""
        reset_key = "earth_zero_start_2026_10"
        if await self.get_meta(reset_key) == "complete":
            return False

        await self._db.execute("BEGIN IMMEDIATE")
        try:
            for table in (
                "earth_country_offers", "earth_trade_routes", "earth_wars", "earth_alliances",
                "earth_intelligence", "earth_spies", "earth_tools", "earth_nuclear_strikes", "earth_citizens",
                "earth_cabinet_invites", "earth_cabinet", "earth_buildings", "earth_un_resolutions"
            ):
                await self._db.execute(f"DELETE FROM {table}")

            now = time.time()
            await self._db.execute("""
                UPDATE earth_countries
                SET owner_id = NULL, gdp = 0, treasury = 0,
                    stability = 50, unrest = 10, tax_rate = 10,
                    economic_doctrine = 'free_market',
                    military_doctrine = 'volunteer',
                    diplomatic_stance = 'neutral',
                    government_type = 'democracy', last_policy_review = 0,
                    for_sale_price = NULL, last_yield_claim = 0,
                    last_riot_check = 0, alliance_id = NULL,
                    last_growth_tick = ?, is_sanctioned = 0,
                    sanction_reason = NULL, sanction_expires = 0,
                    population = 100, army_divisions = 10, tanks = 1, jets = 1, ships = 1,
                    population_last_growth = ?
            """, (now, now))
            await self._db.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (reset_key, "complete")
            )
            await self._db.commit()
            return True
        except Exception:
            await self._db.rollback()
            raise


    async def release_user_earth_claims_once(self, user_id: int, keep_code: str = "IRN") -> bool:
        """Release a flagged user's extra countries once, preserving the requested country."""
        reset_key = f"earth_release_excess_{int(user_id)}_{str(keep_code).upper()}"
        if await self.get_meta(reset_key) == "complete":
            return False

        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                """SELECT id FROM earth_countries
                   WHERE owner_id = ? AND UPPER(code) <> UPPER(?)""",
                (int(user_id), str(keep_code))
            ) as cur:
                country_ids = [int(row[0]) for row in await cur.fetchall()]

            now = time.time()
            for country_id in country_ids:
                await self._reset_unclaimed_earth_country(country_id, now)

            await self._db.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                (reset_key, "complete")
            )
            await self._db.commit()
            return bool(country_ids)
        except Exception:
            await self._db.rollback()
            raise


    async def seed_default_earth_countries(self):
        """Seed the base sovereign country roster with zero economic assets."""
        from utils.constants import EARTH_COUNTRIES
        
        now = time.time()
        for c in EARTH_COUNTRIES:
            await self._db.execute("""
                INSERT OR IGNORE INTO earth_countries (
                    id, code, name, flag, lat, lng, owner_id, gdp, treasury, stability, unrest, is_coastal, capital, desc, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c["id"], c["code"], c["name"], c["flag"], c["lat"], c["lng"],
                None, 0, 0, 50, 10,
                c["is_coastal"], c.get("capital", ""), c.get("desc", ""), now
            ))
        await self._db.commit()

        # All base countries begin unclaimed; player ownership is earned in game.
        await self._db.commit()

    async def get_earth_countries(self) -> list[dict]:
        """Fetch all countries with owner profiles, stats, active wars, and stability."""
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
                item["military_power"] = 20 + int(item.get("army_divisions", 10) or 0) * 4 + int(item.get("tanks", 1) or 0) * 35 + int(item.get("jets", 1) or 0) * 28 + int(item.get("ships", 1) or 0) * 18 + (item.get("building_count", 0) * 15)
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

        async with self._db.execute("SELECT COALESCE(SUM(attacker_divisions),0) FROM earth_wars WHERE status='active' AND attacker_country_id=?", (country_id,)) as cur:
            deployed = int((await cur.fetchone())[0] or 0)
        async with self._db.execute("SELECT COALESCE(SUM(defender_divisions),0) FROM earth_wars WHERE status='active' AND defender_country_id=?", (country_id,)) as cur:
            deployed += int((await cur.fetchone())[0] or 0)
        country["deployed_divisions"] = deployed
        for unit in ("tanks", "jets", "ships"):
            async with self._db.execute(
                f"SELECT COALESCE(SUM(CASE WHEN attacker_country_id=? THEN attacker_{unit} ELSE defender_{unit} END),0) FROM earth_wars WHERE status='active' AND (attacker_country_id=? OR defender_country_id=?)",
                (country_id, country_id, country_id),
            ) as cur:
                country[f"deployed_{unit}"] = int((await cur.fetchone())[0] or 0)
            country[f"available_{unit}"] = max(0, int(country.get(unit, 0) or 0) - country[f"deployed_{unit}"])

        # Calculate combat power
        mil_power = 20
        def_power = 30
        mil_power += int(country.get("tanks", 1) or 0) * 35 + int(country.get("jets", 1) or 0) * 28 + int(country.get("ships", 1) or 0) * 18
        def_power += int(country.get("tanks", 1) or 0) * 18 + int(country.get("jets", 1) or 0) * 10 + int(country.get("ships", 1) or 0) * 12
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

    async def get_earth_country_by_code_or_name(self, value: str) -> dict | None:
        """Resolve an Earth country by its exact country code or case-insensitive name."""
        if self._db is None:
            await self.setup()
        value = " ".join(str(value or "").strip().split())
        if not value:
            return None
        async with self._db.execute("""
            SELECT id FROM earth_countries
            WHERE UPPER(code) = UPPER(?) OR LOWER(name) = LOWER(?)
            ORDER BY id ASC LIMIT 1
        """, (value, value)) as cur:
            row = await cur.fetchone()
        return await self.get_earth_country(row[0]) if row else None

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

    async def get_user_earth_permissions(self, user_id: int) -> dict[str, set[str]]:
        """Return sovereign owner IDs where this user is president or holds a minister role."""
        if self._db is None:
            await self.setup()
        permissions = {"economy": set(), "defense": set(), "intelligence": set()}
        async with self._db.execute(
            "SELECT owner_id FROM earth_countries WHERE owner_id = ?", (user_id,)
        ) as cur:
            for row in await cur.fetchall():
                if row[0] is not None:
                    for role in permissions:
                        permissions[role].add(str(row[0]))
        async with self._db.execute("""
            SELECT DISTINCT c.owner_id, cab.role
            FROM earth_cabinet cab JOIN earth_countries c ON c.id = cab.country_id
            WHERE cab.user_id = ? AND c.owner_id IS NOT NULL
        """, (user_id,)) as cur:
            for row in await cur.fetchall():
                if row[1] in permissions:
                    permissions[row[1]].add(str(row[0]))
        return permissions

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

        # Ocean infrastructure requires a coastal country.
        if building_type in ("naval_port", "ocean_base", "oil_rig"):
            async with self._db.execute("SELECT is_coastal FROM earth_countries WHERE id = ?", (country_id,)) as cur:
                c_row = await cur.fetchone()
                if not c_row or not c_row[0]:
                    return False, "⛔ Landlocked country: ports, ocean bases, and offshore oil rigs require a coastal country.", 0

        # Deduct medals
        await self.subtract_medals(user_id, cost)

        now = time.time()
        new_level = current_lvl + 1
        if current_lvl > 0:
            await self._db.execute("UPDATE earth_buildings SET level = level + 1 WHERE country_id = ? AND building_type = ?", (country_id, building_type))
        else:
            await self._db.execute("INSERT INTO earth_buildings (country_id, building_type, level, created_at) VALUES (?, ?, 1, ?)", (country_id, building_type, now))

        # Infrastructure is how a zero-start country builds GDP.
        stab_boost = meta.get("stability_bonus", 0)
        unrest_drop = meta.get("unrest_reduction", 0)
        gdp_boost = max(1000, int(meta.get("hourly_yield", 0) * 5))
        await self._db.execute("""
            UPDATE earth_countries
            SET stability = min(100, stability + ?),
                unrest = max(0, unrest - ?),
                gdp = gdp + ?
            WHERE id = ?
        """, (stab_boost, unrest_drop, gdp_boost, country_id))
        await self._db.commit()

        return True, f"🏗️ Commissioned! {meta['emoji']} {meta['name']} upgraded to Level {new_level} (-{cost:,} Medals; +{gdp_boost:,} GDP).", cost

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

    async def _reset_unclaimed_earth_country(self, country_id: int, now: float | None = None):
        """Strip prior rule, assets, and state data before a country is claimed as a fresh start."""
        now = float(now or time.time())
        country_id = int(country_id)
        await self._db.execute("DELETE FROM earth_country_offers WHERE country_id = ?", (country_id,))
        await self._db.execute("DELETE FROM earth_cabinet_invites WHERE country_id = ?", (country_id,))
        await self._db.execute("DELETE FROM earth_cabinet WHERE country_id = ?", (country_id,))
        await self._db.execute("DELETE FROM earth_citizens WHERE country_id = ?", (country_id,))
        await self._db.execute("DELETE FROM earth_buildings WHERE country_id = ?", (country_id,))
        await self._db.execute("DELETE FROM earth_tools WHERE country_id = ?", (country_id,))
        await self._db.execute("DELETE FROM earth_military_log WHERE country_id = ?", (country_id,))
        await self._db.execute(
            "DELETE FROM earth_spies WHERE owner_country_id = ? OR target_country_id = ?",
            (country_id, country_id)
        )
        await self._db.execute(
            "DELETE FROM earth_intelligence WHERE gatherer_country_id = ? OR target_country_id = ?",
            (country_id, country_id)
        )
        await self._db.execute(
            "DELETE FROM earth_trade_routes WHERE country_a_id = ? OR country_b_id = ?",
            (country_id, country_id)
        )
        await self._db.execute(
            "DELETE FROM earth_wars WHERE status = 'active' AND (attacker_country_id = ? OR defender_country_id = ?)",
            (country_id, country_id)
        )
        await self._db.execute("""
            UPDATE earth_countries
            SET owner_id = NULL, gdp = 0, treasury = 0, stability = 50, unrest = 10,
                tax_rate = 10, economic_doctrine = 'free_market',
                military_doctrine = 'volunteer', diplomatic_stance = 'neutral',
                government_type = 'democracy', last_policy_review = 0,
                for_sale_price = NULL, last_yield_claim = ?, last_riot_check = ?,
                last_growth_tick = ?, alliance_id = NULL, is_sanctioned = 0,
                sanction_reason = NULL, sanction_expires = 0,
                population = 100, army_divisions = 10, tanks = 1, jets = 1, ships = 1,
                population_last_growth = ?
            WHERE id = ?
        """, (now, now, now, now, country_id))

    async def buy_earth_country(self, user_id: int, country_id: int, offer: int = 0, ip_fingerprint: str | None = None) -> tuple[bool, str]:
        """Claim one unowned country with an atomic wallet and clean-start reset."""
        if self._db is None:
            await self.setup()
        user_id, country_id = int(user_id), int(country_id)
        try:
            offer = int(offer)
        except (ValueError, TypeError):
            offer = 0
        if not 0 <= offer <= 2_000_000_000:
            return False, "Country offer must be between 0 and 2,000,000,000 Medals."
        ip_fingerprint = str(ip_fingerprint or "").strip()[:128] or None
        if offer:
            await self.get_global_economy(user_id)

        now = time.time()
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT id, name FROM earth_countries WHERE owner_id = ? LIMIT 1", (user_id,)
            ) as cur:
                existing = await cur.fetchone()
            if existing:
                await self._db.rollback()
                return False, f"One Sovereign Rule: You already govern {existing['name']}! You cannot claim another starting country."

            if ip_fingerprint:
                async with self._db.execute(
                    "SELECT first_user_id FROM earth_claim_fingerprints WHERE fingerprint = ?",
                    (ip_fingerprint,)
                ) as cur:
                    fingerprint_owner = await cur.fetchone()
                if fingerprint_owner and int(fingerprint_owner[0]) != user_id:
                    await self._db.rollback()
                    return False, "Duplicate claim blocked: this public network already claimed a starting country."

            async with self._db.execute(
                "SELECT id, name, flag, owner_id FROM earth_countries WHERE id = ?", (country_id,)
            ) as cur:
                country = await cur.fetchone()
            if not country:
                await self._db.rollback()
                return False, "Country not found."
            if country["owner_id"] is not None:
                await self._db.rollback()
                return False, f"This nation is already governed by <@{country['owner_id']}>. You can claim one unowned starting country or capture a ruled country through war."

            if offer:
                async with self._db.execute(
                    "SELECT medals FROM global_economy WHERE user_id = ?", (user_id,)
                ) as cur:
                    wallet = await cur.fetchone()
                if not wallet or int(wallet[0] or 0) < offer:
                    await self._db.rollback()
                    return False, f"Insufficient Capital: you offered {offer:,} Medals but do not have enough in your wallet."

            await self._reset_unclaimed_earth_country(country_id, now)
            async with self._db.execute("""
                UPDATE earth_countries SET owner_id = ?
                WHERE id = ? AND owner_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM earth_countries WHERE owner_id = ?)
            """, (user_id, country_id, user_id)) as cur:
                if cur.rowcount != 1:
                    await self._db.rollback()
                    return False, "This nation was just claimed, or you already govern a country."

            if offer:
                async with self._db.execute(
                    "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                    (offer, user_id, offer)
                ) as cur:
                    if cur.rowcount != 1:
                        await self._db.rollback()
                        return False, "Your wallet balance changed before the claim completed; try again."
                await self._db.execute(
                    "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?",
                    (user_id, user_id)
                )

            await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (user_id,))
            await self._db.execute("""
                INSERT OR REPLACE INTO earth_citizens (user_id, country_id, joined_at)
                VALUES (?, ?, ?)
            """, (user_id, country_id, now))
            if ip_fingerprint:
                await self._db.execute("""
                    INSERT OR IGNORE INTO earth_claim_fingerprints (fingerprint, first_user_id, claimed_at)
                    VALUES (?, ?, ?)
                """, (ip_fingerprint, user_id, now))
            await self._db.commit()
            if offer == 0:
                return True, f"{country['flag']} **{country['name']}** is now your country. It starts at 0 GDP, 0 treasury, and no buildings."
            return True, f"{country['flag']} **{country['name']}** is now your country. Your {offer:,}-Medal offer was spent; the country starts with 0 GDP, 0 treasury, and no buildings."
        except Exception:
            await self._db.rollback()
            raise

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
        """Found a zero-start custom country, atomically replacing any explicitly abdicated rule."""
        if self._db is None:
            await self.setup()
        user_id = int(user_id)
        name = " ".join(str(name or "").split())
        if not 2 <= len(name) <= 40:
            return False, "Country name must be between 2 and 40 characters.", None
        flag = " ".join(str(flag or "???").split())[:16] or "???"
        capital = " ".join(str(capital or "Capital City").split())[:64] or "Capital City"
        desc = " ".join(str(desc or "").split())[:300] or f"Sovereign nation of {name} founded by supreme decree."
        try:
            offered_medals = int(offered_medals)
        except (ValueError, TypeError):
            offered_medals = 0
        if not 0 <= offered_medals <= 2_000_000_000:
            return False, "The founding offer must be between 0 and 2,000,000,000 Medals.", None
        if offered_medals:
            await self.get_global_economy(user_id)

        if lat is not None:
            try:
                lat = float(lat)
            except (ValueError, TypeError):
                lat = None
        if lng is not None:
            try:
                lng = float(lng)
            except (ValueError, TypeError):
                lng = None
        if lat is None or lng is None:
            import random
            places = [
                (25.0, -40.0), (14.5, -140.0), (-8.5, 72.0), (-17.5, -149.5),
                (21.5, -72.0), (35.0, 18.0), (-20.0, 57.5), (64.0, -20.0),
                (-12.0, 96.8), (0.5, -30.0)
            ]
            lat, lng = random.choice(places)
            lat = round(lat + random.uniform(-1.5, 1.5), 2)
            lng = round(lng + random.uniform(-1.5, 1.5), 2)
        else:
            lat = max(-80.0, min(80.0, lat))
            lng = max(-180.0, min(180.0, lng))

        now = time.time()
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT id, name FROM earth_countries WHERE owner_id = ? ORDER BY id",
                (user_id,)
            ) as cur:
                existing = await cur.fetchall()
            if existing and not replace_current:
                await self._db.rollback()
                return False, f"You already govern **{existing[0]['name']}**! Choose replace only if you intend to abdicate.", None
            if offered_medals:
                async with self._db.execute(
                    "SELECT medals FROM global_economy WHERE user_id = ?", (user_id,)
                ) as cur:
                    wallet = await cur.fetchone()
                if not wallet or int(wallet[0] or 0) < offered_medals:
                    await self._db.rollback()
                    return False, f"Insufficient funds: your {offered_medals:,}-Medal offer exceeds your wallet.", None

            for row in existing:
                await self._reset_unclaimed_earth_country(int(row["id"]), now)
            if offered_medals:
                async with self._db.execute(
                    "UPDATE global_economy SET medals = medals - ? WHERE user_id = ? AND medals >= ?",
                    (offered_medals, user_id, offered_medals)
                ) as cur:
                    if cur.rowcount != 1:
                        await self._db.rollback()
                        return False, "Your wallet balance changed before the charter completed; try again.", None
                await self._db.execute(
                    "UPDATE users SET medals = (SELECT medals FROM global_economy WHERE user_id = ?) WHERE user_id = ?",
                    (user_id, user_id)
                )
            await self._db.execute("DELETE FROM earth_cabinet WHERE user_id = ?", (user_id,))

            clean_code = "".join(ch for ch in name.upper() if ch.isalnum()) or "NEW"
            base_code = (clean_code + "XXX")[:3]
            code = None
            for suffix in range(0, 1000):
                candidate = base_code if suffix == 0 else f"{base_code[:2]}{suffix:02d}"
                async with self._db.execute(
                    "SELECT 1 FROM earth_countries WHERE UPPER(code) = UPPER(?)", (candidate,)
                ) as cur:
                    if not await cur.fetchone():
                        code = candidate
                        break
            if code is None:
                await self._db.rollback()
                return False, "No unused country code is available. Try a different country name.", None

            async with self._db.execute("""
                INSERT INTO earth_countries (
                    code, name, flag, lat, lng, owner_id, gdp, treasury,
                    stability, unrest, is_coastal, tax_rate,
                    economic_doctrine, military_doctrine, diplomatic_stance, government_type,
                    capital, desc, created_at, last_yield_claim, last_growth_tick,
                    population, army_divisions, tanks, jets, ships, population_last_growth
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 85, 10, 1, 10,
                          'free_market', 'volunteer', 'neutral', 'democracy',
                          ?, ?, ?, ?, ?, 100, 10, 1, 1, 1, ?)
            """, (code, name, flag, lat, lng, user_id, capital, desc, now, now, now, now)) as cur:
                country_id = int(cur.lastrowid)
            await self._db.commit()
            country = {
                "id": country_id, "code": code, "name": name, "flag": flag,
                "capital": capital, "lat": lat, "lng": lng,
                "gdp": 0, "treasury": 0, "owner_id": user_id,
                "population": 100, "army_divisions": 10, "tanks": 1, "jets": 1, "ships": 1
            }
            return True, f"Sovereign Charter Proclaimed! {flag} **{name}** ({code}) begins with 0 GDP, 0 treasury, and no starting buildings. The {offered_medals:,}-Medal offer was spent.", country
        except Exception:
            await self._db.rollback()
            raise

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
            gross_stipend = 3500 if c.get("user_role") == "citizen" else 8500
            tax_rate = max(0, min(50, int(c.get("tax_rate", 10))))
            tax = int(round(gross_stipend * tax_rate / 100))
            stipend = gross_stipend - tax
            await self.add_medals(user_id, stipend)
            await self._db.execute(
                "UPDATE earth_countries SET treasury = treasury + ? WHERE id = ?",
                (tax, c["id"])
            )
            await self._db.commit()
            return stipend, (
                f"National stipend: +{stipend:,} Medals from {c['flag']} {c['name']} "
                f"({tax:,} Medals withheld at {tax_rate}% tax)."
            )

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
            return 0, "No productive infrastructure yet. Build a school, mine, factory, oil rig, or port before collecting national dividends."

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

    async def update_earth_policies(self, user_id: int, country_id: int, economic: str,
                                   military: str, diplomatic: str, tax_rate: int,
                                   government_type: str = "democracy") -> tuple[bool, str]:
        """Let the President or Economy Minister submit policy to a simulated 50/50 AI review."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_DOCTRINES, EARTH_GOVERNMENTS

        if economic not in EARTH_DOCTRINES["economic"] or military not in EARTH_DOCTRINES["military"]:
            return False, "Invalid economic or military doctrine."
        if diplomatic not in EARTH_DOCTRINES["diplomatic"] or government_type not in EARTH_GOVERNMENTS:
            return False, "Invalid diplomatic stance or government type."
        try:
            tax_rate = int(tax_rate)
        except (ValueError, TypeError):
            return False, "Tax rate must be a whole number from 0% to 50%."
        if tax_rate < 0 or tax_rate > 50:
            return False, "Tax rate must be between 0% and 50%."
        if not await self.has_earth_cabinet_permission(user_id, country_id, "economy"):
            return False, "Only the President or appointed Economy Minister can submit national policy and tax changes."

        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT last_policy_review FROM earth_countries WHERE id = ?", (country_id,)
            ) as cur:
                row = await cur.fetchone()
            if not row:
                await self._db.rollback()
                return False, "Country not found."
            now = time.time()
            wait = 900 - (now - (row[0] or 0))
            if wait > 0:
                await self._db.rollback()
                return False, f"The Policy Council is reviewing proposals. Try again in {int(wait // 60) + 1} minutes."

            approved = random.random() < 0.5
            await self._db.execute(
                "UPDATE earth_countries SET last_policy_review = ? WHERE id = ?", (now, country_id)
            )
            if not approved:
                await self._db.commit()
                return False, "The simulated AI Policy Council rejected this proposal. Its approval chance is 50%; current settings remain unchanged."

            unrest_add = 15 if tax_rate > 25 else (5 if tax_rate > 15 else 0)
            await self._db.execute("""
                UPDATE earth_countries
                SET economic_doctrine = ?,
                    military_doctrine = ?,
                    diplomatic_stance = ?,
                    government_type = ?,
                    tax_rate = ?,
                    unrest = min(100, unrest + ?)
                WHERE id = ?
            """, (economic, military, diplomatic, government_type, tax_rate, unrest_add, country_id))
            await self._db.commit()
            return True, f"AI Policy Council approved the proposal. Government set to {EARTH_GOVERNMENTS[government_type]['name']}; custom tax set to {tax_rate}%."
        except Exception:
            await self._db.rollback()
            raise

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
        """Apply tax unrest pressure on a six-hour clock, regardless of page refresh rate."""
        if self._db is None:
            await self.setup()

        events = []
        now = time.time()
        async with self._db.execute(
            "SELECT id, name, flag, owner_id, unrest, stability, tax_rate, last_riot_check "
            "FROM earth_countries WHERE owner_id IS NOT NULL"
        ) as cur:
            countries = [dict(row) for row in await cur.fetchall()]

        for country in countries:
            last_check = country.get("last_riot_check") or 0
            if now - last_check < 6 * 3600:
                continue

            tax_rate = max(0, min(50, int(country.get("tax_rate", 10))))
            pressure = max(0, (tax_rate - 20 + 9) // 10) if tax_rate > 20 else 0
            unrest = min(100, int(country.get("unrest", 0)) + pressure)
            country_id = country["id"]

            if unrest >= 85 and tax_rate >= 25:
                old_leader = country["owner_id"]
                await self._db.execute("""
                    UPDATE earth_countries
                    SET owner_id = NULL, stability = 50, unrest = 25, last_riot_check = ?
                    WHERE id = ?
                """, (now, country_id))
                await self._db.execute("DELETE FROM earth_cabinet WHERE country_id = ?", (country_id,))
                events.append({
                    "type": "revolution",
                    "country_id": country_id,
                    "name": country["name"],
                    "flag": country["flag"],
                    "ousted_leader_id": old_leader,
                    "message": (
                        f"🚨 Revolution: tax pressure and unrest removed the ruler of "
                        f"{country['flag']} {country['name']}."
                    )
                })
            else:
                await self._db.execute(
                    "UPDATE earth_countries SET unrest = ?, last_riot_check = ? WHERE id = ?",
                    (unrest, now, country_id)
                )

        if countries:
            await self._db.commit()
        return events

    # ─── Espionage & Intelligence System ──────────────────────────────────────

    async def resolve_due_earth_spy_missions(self) -> int:
        """Resolve field operations after their mission timers expire."""
        if self._db is None:
            await self.setup()
        now = time.time()
        async with self._db.execute("SELECT * FROM earth_spies WHERE status='infiltrating' AND mission_end_time>0 AND mission_end_time<=?", (now,)) as cur:
            pending = [dict(row) for row in await cur.fetchall()]
        from utils.constants import EARTH_SPY_MISSIONS
        resolved = 0
        for spy in pending:
            target_id = int(spy.get("target_country_id") or 0)
            async with self._db.execute("SELECT * FROM earth_countries WHERE id=?", (target_id,)) as cur:
                row = await cur.fetchone()
            if not row:
                await self._db.execute("UPDATE earth_spies SET status='idle',target_country_id=NULL,mission=NULL,mission_end_time=0 WHERE id=?", (spy["id"],))
                resolved += 1
                continue
            target = dict(row)
            meta = EARTH_SPY_MISSIONS.get(spy.get("mission"), {})
            async with self._db.execute("SELECT COALESCE(SUM(level),0) FROM earth_buildings WHERE country_id=? AND building_type='bunker'", (target_id,)) as cur:
                bunkers = int((await cur.fetchone())[0] or 0)
            risk = max(0.08, min(0.72, float(meta.get("capture_risk",0.25)) + bunkers*0.03 - int(spy.get("skill_level",1))*0.025))
            caught = random.random() < risk
            if caught:
                incident = {"alert":"agent_captured","caught_codename":spy["codename"],"origin_country_id":spy["owner_country_id"],"timestamp":now}
                await self._db.execute("UPDATE earth_spies SET status='captured',mission_end_time=0 WHERE id=?", (spy["id"],))
                await self._db.execute("INSERT INTO earth_intelligence(gatherer_country_id,target_country_id,intel_type,intel_data,expires_at,created_at) VALUES (?,?,'incident',?,?,?)", (target_id,spy["owner_country_id"],json.dumps(incident),now+604800,now))
                resolved += 1
                continue
            mission = spy.get("mission")
            result = {"target_name":target["name"],"flag":target["flag"],"mission":mission,"resolved_at":now}
            intel_type = "covert_result"
            if mission == "intel":
                async with self._db.execute("SELECT tool_key,SUM(level) AS quantity FROM earth_tools WHERE country_id=? GROUP BY tool_key", (target_id,)) as cur:
                    arsenal = {r["tool_key"]:int(r["quantity"] or 0) for r in await cur.fetchall()}
                async with self._db.execute("SELECT action,unit_type,amount,actor_id,created_at FROM earth_military_log WHERE country_id=? AND created_at>=? ORDER BY created_at DESC LIMIT 25", (target_id,now-30*86400)) as cur:
                    orders = [dict(r) for r in await cur.fetchall()]
                result.update({"gdp":target["gdp"],"treasury":target["treasury"],"population":target["population"],"army_divisions":target["army_divisions"],"tanks":target["tanks"],"jets":target["jets"],"ships":target["ships"],"stability":target["stability"],"unrest":target["unrest"],"total_defense_power":target["army_divisions"]*2+target["tanks"]*18+target["jets"]*10+target["ships"]*12,"arsenal":arsenal,"nuclear_plot_detected":bool(arsenal.get("nuclear_launch_pad") and arsenal.get("tactical_nuke")),"military_orders_last_30_days":orders,"buildings":[{"type":b["building_type"],"level":b["level"]} for b in await self.get_country_buildings(target_id)],"alliances":target["alliance_id"] or "Non-Aligned"})
                intel_type = "full_dossier"
            elif mission == "sabotage":
                async with self._db.execute("SELECT id,building_type FROM earth_buildings WHERE country_id=? AND is_sabotaged=0 ORDER BY RANDOM() LIMIT 1", (target_id,)) as cur:
                    building = await cur.fetchone()
                if building:
                    await self._db.execute("UPDATE earth_buildings SET is_sabotaged=1,sabotaged_until=? WHERE id=?", (now+43200,building[0]))
                    result["sabotaged_building"] = building[1]
                else:
                    result["outcome"] = "No vulnerable infrastructure found."
            elif mission == "incite_riot":
                await self._db.execute("UPDATE earth_countries SET unrest=min(80,unrest+8),stability=max(10,stability-5) WHERE id=?", (target_id,))
                result.update({"unrest_added":8,"stability_lost":5,"leadership_change":False})
            await self._db.execute("UPDATE earth_spies SET status='idle',target_country_id=NULL,mission=NULL,mission_end_time=0,skill_level=min(5,skill_level+1) WHERE id=?", (spy["id"],))
            await self._db.execute("INSERT INTO earth_intelligence(gatherer_country_id,target_country_id,intel_type,intel_data,expires_at,created_at) VALUES (?,?,?,?,?,?)", (spy["owner_country_id"],target_id,intel_type,json.dumps(result),now+86400,now))
            resolved += 1
        if resolved:
            await self._db.commit()
        return resolved

    async def get_earth_spies(self, country_id: int) -> list[dict]:
        """Fetch all secret agents in the nation's intelligence bureau."""
        if self._db is None:
            await self.setup()
        await self.resolve_due_earth_spy_missions()
        async with self._db.execute("""
            SELECT s.*, tc.name as target_country_name, tc.flag as target_country_flag
            FROM earth_spies s
            LEFT JOIN earth_countries tc ON s.target_country_id = tc.id
            WHERE s.owner_country_id = ?
            ORDER BY s.id DESC
        """, (country_id,)) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
        now = time.time()
        for spy in rows:
            spy["mission_remaining_seconds"] = max(0,int((spy.get("mission_end_time") or 0)-now)) if spy.get("status")=="infiltrating" else 0
        return rows

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
        """Start a timed covert operation; never apply its effect at dispatch."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_SPY_MISSIONS
        if mission not in EARTH_SPY_MISSIONS:
            return False, f"Invalid mission: {mission}", {}
        if country_id == target_country_id:
            return False, "You cannot dispatch espionage agents against your own nation!", {}
        if not await self.has_earth_cabinet_permission(user_id, country_id, "intelligence"):
            return False, "Only the President or Director of Intelligence can issue covert espionage orders!", {}
        async with self._db.execute("SELECT owner_id FROM earth_countries WHERE id=?", (country_id,)) as cur:
            source = await cur.fetchone()
        target = await self.get_earth_country(target_country_id)
        if not source or not target:
            return False, "Source or target country not found.", {}
        if not target.get("owner_id"):
            return False, "Spies need a ruled country to infiltrate.", {}
        if str(source[0]) == str(target.get("owner_id")):
            return False, "You cannot spy on a country ruled by your own sovereign.", {}
        async with self._db.execute("SELECT * FROM earth_spies WHERE id=? AND owner_country_id=?", (spy_id,country_id)) as cur:
            row = await cur.fetchone()
        if not row:
            return False, "Secret agent not found.", {}
        spy = dict(row)
        if spy.get("status") != "idle":
            return False, f"Agent '{spy['codename']}' is unavailable (status: {spy.get('status')}).", {}
        meta = EARTH_SPY_MISSIONS[mission]
        duration = max(900,int(meta.get("duration_seconds",1800)*max(0.65,1-(int(spy.get("skill_level",1))-1)*0.08)))
        now = time.time()
        end_time = now + duration
        async with self._db.execute("UPDATE earth_spies SET status='infiltrating',target_country_id=?,mission=?,mission_end_time=? WHERE id=? AND status='idle'", (target_country_id,mission,end_time,spy_id)) as cur:
            if cur.rowcount != 1:
                await self._db.rollback()
                return False, "Agent was dispatched elsewhere. Refresh the intelligence screen and retry.", {}
        await self._db.commit()
        return True, f"Agent '{spy['codename']}' is infiltrating {target['name']}. This operation takes {max(1,duration//60)} minutes; effects are applied only after it finishes.", {"complete":False,"end_time":end_time,"duration_seconds":duration,"mission":mission,"target_country_id":target_country_id}

    async def get_earth_intelligence(self, country_id: int) -> list[dict]:
        """Fetch all stolen foreign state intelligence dossiers and security alerts."""
        if self._db is None:
            await self.setup()
        await self.resolve_due_earth_spy_missions()
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

    async def declare_earth_war(self, user_id: int, attacker_country_id: int, defender_country_id: int, scale: str, domain: str = "land", equipment: int = 0) -> tuple[bool, str, dict]:
        """Declare a campaign and reserve only the equipment explicitly committed by the attacker."""
        if self._db is None:
            await self.setup()
        from utils.constants import EARTH_WAR_SCALES
        domain = str(domain or "land").strip().lower()
        if domain not in ("land", "air", "naval"):
            return False, "Choose a land, air, or naval campaign.", {}
        if scale not in EARTH_WAR_SCALES:
            return False, f"Invalid war scale: {scale}", {}
        try:
            equipment = int(equipment)
        except (ValueError, TypeError):
            return False, "Equipment count must be a whole number.", {}
        if equipment < 0 or equipment > 50:
            return False, "Commit between 0 and 50 equipment per campaign.", {}
        if attacker_country_id == defender_country_id:
            return False, "You cannot declare war upon yourself!", {}
        if not await self.has_earth_cabinet_permission(user_id, attacker_country_id, "defense"):
            return False, "Only the President or Army Commander can declare a campaign.", {}
        atk = await self.get_earth_country(attacker_country_id)
        dfn = await self.get_earth_country(defender_country_id)
        if not atk or not dfn:
            return False, "Sovereign country not found.", {}
        if not dfn.get("owner_id"):
            return False, "You cannot attack an unclaimed country.", {}
        if atk.get("owner_id") == dfn.get("owner_id"):
            return False, "You cannot declare war on a country ruled by your own sovereign.", {}
        if atk.get("alliance_id") and dfn.get("alliance_id") and atk["alliance_id"] == dfn["alliance_id"]:
            return False, "You cannot declare war on a fellow alliance member.", {}
        async with self._db.execute("SELECT COUNT(*) FROM earth_countries WHERE owner_id = ?", (atk.get("owner_id"),)) as cur:
            owned_count = (await cur.fetchone())[0]
        if owned_count >= 5:
            return False, "Your empire already governs the maximum of five territories.", {}
        meta = EARTH_WAR_SCALES[scale]
        unit = {"land": "tanks", "air": "jets", "naval": "ships"}[domain]
        unit_count = equipment if domain != "land" else 0
        if domain == "land" and equipment:
            unit_count = equipment
        if domain in ("air", "naval") and unit_count < 1:
            return False, f"A {domain} campaign must commit at least one {unit[:-1]}.", {}
        required_divisions = int(meta["min_divisions"]) if domain == "land" else 0
        now = time.time()
        duration = meta["duration_seconds"]
        end_time = now + duration
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("SELECT id FROM earth_wars WHERE status='active' AND ((attacker_country_id=? AND defender_country_id=?) OR (attacker_country_id=? AND defender_country_id=?))", (attacker_country_id, defender_country_id, defender_country_id, attacker_country_id)) as cur:
                if await cur.fetchone():
                    await self._db.rollback()
                    return False, "An active campaign is already ongoing between these countries.", {}
            async with self._db.execute(f"SELECT {unit}, army_divisions, owner_id FROM earth_countries WHERE id=?", (attacker_country_id,)) as cur:
                attacker_stock = await cur.fetchone()
            async with self._db.execute(f"SELECT {unit}, army_divisions FROM earth_countries WHERE id=?", (defender_country_id,)) as cur:
                defender_stock = await cur.fetchone()
            if not attacker_stock or int(attacker_stock[0] or 0) < unit_count:
                await self._db.rollback()
                return False, f"Your country does not have {unit_count} available {unit}.", {}
            if required_divisions and int(attacker_stock[1] or 0) < required_divisions:
                await self._db.rollback()
                return False, f"This campaign needs {required_divisions} reserve divisions; your country has {int(attacker_stock[1] or 0)}.", {}
            # The BEGIN IMMEDIATE transaction serializes this availability check with other dispatches.
            async with self._db.execute(
                f"SELECT COALESCE(SUM(CASE WHEN attacker_country_id=? THEN attacker_{unit} ELSE defender_{unit} END),0) FROM earth_wars WHERE status='active' AND (attacker_country_id=? OR defender_country_id=?)",
                (attacker_country_id, attacker_country_id, attacker_country_id),
            ) as cur:
                active_committed = int((await cur.fetchone())[0] or 0)
            if int(attacker_stock[0] or 0) - active_committed < unit_count:
                await self._db.rollback()
                return False, f"Only {max(0,int(attacker_stock[0] or 0)-active_committed)} {unit} are available outside other active campaigns.", {}
            # Defenders choose their own response from the equipment deployment controls;
            # declaring a campaign never auto-dispatches or invents their hardware.
            defender_committed_units = 0
            defender_divisions = min(required_divisions, max(0, int(defender_stock[1] or 0))) if defender_stock else 0
            attacker_divisions = required_divisions
            atk_power = 50 + attacker_divisions * 5 + unit_count * (15 if domain == "land" else 25)
            dfn_power = 50 + defender_divisions * 5 + defender_committed_units * (15 if domain == "land" else 25)
            if required_divisions:
                await self._db.execute("UPDATE earth_countries SET army_divisions=army_divisions-? WHERE id=?", (attacker_divisions, attacker_country_id))
                await self._db.execute("UPDATE earth_countries SET army_divisions=army_divisions-? WHERE id=?", (defender_divisions, defender_country_id))
            async with self._db.execute(
                f"""INSERT INTO earth_wars (
                    attacker_country_id, defender_country_id, scale, status, war_domain,
                    attacker_power, defender_power, attacker_divisions, defender_divisions,
                    attacker_{unit}, defender_{unit}, start_time, end_time, reparations
                ) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (attacker_country_id, defender_country_id, scale, domain, atk_power, dfn_power,
                 attacker_divisions, defender_divisions, unit_count, defender_committed_units,
                 now, end_time, meta["reparations"]),
            ) as cur:
                war_id = cur.lastrowid
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            raise
        return True, f"{domain.title()} campaign declared; {unit_count} {unit} reserved for the attacker.", {
            "war_id": war_id, "attacker_name": atk["name"], "attacker_flag": atk["flag"],
            "defender_name": dfn["name"], "defender_flag": dfn["flag"], "scale": scale,
            "scale_name": meta["name"], "domain": domain, "duration_hours": meta["duration_hours"],
            "start_time": now, "end_time": end_time,
        }

    async def get_active_earth_wars(self) -> list[dict]:
        """Fetch all ongoing multi-day global wars with progress percentages and 3D coordinates."""
        if self._db is None:
            await self.setup()
        try:
            await self.resolve_concluded_earth_wars()
        except Exception:
            pass
        now = time.time()
        async with self._db.execute("""
            SELECT w.*,
                   EXISTS (
                       SELECT 1 FROM earth_nuclear_strikes ns
                       WHERE ns.war_id = w.id AND ns.source_country_id = w.attacker_country_id
                         AND ns.target_country_id = w.defender_country_id
                   ) AS attacker_nuke_used,
                   EXISTS (
                       SELECT 1 FROM earth_nuclear_strikes ns
                       WHERE ns.war_id = w.id AND ns.source_country_id = w.defender_country_id
                         AND ns.target_country_id = w.attacker_country_id
                   ) AS defender_nuke_used,
                   ac.name as attacker_name, ac.flag as attacker_flag, ac.lat as atk_lat, ac.lng as atk_lng,
                   ac.tanks as attacker_tank_inventory, ac.jets as attacker_jet_inventory, ac.ships as attacker_ship_inventory, ac.population as attacker_population,
                   dc.name as defender_name, dc.flag as defender_flag, dc.lat as dfn_lat, dc.lng as dfn_lng,
                   dc.tanks as defender_tank_inventory, dc.jets as defender_jet_inventory, dc.ships as defender_ship_inventory, dc.population as defender_population
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

    async def launch_earth_nuclear_strike(self, user_id: int, source_country_id: int, war_id: int) -> tuple[bool, str]:
        """Consume one tactical nuke and damage the opposing country in an active war."""
        if self._db is None:
            await self.setup()
        if not await self.has_earth_cabinet_permission(user_id, source_country_id, "defense"):
            return False, "Only the President or Army Commander (Defense Minister) can launch a nuclear strike."

        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(
                "SELECT attacker_country_id, defender_country_id FROM earth_wars WHERE id = ? AND status = 'active'",
                (war_id,)
            ) as cur:
                war = await cur.fetchone()
            if not war or source_country_id not in (int(war[0]), int(war[1])):
                await self._db.rollback()
                return False, "Nuclear strikes can only be used by a country involved in an active war."

            target_country_id = int(war[1]) if source_country_id == int(war[0]) else int(war[0])
            async with self._db.execute(
                "SELECT 1 FROM earth_nuclear_strikes WHERE war_id = ? AND source_country_id = ? AND target_country_id = ? LIMIT 1",
                (war_id, source_country_id, target_country_id)
            ) as cur:
                if await cur.fetchone():
                    await self._db.rollback()
                    return False, "Each country can be struck only once per active war."
            async with self._db.execute(
                "SELECT owner_id FROM earth_countries WHERE id = ?", (source_country_id,)
            ) as cur:
                source = await cur.fetchone()
            async with self._db.execute(
                "SELECT owner_id, gdp FROM earth_countries WHERE id = ?", (target_country_id,)
            ) as cur:
                target = await cur.fetchone()
            if not source or not target or not source[0] or not target[0] or str(source[0]) == str(target[0]):
                await self._db.rollback()
                return False, "Nuclear strikes require two different ruled countries in an active war."

            async with self._db.execute(
                "SELECT 1 FROM earth_tools WHERE country_id = ? AND tool_key = 'nuclear_launch_pad'",
                (source_country_id,)
            ) as cur:
                if not await cur.fetchone():
                    await self._db.rollback()
                    return False, "A Nuclear Launch Pad is required before launching a tactical nuke."
            async with self._db.execute(
                "SELECT 1 FROM earth_tools WHERE country_id = ? AND tool_key = 'tactical_nuke'",
                (source_country_id,)
            ) as cur:
                if not await cur.fetchone():
                    await self._db.rollback()
                    return False, "This country has no tactical nuclear weapon ready to launch."

            damage = max(0, int((target[1] or 0) * 0.20))
            now = time.time()
            await self._db.execute(
                "DELETE FROM earth_tools WHERE country_id = ? AND tool_key = 'tactical_nuke'",
                (source_country_id,)
            )
            await self._db.execute("""
                UPDATE earth_countries
                SET gdp = max(0, gdp - ?), stability = max(0, stability - 20),
                    unrest = min(100, unrest + 25), population=max(0,population-max(1,population/20))
                WHERE id = ?
            """, (damage, target_country_id))
            await self._db.execute("""
                INSERT INTO earth_nuclear_strikes
                    (war_id, source_country_id, target_country_id, user_id, gdp_damage, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (war_id, source_country_id, target_country_id, int(user_id), damage, now))
            await self._db.commit()
            return True, f"Nuclear strike launched. {damage:,} GDP damage, -20 stability, +25 unrest. The one-use tactical weapon was consumed."
        except Exception:
            await self._db.rollback()
            raise

    async def hire_earth_divisions(self, user_id: int, country_id: int, divisions: int) -> tuple[bool, str]:
        """Recruit reserve divisions with a population-backed force cap."""
        if self._db is None:
            await self.setup()
        try:
            divisions = int(divisions)
        except (ValueError, TypeError):
            return False, "Division count must be a whole number."
        if not 1 <= divisions <= 20:
            return False, "Recruit between 1 and 20 divisions per order."
        if not await self.has_earth_cabinet_permission(user_id,country_id,"defense"):
            return False, "Only the President or Army Commander can recruit divisions."
        await self.get_global_economy(user_id)
        cost = divisions * 25000
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("SELECT population,army_divisions FROM earth_countries WHERE id=?",(country_id,)) as cur:
                c=await cur.fetchone()
            if not c:
                await self._db.rollback()
                return False,"Country not found."
            async with self._db.execute("SELECT COALESCE(SUM(attacker_divisions),0) FROM earth_wars WHERE status='active' AND attacker_country_id=?",(country_id,)) as cur:
                deployed=int((await cur.fetchone())[0] or 0)
            async with self._db.execute("SELECT COALESCE(SUM(defender_divisions),0) FROM earth_wars WHERE status='active' AND defender_country_id=?",(country_id,)) as cur:
                deployed+=int((await cur.fetchone())[0] or 0)
            population=max(0,int(c[0] or 0)); reserve=max(0,int(c[1] or 0)); capacity=population//5
            if reserve+deployed+divisions>capacity:
                await self._db.rollback()
                return False,f"Population supports {capacity} total divisions; {reserve+deployed} are already recruited or deployed."
            civilian_cost = divisions * 5
            if population <= civilian_cost:
                await self._db.rollback()
                return False, f"Recruiting {divisions} divisions requires {civilian_cost} civilians; the country must retain at least 1 civilian."
            async with self._db.execute("UPDATE global_economy SET medals=medals-? WHERE user_id=? AND medals>=?",(cost,user_id,cost)) as cur:
                if cur.rowcount != 1:
                    await self._db.rollback()
                    return False,f"Recruiting {divisions} divisions costs {cost:,} Medals from your wallet."
            await self._db.execute("UPDATE users SET medals=(SELECT medals FROM global_economy WHERE user_id=?) WHERE user_id=?",(user_id,user_id))
            await self._db.execute("UPDATE earth_countries SET army_divisions=army_divisions+?, population=population-? WHERE id=?",(divisions,civilian_cost,country_id))
            await self._db.execute("INSERT INTO earth_military_log(country_id,actor_id,action,unit_type,amount,created_at) VALUES (?,?,'recruited','division',?,?)",(country_id,user_id,divisions,time.time()))
            await self._db.commit()
            return True,f"Recruited {divisions} divisions for {cost:,} Medals. Population-backed force limit: {capacity}."
        except Exception:
            await self._db.rollback()
            raise

    async def purchase_earth_military_hardware(self, user_id: int, country_id: int, unit_type: str, amount: int = 1) -> tuple[bool, str]:
        """Procure additional tanks, jets, or ships, limited by population and coast access."""
        if self._db is None:
            await self.setup()
        specs={"tank":("tanks",200000,25),"jet":("jets",350000,50),"ship":("ships",300000,50)}
        if unit_type not in specs:
            return False,"Choose tank, jet, or ship."
        try:
            amount=int(amount)
        except (ValueError,TypeError):
            return False,"Unit count must be a whole number."
        if not 1<=amount<=10:
            return False,"Buy between 1 and 10 units per order."
        if not await self.has_earth_cabinet_permission(user_id,country_id,"defense"):
            return False,"Only the President or Army Commander can buy military hardware."
        await self.get_global_economy(user_id)
        column,unit_cost,pop_per_unit=specs[unit_type]
        cost=amount*unit_cost
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute(f"SELECT population,{column},is_coastal FROM earth_countries WHERE id=?",(country_id,)) as cur:
                c=await cur.fetchone()
            if not c:
                await self._db.rollback()
                return False,"Country not found."
            if unit_type=="ship" and not c[2]:
                await self._db.rollback()
                return False,"A landlocked country cannot procure ships."
            cap=max(1,int(c[0] or 0)//pop_per_unit)
            if int(c[1] or 0)+amount>cap:
                await self._db.rollback()
                return False,f"Population supports at most {cap} {unit_type}s; population must grow before expanding this force."
            async with self._db.execute("UPDATE global_economy SET medals=medals-? WHERE user_id=? AND medals>=?",(cost,user_id,cost)) as cur:
                if cur.rowcount != 1:
                    await self._db.rollback()
                    return False,f"This purchase costs {cost:,} Medals from your wallet."
            await self._db.execute("UPDATE users SET medals=(SELECT medals FROM global_economy WHERE user_id=?) WHERE user_id=?",(user_id,user_id))
            await self._db.execute(f"UPDATE earth_countries SET {column}={column}+? WHERE id=?",(amount,country_id))
            await self._db.execute("INSERT INTO earth_military_log(country_id,actor_id,action,unit_type,amount,created_at) VALUES (?,?,'purchased',?,?,?)",(country_id,user_id,unit_type,amount,time.time()))
            await self._db.commit()
            return True,f"Purchased {amount} {unit_type}{'s' if amount != 1 else ''} for {cost:,} Medals."
        except Exception:
            await self._db.rollback()
            raise

    async def deploy_earth_war_equipment(self, user_id: int, war_id: int, unit_type: str, amount: int, country_id: int | None = None) -> tuple[bool, str]:
        """Reserve additional owned hardware on a matching active front without creating units."""
        if self._db is None:
            await self.setup()
        unit_type = str(unit_type or "").strip().lower()
        unit_type = {"tanks": "tank", "jets": "jet", "ships": "ship"}.get(unit_type, unit_type)
        columns = {"tank": ("tanks", "land", 15), "jet": ("jets", "air", 25), "ship": ("ships", "naval", 25)}
        if unit_type not in columns:
            return False, "Choose tanks, jets, or ships."
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            return False, "Equipment count must be a whole number."
        if not 1 <= amount <= 50:
            return False, "Deploy between 1 and 50 vehicles per order."
        stock_column, domain, power_each = columns[unit_type]
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("SELECT * FROM earth_wars WHERE id=? AND status='active'", (war_id,)) as cur:
                row = await cur.fetchone()
            if not row:
                await self._db.rollback()
                return False, "Active war campaign not found."
            war = dict(row)
            if war.get("war_domain", "land") != domain:
                await self._db.rollback()
                return False, f"{unit_type.title()}s can only be deployed to {domain} campaigns."
            side = None
            selected_country_id = None
            candidates = (("attacker", int(war["attacker_country_id"])), ("defender", int(war["defender_country_id"])))
            if country_id is not None and int(country_id) > 0:
                candidates = tuple((candidate, cid) for candidate, cid in candidates if cid == int(country_id))
            for candidate, cid in candidates:
                if await self.has_earth_cabinet_permission(user_id, cid, "defense"):
                    side, selected_country_id = candidate, cid
                    break
            if not side:
                await self._db.rollback()
                return False, "Only a President or Army Commander in this war can deploy equipment."
            async with self._db.execute(f"SELECT {stock_column} FROM earth_countries WHERE id=?", (selected_country_id,)) as cur:
                row = await cur.fetchone()
            stock = int(row[0] or 0) if row else 0
            async with self._db.execute(
                f"SELECT COALESCE(SUM(CASE WHEN attacker_country_id=? THEN attacker_{stock_column} ELSE defender_{stock_column} END),0) FROM earth_wars WHERE status='active' AND (attacker_country_id=? OR defender_country_id=?)",
                (selected_country_id, selected_country_id, selected_country_id),
            ) as cur:
                reserved = int((await cur.fetchone())[0] or 0)
            available = stock - reserved
            if amount > available:
                await self._db.rollback()
                return False, f"Only {max(0, available)} {stock_column} are available to deploy."
            await self._db.execute(
                f"UPDATE earth_wars SET {side}_{stock_column}={side}_{stock_column}+?, {side}_power={side}_power+? WHERE id=?",
                (amount, amount * power_each, war_id),
            )
            await self._db.commit()
            return True, f"Deployed {amount} {unit_type}{'s' if amount != 1 else ''}; your national inventory is unchanged and these units are reserved at this front."
        except Exception:
            await self._db.rollback()
            raise

    async def reinforce_earth_war(self, user_id: int, war_id: int, divisions: int) -> tuple[bool, str]:
        """Move existing national reserve divisions to an active front."""
        if self._db is None:
            await self.setup()
        try:
            divisions=int(divisions)
        except (ValueError,TypeError):
            return False,"Division count must be a whole number."
        if not 1<=divisions<=50:
            return False,"Deploy between 1 and 50 divisions per order."
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("SELECT * FROM earth_wars WHERE id=? AND status='active'",(war_id,)) as cur:
                row=await cur.fetchone()
            if not row:
                await self._db.rollback()
                return False,"Active war campaign not found."
            war=dict(row)
            choice=None
            for side,cid in (("attacker",int(war["attacker_country_id"])),("defender",int(war["defender_country_id"]))):
                if await self.has_earth_cabinet_permission(user_id,cid,"defense"):
                    choice=(side,cid)
                    break
            if not choice:
                await self._db.rollback()
                return False,"Only a President or Army Commander of a country in this war can deploy troops."
            side,country_id=choice
            if war.get("war_domain", "land") != "land":
                await self._db.rollback()
                return False,"Division reinforcements are only available in land campaigns."
            async with self._db.execute("SELECT army_divisions FROM earth_countries WHERE id=?",(country_id,)) as cur:
                reserve=await cur.fetchone()
            available=int(reserve[0] or 0) if reserve else 0
            if available<divisions:
                await self._db.rollback()
                return False,f"Only {available} reserve divisions are ready. Recruit more from the Defense panel."
            col="attacker" if side=="attacker" else "defender"
            await self._db.execute("UPDATE earth_countries SET army_divisions=army_divisions-? WHERE id=?",(divisions,country_id))
            await self._db.execute(f"UPDATE earth_wars SET {col}_divisions={col}_divisions+?,{col}_power={col}_power+? WHERE id=?",(divisions,divisions*5,war_id))
            await self._db.commit()
            return True,f"Deployed {divisions} reserve divisions to the {col} front. No Medals were charged and no units were created."
        except Exception:
            await self._db.rollback()
            raise

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
            async with self._db.execute("SELECT owner_id FROM earth_countries WHERE id = ?", (w["defender_country_id"],)) as cur:
                defender_row = await cur.fetchone()
            async with self._db.execute("SELECT owner_id FROM earth_countries WHERE id = ?", (w["attacker_country_id"],)) as cur:
                attacker_row = await cur.fetchone()
            defender_owner = defender_row[0] if defender_row else None
            attacker_owner = attacker_row[0] if attacker_row else None
            if not defender_owner or not attacker_owner or defender_owner == attacker_owner:
                for country_id, divisions in ((w["attacker_country_id"], w["attacker_divisions"]), (w["defender_country_id"], w["defender_divisions"])):
                    await self._db.execute(
                        "UPDATE earth_countries SET army_divisions=MIN(MAX(0,population/5),army_divisions+?) WHERE id=?",
                        (max(0, int(divisions or 0)), country_id),
                    )
                await self._db.execute("UPDATE earth_wars SET status = 'cancelled' WHERE id = ?", (wid,))
                await self._db.commit()
                continue

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
                if w.get("war_domain", "land") == "land" and w.get("scale") in ("annexation", "world_war"):
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

            # Deployed hardware returns to inventory except for campaign attrition.
            attacker_won = status == "attacker_won"
            for unit in ("tanks", "jets", "ships"):
                for side, cid, won in (("attacker", w["attacker_country_id"], attacker_won), ("defender", w["defender_country_id"], not attacker_won)):
                    committed_units = int(w.get(f"{side}_{unit}", 0) or 0)
                    unit_losses = min(committed_units, int(committed_units * (0.10 if won else 0.35) + (0 if won else 0.999)))
                    if unit_losses:
                        await self._db.execute(f"UPDATE earth_countries SET {unit}=MAX(0,{unit}-?) WHERE id=?", (unit_losses, cid))
            # Return surviving formations and apply population losses after the campaign.
            for cid, committed, won in ((w["attacker_country_id"],int(w["attacker_divisions"] or 0),attacker_won),(w["defender_country_id"],int(w["defender_divisions"] or 0),not attacker_won)):
                losses = min(committed,max(1,int(committed*(0.12 if won else 0.32))) if committed else 0)
                survivors = max(0,committed-losses)
                civilians_lost = max(1,int(committed*(0.15 if won else 0.35))) if committed else 0
                await self._db.execute("""
                    UPDATE earth_countries
                    SET population=max(0,population-?),
                        army_divisions=MIN(army_divisions+?,max(0,(population-?)/5))
                    WHERE id=?
                """,(civilians_lost,survivors,civilians_lost,cid))
            await self._db.execute("UPDATE earth_wars SET status = ?, winner_country_id = ? WHERE id = ?", (status, winner_id, wid))
            await self._db.commit()
            concluded.append({"war_id": wid, "status": status, "winner_id": winner_id})

        return concluded

    # ─── Ocean Trade Routes & Bilateral Commerce ──────────────────────────────

    async def propose_trade_route(self, user_id: int, from_country_id: int, to_country_id: int) -> tuple[bool, str]:
        """Create one validated bilateral maritime route without duplicate or phantom endpoints."""
        if self._db is None:
            await self.setup()
        try:
            from_country_id, to_country_id = int(from_country_id), int(to_country_id)
        except (TypeError, ValueError):
            return False, "Invalid trade-route countries."
        if from_country_id == to_country_id:
            return False, "Cannot establish ocean trade with yourself!"

        can_trade = await self.has_earth_cabinet_permission(user_id, from_country_id, "diplomat")
        if not can_trade:
            can_trade = await self.has_earth_cabinet_permission(user_id, from_country_id, "economy")
        if not can_trade:
            return False, "⛔ Authorization Denied: Only the President, Chief Diplomat, or Finance Minister can sign Ocean Trade Treaties!"

        async with self._db.execute(
            "SELECT * FROM earth_countries WHERE id IN (?, ?)", (from_country_id, to_country_id)
        ) as cur:
            rows = {int(row["id"]): dict(row) for row in await cur.fetchall()}
        c_a, c_b = rows.get(from_country_id), rows.get(to_country_id)
        if not c_a or not c_b:
            return False, "Country not found."
        if c_a.get("owner_id") is None or c_b.get("owner_id") is None:
            return False, "Both endpoints must be sovereign countries with current rulers."
        if not c_a.get("is_coastal") or not c_b.get("is_coastal"):
            return False, "⛔ Maritime Access Required: Both countries must possess open oceanic coastlines."
        async with self._db.execute(
            "SELECT 1 FROM earth_buildings WHERE country_id IN (?, ?) AND building_type='naval_port' LIMIT 1",
            (from_country_id, to_country_id)
        ) as cur:
            if not await cur.fetchone():
                return False, "⚓ At least one endpoint must have a Deepwater Naval Port."
        c1, c2 = sorted((from_country_id, to_country_id))
        now = time.time()
        try:
            await self._db.execute(
                "INSERT INTO earth_trade_routes (country_a_id, country_b_id, status, daily_tariff, created_at) VALUES (?, ?, 'active', 85000, ?)",
                (c1, c2, now)
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            return False, "An active Ocean Trade Route already exists between these two countries."
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
        """Establish a coalition and debit the charter fee atomically."""
        if self._db is None:
            await self.setup()
        can_lead = await self.has_earth_cabinet_permission(user_id, country_id, "diplomat")
        if not can_lead:
            return False, "⛔ Authorization Denied: Only the President or Chief Diplomat can charter international coalitions!", 0
        name = " ".join(str(name).split())
        if len(name) < 3 or len(name) > 32:
            return False, "Alliance name must be between 3 and 32 characters.", 0
        cost = 500000
        econ = await self.get_global_economy(user_id)
        if econ.get("medals", 0) < cost:
            return False, f"Chartering a global alliance requires {cost:,} Medals.", 0
        now = time.time()
        try:
            await self._db.execute("BEGIN IMMEDIATE")
            async with self._db.execute("SELECT alliance_id FROM earth_countries WHERE id=? AND owner_id IS NOT NULL", (country_id,)) as cur:
                country = await cur.fetchone()
            if not country:
                await self._db.rollback()
                return False, "Country not found or no longer controlled by you.", 0
            if country[0]:
                await self._db.rollback()
                return False, "Your country is already in an alliance.", 0
            async with self._db.execute(
                "UPDATE global_economy SET medals=medals-? WHERE user_id=? AND medals>=?",
                (cost, user_id, cost)
            ) as cur:
                if cur.rowcount != 1:
                    await self._db.rollback()
                    return False, "Your wallet changed before the charter completed.", 0
            await self._db.execute("UPDATE users SET medals=(SELECT medals FROM global_economy WHERE user_id=?) WHERE user_id=?", (user_id, user_id))
            async with self._db.execute(
                "INSERT INTO earth_alliances (name, creator_country_id, banner_color, created_at) VALUES (?, ?, ?, ?)",
                (name, country_id, banner_color, now)
            ) as cur:
                alliance_id = cur.lastrowid
            await self._db.execute("UPDATE earth_countries SET alliance_id=? WHERE id=?", (alliance_id, country_id))
            await self._db.commit()
            return True, f"🌐 Treaty Established! Custom Coalition **'{name}'** officially chartered.", alliance_id
        except Exception as e:
            await self._db.rollback()
            return False, f"Alliance name already taken or invalid: {e}", 0

    async def join_earth_alliance(self, user_id: int, country_id: int, alliance_id: int) -> tuple[bool, str]:
        """Join an existing alliance directly when authorized; never overwrite membership."""
        if self._db is None:
            await self.setup()
        if not await self.has_earth_cabinet_permission(user_id, country_id, "diplomat"):
            return False, "⛔ Authorization Denied: Only the President or Chief Diplomat can sign alliance accession protocols!"
        async with self._db.execute("SELECT name FROM earth_alliances WHERE id=?", (alliance_id,)) as cur:
            alliance = await cur.fetchone()
        if not alliance:
            return False, "Coalition treaty not found."
        async with self._db.execute("SELECT alliance_id FROM earth_countries WHERE id=? AND owner_id IS NOT NULL", (country_id,)) as cur:
            country = await cur.fetchone()
        if not country:
            return False, "Country not found."
        if country[0] and int(country[0]) != int(alliance_id):
            return False, "Leave your current alliance before joining another."
        if country[0] == alliance_id:
            return False, "Your country is already in this alliance."
        await self._db.execute("UPDATE earth_countries SET alliance_id=? WHERE id=?", (alliance_id, country_id))
        await self._db.execute("UPDATE earth_alliance_requests SET status='cancelled' WHERE country_id=? AND status='pending'", (country_id,))
        await self._db.commit()
        return True, f"🤝 Acceded to **{alliance[0]}**! Your nation is now under collective defense guarantees."

    async def request_earth_alliance(self, user_id: int, country_id: int, alliance_id: int) -> tuple[bool, str]:
        if self._db is None:
            await self.setup()
        if not await self.has_earth_cabinet_permission(user_id, country_id, "diplomat"):
            return False, "Only the President or Chief Diplomat can send alliance requests."
        async with self._db.execute("SELECT alliance_id FROM earth_countries WHERE id=?", (country_id,)) as cur:
            country = await cur.fetchone()
        if not country:
            return False, "Country not found."
        if country[0]:
            return False, "Leave your current alliance before requesting another."
        async with self._db.execute("SELECT 1 FROM earth_alliances WHERE id=?", (alliance_id,)) as cur:
            if not await cur.fetchone():
                return False, "Alliance not found."
        await self._db.execute("UPDATE earth_alliance_requests SET status='cancelled' WHERE country_id=? AND status='pending'", (country_id,))
        try:
            await self._db.execute(
                "INSERT INTO earth_alliance_requests (alliance_id,country_id,requester_id,status,created_at) VALUES (?,?,?,'pending',?)",
                (alliance_id, country_id, user_id, time.time())
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            return False, "A request for this country is already pending."
        return True, "Alliance request sent to the coalition leader."

    async def get_earth_alliance_requests(self, user_id: int, country_id: int) -> list[dict]:
        if self._db is None:
            await self.setup()
        async with self._db.execute("""
            SELECT r.id, r.alliance_id, r.country_id, r.requester_id, r.created_at,
                   a.name AS alliance_name, c.name AS country_name, c.flag AS country_flag
            FROM earth_alliance_requests r
            JOIN earth_alliances a ON a.id=r.alliance_id
            JOIN earth_countries creator ON creator.id=a.creator_country_id
            JOIN earth_countries c ON c.id=r.country_id
            WHERE creator.owner_id=? AND r.status='pending'
            ORDER BY r.created_at DESC
        """, (user_id,)) as cur:
            return [dict(row) for row in await cur.fetchall()]

    async def respond_earth_alliance_request(self, user_id: int, request_id: int, accept: bool) -> tuple[bool, str]:
        if self._db is None:
            await self.setup()
        await self._db.execute("BEGIN IMMEDIATE")
        try:
            async with self._db.execute("""
                SELECT r.*, a.name, creator.owner_id AS leader_id, c.owner_id AS requester_owner, c.alliance_id AS current_alliance
                FROM earth_alliance_requests r
                JOIN earth_alliances a ON a.id=r.alliance_id
                JOIN earth_countries creator ON creator.id=a.creator_country_id
                JOIN earth_countries c ON c.id=r.country_id
                WHERE r.id=? AND r.status='pending'
            """, (request_id,)) as cur:
                row = await cur.fetchone()
            if not row or str(row["leader_id"]) != str(user_id):
                await self._db.rollback()
                return False, "Only the alliance leader can respond to this request."
            if accept and (row["requester_owner"] is None or row["current_alliance"] is not None):
                await self._db.execute("UPDATE earth_alliance_requests SET status='cancelled' WHERE id=?", (request_id,))
                await self._db.commit()
                return False, "This country is no longer eligible for alliance membership."
            status = "accepted" if accept else "rejected"
            await self._db.execute("UPDATE earth_alliance_requests SET status=? WHERE id=?", (status, request_id))
            if accept:
                await self._db.execute("UPDATE earth_countries SET alliance_id=? WHERE id=?", (row["alliance_id"], row["country_id"]))
                await self._db.execute("UPDATE earth_alliance_requests SET status='cancelled' WHERE country_id=? AND status='pending' AND id<>?", (row["country_id"], request_id))
            await self._db.commit()
            return True, ("Alliance request accepted." if accept else "Alliance request rejected.")
        except Exception:
            await self._db.rollback()
            raise

    async def leave_earth_alliance(self, user_id: int, country_id: int) -> tuple[bool, str]:
        """Withdraw from your current international coalition."""
        if self._db is None:
            await self.setup()
        if not await self.has_earth_cabinet_permission(user_id, country_id, "diplomat"):
            return False, "⛔ Authorization Denied: Only the President or Chief Diplomat can renounce alliance membership!"
        await self._db.execute("UPDATE earth_countries SET alliance_id=NULL WHERE id=?", (country_id,))
        await self._db.execute("UPDATE earth_alliance_requests SET status='cancelled' WHERE country_id=? AND status='pending'", (country_id,))
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
            gdp_growth = int(max(1000, country["gdp"]) * 0.0001 * capped_hours * stab_factor)
            # Organic civic treasury yield: based on tax rate & stability
            tax_rate = country.get("tax_rate", 10)
            treasury_gain = int(tax_rate * 250 * capped_hours * stab_factor)
            # Unrest cooling: -1 unrest per 3 hours of peace
            unrest_cool = min(10, int(capped_hours * 0.33))
            
            new_gdp = country["gdp"] + max(1, gdp_growth)
            new_treasury = country["treasury"] + treasury_gain
            new_unrest = max(0, country.get("unrest", 10) - unrest_cool)
            
            population = max(0, int(country.get("population", 100) or 0))
            pop_last = float(country.get("population_last_growth", 0) or 0)
            if pop_last <= 0:
                pop_last = float(country.get("created_at", now) or now)
            population_tick = pop_last
            if now - pop_last >= 86400:
                days = min(30, int((now - pop_last) // 86400))
                population = min(1_000_000, population + max(1, int(population * 0.02 * days)))
                population_tick = pop_last + days * 86400
            await self._db.execute("""
                UPDATE earth_countries
                SET gdp = ?, treasury = ?, unrest = ?, last_growth_tick = ?,
                    population = ?, population_last_growth = ?
                WHERE id = ?
            """, (new_gdp, new_treasury, new_unrest, now, population, population_tick, country["id"]))
            await self._db.commit()
            
            country["gdp"] = new_gdp
            country["treasury"] = new_treasury
            country["unrest"] = new_unrest
            country["last_growth_tick"] = now
            country["population"] = population
            country["population_last_growth"] = population_tick
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

        required_role = {
            "economy": "economy",
            "intelligence": "intelligence",
            "military": "defense",
            "defense": "defense",
            "superweapon": "defense",
        }.get(EARTH_ADVANCED_TOOLS[tool_key].get("category"), "defense")
        can_manage = await self.has_earth_cabinet_permission(user_id, country_id, required_role)
        if not can_manage:
            role_name = "Army Commander" if required_role == "defense" else f"Minister of {required_role.title()}"
            return False, f"Authorization denied: the President or {role_name} is required for this asset.", {}

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
        
        await self._db.execute("INSERT INTO earth_military_log(country_id,actor_id,action,unit_type,amount,created_at) VALUES (?,? ,'purchased',?,1,?)", (country_id,user_id,tool_key,now))
        
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
