"""
Command an Army — Discord Bot
Main entry point: loads cogs, starts Flask keep-alive for Render,
restores DB from GitHub backup, and runs the 10-second auto-backup loop.
"""

import os
import asyncio
import threading
import logging

# Enable discord.py debug logging
logging.basicConfig(level=logging.INFO)

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
    try:
        await asyncio.to_thread(backup.push_if_changed)
    except Exception as e:
        print(f"⚠️ Backup loop encountered an error: {e}")


@bot.event
async def on_ready():
    await bot.db.setup()
    print(f"✅  {bot.user} is online!  (ID {bot.user.id})", flush=True)

    # Start the backup loop
    if not backup_loop.is_running():
        backup_loop.start()

    try:
        synced = await bot.tree.sync()
        print(f"✅  Synced {len(synced)} slash commands.", flush=True)
    except Exception as e:
        print(f"❌  Sync failed: {e}", flush=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f"❌ Slash command error in {interaction.command.name if interaction.command else 'Unknown'}: {error}")
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Internal error: {error}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Internal error: {error}", ephemeral=True)
    except:
        pass

@bot.command()
@commands.is_owner()
async def clearsync(ctx: commands.Context):
    """Remove duplicate guild-specific slash commands."""
    bot.tree.clear_commands(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send("🧹 Cleared duplicate server-specific commands! You may need to restart Discord (`Ctrl+R`) to see the changes.")

@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context):
    """Instantly sync slash commands to the current server (bypasses 1-hour global cache)."""
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Instantly synced {len(synced)} commands to this server!")


COGS = [
    "cogs.application",
    "cogs.leveling",
    "cogs.moderation",
    "cogs.setup",
    "cogs.economy",
    "cogs.gamenight",
    "cogs.strategy",
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
                print(f"✅  Loaded {cog}", flush=True)
            except Exception as e:
                print(f"❌  Failed to load {cog}: {e}", flush=True)

        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            print("❌  DISCORD_TOKEN not set!  Create a .env file (see .env.example).", flush=True)
            return
        await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
