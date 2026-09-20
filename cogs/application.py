"""
Application cog — sequential DM question flow + verification gate.

Flow
────
1. Member joins → gets Unverified role (can only see #welcome, #rules, #announcements).
2. Bot posts "A DM from our bot will be sent to you!" in #welcome.
3. Bot DMs the member 9 questions one-by-one (5 min timeout each).
4. All answers compiled → embed posted to #app-review with Yes / No.
5. Yes  → remove Unverified, add Rookie + Member roles, DM welcome.
6. No   → DM with "Appeal Again" button (5-hour cooldown).
7. Appeal Again → re-runs the 7-question DM flow.
"""

from __future__ import annotations

import asyncio
import time

import discord
from discord.ext import commands
from discord import app_commands

from utils.constants import APPEAL_COOLDOWN_SECONDS, ACCEPTED_ROLE, STAFF_ROLES

_REVIEWERS = {r["name"] for r in STAFF_ROLES} | {"Commander"}

_QUESTIONS = [
    ("1️⃣", "What is your **age**?"),
    ("2️⃣", "How many **wins** do you currently have?"),
    ("3️⃣", "What is your total **kill count**?"),
    ("4️⃣", "What is your **timezone**?"),
    ("5️⃣", "How much **playtime** do you have in the game?"),
    ("6️⃣", "Will you agree to respect and follow the instructions of your **seniors** (Commanders, Admins, etc.)?"),
    ("7️⃣", "What type of **tactics and units** do you prefer to use?"),
    ("8️⃣", "What is your **Roblox username**?"),
    ("9️⃣", "What is your current **in-game level**?"),
]

_ANSWER_LABELS = [
    "🎂 Age", "🏆 Wins", "⚔️ Kills", "🌍 Timezone",
    "⏱️ Playtime", "🤝 Agree to Seniors?", "🎯 Tactics & Units",
    "🎮 Roblox Username", "📊 In-Game Level",
]


# ════════════════════════════════════════════════════════════════════════════════
# Persistent dynamic buttons (survive bot restarts)
# ════════════════════════════════════════════════════════════════════════════════

def _is_reviewer(member: discord.Member) -> bool:
    return bool({r.name for r in member.roles} & _REVIEWERS) or any(r.id == 1550978510229733396 for r in member.roles)


class _AcceptBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"app:accept:(?P<uid>\d+):(?P<gid>\d+)",
):
    def __init__(self, uid: int, gid: int):
        super().__init__(discord.ui.Button(
            label="✅ Yes — Accept",
            style=discord.ButtonStyle.green,
            custom_id=f"app:accept:{uid}:{gid}",
        ))
        self.uid, self.gid = uid, gid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]))

    async def callback(self, interaction: discord.Interaction):
        if not _is_reviewer(interaction.user):
            return await interaction.response.send_message("❌ You can't do this.", ephemeral=True)

        guild = interaction.client.get_guild(self.gid)
        member = guild.get_member(self.uid) if guild else None
        if not member:
            return await interaction.response.send_message("❌ User not found in server.", ephemeral=True)

        # Show modal for optional additional message
        modal = _AcceptMessageModal(member, guild, interaction.message)
        await interaction.response.send_modal(modal)


class _AcceptMessageModal(discord.ui.Modal, title="Accept Application"):
    extra_message = discord.ui.TextInput(
        label="Additional message to send via DM (optional)",
        placeholder="e.g. We have sent you an invite, please accept it!",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500,
    )

    def __init__(self, member: discord.Member, guild: discord.Guild, orig_message: discord.Message):
        super().__init__()
        self.member = member
        self.guild = guild
        self.orig_message = orig_message

    async def on_submit(self, interaction: discord.Interaction):
        member = self.member
        guild = self.guild

        # Remove Unverified, add Rookie + Member
        unverified = discord.utils.get(guild.roles, name="Unverified")
        rookie     = discord.utils.get(guild.roles, name=ACCEPTED_ROLE)
        member_r   = discord.utils.get(guild.roles, name="Member")

        roles_add = [r for r in (rookie, member_r) if r]
        roles_rm  = [r for r in (unverified,) if r and r in member.roles]

        try:
            if roles_add:
                await member.add_roles(*roles_add, reason="Application accepted")
            if roles_rm:
                await member.remove_roles(*roles_rm, reason="Application accepted")
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ **Error:** The bot is unable to give roles! Please go to **Server Settings > Roles** and make sure the `Phantom Regiment` bot role is **HIGHER** than the Rookie/Member/Unverified roles.", 
                ephemeral=True
            )

        await interaction.client.db.clear_app_cooldown(member.id)

        # Update embed
        embed = self.orig_message.embeds[0].copy()
        embed.colour = discord.Colour.green()
        embed.add_field(name="✅ Result", value=f"Accepted by {interaction.user.mention}", inline=False)
        await self.orig_message.edit(embed=embed, view=None)

        try:
            dm_msg = (
                f"🎉 **Welcome to {guild.name}!** Your application has been **accepted**!\n"
                f"You've been given the **{ACCEPTED_ROLE}** role. See you on the battlefield! ⚔️"
            )
            if self.extra_message.value.strip():
                dm_msg += f"\n\n📩 **Message from staff:** {self.extra_message.value.strip()}"
            await member.send(dm_msg)
        except discord.Forbidden:
            pass

        await interaction.response.send_message(f"✅ {member.mention} accepted.", ephemeral=True)


class _DenyBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"app:deny:(?P<uid>\d+):(?P<gid>\d+)",
):
    def __init__(self, uid: int, gid: int):
        super().__init__(discord.ui.Button(
            label="❌ No — Deny",
            style=discord.ButtonStyle.danger,
            custom_id=f"app:deny:{uid}:{gid}",
        ))
        self.uid, self.gid = uid, gid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]))

    async def callback(self, interaction: discord.Interaction):
        if not _is_reviewer(interaction.user):
            return await interaction.response.send_message("❌ You can't do this.", ephemeral=True)

        guild = interaction.client.get_guild(self.gid)
        await interaction.client.db.set_app_cooldown(self.uid)

        embed = interaction.message.embeds[0].copy()
        embed.colour = discord.Colour.red()
        embed.add_field(name="❌ Result", value=f"Denied by {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)

        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        if user:
            cooldown_end = int(time.time() + APPEAL_COOLDOWN_SECONDS)
            try:
                await user.send(
                    f"❌ **Your application to {guild.name} has been denied.**\n"
                    f"You can appeal again <t:{cooldown_end}:R> (at <t:{cooldown_end}:t>).\n"
                    f"Click the button below when the cooldown expires.",
                    view=_AppealView(interaction.client),
                )
            except discord.Forbidden:
                pass

        await interaction.response.send_message("❌ Application denied.", ephemeral=True)


class _AppealBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"app:appeal",
):
    def __init__(self):
        super().__init__(discord.ui.Button(
            label="🔄 Appeal Again",
            style=discord.ButtonStyle.primary,
            custom_id="app:appeal",
        ))

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: discord.Interaction):
        denied_at = await interaction.client.db.get_app_cooldown(interaction.user.id)
        if denied_at:
            elapsed = time.time() - denied_at
            if elapsed < APPEAL_COOLDOWN_SECONDS:
                remaining = APPEAL_COOLDOWN_SECONDS - elapsed
                hrs = int(remaining // 3600)
                mins = int((remaining % 3600) // 60)
                return await interaction.response.send_message(
                    f"⏳ Please wait **{hrs}h {mins}m** before appealing again.",
                    ephemeral=True,
                )

        cog: ApplicationCog | None = interaction.client.get_cog("ApplicationCog")
        if not cog:
            return await interaction.response.send_message("⚠️ Bot error.", ephemeral=True)

        # Find a mutual guild
        guild = None
        for g in interaction.client.guilds:
            if g.get_member(interaction.user.id):
                guild = g
                break
        if not guild:
            return await interaction.response.send_message("⚠️ You must be in the server.", ephemeral=True)

        await interaction.response.send_message("📝 Starting your appeal — answer the questions below!")
        asyncio.create_task(cog._run_application(interaction.user, guild))


class _AppealView(discord.ui.View):
    def __init__(self, bot=None):
        super().__init__(timeout=None)
        self.add_item(_AppealBtn())


# ════════════════════════════════════════════════════════════════════════════════
# Cog
# ════════════════════════════════════════════════════════════════════════════════

class ApplicationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._active: set[int] = set()

    async def cog_load(self):
        self.bot.add_dynamic_items(_AcceptBtn, _DenyBtn, _AppealBtn)
        self.bot.add_view(_AppealView(self.bot))

    # ── Sequential DM application ──────────────────────────────────────────

    async def _run_application(self, user: discord.User, guild: discord.Guild):
        """Ask 7 questions one-by-one in DMs, then post to #app-review."""
        # If they force-restart, just remove them from active and start fresh
        if user.id in self._active:
            self._active.remove(user.id)

        self._active.add(user.id)
        try:
            # Intro message
            intro = discord.Embed(
                title=f"📝 Application — {guild.name}",
                description=(
                    "I'll ask you **9 questions** one at a time.\n"
                    "Just type your answer after each question.\n"
                    "You have **5 minutes** per question — take your time!"
                ),
                colour=discord.Colour.gold(),
            )
            if guild.icon:
                intro.set_thumbnail(url=guild.icon.url)
            await user.send(embed=intro)

            answers: list[str] = []

            def check(m: discord.Message) -> bool:
                return (
                    m.author.id == user.id
                    and m.guild is None
                )

            for i, (emoji, question) in enumerate(_QUESTIONS, 1):
                q_embed = discord.Embed(
                    description=f"{emoji}  {question}",
                    colour=discord.Colour.gold(),
                )
                q_embed.set_footer(text=f"Question {i} of {len(_QUESTIONS)}  •  Type your answer below")
                await user.send(embed=q_embed)

                try:
                    try:
                        msg = await self.bot.wait_for("message", check=check, timeout=300)
                    except asyncio.TimeoutError:
                        await user.send(
                            "⏰ **Application timed out** (5 min per question).\n"
                            "Click the button below when you're ready to try again.",
                            view=_AppealView(self.bot)
                        )
                        return

                    content = msg.content
                    if not content and msg.attachments:
                        content = msg.attachments[0].url
                    elif not content:
                        content = "*(No text provided)*"
                        
                    answers.append(content)
                    try:
                        await msg.add_reaction("✅")
                    except Exception:
                        pass
                except Exception as e:
                    # Log hidden errors to staff channel
                    staff_channel = guild.get_channel(1551255144233173084)
                    if staff_channel:
                        await staff_channel.send(f"❌ Uncaught error during application loop for {user.mention}: {e}")
                    raise e

            # ── Build and post the application ──────────────────────────
            ch = discord.utils.get(guild.text_channels, name="📋│app-review")
            if not ch:
                await user.send("⚠️ Could not find the review channel. Please contact staff.")
                return

            embed = discord.Embed(
                title="📋  New Application",
                colour=discord.Colour.gold(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(
                name="👤 Applicant",
                value=f"{user.mention} (`{user}`)",
                inline=False,
            )

            for label, answer in zip(_ANSWER_LABELS, answers):
                inline = label not in ("🤝 Agree to Seniors?", "🎯 Tactics & Units")
                embed.add_field(name=label, value=answer, inline=inline)

            embed.set_footer(text=f"User ID: {user.id}  •  Guild: {guild.id}")

            view = discord.ui.View(timeout=None)
            view.add_item(_AcceptBtn(user.id, guild.id))
            view.add_item(_DenyBtn(user.id, guild.id))
            await ch.send(embed=embed, view=view)

            await user.send(
                "✅ **Application submitted!**\n"
                "Staff will review it shortly — you'll be DM'd the result.\n"
                "For now you can read the rules and announcements while you wait."
            )

        except discord.Forbidden:
            pass  # DMs closed — handled in on_member_join fallback
        finally:
            self._active.discard(user.id)

    # ── Manual Apply Command ────────────────────────────────────────────────
    
    @app_commands.command(name="apply", description="Manually start or restart your regiment application")
    async def apply_cmd(self, interaction: discord.Interaction):
        await self._handle_apply(interaction)

    @app_commands.command(name="restart-app", description="Force start your regiment application (use if /apply fails)")
    async def restart_app_cmd(self, interaction: discord.Interaction):
        await self._handle_apply(interaction)

    async def _handle_apply(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        denied_at = await self.bot.db.get_app_cooldown(interaction.user.id)
        if denied_at:
            elapsed = time.time() - denied_at
            if elapsed < APPEAL_COOLDOWN_SECONDS:
                remaining = APPEAL_COOLDOWN_SECONDS - elapsed
                hrs = int(remaining // 3600)
                mins = int((remaining % 3600) // 60)
                return await interaction.followup.send(
                    f"⏳ Your previous application was denied. You must wait **{hrs}h {mins}m** before appealing."
                )

        await interaction.followup.send("📝 Starting your application! Please check your DMs.")
        asyncio.create_task(self._run_application(interaction.user, interaction.guild))


    # ── Application Flow (DMs) ──────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        if member.pending:
            # They haven't accepted server rules yet. 
            # We will process them in on_member_update when they accept.
            return

        guild = member.guild

        # Give Unverified role
        unverified = discord.utils.get(guild.roles, name="Unverified")
        if unverified:
            try:
                await member.add_roles(unverified, reason="New member — pending application")
            except discord.Forbidden:
                pass

        # Start DM application
        try:
            await self._run_application(member, guild)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # When a user agrees to the server rules (Membership Screening), they go from pending=True to pending=False
        if before.pending and not after.pending:
            guild = after.guild
            
            # Give Unverified role
            unverified = discord.utils.get(guild.roles, name="Unverified")
            if unverified:
                try:
                    await after.add_roles(unverified, reason="Passed membership screening — pending application")
                except discord.Forbidden:
                    pass

            # Start DM application
            try:
                await self._run_application(after, guild)
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ApplicationCog(bot))
