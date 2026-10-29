"""

Command an Army — Discord Bot

Main entry point: loads cogs, starts Flask keep-alive for Render,

restores DB from GitHub backup, and runs the 10-second auto-backup loop.

"""



import os

import asyncio

import time

import threading

import logging
import sqlite3



# Enable discord.py debug logging

logging.basicConfig(level=logging.INFO)



import discord

from discord.ext import commands, tasks

from dotenv import load_dotenv

from web import create_app



from utils.database import Database

from utils.git_backup import GitBackup



load_dotenv()


def emergency_disk_clean():
    """Purge pip cache, orphaned packs, duplicate code trees, and test databases to reclaim disk space immediately."""
    try:
        import os, shutil, stat, subprocess
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, "data")

        # 1. Purge pip caches to free 50-150MB of downloaded wheels
        for cd in [os.path.expanduser("~/.cache"), os.path.join(base_dir, ".cache"), "/home/container/.cache", "/tmp"]:
            if os.path.isdir(cd):
                for item in os.listdir(cd):
                    p = os.path.join(cd, item)
                    try:
                        if os.path.isdir(p):
                            shutil.rmtree(p, ignore_errors=True)
                        else:
                            os.remove(p)
                    except Exception:
                        pass
        try:
            subprocess.run(["pip", "cache", "purge"], timeout=10, capture_output=True)
        except Exception:
            pass

        # 2. Remove duplicate code trees mistakenly cloned into data/
        for sub in ("assets", "cogs", "utils", "web", "__pycache__"):
            target = os.path.join(data_dir, sub)
            if os.path.isdir(target):
                try:
                    shutil.rmtree(target, ignore_errors=True)
                    print(f"🧹 [Disk Cleanup] Cleaned duplicate directory: {sub}", flush=True)
                except Exception:
                    pass

        # Remove redundant data/.git if main repository is present
        rogue_data_git = os.path.join(data_dir, ".git")
        if os.path.isdir(rogue_data_git) and os.path.isdir(os.path.join(base_dir, ".git")):
            try:
                shutil.rmtree(rogue_data_git, ignore_errors=True)
                print("🧹 [Disk Cleanup] Removed redundant data/.git", flush=True)
            except Exception:
                pass

        # 3. Remove orphaned tmp_pack_* files in all .git folders
        for git_candidate in (os.path.join(base_dir, ".git"), os.path.join(data_dir, ".git")):
            pack_dir = os.path.join(git_candidate, "objects", "pack")
            if os.path.exists(pack_dir):
                for f in os.listdir(pack_dir):
                    if f.startswith("tmp_pack"):
                        fp = os.path.join(pack_dir, f)
                        try:
                            os.chmod(fp, stat.S_IWRITE)
                            os.remove(fp)
                            print(f"🧹 [Disk Cleanup] Removed abandoned pack: {f}", flush=True)
                        except Exception:
                            pass

        # 4. Remove leftover test databases, salvage files, and temp files
        for root_scan in (base_dir, data_dir):
            if os.path.exists(root_scan):
                for f in os.listdir(root_scan):
                    if (
                        f.startswith("test_")
                        or f.endswith(".tmp")
                        or f.endswith(".recovery-candidate")
                        or f.endswith(".salvaged")
                        or f.endswith(".reindexed")
                    ):
                        fp = os.path.join(root_scan, f)
                        if os.path.isfile(fp):
                            try:
                                os.remove(fp)
                                print(f"🧹 [Disk Cleanup] Removed temporary file: {f}", flush=True)
                            except Exception:
                                pass

        # Remove redundant root database files if data/bot.db is present
        for db_name in ("bot.db", "bot_snapshot.db"):
            root_db = os.path.join(base_dir, db_name)
            if os.path.isfile(root_db) and os.path.isfile(os.path.join(data_dir, "bot.db")):
                try:
                    os.remove(root_db)
                    print(f"🧹 [Disk Cleanup] Removed redundant root {db_name}", flush=True)
                except Exception:
                    pass

        # 5. Prune git reflogs and repack loose objects in base_dir/.git
        if os.path.isdir(os.path.join(base_dir, ".git")):
            try:
                subprocess.run(["git", "reflog", "expire", "--expire=now", "--all"], cwd=base_dir, timeout=15, capture_output=True)
                subprocess.run(["git", "prune", "--expire=now"], cwd=base_dir, timeout=15, capture_output=True)
                subprocess.run(["git", "repack", "-a", "-d"], cwd=base_dir, timeout=30, capture_output=True)
                print("🧹 [Disk Cleanup] Repacked and pruned base_dir/.git", flush=True)
            except Exception as git_err:
                print(f"⚠️ [Disk Cleanup] Git repack/prune notice: {git_err}", flush=True)

        # 6. Auto-sync repository code from GitHub
        if os.path.isdir(os.path.join(base_dir, ".git")):
            token = os.environ.get("GITHUB_TOKEN", "").strip()
            repo = os.environ.get("GITHUB_REPO", "").strip()
            if token and repo:
                auth_url = repo.replace("https://", f"https://{token}@")
                try:
                    subprocess.run(["git", "fetch", auth_url, "main"], cwd=base_dir, timeout=15, capture_output=True)
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ Emergency disk cleanup notice: {e}", flush=True)

emergency_disk_clean()




# ── Phantom Regiment Web Portal & API ──────────────────────────────────────────

def _run_flask(loop=None):

    port = int(os.environ.get("PORT", 10000))

    app = create_app(bot, bot.db, loop=loop)

    app.run(host="0.0.0.0", port=port, use_reloader=False)





# ── Git backup ─────────────────────────────────────────────────────────────────

backup = GitBackup("data/bot.db")





# ── Bot setup ──────────────────────────────────────────────────────────────────

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

bot.db = Database("data/bot.db")

# Bans from the original Phantom Regiment guild apply to every bot surface.
# The short cache avoids a REST request for every command while keeping bans prompt.
ORIGINAL_PR_GUILD_ID = int(os.environ.get("GUILD_ID", 1550544659217125467))
_ban_cache: dict[int, tuple[bool, float]] = {}


async def is_banned_from_original_pr(user_id: int) -> bool:
    user_id = int(user_id)
    cached = _ban_cache.get(user_id)
    now = time.monotonic()
    if cached and cached[1] > now:
        return cached[0]
    guild = bot.get_guild(ORIGINAL_PR_GUILD_ID)
    if guild is None:
        return False
    try:
        await guild.fetch_ban(discord.Object(id=user_id))
        banned = True
    except discord.NotFound:
        banned = False
    except (discord.Forbidden, discord.HTTPException) as exc:
        print(f"⚠️ Could not verify original-server ban for {user_id}: {exc}", flush=True)
        return False
    _ban_cache[user_id] = (banned, now + 60.0)
    return banned


# Flask receives the bot object, so expose the central authorization check there.
bot.is_banned_from_original_pr = is_banned_from_original_pr


@bot.check
async def block_banned_prefix_commands(ctx: commands.Context) -> bool:
    if await is_banned_from_original_pr(ctx.author.id):
        raise commands.CheckFailure("You are banned from Phantom Regiment and cannot use this bot.")
    return True


async def block_banned_app_commands(interaction: discord.Interaction) -> bool:
    if await is_banned_from_original_pr(interaction.user.id):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "⛔ You are banned from Phantom Regiment and cannot use this application.",
                ephemeral=True,
            )
        return False
    return True


# CommandTree exposes interaction_check as an overridable coroutine, not a
# decorator. Replace the default global check so slash/context-menu commands
# receive the same ban gate as prefix commands.
bot.tree.interaction_check = block_banned_app_commands





_last_disk_clean = 0

@tasks.loop(seconds=10)

async def backup_loop():

    """Push DB to GitHub every 10 seconds if it changed and keep disk space lean."""

    global _last_disk_clean

    try:
        now = time.time()
        if now - _last_disk_clean > 300:
            _last_disk_clean = now
            await asyncio.to_thread(emergency_disk_clean)

        await asyncio.to_thread(backup.push_if_changed)

    except Exception as e:

        print(f"⚠️ Backup loop encountered an error: {e}")





@bot.event

async def on_ready():

    # main() initializes the database before connecting; only initialize here
    # when a reconnect starts without an initialized connection.
    if getattr(bot.db, "_db", None) is None:
        await bot.db.setup()

    print(f"✅  {bot.user} is online!  (ID {bot.user.id})", flush=True)



    # Register all connected guilds into the alliance database

    for g in bot.guilds:

        try:

            await bot.db.register_guild(g.id, g.name, g.member_count or 0, "Phantom Regiment")

        except Exception as e:

            print(f"⚠️ Failed to register guild {g.id}: {e}")



    # Start the backup loop

    if not backup_loop.is_running():

        backup_loop.start()



    try:

        synced = await bot.tree.sync()

        print(f"✅  Synced {len(synced)} slash commands.", flush=True)

    except Exception as e:

        print(f"❌  Sync failed: {e}", flush=True)



@bot.event

async def on_guild_join(guild: discord.Guild):

    try:

        await bot.db.register_guild(guild.id, guild.name, guild.member_count or 0, "Phantom Regiment")

    except Exception as e:

        print(f"⚠️ Failed to register joined guild {guild.id}: {e}")


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    if guild.id == ORIGINAL_PR_GUILD_ID:
        _ban_cache[int(user.id)] = (True, time.monotonic() + 3600.0)


@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    if guild.id == ORIGINAL_PR_GUILD_ID:
        _ban_cache[int(user.id)] = (False, time.monotonic() + 60.0)



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

    "cogs.invites",

    "cogs.giveaway",

    "cogs.roblox",

    "cogs.suggestions",

    "cogs.squads",

    "cogs.staffapply",

    "cogs.pingcooldown",

    "cogs.banking",
    "cogs.elections",
    "cogs.earth",
    "cogs.ai_advisor_cog",

]



PARTNER_COGS = [

    "cogs.economy",

    "cogs.banking",
    "cogs.elections",
    "cogs.earth",

    "cogs.roblox",

    "cogs.giveaway",

    "cogs.suggestions",

]



# ── Partner Bot Setup (Multi-Clan Support) ────────────────────────────────────

partner_token = os.environ.get("PARTNER_BOT_TOKEN")

partner_bot = None



if partner_token:

    partner_intents = discord.Intents.all()

    partner_bot = commands.Bot(command_prefix="!", intents=partner_intents)

    partner_bot.db = bot.db

    partner_bot.is_partner = True



    # Link both bots in memory

    bot.partner_bot = partner_bot

    partner_bot.primary_bot = bot



    @partner_bot.event

    async def on_ready():

        print(f"🤝  [Partner Bot] {partner_bot.user} is online!  (ID {partner_bot.user.id})", flush=True)



        # Register partner bot guilds into alliance database

        for g in partner_bot.guilds:

            try:

                await partner_bot.db.register_guild(g.id, g.name, g.member_count or 0, "Collation of Rose")

            except Exception as e:

                print(f"⚠️ [Partner Bot] Failed to register guild {g.id}: {e}")



        try:

            synced = await partner_bot.tree.sync()

            print(f"🤝  [Partner Bot] Synced {len(synced)} slash commands.", flush=True)

        except Exception as e:

            print(f"❌  [Partner Bot] Sync failed: {e}", flush=True)



    @partner_bot.event

    async def on_guild_join(guild: discord.Guild):

        try:

            await partner_bot.db.register_guild(guild.id, guild.name, guild.member_count or 0, "Collation of Rose")

        except Exception as e:

            print(f"⚠️ [Partner Bot] Failed to register joined guild {guild.id}: {e}")



    @partner_bot.tree.error

    async def on_partner_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):

        print(f"❌  [Partner Bot] Slash command error in {interaction.command.name if interaction.command else 'Unknown'}: {error}")

        try:

            if not interaction.response.is_done():

                await interaction.response.send_message(f"❌ Internal error: {error}", ephemeral=True)

            else:

                await interaction.followup.send(f"❌ Internal error: {error}", ephemeral=True)

        except:

            pass



    @partner_bot.command()

    @commands.is_owner()

    async def sync(ctx: commands.Context):

        partner_bot.tree.copy_global_to(guild=ctx.guild)

        synced = await partner_bot.tree.sync(guild=ctx.guild)

        await ctx.send(f"✅  [Partner Bot] Instantly synced {len(synced)} commands to this server!")





async def _start_client(client, client_token):

    async with client:

        await client.start(client_token)





async def main():

    # Bind Render's health/web port before slow backup restoration. A Git
    # clone can take minutes on a cold deploy; starting Flask first lets
    # Render pass its port/health check while the database is prepared.
    loop = asyncio.get_running_loop()
    # Keep web requests from racing database restore/setup while still binding
    # Render's health port immediately.
    bot.web_db_ready = asyncio.Event()
    threading.Thread(target=_run_flask, args=(loop,), daemon=True).start()

    # Git operations are synchronous and can block on a cold deploy. Run them
    # off the event loop and continue with a local DB if GitHub is unavailable.
    try:
        restored = await asyncio.wait_for(asyncio.to_thread(backup.restore), timeout=60)
        if backup.is_render() and not restored:
            print("⚠️ No remote backup was restored; checking local database integrity...", flush=True)
    except Exception as e:
        print(f"⚠️ Database backup restore notice: {e}", flush=True)

    local_db = bot.db.db_path
    local_valid = False
    if os.path.exists(local_db) and os.path.getsize(local_db) > 1000:
        try:
            conn = sqlite3.connect(local_db, timeout=15.0)
            local_valid = conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            conn.close()
        except Exception:
            local_valid = False

    if local_valid:
        print(f"✅ Local database verified healthy ({os.path.getsize(local_db):,} bytes).", flush=True)
    elif backup.is_render():
        raise RuntimeError("No valid local or remote database available; startup aborted to prevent data loss.")

    # Open SQLite first, then release web requests. Stock seeding is
    # non-critical and must never hold every page behind the readiness gate.
    await bot.db.setup()
    bot.web_db_ready.set()
    try:
        await bot.db.seed_default_stocks()
    except Exception as e:
        print(f"⚠️ Stock seeding notice: {e}", flush=True)

    token = os.environ.get("DISCORD_TOKEN")

    if not token:

        print("❌  DISCORD_TOKEN not set!  Create a .env file (see .env.example).", flush=True)

        return



    # Load primary cogs

    for cog in COGS:

        try:

            await bot.load_extension(cog)

            print(f"✅  Loaded {cog} on Primary Bot", flush=True)

        except Exception as e:

            print(f"❌  Failed to load {cog} on Primary Bot: {e}", flush=True)



    clients_to_run = [_start_client(bot, token)]



    # Load partner bot if token provided

    if partner_token and partner_bot:

        print("🤝  Loading extensions for Partner Bot...", flush=True)

        for cog in PARTNER_COGS:

            try:

                await partner_bot.load_extension(cog)

                print(f"✅  Loaded {cog} on Partner Bot", flush=True)

            except Exception as e:

                print(f"❌  Failed to load {cog} on Partner Bot: {e}", flush=True)

        clients_to_run.append(_start_client(partner_bot, partner_token))



    await asyncio.gather(*clients_to_run)





if __name__ == "__main__":

    asyncio.run(main())

