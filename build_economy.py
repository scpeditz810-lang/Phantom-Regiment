import os

CODE = '''import random
import time
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

SHOP_ITEMS = {
    # Banners
    "galaxy": {"name": "🌌 Galaxy Banner", "price": 1000, "type": "banner", "desc": "A beautiful deep space galaxy background."},
    "neon": {"name": "✨ Neon Cyber", "price": 1500, "type": "banner", "desc": "A glowing cyberpunk neon aesthetic."},
    "camo": {"name": "🪖 Military Camo", "price": 800, "type": "banner", "desc": "A classic tactical camouflage pattern."},
    "fire": {"name": "🔥 Hellfire", "price": 2000, "type": "banner", "desc": "A blazing fire background."},
    
    # Weapons
    "mercenary_sword": {"name": "⚔️ Mercenary's Sword", "price": 1000, "type": "weapon", "min_dmg": 10, "max_dmg": 25, "dodge": 40, "acc": 0, "speed": 0, "desc": "10-25 DMG | +40% Dodge"},
    "samurai_sword": {"name": "🗡️ Samurai's Sword", "price": 2500, "type": "weapon", "min_dmg": 25, "max_dmg": 40, "dodge": 40, "acc": 0, "speed": 0, "desc": "25-40 DMG | +40% Dodge"},
    "flame_bow": {"name": "🏹 Flame Archer's Bow", "price": 5000, "type": "weapon", "min_dmg": 35, "max_dmg": 60, "dodge": 0, "acc": 30, "speed": 0, "desc": "35-60 DMG | +30% Accuracy"},
    
    # Utility
    "heal_potion": {"name": "🧪 Heal Potion", "price": 500, "type": "utility", "desc": "Consumable: Heals 30 HP during combat."},
    "lancers_horse": {"name": "🐎 Lancer's Horse", "price": 3000, "type": "utility", "desc": "Passive: +15 Speed, +10% Dodge, +10% Accuracy"},
}

class BannerSelect(discord.ui.Select):
    def __init__(self, owned_items: list[str]):
        options = [discord.SelectOption(label="Default Gradient", value="default", description="Equip the standard background")]
        for item_id in owned_items:
            if item_id in SHOP_ITEMS and SHOP_ITEMS[item_id]["type"] == "banner":
                options.append(
                    discord.SelectOption(
                        label=SHOP_ITEMS[item_id]["name"],
                        value=item_id,
                        description="Equip this custom banner!"
                    )
                )
        super().__init__(placeholder="Select a banner to equip...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        bot = interaction.client
        if choice == "default":
            await bot.db.set_active_banner(interaction.user.id, interaction.guild_id, None)
            await interaction.response.send_message("✅ Unequipped your banner. You are using the default background now.", ephemeral=True)
        else:
            await bot.db.set_active_banner(interaction.user.id, interaction.guild_id, choice)
            await interaction.response.send_message(f"✅ Successfully equipped **{SHOP_ITEMS[choice]['name']}**! Run `/rank` to see it.", ephemeral=True)

class BannerView(discord.ui.View):
    def __init__(self, owned_items: list[str]):
        super().__init__(timeout=60)
        self.add_item(BannerSelect(owned_items))


# ── RPS System ─────────────────────────────────────────────────────────
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
            if self.p1_choice: return await interaction.response.send_message("❌ You already chose!", ephemeral=True)
            self.p1_choice = choice
        else:
            if self.p2_choice: return await interaction.response.send_message("❌ You already chose!", ephemeral=True)
            self.p2_choice = choice
            
        await interaction.response.send_message(f"✅ You secretly chose **{choice.title()}**!", ephemeral=True)
        
        if self.p1_choice and self.p2_choice:
            self.stop()
            await self.resolve_game(interaction.message)
        else:
            embed = interaction.message.embeds[0]
            embed.description = f"**{self.challenger.mention}** vs **{self.opponent.mention}**\\n\\n"
            embed.description += f"✅ {self.challenger.mention} locked in.\\n" if self.p1_choice else f"⏳ Waiting for {self.challenger.mention}...\\n"
            embed.description += f"✅ {self.opponent.mention} locked in.\\n" if self.p2_choice else f"⏳ Waiting for {self.opponent.mention}...\\n"
            await interaction.message.edit(embed=embed)

    async def resolve_game(self, message: discord.Message):
        c1, c2 = self.p1_choice, self.p2_choice
        winner = None
        if c1 == c2:
            result = "It's a tie! Both players keep their medals."
        elif (c1 == "rock" and c2 == "scissors") or (c1 == "paper" and c2 == "rock") or (c1 == "scissors" and c2 == "paper"):
            winner, result = self.challenger, f"🎉 {self.challenger.mention} wins **{self.bet} Medals**!"
        else:
            winner, result = self.opponent, f"🎉 {self.opponent.mention} wins **{self.bet} Medals**!"
            
        if winner:
            loser = self.opponent if winner == self.challenger else self.challenger
            await self.bot.db.add_medals(winner.id, message.guild.id, self.bet)
            await self.bot.db.add_medals(loser.id, message.guild.id, -self.bet)
            
        embed = discord.Embed(title="✊🤚✌️ Rock Paper Scissors - RESULTS", description=f"{self.challenger.mention} chose **{c1.title()}**\\n{self.opponent.mention} chose **{c2.title()}**\\n\\n{result}", color=discord.Colour.gold())
        for item in self.children: item.disabled = True
        await message.edit(embed=embed, view=self)

    @discord.ui.button(label="Rock", emoji="✊", style=discord.ButtonStyle.secondary)
    async def rock(self, interaction, button): await self.process_choice(interaction, "rock")
    @discord.ui.button(label="Paper", emoji="🤚", style=discord.ButtonStyle.secondary)
    async def paper(self, interaction, button): await self.process_choice(interaction, "paper")
    @discord.ui.button(label="Scissors", emoji="✌️", style=discord.ButtonStyle.secondary)
    async def scissors(self, interaction, button): await self.process_choice(interaction, "scissors")


# ── Combat System ─────────────────────────────────────────────────────────

class Fighter:
    def __init__(self, member: discord.Member, loadout: list[str]):
        self.member = member
        self.loadout = loadout
        self.hp = 100
        self.speed = 10
        self.accuracy = 70
        self.dodge = 0
        self.potions = 0
        self.weapon_min = 5
        self.weapon_max = 10
        self.weapon_name = "Fists"
        self.action = None # "attack" or "heal"
        
        # Apply loadout stats
        for item_id in loadout:
            if item_id not in SHOP_ITEMS: continue
            item = SHOP_ITEMS[item_id]
            if item["type"] == "weapon":
                self.weapon_name = item["name"]
                self.weapon_min = item["min_dmg"]
                self.weapon_max = item["max_dmg"]
                self.dodge += item["dodge"]
                self.accuracy += item["acc"]
                self.speed += item["speed"]
            elif item_id == "heal_potion":
                self.potions += 1
            elif item_id == "lancers_horse":
                self.speed += 15
                self.dodge += 10
                self.accuracy += 10

class BattleView(discord.ui.View):
    def __init__(self, p1: Fighter, p2: Fighter, bot: commands.Bot, message: discord.Message):
        super().__init__(timeout=300)
        self.p1 = p1
        self.p2 = p2
        self.bot = bot
        self.message = message
        self.log = ["*The battle begins!*"]

    def update_buttons(self):
        self.clear_items()
        
        # Attack Button
        btn_atk = discord.ui.Button(label="Attack", emoji="⚔️", style=discord.ButtonStyle.danger)
        async def atk_callback(interaction: discord.Interaction):
            await self.process_action(interaction, "attack")
        btn_atk.callback = atk_callback
        self.add_item(btn_atk)
        
        # Heal Button
        btn_heal = discord.ui.Button(label="Use Potion", emoji="🧪", style=discord.ButtonStyle.success)
        async def heal_callback(interaction: discord.Interaction):
            await self.process_action(interaction, "heal")
        btn_heal.callback = heal_callback
        self.add_item(btn_heal)

    async def process_action(self, interaction: discord.Interaction, action: str):
        if interaction.user.id not in (self.p1.member.id, self.p2.member.id):
            return await interaction.response.send_message("❌ Not your fight!", ephemeral=True)
            
        fighter = self.p1 if interaction.user.id == self.p1.member.id else self.p2
        
        if fighter.action is not None:
            return await interaction.response.send_message("❌ You already locked in your move!", ephemeral=True)
            
        if action == "heal" and fighter.potions <= 0:
            return await interaction.response.send_message("❌ You don't have any Heal Potions!", ephemeral=True)
            
        fighter.action = action
        await interaction.response.send_message(f"✅ Locked in: **{action.title()}**", ephemeral=True)
        
        if self.p1.action and self.p2.action:
            await self.resolve_turn()
        else:
            await self.update_embed()

    async def resolve_turn(self):
        # Determine order by speed (random tiebreaker)
        if self.p1.speed > self.p2.speed: order = [(self.p1, self.p2), (self.p2, self.p1)]
        elif self.p2.speed > self.p1.speed: order = [(self.p2, self.p1), (self.p1, self.p2)]
        else:
            order = [(self.p1, self.p2), (self.p2, self.p1)]
            random.shuffle(order)
            
        self.log = []
        for attacker, defender in order:
            if attacker.hp <= 0: continue
            
            if attacker.action == "heal":
                attacker.hp = min(100, attacker.hp + 30)
                attacker.potions -= 1
                self.log.append(f"🧪 **{attacker.member.display_name}** used a Potion and healed 30 HP!")
            elif attacker.action == "attack":
                # Accuracy check
                hit_chance = attacker.accuracy - defender.dodge
                roll = random.randint(1, 100)
                if roll <= hit_chance:
                    dmg = random.randint(attacker.weapon_min, attacker.weapon_max)
                    defender.hp -= dmg
                    self.log.append(f"⚔️ **{attacker.member.display_name}** hit for **{dmg} DMG**!")
                else:
                    self.log.append(f"💨 **{attacker.member.display_name}** missed! (Dodged)")
                    
        # Reset actions
        self.p1.action = None
        self.p2.action = None
        
        if self.p1.hp <= 0 or self.p2.hp <= 0:
            self.stop()
            winner = self.p1 if self.p1.hp > 0 else self.p2
            loser = self.p2 if self.p1.hp > 0 else self.p1
            # Prize
            data = await self.bot.db.get_user(loser.member.id, self.message.guild.id)
            prize = min(500, int(data.get("medals", 0) * 0.1))
            if prize > 0:
                await self.bot.db.add_medals(winner.member.id, self.message.guild.id, prize)
                await self.bot.db.add_medals(loser.member.id, self.message.guild.id, -prize)
            self.log.append(f"\\n🏆 **{winner.member.display_name}** WINS! They stole **{prize} Medals**!")
            self.clear_items()
            
        await self.update_embed()

    async def update_embed(self):
        embed = discord.Embed(title="⚔️ ARENA COMBAT", color=0xE74C3C)
        embed.add_field(name=f"{self.p1.member.display_name}", value=f"**HP:** {max(0, self.p1.hp)}/100\\n**Weapon:** {self.p1.weapon_name}\\n*{'✅ Ready' if self.p1.action else '⏳ Waiting...'}*", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=f"{self.p2.member.display_name}", value=f"**HP:** {max(0, self.p2.hp)}/100\\n**Weapon:** {self.p2.weapon_name}\\n*{'✅ Ready' if self.p2.action else '⏳ Waiting...'}*", inline=True)
        embed.description = "\\n".join(self.log)
        if not self.is_finished():
            self.update_buttons()
        await self.message.edit(embed=embed, view=self)


class LoadoutModal(discord.ui.Modal, title="Equip Your Loadout"):
    weapon = discord.ui.TextInput(label="Weapon ID", placeholder="e.g. samurai_sword", required=True)
    util1 = discord.ui.TextInput(label="Utility 1 ID (Optional)", placeholder="e.g. heal_potion", required=False)
    util2 = discord.ui.TextInput(label="Utility 2 ID (Optional)", placeholder="e.g. lancers_horse", required=False)
    
    def __init__(self, bot: commands.Bot, member: discord.Member, callback_fn):
        super().__init__()
        self.bot = bot
        self.member = member
        self.callback_fn = callback_fn
        
    async def on_submit(self, interaction: discord.Interaction):
        owned = await self.bot.db.get_inventory(interaction.user.id, interaction.guild_id)
        loadout = []
        for val in (self.weapon.value, self.util1.value, self.util2.value):
            val = val.strip().lower()
            if not val: continue
            if val not in owned:
                return await interaction.response.send_message(f"❌ You do not own `{val}`! Buy it in the `/shop`.", ephemeral=True)
            loadout.append(val)
            
        await interaction.response.send_message("✅ Loadout locked in!", ephemeral=True)
        await self.callback_fn(self.member, loadout)


class ChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, bot: commands.Bot):
        super().__init__(timeout=300)
        self.challenger = challenger
        self.opponent = opponent
        self.bot = bot
        self.p1_loadout = None
        self.p2_loadout = None
        
    @discord.ui.button(label="Equip Loadout (Challenger)", style=discord.ButtonStyle.primary)
    async def equip_p1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.challenger.id: return await interaction.response.send_message("❌ Not for you!", ephemeral=True)
        async def cb(member, loadout):
            self.p1_loadout = loadout
            await self.check_start(interaction.message)
        await interaction.response.send_modal(LoadoutModal(self.bot, self.challenger, cb))
        
    @discord.ui.button(label="Equip Loadout (Opponent)", style=discord.ButtonStyle.danger)
    async def equip_p2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id: return await interaction.response.send_message("❌ Not for you!", ephemeral=True)
        async def cb(member, loadout):
            self.p2_loadout = loadout
            await self.check_start(interaction.message)
        await interaction.response.send_modal(LoadoutModal(self.bot, self.opponent, cb))
        
    async def check_start(self, message: discord.Message):
        if self.p1_loadout and self.p2_loadout:
            self.stop()
            f1 = Fighter(self.challenger, self.p1_loadout)
            f2 = Fighter(self.opponent, self.p2_loadout)
            battle = BattleView(f1, f2, self.bot, message)
            await battle.update_embed()

# ── Economy Cog ──────────────────────────────────────────────────────────

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
            return await interaction.response.send_message(f"⏳ Wait **{rem//3600}h {(rem%3600)//60}m**!", ephemeral=True)
            
        await self.bot.db.set_last_daily(interaction.user.id, interaction.guild_id, now)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, 100)
        await interaction.response.send_message("🏅 You successfully claimed your **100 Daily Medals**!")

    @app_commands.command(name="balance", description="Check how many Medals you have.")
    async def balance(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(f"🏅 You currently have **{data.get('medals', 0)} Medals**.")

    @app_commands.command(name="coinflip", description="Gamble your Medals against the bot!")
    async def coinflip(self, interaction: discord.Interaction, bet: int):
        if bet <= 0: return await interaction.response.send_message("❌ Bet positive!", ephemeral=True)
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < bet: return await interaction.response.send_message("❌ Not enough Medals!", ephemeral=True)
        if random.choice([True, False]):
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, bet)
            await interaction.response.send_message(f"🎉 **Heads**! Won **{bet} Medals**!")
        else:
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -bet)
            await interaction.response.send_message(f"💀 **Tails**... Lost **{bet} Medals**.")

    @app_commands.command(name="rps", description="Rock Paper Scissors for Medals!")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member, bet: int):
        if opponent.id == interaction.user.id or opponent.bot: return await interaction.response.send_message("❌ Invalid opponent!", ephemeral=True)
        if bet <= 0: return await interaction.response.send_message("❌ Bet positive!", ephemeral=True)
        d1 = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        d2 = await self.bot.db.ensure_user(opponent.id, interaction.guild_id)
        if d1.get("medals", 0) < bet or d2.get("medals", 0) < bet:
            return await interaction.response.send_message("❌ Someone doesn't have enough Medals!", ephemeral=True)
            
        embed = discord.Embed(title="✊🤚✌️ RPS Challenge", description=f"**{interaction.user.mention}** challenged **{opponent.mention}** for **{bet} Medals**!\\nClick below to lock in secretly!", color=discord.Colour.blue())
        await interaction.response.send_message(content=opponent.mention, embed=embed, view=RpsView(interaction.user, opponent, bet, self.bot))

    @app_commands.command(name="shop", description="View the Armory and Banner Shop")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛒 Phantom Regiment Shop", description="Buy items using `/buy <id>`!", color=0x2ECC71)
        for cat_name, type_id in [("🎨 Banners", "banner"), ("⚔️ Weapons", "weapon"), ("🎒 Utility", "utility")]:
            items = []
            for item_id, details in SHOP_ITEMS.items():
                if details["type"] == type_id:
                    items.append(f"**{details['name']}** — 🏅 {details['price']}\\nID: `{item_id}`\\n*{details['desc']}*")
            if items:
                embed.add_field(name=cat_name, value="\\n\\n".join(items), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Buy an item from the shop")
    async def buy(self, interaction: discord.Interaction, item_id: str):
        item_id = item_id.lower()
        if item_id not in SHOP_ITEMS: return await interaction.response.send_message("❌ Item ID not found.", ephemeral=True)
        if await self.bot.db.has_item(interaction.user.id, interaction.guild_id, item_id):
            # Allow buying multiple heal potions? No, keep it simple, one time unlock but infinite use?
            # Wait, user wants heal potion to be consumable. But inventory system checks if they own it.
            # If they own it, they can use it. I will let them own it permanently but it's only 1 use per fight.
            return await interaction.response.send_message("❌ You already own this!", ephemeral=True)
            
        price = SHOP_ITEMS[item_id]["price"]
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < price: return await interaction.response.send_message(f"❌ You need {price} Medals!", ephemeral=True)
            
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -price)
        await self.bot.db.add_inventory(interaction.user.id, interaction.guild_id, item_id)
        await interaction.response.send_message(f"✅ You bought **{SHOP_ITEMS[item_id]['name']}**!")

    @app_commands.command(name="changebanner", description="Equip a custom banner")
    async def changebanner(self, interaction: discord.Interaction):
        owned_items = await self.bot.db.get_inventory(interaction.user.id, interaction.guild_id)
        if not owned_items: return await interaction.response.send_message("❌ You don't own any custom banners yet! Buy some using `/shop`.", ephemeral=True)
        await interaction.response.send_message("Select a banner from your inventory below to equip it:", view=BannerView(owned_items), ephemeral=True)

    @app_commands.command(name="fight", description="Challenge someone to an interactive Arena Battle!")
    async def fight(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.id == interaction.user.id or opponent.bot: return await interaction.response.send_message("❌ Invalid opponent!", ephemeral=True)
        embed = discord.Embed(title="⚔️ ARENA CHALLENGE", description=f"{interaction.user.mention} has challenged {opponent.mention} to a deathmatch!\\n\\nBoth players: Click your button below to equip your Weapon and Utilities from your inventory!", color=0xE74C3C)
        await interaction.response.send_message(content=opponent.mention, embed=embed, view=ChallengeView(interaction.user, opponent, self.bot))

    @app_commands.command(name="givemedals", description="Give Medals to a user (Staff Only)")
    @app_commands.default_permissions(manage_guild=True)
    async def givemedals(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0: return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
        await self.bot.db.add_medals(member.id, interaction.guild_id, amount)
        await interaction.response.send_message(f"✅ Gave **{amount} Medals** to {member.mention}.")

    @app_commands.command(name="removemedals", description="Remove Medals from a user (Staff Only)")
    @app_commands.default_permissions(manage_guild=True)
    async def removemedals(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0: return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
        await self.bot.db.add_medals(member.id, interaction.guild_id, -amount)
        await interaction.response.send_message(f"✅ Removed **{amount} Medals** from {member.mention}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
'''

with open('cogs/economy.py', 'w', encoding='utf-8') as f:
    f.write(CODE)
