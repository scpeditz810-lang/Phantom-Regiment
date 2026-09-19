"""
Moderation cog — warn, timeout, kick, ban, unban, purge.

Warn escalation:
    Warn 1 → warning only
    Warn 2 → 12-hour timeout
    Warn 3 → 1-day timeout
    Warn 4 → 1 day 12 h timeout
    Warn 5 → permanent ban

All commands respect role hierarchy — you cannot moderate someone
with an equal or higher staff rank, or the server owner.
"""

from __future__ import annotations

import datetime

import discord
from discord.ext import commands
from discord import app_commands

from utils.constants import STAFF_ROLES

_HIERARCHY = [r["name"] for r in STAFF_ROLES]   # low → high

# Warn # → (action_label, timedelta | "ban")
_ESCALATION = {
    1: ("🔇 Auto-timeout 1 hour",                     datetime.timedelta(hours=1)),
    2: ("🔇 Auto-timeout 4 hours",                    datetime.timedelta(hours=4)),
    3: ("🔇 Auto-timeout 8 hours",                    datetime.timedelta(hours=8)),
    4: ("🔇 Auto-timeout 12 hours",                   datetime.timedelta(hours=12)),
    5: ("🔨 Auto-permanent ban",                       "ban"),
}


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── permission helpers ──────────────────────────────────────────────────

    @staticmethod
    def _has(member: discord.Member, min_role: str) -> bool:
        """True if *member* holds *min_role* or anything above it."""
        idx = _HIERARCHY.index(min_role)
        names = {r.name for r in member.roles}
        return any(h in names for h in _HIERARCHY[idx:])

    @staticmethod
    def _staff_rank(member: discord.Member) -> int:
        """Highest staff hierarchy index (−1 if not staff)."""
        names = {r.name for r in member.roles}
        best = -1
        for i, name in enumerate(_HIERARCHY):
            if name in names:
                best = i
        return best

    @classmethod
    def _outranks(cls, mod: discord.Member, target: discord.Member) -> str | None:
        """Return an error string if *mod* cannot moderate *target*, else None."""
        if target.id == mod.guild.owner_id:
            return "❌ You can't moderate the server owner."
        if target.id == mod.id:
            return "❌ You can't moderate yourself."
        if target.bot:
            return "❌ You can't moderate a bot."
        if cls._staff_rank(mod) <= cls._staff_rank(target):
            return "❌ You can't moderate someone with equal or higher staff rank."
        if mod.top_role <= target.top_role:
            return "❌ Your highest role isn't above this member's highest role."
        return None

    # ── mod-log helper ──────────────────────────────────────────────────────

    @staticmethod
    async def _log(guild: discord.Guild, *, action: str, mod: discord.Member,
                   target: discord.User, reason: str, colour: discord.Colour):
        ch = guild.get_channel(1550657845526265856)
        if not ch:
            return
        e = discord.Embed(title=f"🔨  {action}", colour=colour,
                          timestamp=discord.utils.utcnow())
        e.add_field(name="User",      value=f"{target.mention} (`{target}`)", inline=True)
        e.add_field(name="Moderator", value=mod.mention, inline=True)
        e.add_field(name="Reason",    value=reason or "No reason provided", inline=False)
        e.set_thumbnail(url=target.display_avatar.url)
        await ch.send(embed=e)

    # ── /warn  (with auto-escalation) ──────────────────────────────────────

    @app_commands.command(name="warn", description="Warn a member (auto-escalates)")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    async def warn(self, interaction: discord.Interaction,
                   member: discord.Member, reason: str):
        if not self._has(interaction.user, "Trial Mod"):
            return await interaction.response.send_message("❌ Trial Mod+ required.", ephemeral=True)
        if err := self._outranks(interaction.user, member):
            return await interaction.response.send_message(err, ephemeral=True)

        # Record warning
        await self.bot.db.add_warning(member.id, interaction.guild_id,
                                      interaction.user.id, reason)
        warns = await self.bot.db.get_warnings(member.id, interaction.guild_id)
        count = len(warns)

        # Determine escalation
        label, punishment = _ESCALATION.get(count, _ESCALATION[5])  # 5+ → ban

        # Build DM embed
        dm = discord.Embed(
            title="⚠️  Warning",
            colour=discord.Colour.yellow(),
            description=f"You were warned in **{interaction.guild.name}**.",
        )
        dm.add_field(name="Reason",          value=reason)
        dm.add_field(name="Warning #",       value=f"{count} / 5")
        dm.add_field(name="Consequence",     value=label, inline=False)

        try:
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

        # Apply punishment
        result_extra = ""
        if punishment is None:
            pass  # warn 1 — nothing extra
        elif punishment == "ban":
            try:
                await member.ban(reason=f"Auto-ban: reached {count} warnings. Last: {reason}",
                                 delete_message_days=0)
                result_extra = f"\n🔨 **Auto-banned** (reached {count} warnings)."
            except discord.Forbidden:
                result_extra = "\n⚠️ Could not auto-ban (missing permissions)."
        else:  # timedelta
            try:
                await member.timeout(punishment, reason=f"Auto-timeout: warn #{count}. {reason}")
                hrs = int(punishment.total_seconds() // 3600)
                result_extra = f"\n🔇 **Auto-timed out** for {hrs}h (warn #{count})."
            except discord.Forbidden:
                result_extra = "\n⚠️ Could not auto-timeout (missing permissions)."

        # Log
        await self._log(interaction.guild, action=f"Warning #{count}", mod=interaction.user,
                        target=member, reason=f"{reason}\n{label}",
                        colour=discord.Colour.red() if punishment == "ban" else discord.Colour.yellow())

        await interaction.response.send_message(
            f"⚠️ {member.mention} warned — **{count}/5**.  {label}{result_extra}",
            ephemeral=True,
        )

    # ── /timeout ────────────────────────────────────────────────────────────

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.describe(member="Member", duration="Minutes", reason="Reason")
    async def timeout_cmd(self, interaction: discord.Interaction,
                          member: discord.Member, duration: int,
                          reason: str = "No reason provided"):
        if not self._has(interaction.user, "Trial Mod"):
            return await interaction.response.send_message("❌ Trial Mod+ required.", ephemeral=True)
        if err := self._outranks(interaction.user, member):
            return await interaction.response.send_message(err, ephemeral=True)

        await member.timeout(datetime.timedelta(minutes=duration), reason=reason)
        await self._log(interaction.guild, action="Timeout", mod=interaction.user,
                        target=member, reason=f"{reason} ({duration}min)",
                        colour=discord.Colour.orange())
        await interaction.response.send_message(
            f"🔇 {member.mention} timed out for {duration}m.", ephemeral=True)

    # ── /kick ───────────────────────────────────────────────────────────────

    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.describe(member="Member", reason="Reason")
    async def kick(self, interaction: discord.Interaction,
                   member: discord.Member, reason: str = "No reason provided"):
        if not self._has(interaction.user, "Senior Mod"):
            return await interaction.response.send_message("❌ Senior Mod+ required.", ephemeral=True)
        if err := self._outranks(interaction.user, member):
            return await interaction.response.send_message(err, ephemeral=True)

        try:
            await member.send(f"👢 Kicked from **{interaction.guild.name}** — {reason}")
        except discord.Forbidden:
            pass
        await member.kick(reason=reason)
        await self._log(interaction.guild, action="Kick", mod=interaction.user,
                        target=member, reason=reason, colour=discord.Colour.orange())
        await interaction.response.send_message(
            f"👢 {member.mention} kicked.", ephemeral=True)

    # ── /ban ────────────────────────────────────────────────────────────────

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(member="Member", reason="Reason")
    async def ban(self, interaction: discord.Interaction,
                  member: discord.Member, reason: str = "No reason provided"):
        if not self._has(interaction.user, "Senior Mod"):
            return await interaction.response.send_message("❌ Senior Mod+ required.", ephemeral=True)
        if err := self._outranks(interaction.user, member):
            return await interaction.response.send_message(err, ephemeral=True)

        try:
            await member.send(f"🔨 Banned from **{interaction.guild.name}** — {reason}")
        except discord.Forbidden:
            pass
        await member.ban(reason=reason, delete_message_days=0)
        await self._log(interaction.guild, action="Ban", mod=interaction.user,
                        target=member, reason=reason, colour=discord.Colour.red())
        await interaction.response.send_message(
            f"🔨 {member.mention} banned.", ephemeral=True)

    # ── /unban ──────────────────────────────────────────────────────────────

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="User ID to unban")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not self._has(interaction.user, "Admin"):
            return await interaction.response.send_message("❌ Admin+ required.", ephemeral=True)
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(f"✅ {user} unbanned.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

    # ── /purge ──────────────────────────────────────────────────────────────

    @app_commands.command(name="purge", description="Bulk-delete messages")
    @app_commands.describe(amount="Number of messages (max 100)")
    async def purge(self, interaction: discord.Interaction, amount: int):
        if not self._has(interaction.user, "Moderator"):
            return await interaction.response.send_message("❌ Moderator+ required.", ephemeral=True)
        amount = min(amount, 100)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🗑️ Deleted {len(deleted)} messages.", ephemeral=True)

    # ── /warnings ───────────────────────────────────────────────────────────

    @app_commands.command(name="warnings", description="View a member's warnings")
    @app_commands.describe(member="Member to check")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        if not self._has(interaction.user, "Trial Mod"):
            return await interaction.response.send_message("❌ Trial Mod+ required.", ephemeral=True)

        ws = await self.bot.db.get_warnings(member.id, interaction.guild_id)
        if not ws:
            return await interaction.response.send_message(
                f"✅ {member.mention} has no warnings.", ephemeral=True)

        e = discord.Embed(title=f"⚠️  Warnings — {member}", colour=discord.Colour.yellow())
        for i, w in enumerate(ws[:10], 1):
            mod = interaction.guild.get_member(w["mod_id"])
            mod_s = mod.name if mod else f"Unknown ({w['mod_id']})"
            e.add_field(
                name=f"#{i}  •  <t:{int(w['timestamp'])}:R>",
                value=f"**Reason:** {w['reason']}\n**By:** {mod_s}",
                inline=False,
            )

        # Show escalation status
        count = len(ws)
        if count < 5:
            _, next_label = _ESCALATION.get(count + 1, _ESCALATION[5])
            if next_label == "ban":
                nxt = "🔨 Permanent ban"
            elif next_label:
                hrs = int(next_label.total_seconds() // 3600)
                nxt = f"🔇 {hrs}h timeout"
            else:
                nxt = "⚠️ Warning only"
            e.set_footer(text=f"Total: {count}/5 warnings  •  Next warn → {nxt}")
        else:
            e.set_footer(text=f"Total: {count} warnings  •  Next warn → 🔨 Permanent ban")

        await interaction.response.send_message(embed=e, ephemeral=True)

    # ── /clear-warnings ────────────────────────────────────────────────────

    @app_commands.command(name="clear-warnings", description="Clear all warnings for a member")
    @app_commands.describe(member="Member to clear")
    async def clear_warnings(self, interaction: discord.Interaction, member: discord.Member):
        if not self._has(interaction.user, "Admin"):
            return await interaction.response.send_message("❌ Admin+ required.", ephemeral=True)

        await self.bot.db.clear_warnings(member.id, interaction.guild_id)
        await self._log(interaction.guild, action="Warnings Cleared", mod=interaction.user,
                        target=member, reason="All warnings cleared",
                        colour=discord.Colour.green())
        await interaction.response.send_message(
            f"✅ All warnings cleared for {member.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
