import os
from flask import Flask, request, redirect, session, url_for
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

    # Context processors for all Jinja2 templates
    @app.context_processor
    def inject_global_data():
        return {
            "current_year": 2026,
            "bot_online": bool(bot and bot.is_ready())
        }

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)

    @app.route("/ping")
    def ping():
        return "OK", 200

    @app.before_request
    def enforce_discord_verification():
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

        # If not verified via Discord OAuth, block access
        if "user" not in session:
            if path.startswith("/api/"):
                return {"error": "Discord OAuth verification required to access Phantom Regiment network", "status": 401, "verify_url": "/verify"}, 401

            next_target = request.full_path.rstrip("?") if request.query_string else request.path
            return redirect(url_for("views.verify", next=next_target))

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
