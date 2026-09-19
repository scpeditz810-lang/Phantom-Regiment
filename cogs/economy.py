import random
import time
import asyncio

import discord
from discord.ext import commands
from discord import app_commands

SHOP_ITEMS = {
    "galaxy": {"name": "🌌 Galaxy Banner", "price": 1000, "desc": "A beautiful deep space galaxy background."},
    "neon": {"name": "✨ Neon Cyber", "price": 1500, "desc": "A glowing cyberpunk neon aesthetic."},
    "camo": {"name": "🪖 Military Camo", "price": 800, "desc": "A classic tactical camouflage pattern."},
    "fire": {"name": "🔥 Hellfire", "price": 2000, "desc": "A blazing fire background."},
}

class RpsView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, bet: int, bot: commands.Bot):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.opponent = opponent
        self.bet = bet
        self.bot = bot
        
        self.p1_choice: str | None = None
        self.p2_choice: str | None = None
        
    async def process_choice(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id not in (self.challenger.id, self.opponent.id):
            return await interaction.response.send_message("❌ This is not your game!", ephemeral=True)
            
        if interaction.user.id == self.challenger.id:
            if self.p1_choice:
                return await interaction.response.send_message("❌ You already chose!", ephemeral=True)
            self.p1_choice = choice
        else:
            if self.p2_choice:
                return await interaction.response.send_message("❌ You already chose!", ephemeral=True)
            self.p2_choice = choice
            
        await interaction.response.send_message(f"✅ You secretly chose **{choice.title()}**!", ephemeral=True)
        
        if self.p1_choice and self.p2_choice:
            self.stop()
            await self.resolve_game(interaction.message)
        else:
            embed = interaction.message.embeds[0]
            embed.description = f"**{self.challenger.mention}** vs **{self.opponent.mention}**\n\n"
            if self.p1_choice:
                embed.description += f"✅ {self.challenger.mention} has locked in their choice.\n"
            else:
                embed.description += f"⏳ Waiting for {self.challenger.mention}...\n"
                
            if self.p2_choice:
                embed.description += f"✅ {self.opponent.mention} has locked in their choice.\n"
            else:
                embed.description += f"⏳ Waiting for {self.opponent.mention}...\n"
                
            await interaction.message.edit(embed=embed)

    async def resolve_game(self, message: discord.Message):
        c1, c2 = self.p1_choice, self.p2_choice
        winner = None
        
        if c1 == c2:
            result = "It's a tie! Both players keep their medals."
        elif (c1 == "rock" and c2 == "scissors") or \
             (c1 == "paper" and c2 == "rock") or \
             (c1 == "scissors" and c2 == "paper"):
            winner = self.challenger
            result = f"🎉 {self.challenger.mention} wins **{self.bet} Medals**!"
        else:
            winner = self.opponent
            result = f"🎉 {self.opponent.mention} wins **{self.bet} Medals**!"
            
        if winner:
            loser = self.opponent if winner == self.challenger else self.challenger
            await self.bot.db.add_medals(winner.id, message.guild.id, self.bet)
            await self.bot.db.add_medals(loser.id, message.guild.id, -self.bet)
            
        embed = discord.Embed(
            title="✊🤚✌️ Rock Paper Scissors - RESULTS",
            description=f"{self.challenger.mention} chose **{c1.title()}**\n{self.opponent.mention} chose **{c2.title()}**\n\n{result}",
            color=discord.Colour.gold()
        )
        for item in self.children:
            item.disabled = True
        await message.edit(embed=embed, view=self)

    @discord.ui.button(label="Rock", emoji="✊", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "rock")

    @discord.ui.button(label="Paper", emoji="🤚", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "paper")

    @discord.ui.button(label="Scissors", emoji="✌️", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_choice(interaction, "scissors")


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="daily", description="Claim your daily 100 Medals!")
    async def daily(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_daily", 0)
        
        if now - last < 86400:
            rem = int(86400 - (now - last))
            h, m = rem // 3600, (rem % 3600) // 60
            return await interaction.response.send_message(f"⏳ You must wait **{h}h {m}m** before claiming your next daily!", ephemeral=True)
            
        await self.bot.db.set_last_daily(interaction.user.id, interaction.guild_id, now)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, 100)
        
        await interaction.response.send_message("🏅 You successfully claimed your **100 Daily Medals**!")

    @app_commands.command(name="balance", description="Check how many Medals you have.")
    async def balance(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        medals = data.get("medals", 0)
        await interaction.response.send_message(f"🏅 You currently have **{medals} Medals**.")

    @app_commands.command(name="coinflip", description="Gamble your Medals against the bot!")
    @app_commands.describe(bet="How many medals to bet")
    async def coinflip(self, interaction: discord.Interaction, bet: int):
        if bet <= 0:
            return await interaction.response.send_message("❌ You must bet a positive amount!", ephemeral=True)
            
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < bet:
            return await interaction.response.send_message("❌ You don't have enough Medals to bet that much!", ephemeral=True)
            
        won = random.choice([True, False])
        if won:
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, bet)
            msg = f"🎉 The coin landed on **Heads**! You won **{bet} Medals**! (New balance: {data.get('medals', 0) + bet})"
        else:
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -bet)
            msg = f"💀 The coin landed on **Tails**... You lost **{bet} Medals**. (New balance: {data.get('medals', 0) - bet})"
            
        await interaction.response.send_message(msg)

    @app_commands.command(name="rps", description="Challenge another player to Rock Paper Scissors for Medals!")
    @app_commands.describe(opponent="The player to challenge", bet="Medals to bet")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member, bet: int):
        if opponent.id == interaction.user.id or opponent.bot:
            return await interaction.response.send_message("❌ You cannot challenge yourself or a bot!", ephemeral=True)
        if bet <= 0:
            return await interaction.response.send_message("❌ Bet must be positive!", ephemeral=True)
            
        d1 = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        d2 = await self.bot.db.ensure_user(opponent.id, interaction.guild_id)
        
        if d1.get("medals", 0) < bet:
            return await interaction.response.send_message("❌ You don't have enough Medals!", ephemeral=True)
        if d2.get("medals", 0) < bet:
            return await interaction.response.send_message(f"❌ {opponent.mention} doesn't have enough Medals to match that bet!", ephemeral=True)
            
        embed = discord.Embed(
            title="✊🤚✌️ Rock Paper Scissors Challenge",
            description=f"**{interaction.user.mention}** has challenged **{opponent.mention}** for **{bet} Medals**!\n\nBoth players, click a button below to lock in your choice secretly!",
            color=discord.Colour.blue()
        )
        view = RpsView(interaction.user, opponent, bet, self.bot)
        await interaction.response.send_message(content=opponent.mention, embed=embed, view=view)

    @app_commands.command(name="shop", description="View the Banner Shop")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛒 Banner Shop", description="Buy custom backgrounds for your `/rank` card using Medals!\nUse `/buy <item_id>` to purchase.", color=0x2ECC71)
        
        for item_id, details in SHOP_ITEMS.items():
            embed.add_field(name=f"{details['name']} — 🏅 {details['price']} Medals", value=f"ID: `{item_id}`\n{details['desc']}", inline=False)
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    async def buy(self, interaction: discord.Interaction, item_id: str):
        item_id = item_id.lower()
        if item_id not in SHOP_ITEMS:
            return await interaction.response.send_message("❌ Item ID not found. Use `/shop` to see available items.", ephemeral=True)
            
        if await self.bot.db.has_item(interaction.user.id, interaction.guild_id, item_id):
            return await interaction.response.send_message("❌ You already own this banner!", ephemeral=True)
            
        price = SHOP_ITEMS[item_id]["price"]
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < price:
            return await interaction.response.send_message(f"❌ You need **{price} Medals** to buy this!", ephemeral=True)
            
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -price)
        await self.bot.db.add_inventory(interaction.user.id, interaction.guild_id, item_id)
        
        await interaction.response.send_message(f"✅ You successfully bought **{SHOP_ITEMS[item_id]['name']}**!\nUse `/equip {item_id}` to put it on your rank card.")

    @app_commands.command(name="equip", description="Equip a purchased banner to your rank card")
    async def equip(self, interaction: discord.Interaction, item_id: str):
        item_id = item_id.lower()
        if item_id == "none" or item_id == "default":
            await self.bot.db.set_active_banner(interaction.user.id, interaction.guild_id, None)
            return await interaction.response.send_message("✅ Unequipped your banner. You are using the default background now.")
            
        if item_id not in SHOP_ITEMS:
            return await interaction.response.send_message("❌ Invalid Item ID.", ephemeral=True)
            
        if not await self.bot.db.has_item(interaction.user.id, interaction.guild_id, item_id):
            return await interaction.response.send_message("❌ You do not own this banner! Buy it in the `/shop`.", ephemeral=True)
            
        await self.bot.db.set_active_banner(interaction.user.id, interaction.guild_id, item_id)
        await interaction.response.send_message(f"✅ Successfully equipped **{SHOP_ITEMS[item_id]['name']}**! Run `/rank` to see it.")

    # ── Staff commands ──────────────────────────────────────────────────────
    
    @app_commands.command(name="givemedals", description="Give Medals to a user (Staff Only)")
    @app_commands.default_permissions(manage_guild=True)
    async def givemedals(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
        await self.bot.db.add_medals(member.id, interaction.guild_id, amount)
        await interaction.response.send_message(f"✅ Gave **{amount} Medals** to {member.mention}.")

    @app_commands.command(name="removemedals", description="Remove Medals from a user (Staff Only)")
    @app_commands.default_permissions(manage_guild=True)
    async def removemedals(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
        await self.bot.db.add_medals(member.id, interaction.guild_id, -amount)
        await interaction.response.send_message(f"✅ Removed **{amount} Medals** from {member.mention}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
