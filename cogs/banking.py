import discord
from discord.ext import commands
from discord import app_commands
import time
import random
import hashlib

from discord.ext import tasks

BANK_TIERS = {
    1: {"name": "Basic Vault", "cap": 1000, "upgrade_cost": 0},
    2: {"name": "Iron Vault", "cap": 2500, "upgrade_cost": 2500},
    3: {"name": "Steel Vault", "cap": 7500, "upgrade_cost": 7500},
    4: {"name": "Reinforced Vault", "cap": 20000, "upgrade_cost": 20000},
    5: {"name": "Titanium Vault", "cap": 50000, "upgrade_cost": 50000},
    6: {"name": "Obsidian Vault", "cap": 100000, "upgrade_cost": 120000},
    7: {"name": "Quantum Vault", "cap": 250000, "upgrade_cost": 250000},
    8: {"name": "Cybernetic Vault", "cap": 500000, "upgrade_cost": 500000},
    9: {"name": "Apex Vault", "cap": 750000, "upgrade_cost": 1000000},
    10: {"name": "Phantom Sovereign Vault", "cap": 1000000, "upgrade_cost": 2000000},
}

class BankingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if not getattr(bot, "is_partner", False):
            self.check_loans.start()
        
    def cog_unload(self):
        if not getattr(self.bot, "is_partner", False):
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
                await user.send(f"**Bank Loan Overdue:** Your loan wasn't paid back on time. A 20% late fee (**{fee:,} medals**) was added to what you owe. Repay the loan explicitly with the repayment command; earnings are not withheld automatically.")
            except: pass
            
        # 2. Player loans
        async with self.bot.db._db.execute("SELECT id, borrower_id, principal, total_owed FROM player_loans WHERE status = 'active' AND due_at < ? AND late_fee_applied = 0", (now,)) as cur:
            player_loans = await cur.fetchall()
            
        for loan_id, borrower_id, principal, owed in player_loans:
            fee = int(principal * 0.20)
            await self.bot.db._db.execute("UPDATE player_loans SET total_owed = total_owed + ?, late_fee_applied = 1 WHERE id = ?", (fee, loan_id))
            try:
                user = await self.bot.fetch_user(borrower_id)
                await user.send(f"**Player Loan Overdue:** Your loan #{loan_id} wasn't paid back on time. A 20% late fee (**{fee:,} medals**) was added. Any medals you earn will go toward paying the lender back.")
            except: pass
            
        # 3. Bank Interest (2.5% daily, capped based on vault tier up to 1M)
        async with self.bot.db._db.execute("SELECT user_id, guild_id, balance, last_interest, tier FROM banks WHERE balance > 0 AND last_interest < ?", (now - 86400,)) as cur:
            banks = await cur.fetchall()
            
        for user_id, guild_id, balance, last_interest, tier in banks:
            tier_num = tier or 1
            tier_info = BANK_TIERS.get(tier_num, BANK_TIERS[1])
            interest = min(tier_info["cap"], int(balance * 0.025))
            if interest > 0:
                await self.bot.db._db.execute("UPDATE banks SET balance = balance + ?, last_interest = ? WHERE user_id = ? AND guild_id = ?", (interest, now, user_id, guild_id))
            else:
                await self.bot.db._db.execute("UPDATE banks SET last_interest = ? WHERE user_id = ? AND guild_id = ?", (now, user_id, guild_id))
                
        # 4. Expired pending player loans (24 hours)
        async with self.bot.db._db.execute("SELECT id, lender_id, guild_id, principal FROM player_loans WHERE status = 'pending' AND ? - created_at > 86400", (now,)) as cur:
            expired_offers = await cur.fetchall()
            
        for loan_id, lender_id, guild_id, principal in expired_offers:
            await self.bot.db._db.execute("UPDATE player_loans SET status = 'expired' WHERE id = ?", (loan_id,))
            await self.bot.db.add_medals(lender_id, guild_id, principal)
            try:
                user = await self.bot.fetch_user(lender_id)
                await user.send(f"**Loan Offer Expired:** Your pending loan offer #{loan_id} was not accepted within 24 hours. The **{principal:,} medals** have been refunded to your wallet.")
            except:
                pass

        # 5. Bank Insurance Daily Payouts (10% daily for 7 days)
        async with self.bot.db._db.execute(
            "SELECT id, user_id, guild_id, daily_amount, days_remaining, last_payout FROM bank_insurance WHERE days_remaining > 0 AND last_payout < ?",
            (now - 86400,)
        ) as cur:
            insurances = await cur.fetchall()

        for ins_id, ins_uid, ins_gid, daily_amount, days_rem, last_payout in insurances:
            new_days = days_rem - 1
            await self.bot.db._db.execute(
                "UPDATE banks SET balance = balance + ? WHERE user_id = ? AND guild_id = ?",
                (daily_amount, ins_uid, ins_gid)
            )
            if new_days <= 0:
                await self.bot.db._db.execute("DELETE FROM bank_insurance WHERE id = ?", (ins_id,))
            else:
                await self.bot.db._db.execute(
                    "UPDATE bank_insurance SET days_remaining = ?, last_payout = ? WHERE id = ?",
                    (new_days, now, ins_id)
                )
            try:
                ins_user = await self.bot.fetch_user(ins_uid)
                day_num = 7 - new_days
                await ins_user.send(
                    f"**Bank Insurance Payout (Day {day_num}/7)**\n"
                    f"You received **{daily_amount:,} Medals** back into your bank vault.\n"
                    f"• Days Left: {new_days} days ({new_days * daily_amount:,} Medals left to receive)\n"
                    f"• Made By Phantom Regiment"
                )
            except:
                pass

        await self.bot.db._db.commit()

    @check_loans.before_loop
    async def before_check_loans(self):
        await self.bot.wait_until_ready()

    bank = app_commands.Group(name="bank", description="Banking system")
    loan = app_commands.Group(name="loan", description="Player-to-player loans")

    @bank.command(name="create", description="Create a bank account (costs 500 medals)")
    async def bank_create(self, interaction: discord.Interaction):
        # Check if already has bank
        existing = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if existing:
            return await interaction.response.send_message("❌ You already have a bank account.", ephemeral=True)
            
        # Check wallet
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        if wallet < 500:
            return await interaction.response.send_message("❌ You need **500 medals** in your wallet to open a bank account.", ephemeral=True)
            
        # Show password modal
        await interaction.response.send_modal(BankPasswordModal(self.bot))

    @bank.command(name="changepassword", description="Change your bank password")
    async def bank_changepassword(self, interaction: discord.Interaction):
        existing = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if not existing:
            return await interaction.response.send_message("❌ You don't have a bank account.", ephemeral=True)
        await interaction.response.send_modal(BankChangePasswordModal(self.bot))

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
            
        # Atomic wallet → bank transfer. This prevents a race or double-click
        # from debiting the wallet without crediting the bank.
        success = await self.bot.db.deposit_bank(interaction.user.id, interaction.guild_id, amount)
        if not success:
            return await interaction.response.send_message("❌ Deposit failed: your wallet or bank balance changed. Try again.", ephemeral=True)
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
            
        # Atomic bank → wallet transfer; the database checks the balance again.
        success = await self.bot.db.withdraw_bank(interaction.user.id, interaction.guild_id, amount)
        if success:
            await interaction.response.send_message(f"✅ Successfully withdrew **{amount:,} medals** from your bank.")
        else:
            await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)

    @bank.command(name="balance", description="Check your bank balance")
    async def bank_balance(self, interaction: discord.Interaction):
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        embed = discord.Embed(title="Your Balances", color=discord.Color.green())
        embed.add_field(name="Wallet", value=f"**{wallet:,} Medals**", inline=True)
        if bank:
            tier_num = bank.get("tier") or 1
            tier_info = BANK_TIERS.get(tier_num, BANK_TIERS[1])
            embed.add_field(name="Bank", value=f"**{bank['balance']:,} Medals**", inline=True)
            embed.add_field(
                name="Vault Tier",
                value=f"**Tier {tier_num}/10** — {tier_info['name']}\nDaily Interest Cap: **{tier_info['cap']:,} Medals/day** (2.5% yield)",
                inline=False
            )
        else:
            embed.add_field(name="Bank", value="*No Account (Use `/bank create`)*", inline=True)
            
        embed.set_footer(text="Made By Phantom Regiment")
        await interaction.response.send_message(embed=embed)

    async def _handle_upgrade(self, interaction: discord.Interaction):
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if not bank:
            return await interaction.response.send_message("❌ You do not have a bank account. Create one with `/bank create`.", ephemeral=True)
            
        current_tier = bank.get("tier") or 1
        if current_tier >= 10:
            return await interaction.response.send_message("Your bank vault is already at the maximum **Tier 10 (Phantom Sovereign Vault)** with a **1,000,000 Medals/day** cap!", ephemeral=True)
            
        next_tier = current_tier + 1
        next_info = BANK_TIERS[next_tier]
        cost = next_info["upgrade_cost"]
        
        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        
        if wallet < cost:
            return await interaction.response.send_message(
                f"❌ You need **{cost:,} Medals** in your wallet to upgrade to **Tier {next_tier} ({next_info['name']})**.\n"
                f"Your wallet only has **{wallet:,} Medals**.",
                ephemeral=True
            )
            
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -cost)
        await self.bot.db.upgrade_bank_tier(interaction.user.id, interaction.guild_id, next_tier)
        
        if next_tier == 10:
            next_text = "Max Level Reached"
        else:
            next_cost = BANK_TIERS[next_tier + 1]["upgrade_cost"]
            next_text = f"Tier {next_tier + 1} ({next_cost:,} Medals)"

        embed = discord.Embed(
            title="Vault Upgraded",
            description=f"Congratulations! Your bank vault has been upgraded to **Tier {next_tier} — {next_info['name']}**!\n\n"
                        f"• New Daily Interest Cap: **{next_info['cap']:,} Medals/day** (2.5% daily yield)\n"
                        f"• Upgrade Cost Paid: {cost:,} Medals\n"
                        f"• Next Upgrade: {next_text}",
            color=0x2ECC71
        )
        embed.set_footer(text="Made By Phantom Regiment")
        await interaction.response.send_message(embed=embed)

    @bank.command(name="upgrade", description="Upgrade your bank vault tier to increase your daily interest cap (up to 1M)!")
    async def bank_upgrade(self, interaction: discord.Interaction):
        await self._handle_upgrade(interaction)

    @app_commands.command(name="updatebank", description="Upgrade your bank vault tier to increase your daily interest cap (up to 1M)!")
    async def updatebank(self, interaction: discord.Interaction):
        await self._handle_upgrade(interaction)

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
        total_owed = amount + interest_amount
        
        # Give loan
        await self.bot.db.create_bank_loan(interaction.user.id, interaction.guild_id, amount, interest_amount, due_at)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
        
        await interaction.response.send_message(f"✅ You took a bank loan of **{amount:,} medals** for **{days} days**.\n"
                                                f"The medals have been added to your wallet. You need to repay **{total_owed:,} medals**.\n\n"
                                                f"If you don't repay on time, a **20% late fee** is added and repay the loan explicitly; earnings are not withheld automatically.")

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
            
        # Atomic and idempotent repayment; duplicate clicks cannot charge twice.
        if not await self.bot.db.settle_bank_loan(interaction.user.id, loan["id"], owed):
            return await interaction.response.send_message("❌ Repayment failed or was already processed. Your wallet was not charged.", ephemeral=True)
        await interaction.response.send_message(f"✅ You successfully repaid your bank loan of **{owed:,} medals**!")

    # ── Player Loans ────────────────────────────────────────────────────────
    
    @loan.command(name="offer", description="Offer a loan to another player")
    @app_commands.describe(user="The user to offer the loan to", amount="Amount of medals", interest="Interest rate percentage (e.g. 10)", days="Duration in days")
    async def player_loan_offer(self, interaction: discord.Interaction, user: discord.Member, amount: int, interest: float, days: int):
        if amount <= 0 or amount > 50000 or days <= 0 or days > 30 or interest < 0 or interest > 100:
            return await interaction.response.send_message("❌ Invalid loan parameters. Max loan is **50,000 medals**, max interest is **100%**, and max duration is **30 days**.", ephemeral=True)
            
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
        
        try:
            loan_id = await self.bot.db.create_player_loan(
                interaction.user.id, user.id, interaction.guild_id, amount, interest_medals, due_at
            )
        except Exception:
            # Never leave the lender short if creating the loan record fails.
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
            raise
        
        await interaction.response.send_message(f"✅ **Loan Offer Sent!** {interaction.user.mention} has offered {user.mention} a loan of **{amount:,} medals**.\n"
                                                f"**Terms:** {interest}% interest over {days} days. Total repayment: **{amount + interest_medals:,} medals**.\n\n"
                                                f"{user.mention}, run `/loan accept {loan_id}` to take it, or `/loan reject {loan_id}` to decline.\n"
                                                f"*(If not accepted within 24 hours, the offer will expire)*")
        try:
            await user.send(f"**{interaction.user.display_name}** has offered you a loan of **{amount:,} medals**!\n"
                            f"**Interest:** {interest}%\n"
                            f"**Total Owed:** {amount + interest_medals:,} medals\n"
                            f"**Duration:** {days} days\n\n"
                            f"If you don't repay on time, a **20% late fee** is added and earnings are not withheld automatically; repay the loan explicitly.\n\n"
                            f"Type `/loan accept {loan_id}` in the server to accept it. *(Expires in 24 hours)*")
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
                                                f"Make sure to repay **{loan['total_owed']:,} medals** before it expires.\n\n"
                                                f"If you don't repay on time, a **20% late fee** is added and earnings are not withheld automatically; repay the loan explicitly.")

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
            
        # Atomic and idempotent borrower → lender settlement.
        if not await self.bot.db.settle_player_loan(interaction.user.id, loan_id):
            return await interaction.response.send_message("❌ Repayment failed or was already processed. Your wallet was not charged.", ephemeral=True)
        await interaction.response.send_message(f"✅ Successfully repaid **{owed:,} medals** to the lender for loan #{loan_id}!")

    @loan.command(name="list", description="List your active player loans")
    async def player_loan_list(self, interaction: discord.Interaction):
        loans = await self.bot.db.get_all_player_loans(interaction.user.id, interaction.guild_id)
        if not loans:
            return await interaction.response.send_message("You have no active player loans.")
            
        embed = discord.Embed(title="Active Player Loans", color=discord.Color.blue())
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

    async def _execute_rob(self, interaction: discord.Interaction, user: discord.Member, password: str):
        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ You cannot rob your own bank vault!", ephemeral=True)
            
        if user.bot:
            return await interaction.response.send_message("❌ Bots do not have bank vaults.", ephemeral=True)

        target_bank = await self.bot.db.get_bank(user.id, interaction.guild_id)
        if not target_bank:
            return await interaction.response.send_message(f"❌ {user.display_name} does not have a bank account.", ephemeral=True)

        balance = target_bank.get("balance", 0)
        if balance <= 0:
            return await interaction.response.send_message(f"❌ {user.display_name}'s bank vault has no medals inside.", ephemeral=True)

        now = time.time()
        last_attempt = await self.bot.db.get_rob_cooldown(interaction.user.id, user.id, interaction.guild_id)
        COOLDOWN = 1800  # 30 minutes cooldown per target
        if now - last_attempt < COOLDOWN:
            rem = int(COOLDOWN - (now - last_attempt))
            return await interaction.response.send_message(
                f"⏳ You have to wait **{rem // 60}m {rem % 60}s** before trying to rob {user.display_name}'s bank again.",
                ephemeral=True
            )

        # Update cooldown
        await self.bot.db.set_rob_cooldown(interaction.user.id, user.id, interaction.guild_id)

        from utils.cipher import verify_password, generate_password_hint

        stored_hash = target_bank.get("password_hash")
        if not stored_hash:
            return await interaction.response.send_message("❌ This bank account doesn't have a password set yet.", ephemeral=True)

        is_correct = verify_password(password, stored_hash)

        if is_correct:
            # Success! Robber steals the bank balance
            stolen = balance
            await self.bot.db.withdraw_bank(user.id, interaction.guild_id, stolen)
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, stolen)

            # Bank Insurance for Victim:
            # 30% immediate relief returned directly to their bank vault
            immediate_comp = int(stolen * 0.30)
            # Remaining 70% paid over 7 days (10% each day)
            daily_comp = int(stolen * 0.10)
            if immediate_comp > 0:
                await self.bot.db.deposit_bank(user.id, interaction.guild_id, immediate_comp)
            if daily_comp > 0:
                await self.bot.db.create_bank_insurance(user.id, interaction.guild_id, daily_comp, days=7)

            embed = discord.Embed(
                title="Bank Robbed!",
                description=f"{interaction.user.mention} cracked {user.mention}'s bank password!\n\n"
                            f"**Stolen:** **{stolen:,} Medals** sent to {interaction.user.mention}'s wallet!",
                color=0x2ECC71
            )
            embed.set_footer(text="Made By Phantom Regiment")
            await interaction.response.send_message(embed=embed)

            try:
                alert_embed = discord.Embed(
                    title="Your Bank Was Robbed",
                    description=f"**{interaction.user.display_name}** guessed your password in **{interaction.guild.name}** and took **{stolen:,} medals** from your vault!\n\n"
                                f"**Bank Insurance:**\n"
                                f"• **30% back right now:** **{immediate_comp:,} Medals** added back to your bank vault!\n"
                                f"• **Remaining 70%:** You'll get **{daily_comp:,} Medals/day** every day for the next **7 days**!\n\n"
                                f"Change your password soon with `/bank changepassword` so they can't rob you again.",
                    color=0xE74C3C
                )
                alert_embed.set_footer(text="Made By Phantom Regiment")
                await user.send(embed=alert_embed)
            except:
                pass
        else:
            # Failed attempt! Send the robber an encrypted hint of the victim's password
            raw_password = target_bank.get("password")
            hint = generate_password_hint(raw_password) if raw_password else "XXXENCRYPTEDHINTXX"

            # Ephemeral failure message to robber with the clue
            fail_embed = discord.Embed(
                title="Wrong Password",
                description=f"That wasn't the right password for **{user.display_name}**'s bank vault.\n\n"
                            f"Here's a clue to help you guess it next time:\n\n"
                            f"**Password Hint:**\n"
                            f"```\n{hint}\n```\n"
                            f"*(Fill in the missing letters and try again later!)*\n\n"
                            f"You have a **30-minute cooldown** before you can try robbing {user.display_name} again.",
                color=0xE74C3C
            )
            fail_embed.set_footer(text="Made By Phantom Regiment")
            await interaction.response.send_message(embed=fail_embed, ephemeral=True)

            # Send defense alert to victim
            try:
                victim_embed = discord.Embed(
                    title="Someone Tried Robbing Your Bank",
                    description=f"**{interaction.user.display_name}** tried to guess your bank password in **{interaction.guild.name}**, but they got it wrong!\n\n"
                                f"*If you think your password is too easy to guess, change it with `/bank changepassword`.*",
                    color=0xE67E22
                )
                victim_embed.set_footer(text="Made By Phantom Regiment")
                await user.send(embed=victim_embed)
            except:
                pass

    @bank.command(name="rob", description="Try to rob a player's bank vault by guessing their password")
    @app_commands.describe(user="The player you want to rob", password="Your password guess")
    async def bank_rob(self, interaction: discord.Interaction, user: discord.Member, password: str):
        await self._execute_rob(interaction, user, password)

    @app_commands.command(name="rob", description="Try to rob a player's bank vault by guessing their password")
    @app_commands.describe(user="The player you want to rob", password="Your password guess")
    async def rob(self, interaction: discord.Interaction, user: discord.Member, password: str):
        await self._execute_rob(interaction, user, password)

    @bank.command(name="resetall", description="[OWNER ONLY] Wipe all banks, loans, and economy balances")
    async def bank_resetall(self, interaction: discord.Interaction):
        if interaction.user.id != 1162404296097275904 and not await self.bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ Owner only.", ephemeral=True)
        await self.bot.db.hard_reset_all_banks()
        await self.bot.db.add_role_purchase(1162404296097275904, 1550544659217125467, "role_phantom")
        await interaction.response.send_message("All banks, loans, and wallets have been completely wiped! Elite role preserved for TS_Aryan.")

    @commands.command(name="resetbanks")
    async def resetbanks_prefix(self, ctx: commands.Context):
        """Owner prefix command to wipe all banks and economy balances."""
        if ctx.author.id != 1162404296097275904 and not await self.bot.is_owner(ctx.author):
            return await ctx.send("❌ Owner only.")
        await self.bot.db.hard_reset_all_banks()
        await self.bot.db.add_role_purchase(1162404296097275904, 1550544659217125467, "role_phantom")
        await ctx.send("All banks, loans, and wallets have been completely wiped! Elite role preserved for TS_Aryan.")

# ── Bank Password Modals ────────────────────────────────────────────────────

class BankPasswordModal(discord.ui.Modal, title="Set Bank Password"):
    password = discord.ui.TextInput(
        label="Choose a secure password",
        placeholder="Your bank vault password...",
        min_length=4,
        max_length=32,
        style=discord.TextStyle.short,
        required=True
    )
    confirm = discord.ui.TextInput(
        label="Confirm your password",
        placeholder="Type it again to confirm...",
        min_length=4,
        max_length=32,
        style=discord.TextStyle.short,
        required=True
    )
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        
    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != self.confirm.value:
            return await interaction.response.send_message("❌ Passwords don't match! Try again.", ephemeral=True)
        
        existing = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if existing:
            return await interaction.response.send_message("❌ You already have a bank account.", ephemeral=True)

        user = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        wallet = user.get("medals", 0) if user else 0
        if wallet < 500:
            return await interaction.response.send_message("❌ You need **500 medals** in your wallet to open a bank account.", ephemeral=True)

        from utils.cipher import hash_password
        pw_hash = hash_password(self.password.value)
        raw_password = self.password.value
        
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -500)
        await self.bot.db.create_bank(interaction.user.id, interaction.guild_id, pw_hash, raw_password)
        
        await interaction.response.send_message(
            "✅ Bank account created with a secure password! **500 medals** deducted.\n"
            "**Remember your password!** Other players can try to `/rob` your vault by guessing it.", ephemeral=True
        )

class BankChangePasswordModal(discord.ui.Modal, title="Change Bank Password"):
    old_pw = discord.ui.TextInput(label="Current password", style=discord.TextStyle.short, required=True)
    new_pw = discord.ui.TextInput(label="New password", min_length=4, max_length=32, style=discord.TextStyle.short, required=True)
    confirm_pw = discord.ui.TextInput(label="Confirm new password", min_length=4, max_length=32, style=discord.TextStyle.short, required=True)
    
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    async def on_submit(self, interaction: discord.Interaction):
        from utils.cipher import hash_password, verify_password
        
        bank = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        if not bank or not verify_password(self.old_pw.value, bank.get("password_hash", "")):
            return await interaction.response.send_message("❌ Current password is incorrect.", ephemeral=True)
        
        if self.new_pw.value != self.confirm_pw.value:
            return await interaction.response.send_message("❌ New passwords don't match.", ephemeral=True)
        
        await self.bot.db.set_bank_password(
            interaction.user.id, 
            interaction.guild_id, 
            hash_password(self.new_pw.value),
            self.new_pw.value
        )
        await interaction.response.send_message("✅ Bank password changed successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BankingCog(bot))
