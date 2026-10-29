import os
import asyncio
import requests
from urllib.parse import urlparse
from functools import wraps
from flask import Blueprint, request, redirect, session, url_for, flash, current_app

auth_bp = Blueprint("auth", __name__)

DISCORD_API = "https://discord.com/api/v10"

def get_oauth_config():
    return {
        "client_id": os.environ.get("DISCORD_CLIENT_ID", ""),
        "client_secret": os.environ.get("DISCORD_CLIENT_SECRET", ""),
        "redirect_uri": os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:10000/callback"),
        "guild_id": int(os.environ.get("GUILD_ID", 1550544659217125467)),
        "bot_token": os.environ.get("DISCORD_TOKEN", "")
    }

def get_clean_next(target: str | None) -> str | None:
    """Safely sanitize and extract a relative path redirect target, preventing open redirects."""
    if not target:
        return None
    try:
        parsed = urlparse(target)
        # If absolute URL with netloc, ensure it's our own domain
        if parsed.netloc:
            allowed_hosts = {
                "phantomregiment.apps.bot-hosting.cloud",
                "phantom-regiment.onrender.com",
                "localhost:10000",
                "localhost",
                "127.0.0.1:10000",
                "127.0.0.1"
            }
            host = parsed.netloc.lower()
            if host not in allowed_hosts and not host.endswith(".onrender.com") and not host.endswith(".apps.bot-hosting.cloud"):
                return None

        path = parsed.path or ""
        if parsed.query:
            path += f"?{parsed.query}"
        if path.startswith("/") and not path.startswith("//") and path != "/verify":
            return path
    except Exception:
        pass
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            next_target = request.full_path.rstrip("?") if request.query_string else request.path
            return redirect(url_for("auth.login", next=next_target))
        return f(*args, **kwargs)
    return decorated_function

def is_current_mayor(user_id: int | str) -> bool:
    if not user_id:
        return False
    try:
        uid_int = int(user_id)
        uid_str = str(user_id)
    except (ValueError, TypeError):
        return False

    # 1. Check active session if available
    try:
        user_sess = session.get("user")
        if user_sess:
            if user_sess.get("is_owner"):
                return True
            roles = user_sess.get("roles") or []
            if any("mayor" in str(r).lower() or "🏛️" in str(r) for r in roles):
                return True
    except Exception:
        pass

    bot = current_app.config.get("DISCORD_BOT")
    db = current_app.config.get("DB")
    cfg = get_oauth_config()

    # 2. Check Discord Guild & Member roles directly
    if bot:
        guilds = []
        if cfg.get("guild_id"):
            g = bot.get_guild(cfg["guild_id"])
            if g:
                guilds.append(g)
        guilds.extend(bot.guilds or [])
        for guild in guilds:
            if not guild:
                continue
            if getattr(guild, "owner_id", None) == uid_int:
                return True
            member = guild.get_member(uid_int)
            if member and any("mayor" in r.name.lower() or "🏛️" in r.name for r in member.roles):
                return True

    # 3. Check Database elections
    if db:
        from web.views import run_async
        import time
        now = time.time()
        try:
            if run_async(db.is_user_current_mayor(uid_int)):
                return True
        except Exception:
            pass

        try:
            curr = run_async(db.get_current_commander(cfg["guild_id"]))
            if curr and str(curr.get("winner_id")) == uid_str:
                return True
            latest = run_async(db.get_latest_election(cfg["guild_id"]))
            if latest and str(latest.get("winner_id")) == uid_str:
                term_end = latest.get("term_end", 0) or 0
                if now < term_end:
                    return True
        except Exception:
            pass

    return False

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            next_target = request.full_path.rstrip("?") if request.query_string else request.path
            return redirect(url_for("auth.login", next=next_target))
        user = session["user"]
        if not (user.get("is_owner") or user.get("is_manager")):
            return redirect(url_for("views.unauthorized"))
        return f(*args, **kwargs)
    return decorated_function

def mayor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            next_target = request.full_path.rstrip("?") if request.query_string else request.path
            return redirect(url_for("auth.login", next=next_target))
        user_id = session["user"]["id"]
        if not is_current_mayor(user_id) and not session["user"].get("is_owner"):
            return redirect(url_for("views.unauthorized"))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route("/login")
def login():
    # Save redirect destination if provided and safe
    next_dest = get_clean_next(request.args.get("next"))
    if next_dest:
        session["next_url"] = next_dest

    cfg = get_oauth_config()
    if not cfg["client_id"]:
        # Fallback for dev mode when credentials aren't configured yet
        session["user"] = {
            "id": 1162404296097275904,
            "username": "DevCommander",
            "global_name": "Commander",
            "avatar": "https://cdn.discordapp.com/embed/avatars/0.png",
            "is_owner": True,
            "is_manager": True
        }
        dest = session.pop("next_url", None) or url_for("views.index")
        return redirect(dest)

    scope = "identify guilds guilds.join"
    discord_auth_url = (
        f"{DISCORD_API}/oauth2/authorize?client_id={cfg['client_id']}"
        f"&redirect_uri={requests.utils.quote(cfg['redirect_uri'], safe='')}"
        f"&response_type=code&scope={requests.utils.quote(scope, safe='')}"
    )
    return redirect(discord_auth_url)

@auth_bp.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        flash("Authorization failed or was cancelled.", "error")
        return redirect(url_for("views.index"))

    cfg = get_oauth_config()
    token_url = f"{DISCORD_API}/oauth2/token"
    data = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg["redirect_uri"]
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        token_resp = requests.post(token_url, data=data, headers=headers, timeout=10)
        token_data = token_resp.json()

        if "access_token" not in token_data:
            flash("Failed to obtain Discord token.", "error")
            return redirect(url_for("views.index"))

        access_token = token_data["access_token"]

        user_resp = requests.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        user_data = user_resp.json()
        user_id = int(user_data["id"])

        is_owner = False
        is_manager = False
        roles = []
        is_in_guild = False

        bot = current_app.config.get("DISCORD_BOT")
        if bot:
            guild = bot.get_guild(cfg["guild_id"]) or (bot.guilds[0] if bot.guilds else None)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    is_in_guild = True
                    is_owner = (guild.owner_id == user_id)
                    roles = [r.name for r in member.roles]
                    is_manager = is_owner or any(
                        r.name.lower() in ["manager", "admin", "administrator", "co-owner"]
                        or r.permissions.administrator
                        for r in member.roles
                    )

        if not is_in_guild and cfg["bot_token"]:
            join_url = f"{DISCORD_API}/guilds/{cfg['guild_id']}/members/{user_id}"
            join_headers = {
                "Authorization": f"Bot {cfg['bot_token']}",
                "Content-Type": "application/json"
            }
            try:
                requests.put(join_url, json={"access_token": access_token}, headers=join_headers, timeout=5)
            except Exception:
                pass

        is_mayor = is_current_mayor(user_id)
        session["user"] = {
            "id": user_id,
            "username": user_data.get("username", "Unknown"),
            "global_name": user_data.get("global_name") or user_data.get("username"),
            "avatar": (
                f"https://cdn.discordapp.com/avatars/{user_id}/{user_data['avatar']}.png"
                if user_data.get("avatar")
                else "https://cdn.discordapp.com/embed/avatars/0.png"
            ),
            "is_owner": is_owner,
            "is_manager": is_manager,
            "is_mayor": is_mayor,
            "roles": roles
        }

        flash(f"Welcome back, {session['user']['global_name']}!", "success")
        dest = session.pop("next_url", None) or url_for("views.index")
        return redirect(dest)

    except Exception as e:
        flash(f"Login failed: {str(e)}", "error")
        return redirect(url_for("views.index"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("views.index"))
