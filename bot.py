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

from web import create_app



from utils.database import Database

from utils.git_backup import GitBackup



load_dotenv()



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

]



PARTNER_COGS = [

    "cogs.economy",

    "cogs.banking",

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

    # Restore DB from GitHub backup (runs before bot connects)

    backup.restore()



    # Ensure database schema and stock market seeding are ready

    await bot.db.setup()

    try:

        await bot.db.seed_default_stocks()

    except Exception as e:

        print(f"⚠️ Stock seeding notice: {e}", flush=True)



    # Start Flask in a daemon thread

    loop = asyncio.get_running_loop()
    threading.Thread(target=_run_flask, args=(loop,), daemon=True).start()



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

