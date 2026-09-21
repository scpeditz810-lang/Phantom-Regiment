import random
import re
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks
from discord import app_commands


# ── Duration parser ────────────────────────────────────────────────────────────
_DURATION_RE = re.compile(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?")

GIVEAWAY_HOSTER_ROLE_ID = 1551669862471049416


def parse_duration(text: str) -> int:
    """Convert strings like '1h', '30m', '1d', '2h30m', '1d12h' into total seconds."""
    text = text.strip().lower()
    match = _DURATION_RE.fullmatch(text)
    if not match or not any(match.groups()):
        raise ValueError(f"Invalid duration format: `{text}`. Use combinations of `d`, `h`, `m` (e.g. `1d12h`, `2h30m`).")
    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    total = days * 86400 + hours * 3600 + minutes * 60
    if total <= 0:
        raise ValueError("Duration must be greater than 0.")
    return total


# ── Permission check ──────────────────────────────────────────────────────────
def _can_host(interaction: discord.Interaction) -> bool:
    """Return True if user has the Giveaway Hoster role or manage_guild permission."""
    if interaction.user.guild_permissions.manage_guild:
        return True
    return any(r.id == GIVEAWAY_HOSTER_ROLE_ID for r in interaction.user.roles)


# ── Persistent Enter button (survives bot restarts) ───────────────────────────
class EnterGiveawayButton(discord.ui.DynamicItem[discord.ui.Button],
                          template=r"giveaway:enter:(?P<mid>\d+)"):
    def __init__(self, message_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label="🎉 Enter",
                style=discord.ButtonStyle.green,
                custom_id=f"giveaway:enter:{message_id}",
            )
        )
        self.message_id = message_id

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match[str],
    ):
        return cls(message_id=int(match["mid"]))

    async def callback(self, interaction: discord.Interaction) -> None:
        db = interaction.client.db
        try:
            already = await db.has_giveaway_entry(self.message_id, interaction.user.id)
            if already:
                return await interaction.response.send_message(
                    "❌ You have already entered this giveaway!", ephemeral=True
                )

            await db.add_giveaway_entry(self.message_id, interaction.user.id)
            total = await db.count_giveaway_entries(self.message_id)
            await interaction.response.send_message(
                f"✅ You have entered the giveaway! There are now **{total}** entries.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"❌ Giveaway enter error: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Something went wrong. Please try again.", ephemeral=True
                    )
            except Exception:
                pass


# ── Cog ───────────────────────────────────────────────────────────────────────
class GiveawayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Register the persistent view and start the checker loop."""
        self.bot.add_dynamic_items(EnterGiveawayButton)
        self.giveaway_checker.start()

    async def cog_unload(self):
        self.giveaway_checker.cancel()

    # ── Checker loop ───────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def giveaway_checker(self):
        """Check for expired giveaways every 30 seconds."""
        try:
            expired = await self.bot.db.get_active_giveaways()
            for giveaway in expired:
                await self._end_giveaway(giveaway)
        except Exception as e:
            print(f"⚠️ Giveaway checker error: {e}")

    @giveaway_checker.before_loop
    async def before_giveaway_checker(self):
        import asyncio
        await self.bot.wait_until_ready()
        # Wait until the database connection is fully established
        while not getattr(self.bot, "db", None) or self.bot.db._db is None:
            await asyncio.sleep(1)

    # ── Winner picking & ending ────────────────────────────────────────────
    async def _end_giveaway(self, giveaway: dict):
        """Pick winners, edit embed, ping winners, mark as ended."""
        message_id = giveaway["message_id"]
        channel_id = giveaway["channel_id"]
        prize = giveaway["prize"]
        winner_count = giveaway["winners"]

        channel = self.bot.get_channel(channel_id)
        if not channel:
            await self.bot.db.end_giveaway(message_id)
            return

        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await self.bot.db.end_giveaway(message_id)
            return

        entries = await self.bot.db.get_giveaway_entries(message_id)

        if not entries:
            embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED 🎉",
                description=f"**{prize}**\n\nNo valid entries — no winners.",
                color=0x95A5A6,
            )
            await message.edit(embed=embed, view=None)
            await channel.send(f"⚠️ The giveaway for **{prize}** ended with no entries.")
        else:
            winners = random.sample(entries, min(winner_count, len(entries)))
            winner_mentions = ", ".join(f"<@{uid}>" for uid in winners)

            embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED 🎉",
                description=f"**{prize}**\n\n🏆 **Winner(s):** {winner_mentions}",
                color=0x2ECC71,
            )
            embed.set_footer(text=f"Ended")
            embed.timestamp = discord.utils.utcnow()
            await message.edit(embed=embed, view=None)
            await channel.send(
                f"🎉 Congratulations {winner_mentions}! You won **{prize}**!"
            )

        await self.bot.db.end_giveaway(message_id)

    # ── Slash commands ─────────────────────────────────────────────────────
    @app_commands.command(name="giveaway", description="Start a giveaway!")
    @app_commands.describe(
        duration="How long the giveaway lasts (e.g. 1h, 30m, 1d12h)",
        prize="What are you giving away?",
        winners="Number of winners (default 1)",
    )
    async def giveaway_cmd(
        self,
        interaction: discord.Interaction,
        duration: str,
        prize: str,
        winners: int = 1,
    ):
        if not _can_host(interaction):
            return await interaction.response.send_message(
                "❌ You need the **Giveaway Hoster** role or **Manage Server** permission to host giveaways.",
                ephemeral=True,
            )

        try:
            seconds = parse_duration(duration)
        except ValueError as e:
            return await interaction.response.send_message(str(e), ephemeral=True)

        if winners < 1:
            return await interaction.response.send_message(
                "❌ Winner count must be at least 1.", ephemeral=True
            )

        end_time = time.time() + seconds
        end_dt = datetime.fromtimestamp(end_time)

        embed = discord.Embed(
            title="🎉 GIVEAWAY 🎉",
            description=(
                f"**{prize}**\n\n"
                f"React with the button below to enter!\n\n"
                f"⏰ **Ends:** {discord.utils.format_dt(end_dt, 'R')} ({discord.utils.format_dt(end_dt, 'f')})\n"
                f"🏆 **Winners:** {winners}\n"
                f"🎗️ **Hosted by:** {interaction.user.mention}"
            ),
            color=0xE74C3C,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(text="Ends at")

        await interaction.response.send_message("🎉 Giveaway started!", ephemeral=True)

        # Send the giveaway message with the persistent button
        view = discord.ui.View(timeout=None)
        # We need a placeholder message_id, so send first then edit
        msg = await interaction.channel.send(embed=embed)

        # Now attach the real button with the message ID
        real_view = discord.ui.View(timeout=None)
        real_view.add_item(EnterGiveawayButton(msg.id))
        await msg.edit(view=real_view)

        # Store in DB
        await self.bot.db.create_giveaway(
            message_id=msg.id,
            channel_id=interaction.channel_id,
            guild_id=interaction.guild_id,
            prize=prize,
            winners=winners,
            end_time=end_time,
            host_id=interaction.user.id,
        )

    @app_commands.command(name="greroll", description="Re-roll a new winner for an ended giveaway")
    @app_commands.describe(message_id="The message ID of the ended giveaway")
    async def greroll_cmd(self, interaction: discord.Interaction, message_id: str):
        if not _can_host(interaction):
            return await interaction.response.send_message(
                "❌ You need the **Giveaway Hoster** role or **Manage Server** permission.",
                ephemeral=True,
            )

        try:
            mid = int(message_id)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Invalid message ID.", ephemeral=True
            )

        giveaway = await self.bot.db.get_giveaway(mid)
        if not giveaway:
            return await interaction.response.send_message(
                "❌ No giveaway found with that message ID.", ephemeral=True
            )

        entries = await self.bot.db.get_giveaway_entries(mid)
        if not entries:
            return await interaction.response.send_message(
                "❌ No entries found for that giveaway.", ephemeral=True
            )

        winner = random.choice(entries)
        winner_mention = f"<@{winner}>"

        channel = self.bot.get_channel(giveaway["channel_id"])
        if channel:
            await channel.send(
                f"🎉 The new winner for **{giveaway['prize']}** is {winner_mention}! Congratulations!"
            )

        await interaction.response.send_message(
            f"✅ Re-rolled! New winner: {winner_mention}", ephemeral=True
        )

    @app_commands.command(name="gend", description="Force-end a giveaway early")
    @app_commands.describe(message_id="The message ID of the active giveaway")
    async def gend_cmd(self, interaction: discord.Interaction, message_id: str):
        if not _can_host(interaction):
            return await interaction.response.send_message(
                "❌ You need the **Giveaway Hoster** role or **Manage Server** permission.",
                ephemeral=True,
            )

        try:
            mid = int(message_id)
        except ValueError:
            return await interaction.response.send_message(
                "❌ Invalid message ID.", ephemeral=True
            )

        giveaway = await self.bot.db.get_giveaway(mid)
        if not giveaway:
            return await interaction.response.send_message(
                "❌ No giveaway found with that message ID.", ephemeral=True
            )
        if giveaway["ended"]:
            return await interaction.response.send_message(
                "❌ That giveaway has already ended.", ephemeral=True
            )

        await interaction.response.send_message("✅ Force-ending the giveaway…", ephemeral=True)
        await self._end_giveaway(giveaway)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
