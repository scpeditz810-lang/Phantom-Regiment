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

Brain: web/ai_advisor.py (real LLM first, keyword engine only as fail-safe). Admin commands: !aistatus, !aitest

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

    def _split_reply(self, text: str, limit: int = 1900) -> list:
        """Split a long reply into Discord-safe chunks, preferring line breaks."""
        chunks = []
        while len(text) > limit:
            cut = text.rfind("\n", 0, limit)
            if cut < limit // 2:
                cut = text.rfind(" ", 0, limit)
            if cut < limit // 2:
                cut = limit
            chunks.append(text[:cut].rstrip())
            text = text[cut:].lstrip()
        if text:
            chunks.append(text)
        return chunks[:3]

    def _providers_configured(self) -> str:
        names = []
        for label, env in (("Anthropic", "ANTHROPIC_API_KEY"), ("Gemini", "GEMINI_API_KEY"),
                           ("Groq", "GROQ_API_KEY"), ("OpenRouter", "OPENROUTER_API_KEY"),
                           ("OpenAI", "OPENAI_API_KEY")):
            if os.getenv(env, "").strip():
                names.append(label)
        if os.getenv("AI_ALLOW_KEYLESS", "1") != "0":
            names.append("Pollinations (keyless)")
        return ", ".join(names) if names else "none"

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

        # 0. Admin diagnostics: "!aistatus" shows which brain is answering and why
        if user_prompt.lower() == "!aistatus":
            perms = getattr(message.author, "guild_permissions", None)
            if perms and perms.administrator:
                await message.reply(
                    f"🧠 **AI Status**\n"
                    f"• Providers configured: {self._providers_configured()}\n"
                    f"• Last answer source: {self.advisor.last_source or 'none yet'}\n"
                    f"• Last error: {self.advisor.last_error or 'none'}\n"
                    f"• Run `!aitest` to test every provider live.",
                    mention_author=False,
                    allowed_mentions=discord.AllowedMentions.none()
                )
            return

        # 0b. Admin live test: "!aitest" calls every configured provider and shows the real result
        if user_prompt.lower() == "!aitest":
            perms = getattr(message.author, "guild_permissions", None)
            if perms and perms.administrator:
                async with message.channel.typing():
                    results = await asyncio.to_thread(self.advisor.test_providers)
                lines = [f"{'✅' if ok else '❌'} **{name}** — {detail}" for name, ok, detail in results]
                await message.reply(
                    "🧪 **AI Provider Test**\n" + ("\n".join(lines) if lines else "No providers to test."),
                    mention_author=False,
                    allowed_mentions=discord.AllowedMentions.none()
                )
            return

        if not user_prompt:
            return

        # 1. Self-Awareness: Check for attempt to mention everyone
        if self.is_mass_mention_attempt(user_prompt):
            await self.report_mass_mention_attempt(message)
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

            server_info = {
                "mayor_name": mayor_info.get("name", "None"),
                "owner_name": leadership.get("owner", "Server Owner"),
                "managers": leadership.get("managers", []),
                "asker_name": message.author.display_name,
                "website_url": "https://phantomregiment.apps.bot-hosting.cloud/",
                "website_channel": "https://discord.com/channels/1550544659217125467/1552470594380103822",
            }

            try:
                # LLM brain answers independently; per-user memory keyed by Discord user ID
                result = await asyncio.to_thread(
                    self.advisor.ask, user_prompt, server_info, message.author.id
                )
                reply_text = result.get("response") or "Tactical systems reporting nominal. How may I assist your operations?"
                print(f"[AI Advisor Cog] Answered via: {result.get('source')} ({result.get('latency_ms')} ms)")
            except Exception as e:
                print(f"[AI Advisor Cog] ask() crashed, using local fail-safe: {e}")
                try:
                    stocks = await asyncio.to_thread(self.advisor.get_market_data)
                    wars = await asyncio.to_thread(self.advisor.get_wars_data)
                    reply_text = self.advisor.generate_tactical_fallback(user_prompt, stocks, wars, server_info)
                except Exception as e2:
                    print(f"[AI Advisor Cog] Fallback failed too: {e2}")
                    reply_text = "⚠️ My systems hit an error. Please try again in a moment."

            # Extra defense: neutralise any @everyone / @here in the generated output
            reply_text = reply_text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

            safe_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True)
            chunks = self._split_reply(reply_text)
            for i, chunk in enumerate(chunks):
                try:
                    if i == 0:
                        await message.reply(chunk, mention_author=False, allowed_mentions=safe_mentions)
                    else:
                        await message.channel.send(chunk, allowed_mentions=safe_mentions)
                except discord.HTTPException:
                    await message.channel.send(chunk, allowed_mentions=safe_mentions)

async def setup(bot: commands.Bot):
    await bot.add_cog(AIAdvisorDiscordCog(bot))
