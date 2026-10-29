import os
import asyncio
from flask import Flask, request, redirect, session, url_for, jsonify
from web.auth import auth_bp
from web.views import views_bp
from web.api import api_bp
from web.stock_engine import StockMarketEngine

def create_app(bot=None, db=None, loop=None):
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.secret_key = os.environ.get("SECRET_KEY", "phantom_regiment_secret_session_key_2026")

    app.config["DISCORD_BOT"] = bot
    app.config["DB"] = db
    # Keep the bot event loop explicit for Flask's synchronous worker thread.
    app.config["BOT_LOOP"] = loop
    app.config["DB_READY"] = getattr(bot, "web_db_ready", None) if bot else None
    app.config["BAN_CHECK"] = getattr(bot, "is_banned_from_original_pr", None) if bot else None

    # Context processors for all Jinja2 templates
    @app.context_processor
    def inject_global_data():
        user = session.get("user")
        user_is_mayor = False
        if user and user.get("id"):
            try:
                from web.auth import is_current_mayor
                user_is_mayor = bool(is_current_mayor(user["id"]))
                user["is_mayor"] = user_is_mayor
                session["user"] = user
            except Exception:
                user_is_mayor = bool(user.get("is_mayor"))
        return {
            "current_year": 2026,
            "bot_online": bool(bot and bot.is_ready()),
            "user_is_mayor": user_is_mayor
        }

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    @app.route("/ping")
    def ping():
        return "OK", 200

    _last_web_clean = 0

    @app.before_request
    def enforce_discord_verification():
        nonlocal _last_web_clean
        import time
        now = time.time()
        if now - _last_web_clean > 120:
            _last_web_clean = now
            try:
                from bot import emergency_disk_clean
                emergency_disk_clean()
            except Exception:
                pass

        path = request.path
        # Allow static files, ping, and favicon without authentication
        if path.startswith("/static/") or path == "/ping" or path == "/favicon.ico":
            return None

        exempt_endpoints = {
            "ping",
            "auth.login",
            "auth.callback",
            "auth.logout",
            "views.verify",
            "static"
        }
        if request.endpoint in exempt_endpoints or path in ["/login", "/callback", "/logout", "/verify"]:
            return None

        if "user" in session and session["user"].get("id"):
            try:
                from web.auth import is_current_mayor
                session["user"]["is_mayor"] = bool(is_current_mayor(session["user"]["id"]))
            except Exception:
                pass

        # If not verified via Discord OAuth, block access
        if "user" not in session:
            if path.startswith("/api/"):
                return {"error": "Discord OAuth verification required to access Phantom Regiment network", "status": 401, "verify_url": "/verify"}, 401

            next_target = request.full_path.rstrip("?") if request.query_string else request.path
            return redirect(url_for("views.verify", next=next_target))

        # Apply original Phantom Regiment bans to all existing web/API sessions.
        ban_check = app.config.get("BAN_CHECK")
        bot_loop = app.config.get("BOT_LOOP")
        user_id = session.get("user", {}).get("id")
        if ban_check and bot_loop and bot_loop.is_running() and user_id:
            try:
                banned = asyncio.run_coroutine_threadsafe(
                    ban_check(int(user_id)), bot_loop
                ).result(timeout=5)
            except Exception:
                banned = False
            if banned:
                session.clear()
                if path.startswith("/api/"):
                    return jsonify({"error": "You are banned from Phantom Regiment and cannot use this service."}), 403
                return "Access denied: you are banned from Phantom Regiment.", 403

    # Start stock market simulation engine
    if db:
        if loop is None and bot:
            try:
                loop = bot.loop
            except Exception:
                loop = None
        engine = StockMarketEngine(db, bot_loop=loop, tick_interval=25)
        engine.start()
        app.config["STOCK_ENGINE"] = engine

    return app
