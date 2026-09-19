"""
Command an Army — Discord Bot
Main entry point: loads cogs, starts Flask keep-alive for Render,
restores DB from GitHub backup, and runs the 10-second auto-backup loop.
"""

import os
import asyncio
import threading

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from flask import Flask

from utils.database import Database
from utils.git_backup import GitBackup

load_dotenv()

# ── Flask keep-alive (UptimeRobot pings this) ──────────────────────────────────
web = Flask(__name__)

@web.route("/")
@web.route("/ping")
def ping():
    return "OK", 200

def _run_flask():
    port = int(os.environ.get("PORT", 10000))
    web.run(host="0.0.0.0", port=port, use_reloader=False)


# ── Git backup ─────────────────────────────────────────────────────────────────
backup = GitBackup("data/bot.db")


# ── Bot setup ──────────────────────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.db = Database("data/bot.db")


@tasks.loop(seconds=10)
async def backup_loop():
    """Push DB to GitHub every 10 seconds if it changed."""
    await asyncio.to_thread(backup.push_if_changed)


@bot.event
async def on_ready():
    await bot.db.setup()
    print(f"✅  {bot.user} is online!  (ID {bot.user.id})")

    # Start the backup loop
    if not backup_loop.is_running():
        backup_loop.start()

    try:
        synced = await bot.tree.sync()
        print(f"✅  Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌  Sync failed: {e}")


COGS = [
    "cogs.application",
    "cogs.leveling",
    "cogs.moderation",
    "cogs.setup",
    "cogs.economy",
    "cogs.gamenight",
]


async def main():
    # Restore DB from GitHub backup (runs before bot connects)
    backup.restore()

    # Start Flask in a daemon thread
    threading.Thread(target=_run_flask, daemon=True).start()

    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                print(f"✅  Loaded {cog}")
            except Exception as e:
                print(f"❌  Failed to load {cog}: {e}")

        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            print("❌  DISCORD_TOKEN not set!  Create a .env file (see .env.example).")
            return
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
