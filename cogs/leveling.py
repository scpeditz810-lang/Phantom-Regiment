"""
Leveling cog — XP tracking, level-ups, rank cards, leaderboard, wins management.

Wins verification:
  • /submit-wins <count> <screenshot>  — player submits proof → #win-verification
  • Staff / Commander clicks Approve → wins recorded, roles synced
  • /set-wins @user <count>            — direct staff override (no screenshot needed)
  • /wins @user                        — public stat lookup
"""

from __future__ import annotations

import random
import time

import discord
from discord.ext import commands
from discord import app_commands

from utils.constants import (
    XP_PER_MESSAGE, XP_COOLDOWN, xp_for_level,
    LEVEL_ROLES, IN_GAME_ROLES, STAFF_ROLES,
)
from utils.rank_card import generate_rank_card

_STAFF_NAMES = {r["name"] for r in STAFF_ROLES} | {"Commander"}


# ════════════════════════════════════════════════════════════════════════════════
# Persistent buttons for win verification
# ════════════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════════════
# Cog
# ════════════════════════════════════════════════════════════════════════════════

class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cooldowns: dict[int, float] = {}

    async def cog_load(self):
        pass

    # ── helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def rank_info(level: int) -> tuple[str, tuple[int, int, int]]:
        """Return (rank_name, (r, g, b)) for the highest level role."""
        name, colour = "Recruit", (149, 165, 166)
        for r in LEVEL_ROLES:
            if level >= r["level"]:
                name = r["name"]
                c = r["color"]
                colour = ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)
        return name, colour

    async def _sync_roles(self, member: discord.Member, level: int, wins: int):
        """Add the correct level role and (if qualified) in-game role; remove old ones."""
        guild = member.guild

        # ── level roles ─────────────────────────────────────────────────
        earned = None
        for r in reversed(LEVEL_ROLES):
            if level >= r["level"]:
                earned = r["name"]
                break
        for r in LEVEL_ROLES:
            role = discord.utils.get(guild.roles, name=r["name"])
            if not role:
                continue
            if r["name"] == earned and role not in member.roles:
                await member.add_roles(role)
            elif r["name"] != earned and role in member.roles:
                await member.remove_roles(role)

        # ── in-game roles (PURELY WINS) ─────────────────────────────────
        earned_ig = None
        for r in reversed(IN_GAME_ROLES):
            if wins >= r["wins"]:
                earned_ig = r["name"]
                break
        for r in IN_GAME_ROLES:
            role = discord.utils.get(guild.roles, name=r["name"])
            if not role:
                continue
            if r["name"] == earned_ig and role not in member.roles:
                await member.add_roles(role)
            elif r["name"] != earned_ig and role in member.roles:
                await member.remove_roles(role)

    # ── XP on message ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        uid = message.author.id
        now = time.time()
        if uid in self._cooldowns and now - self._cooldowns[uid] < XP_COOLDOWN:
            return
        self._cooldowns[uid] = now

        xp_gain = random.randint(*XP_PER_MESSAGE)
        await self.bot.db.add_xp(uid, message.guild.id, xp_gain)

        data = await self.bot.db.get_user(uid, message.guild.id)
        lvl, xp = data["level"], data["xp"]
        req = xp_for_level(lvl + 1)

        if xp >= req:
            new_lvl = lvl + 1
            await self.bot.db.set_level(uid, message.guild.id, new_lvl)
            await self.bot.db.set_xp(uid, message.guild.id, xp - req)
            await self.bot.db.add_medals(uid, message.guild.id, 50)
            await self._sync_roles(message.author, new_lvl, data["wins"])

            rank_name, _ = self.rank_info(new_lvl)
            embed = discord.Embed(
                title="🎉  Level Up!",
                description=f"{message.author.mention} advanced to **Level {new_lvl}**!\nYou earned 🏅 **50 Medals**!",
                colour=discord.Colour.gold(),
            )
            embed.add_field(name="Rank", value=rank_name, inline=True)
            embed.set_thumbnail(url=message.author.display_avatar.url)

            ch = discord.utils.get(message.guild.text_channels, name="🎉│level-up")
            await (ch or message.channel).send(embed=embed)

    # ── /rank ───────────────────────────────────────────────────────────────

    @app_commands.command(name="rank", description="Show your (or someone's) rank card")
    @app_commands.describe(member="Leave blank for yourself")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        await interaction.response.defer()

        data  = await self.bot.db.ensure_user(member.id, interaction.guild_id)
        grank = await self.bot.db.get_rank(member.id, interaction.guild_id)
        lvl, xp = data["level"], data["xp"]
        req = xp_for_level(lvl + 1)
        rname, rcol = self.rank_info(lvl)
        
        # Override rank display with the highest Discord role the user actually has
        from utils.constants import ROLE_HIERARCHY
        member_role_names = {r.name for r in member.roles}
        for rh in reversed(ROLE_HIERARCHY):
            if rh["name"] in member_role_names:
                rname = rh["name"]
                c = rh["color"]
                rcol = ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)
                break

        buf = await generate_rank_card(
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            level=lvl, xp=xp, required_xp=req,
            global_rank=grank, rank_name=rname, rank_color=rcol,
            active_banner=data.get("active_banner")
        )
        await interaction.followup.send(file=discord.File(buf, "rank_card.png"))

    @app_commands.command(name="level", description="View your (or another user's) current level and XP")
    async def level_cmd(self, interaction: discord.Interaction, member: discord.Member = None):
        # Alias for /rank
        await self.rank(interaction, member)

    # ── /leaderboard ────────────────────────────────────────────────────────

    @app_commands.command(name="leaderboard", description="Top 10 server leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        lb = await self.bot.db.get_leaderboard(interaction.guild_id, 10)

        if not lb:
            return await interaction.followup.send("📊 No one has earned XP yet!")

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, e in enumerate(lb):
            u = interaction.guild.get_member(e["user_id"])
            name = u.display_name if u else f"Unknown ({e['user_id']})"
            m = medals[i] if i < 3 else f"`#{i+1}`"
            rn, _ = self.rank_info(e["level"])
            lines.append(f"{m} **{name}** — Lvl {e['level']} • {e['xp']} XP • {rn}")

        embed = discord.Embed(
            title="🏆  Server Leaderboard",
            description="\n".join(lines),
            colour=discord.Colour.gold(),
        )
        await interaction.followup.send(embed=embed)

    # ── /submit-wins  (player submits screenshot for verification) ──────────

    @app_commands.command(
        name="submit-wins",
        description="Submit a screenshot of your wins for staff verification",
    )
    @app_commands.describe(
        wins="Your total win count",
        in_game_level="Your current in-game level",
        screenshot="Screenshot proof of your wins and level",
    )
    async def submit_wins(
        self,
        interaction: discord.Interaction,
        wins: int,
        in_game_level: int,
        screenshot: discord.Attachment,
    ):
        if wins < 0 or in_game_level < 0:
            return await interaction.response.send_message(
                "❌ Wins and Level can't be negative!", ephemeral=True)

        # Validate it's an image
        if not screenshot.content_type or not screenshot.content_type.startswith("image"):
            return await interaction.response.send_message(
                "❌ Please attach an **image** screenshot.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Post to #win-verification
        ch = discord.utils.get(interaction.guild.text_channels, name="🏆│win-verification")
        if not ch:
            return await interaction.followup.send(
                "⚠️ `#win-verification` channel not found. Ask an admin to run `!setup`.",
                ephemeral=True,
            )

        embed = discord.Embed(
            title="🏆  Win Verification Request",
            colour=discord.Colour.gold(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(
            name="👤 Player",
            value=f"{interaction.user.mention} (`{interaction.user}`)",
            inline=True,
        )
        embed.add_field(name="🏆 Claimed Wins", value=str(wins), inline=True)
        embed.add_field(name="🎮 Claimed Level", value=str(in_game_level), inline=True)

        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        embed.add_field(name="📊 Current Recorded Wins", value=str(data["wins"]), inline=False)
        embed.add_field(name="📈 Chat XP Level", value=str(data["level"]), inline=True)
        embed.set_image(url=screenshot.url)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        embed.add_field(name="🛠️ Verification", value="Commanders: Use `/set-stats` to verify and update this user's stats!", inline=False)
        await ch.send(embed=embed)

        await interaction.followup.send(
            "✅ Your screenshot has been submitted for verification! "
            "You'll be notified when staff reviews it.",
            ephemeral=True,
        )

    # ── /set-stats  (staff / commander direct override) ──────────────────────

    @app_commands.command(
        name="set-stats",
        description="Directly set a member's win count and in-game level (Staff / Commander)",
    )
    @app_commands.describe(member="The member", wins="Their verified total wins", in_game_level="Their verified in-game level", message="Optional message to send to the user via DM")
    async def set_stats(self, interaction: discord.Interaction,
                        member: discord.Member, wins: int, in_game_level: int, message: str | None = None):
        if not ({r.name for r in interaction.user.roles} & _STAFF_NAMES) and not any(r.id == 1550978510229733396 for r in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ Staff, Commander, or Branch Commander only.", ephemeral=True)
        if wins < 0 or in_game_level < 0:
            return await interaction.response.send_message(
                "❌ Stats can't be negative.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        try:
            await self.bot.db.set_stats(member.id, interaction.guild_id, wins, in_game_level)
            data = await self.bot.db.get_user(member.id, interaction.guild_id)
            await self._sync_roles(member, data["level"], wins)
        except Exception as e:
            return await interaction.followup.send(f"❌ Error updating stats: {e}")

        qualified = None
        for r in reversed(IN_GAME_ROLES):
            if data["level"] >= r["level"] and wins >= r["wins"]:
                qualified = r
                break

        msg = f"✅ **{member.display_name}**'s stats set to **{wins} Wins** and **Level {in_game_level}**."
        if qualified:
            msg += f"\nThey now qualify for **{qualified['name']}** role!"
            
        try:
            dm_msg = f"✅ Your stats have been verified and updated by {interaction.user.mention}! You now have **{wins} Wins** and are **Level {in_game_level}**."
            if message and message.strip():
                dm_msg += f"\n\n📩 **Message from staff:** {message.strip()}"
            await member.send(dm_msg)
        except discord.Forbidden:
            msg += "\n⚠️ Could not DM the user (their DMs are closed)."
            
        await interaction.followup.send(msg)

    # ── /wins  (public lookup) ──────────────────────────────────────────────

    @app_commands.command(name="wins", description="Check a member's recorded wins")
    @app_commands.describe(member="The member to check")
    async def wins(self, interaction: discord.Interaction,
                   member: discord.Member | None = None):
        member = member or interaction.user
        data = await self.bot.db.ensure_user(member.id, interaction.guild_id)

        qualified = None
        for r in reversed(IN_GAME_ROLES):
            if data["level"] >= r["level"] and data["wins"] >= r["wins"]:
                qualified = r
                break
        nxt = None
        for r in IN_GAME_ROLES:
            if data["level"] < r["level"] or data["wins"] < r["wins"]:
                nxt = r
                break

        embed = discord.Embed(
            title=f"🏆  {member.display_name}'s Stats",
            colour=discord.Colour.gold(),
        )
        embed.add_field(name="Wins",  value=str(data["wins"]),  inline=True)
        embed.add_field(name="Level", value=str(data["level"]), inline=True)
        if qualified:
            embed.add_field(name="In-Game Rank", value=qualified["name"], inline=True)
        if nxt:
            embed.add_field(
                name="Next Rank",
                value=f"**{nxt['name']}** — Lvl {nxt['level']}, {nxt['wins']} Wins",
                inline=False,
            )
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LevelingCog(bot))
