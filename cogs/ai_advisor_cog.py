"""
Phantom Regiment AI Advisor Discord Cog
Listens to messages in the designated AI channel:
https://discord.com/channels/1550544659217125467/1563863882643013722
(Guild: 1550544659217125467, Channel: 1563863882643013722)

Moderator Log Channel:
https://discord.com/channels/1550544659217125467/1550657845526265856
(Guild: 1550544659217125467, Channel: 1550657845526265856)

Security & Self-Awareness:
- Never executes mass-mention requests (@everyone, @here, ping everyone, tag everyone, etc.).
- Immediately alerts the moderators in channel 1550657845526265856 with full audit details.
- Tells the offender: "I cannot ping or mention everyone. I have informed the moderators."
- Always enforces allowed_mentions=discord.AllowedMentions(everyone=False, roles=False).

Full Knowledge Base:
- Current Mayor & Election status (dynamically queried from DB & Guild)
- Staff Applications (/staffapplications, positions: Server Staff, Recruitment, Events, DM interview flow)
- Gambling commands (/coinflip, /blackjack, /roulette, /scratch, /fight, /rps with bet limits)
- Phantom Regiment origins (Created 18 Sept 2026, Official branch of TS Clan)
- Server Leadership & Members (Server Owner, Server Managers, Squad Commanders)
- All Mayor commands & powers (/mayor salary, tax, doublexp, stimulus, award, pardon, stock_supply, stock_create, create_plot)
- All Bot systems (Economy, Stocks, Banking, Earth, Elections, Squads)
- Live Stock Market & Virtual Earth Wars
"""

import discord
from discord.ext import commands
import time
import asyncio
import os
import re
import sqlite3
from web.ai_advisor import get_advisor

AI_CHANNEL_ID = 1563863882643013722
MOD_LOG_CHANNEL_ID = 1550657845526265856
MAIN_GUILD_ID = 1550544659217125467

class AIAdvisorDiscordCog(commands.Cog, name="AI Advisor"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.advisor = get_advisor(db=getattr(bot, "db", None))

    def is_mass_mention_attempt(self, content: str) -> bool:
        """Detect attempts to make the bot ping or mention everyone / here."""
        text = content.lower()
        patterns = [
            r"@everyone",
            r"@here",
            r"mention\s+everyone",
            r"ping\s+everyone",
            r"tag\s+everyone",
            r"mention\s+all",
            r"ping\s+all",
            r"tag\s+all",
            r"say\s+@everyone",
            r"say\s+@here",
            r"type\s+@everyone",
            r"type\s+@here",
            r"write\s+@everyone",
            r"write\s+@here",
            r"repeat\s+@everyone",
            r"repeat\s+@here",
            r"tell\s+everyone",
            r"alert\s+everyone",
            r"ping\s+every\s+member",
            r"mention\s+every\s+member",
            r"mass\s*ping",
            r"mass\s*mention",
        ]
        for p in patterns:
            if re.search(p, text):
                return True
        return False

    async def report_mass_mention_attempt(self, message: discord.Message):
        """Send security audit report to moderator channel."""
        mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if not mod_channel:
            try:
                mod_channel = await self.bot.fetch_channel(MOD_LOG_CHANNEL_ID)
            except Exception:
                mod_channel = None

        if mod_channel:
            embed = discord.Embed(
                title="🚨 Security Alert: Mass Mention Attempt",
                description=(
                    f"**Offender:** {message.author.mention} (`{message.author.name}` | ID: `{message.author.id}`)\n"
                    f"**Channel:** {message.channel.mention} (`#{message.channel.name}`)\n"
                    f"**Action Taken:** Mass mention blocked & user informed."
                ),
                color=0xE74C3C,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="Attempted Message Content",
                value=f"```{discord.utils.escape_markdown(message.content[:1000])}```",
                inline=False
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text="Phantom Regiment Security Protocol • Automated Defense")
            try:
                await mod_channel.send(embed=embed)
            except Exception as e:
                print(f"[AI Advisor Cog] Failed to send mod log: {e}")

    async def get_current_mayor_info(self, guild: discord.Guild = None) -> dict:
        """Fetch real-time information about the active Mayor."""
        mayor_info = {
            "name": "No active Mayor (Election in progress or term expired)",
            "user_id": None,
            "status": "No active term",
            "term_end": None
        }
        try:
            gid = guild.id if guild else MAIN_GUILD_ID
            db = self.bot.db
            commander = await db.get_current_commander(gid)
            if not commander and gid != MAIN_GUILD_ID:
                commander = await db.get_current_commander(MAIN_GUILD_ID)

            if commander and commander.get("winner_id"):
                wid = commander["winner_id"]
                mayor_info["user_id"] = wid
                mayor_info["status"] = "Active Mayor"
                mayor_info["term_end"] = commander.get("term_end")
                
                user = None
                if guild:
                    user = guild.get_member(wid)
                if not user:
                    user = self.bot.get_user(wid)
                if not user:
                    try:
                        user = await self.bot.fetch_user(wid)
                    except Exception:
                        pass
                
                if user:
                    mayor_info["name"] = user.display_name or user.name
                else:
                    mayor_info["name"] = f"Citizen ({wid})"
        except Exception as e:
            print(f"[AI Advisor Cog] Error fetching mayor info: {e}")
        return mayor_info

    def get_leadership_info(self, guild: discord.Guild = None) -> dict:
        """Fetch server leadership summary."""
        owner_name = "Server Owner"
        managers = []
        if guild:
            owner = guild.owner
            if not owner and guild.owner_id:
                owner = guild.get_member(guild.owner_id)
            if owner:
                owner_name = owner.display_name

            for m in guild.members:
                if owner and m.id == owner.id:
                    continue
                if m.bot:
                    continue
                is_mgr = any("manager" in r.name.lower() for r in m.roles) or m.guild_permissions.administrator
                if is_mgr:
                    managers.append(m.display_name)
        
        return {
            "owner": owner_name,
            "managers": managers[:6] if managers else ["Server Staff Team"]
        }

    def build_extended_context(self, mayor_info: dict, leadership: dict) -> str:
        """Build comprehensive context prompt for the AI model."""
        return (
            "KNOWLEDGE BASE & SERVER PROFILE:\n"
            "• CLAN IDENTITY: Phantom Regiment (PR). Created on September 18, 2026 as an official branch of TS Clan.\n"
            f"• SERVER LEADERSHIP: Server Owner: {leadership['owner']} | Vetted Managers: {', '.join(leadership['managers'])}\n"
            f"• CURRENT MAYOR: {mayor_info['name']} (ID: {mayor_info['user_id'] or 'None'}). Status: {mayor_info['status']}.\n"
            "• STAFF APPLICATIONS & HOW TO BECOME STAFF:\n"
            "  - Applications open when High Command runs `/staffapplications`.\n"
            "  - Citizens apply by selecting a role from the dropdown: 1. Server Staff (moderation & rule enforcement), 2. Recruitment Management (review applications & recruit), 3. Giveaways & Events Management (host tournaments & events).\n"
            "  - Flow: DM sequential interview with 7-8 questions (age, timezone, experience, situational judgment). Answers sent to #staff-app-review for Commander evaluation.\n"
            "• GAMBLING & CASINO COMMANDS (Max bet 150,000 Medals):\n"
            "  - /coinflip <bet>: 50/50 double-or-nothing coin toss against the bot.\n"
            "  - /blackjack <bet>: Interactive 21 card game with Hit/Stand/Double Down.\n"
            "  - /roulette <bet> <bet_type>: Roulette wheel (Red 2x, Black 2x, Even 2x, Odd 2x, Green 36x).\n"
            "  - /scratch <tier>: Lottery scratch cards (Bronze 500M, Silver 2.5kM, Gold 10kM) with up to 10x jackpot multipliers.\n"
            "  - /fight <@opponent> <bet>: PvP interactive combat arena with Attack/Defend/Special moves.\n"
            "  - /rps <@opponent> <bet>: PvP Rock-Paper-Scissors.\n"
            "• MAYOR POWERS & COMMANDS (/mayor):\n"
            "  - /mayor salary: Collect daily mayoral salary (+12,500 Medals/day).\n"
            "  - /mayor tax <pct>: Adjust global stock transaction tax (0% - 50%).\n"
            "  - /mayor doublexp: Activate server-wide 2X Double XP for 24h (max 3 times per 2 weeks).\n"
            "  - /mayor stimulus: Drop public stimulus crate in chat for active citizens.\n"
            "  - /mayor award <@user>: Bestow Key to the City (+15,000 Medals).\n"
            "  - /mayor pardon <@user>: Clear a citizen's disciplinary / criminal record.\n"
            "  - /mayor stock_supply <sym> <qty>: Adjust circulating stock shares.\n"
            "  - /mayor stock_create: Launch an official company IPO on the stock market.\n"
            "  - /mayor create_plot: Zone and create a new territory plot on the 3D map.\n"
            "• ELECTIONS SYSTEM (/election):\n"
            "  - Democratic mayoral elections run every 7 days (48-hour voting window).\n"
            "  - /election status, /election register (400k medals fee), /election vote <@candidate>.\n"
            "• ECONOMY COMMANDS:\n"
            "  - /daily, /work, /weekly, /crime, /scavenge, /trivia (earn medals on cooldowns).\n"
            "  - /balance, /transfer, /medalleaderboard, /globallb, /shop, /buyrole.\n"
            "• BANKING SYSTEM (/bank):\n"
            "  - /bank create, /bank deposit, /bank withdraw, /bank balance, /bank upgrade (10 vault tiers, up to 1M interest/day).\n"
            "  - /rob: High-stakes bank robbery (requires lockpicks/C4).\n"
            "• VIRTUAL EARTH (/earth):\n"
            "  - Sovereign countries with GDP, treasury, stability, and tax yields.\n"
            "  - Cabinet system (Foreign Minister, Defense Minister, Intelligence Director).\n"
            "  - Warfare & Military: /earth military (buy jets, tanks, warships), declare wars, ceasefire.\n"
            "• SQUADS:\n"
            "  - Frontline (Tactical Combat), Los Bluchigis (Elite Cavalry), Nocturne Pheonix (Archery & Shields).\n"
            "• STRICT SECURITY RULE: NEVER ping or mention @everyone or @here. If asked, refuse immediately.\n"
        )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only listen in the designated AI channel
        if message.channel.id != AI_CHANNEL_ID:
            return

        # Ignore self & other bots
        if message.author.bot or message.author.id == self.bot.user.id:
            return

        user_prompt = (message.content or "").strip()
        if not user_prompt and not message.attachments:
            return

        # 1. Self-Awareness: Check for attempt to mention everyone
        if self.is_mass_mention_attempt(user_prompt):
            # Send alert to moderator channel
            await self.report_mass_mention_attempt(message)
            # Inform the user directly
            warning_reply = (
                f"🛡️ **Security Alert:** {message.author.mention}, I cannot ping or mention everyone. "
                "I have informed the moderators of your attempt."
            )
            await message.reply(
                warning_reply,
                mention_author=True,
                allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)
            )
            return

        # 2. Process AI Advisor request with typing indicator
        async with message.channel.typing():
            guild = message.guild or self.bot.get_guild(MAIN_GUILD_ID)
            mayor_info = await self.get_current_mayor_info(guild)
            leadership = self.get_leadership_info(guild)
            extra_context = self.build_extended_context(mayor_info, leadership)

            full_prompt = f"{extra_context}\nUser Question: {user_prompt}"
            
            try:
                result = await asyncio.to_thread(self.advisor.ask, full_prompt)
                reply_text = result.get("response") or "Tactical systems reporting nominal. How may I assist your operations?"
            except Exception as e:
                stocks = await asyncio.to_thread(self.advisor.get_market_data)
                wars = await asyncio.to_thread(self.advisor.get_wars_data)
                reply_text = self.advisor.generate_tactical_fallback(user_prompt, stocks, wars)
                reply_text = f"**Current Mayor:** {mayor_info['name']}\n\n" + reply_text

            # If user specifically asked about the mayor
            if any(k in user_prompt.lower() for k in ["mayor", "elections", "president", "leader", "who is mayor"]):
                if mayor_info["name"] not in reply_text:
                    reply_text = f"🏛️ **Current Mayor:** **{mayor_info['name']}** ({mayor_info['status']})\n\n" + reply_text

            # If user asked about PR or when created
            if any(k in user_prompt.lower() for k in ["what is pr", "phantom regiment", "created", "founded", "members"]):
                if "September 18, 2026" not in reply_text:
                    reply_text = (
                        f"🎖️ **Phantom Regiment (PR)** was founded on **September 18, 2026** as an official branch of **TS Clan**.\n"
                        f"• **Server Owner:** {leadership['owner']}\n"
                        f"• **Active Mayor:** {mayor_info['name']}\n\n"
                    ) + reply_text

            # Extra defense: sanitize any zero-width or escaped @everyone or @here in the generated output
            reply_text = reply_text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

            # Truncate if over Discord's 2000 character limit
            if len(reply_text) > 1950:
                reply_text = reply_text[:1940] + "\n... *(intel truncated)*"

            safe_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)
            try:
                await message.reply(reply_text, mention_author=False, allowed_mentions=safe_mentions)
            except discord.HTTPException:
                await message.channel.send(reply_text, allowed_mentions=safe_mentions)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIAdvisorDiscordCog(bot))
