import os
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
                "phantom-regiment.onrender.com",
                "localhost:10000",
                "localhost",
                "127.0.0.1:10000",
                "127.0.0.1"
            }
            host = parsed.netloc.lower()
            if host not in allowed_hosts and not host.endswith(".onrender.com"):
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
        return redirect(url_for("views.verify"))

    cfg = get_oauth_config()
    token_data = {
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg["redirect_uri"]
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        token_res = requests.post(f"{DISCORD_API}/oauth2/token", data=token_data, headers=headers, timeout=10)
        token_json = token_res.json()
        access_token = token_json.get("access_token")
        if not access_token:
            return redirect(url_for("views.verify"))

        # Fetch user info
        user_headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(f"{DISCORD_API}/users/@me", headers=user_headers, timeout=10)
        user_info = user_res.json()
        user_id = int(user_info["id"])
        username = user_info.get("username", "Unknown")
        global_name = user_info.get("global_name") or username
        avatar_hash = user_info.get("avatar")

        if avatar_hash:
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size=128"
        else:
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{(user_id >> 22) % 6}.png"

        # Attempt to auto-add user to the Phantom Regiment server if not present
        if cfg["bot_token"] and cfg["guild_id"]:
            try:
                join_url = f"{DISCORD_API}/guilds/{cfg['guild_id']}/members/{user_id}"
                bot_headers = {
                    "Authorization": f"Bot {cfg['bot_token']}",
                    "Content-Type": "application/json"
                }
                requests.put(join_url, headers=bot_headers, json={"access_token": access_token}, timeout=5)
            except Exception as e:
                print(f"[OAuth2 Guild Join] Note: {e}")

        # Persist OAuth tokens to database for Anti-Raid Server Member Recovery
        try:
            db = current_app.config.get("DB")
            if db:
                from web.views import run_async
                refresh_token = token_json.get("refresh_token")
                expires_in = token_json.get("expires_in", 604800)
                run_async(db.save_oauth_member(user_id, username, access_token, refresh_token, expires_in))
        except Exception as e:
            print(f"[OAuth Member Backup] {e}")

        # Check Manager / Owner status from bot guild
        bot = current_app.config.get("DISCORD_BOT")
        is_owner = False
        is_manager = False

        if bot:
            guild = bot.get_guild(cfg["guild_id"])
            if not guild and bot.guilds:
                guild = bot.guilds[0]

            if guild:
                if guild.owner_id == user_id:
                    is_owner = True
                    is_manager = True
                else:
                    member = guild.get_member(user_id)
                    if member:
                        perms = member.guild_permissions
                        if perms.administrator or perms.manage_guild:
                            is_manager = True
                        role_names = {r.name.lower() for r in member.roles}
                        if "server manager" in role_names or "manager" in role_names:
                            is_manager = True

        session["user"] = {
            "id": user_id,
            "username": username,
            "global_name": global_name,
            "avatar": avatar_url,
            "is_owner": is_owner,
            "is_manager": is_manager
        }
        dest = get_clean_next(session.pop("next_url", None)) or url_for("views.index")
        return redirect(dest)

    except Exception as e:
        print(f"[OAuth2 Error] {e}")
        return redirect(url_for("views.verify"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("views.verify"))
