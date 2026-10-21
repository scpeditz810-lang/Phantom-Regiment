import os
import json
import asyncio
from datetime import datetime
from flask import Blueprint, jsonify, request, session, current_app
from web.auth import login_required, admin_required

api_bp = Blueprint("api", __name__, url_prefix="/api")

def run_async(coro):
    bot = current_app.config.get("DISCORD_BOT")
    if bot:
        try:
            loop = bot.loop
            if loop and loop.is_running():
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                return future.result(timeout=10)
        except Exception:
            pass

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

@api_bp.route("/buy", methods=["POST"])
@login_required
def buy_stock():
    data = request.get_json() or {}
    stock_id = data.get("stock_id")
    try:
        shares = int(data.get("shares", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Shares must be a valid integer."}), 400

    if not stock_id or shares <= 0:
        return jsonify({"success": False, "message": "Invalid stock ID or share amount."}), 400

    user_id = session["user"]["id"]
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
    data = request.get_json() or {}
    stock_id = data.get("stock_id")
    try:
        shares = int(data.get("shares", 0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Shares must be a valid integer."}), 400

    if not stock_id or shares <= 0:
        return jsonify({"success": False, "message": "Invalid stock ID or share amount."}), 400

    user_id = session["user"]["id"]
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

    return jsonify({"medals": medals_lb, "gambling": gambling_lb})

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
    return jsonify(result)
