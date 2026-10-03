import discord
from discord import app_commands
from discord.ext import commands
import re

class _ConvertAcceptBtn(discord.ui.DynamicItem[discord.ui.Button], template=r"convert:accept:(?P<uid>\d+):(?P<amt>\d+)"):
    def __init__(self, user_id: int, amount: int) -> None:
        super().__init__(
            discord.ui.Button(
                label="✅ Accept & Convert",
                style=discord.ButtonStyle.green,
                custom_id=f"convert:accept:{user_id}:{amount}",
            )
        )
        self.target_user_id = user_id
        self.amount = amount

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(user_id=int(match["uid"]), amount=int(match["amt"]))

    async def callback(self, interaction: discord.Interaction):
        staff_names = {"Commander", "Server Manager", "Admin", "Senior Mod"}
        user_roles = {r.name for r in interaction.user.roles}
        if not (user_roles & staff_names) and not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Only high-ranking staff can accept Robux payouts.", ephemeral=True)

        # Disable buttons
        view = discord.ui.View()
        for child in self.view.children:
            child.disabled = True
        self.view.stop()

        await interaction.message.edit(content="✅ **Accepted** by " + interaction.user.mention, view=view)
        await interaction.response.send_message("You have accepted the conversion. The medals were already deducted.", ephemeral=True)
        
        # Notify the user
        target = interaction.guild.get_member(self.target_user_id)
        if target:
            try:
                await target.send(f"✅ Your request to convert **{self.amount:,} Medals** to Robux has been **ACCEPTED**!")
            except:
                pass


class _ConvertDenyBtn(discord.ui.DynamicItem[discord.ui.Button], template=r"convert:deny:(?P<uid>\d+):(?P<amt>\d+)"):
    def __init__(self, user_id: int, amount: int) -> None:
        super().__init__(
            discord.ui.Button(
                label="❌ Deny & Refund",
                style=discord.ButtonStyle.danger,
                custom_id=f"convert:deny:{user_id}:{amount}",
            )
        )
        self.target_user_id = user_id
        self.amount = amount

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(user_id=int(match["uid"]), amount=int(match["amt"]))

    async def callback(self, interaction: discord.Interaction):
        staff_names = {"Commander", "Server Manager", "Admin", "Senior Mod"}
        user_roles = {r.name for r in interaction.user.roles}
        if not (user_roles & staff_names) and not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ Only high-ranking staff can deny Robux payouts.", ephemeral=True)

        # Refund the medals
        await interaction.client.db.add_medals(self.target_user_id, interaction.guild_id, self.amount)

        # Disable buttons
        view = discord.ui.View()
        for child in self.view.children:
            child.disabled = True
        self.view.stop()

        await interaction.message.edit(content="❌ **Denied & Refunded** by " + interaction.user.mention, view=view)
        await interaction.response.send_message("You have denied the conversion. Medals have been refunded.", ephemeral=True)

        # Notify the user
        target = interaction.guild.get_member(self.target_user_id)
        if target:
            try:
                await target.send(f"❌ Your request to convert **{self.amount:,} Medals** has been **DENIED**. Your medals have been refunded.")
            except:
                pass


class ConvertCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.bot.add_dynamic_items(_ConvertAcceptBtn, _ConvertDenyBtn)

    @app_commands.command(name="convertmedals", description="Convert your medals to Robux (25k medals = 10 Robux)")
    @app_commands.describe(amount="Amount of medals to convert", roblox_username="Your Roblox Username")
    @app_commands.guild_only()
    async def convertmedals(self, interaction: discord.Interaction, amount: int, roblox_username: str):
        if amount < 25000:
            return await interaction.response.send_message("❌ You must convert at least **25,000 medals** (10 Robux).", ephemeral=True)
            
        if amount % 2500 != 0:
            return await interaction.response.send_message("❌ Amount must be a multiple of 2,500 (since 2,500 medals = 1 Robux).", ephemeral=True)
            
        # Check if they have active loans
        bank_loan = await self.bot.db.get_active_bank_loan(interaction.user.id, interaction.guild_id)
        player_loans = await self.bot.db.get_all_player_loans(interaction.user.id, interaction.guild_id)
        
        # We need to see if they are a borrower in any player loan
        has_player_loan = any(loan["borrower_id"] == interaction.user.id for loan in player_loans)
        
        if bank_loan or has_player_loan:
            return await interaction.response.send_message("❌ You have an active loan! You cannot convert medals while you owe money.", ephemeral=True)

        # Check balance
        user_data = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        balance = user_data.get("medals", 0) if user_data else 0
        
        if balance < amount:
            return await interaction.response.send_message(f"❌ You don't have enough medals! You only have **{balance:,}**.", ephemeral=True)

        # Deduct medals immediately
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -amount)

        # Send to staff channel
        review_channel = interaction.guild.get_channel(1550657834142793909)
        if not review_channel:
            # Refund if channel doesn't exist to avoid eating medals
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
            return await interaction.response.send_message("❌ Review channel not found. Please contact staff.", ephemeral=True)

        robux = amount // 2500
        
        embed = discord.Embed(
            title="🔄 Robux Conversion Request",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user}`)", inline=False)
        embed.add_field(name="Roblox Username", value=f"**{roblox_username}**", inline=False)
        embed.add_field(name="Medals Sent", value=f"🏅 **{amount:,}**", inline=True)
        embed.add_field(name="Robux Owed", value=f"💵 **{robux:,} R$**", inline=True)
        
        view = discord.ui.View(timeout=None)
        view.add_item(_ConvertAcceptBtn(interaction.user.id, amount))
        view.add_item(_ConvertDenyBtn(interaction.user.id, amount))
        
        await review_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"✅ Your request to convert **{amount:,} medals** into **{robux:,} Robux** has been sent to staff for review! The medals have been deducted from your wallet.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ConvertCog(bot))
