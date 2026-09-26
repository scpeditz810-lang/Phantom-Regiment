"""
Staff Application Cog — /staffapplications sends a persistent embed with a
dropdown to apply for staff positions. Applications go through a DM interview
and results are sent to a review channel for commanders to Accept/Deny.
"""

import asyncio
import time
import discord
from discord import app_commands
from discord.ext import commands

# ── Config ────────────────────────────────────────────────────────────────────
STAFF_APP_REVIEW_CHANNEL = 1553463789200875550  # channel where answers are sent

# Commander IDs that can accept/deny (same as squad commanders)
COMMANDER_IDS = {1319203870681071679, 1431779664140959836, 754264189601710100}
# Role that can also accept/deny
REVIEWER_ROLE_ID = 1551265887934218311

POSITIONS = {
    "server_staff": {
        "label": "Server Staff",
        "emoji": "🛡️",
        "description": "Moderate the server and help members",
        "questions": [
            "How old are you?",
            "What is your timezone and how many hours a day can you be active?",
            "Do you have any prior moderation experience? If yes, please describe.",
            "Why do you want to become a Server Staff member?",
            "How would you handle a member breaking the rules?",
            "How long have you been a member of Phantom Regiment?",
            "Are you willing to follow orders from higher-ranking staff?",
        ],
    },
    "recruitment": {
        "label": "Recruitment Management",
        "emoji": "📋",
        "description": "Review applications and recruit new members",
        "questions": [
            "How old are you?",
            "What is your timezone and how many hours a day can you be active?",
            "Why do you want to join the Recruitment team?",
            "How would you evaluate a new applicant's potential?",
            "Do you have experience managing communities or teams?",
            "How many members do you think you can recruit for us?",
            "How long have you been a member of Phantom Regiment?",
            "Are you willing to follow orders from higher-ranking staff?",
        ],
    },
    "events": {
        "label": "Giveaways & Events Management",
        "emoji": "🎉",
        "description": "Organize giveaways, game nights, and events",
        "questions": [
            "How old are you?",
            "What is your timezone and how many hours a day can you be active?",
            "Why do you want to manage Giveaways & Events?",
            "Have you ever hosted or organized events before? Describe them.",
            "What kind of events or giveaways would you plan for the server?",
            "How long have you been a member of Phantom Regiment?",
            "Are you willing to follow orders from higher-ranking staff?",
        ],
    },
}


# ════════════════════════════════════════════════════════════════════════════════
# Reviewer permission check
# ════════════════════════════════════════════════════════════════════════════════

def _can_review(user: discord.User | discord.Member) -> bool:
    """Commander IDs, the special role, or admin can review."""
    if user.id in COMMANDER_IDS:
        return True
    if hasattr(user, "roles"):
        if any(r.id == REVIEWER_ROLE_ID for r in user.roles):
            return True
        if user.guild_permissions.administrator:
            return True
    return False


# ════════════════════════════════════════════════════════════════════════════════
# Persistent Accept / Deny buttons
# ════════════════════════════════════════════════════════════════════════════════

class _StaffAcceptBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"staff:acc:(?P<uid>\d+):(?P<gid>\d+):(?P<pos>\w+)",
):
    def __init__(self, uid: int, gid: int, pos: str):
        super().__init__(discord.ui.Button(
            label="✅ Accept",
            style=discord.ButtonStyle.success,
            custom_id=f"staff:acc:{uid}:{gid}:{pos}",
        ))
        self.uid, self.gid, self.pos = uid, gid, pos

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]), match["pos"])

    async def callback(self, interaction: discord.Interaction):
        if not _can_review(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to review staff applications.", ephemeral=True)

        await interaction.response.defer()

        position = POSITIONS.get(self.pos, {})
        pos_label = position.get("label", self.pos)

        # Update embed
        embed = interaction.message.embeds[0].copy()
        embed.colour = discord.Colour.green()
        embed.add_field(name="✅ Result", value=f"Accepted by {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)

        # DM user
        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        if user:
            try:
                await user.send(
                    f"🎉 **Congratulations!** Your staff application for **{pos_label}** has been **accepted**!\n"
                    f"A staff member will reach out to you with next steps."
                )
            except discord.Forbidden:
                pass


class _StaffDenyBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"staff:den:(?P<uid>\d+):(?P<gid>\d+):(?P<pos>\w+)",
):
    def __init__(self, uid: int, gid: int, pos: str):
        super().__init__(discord.ui.Button(
            label="❌ Deny",
            style=discord.ButtonStyle.danger,
            custom_id=f"staff:den:{uid}:{gid}:{pos}",
        ))
        self.uid, self.gid, self.pos = uid, gid, pos

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]), match["pos"])

    async def callback(self, interaction: discord.Interaction):
        if not _can_review(interaction.user):
            return await interaction.response.send_message("❌ You don't have permission to review staff applications.", ephemeral=True)

        await interaction.response.defer()

        position = POSITIONS.get(self.pos, {})
        pos_label = position.get("label", self.pos)

        embed = interaction.message.embeds[0].copy()
        embed.colour = discord.Colour.red()
        embed.add_field(name="❌ Result", value=f"Denied by {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)

        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        if user:
            try:
                await user.send(f"❌ Your staff application for **{pos_label}** has been denied. Better luck next time!")
            except discord.Forbidden:
                pass


# ════════════════════════════════════════════════════════════════════════════════
# Persistent Position Dropdown (survives restarts)
# ════════════════════════════════════════════════════════════════════════════════

class _StaffPositionSelect(
    discord.ui.DynamicItem[discord.ui.Select],
    template=r"staff:apply_select",
):
    def __init__(self):
        select = discord.ui.Select(
            placeholder="Choose a position to apply for...",
            custom_id="staff:apply_select",
            options=[
                discord.SelectOption(
                    label=pos["label"],
                    value=key,
                    emoji=pos["emoji"],
                    description=pos["description"],
                )
                for key, pos in POSITIONS.items()
            ],
        )
        super().__init__(select)

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls()

    async def callback(self, interaction: discord.Interaction):
        pos_key = self.item.values[0]
        position = POSITIONS[pos_key]

        # Check if verified
        roblox_link = await interaction.client.db.get_roblox_link(interaction.user.id)
        if not roblox_link:
            return await interaction.response.send_message("❌ You must link your Roblox account using `/verify` before applying for staff.", ephemeral=True)

        # Get the cog to run the DM interview
        cog: StaffApplyCog | None = interaction.client.get_cog("StaffApplyCog")
        if not cog:
            return await interaction.response.send_message("⚠️ Bot error — cog not loaded.", ephemeral=True)

        if interaction.user.id in cog._active:
            return await interaction.response.send_message("⏳ You already have an active application in progress. Please finish it first.", ephemeral=True)

        await interaction.response.send_message(f"📬 Check your DMs! I'm starting your **{position['label']}** application.", ephemeral=True)

        asyncio.create_task(cog._run_staff_application(interaction.user, interaction.guild, pos_key))


class _StaffApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(_StaffPositionSelect())


# ════════════════════════════════════════════════════════════════════════════════
# Cog
# ════════════════════════════════════════════════════════════════════════════════

class StaffApplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._active: set[int] = set()

    async def cog_load(self):
        self.bot.add_dynamic_items(_StaffAcceptBtn, _StaffDenyBtn, _StaffPositionSelect)
        self.bot.add_view(_StaffApplyView())

    # ── DM Interview Loop ─────────────────────────────────────────────────

    async def _run_staff_application(self, user: discord.User, guild: discord.Guild, pos_key: str):
        position = POSITIONS[pos_key]
        questions = position["questions"]

        if user.id in self._active:
            self._active.remove(user.id)
        self._active.add(user.id)

        try:
            intro = discord.Embed(
                title=f"📝 {position['label']} Application",
                description=(
                    f"I'll ask you **{len(questions)} questions** one at a time.\n"
                    "Just type your answer after each question.\n"
                    "You have **5 minutes** per question — take your time!"
                ),
                colour=discord.Colour.blue(),
            )
            try:
                await user.send(embed=intro)
            except discord.Forbidden:
                return

            def check(m: discord.Message) -> bool:
                return m.author.id == user.id and m.guild is None

            answers = []
            for i, q in enumerate(questions, start=1):
                if user.id not in self._active:
                    return

                embed = discord.Embed(description=f"**{i}.** {q}")
                embed.set_footer(text=f"Question {i} of {len(questions)} • Type your answer below")
                embed.colour = discord.Colour.gold()
                await user.send(embed=embed)

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=300)
                except asyncio.TimeoutError:
                    if user.id in self._active:
                        self._active.remove(user.id)
                    try:
                        await user.send("⏰ Application timed out. You can apply again from the staff applications channel.")
                    except discord.HTTPException:
                        pass
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

            # Done asking
            if user.id in self._active:
                self._active.remove(user.id)

            await user.send("✅ **Application complete!** Your answers have been sent to the review team.")

            # Build submission embed
            roblox_link = await self.bot.db.get_roblox_link(user.id)
            roblox_txt = "Not Linked"
            if roblox_link:
                r_disp = roblox_link.get("roblox_display", "Unknown")
                r_user = roblox_link.get("roblox_username", "Unknown")
                roblox_txt = f"{r_disp} (@{r_user})"

            embed = discord.Embed(
                title=f"📋 Staff Application: {position['label']}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.add_field(name="👤 Applicant", value=f"{user.mention} (`{user}`)", inline=False)
            embed.add_field(name="🎮 Roblox Account", value=roblox_txt, inline=False)
            embed.add_field(name="📌 Position", value=f"{position['emoji']} {position['label']}", inline=False)

            for i, (q, a) in enumerate(zip(questions, answers), start=1):
                embed.add_field(name=f"Q{i}. {q}", value=str(a)[:1024], inline=False)

            view = discord.ui.View(timeout=None)
            view.add_item(_StaffAcceptBtn(user.id, guild.id, pos_key))
            view.add_item(_StaffDenyBtn(user.id, guild.id, pos_key))

            # Send to review channel
            review_ch = guild.get_channel(STAFF_APP_REVIEW_CHANNEL)
            if review_ch:
                await review_ch.send(embed=embed, view=view)
            else:
                await user.send("⚠️ Could not find the review channel. Please contact an admin.")

        except Exception as e:
            if user.id in self._active:
                self._active.remove(user.id)
            print(f"Staff application error for {user}: {e}")

    # ── Slash Command ─────────────────────────────────────────────────────

    @app_commands.command(name="staffapplications", description="Send a staff application embed to a channel")
    @app_commands.describe(channel="Channel to post the application embed in")
    async def staffapplications(self, interaction: discord.Interaction, channel: discord.TextChannel):
        # Only commanders or admins can use this
        is_commander = any(r.name == "Commander" for r in interaction.user.roles)
        is_admin = interaction.user.guild_permissions.administrator
        if not is_commander and not is_admin:
            return await interaction.response.send_message("❌ Only Commanders can use this.", ephemeral=True)

        embed = discord.Embed(
            title="📋 STAFF APPLICATIONS",
            description=(
                "Want to join the staff team? Select a position below and complete the application!\n\n"
                "**Available Positions:**\n"
                "🛡️ **Server Staff** — Moderate the server and help members\n"
                "📋 **Recruitment Management** — Review applications and recruit new members\n"
                "🎉 **Giveaways & Events Management** — Organize giveaways, game nights, and events\n\n"
                "*You must be `/verify`'d before applying.*"
            ),
            color=discord.Color.blurple(),
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)

        view = _StaffApplyView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Staff application embed sent to {channel.mention}!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StaffApplyCog(bot))
