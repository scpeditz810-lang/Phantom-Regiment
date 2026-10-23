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

    # 2. Database lookup (Roblox Link & OAuth Members)
    if not db:
        try:
            db = current_app.config.get("DB")
        except Exception:
            db = None

    if db:
        try:
            rlink = run_async(db.get_roblox_link(int_uid))
            if rlink:
                disp = rlink.get("roblox_display")
                uname = rlink.get("roblox_username")
                if disp and uname and disp.lower() != uname.lower():
                    name = f"{disp} (@{uname})"
                else:
                    name = disp or uname
                rid = rlink.get("roblox_id")
                if rid:
                    avatar = f"https://www.roblox.com/headshot-thumbnail/image?userId={rid}&width=150&height=150&format=png"
                if name:
                    _DISCORD_PROFILES[int_uid] = (name, avatar)
                    return _DISCORD_PROFILES[int_uid]
        except Exception:
            pass

        try:
            omember = run_async(db.get_oauth_member(int_uid))
            if omember and omember.get("username"):
                name = omember["username"]
                _DISCORD_PROFILES[int_uid] = (name, avatar)
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

    fallback_name = f"Commander {str(uid)[-4:]}"
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


# ─── E-State Virtual Real Estate & Tycoon API ─────────────────────────────────

@api_bp.route("/estate/plots")
def estate_plots():
    db = get_db()
    bot = current_app.config.get("DISCORD_BOT")
    plots = run_async(db.get_estate_plots())

    def resolve_user(uid):
        return _resolve_discord_user(uid, bot, db) if uid else (None, None)

    from utils.constants import ESTATE_BUILDINGS

    user_allies = set()
    user_pending_allies = set()
    curr_user = session.get("user")
    if curr_user and curr_user.get("id"):
        try:
            int_uid = int(curr_user["id"])
            user_allies = set(run_async(db.get_user_allies(int_uid)))
            raw_out = run_async(db.get_outgoing_alliance_requests(int_uid))
            user_pending_allies = {int(o["ally_id"]) for o in raw_out}
        except Exception:
            pass

    enriched = []
    for p in plots:
        item = dict(p)
        owner_name, owner_avatar = resolve_user(p.get("owner_id"))
        item["owner_name"] = owner_name or "Unclaimed (State Bank)"
        item["owner_avatar"] = owner_avatar or "https://cdn.discordapp.com/embed/avatars/0.png"
        b_type = p.get("building_type", "empty")
        b_info = ESTATE_BUILDINGS.get(b_type, {
            "name": "Vacant Land",
            "emoji": "🌱",
            "desc": "Unimproved natural terrain. Ready for tycoon development.",
            "daily_yield": 0.002
        })
        item["building_name"] = b_info["name"]
        item["building_emoji"] = b_info["emoji"]
        item["building_desc"] = b_info["desc"]
        
        owner_id = p.get("owner_id")
        int_owner = None
        if owner_id:
            try:
                int_owner = int(owner_id)
            except (ValueError, TypeError):
                int_owner = None
        item["is_allied"] = bool(int_owner and int_owner in user_allies)
        item["is_pending_ally"] = bool(int_owner and int_owner in user_pending_allies)
        enriched.append(item)

    resp = jsonify(enriched)
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    return resp

@api_bp.route("/estate/stats")
def estate_stats():
    db = get_db()
    plots = run_async(db.get_estate_plots())
    total_val = sum(p["current_value"] for p in plots)
    total_owned = sum(1 for p in plots if p.get("owner_id"))

    user_stats = {
        "plots_owned": 0,
        "total_valuation": 0,
        "accrued_yield": 0,
        "daily_yield": 0,
        "wallet": 0
    }

    user = session.get("user")
    if user:
        raw_uid = user.get("id")
        uid = int(raw_uid) if str(raw_uid).isdigit() else raw_uid
        u_stats = run_async(db.get_user_estate_stats(uid))
        econ = run_async(db.get_global_economy(uid))
        user_stats = u_stats
        user_stats["wallet"] = econ.get("medals", 0)

    from utils.constants import ESTATE_BUILDINGS
    return jsonify({
        "total_plots": len(plots),
        "total_owned": total_owned,
        "total_market_cap": total_val,
        "user": user_stats,
        "buildings_info": ESTATE_BUILDINGS
    })

@api_bp.route("/estate/buy", methods=["POST"])
@login_required
def estate_buy():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Plot ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.buy_estate_plot(user_id, plot_id))
    econ = run_async(db.get_global_economy(user_id))
    return jsonify({
        "success": success, 
        "message": msg,
        "wallet": econ.get("medals", 0)
    }), 200 if success else 400

@api_bp.route("/estate/upgrade", methods=["POST"])
@login_required
def estate_upgrade():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Plot ID."}), 400

    building_type = str(data.get("building_type", "")).strip().lower()
    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.upgrade_estate_plot(user_id, plot_id, building_type))
    econ = run_async(db.get_global_economy(user_id))
    plot = run_async(db.get_estate_plot(plot_id))
    return jsonify({
        "success": success,
        "message": msg,
        "wallet": econ.get("medals", 0),
        "new_value": plot.get("current_value") if plot else 0
    }), 200 if success else 400

@api_bp.route("/estate/sell_bank", methods=["POST"])
@login_required
def estate_sell_bank():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Plot ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg, payout = run_async(db.sell_estate_plot_to_bank(user_id, plot_id))
    econ = run_async(db.get_global_economy(user_id))
    return jsonify({
        "success": success,
        "message": msg,
        "payout": payout,
        "wallet": econ.get("medals", 0)
    }), 200 if success else 400

@api_bp.route("/estate/market_listing", methods=["POST"])
@login_required
def estate_market_listing():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
        price_raw = data.get("price")
        price = int(price_raw) if price_raw is not None and str(price_raw).isdigit() else None
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid parameters."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.set_estate_plot_market_price(user_id, plot_id, price))
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@api_bp.route("/estate/buy_market", methods=["POST"])
@login_required
def estate_buy_market():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Plot ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.buy_estate_plot_from_market(user_id, plot_id))
    econ = run_async(db.get_global_economy(user_id))
    return jsonify({
        "success": success,
        "message": msg,
        "error": msg if not success else None,
        "wallet": econ.get("medals", 0)
    }), 200 if success else 400

@api_bp.route("/estate/offer", methods=["POST"])
@login_required
def estate_offer():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
        amount = int(data.get("offer_amount", data.get("amount", 0)))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid parameters.", "error": "Invalid parameters."}), 400

    if plot_id <= 0 or amount <= 0:
        return jsonify({"success": False, "message": "Invalid Plot ID or offer amount.", "error": "Invalid Plot ID or offer amount."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.create_estate_offer(user_id, plot_id, amount))
    return jsonify({
        "success": success, 
        "message": msg,
        "error": msg if not success else None
    }), 200 if success else 400

@api_bp.route("/estate/offers")
@login_required
def estate_get_offers():
    user_id = session["user"]["id"]
    db = get_db()
    bot = current_app.config.get("DISCORD_BOT")
    offers = run_async(db.get_estate_offers(user_id=user_id))

    def resolve_name(uid):
        if not uid:
            return f"User {uid}"
        if uid in _DISCORD_PROFILES:
            return _DISCORD_PROFILES[uid][0]
        if bot:
            u = bot.get_user(uid)
            if u:
                return u.global_name or u.display_name or u.name
        return f"User {uid}"

    for o in offers:
        o["buyer_name"] = resolve_name(o.get("buyer_id"))
        o["seller_name"] = resolve_name(o.get("seller_id"))
        o["is_incoming"] = (o.get("seller_id") == user_id)
        amt = o.get("offer_amount", 0)
        o["tax_amount"] = int(round(amt * 0.30))
        o["seller_net"] = amt - o["tax_amount"]

    return jsonify(offers)

@api_bp.route("/estate/offer/accept", methods=["POST"])
@login_required
def estate_accept_offer():
    data = request.get_json() or {}
    try:
        offer_id = int(data.get("offer_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Offer ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.accept_estate_offer(user_id, offer_id))
    econ = run_async(db.get_global_economy(user_id))
    return jsonify({
        "success": success,
        "message": msg,
        "wallet": econ.get("medals", 0)
    }), 200 if success else 400

@api_bp.route("/estate/offer/reject", methods=["POST"])
@login_required
def estate_reject_offer():
    data = request.get_json() or {}
    try:
        offer_id = int(data.get("offer_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Offer ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.reject_estate_offer(user_id, offer_id))
    return jsonify({"success": success, "message": msg, "error": msg if not success else None}), 200 if success else 400

@api_bp.route("/estate/collect_yield", methods=["POST"])
@login_required
def estate_collect_yield():
    user_id = session["user"]["id"]
    db = get_db()
    total_yield, msg = run_async(db.collect_estate_yields(user_id))
    econ = run_async(db.get_global_economy(user_id))
    return jsonify({
        "success": total_yield > 0,
        "message": msg,
        "total_yield": total_yield,
        "wallet": econ.get("medals", 0)
    }), 200 if total_yield > 0 else 400


# ─── Anti-Raid Emergency Member Restore Endpoints ────────────────────────────

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
@api_bp.route("/mayor/plot/create", methods=["POST"])
@mayor_required
def api_mayor_create_plot():
    data = request.get_json() or {}
    name = str(data.get("name", "")).strip()
    district = str(data.get("district", "The Outskirts")).strip()
    terrain = str(data.get("terrain", "plains")).strip()
    try:
        price = int(data.get("price", 50000))
    except (ValueError, TypeError):
        price = 50000
    x = int(data["x"]) if data.get("x") is not None and str(data.get("x")).isdigit() else None
    y = int(data["y"]) if data.get("y") is not None and str(data.get("y")).isdigit() else None

    if not name:
        return jsonify({"success": False, "message": "Plot name is required."}), 400

    db = get_db()
    success, msg, new_plot = run_async(db.create_estate_plot(name, district, terrain, price, x, y))
    quota = run_async(db.get_mayor_weekly_zoning_quota())
    return jsonify({"success": success, "message": msg, "plot": new_plot, "quota": quota}), 200 if success else 400

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

# ── E-State Military Combat & Defense Endpoints ─────────────────────────────
@api_bp.route("/estate/attack", methods=["POST"])
@login_required
def api_estate_attack():
    data = request.get_json() or {}
    try:
        plot_id = int(data.get("plot_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Plot ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg, battle_data = run_async(db.attack_estate_plot(user_id, plot_id))
    econ = run_async(db.get_global_economy(user_id))

    # Dispatch Discord DM alert to defender
    bot = current_app.config.get("DISCORD_BOT")
    if bot and battle_data and battle_data.get("defender_id"):
        try:
            target_plot = run_async(db.get_estate_plot(plot_id))
            attacker_user = session.get("user", {})
            attacker_name = attacker_user.get("global_name") or attacker_user.get("username")
            if not attacker_name:
                attacker_name, _ = _resolve_discord_user(user_id, bot=bot, db=db)
            if target_plot:
                import asyncio
                from cogs.economy import send_raid_alert_dm
                asyncio.run_coroutine_threadsafe(
                    send_raid_alert_dm(bot, attacker_name, battle_data["defender_id"], target_plot, battle_data),
                    bot.loop
                )
        except Exception:
            pass

    has_battle = bool(battle_data and "attacker_roll" in battle_data)
    return jsonify({
        "success": success,
        "battle_initiated": has_battle,
        "message": msg,
        "battle": battle_data,
        "wallet": econ.get("medals", 0)
    }), 200 if (success or has_battle) else 400

@api_bp.route("/estate/active_battle", methods=["GET"])
def api_estate_active_battle():
    db = get_db()
    battle = run_async(db.get_active_estate_battle())
    if not battle:
        return jsonify({"active": False})

    bot = current_app.config.get("DISCORD_BOT")
    def resolve_user(uid):
        return _resolve_discord_user(uid, bot, db)

    atk_name, atk_avatar = resolve_user(battle.get("attacker_id"))
    def_name, def_avatar = resolve_user(battle.get("defender_id"))
    battle["attacker_name"] = atk_name
    battle["attacker_avatar"] = atk_avatar
    battle["defender_name"] = def_name
    battle["defender_avatar"] = def_avatar

    curr_user = session.get("user")
    user_id = str(curr_user.get("id")) if curr_user else None
    battle["is_my_attack"] = (user_id == str(battle.get("attacker_id")))
    battle["is_my_defense"] = (user_id == str(battle.get("defender_id")))

    return jsonify({
        "active": True,
        "battle": battle
    })

@api_bp.route("/estate/military", methods=["GET"])
@login_required
def api_estate_military():
    user_id = session["user"]["id"]
    db = get_db()
    bot = current_app.config.get("DISCORD_BOT")
    
    # 1. User military stats
    stats = run_async(db.get_user_military_stats(user_id))
    
    # 2. Active allies
    raw_allies = run_async(db.get_user_allies(user_id))
    allies = []
    for a_id in raw_allies:
        a_name, a_av = _resolve_discord_user(a_id, bot)
        a_stats = run_async(db.get_user_military_stats(a_id))
        allies.append({
            "user_id": a_id,
            "name": a_name,
            "avatar": a_av,
            "defense_power": a_stats.get("defense_power", 0),
            "attack_power": a_stats.get("attack_power", 0),
            "bases_count": len(a_stats.get("military_bases", [])),
            "defense_contribution": int(round(a_stats.get("defense_power", 0) * 0.35))
        })
        
    # 3. Pending incoming requests
    raw_pending = run_async(db.get_pending_alliance_requests(user_id))
    pending_requests = []
    for p in raw_pending:
        req_id = p["requester_id"]
        req_name, req_av = _resolve_discord_user(req_id, bot)
        req_stats = run_async(db.get_user_military_stats(req_id))
        pending_requests.append({
            "id": p["id"],
            "requester_id": req_id,
            "name": req_name,
            "avatar": req_av,
            "defense_power": req_stats.get("defense_power", 0),
            "created_at": p.get("created_at", 0)
        })

    # 4. Outgoing pending requests
    raw_outgoing = run_async(db.get_outgoing_alliance_requests(user_id))
    outgoing_requests = []
    for o in raw_outgoing:
        target_id = o["ally_id"]
        t_name, t_av = _resolve_discord_user(target_id, bot)
        outgoing_requests.append({
            "id": o["id"],
            "ally_id": target_id,
            "name": t_name,
            "avatar": t_av,
            "created_at": o.get("created_at", 0)
        })

    # 5. Raid targets (rival plots)
    plots = run_async(db.get_estate_plots())
    from utils.constants import ESTATE_BUILDINGS
    targets = []
    other_landowners = {}
    
    for p in plots:
        o_id = p.get("owner_id")
        if not o_id:
            continue
        if str(o_id) == str(user_id):
            continue
        
        o_name, o_av = _resolve_discord_user(o_id, bot)
        if o_id not in other_landowners:
            other_landowners[o_id] = {
                "user_id": o_id,
                "name": o_name,
                "avatar": o_av
            }
            
        # If allied, cannot attack
        if int(o_id) in raw_allies:
            continue
            
        b_type = p.get("building_type", "empty")
        b_info = ESTATE_BUILDINGS.get(b_type, {"name": "Vacant Land", "emoji": "🌱"})
        def_stats = run_async(db.get_plot_defense_stats(p["id"]))
        
        is_prot = p.get("is_protected", False)
        prot_left = p.get("protection_seconds_left", 0)
        
        targets.append({
            "id": p["id"],
            "name": p["name"],
            "district": p["district"],
            "terrain": p.get("terrain", "plains"),
            "owner_id": o_id,
            "owner_name": o_name,
            "owner_avatar": o_av,
            "building_type": b_type,
            "building_name": b_info.get("name", "Vacant Land"),
            "building_emoji": b_info.get("emoji", "🌱"),
            "building_level": p.get("building_level", 0),
            "current_value": p.get("current_value", 0),
            "accrued_yield": p.get("accrued_yield", 0),
            "defense_rating": def_stats.get("total_defense", 0),
            "is_protected": is_prot,
            "protection_seconds_left": prot_left,
            "can_attack": (len(stats.get("military_bases", [])) > 0) and (not is_prot)
        })

    # 6. Recent server-wide raids
    raw_raids = run_async(db.get_recent_raids(12))
    recent_raids = []
    for r in raw_raids:
        atk_name, atk_av = _resolve_discord_user(r["attacker_id"], bot, db)
        def_name, def_av = _resolve_discord_user(r["defender_id"], bot, db)
        recent_raids.append({
            "id": r["id"],
            "attacker_id": r["attacker_id"],
            "attacker_name": atk_name,
            "attacker_avatar": atk_av,
            "defender_id": r["defender_id"],
            "defender_name": def_name,
            "defender_avatar": def_av,
            "plot_id": r["plot_id"],
            "plot_name": r.get("plot_name", f"Plot #{r['plot_id']}"),
            "district": r.get("district", "City Territory"),
            "attacker_power": r["attacker_power"],
            "defender_power": r["defender_power"],
            "allied_bonus": r.get("allied_bonus", 0),
            "success": bool(r["success"]),
            "loot": r.get("loot", 0),
            "timestamp": r["timestamp"]
        })

    return jsonify({
        "stats": stats,
        "allies": allies,
        "pending_requests": pending_requests,
        "outgoing_requests": outgoing_requests,
        "targets": targets,
        "recent_raids": recent_raids,
        "other_landowners": list(other_landowners.values())
    })

@api_bp.route("/estate/ally/request", methods=["POST"])
@login_required
def api_estate_ally_request():
    data = request.get_json() or {}
    try:
        ally_id = int(data.get("ally_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Ally User ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.create_alliance_request(user_id, ally_id))
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@api_bp.route("/estate/ally/accept", methods=["POST"])
@login_required
def api_estate_ally_accept():
    data = request.get_json() or {}
    try:
        requester_id = int(data.get("requester_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Requester ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.accept_alliance(user_id, requester_id))
    return jsonify({"success": success, "message": msg}), 200 if success else 400
@api_bp.route("/estate/ally/decline", methods=["POST"])
@login_required
def api_estate_ally_decline():
    data = request.get_json() or {}
    try:
        requester_id = int(data.get("requester_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Requester ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.decline_alliance(user_id, requester_id))
    return jsonify({"success": success, "message": msg}), 200 if success else 400

@api_bp.route("/estate/ally/break", methods=["POST"])
@login_required
def api_estate_ally_break():
    data = request.get_json() or {}
    try:
        ally_id = int(data.get("ally_id", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid Ally ID."}), 400

    user_id = session["user"]["id"]
    db = get_db()
    success, msg = run_async(db.break_alliance(user_id, ally_id))
    return jsonify({"success": success, "message": msg}), 200 if success else 400
