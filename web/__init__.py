import os
from flask import Flask
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
