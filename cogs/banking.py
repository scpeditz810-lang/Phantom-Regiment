import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class BankingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    bank = app_commands.Group(name="bank", description="Banking system")
    loan = app_commands.Group(name="loan", description="Player-to-player loans")

    @bank.command(name="create", description="Create a bank account (costs 500 medals)")
    async def bank_create(self, interaction: discord.Interaction):
        try:
            success = await self.bot.db.create_bank(interaction.user.id, interaction.guild.id)
            if success:
                await interaction.response.send_message("Bank account created successfully for 500 medals.")
            else:
                await interaction.response.send_message("Could not create bank account. Do you already have one or lack the 500 medals?", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @bank.command(name="deposit", description="Deposit medals into your bank")
    @app_commands.describe(amount="Amount of medals to deposit")
    async def bank_deposit(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        try:
            success = await self.bot.db.deposit_bank(interaction.user.id, interaction.guild.id, amount)
            if success:
                await interaction.response.send_message(f"Successfully deposited {amount} medals.")
            else:
                await interaction.response.send_message("Could not deposit. Check your balance and account.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @bank.command(name="withdraw", description="Withdraw medals from your bank")
    @app_commands.describe(amount="Amount of medals to withdraw")
    async def bank_withdraw(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
        try:
            success = await self.bot.db.withdraw_bank(interaction.user.id, interaction.guild.id, amount)
            if success:
                await interaction.response.send_message(f"Successfully withdrew {amount} medals.")
            else:
                await interaction.response.send_message("Could not withdraw. Check your bank balance.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @bank.command(name="balance", description="Check your bank balance")
    async def bank_balance(self, interaction: discord.Interaction):
        try:
            balance = await self.bot.db.get_bank(interaction.user.id, interaction.guild.id)
            if balance is not None:
                await interaction.response.send_message(f"Your bank balance is {balance} medals.")
            else:
                await interaction.response.send_message("You do not have a bank account.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @bank.command(name="loan", description="Take a loan from the bank")
    @app_commands.describe(amount="Amount to borrow (max 5000)", days="Duration in days (1, 3, 7, 14, 30)")
    @app_commands.choices(days=[
        app_commands.Choice(name="1 day (5% interest)", value=1),
        app_commands.Choice(name="3 days (12% interest)", value=3),
        app_commands.Choice(name="7 days (20% interest)", value=7),
        app_commands.Choice(name="14 days (35% interest)", value=14),
        app_commands.Choice(name="30 days (50% interest)", value=30)
    ])
    async def bank_loan(self, interaction: discord.Interaction, amount: int, days: int):
        if amount <= 0 or amount > 5000:
            return await interaction.response.send_message("Amount must be between 1 and 5000.", ephemeral=True)
        
        rates = {1: 0.05, 3: 0.12, 7: 0.20, 14: 0.35, 30: 0.50}
        if days not in rates:
            return await interaction.response.send_message("Invalid duration.", ephemeral=True)
            
        interest_rate = rates[days]
        try:
            success = await self.bot.db.create_bank_loan(interaction.user.id, interaction.guild.id, amount, days, interest_rate)
            if success:
                total_repay = int(amount * (1 + interest_rate))
                await interaction.response.send_message(f"You took a loan of {amount} medals for {days} days. You will need to repay {total_repay} medals.")
            else:
                await interaction.response.send_message("Could not process the loan. Do you already have an active loan?", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @bank.command(name="repay", description="Repay your bank loan")
    async def bank_loan_repay(self, interaction: discord.Interaction):
        try:
            success = await self.bot.db.repay_bank_loan(interaction.user.id, interaction.guild.id)
            if success:
                await interaction.response.send_message("You have successfully repaid your bank loan.")
            else:
                await interaction.response.send_message("Could not repay the loan. Ensure you have enough medals.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @loan.command(name="offer", description="Offer a loan to another player")
    @app_commands.describe(user="The user to offer the loan to", amount="Amount of medals", interest="Interest rate percentage", days="Duration in days")
    async def player_loan_offer(self, interaction: discord.Interaction, user: discord.Member, amount: int, interest: float, days: int):
        if amount <= 0 or days <= 0 or interest < 0:
            return await interaction.response.send_message("Invalid loan parameters.", ephemeral=True)
        try:
            loan_id = await self.bot.db.create_player_loan(interaction.user.id, user.id, interaction.guild.id, amount, interest, days)
            if loan_id:
                await interaction.response.send_message(f"Loan offer sent to {user.mention} for {amount} medals at {interest}% interest for {days} days. Loan ID: {loan_id}")
            else:
                await interaction.response.send_message("Could not create loan offer.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @loan.command(name="accept", description="Accept a loan offer")
    @app_commands.describe(loan_id="The ID of the loan offer")
    async def player_loan_accept(self, interaction: discord.Interaction, loan_id: int):
        try:
            success = await self.bot.db.accept_player_loan(interaction.user.id, interaction.guild.id, loan_id)
            if success:
                await interaction.response.send_message(f"Successfully accepted loan {loan_id}.")
            else:
                await interaction.response.send_message("Could not accept the loan. Ensure the offer is valid.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @loan.command(name="repay", description="Repay a player loan")
    @app_commands.describe(loan_id="The ID of the loan to repay")
    async def player_loan_repay(self, interaction: discord.Interaction, loan_id: int):
        try:
            success = await self.bot.db.repay_player_loan(interaction.user.id, interaction.guild.id, loan_id)
            if success:
                await interaction.response.send_message(f"Successfully repaid loan {loan_id}.")
            else:
                await interaction.response.send_message("Could not repay the loan. Ensure you have enough medals.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

    @loan.command(name="list", description="List your active player loans")
    async def player_loan_list(self, interaction: discord.Interaction):
        try:
            loans = await self.bot.db.get_player_loans(interaction.user.id, interaction.guild.id)
            if loans:
                msg = "\n".join([f"ID: {l['id']} | Amount: {l['amount']} | Interest: {l['interest']}% | Status: {l['status']}" for l in loans])
                await interaction.response.send_message(f"**Your Loans:**\n{msg}")
            else:
                await interaction.response.send_message("You have no active player loans.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BankingCog(bot))
