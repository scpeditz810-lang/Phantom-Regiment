import discord
from discord.ext import commands
from discord import app_commands
import time

from discord.ext import tasks

class BankingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_loans.start()
        
    def cog_unload(self):
        self.check_loans.cancel()
        
    @tasks.loop(minutes=10)
    async def check_loans(self):
        now = time.time()
        # 1. Bank loans
        async with self.bot.db._db.execute("SELECT id, user_id, principal, total_owed FROM bank_loans WHERE repaid < total_owed AND due_at < ? AND late_fee_applied = 0", (now,)) as cur:
            bank_loans = await cur.fetchall()
            
        for loan_id, user_id, principal, owed in bank_loans:
            fee = int(principal * 0.20)
            await self.bot.db._db.execute("UPDATE bank_loans SET total_owed = total_owed + ?, late_fee_applied = 1 WHERE id = ?", (fee, loan_id))
            try:
                user = await self.bot.fetch_user(user_id)
                await user.send(f"⚠️ **Bank Loan Overdue!** Your bank loan has expired. A 20% late fee (**{fee:,} medals**) has been added to your debt. Until this is paid, all medals you earn will be automatically seized by the bank.")
            except: pass
            
        # 2. Player loans
        async with self.bot.db._db.execute("SELECT id, borrower_id, principal, total_owed FROM player_loans WHERE status = 'active' AND due_at < ? AND late_fee_applied = 0", (now,)) as cur:
            player_loans = await cur.fetchall()
            
        for loan_id, borrower_id, principal, owed in player_loans:
            fee = int(principal * 0.20)
            await self.bot.db._db.execute("UPDATE player_loans SET total_owed = total_owed + ?, late_fee_applied = 1 WHERE id = ?", (fee, loan_id))
            try:
                user = await self.bot.fetch_user(borrower_id)
                await user.send(f"⚠️ **Player Loan Overdue!** Your player loan #{loan_id} has expired. A 20% late fee (**{fee:,} medals**) has been added. Until this is paid, all medals you earn will be automatically seized and sent to the lender.")
            except: pass
            
        await self.bot.db._db.commit()

    @check_loans.before_loop
    async def before_check_loans(self):
        await self.bot.wait_until_ready()

    bank = app_commands.Group(name="bank", description="Banking system")
    loan = app_commands.Group(name="loan", description="Player-to-player loans")

    @bank.command(name="create", description="Create a bank account (costs 500 medals)")
    async def bank_create(self, interaction: discord.Interaction):
        # Check if already has bank
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if bank:
            return await interaction.response.send_message("❌ You already have a bank account.", ephemeral=True)
            
        # Check wallet
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        if wallet < 500:
            return await interaction.response.send_message("❌ You need **500 medals** in your wallet to open a bank account.", ephemeral=True)
            
        # Create bank and deduct fee
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -500)
        await self.bot.db.create_bank(interaction.user.id, interaction.guild_id)
        
        await interaction.response.send_message("✅ Bank account created successfully! **500 medals** were deducted from your wallet.")

    @bank.command(name="deposit", description="Deposit medals into your bank")
    @app_commands.describe(amount="Amount of medals to deposit")
    async def bank_deposit(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be greater than 0.", ephemeral=True)
            
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if not bank:
            return await interaction.response.send_message("❌ You do not have a bank account. Create one with `/bank create`.", ephemeral=True)
            
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        if wallet < amount:
            return await interaction.response.send_message(f"❌ You don't have enough medals! Your wallet has **{wallet:,}**.", ephemeral=True)
            
        # Transfer
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -amount)
        await self.bot.db.deposit_bank(interaction.user.id, interaction.guild_id, amount)
        
        await interaction.response.send_message(f"✅ Successfully deposited **{amount:,} medals** into your bank.")

    @bank.command(name="withdraw", description="Withdraw medals from your bank")
    @app_commands.describe(amount="Amount of medals to withdraw")
    async def bank_withdraw(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ Amount must be greater than 0.", ephemeral=True)
            
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if not bank:
            return await interaction.response.send_message("❌ You do not have a bank account.", ephemeral=True)
            
        if bank["balance"] < amount:
            return await interaction.response.send_message(f"❌ You don't have enough in your bank! Your bank balance is **{bank['balance']:,}**.", ephemeral=True)
            
        # Transfer
        success = await self.bot.db.withdraw_bank(interaction.user.id, interaction.guild_id, amount)
        if success:
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
            await interaction.response.send_message(f"✅ Successfully withdrew **{amount:,} medals** from your bank.")
        else:
            await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)

    @bank.command(name="balance", description="Check your bank balance")
    async def bank_balance(self, interaction: discord.Interaction):
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        embed = discord.Embed(title="💰 Your Balances", color=discord.Color.green())
        embed.add_field(name="👛 Wallet", value=f"**{wallet:,} 🏅**", inline=True)
        if bank:
            embed.add_field(name="🏦 Bank", value=f"**{bank['balance']:,} 🏅**", inline=True)
        else:
            embed.add_field(name="🏦 Bank", value="*No Account*", inline=True)
            
        await interaction.response.send_message(embed=embed)

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
            return await interaction.response.send_message("❌ Amount must be between 1 and 5,000.", ephemeral=True)
            
        active_loan = await self.bot.db.get_active_bank_loan(interaction.user.id, interaction.guild_id)
        if active_loan:
            return await interaction.response.send_message("❌ You already have an active bank loan! Repay it first.", ephemeral=True)
        
        rates = {1: 0.05, 3: 0.12, 7: 0.20, 14: 0.35, 30: 0.50}
        if days not in rates:
            return await interaction.response.send_message("❌ Invalid duration.", ephemeral=True)
            
        interest_rate = rates[days]
        interest_amount = int(amount * interest_rate)
        due_at = time.time() + (days * 86400)
        
        # Give loan
        await self.bot.db.create_bank_loan(interaction.user.id, interaction.guild_id, amount, interest_amount, due_at)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
        
        total_repay = amount + interest_amount
        await interaction.response.send_message(f"✅ You took a bank loan of **{amount:,} medals** for **{days} days**.\n"
                                                f"You received the funds in your wallet. You must repay **{total_repay:,} medals**.")

    @bank.command(name="repay", description="Repay your bank loan")
    async def bank_loan_repay(self, interaction: discord.Interaction):
        loan = await self.bot.db.get_active_bank_loan(interaction.user.id, interaction.guild_id)
        if not loan:
            return await interaction.response.send_message("❌ You don't have an active bank loan.", ephemeral=True)
            
        owed = loan["total_owed"] - loan["repaid"]
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        if wallet < owed:
            return await interaction.response.send_message(f"❌ You don't have enough medals to repay the loan. You owe **{owed:,}** but only have **{wallet:,}** in your wallet.", ephemeral=True)
            
        # Repay
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -owed)
        await self.bot.db.repay_bank_loan(loan["id"], owed)
        
        await interaction.response.send_message(f"✅ You successfully repaid your bank loan of **{owed:,} medals**!")

    # ── Player Loans ────────────────────────────────────────────────────────
    
    @loan.command(name="offer", description="Offer a loan to another player")
    @app_commands.describe(user="The user to offer the loan to", amount="Amount of medals", interest="Interest rate percentage (e.g. 10)", days="Duration in days")
    async def player_loan_offer(self, interaction: discord.Interaction, user: discord.Member, amount: int, interest: float, days: int):
        if amount <= 0 or days <= 0 or interest < 0:
            return await interaction.response.send_message("❌ Invalid loan parameters.", ephemeral=True)
            
        if user.id == interaction.user.id or user.bot:
            return await interaction.response.send_message("❌ You cannot loan to yourself or a bot.", ephemeral=True)

        lender = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = lender.get("medals", 0) if lender else 0
        if wallet < amount:
            return await interaction.response.send_message(f"❌ You don't have enough medals to lend! Your wallet has **{wallet:,}**.", ephemeral=True)

        interest_medals = int(amount * (interest / 100))
        due_at = time.time() + (days * 86400)
        
        # Deduct from lender (escrow)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -amount)
        
        loan_id = await self.bot.db.create_player_loan(interaction.user.id, user.id, interaction.guild_id, amount, interest_medals, due_at)
        
        await interaction.response.send_message(f"✅ Loan offer sent to {user.mention}! The **{amount:,} medals** have been held from your wallet.\n"
                                                f"They can run `/loan accept {loan_id}` to take it, or `/loan reject {loan_id}` to refund you.")
        try:
            await user.send(f"📬 **{interaction.user.display_name}** has offered you a loan of **{amount:,} medals**!\n"
                            f"**Interest:** {interest}%\n"
                            f"**Total Owed:** {amount + interest_medals:,} medals\n"
                            f"**Duration:** {days} days\n\n"
                            f"Run `/loan accept {loan_id}` in the server to accept it.")
        except:
            pass

    @loan.command(name="accept", description="Accept a loan offer")
    @app_commands.describe(loan_id="The ID of the loan offer")
    async def player_loan_accept(self, interaction: discord.Interaction, loan_id: int):
        loans = await self.bot.db.get_all_player_loans(interaction.user.id, interaction.guild_id)
        # Fetch directly from DB to see pending ones
        async with self.bot.db._db.execute("SELECT * FROM player_loans WHERE id = ? AND borrower_id = ? AND status = 'pending'", (loan_id, interaction.user.id)) as cur:
            row = await cur.fetchone()
            loan = dict(row) if row else None
            
        if not loan:
            return await interaction.response.send_message("❌ No pending loan found with that ID for you.", ephemeral=True)
            
        # Give money to borrower, set status to active
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, loan["principal"])
        await self.bot.db.accept_player_loan(loan_id)
        
        await interaction.response.send_message(f"✅ You accepted the loan! **{loan['principal']:,} medals** have been added to your wallet.\n"
                                                f"You must repay **{loan['total_owed']:,} medals** before it expires.")

    @loan.command(name="reject", description="Reject a loan offer")
    @app_commands.describe(loan_id="The ID of the loan offer")
    async def player_loan_reject(self, interaction: discord.Interaction, loan_id: int):
        async with self.bot.db._db.execute("SELECT * FROM player_loans WHERE id = ? AND borrower_id = ? AND status = 'pending'", (loan_id, interaction.user.id)) as cur:
            row = await cur.fetchone()
            loan = dict(row) if row else None
            
        if not loan:
            return await interaction.response.send_message("❌ No pending loan found with that ID for you.", ephemeral=True)
            
        # Refund lender
        await self.bot.db.add_medals(loan["lender_id"], interaction.guild_id, loan["principal"])
        await self.bot.db._db.execute("UPDATE player_loans SET status = 'rejected' WHERE id = ?", (loan_id,))
        await self.bot.db._db.commit()
        
        await interaction.response.send_message("✅ You rejected the loan. The medals have been returned to the lender.")

    @loan.command(name="repay", description="Repay a player loan")
    @app_commands.describe(loan_id="The ID of the loan to repay")
    async def player_loan_repay(self, interaction: discord.Interaction, loan_id: int):
        async with self.bot.db._db.execute("SELECT * FROM player_loans WHERE id = ? AND borrower_id = ? AND status = 'active'", (loan_id, interaction.user.id)) as cur:
            row = await cur.fetchone()
            loan = dict(row) if row else None
            
        if not loan:
            return await interaction.response.send_message("❌ No active loan found with that ID.", ephemeral=True)
            
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        owed = loan["total_owed"]
        if wallet < owed:
            return await interaction.response.send_message(f"❌ You don't have enough medals to repay! You owe **{owed:,}**.", ephemeral=True)
            
        # Transfer money from borrower to lender
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -owed)
        await self.bot.db.add_medals(loan["lender_id"], interaction.guild_id, owed)
        await self.bot.db.repay_player_loan(loan_id)
        
        await interaction.response.send_message(f"✅ Successfully repaid **{owed:,} medals** to the lender for loan #{loan_id}!")

    @loan.command(name="list", description="List your active player loans")
    async def player_loan_list(self, interaction: discord.Interaction):
        loans = await self.bot.db.get_all_player_loans(interaction.user.id, interaction.guild_id)
        if not loans:
            return await interaction.response.send_message("You have no active player loans.")
            
        embed = discord.Embed(title="📜 Active Player Loans", color=discord.Color.blue())
        for l in loans:
            lender = interaction.guild.get_member(l["lender_id"])
            borrower = interaction.guild.get_member(l["borrower_id"])
            lname = lender.display_name if lender else "Unknown"
            bname = borrower.display_name if borrower else "Unknown"
            
            embed.add_field(
                name=f"Loan #{l['id']}",
                value=f"**Lender:** {lname}\n**Borrower:** {bname}\n**Principal:** {l['principal']:,}\n**Total Owed:** {l['total_owed']:,}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BankingCog(bot))
