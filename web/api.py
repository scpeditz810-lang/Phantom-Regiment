import os

import json

import asyncio

import time

from datetime import datetime

from flask import Blueprint, jsonify, request, session, current_app

from web.auth import login_required, admin_required, mayor_required



api_bp = Blueprint("api", __name__, url_prefix="/api")



def run_async(coro):

    bot = current_app.config.get("DISCORD_BOT")

    if bot and bot.loop and bot.loop.is_running():

        future = asyncio.run_coroutine_threadsafe(coro, bot.loop)

        return future.result(timeout=10)



    try:

        loop = asyncio.get_running_loop()

    except RuntimeError:

        loop = None



    if loop and loop.is_running():

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:

            return pool.submit(lambda: asyncio.run(coro)).result(timeout=10)

    return asyncio.run(coro)



def get_db():

    return current_app.config["DB"]



@api_bp.route("/stocks")

def get_stocks():

    db = get_db()

    stocks = run_async(db.get_all_stocks())

    result = []

    for s in stocks:

        history = run_async(db.get_stock_history(s["id"], limit=15))

        first_price = history[0]["price"] if history else s["price"]

        current_price = s["price"]

        diff = current_price - first_price

        pct = round((diff / first_price) * 100, 2) if first_price > 0 else 0.0



        item = dict(s)

        item["change_pct"] = pct

        item["change_diff"] = diff

        item["is_up"] = diff >= 0

        item["dividend_yield_pct"] = 0.4

        item["dividend_per_share"] = max(1, int(round(s["price"] * 0.004)))

        engine = current_app.config.get("STOCK_ENGINE")

        item["market_news"] = engine.latest_news if engine and hasattr(engine, "latest_news") else "Market operating at normal liquidity."

        item["market_regime"] = engine.market_regime if engine and hasattr(engine, "market_regime") else "SIDEWAYS"

        item["regime_name"] = engine.get_regime_display_name() if engine and hasattr(engine, "get_regime_display_name") else "Sideways (Consolidation)"

        try:

            item["tax_rate_pct"] = int(round(run_async(db.get_stock_tax_rate()) * 100))

        except Exception:

            item["tax_rate_pct"] = 15

        result.append(item)

    return jsonify(result)



@api_bp.route("/stocks/<int:stock_id>/history")

def get_stock_history(stock_id):

    db = get_db()

    history = run_async(db.get_stock_history(stock_id, limit=30))

    labels = []

    prices = []

    for h in history:

        t = datetime.fromtimestamp(h["timestamp"]).strftime("%H:%M:%S")

        labels.append(t)

        prices.append(h["price"])

    return jsonify({"labels": labels, "prices": prices})



@api_bp.route("/companies/mine")

@login_required

def api_company_mine():

    db = get_db()

    company = run_async(db.get_player_company(session["user"]["id"]))

    return jsonify({"company": company})





@api_bp.route("/companies/create", methods=["POST"])

@login_required

def api_company_create():

    data = request.get_json() or {}

    try:

        valuation = int(data.get("valuation", 0))

        revenue = int(data.get("annual_revenue", 0))

        profit = int(data.get("annual_profit", 0))

        debt = int(data.get("debt", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Financial figures must be whole Medal amounts."}), 400



    db = get_db()

    success, message, company = run_async(db.create_player_company(

        session["user"]["id"],

        str(data.get("name", "")),

        str(data.get("symbol", "")),

        str(data.get("sector", "")),

        valuation,

        revenue,

        profit,

        debt,

        str(data.get("description", "")),

    ))

    return jsonify({"success": success, "message": message, "company": company}), 200 if success else 400





@api_bp.route("/companies/bank-balance")
@login_required
def api_company_bank_balance():
    db = get_db()
    balance = run_async(db.get_company_market_balance())
    tax_pct = int(round(run_async(db.get_stock_tax_rate()) * 100))
    return jsonify({"balance": balance, "tax_pct": tax_pct})


@api_bp.route("/companies/offers")
@login_required
def api_company_offers():
    offers = run_async(get_db().get_company_sale_offers(session["user"]["id"]))
    return jsonify({"offers": offers})


@api_bp.route("/companies/offers", methods=["POST"])
@login_required
def api_company_offer_create():
    data = request.get_json() or {}
    try:
        price = int(data.get("price", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Sale price must be a whole Medal amount."}), 400
    success, message, offer = run_async(get_db().create_company_sale_offer(
        session["user"]["id"], str(data.get("buyer_username", "")), price
    ))
    return jsonify({"success": success, "message": message, "offer": offer}), 200 if success else 400


@api_bp.route("/companies/offers/<int:offer_id>/accept", methods=["POST"])
@login_required
def api_company_offer_accept(offer_id):
    success, message = run_async(get_db().accept_company_sale_offer(session["user"]["id"], offer_id))
    return jsonify({"success": success, "message": message}), 200 if success else 400


@api_bp.route("/companies/offers/<int:offer_id>/reject", methods=["POST"])
@login_required
def api_company_offer_reject(offer_id):
    success, message = run_async(get_db().reject_company_sale_offer(session["user"]["id"], offer_id))
    return jsonify({"success": success, "message": message}), 200 if success else 400


@api_bp.route("/companies/sell-to-bank", methods=["POST"])
@login_required
def api_company_sell_to_bank():
    data = request.get_json() or {}
    try:
        price = int(data.get("price", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Sale price must be a whole Medal amount."}), 400
    success, message = run_async(get_db().sell_company_to_bank(session["user"]["id"], price))
    return jsonify({"success": success, "message": message}), 200 if success else 400


@api_bp.route("/portfolio")

@login_required

def get_portfolio():

    user_id = session["user"]["id"]

    db = get_db()

    holdings = run_async(db.get_user_stocks(user_id))

    total_invested = 0

    total_value = 0



    enriched = []

    for h in holdings:

        inv = round(h["shares"] * h["avg_buy_price"])

        val = h["shares"] * h["current_price"]

        total_invested += inv

        total_value += val

        item = dict(h)

        item["total_invested"] = inv

        item["current_value"] = val

        item["profit"] = val - inv

        item["profit_pct"] = round(((val - inv) / inv) * 100, 2) if inv > 0 else 0.0

        enriched.append(item)



    return jsonify({

        "holdings": enriched,

        "total_invested": total_invested,

        "total_value": total_value,

        "net_profit": total_value - total_invested

    })



_USER_LAST_STOCK_TRADE = {}



@api_bp.route("/buy", methods=["POST"])

@login_required

def buy_stock():

    user_id = session["user"]["id"]

    now = time.time()

    if now - _USER_LAST_STOCK_TRADE.get(user_id, 0) < 3.0:

        return jsonify({"success": False, "message": "Market rate limit: Please wait 3 seconds between orders."}), 429

    _USER_LAST_STOCK_TRADE[user_id] = now



    data = request.get_json() or {}

    stock_id = data.get("stock_id")

    try:

        shares = int(data.get("shares", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Shares must be a valid integer."}), 400



    if not stock_id or shares <= 0:

        return jsonify({"success": False, "message": "Invalid stock ID or share amount."}), 400



    db = get_db()

    success, message = run_async(db.buy_stock(user_id, stock_id, shares))

    if success:

        st = run_async(db.get_stock(stock_id))

        econ = run_async(db.get_global_economy(user_id))

        return jsonify({

            "success": True, 

            "message": message, 

            "new_price": st["price"] if st else None,

            "wallet": econ.get("medals", 0)

        }), 200

    return jsonify({"success": False, "message": message}), 400



@api_bp.route("/sell", methods=["POST"])

@login_required

def sell_stock():

    user_id = session["user"]["id"]

    now = time.time()

    if now - _USER_LAST_STOCK_TRADE.get(user_id, 0) < 3.0:

        return jsonify({"success": False, "message": "Market rate limit: Please wait 3 seconds between orders."}), 429

    _USER_LAST_STOCK_TRADE[user_id] = now



    data = request.get_json() or {}

    stock_id = data.get("stock_id")

    try:

        shares = int(data.get("shares", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Shares must be a valid integer."}), 400



    if not stock_id or shares <= 0:

        return jsonify({"success": False, "message": "Invalid stock ID or share amount."}), 400



    db = get_db()

    success, message = run_async(db.sell_stock(user_id, stock_id, shares))

    if success:

        st = run_async(db.get_stock(stock_id))

        econ = run_async(db.get_global_economy(user_id))

        return jsonify({

            "success": True, 

            "message": message, 

            "new_price": st["price"] if st else None,

            "wallet": econ.get("medals", 0)

        }), 200

    return jsonify({"success": False, "message": message}), 400



@api_bp.route("/bank/deposit", methods=["POST"])

@login_required

def bank_deposit():

    data = request.get_json() or {}

    try:

        amount = int(data.get("amount", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Amount must be a valid number."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, message = run_async(db.web_deposit_bank(user_id, amount))

    if success:

        econ = run_async(db.get_global_economy(user_id))

        bank = run_async(db.get_bank(user_id, 0))

        return jsonify({

            "success": True, 

            "message": message, 

            "wallet": econ.get("medals", 0),

            "vault": bank.get("balance", 0) if bank else 0

        }), 200

    return jsonify({"success": False, "message": message}), 400



@api_bp.route("/bank/withdraw", methods=["POST"])

@login_required

def bank_withdraw():

    data = request.get_json() or {}

    try:

        amount = int(data.get("amount", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Amount must be a valid number."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, message = run_async(db.web_withdraw_bank(user_id, amount))

    if success:

        econ = run_async(db.get_global_economy(user_id))

        bank = run_async(db.get_bank(user_id, 0))

        return jsonify({

            "success": True, 

            "message": message, 

            "wallet": econ.get("medals", 0),

            "vault": bank.get("balance", 0) if bank else 0

        }), 200

    return jsonify({"success": False, "message": message}), 400



# Persistent User Cache for fast, accurate Discord name/avatar resolution

_DISCORD_PROFILES = {

    1291083270426988544: ("Dark \u02e3", "https://cdn.discordapp.com/avatars/1291083270426988544/3b26c36587224cc73c82922822e783cf.png"),

    1162404296097275904: ("TS_Zenith", "https://cdn.discordapp.com/avatars/1162404296097275904/2c9b54fbf2e111c6c50b931579168f4b.png"),

    828513350883213342: ("AkSparkz", "https://cdn.discordapp.com/avatars/828513350883213342/ead6a2c4f0a8e2b3d44f46889144efa8.png"),

    895663524343345162: ("esel3169", "https://cdn.discordapp.com/embed/avatars/1.png"),

    1225651540312981586: ("Philip", "https://cdn.discordapp.com/embed/avatars/2.png"),

    1423907121229074452: ("mario", "https://cdn.discordapp.com/avatars/1423907121229074452/6cbe95a916e04fdfaa7f0210235b7504.png"),

    961431758262399046: ("KaijoDoma", "https://cdn.discordapp.com/avatars/961431758262399046/5202f51721a93a361931a805263e55ec.png"),

    1556111722165575752: ("mr_ya868", "https://cdn.discordapp.com/embed/avatars/3.png"),

    839916533534294037: ("Spector\u300a\u300b", "https://cdn.discordapp.com/embed/avatars/4.png"),

    754264189601710100: ("Ignite", "https://cdn.discordapp.com/avatars/754264189601710100/2cb61c16f9447ac28d16800d09ff7c89.png"),

}



# Load extra Discord profiles from discord_users.json

try:

    _users_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "discord_users.json")

    if not os.path.exists(_users_file):

        _users_file = "discord_users.json"

    if os.path.exists(_users_file):

        with open(_users_file, "r", encoding="utf-8") as _f:

            _dusers = json.load(_f)

            for _uid_str, _uinfo in _dusers.items():

                _uid_int = int(_uid_str)

                if _uid_int not in _DISCORD_PROFILES:

                    _dname = _uinfo.get("global_name") or _uinfo.get("username") or f"User {_uid_int}"

                    _uname = _uinfo.get("username") or ""

                    _display = f"{_dname} (@{_uname})" if _uname else _dname

                    _av = _uinfo.get("avatar") or "https://cdn.discordapp.com/embed/avatars/0.png"

                    _DISCORD_PROFILES[_uid_int] = (_display, _av)

except Exception as _e:

    pass



def _resolve_discord_user(uid, bot=None, db=None):

    if not uid:

        return "Unknown Citizen", "https://cdn.discordapp.com/embed/avatars/0.png"

    try:

        int_uid = int(uid)

    except (ValueError, TypeError):

        int_uid = uid



    if int_uid in _DISCORD_PROFILES:

        return _DISCORD_PROFILES[int_uid]



    # Known sovereign and army commander direct mapping

    if int_uid in (1162404296097275904, 1162404296097276000):

        _DISCORD_PROFILES[int_uid] = ("TS_Aryan", "https://www.roblox.com/headshot-thumbnail/image?userId=2673686693&width=150&height=150&format=png")

        return _DISCORD_PROFILES[int_uid]

    if int_uid in (429350468796416013, 429350468796416000):

        _DISCORD_PROFILES[int_uid] = ("Supreme Sovereign", "https://cdn.discordapp.com/embed/avatars/1.png")



    name = None

    avatar = "https://cdn.discordapp.com/embed/avatars/0.png"



    # 1. Discord Bot in-memory member/user cache

    if bot:

        user = bot.get_user(int_uid)

        if user:

            name = user.global_name or user.display_name or user.name

            avatar = user.display_avatar.url

            _DISCORD_PROFILES[int_uid] = (name, avatar)

            return _DISCORD_PROFILES[int_uid]

        for g in getattr(bot, "guilds", []):

            m = g.get_member(int_uid)

            if m:

                name = m.global_name or m.display_name or m.name

                avatar = m.display_avatar.url

                _DISCORD_PROFILES[int_uid] = (name, avatar)

                return _DISCORD_PROFILES[int_uid]



    # 2. Database lookup (Roblox Links with fuzzy snowflake tolerance & Cabinet table)

    if not db:

        try:

            db = current_app.config.get("DB")

        except Exception:

            db = None



    if db and getattr(db, "_db", None):

        try:

            # Check roblox_links with exact and fuzzy tolerance for JS float rounding

            async def _find_db_profile():

                async with db._db.execute("""

                    SELECT roblox_display, roblox_username, roblox_id 

                    FROM roblox_links 

                    WHERE user_id = ? OR (user_id BETWEEN ? - 250 AND ? + 250)

                    LIMIT 1

                """, (int_uid, int_uid, int_uid)) as cur:

                    r = await cur.fetchone()

                    if r:

                        disp, uname, rid = r[0], r[1], r[2]

                        dname = f"{disp} (@{uname})" if disp and uname and disp.lower() != uname.lower() else (disp or uname)

                        av = f"https://www.roblox.com/headshot-thumbnail/image?userId={rid}&width=150&height=150&format=png" if rid else avatar

                        return dname, av



                # Check earth_cabinet stored username

                async with db._db.execute("""

                    SELECT username FROM earth_cabinet 

                    WHERE (user_id = ? OR user_id BETWEEN ? - 250 AND ? + 250) AND username IS NOT NULL

                    LIMIT 1

                """, (int_uid, int_uid, int_uid)) as cur:

                    cr = await cur.fetchone()

                    if cr and cr[0]:

                        return cr[0], avatar



                # Check oauth_members

                async with db._db.execute("""

                    SELECT username FROM oauth_members 

                    WHERE user_id = ? OR (user_id BETWEEN ? - 250 AND ? + 250)

                    LIMIT 1

                """, (int_uid, int_uid, int_uid)) as cur:

                    om = await cur.fetchone()

                    if om and om[0]:

                        return om[0], avatar



                return None, avatar



            res_name, res_av = run_async(_find_db_profile())

            if res_name:

                _DISCORD_PROFILES[int_uid] = (res_name, res_av)

                return _DISCORD_PROFILES[int_uid]

        except Exception:

            pass



    # 3. Discord API fetch fallback

    if bot and hasattr(bot, "fetch_user"):

        try:

            user = run_async(bot.fetch_user(int_uid))

            if user:

                name = user.global_name or user.display_name or user.name

                avatar = user.display_avatar.url

                _DISCORD_PROFILES[int_uid] = (name, avatar)

                return _DISCORD_PROFILES[int_uid]

        except Exception:

            pass



    fallback_name = f"Citizen @{str(uid)}"

    return fallback_name, avatar



@api_bp.route("/squads")

def api_squads():

    bot = current_app.config.get("DISCORD_BOT")

    from web.views import get_pr_guild, get_squads_data

    guild = get_pr_guild()

    user = session.get("user")

    squads, active = get_squads_data(guild, bot, user)

    return jsonify({

        "squads": squads,

        "user_active_squad": active

    })



@api_bp.route("/leaderboards")

def get_leaderboards():

    db = get_db()

    bot = current_app.config.get("DISCORD_BOT")



    medals_raw = run_async(db.get_global_leaderboard(limit=10))

    gambling_raw = run_async(db.get_best_gamblers(limit=10))



    def resolve_user(uid):

        try:

            int_uid = int(uid)

        except (ValueError, TypeError):

            int_uid = uid

        if int_uid in _DISCORD_PROFILES:

            return _DISCORD_PROFILES[int_uid]

        name = f"User {uid}"

        avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

        if bot:

            user = bot.get_user(int_uid)

            if user:

                res = (user.global_name or user.display_name or user.name, user.display_avatar.url)

                _DISCORD_PROFILES[int_uid] = res

                return res

            for g in bot.guilds:

                m = g.get_member(int_uid)

                if m:

                    res = (m.global_name or m.display_name or m.name, m.display_avatar.url)

                    _DISCORD_PROFILES[int_uid] = res

                    return res

        return name, avatar



    medals_lb = []

    for i, u in enumerate(medals_raw, 1):

        name, avatar = resolve_user(u["user_id"])

        medals_lb.append({

            "rank": i,

            "user_id": u["user_id"],

            "name": name,

            "avatar": avatar,

            "medals": u.get("total_medals", 0)

        })



    gambling_lb = []

    for i, u in enumerate(gambling_raw, 1):

        name, avatar = resolve_user(u["user_id"])

        gambling_lb.append({

            "rank": i,

            "user_id": u["user_id"],

            "name": name,

            "avatar": avatar,

            "net_profit": u.get("net_profit", 0),

            "total_won": u.get("total_won", 0),

            "total_lost": u.get("total_lost", 0)

        })



    # Command an Army Combat Champions (Top 1, Top 2, Top 3 roles)

    ROLE_TOP_1 = 1560533558286745672

    ROLE_TOP_2 = 1560533684141035530

    ROLE_TOP_3 = 1560533774201266247



    combat_champions = {

        "top_1": [],

        "top_2": [],

        "top_3": []

    }



    if bot:

        try:

            from web.views import get_pr_guild

            guild = get_pr_guild()

            if guild:

                r1 = guild.get_role(ROLE_TOP_1)

                r2 = guild.get_role(ROLE_TOP_2)

                r3 = guild.get_role(ROLE_TOP_3)



                def format_member(m, rank_num):

                    name = m.global_name or m.display_name or m.name

                    pfp = m.display_avatar.url if hasattr(m, 'display_avatar') else (m.avatar.url if m.avatar else "https://cdn.discordapp.com/embed/avatars/0.png")

                    return {

                        "user_id": m.id,

                        "name": name,

                        "username": m.name,

                        "avatar": pfp,

                        "rank": rank_num

                    }



                if r1:

                    combat_champions["top_1"] = [format_member(m, 1) for m in r1.members]

                if r2:

                    combat_champions["top_2"] = [format_member(m, 2) for m in r2.members]

                if r3:

                    combat_champions["top_3"] = [format_member(m, 3) for m in r3.members]

        except Exception as e:

            pass



    return jsonify({

        "medals": medals_lb, 

        "gambling": gambling_lb,

        "combat_champions": combat_champions

    })



# ── Admin Only Endpoints ──────────────────────────────────────────────────────

@api_bp.route("/admin/stock/create", methods=["POST"])

@admin_required

def admin_create_stock():

    data = request.get_json() or {}

    symbol = data.get("symbol", "").strip()

    name = data.get("name", "").strip()

    try:

        price = int(data.get("price", 100))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Price must be a valid integer."}), 400



    description = data.get("description", "").strip()

    if not symbol or not name or price <= 0:

        return jsonify({"success": False, "message": "Symbol, name, and positive price required."}), 400



    db = get_db()

    created = run_async(db.create_stock(symbol, name, price, description))

    if created:

        return jsonify({"success": True, "message": f"Created stock {symbol.upper()} at {price:,} Medals!"})

    return jsonify({"success": False, "message": f"Stock with symbol {symbol.upper()} already exists."}), 400



@api_bp.route("/admin/stock/update_price", methods=["POST"])

@admin_required

def admin_update_stock_price():

    data = request.get_json() or {}

    stock_id = data.get("stock_id")

    try:

        new_price = int(data.get("new_price", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Price must be a valid number."}), 400



    if not stock_id or new_price <= 0:

        return jsonify({"success": False, "message": "Stock ID and positive price required."}), 400



    db = get_db()

    run_async(db.update_stock_price(stock_id, new_price))

    return jsonify({"success": True, "message": f"Updated stock price to {new_price:,} Medals!"})



@api_bp.route("/admin/stock/delete", methods=["POST"])

@admin_required

def admin_delete_stock():

    data = request.get_json() or {}

    stock_id = data.get("stock_id")

    if not stock_id:

        return jsonify({"success": False, "message": "Stock ID required."}), 400



    db = get_db()

    run_async(db.delete_stock(stock_id))

    return jsonify({"success": True, "message": "Stock delisted and active shareholders refunded."})



@api_bp.route("/admin/bank_passwords")

@admin_required

def admin_bank_passwords():

    # Sync from GitHub remote on refresh or periodic check if running locally

    force = request.args.get("force") in ("1", "true")

    try:

        from bot import backup

        if backup:

            backup.sync_from_remote(force=force)

    except Exception:

        pass



    db = get_db()

    bot = current_app.config.get("DISCORD_BOT")

    raw_banks = run_async(db.get_all_bank_passwords())



    result = []

    for b in raw_banks:

        uid = b["user_id"]

        name = f"User {uid}"

        avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

        if uid in _DISCORD_PROFILES:

            name, avatar = _DISCORD_PROFILES[uid]

        elif bot:

            u = bot.get_user(uid)

            if u:

                name = f"{u.display_name} (@{u.name})"

                avatar = u.display_avatar.url

            else:

                for g in bot.guilds:

                    m = g.get_member(uid)

                    if m:

                        name = f"{m.display_name} (@{m.name})"

                        avatar = m.display_avatar.url

                        break



        from utils.constants import BANK_TIERS

        tier_info = BANK_TIERS.get(b.get("tier", 1), {})

        tier_name = tier_info.get("name", f"Tier {b.get('tier', 1)}")



        date_str = datetime.fromtimestamp(b["created_at"]).strftime("%Y-%m-%d %H:%M") if b.get("created_at") else "N/A"



        result.append({

            "user_id": uid,

            "username": name,

            "avatar": avatar,

            "balance": b.get("balance", 0),

            "tier": b.get("tier", 1),

            "tier_name": tier_name,

            "password": b.get("password") or "(Password Not Set)",

            "created_at": date_str

        })

    resp = jsonify(result)

    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"

    resp.headers["Pragma"] = "no-cache"

    resp.headers["Expires"] = "0"

    return resp



@api_bp.route("/admin/bank_password/update", methods=["POST"])

@admin_required

def admin_update_bank_password():

    data = request.get_json() or {}

    user_id = data.get("user_id")

    new_password = str(data.get("password", "")).strip()



    if not user_id or not new_password:

        return jsonify({"success": False, "message": "User ID and new password are required."}), 400



    from utils.cipher import hash_password

    db = get_db()

    pw_hash = hash_password(new_password)

    run_async(db.set_bank_password(int(user_id), 0, pw_hash, new_password))



    try:

        from bot import backup

        if backup:

            backup.push_admin_update(f"Admin updated bank password for user {user_id}")

    except Exception:

        pass



    return jsonify({"success": True, "message": f"Bank password updated successfully for user {user_id}!"})





# ─── Virtual Earth API ────────────────────────────────────────────────────────



@api_bp.route("/admin/oauth_members")

@admin_required

def admin_oauth_members():

    db = get_db()

    members = run_async(db.get_all_oauth_members())

    return jsonify({

        "total": len(members),

        "members": [{"user_id": m["user_id"], "username": m.get("username", "Member"), "updated_at": m.get("updated_at", 0)} for m in members]

    })



@api_bp.route("/admin/restore_members", methods=["POST"])

@admin_required

def admin_restore_members():

    db = get_db()

    from web.auth import get_oauth_config, DISCORD_API

    import requests

    import time



    cfg = get_oauth_config()

    bot_token = cfg.get("bot_token")

    guild_id = cfg.get("guild_id")

    client_id = cfg.get("client_id")

    client_secret = cfg.get("client_secret")



    if not bot_token or not guild_id:

        return jsonify({"success": False, "message": "Bot token or Guild ID not configured."}), 400



    members = run_async(db.get_all_oauth_members())

    if not members:

        return jsonify({"success": False, "message": "No authorized members saved in database yet."}), 400



    now = time.time()

    restored = 0

    already_present = 0

    failed = 0



    bot_headers = {

        "Authorization": f"Bot {bot_token}",

        "Content-Type": "application/json"

    }



    for m in members:

        uid = m["user_id"]

        token = m.get("access_token")

        expires_at = m.get("expires_at", 0)

        refresh_tok = m.get("refresh_token")



        # Refresh token if expired

        if now >= (expires_at - 120) and refresh_tok and client_id and client_secret:

            try:

                refresh_payload = {

                    "client_id": client_id,

                    "client_secret": client_secret,

                    "grant_type": "refresh_token",

                    "refresh_token": refresh_tok

                }

                r_res = requests.post(f"{DISCORD_API}/oauth2/token", data=refresh_payload, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=5)

                if r_res.status_code == 200:

                    r_json = r_res.json()

                    token = r_json.get("access_token")

                    new_refresh = r_json.get("refresh_token", refresh_tok)

                    new_exp = r_json.get("expires_in", 604800)

                    run_async(db.save_oauth_member(uid, m.get("username", "Member"), token, new_refresh, new_exp))

            except Exception:

                pass



        if not token:

            failed += 1

            continue



        try:

            join_url = f"{DISCORD_API}/guilds/{guild_id}/members/{uid}"

            res = requests.put(join_url, headers=bot_headers, json={"access_token": token}, timeout=5)

            if res.status_code == 201:

                restored += 1

            elif res.status_code == 204:

                already_present += 1

            else:

                failed += 1

        except Exception:

            failed += 1



    return jsonify({

        "success": True,

        "message": f"Server Member Recovery Complete! Restored {restored} members back to server ({already_present} were already in server, {failed} could not be reached).",

        "restored": restored,

        "already_present": already_present,

        "failed": failed,

        "total": len(members)

    })





@api_bp.route("/admin/election/audit", methods=["GET"])

@admin_required

def admin_audit_election():

    db = get_db()

    from web.auth import get_oauth_config

    cfg = get_oauth_config()

    gid = cfg["guild_id"]

    active_ele = run_async(db.get_active_election(gid))

    if not active_ele:

        return jsonify({"success": False, "message": "No active election running."}), 400

    audit = run_async(db.audit_election_votes(active_ele["id"]))

    return jsonify({"success": True, "audit": audit})



@api_bp.route("/admin/election/purge_alts", methods=["POST"])

@admin_required

def admin_purge_election_alts():

    db = get_db()

    from web.auth import get_oauth_config

    cfg = get_oauth_config()

    gid = cfg["guild_id"]

    active_ele = run_async(db.get_active_election(gid))

    if not active_ele:

        return jsonify({"success": False, "message": "No active election running."}), 400

    audit = run_async(db.audit_election_votes(active_ele["id"]))

    flagged = audit.get("flagged_voters", [])

    if not flagged:

        return jsonify({"success": True, "message": "No alt votes detected to purge.", "purged_count": 0})

    flagged_ids = [f["voter_id"] for f in flagged]

    purged_count, removed_by_cand = run_async(db.purge_alt_votes(active_ele["id"], flagged_ids))

    return jsonify({

        "success": True,

        "message": f"Successfully purged {purged_count} alt votes!",

        "purged_count": purged_count,

        "removed_by_cand": removed_by_cand

    })



@api_bp.route("/admin/election/end", methods=["POST"])

@admin_required

def admin_end_election():

    db = get_db()

    bot = current_app.config.get("DISCORD_BOT")

    from web.auth import get_oauth_config

    cfg = get_oauth_config()

    gid = cfg["guild_id"]

    

    active_ele = run_async(db.get_active_election(gid))

    if not active_ele:

        return jsonify({"success": False, "message": "No active election currently running to end."}), 400



    elections_cog = bot.get_cog("ElectionsCog") if bot else None

    guild = bot.get_guild(gid) if bot else None



    if elections_cog and guild:

        success, winner_member, msg = run_async(elections_cog.conclude_election_for_guild(guild, active_ele))

        winner_name = winner_member.display_name if winner_member else "None"

    else:

        success, finished_ele, msg = run_async(db.conclude_election(active_ele["id"]))

        winner_name = f"Winner ID: {finished_ele.get('winner_id')}" if (finished_ele and finished_ele.get('winner_id')) else "None"



    if not success:

        return jsonify({"success": False, "message": msg}), 400



    return jsonify({

        "success": True,

        "message": f"Election concluded successfully! New Mayor declared: {winner_name}."

    })



# ── Mayor Executive Endpoints ──────────────────────────────────────────────

@api_bp.route("/mayor/stock/tax", methods=["POST"])

@mayor_required

def api_mayor_stock_tax():

    data = request.get_json() or {}

    try:

        tax_pct = int(data.get("tax_pct", 15))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid tax percentage."}), 400



    if tax_pct < 0 or tax_pct > 50:

        return jsonify({"success": False, "message": "Tax rate must be between 0% and 50%."}), 400



    db = get_db()

    run_async(db.set_stock_tax_rate(tax_pct / 100.0))

    return jsonify({"success": True, "message": f"Global market transaction tax updated to {tax_pct}%."})



@api_bp.route("/mayor/stock/supply", methods=["POST"])

@mayor_required

def api_mayor_stock_supply():

    data = request.get_json() or {}

    symbol = str(data.get("symbol", "")).strip().upper()

    try:

        amount = int(data.get("amount", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid adjustment amount."}), 400



    if not symbol or amount == 0:

        return jsonify({"success": False, "message": "Symbol and non-zero amount required."}), 400



    db = get_db()

    success, msg, updated = run_async(db.adjust_stock_supply(symbol, amount))

    return jsonify({"success": success, "message": msg, "stock": updated}), 200 if success else 400



@api_bp.route("/mayor/stock/create", methods=["POST"])

@mayor_required

def api_mayor_stock_create():

    data = request.get_json() or {}

    symbol = str(data.get("symbol", "")).strip().upper()

    name = str(data.get("name", "")).strip()

    try:

        price = int(data.get("price", 100))

        supply = int(data.get("supply", 2500))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid price or supply."}), 400

    description = str(data.get("description", "")).strip()



    if not (2 <= len(symbol) <= 6 and symbol.isalnum()):

        return jsonify({"success": False, "message": "Symbol must be 2-6 alphanumeric chars."}), 400

    if not name:

        return jsonify({"success": False, "message": "Company name is required."}), 400



    db = get_db()

    created = run_async(db.create_stock(symbol, name, price, description, supply))

    if not created:

        return jsonify({"success": False, "message": f"Stock {symbol} already exists on the exchange."}), 400

    return jsonify({"success": True, "message": f"IPO successfully issued for {symbol} ({name}) at {price:,} Medals!"})



@api_bp.route("/mayor/company-aid", methods=["POST"])

@mayor_required

def api_mayor_company_aid():

    data = request.get_json() or {}

    try:

        company_id = int(data.get("company_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid company ID."}), 400

    success, message, company = run_async(get_db().grant_player_company_aid(

        session["user"]["id"], company_id

    ))

    return jsonify({"success": success, "message": message, "company": company}), 200 if success else 400





# ── Earth Defense Endpoints ──────────────────────────────────────────────────

@api_bp.route("/earth/countries")

def api_earth_countries():

    db = get_db()

    bot = current_app.config.get("DISCORD_BOT")

    countries = run_async(db.get_earth_countries())

    

    curr_user = session.get("user")

    user_id = int(curr_user["id"]) if curr_user and curr_user.get("id") and str(curr_user["id"]).isdigit() else None

    permissions = run_async(db.get_user_earth_permissions(user_id)) if user_id else {}

    

    enriched = []

    for c in countries:

        item = dict(c)

        owner_id = c.get("owner_id")

        if owner_id:

            name, av = _resolve_discord_user(owner_id, bot=bot, db=db)

            item["owner_name"] = name

            item["owner_avatar"] = av

        else:

            item["owner_name"] = "Sovereign State Trust (Unclaimed)"

            item["owner_avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"

            

        owner_key = str(owner_id) if owner_id is not None else None

        item["is_my_country"] = bool(user_id and owner_id and int(owner_id) == user_id)

        item["can_manage_economy"] = bool(owner_key and owner_key in permissions.get("economy", set()))

        item["can_command_defense"] = bool(owner_key and owner_key in permissions.get("defense", set()))

        item["can_manage_intelligence"] = bool(owner_key and owner_key in permissions.get("intelligence", set()))

        # Compatibility fields for legacy consumers

        item["x"] = int(round(c.get("lat", 0)))

        item["y"] = int(round(c.get("lng", 0)))

        item["current_value"] = c.get("gdp", 10000000)

        enriched.append(item)

        

    resp = jsonify(enriched)

    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"

    return resp



@api_bp.route("/earth/stats")

def api_earth_stats():

    db = get_db()

    countries = run_async(db.get_earth_countries())

    total_gdp = sum(c.get("gdp", 0) for c in countries)

    total_claimed = sum(1 for c in countries if c.get("owner_id"))

    

    from utils.constants import EARTH_BUILDINGS, EARTH_CABINET_ROLES, EARTH_WAR_SCALES, EARTH_DOCTRINES, EARTH_GOVERNMENTS, EARTH_SPY_MISSIONS

    

    user_stats = {

        "wallet": 0,

        "country": None,

        "role": None,

        "role_title": None,

        "uncollected_yield": 0

    }

    

    curr_user = session.get("user")

    if curr_user and curr_user.get("id"):

        raw_uid = curr_user["id"]

        uid = int(raw_uid) if str(raw_uid).isdigit() else raw_uid

        econ = run_async(db.get_global_economy(uid))

        user_c = run_async(db.get_user_earth_country(uid))

        user_stats["id"] = uid

        user_stats["wallet"] = econ.get("medals", 0)

        user_stats["pending_invites"] = run_async(db.get_user_pending_cabinet_invites(uid))

        if user_c:

            user_stats["country"] = user_c

            user_stats["role"] = user_c.get("user_role", "president")

            user_stats["role_title"] = user_c.get("role_title", "President")

            now = time.time()

            last_c = user_c.get("last_yield_claim", 0) or (now - 3600)

            elapsed = min(24.0, max(0.01, (now - last_c) / 3600.0))

            hourly = sum(b.get("hourly_yield", 0) for b in user_c.get("buildings", []))

            user_stats["uncollected_yield"] = int(round(hourly * elapsed))



    return jsonify({

        "total_countries": len(countries),

        "total_claimed": total_claimed,

        "total_global_gdp": total_gdp,

        "user": user_stats,

        "buildings_info": EARTH_BUILDINGS,

        "cabinet_roles": EARTH_CABINET_ROLES,

        "war_scales": EARTH_WAR_SCALES,

        "doctrines": EARTH_DOCTRINES,

        "governments": EARTH_GOVERNMENTS,

        "spy_missions": EARTH_SPY_MISSIONS

    })



@api_bp.route("/earth/country/<int:country_id>")

def api_earth_country_detail(country_id):

    db = get_db()

    bot = current_app.config.get("DISCORD_BOT")

    c = run_async(db.get_earth_country(country_id))

    if not c:

        return jsonify({"success": False, "message": "Country not found."}), 404

        

    if c.get("owner_id"):

        name, av = _resolve_discord_user(c["owner_id"], bot=bot, db=db)

        c["owner_name"] = name

        c["owner_avatar"] = av

    else:

        c["owner_name"] = "Sovereign State Trust (Unclaimed)"

        c["owner_avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"



    current_user = session.get("user")

    if current_user and current_user.get("id"):

        permissions = run_async(db.get_user_earth_permissions(current_user["id"]))

        owner_key = str(c.get("owner_id")) if c.get("owner_id") is not None else None

        c["can_manage_economy"] = bool(owner_key and owner_key in permissions["economy"])

        c["can_command_defense"] = bool(owner_key and owner_key in permissions["defense"])

        c["can_manage_intelligence"] = bool(owner_key and owner_key in permissions["intelligence"])



    # Enrich cabinet names and avatars

    if c.get("owner_id"):

        c["owner_id"] = str(c["owner_id"])



    if c.get("cabinet"):

        for r_key, r_info in c["cabinet"].items():

            cab_uid = r_info.get("user_id")

            if cab_uid:

                r_info["user_id"] = str(cab_uid)

                # Keep imperial inheritance notice if present

                if not r_info.get("is_imperial_inherit"):

                    cab_name, cab_av = _resolve_discord_user(cab_uid, bot=bot, db=db)

                    r_info["username"] = cab_name

                    if cab_av and not r_info.get("avatar"):

                        r_info["avatar"] = cab_av



    return jsonify(c)



@api_bp.route("/earth/buy", methods=["POST"])

@login_required

def api_earth_buy():

    data = request.get_json() or {}

    try:

        country_id = int(data["country_id"]) if data.get("country_id") is not None else None

        offer = max(0, int(data.get("offer", 0)))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.buy_earth_country(user_id, country_id, offer=offer))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": success,

        "message": msg,

        "wallet": econ.get("medals", 0)

    }), 200 if success else 400



@api_bp.route("/earth/custom_country", methods=["POST"])

@login_required

def api_earth_custom_country():

    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()

    flag = str(data.get("flag", "???")).strip() or "???"

    capital = str(data.get("capital", "Capital City")).strip() or "Capital City"

    desc = str(data.get("desc", "")).strip()

    replace_current = bool(data.get("replace_current", False))



    try:

        offer = max(0, int(data.get("offer", 0)))

    except (ValueError, TypeError):

        offer = 0



    lat = data.get("lat")

    lng = data.get("lng")

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



    user_id = session["user"]["id"]

    db = get_db()

    success, msg, country = run_async(db.create_custom_country(

        user_id=user_id,

        name=name,

        flag=flag,

        capital=capital,

        lat=lat,

        lng=lng,

        offered_medals=offer,

        desc=desc,

        replace_current=replace_current

    ))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": success,

        "message": msg,

        "country": country,

        "wallet": econ.get("medals", 0)

    }), 200 if success else 400



@api_bp.route("/earth/build", methods=["POST"])

@login_required

def api_earth_build():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        b_type = str(data.get("building_type", "")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg, cost = run_async(db.build_earth_infrastructure(user_id, country_id, b_type))

    econ = run_async(db.get_global_economy(user_id))

    updated_c = run_async(db.get_earth_country(country_id))

    return jsonify({

        "success": success,

        "message": msg,

        "cost": cost,

        "wallet": econ.get("medals", 0),

        "country": updated_c

    }), 200 if success else 400



@api_bp.route("/earth/cabinet/appoint", methods=["POST"])

@login_required

def api_earth_cabinet_appoint():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        role = str(data.get("role", "")).strip().lower()

        target_user_id = int(data.get("target_user_id", 0))

        target_username = str(data.get("target_username", "")).strip() or None

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg, res_data = run_async(db.appoint_earth_cabinet(user_id, country_id, role, target_user_id, target_username=target_username))

    cab = run_async(db.get_earth_cabinet(country_id))

    return jsonify({

        "success": success,

        "message": msg,

        "cabinet": cab,

        "pending": res_data.get("pending", False),

        "invite_id": res_data.get("invite_id")

    }), 200 if success else 400



@api_bp.route("/earth/cabinet/invites", methods=["GET"])

@login_required

def api_earth_cabinet_invites():

    user_id = session["user"]["id"]

    db = get_db()

    incoming = run_async(db.get_user_pending_cabinet_invites(user_id))

    outgoing = []

    user_c = run_async(db.get_user_earth_country(user_id))

    if user_c and user_c.get("user_role") == "president":

        outgoing = run_async(db.get_country_pending_cabinet_invites(user_c["id"]))

    return jsonify({

        "incoming": incoming,

        "outgoing": outgoing

    })



@api_bp.route("/earth/cabinet/invite/respond", methods=["POST"])

@login_required

def api_earth_cabinet_invite_respond():

    data = request.get_json() or {}

    try:

        invite_id = int(data.get("invite_id", 0))

        action = str(data.get("action", "")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters"}), 400



    if not invite_id or action not in ("accept", "decline"):

        return jsonify({"success": False, "message": "Please specify invite ID and action (accept or decline)."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.respond_earth_cabinet_invite(user_id, invite_id, accept=(action == "accept")))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/cabinet/invite/cancel", methods=["POST"])

@login_required

def api_earth_cabinet_invite_cancel():

    data = request.get_json() or {}

    try:

        invite_id = int(data.get("invite_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid invite ID"}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.cancel_earth_cabinet_invite(user_id, invite_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/cabinet/resign", methods=["POST"])

@login_required

def api_earth_cabinet_resign():

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.resign_earth_cabinet(user_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/cabinet/dismiss", methods=["POST"])

@login_required

def api_earth_cabinet_dismiss():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        role = str(data.get("role", "")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.dismiss_earth_cabinet(user_id, country_id, role))

    cab = run_async(db.get_earth_cabinet(country_id))

    return jsonify({

        "success": success,

        "message": msg,

        "cabinet": cab

    }), 200 if success else 400



@api_bp.route("/earth/policies", methods=["POST"])

@login_required

def api_earth_policies():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        economic = str(data.get("economic_doctrine", "free_market")).strip().lower()

        military = str(data.get("military_doctrine", "volunteer")).strip().lower()

        diplomatic = str(data.get("diplomatic_stance", "neutral")).strip().lower()

        government_type = str(data.get("government_type", "democracy")).strip().lower()

        tax_rate = int(data.get("tax_rate", 10))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.update_earth_policies(

        user_id, country_id, economic, military, diplomatic, tax_rate, government_type

    ))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/quell_unrest", methods=["POST"])

@login_required

def api_earth_quell_unrest():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        method = str(data.get("method", "relief")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.quell_earth_unrest(user_id, country_id, method))

    econ = run_async(db.get_global_economy(user_id))

    c = run_async(db.get_earth_country(country_id))

    return jsonify({

        "success": success,

        "message": msg,

        "wallet": econ.get("medals", 0),

        "stability": c.get("stability", 80) if c else 80,

        "unrest": c.get("unrest", 10) if c else 10

    }), 200 if success else 400



@api_bp.route("/earth/spy/recruit", methods=["POST"])

@login_required

def api_earth_spy_recruit():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        codename = str(data.get("codename", "Operative")).strip()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.recruit_earth_spy(user_id, country_id, codename))

    spies = run_async(db.get_earth_spies(country_id))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": success,

        "message": msg,

        "spies": spies,

        "wallet": econ.get("medals", 0)

    }), 200 if success else 400



@api_bp.route("/earth/spy/dispatch", methods=["POST"])

@login_required

def api_earth_spy_dispatch():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        spy_id = int(data.get("spy_id", 0))

        target_country_id = int(data.get("target_country_id", 0))

        mission = str(data.get("mission", "intel")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg, mission_data = run_async(db.dispatch_earth_spy(user_id, country_id, spy_id, target_country_id, mission))

    spies = run_async(db.get_earth_spies(country_id))

    return jsonify({

        "success": success,

        "message": msg,

        "mission_data": mission_data,

        "spies": spies

    }), 200 if success else 400



@api_bp.route("/earth/intel")

@login_required

def api_earth_intel():

    user_id = session["user"]["id"]

    db = get_db()

    user_c = run_async(db.get_user_earth_country(user_id))

    if not user_c:

        return jsonify([])

    intel = run_async(db.get_earth_intelligence(user_c["id"]))

    return jsonify(intel)



@api_bp.route("/earth/war/declare", methods=["POST"])

@login_required

def api_earth_war_declare():

    data = request.get_json() or {}

    try:

        attacker_country_id = int(data.get("attacker_country_id", 0))

        defender_country_id = int(data.get("defender_country_id", 0))

        scale = str(data.get("scale", "border")).strip().lower()
        domain = str(data.get("domain", "land")).strip().lower()
        equipment = int(data.get("equipment", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg, war_data = run_async(db.declare_earth_war(user_id, attacker_country_id, defender_country_id, scale, domain, equipment))

    return jsonify({

        "success": success,

        "message": msg,

        "war": war_data

    }), 200 if success else 400





@api_bp.route("/earth/war/deploy-equipment", methods=["POST"])
@login_required
def api_earth_war_deploy_equipment():
    data = request.get_json() or {}
    try:
        war_id = int(data.get("war_id", 0))
        amount = int(data.get("amount", 0))
        unit_type = str(data.get("unit_type", "")).strip().lower()
        country_id = int(data.get("country_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid equipment order."}), 400
    db = get_db()
    success, msg = run_async(db.deploy_earth_war_equipment(session["user"]["id"], war_id, unit_type, amount, country_id))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@api_bp.route("/earth/war/reinforce", methods=["POST"])

@login_required

def api_earth_war_reinforce():

    data = request.get_json() or {}

    try:

        war_id = int(data.get("war_id", 0))

        divisions = int(data.get("divisions", 5))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.reinforce_earth_war(user_id, war_id, divisions))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": success,

        "message": msg,

        "wallet": econ.get("medals", 0)

    }), 200 if success else 400



@api_bp.route("/earth/army/hire", methods=["POST"])
@login_required
def api_earth_army_hire():
    data = request.get_json() or {}
    try:
        country_id = int(data.get("country_id", 0))
        divisions = int(data.get("divisions", 1))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid recruitment order."}), 400
    db = get_db()
    success, msg = run_async(db.hire_earth_divisions(session["user"]["id"], country_id, divisions))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@api_bp.route("/earth/army/purchase", methods=["POST"])
@login_required
def api_earth_army_purchase():
    data = request.get_json() or {}
    try:
        country_id = int(data.get("country_id", 0))
        amount = int(data.get("amount", 1))
        unit_type = str(data.get("unit_type", "")).strip().lower()
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid equipment order."}), 400
    db = get_db()
    success, msg = run_async(db.purchase_earth_military_hardware(session["user"]["id"], country_id, unit_type, amount))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@api_bp.route("/earth/wars")

def api_earth_wars():

    db = get_db()

    wars = run_async(db.get_active_earth_wars())

    return jsonify(wars)



@api_bp.route("/earth/trade/propose", methods=["POST"])

@login_required

def api_earth_trade_propose():

    data = request.get_json() or {}

    try:

        from_country_id = int(data.get("from_country_id", 0))

        to_country_id = int(data.get("to_country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.propose_trade_route(user_id, from_country_id, to_country_id))

    routes = run_async(db.get_earth_trade_routes(from_country_id))

    return jsonify({

        "success": success,

        "message": msg,

        "routes": routes

    }), 200 if success else 400



@api_bp.route("/earth/trade/routes")

def api_earth_trade_routes():

    db = get_db()

    routes = run_async(db.get_earth_trade_routes())

    return jsonify(routes)



@api_bp.route("/earth/alliance/create", methods=["POST"])

@login_required

def api_earth_alliance_create():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        name = str(data.get("name", "")).strip()

        color = str(data.get("color", "#3b82f6")).strip()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg, al_id = run_async(db.create_earth_alliance(user_id, country_id, name, color))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": success,

        "message": msg,

        "alliance_id": al_id,

        "wallet": econ.get("medals", 0)

    }), 200 if success else 400



@api_bp.route("/earth/alliance/join", methods=["POST"])

@login_required

def api_earth_alliance_join():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        alliance_id = int(data.get("alliance_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.join_earth_alliance(user_id, country_id, alliance_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/alliance/request", methods=["POST"])
@login_required
def api_earth_alliance_request():
    data = request.get_json() or {}
    try:
        country_id, alliance_id = int(data.get("country_id", 0)), int(data.get("alliance_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid parameters."}), 400
    success, msg = run_async(get_db().request_earth_alliance(session["user"]["id"], country_id, alliance_id))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@api_bp.route("/earth/alliance/requests")
@login_required
def api_earth_alliance_requests():
    country_id = int((request.args.get("country_id") or 0))
    return jsonify(run_async(get_db().get_earth_alliance_requests(session["user"]["id"], country_id)))


@api_bp.route("/earth/alliance/request/respond", methods=["POST"])
@login_required
def api_earth_alliance_request_respond():
    data = request.get_json() or {}
    try: request_id = int(data.get("request_id", 0))
    except (ValueError, TypeError): return jsonify({"success": False, "message": "Invalid request ID."}), 400
    accept = bool(data.get("accept", False))
    success, msg = run_async(get_db().respond_earth_alliance_request(session["user"]["id"], request_id, accept))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@api_bp.route("/earth/alliance/leave", methods=["POST"])

@login_required

def api_earth_alliance_leave():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.leave_earth_alliance(user_id, country_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/alliances")

def api_earth_alliances():

    db = get_db()

    alliances = run_async(db.get_earth_alliances())

    return jsonify(alliances)



@api_bp.route("/earth/collect_yield", methods=["POST"])

@login_required

def api_earth_collect_yield():

    user_id = session["user"]["id"]

    db = get_db()

    yield_amount, msg = run_async(db.collect_earth_yield(user_id))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": yield_amount > 0,

        "message": msg,

        "yield": yield_amount,

        "wallet": econ.get("medals", 0)

    }), 200 if yield_amount > 0 else 400





@api_bp.route("/earth/offer", methods=["POST"])

@login_required

def api_earth_offer():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        amount = max(0, int(data.get("amount", 0)))

        offer_scope = str(data.get("offer_scope", "state")).strip().lower()

        if offer_scope not in ("state", "whole_country", "empire"):

            offer_scope = "state"

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = int(session["user"]["id"]) if str(session["user"]["id"]).isdigit() else session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.create_country_offer(user_id, country_id, amount, offer_scope))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/offers")

@login_required

def api_earth_offers():

    user_id = session["user"]["id"]

    db = get_db()

    offers = run_async(db.get_country_offers(user_id))

    return jsonify(offers)



@api_bp.route("/earth/offer/accept", methods=["POST"])

@login_required

def api_earth_offer_accept():

    data = request.get_json() or {}

    try:

        offer_id = int(data.get("offer_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid Offer ID."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.accept_country_offer(user_id, offer_id))

    econ = run_async(db.get_global_economy(user_id))

    return jsonify({

        "success": success,

        "message": msg,

        "wallet": econ.get("medals", 0)

    }), 200 if success else 400



@api_bp.route("/earth/offer/reject", methods=["POST"])

@login_required

def api_earth_offer_reject():

    data = request.get_json() or {}

    try:

        offer_id = int(data.get("offer_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid Offer ID."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.reject_country_offer(user_id, offer_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/market_listing", methods=["POST"])

@login_required

def api_earth_market_listing():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        price_raw = data.get("price")

        price = int(price_raw) if price_raw is not None and str(price_raw).isdigit() else None

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400

        

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.set_country_market_price(user_id, country_id, price))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/members")

def api_earth_members():

    db = get_db()

    # Pull from both oauth_members and roblox_links to offer a rich directory

    async def _get_all_citizens():

        citizens = []

        seen = set()

        async with db._db.execute("SELECT user_id, username FROM oauth_members") as cur:

            for r in await cur.fetchall():

                uid_str = str(r[0])

                citizens.append({"user_id": uid_str, "username": r[1] or f"Member {uid_str[-4:]}"})

                seen.add(uid_str)

        async with db._db.execute("SELECT user_id, roblox_display, roblox_username FROM roblox_links") as cur:

            for r in await cur.fetchall():

                uid_str = str(r[0])

                if uid_str not in seen:

                    disp = r[1] or r[2] or f"Member {uid_str[-4:]}"

                    citizens.append({"user_id": uid_str, "username": disp})

                    seen.add(uid_str)

        return citizens



    try:

        result = run_async(_get_all_citizens())

    except Exception:

        result = []

    return jsonify(result)





@api_bp.route("/earth/join", methods=["POST"])

@login_required

def api_earth_join():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid Country ID."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.join_earth_country(user_id, country_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/leave", methods=["POST"])

@login_required

def api_earth_leave():

    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.leave_earth_country(user_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/citizens")

def api_earth_citizens():

    try:

        country_id = int(request.args.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify([]), 400

    db = get_db()

    citizens = run_async(db.get_earth_country_citizens(country_id))

    return jsonify(citizens)



@api_bp.route("/earth/captured_spies")

@login_required

def api_earth_captured_spies():

    try:

        country_id = int(request.args.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify([]), 400

    db = get_db()

    spies = run_async(db.get_captured_foreign_spies(country_id))

    return jsonify(spies)



@api_bp.route("/earth/spy/interrogate", methods=["POST"])

@login_required

def api_earth_spy_interrogate():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        spy_id = int(data.get("spy_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg, intel = run_async(db.interrogate_captured_spy(user_id, country_id, spy_id))

    return jsonify({"success": success, "message": msg, "intel": intel}), 200 if success else 400



@api_bp.route("/earth/spy/execute", methods=["POST"])

@login_required

def api_earth_spy_execute():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        spy_id = int(data.get("spy_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg = run_async(db.execute_captured_spy(user_id, country_id, spy_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/spy/train", methods=["POST"])

@login_required

def api_earth_spy_train():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        spy_id = int(data.get("spy_id", 0))

        target_level = int(data.get("target_level", 2))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg, res = run_async(db.train_earth_spy(user_id, country_id, spy_id, target_level))

    return jsonify({"success": success, "message": msg, "data": res}), 200 if success else 400



@api_bp.route("/earth/intel/buy", methods=["POST"])

@login_required

def api_earth_intel_buy():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        target_country_id = int(data.get("target_country_id", 0))

        intel_type = str(data.get("intel_type", "covert_history")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg, res = run_async(db.buy_earth_intel_dossier(user_id, country_id, target_country_id, intel_type))

    return jsonify({"success": success, "message": msg, "dossier": res}), 200 if success else 400



@api_bp.route("/earth/counter_sweep", methods=["POST"])

@login_required

def api_earth_counter_sweep():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid Country ID."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg, report = run_async(db.counter_intel_sweep(user_id, country_id))

    return jsonify({"success": success, "message": msg, "report": report}), 200 if success else 400





@api_bp.route("/earth/tools")

@login_required

def api_earth_tools():

    try:

        country_id = int(request.args.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"error": "Invalid country_id"}), 400



    from utils.constants import EARTH_ADVANCED_TOOLS

    db = get_db()

    owned_tools = run_async(db.get_country_tools(country_id))

    owned_keys = {t["tool_key"] for t in owned_tools}



    catalogue = []

    for key, val in EARTH_ADVANCED_TOOLS.items():

        catalogue.append({

            **val,

            "owned": key in owned_keys

        })



    return jsonify({

        "catalogue": catalogue,

        "owned": owned_tools

    })



@api_bp.route("/earth/tool/buy", methods=["POST"])

@login_required

def api_earth_tool_buy():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        tool_key = str(data.get("tool_key", "")).strip().lower()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    user_id = session["user"]["id"]

    db = get_db()

    success, msg, res = run_async(db.buy_country_tool(user_id, country_id, tool_key))

    return jsonify({

        "success": success,

        "message": msg,

        "result": res

    }), 200 if success else 400





@api_bp.route("/earth/nuclear/launch", methods=["POST"])

@login_required

def api_earth_nuclear_launch():

    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        war_id = int(data.get("war_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid country or war ID."}), 400

    success, message = run_async(get_db().launch_earth_nuclear_strike(

        session["user"]["id"], country_id, war_id

    ))

    return jsonify({"success": success, "message": message}), 200 if success else 400





# ═══════════════════════════════════════════════════════════════════════════════

# 🇺🇳 UNITED NATIONS (UN) & MAYOR GLOBAL PEACEKEEPING API

# ═══════════════════════════════════════════════════════════════════════════════



@api_bp.route("/earth/un/status")

def api_earth_un_status():

    db = get_db()

    bot = current_app.config.get("DISCORD_BOT")

    status = run_async(db.get_earth_un_status())

    mayor_uid = status.get("mayor_id")

    if mayor_uid:

        m_name, m_av = _resolve_discord_user(mayor_uid, bot=bot, db=db)

        status["mayor_name"] = m_name

        status["mayor_avatar"] = m_av

    else:

        status["mayor_name"] = "UN Security Council"

        status["mayor_avatar"] = "https://cdn.discordapp.com/embed/avatars/0.png"

    return jsonify(status)



@api_bp.route("/earth/un/ceasefire", methods=["POST"])

@login_required

def api_earth_un_ceasefire():

    from web.auth import is_current_mayor

    user_id = session["user"]["id"]

    if not is_current_mayor(user_id):

        return jsonify({"success": False, "message": "⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) or High Council can enforce international ceasefires."}), 403



    data = request.get_json() or {}

    try:

        war_id = int(data.get("war_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid War ID."}), 400



    db = get_db()

    success, msg, res = run_async(db.un_issue_ceasefire(user_id, war_id))

    return jsonify({"success": success, "message": msg, "data": res}), 200 if success else 400



@api_bp.route("/earth/un/sanction", methods=["POST"])

@login_required

def api_earth_un_sanction():

    from web.auth import is_current_mayor

    user_id = session["user"]["id"]

    if not is_current_mayor(user_id):

        return jsonify({"success": False, "message": "⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) can impose international sanctions."}), 403



    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

        reason = str(data.get("reason", "Breach of sovereign international stability accords")).strip()

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    db = get_db()

    success, msg = run_async(db.un_impose_sanctions(user_id, country_id, reason))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/un/lift_sanction", methods=["POST"])

@login_required

def api_earth_un_lift_sanction():

    from web.auth import is_current_mayor

    user_id = session["user"]["id"]

    if not is_current_mayor(user_id):

        return jsonify({"success": False, "message": "⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) can lift sanctions."}), 403



    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    db = get_db()

    success, msg = run_async(db.un_lift_sanctions(user_id, country_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400



@api_bp.route("/earth/un/aid", methods=["POST"])

@login_required

def api_earth_un_aid():

    from web.auth import is_current_mayor

    user_id = session["user"]["id"]

    if not is_current_mayor(user_id):

        return jsonify({"success": False, "message": "⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) can deploy UN Humanitarian Relief Grants."}), 403



    data = request.get_json() or {}

    try:

        country_id = int(data.get("country_id", 0))

    except (ValueError, TypeError):

        return jsonify({"success": False, "message": "Invalid parameters."}), 400



    db = get_db()

    success, msg = run_async(db.un_send_humanitarian_aid(user_id, country_id))

    return jsonify({"success": success, "message": msg}), 200 if success else 400

