"""
Phantom Regiment Tactical Advisor AI Module
Handles live market scanning, active war analysis, game mechanics explanations,
staff application guidance, all slash commands (economy, gambling, banking, earth, etc.),
and smart natural language responses with multi-tier free inference:
1. Pollinations AI Free Tier (openai-fast)
2. Built-in Deterministic Tactical Intelligence Engine (never fails, 100% uptime, 0 cost, instant)
"""

import os
import re
import json
import time
import requests
import urllib.parse
from datetime import datetime

class TacticalAdvisor:
    def __init__(self, db=None):
        self.db = db

    def get_market_data(self):
        """Extract live stock prices, trends, supply, and tax rates directly from SQLite or API."""
        stocks_info = []
        try:
            import sqlite3
            db_path = getattr(self.db, "db_path", "data/bot.db")
            if not os.path.exists(db_path):
                db_path = "bot.db"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, symbol, name, price, total_supply, available_shares FROM stocks ORDER BY price DESC")
            rows = cur.fetchall()
            for r in rows:
                sid = r["id"]
                cur.execute("SELECT price FROM stock_history WHERE stock_id = ? ORDER BY timestamp DESC LIMIT 2", (sid,))
                h_rows = cur.fetchall()
                change_str = "Stable"
                if len(h_rows) >= 2:
                    diff = h_rows[0][0] - h_rows[1][0]
                    if diff > 0:
                        change_str = f"+{diff:,} Medals"
                    elif diff < 0:
                        change_str = f"-{abs(diff):,} Medals"
                
                stocks_info.append({
                    "symbol": r["symbol"],
                    "name": r["name"],
                    "price": r["price"],
                    "total_supply": r["total_supply"],
                    "available_shares": r["available_shares"],
                    "trend": change_str
                })
            conn.close()
        except Exception as e:
            print(f"[Advisor] Error reading market data: {e}")
        return stocks_info

    def get_wars_data(self):
        """Extract active earth wars, domain, power, participants, and military hardware safely."""
        wars_info = []
        try:
            import sqlite3
            db_path = getattr(self.db, "db_path", "data/bot.db")
            if not os.path.exists(db_path):
                db_path = "bot.db"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("PRAGMA table_info(earth_wars)")
            col_names = set(c[1] for c in cur.fetchall())

            cur.execute("""
                SELECT w.*,
                       c1.name as atk_name, c1.flag as atk_flag,
                       c2.name as def_name, c2.flag as def_flag
                FROM earth_wars w
                LEFT JOIN earth_countries c1 ON w.attacker_country_id = c1.id
                LEFT JOIN earth_countries c2 ON w.defender_country_id = c2.id
                WHERE w.status = 'active'
                ORDER BY w.id DESC
            """)
            rows = cur.fetchall()
            for r in rows:
                domain = r["war_domain"] if "war_domain" in col_names and r["war_domain"] else "LAND"
                scale = r["scale"] if "scale" in col_names and r["scale"] else "border"
                atk_p = r["attacker_power"] if "attacker_power" in col_names and r["attacker_power"] is not None else 0
                def_p = r["defender_power"] if "defender_power" in col_names and r["defender_power"] is not None else 0

                wars_info.append({
                    "id": r["id"],
                    "attacker": r["atk_name"] or f"Country #{r['attacker_country_id']}",
                    "attacker_flag": r["atk_flag"] or "⚔️",
                    "defender": r["def_name"] or f"Country #{r['defender_country_id']}",
                    "defender_flag": r["def_flag"] or "🛡️",
                    "domain": str(domain).upper(),
                    "scale": str(scale),
                    "attacker_power": atk_p,
                    "defender_power": def_p,
                    "hardware": {
                        "atk_tanks": r["attacker_tanks"] if "attacker_tanks" in col_names else 0,
                        "def_tanks": r["defender_tanks"] if "defender_tanks" in col_names else 0,
                        "atk_jets": r["attacker_jets"] if "attacker_jets" in col_names else 0,
                        "def_jets": r["defender_jets"] if "defender_jets" in col_names else 0,
                        "atk_ships": r["attacker_ships"] if "attacker_ships" in col_names else 0,
                        "def_ships": r["defender_ships"] if "defender_ships" in col_names else 0,
                    }
                })
            conn.close()
        except Exception as e:
            print(f"[Advisor] Error reading wars data: {e}")
        return wars_info

    def generate_tactical_fallback(self, query: str, stocks: list, wars: list) -> str:
        """Deterministic military intelligence analyzer that guarantees an instant, high-grade response 24/7."""
        q_lower = query.lower()
        response_parts = []

        is_staff_query = any(w in q_lower for w in ["staff", "apply", "application", "mod", "moderator", "admin", "recruitment", "hire"])
        is_gamble_query = any(w in q_lower for w in ["gamble", "gambling", "coinflip", "blackjack", "roulette", "scratch", "bet", "fight", "rps", "lottery"])
        is_stock_query = any(w in q_lower for w in ["stock", "market", "trade", "price", "portfolio", "invest", "share", "prc", "tsc", "vng", "aero", "cryp"])
        is_war_query = any(w in q_lower for w in ["war", "battle", "conflict", "earth", "country", "attack", "defend", "jet", "tank", "ship", "invade", "military", "un"])
        is_help_query = any(w in q_lower for w in ["how", "what is", "help", "explain", "guide", "rule", "medal", "bank", "rob", "work", "daily", "commands", "cmd"])

        # 1. Staff Application Inquiry
        if is_staff_query:
            response_parts.append("🛡️ **How to Become Staff / Staff Applications**")
            response_parts.append("• **When Staff Applications Open:** Staff applications are released periodically by High Command using the command `/staffapplications`.")
            response_parts.append("• **How to Apply:** When opened in the announcements/applications channel, select your desired position from the dropdown:")
            response_parts.append("  1. **Server Staff:** Moderate chat channels, enforce rules, assist citizens.")
            response_parts.append("  2. **Recruitment Management:** Review new applicant entries, evaluate recruits, onboard members.")
            response_parts.append("  3. **Giveaways & Events Management:** Organize server tournaments, game nights, and community giveaways.")
            response_parts.append("• **The Interview Flow:** The bot sends you a private DM interview with custom questions (age, timezone, experience, scenarios). Your answers are automatically compiled and submitted to the Commanders & Reviewers in `#staff-app-review` for final decision.")
            response_parts.append("• **Pro-Tip:** Stay active, maintain a clean disciplinary record, and avoid rule infractions to increase your chances of being accepted!")

        # 2. Gambling Inquiry
        if is_gamble_query:
            if response_parts: response_parts.append("\n" + "─" * 32 + "\n")
            response_parts.append("🎲 **Gambling & High-Stakes Games Commands**")
            response_parts.append("• **`/coinflip <bet>`** — Flip a coin (Heads/Tails) against the bot. Double your medals on a win! (Max bet: 150,000 Medals).")
            response_parts.append("• **`/blackjack <bet>`** — Play Blackjack (21) against the dealer with Hit, Stand, and Double Down interactive buttons (Max bet: 150,000 Medals).")
            response_parts.append("• **`/roulette <bet> <bet_type>`** — Bet on `Red` (2x), `Black` (2x), `Even` (2x), `Odd` (2x), or high-risk `Green` (36x)! (Max bet: 150,000 Medals).")
            response_parts.append("• **`/scratch <tier>`** — Buy an interactive scratch-off lottery ticket (`bronze` 500M, `silver` 2.5kM, `gold` 10kM) for up to 10x jackpot multipliers!")
            response_parts.append(
                "• **`/fight <@opponent> <bet>`** — Challenge another citizen to a 1v1 PvP combat arena for wagered Medals (1 to 150,000)!\n"
                "  └ **How it works:**\n"
                "    1. Both players click **Equip Loadout** to select Weapons and Utilities (Armor, Medkit, Adrenaline) from their inventory (`/shop`).\n"
                "    2. Interactive combat begins where players take turns choosing **Attack** (deals weapon damage + critical hits) or **Use Potion** (restores health).\n"
                "    3. The last fighter standing claims the total wagered medal pot!"
            )
            response_parts.append("• **`/rps <@opponent> <bet>`** — High-stakes Rock-Paper-Scissors against another player for wagered medals.")

        # 3. Stock Market Inquiry
        if is_stock_query or (not is_war_query and not is_help_query and not is_staff_query and not is_gamble_query):
            if response_parts: response_parts.append("\n" + "─" * 32 + "\n")
            response_parts.append("📈 **Tactical Market Scan Report**")
            if stocks:
                top_stock = max(stocks, key=lambda s: s["price"])
                cheapest_stock = min(stocks, key=lambda s: s["price"])
                response_parts.append(f"• **Market Leader:** **{top_stock['name']} ({top_stock['symbol']})** trading at **{top_stock['price']:,} Medals** ({top_stock['trend']}).")
                response_parts.append(f"• **Entry Value Asset:** **{cheapest_stock['name']} ({cheapest_stock['symbol']})** currently at **{cheapest_stock['price']:,} Medals**.")
                response_parts.append("\n**Active Stock Ticker Board:**")
                for s in stocks[:6]:
                    response_parts.append(f"• `{s['symbol']}` — **{s['price']:,} Medals** | Avail: `{s['available_shares']}/{s['total_supply']}` | Trend: {s['trend']}")
                response_parts.append("\n💡 **Advisor Recommendation:** Hold high-value shares for recurring 0.4% passive dividend payouts. Monitor the Mayor's office for transaction tax adjustments (typically 15%).")
            else:
                response_parts.append("• No publicly traded equities found on the local exchange.")

        # 4. Wars Inquiry
        if is_war_query or (not is_stock_query and not is_help_query and not is_staff_query and not is_gamble_query):
            if response_parts: response_parts.append("\n" + "─" * 32 + "\n")
            response_parts.append("⚔️ **Global Virtual Earth Conflict Scan**")
            if wars:
                response_parts.append(f"• Detected **{len(wars)} active theater(s) of war** currently underway:")
                for w in wars[:5]:
                    hw = w["hardware"]
                    hw_details = []
                    if hw.get("atk_jets") or hw.get("def_jets"):
                        hw_details.append(f"✈️ Jets: {hw.get('atk_jets', 0)} vs {hw.get('def_jets', 0)}")
                    if hw.get("atk_tanks") or hw.get("def_tanks"):
                        hw_details.append(f"🛡️ Tanks: {hw.get('atk_tanks', 0)} vs {hw.get('def_tanks', 0)}")
                    if hw.get("atk_ships") or hw.get("def_ships"):
                        hw_details.append(f"⚓ Ships: {hw.get('atk_ships', 0)} vs {hw.get('def_ships', 0)}")
                    
                    hw_str = f" ({', '.join(hw_details)})" if hw_details else ""
                    response_parts.append(
                        f"• **{w['attacker_flag']} {w['attacker']}** vs **{w['defender_flag']} {w['defender']}**\n"
                        f"  └ Domain: `{w['domain']}` | Scale: `{w['scale']}` | Power: `{w['attacker_power']} vs {w['defender_power']}`{hw_str}"
                    )
                response_parts.append("\n🛡️ **Defense Advisory:** Coastal nations require deployed Naval Fleets. Deploy Jet Squadrons for air superiority or Tanks to defend territory borders against invading divisions.")
            else:
                response_parts.append("• **Current Geopolitical Status:** No active military war declarations detected. The global arena is operating under temporary peace or UN ceasefire resolutions.")

        # 5. General Portal & Commands Overview
        if is_help_query and not is_staff_query and not is_gamble_query:
            if response_parts: response_parts.append("\n" + "─" * 32 + "\n")
            response_parts.append("🎖️ **Phantom Regiment Operations & Mechanics Guide**")
            response_parts.append("• **Earning Medals:** `/daily` (daily streak), `/work` (4h), `/crime` (2h high-risk), `/scavenge` (45m), `/trivia` (30m quiz).")
            response_parts.append("• **Banking & Vaults:** `/bank create`, `/bank deposit`, `/bank withdraw`, `/bank balance`, `/bank upgrade` (10 vault tiers yielding up to 1M interest/day).")
            response_parts.append("• **Stock Market:** `/stocks` or the `/medals` web terminal to buy/sell shares and collect automated dividends.")
            response_parts.append("• **Virtual Earth:** `/earth view`, `/earth my_country`, buy hardware (jets/tanks/ships), appoint ministers, manage stability, and launch tactical wars.")
            response_parts.append("• **Mayor Office:** Democratic elections every 7 days. Regulates transaction taxes, manages market share supply, awards Key to the City, and pardons citizens.")

        return "\n".join(response_parts)

    def query_online_llm(self, user_query: str, stocks: list, wars: list) -> str | None:
        """Attempt free public AI inference. Returns None if timed out, ratelimited, or unavailable."""
        stock_summary = [f"{s['symbol']}: {s['price']:,} Medals ({s['trend']})" for s in stocks[:8]]
        war_summary = [f"{w['attacker']} vs {w['defender']} ({w['domain']} war, Power: {w['attacker_power']} vs {w['defender_power']})" for w in wars[:6]]

        sys_prompt = (
            "You are 'Phantom Tactical Advisor', the official in-game intelligence AI for Phantom Regiment.\n"
            "You possess complete mastery over the game: Economy, Gambling (/coinflip, /blackjack, /roulette, /scratch, /fight, /rps), "
            "Banking, Virtual Earth, Mayor commands (/mayor salary, tax, doublexp, stimulus, award, pardon, stock_supply), "
            "Elections, and Staff Applications (opened via /staffapplications with DM interviews for Server Staff, Recruitment, Events).\n"
            "Analyze live stocks and ongoing Virtual Earth wars accurately based on this verified data:\n\n"
            f"LIVE STOCKS:\n{chr(10).join(stock_summary) if stock_summary else 'No active stocks.'}\n\n"
            f"ACTIVE WARS:\n{chr(10).join(war_summary) if war_summary else 'No active wars.'}\n\n"
            "Keep answers concise, strategic, clear, military-themed, and formatted with markdown bullet points."
        )

        try:
            payload = {
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_query}
                ],
                "model": "openai-fast"
            }
            resp = requests.post(
                "https://text.pollinations.ai/",
                json=payload,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=5
            )
            if resp.status_code == 200 and resp.text and not "Free limit reached" in resp.text:
                return resp.text.strip()
        except Exception:
            pass

        return None

    def ask(self, user_query: str) -> dict:
        """Main entry point: scans market, scans wars, and produces the optimal AI answer."""
        start_time = time.time()
        stocks = self.get_market_data()
        wars = self.get_wars_data()

        # Try online LLM first
        ai_reply = self.query_online_llm(user_query, stocks, wars)
        source = "Free Public AI Core (Cloud LLM)"
        
        # If cloud LLM is rate-limited or slow, seamlessly fallback to instant tactical engine
        if not ai_reply:
            ai_reply = self.generate_tactical_fallback(user_query, stocks, wars)
            source = "Phantom Tactical Intelligence Engine (Local Fail-Safe)"

        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "success": True,
            "response": ai_reply,
            "source": source,
            "latency_ms": elapsed_ms,
            "active_wars_count": len(wars),
            "tracked_stocks_count": len(stocks)
        }

_advisor_instance = None

def get_advisor(db=None):
    global _advisor_instance
    if _advisor_instance is None:
        _advisor_instance = TacticalAdvisor(db=db)
    elif db and not _advisor_instance.db:
        _advisor_instance.db = db
    return _advisor_instance
