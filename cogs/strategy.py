"""
Strategy cog — players submit strategies for staff review.

Flow
────
1. Player uses /strategy with their strategy text + optional screenshot.
2. Submission posted to the review channel (staff-only) with Approve / Deny buttons.
3. Approve → strategy posted to the public strategies channel for everyone.
4. Deny   → user gets DM'd that their strategy was not approved.
"""

from __future__ import annotations

import discord
from discord.ext import commands
from discord import app_commands

from utils.constants import STAFF_ROLES

_STAFF_NAMES = {r["name"] for r in STAFF_ROLES} | {"Commander"}

# Channel IDs
STRATEGY_REVIEW_CH = 1551255144233173084   # Staff reviews here
STRATEGY_PUBLIC_CH = 1550657827045900379    # Approved strategies go here


# ════════════════════════════════════════════════════════════════════════════════
# Persistent Approve / Deny buttons (survive bot restarts)
# ════════════════════════════════════════════════════════════════════════════════

class _StrategyApproveBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"strat:approve:(?P<uid>\d+):(?P<gid>\d+)",
):
    def __init__(self, uid: int, gid: int):
        super().__init__(discord.ui.Button(
            label="✅ Approve",
            style=discord.ButtonStyle.green,
            custom_id=f"strat:approve:{uid}:{gid}",
        ))
        self.uid, self.gid = uid, gid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]))

    async def callback(self, interaction: discord.Interaction):
        user_roles = {r.name for r in interaction.user.roles}
        has_special = any(r.id == 1550978510229733396 for r in interaction.user.roles)
        if not (user_roles & _STAFF_NAMES) and not has_special:
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        # Get the original embed
        embed = interaction.message.embeds[0].copy()

        # Post to the public strategies channel
        public_ch = interaction.guild.get_channel(STRATEGY_PUBLIC_CH)
        if not public_ch:
            return await interaction.response.send_message("❌ Public strategy channel not found!", ephemeral=True)

        # Build the public embed
        pub_embed = discord.Embed(
            title="📋 Approved Strategy",
            description=embed.description,
            color=0x2ECC71,
            timestamp=discord.utils.utcnow(),
        )
        # Copy the author field (submitter info)
        if embed.author:
            pub_embed.set_author(name=embed.author.name, icon_url=embed.author.icon_url)
        # Copy the screenshot if present
        if embed.image:
            pub_embed.set_image(url=embed.image.url)

        pub_embed.set_footer(text=f"Approved by {interaction.user.display_name}")
        await public_ch.send(embed=pub_embed)

        # Update the review embed
        embed.colour = discord.Colour.green()
        embed.add_field(name="✅ Result", value=f"Approved by {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)

        # DM the user
        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        if user:
            try:
                await user.send("✅ **Your strategy has been approved** and posted for the entire regiment to see! Great work, soldier! ⚔️")
            except discord.Forbidden:
                pass

        # Give the strategy role
        if interaction.guild:
            member = interaction.guild.get_member(self.uid)
            if member:
                role = interaction.guild.get_role(1551265887934218311)
                if role:
                    try:
                        await member.add_roles(role, reason="Strategy approved")
                    except discord.Forbidden:
                        pass

        await interaction.response.send_message("✅ Strategy approved and posted!", ephemeral=True)


class _StrategyDenyBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"strat:deny:(?P<uid>\d+):(?P<gid>\d+)",
):
    def __init__(self, uid: int, gid: int):
        super().__init__(discord.ui.Button(
            label="❌ Deny",
            style=discord.ButtonStyle.danger,
            custom_id=f"strat:deny:{uid}:{gid}",
        ))
        self.uid, self.gid = uid, gid

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]))

    async def callback(self, interaction: discord.Interaction):
        user_roles = {r.name for r in interaction.user.roles}
        has_special = any(r.id == 1550978510229733396 for r in interaction.user.roles)
        if not (user_roles & _STAFF_NAMES) and not has_special:
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)

        embed = interaction.message.embeds[0].copy()
        embed.colour = discord.Colour.red()
        embed.add_field(name="❌ Result", value=f"Denied by {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)

        # DM the user
        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        if user:
            try:
                await user.send("❌ **Your strategy submission was not approved.** Feel free to refine it and submit again!")
            except discord.Forbidden:
                pass

        await interaction.response.send_message("❌ Strategy denied.", ephemeral=True)


# ════════════════════════════════════════════════════════════════════════════════
# Cog
# ════════════════════════════════════════════════════════════════════════════════

class StrategyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_dynamic_items(_StrategyApproveBtn, _StrategyDenyBtn)

    @app_commands.command(name="strategy", description="Submit a strategy for staff review")
    @app_commands.describe(
        strategy="Describe your strategy in detail",
        screenshot="Attach a screenshot to explain better (optional)",
    )
    async def strategy(
        self,
        interaction: discord.Interaction,
        strategy: str,
        screenshot: discord.Attachment | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        review_ch = interaction.guild.get_channel(STRATEGY_REVIEW_CH)
        if not review_ch:
            return await interaction.followup.send("❌ Strategy review channel not found! Contact an admin.")

        embed = discord.Embed(
            title="📋 New Strategy Submission",
            description=strategy,
            color=0xF1C40F,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"User ID: {interaction.user.id}")

        if screenshot:
            embed.set_image(url=screenshot.url)

        view = discord.ui.View(timeout=None)
        view.add_item(_StrategyApproveBtn(interaction.user.id, interaction.guild_id))
        view.add_item(_StrategyDenyBtn(interaction.user.id, interaction.guild_id))

        await review_ch.send(embed=embed, view=view)
        await interaction.followup.send(
            "✅ **Strategy submitted!** Staff will review it shortly. "
            "You'll be DM'd when it's approved or denied."
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(StrategyCog(bot))
