import random
import time
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from utils.constants import ROLES_SHOP

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
    "berserker_axe": {"name": "🪓 Berserker's Axe", "price": 1800, "type": "weapon", "min_dmg": 20, "max_dmg": 35, "dodge": 0, "acc": 0, "speed": 0, "desc": "20-35 DMG"},
    "spartans_shield": {"name": "🛡️ Spartan's Shield", "price": 2200, "type": "utility", "desc": "Passive: +30% Dodge (Block Chance)"},
    "immortals_mask": {"name": "🎭 Immortal's Mask", "price": 2800, "type": "utility", "desc": "Passive: +35% Accuracy"},

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
            
        rps_emojis = {"rock": "✊", "paper": "🤚", "scissors": "✌️"}
        await interaction.response.send_message(f"✅ You secretly chose **{choice.title()}** {rps_emojis.get(choice, '')}!", ephemeral=True)
        
        if self.p1_choice and self.p2_choice:
            self.stop()
            await self.resolve_game(interaction.message)
        else:
            embed = interaction.message.embeds[0]
            embed.description = f"**{self.challenger.mention}** vs **{self.opponent.mention}**\n\n"
            embed.description += f"✅ {self.challenger.mention} locked in.\n" if self.p1_choice else f"⏳ Waiting for {self.challenger.mention}...\n"
            embed.description += f"✅ {self.opponent.mention} locked in.\n" if self.p2_choice else f"⏳ Waiting for {self.opponent.mention}...\n"
            await interaction.message.edit(embed=embed)

    async def resolve_game(self, message: discord.Message):
        c1, c2 = self.p1_choice, self.p2_choice
        rps_emojis = {"rock": "✊", "paper": "🤚", "scissors": "✌️"}
        winner = None
        if c1 == c2:
            result = "🤝 It's a tie! Both players keep their medals."
        elif (c1 == "rock" and c2 == "scissors") or (c1 == "paper" and c2 == "rock") or (c1 == "scissors" and c2 == "paper"):
            winner, result = self.challenger, f"🎉 {self.challenger.mention} wins **{self.bet:,} Medals**!"
        else:
            winner, result = self.opponent, f"🎉 {self.opponent.mention} wins **{self.bet:,} Medals**!"
            
        if winner:
            loser = self.opponent if winner == self.challenger else self.challenger
            await self.bot.db.add_medals(winner.id, message.guild.id, self.bet)
            await self.bot.db.add_medals(loser.id, message.guild.id, -self.bet)
            
        embed = discord.Embed(title="✊🤚✌️ Rock Paper Scissors - RESULTS", description=f"{self.challenger.mention} chose **{c1.title()}** {rps_emojis.get(c1, '')}\n{self.opponent.mention} chose **{c2.title()}** {rps_emojis.get(c2, '')}\n\n{result}", color=discord.Colour.gold())
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
            elif item_id == "spartans_shield":
                self.dodge += 30
            elif item_id == "immortals_mask":
                self.accuracy += 35

class BattleView(discord.ui.View):
    def __init__(self, p1: Fighter, p2: Fighter, bot: commands.Bot, message: discord.Message, bet: int):
        super().__init__(timeout=300)
        self.p1 = p1
        self.p2 = p2
        self.bot = bot
        self.message = message
        self.bet = bet
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
            
            pot = self.bet * 2
            if pot > 0:
                await self.bot.db.add_medals(winner.member.id, self.message.guild.id, pot)
                self.log.append(f"\n🏆 **{winner.member.display_name}** WINS and takes the **{pot:,} Medals** pot!")
            else:
                self.log.append(f"\n🏆 **{winner.member.display_name}** WINS!")
                
            self.clear_items()
            
        await self.update_embed()

    async def update_embed(self):
        embed = discord.Embed(title="⚔️ ARENA COMBAT", color=0xE74C3C)
        embed.add_field(name=f"{self.p1.member.display_name}", value=f"**HP:** {max(0, self.p1.hp)}/100\n**Weapon:** {self.p1.weapon_name}\n*{'✅ Ready' if self.p1.action else '⏳ Waiting...'}*", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=f"{self.p2.member.display_name}", value=f"**HP:** {max(0, self.p2.hp)}/100\n**Weapon:** {self.p2.weapon_name}\n*{'✅ Ready' if self.p2.action else '⏳ Waiting...'}*", inline=True)
        embed.description = "\n".join(self.log)
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
        
        # Helper to validate and add
        def check_and_add(val, slot_type):
            val = val.strip().lower()
            if not val: return None
            if val not in owned:
                return f"❌ You do not own `{val}`! Buy it in the `/shop`."
            if val not in SHOP_ITEMS:
                return f"❌ `{val}` is not a valid item."
            if SHOP_ITEMS[val]["type"] != slot_type:
                return f"❌ `{val}` is not a {slot_type}!"
            if val in loadout:
                return f"❌ You cannot equip `{val}` twice!"
            loadout.append(val)
            return None
            
        err = check_and_add(self.weapon.value, "weapon")
        if err: return await interaction.response.send_message(err, ephemeral=True)
        
        err = check_and_add(self.util1.value, "utility")
        if err: return await interaction.response.send_message(err, ephemeral=True)
        
        err = check_and_add(self.util2.value, "utility")
        if err: return await interaction.response.send_message(err, ephemeral=True)
            
        await interaction.response.send_message("✅ Loadout locked in!", ephemeral=True)
        await self.callback_fn(self.member, loadout)


class ChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, bot: commands.Bot, bet: int):
        super().__init__(timeout=300)
        self.challenger = challenger
        self.opponent = opponent
        self.bot = bot
        self.bet = bet
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
            # Check balances one last time before starting
            u1 = await self.bot.db.get_user(self.challenger.id, message.guild.id)
            u2 = await self.bot.db.get_user(self.opponent.id, message.guild.id)
            if (u1.get("medals", 0) if u1 else 0) < self.bet or (u2.get("medals", 0) if u2 else 0) < self.bet:
                self.stop()
                await message.edit(content="❌ Someone no longer has enough medals for the wager. Fight cancelled.", embed=None, view=None)
                return
                
            # Deduct the bet from both players
            if self.bet > 0:
                await self.bot.db.add_medals(self.challenger.id, message.guild.id, -self.bet)
                await self.bot.db.add_medals(self.opponent.id, message.guild.id, -self.bet)
            
            self.stop()
            f1 = Fighter(self.challenger, self.p1_loadout)
            f2 = Fighter(self.opponent, self.p2_loadout)
            battle = BattleView(f1, f2, self.bot, message, self.bet)
            await battle.update_embed()

# ── Blackjack Helpers & View ──────────────────────────────────────────────

def calculate_hand(hand):
    val = sum(c[1] for c in hand)
    aces = sum(1 for c in hand if c[1] == 11)
    while val > 21 and aces:
        val -= 10
        aces -= 1
    return val

def format_hand(hand):
    return " ".join([c[0] for c in hand])

class BlackjackView(discord.ui.View):
    def __init__(self, bot, user, bet, player_hand, dealer_hand, deck):
        super().__init__(timeout=120)
        self.bot = bot
        self.user = user
        self.bet = bet
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.deck = deck
        
    async def update_embed(self, interaction, final=False):
        p_val = calculate_hand(self.player_hand)
        d_val = calculate_hand(self.dealer_hand)
        
        embed = discord.Embed(title="🃏 Blackjack", color=0x2ECC71 if final else 0x3498DB)
        embed.add_field(name=f"Your Hand ({p_val})", value=format_hand(self.player_hand), inline=False)
        
        if final:
            embed.add_field(name=f"Dealer's Hand ({d_val})", value=format_hand(self.dealer_hand), inline=False)
            
            if p_val > 21:
                res = f"💀 Bust! You lost **{self.bet:,} Medals**."
                embed.color = 0xE74C3C
                await self.bot.db.add_medals(self.user.id, interaction.guild_id, -self.bet)
            elif d_val > 21 or p_val > d_val:
                res = f"🎉 You won **{self.bet:,} Medals**!"
                embed.color = 0x2ECC71
                await self.bot.db.add_medals(self.user.id, interaction.guild_id, self.bet)
            elif p_val == d_val:
                res = "🤝 Push! It's a tie. Your bet was returned."
                embed.color = 0x95A5A6
            else:
                res = f"💀 Dealer wins! You lost **{self.bet:,} Medals**."
                embed.color = 0xE74C3C
                await self.bot.db.add_medals(self.user.id, interaction.guild_id, -self.bet)
                
            embed.description = res
            self.clear_items()
        else:
            embed.add_field(name="Dealer's Hand", value=f"{self.dealer_hand[0][0]} 🂠", inline=False)
            
        await interaction.response.edit_message(embed=embed, view=self if not final else None)

    @discord.ui.button(label="Hit", emoji="🃏", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id: return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
        self.player_hand.append(self.deck.pop())
        if calculate_hand(self.player_hand) > 21:
            await self.update_embed(interaction, final=True)
        else:
            await self.update_embed(interaction)
            
    @discord.ui.button(label="Stand", emoji="🛑", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id: return await interaction.response.send_message("❌ Not your game!", ephemeral=True)
        while calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        await self.update_embed(interaction, final=True)

# ── Trivia View & Questions ────────────────────────────────────────────────

TRIVIA_QUESTIONS = [
    {
        "q": "What is the primary role of a Vanguard in tactical military operations?",
        "options": ["Lead the advance guard", "Provide rear medical support", "Manage supply communications", "Guard artillery reserves"],
        "answer": 0
    },
    {
        "q": "Which classic strategy involves encircling an enemy force to cut off retreat and supplies?",
        "options": ["Scorched Earth", "Pincer / Encirclement", "Fabian Strategy", "Blitzkrieg"],
        "answer": 1
    },
    {
        "q": "In naval warfare, what does the term 'Broadside' refer to?",
        "options": ["Surrendering flag", "Simultaneous fire from one side of a ship", "Ramming enemy bow", "Depth charge pattern"],
        "answer": 1
    },
    {
        "q": "What legendary ancient general crossed the Alps with war elephants in 218 BC?",
        "options": ["Julius Caesar", "Alexander the Great", "Hannibal Barca", "Scipio Africanus"],
        "answer": 2
    },
    {
        "q": "What is a Spartan 'Phalanx' formation primarily known for?",
        "options": ["Horse archer skirmishing", "Dense wall of overlapping shields & spears", "Stealth jungle guerrilla tactics", "High-ground sniper firing lines"],
        "answer": 1
    },
    {
        "q": "Who is the legendary ancient author of 'The Art of War'?",
        "options": ["Sun Tzu", "Miyamoto Musashi", "Carl von Clausewitz", "Laozi"],
        "answer": 0
    },
    {
        "q": "In military aviation, what does the tactical acronym 'CAS' stand for?",
        "options": ["Combat Armored Strike", "Command And Surveillance", "Close Air Support", "Covert Assault Squad"],
        "answer": 2
    },
    {
        "q": "In NATO phonetic alphabet, which code word represents the letter 'P'?",
        "options": ["Phantom", "Papa", "Peter", "Pioneer"],
        "answer": 1
    },
    {
        "q": "Which famous French defense fortification was bypassed during the 1940 Ardennes offensive?",
        "options": ["Siegfried Line", "Maginot Line", "Mannerheim Line", "Hindenburg Line"],
        "answer": 1
    },
    {
        "q": "What tactical maneuver involves a controlled retreat while continuing to inflict damage on the pursuer?",
        "options": ["Fighting Withdrawal", "Kamikaze Rush", "Siege Collapse", "Ambush Route"],
        "answer": 0
    }
]

class TriviaView(discord.ui.View):
    def __init__(self, user: discord.Member, correct_idx: int, reward: int, bot):
        super().__init__(timeout=25)
        self.user = user
        self.correct_idx = correct_idx
        self.reward = reward
        self.bot = bot
        self.answered = False

    async def handle_answer(self, interaction: discord.Interaction, selected_idx: int):
        if interaction.user.id != self.user.id:
            return await interaction.response.send_message("❌ This is not your trivia question!", ephemeral=True)
        if self.answered:
            return
        self.answered = True
        self.stop()

        for i, child in enumerate(self.children):
            child.disabled = True
            if i == self.correct_idx:
                child.style = discord.ButtonStyle.success
            elif i == selected_idx:
                child.style = discord.ButtonStyle.danger

        if selected_idx == self.correct_idx:
            await self.bot.db.add_medals(self.user.id, interaction.guild_id, self.reward)
            embed = discord.Embed(
                title="Correct Answer!",
                description=f"Outstanding tactical intelligence, soldier!\nYou were awarded **{self.reward} Medals**!",
                color=0x2ECC71
            )
        else:
            embed = discord.Embed(
                title="Incorrect",
                description=f"Wrong answer! The correct answer was **Option {chr(65 + self.correct_idx)}**.\nReview your tactical manuals and try again later!",
                color=0xE74C3C
            )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="A", style=discord.ButtonStyle.secondary)
    async def btn_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 0)

    @discord.ui.button(label="B", style=discord.ButtonStyle.secondary)
    async def btn_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 1)

    @discord.ui.button(label="C", style=discord.ButtonStyle.secondary)
    async def btn_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 2)

    @discord.ui.button(label="D", style=discord.ButtonStyle.secondary)
    async def btn_d(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 3)

# ── Economy Cog ──────────────────────────────────────────────────────────

class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        if getattr(self.bot, "is_partner", False):
            self.bot.tree.remove_command("buyrole")
            self.bot.tree.remove_command("roleshop")

    @app_commands.command(name="daily", description="Claim your daily Medals and build a streak!")
    async def daily(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_daily", 0)
        
        if now - last < 86400:
            rem = int(86400 - (now - last))
            return await interaction.response.send_message(f"You already claimed today! Come back in **{rem//3600}h {(rem%3600)//60}m**.", ephemeral=True)
            
        streak_data = await self.bot.db.get_streak(interaction.user.id, interaction.guild_id)
        current_streak = streak_data.get("streak", 0)
        
        if now - last > 172800:
            streak = 1
        else:
            streak = current_streak + 1
            
        await self.bot.db.update_streak(interaction.user.id, interaction.guild_id, streak)
        await self.bot.db.set_last_daily(interaction.user.id, interaction.guild_id, now)
        
        if streak >= 30:
            amount = 1000
        elif streak >= 14:
            amount = 500
        elif streak >= 7:
            amount = 300
        elif streak >= 5:
            amount = 200
        elif streak >= 3:
            amount = 150
        elif streak >= 2:
            amount = 120
        else:
            amount = 100
            
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
        await interaction.response.send_message(f"You claimed your daily **{amount} Medals**! (Current Streak: {streak} days)")

    @app_commands.command(name="work", description="Work for some medals (4h cooldown)")
    async def work(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_work", 0)
        if now - last < 14400:
            rem = int(14400 - (now - last))
            return await interaction.response.send_message(f"You can work again in **{rem//3600}h {(rem%3600)//60}m**.", ephemeral=True)
            
        amount = random.randint(50, 200)
        await self.bot.db.set_last_work(interaction.user.id, interaction.guild_id, now)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, amount)
        
        responses = [
            f"You scrubbed the barracks and earned **{amount} Medals**.",
            f"You went on a patrol and found **{amount} Medals** dropped by an enemy.",
            f"You helped the quartermaster organize supplies for **{amount} Medals**."
        ]
        await interaction.response.send_message(random.choice(responses))

    @app_commands.command(name="weekly", description="Claim your weekly 500 Medals!")
    async def weekly(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_weekly", 0)
        if now - last < 604800:
            rem = int(604800 - (now - last))
            return await interaction.response.send_message(f"You can claim your weekly medals again in **{rem//86400}d {(rem%86400)//3600}h**.", ephemeral=True)
            
        await self.bot.db.set_last_weekly(interaction.user.id, interaction.guild_id, now)
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, 500)
        await interaction.response.send_message("You successfully claimed your weekly **500 Medals**!")

    @app_commands.command(name="crime", description="Commit a high-risk criminal operation for high rewards (2h cooldown)!")
    @app_commands.choices(operation=[
        app_commands.Choice(name="Pickpocket a Civilian (85% win, 75-150 medals)", value="pickpocket"),
        app_commands.Choice(name="Hack an ATM Terminal (65% win, 200-450 medals)", value="hack"),
        app_commands.Choice(name="Hijack a Supply Convoy (45% win, 600-1,200 medals)", value="convoy"),
        app_commands.Choice(name="Infiltrate Rival Clan Base (25% win, 1,500-3,500 medals)", value="infiltrate")
    ])
    async def crime(self, interaction: discord.Interaction, operation: str):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_crime", 0)
        COOLDOWN = 7200  # 2 hours
        if now - last < COOLDOWN:
            rem = int(COOLDOWN - (now - last))
            return await interaction.response.send_message(f"You need to lay low! Wait **{rem//3600}h {(rem%3600)//60}m** before doing another crime.", ephemeral=True)

        ops = {
            "pickpocket": {"chance": 0.85, "min": 75, "max": 150, "fail_penalty": 40, "name": "Pickpocketing"},
            "hack": {"chance": 0.65, "min": 200, "max": 450, "fail_penalty": 100, "name": "ATM Hack"},
            "convoy": {"chance": 0.45, "min": 600, "max": 1200, "fail_penalty": 250, "name": "Supply Convoy Hijack"},
            "infiltrate": {"chance": 0.25, "min": 1500, "max": 3500, "fail_penalty": 500, "name": "Clan Base Infiltration"}
        }
        op = ops[operation]
        await self.bot.db.set_last_crime(interaction.user.id, interaction.guild_id, now)

        if random.random() < op["chance"]:
            payout = random.randint(op["min"], op["max"])
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, payout)
            embed = discord.Embed(
                title="Crime Successful",
                description=f"Your **{op['name']}** went off smoothly!\nYou made off with **{payout:,} Medals**.",
                color=0x2ECC71
            )
        else:
            penalty = op["fail_penalty"]
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -penalty)
            embed = discord.Embed(
                title="Busted!",
                description=f"Your **{op['name']}** went wrong!\nYou got caught and fined **{penalty:,} Medals**.",
                color=0xE74C3C
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="scavenge", description="Scavenge ruins and warzones for hidden medals (45m cooldown)!")
    @app_commands.choices(location=[
        app_commands.Choice(name="Abandoned Military Outpost", value="outpost"),
        app_commands.Choice(name="Dark Tactical Woods", value="woods"),
        app_commands.Choice(name="Ancient War Ruins", value="ruins"),
        app_commands.Choice(name="Sunken Armory Wreck", value="wreck")
    ])
    async def scavenge(self, interaction: discord.Interaction, location: str):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_scavenge", 0)
        COOLDOWN = 2700  # 45 minutes
        if now - last < COOLDOWN:
            rem = int(COOLDOWN - (now - last))
            return await interaction.response.send_message(f"Your squad is resting. Wait **{rem//60}m {rem%60}s** before searching again.", ephemeral=True)

        await self.bot.db.set_last_scavenge(interaction.user.id, interaction.guild_id, now)
        roll = random.random()

        loc_names = {
            "outpost": "the Abandoned Military Outpost",
            "woods": "the Dark Tactical Woods",
            "ruins": "the Ancient War Ruins",
            "wreck": "the Sunken Armory Wreck"
        }
        loc = loc_names.get(location, "the wasteland")

        if roll < 0.10:
            loot = 1000
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, loot)
            embed = discord.Embed(
                title="Jackpot!",
                description=f"While exploring {loc}, you found a hidden supply crate!\nYou opened it and found **{loot:,} Medals**!",
                color=0xF1C40F
            )
        elif roll < 0.45:
            loot = random.randint(250, 500)
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, loot)
            embed = discord.Embed(
                title="Heavy Supply Cache Found",
                description=f"You searched {loc} and recovered a locked supply crate containing **{loot:,} Medals**.",
                color=0x3498DB
            )
        elif roll < 0.85:
            loot = random.randint(50, 180)
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, loot)
            embed = discord.Embed(
                title="Battlefield Scraps Salvaged",
                description=f"You combed through {loc} and salvaged leftover ammunition and equipment worth **{loot:,} Medals**.",
                color=0x95A5A6
            )
        else:
            embed = discord.Embed(
                title="Hostile Ambush",
                description=f"Enemy scouts spotted your squad in {loc}! You were forced to retreat empty-handed before extracting any loot.",
                color=0xE67E22
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="trivia", description="Answer a tactical military quiz question for instant medals (30m cooldown)!")
    async def trivia(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        now = time.time()
        last = data.get("last_trivia", 0)
        COOLDOWN = 1800  # 30 minutes
        if now - last < COOLDOWN:
            rem = int(COOLDOWN - (now - last))
            return await interaction.response.send_message(f"Next quiz available in **{rem//60}m {rem%60}s**.", ephemeral=True)

        await self.bot.db.set_last_trivia(interaction.user.id, interaction.guild_id, now)

        q_data = random.choice(TRIVIA_QUESTIONS)
        reward = random.randint(120, 250)

        embed = discord.Embed(
            title="Tactical Combat Quiz",
            description=f"**{q_data['q']}**\n\n" +
                        f"**A)** {q_data['options'][0]}\n" +
                        f"**B)** {q_data['options'][1]}\n" +
                        f"**C)** {q_data['options'][2]}\n" +
                        f"**D)** {q_data['options'][3]}\n\n" +
                        f"**Reward:** {reward} Medals | *You have 25 seconds to choose!*",
            color=0x9B59B6
        )
        view = TriviaView(interaction.user, q_data["answer"], reward, self.bot)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="transfer", description="Transfer medals to another user (30% tax applied).")
    async def transfer(self, interaction: discord.Interaction, recipient: discord.Member, amount: int):
        if amount <= 0 or amount > 100000: return await interaction.response.send_message("❌ Amount must be between 1 and 100,000 Medals.", ephemeral=True)
        if recipient.id == interaction.user.id or recipient.bot:
            return await interaction.response.send_message("❌ Invalid recipient.", ephemeral=True)
            
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < amount:
            return await interaction.response.send_message(f"❌ You don't have enough Medals to send {amount:,}.", ephemeral=True)
            
        tax = int(amount * 0.30)
        final_amount = amount - tax
        
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -amount)
        await self.bot.db.add_medals(recipient.id, interaction.guild_id, final_amount)
        await interaction.response.send_message(f"You transferred **{amount:,} Medals** to {recipient.mention}.\nAfter a 30% tax (**-{tax:,}**), they received **{final_amount:,} Medals**.")

    @app_commands.command(name="roleshop", description="View the cosmetic roles available for purchase.")
    async def roleshop(self, interaction: discord.Interaction):
        if getattr(self.bot, "is_partner", False):
            return await interaction.response.send_message("❌ `/roleshop` is not available on this bot.", ephemeral=True)
        embed = discord.Embed(title="Cosmetic Role Shop", description="Buy these roles using `/buyrole <role_id>`!", color=0x9B59B6)
        roles_text = []
        for role_id, details in ROLES_SHOP.items():
            roles_text.append(f"**{details['name']}** — {details['price']:,} Medals\nID: `{role_id}`")
        embed.add_field(name="Available Roles", value="\n\n".join(roles_text), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buyrole", description="Purchase or equip a cosmetic role from the role shop.")
    @app_commands.choices(role_id=[
        app_commands.Choice(name="Wealthy (5,000 Medals)", value="role_wealthy"),
        app_commands.Choice(name="Rich (10,000 Medals)", value="role_rich"),
        app_commands.Choice(name="High Roller (15,000 Medals)", value="role_investor"),
        app_commands.Choice(name="Millionaire (25,000 Medals)", value="role_millionaire"),
        app_commands.Choice(name="Billionaire (50,000 Medals)", value="role_billionaire"),
        app_commands.Choice(name="Phantom Regiment Elite (100,000 Medals)", value="role_phantom")
    ])
    async def buyrole(self, interaction: discord.Interaction, role_id: str):
        if getattr(self.bot, "is_partner", False):
            return await interaction.response.send_message("❌ `/buyrole` is not available on this bot.", ephemeral=True)
        if role_id not in ROLES_SHOP:
            return await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            
        role_info = ROLES_SHOP[role_id]
        role = discord.utils.get(interaction.guild.roles, name=role_info["name"])
        
        owned = await self.bot.db.has_role_purchase(interaction.user.id, interaction.guild_id, role_id)
        
        if owned:
            if role:
                try:
                    await interaction.user.add_roles(role, reason="Equipping owned Role Shop role")
                    return await interaction.response.send_message(f"✅ You already own **{role_info['name']}**, so it has been equipped for free!", ephemeral=True)
                except discord.Forbidden:
                    return await interaction.response.send_message("✅ You own this role, but I lack permissions to assign it.", ephemeral=True)
            else:
                pass # Fall through to creation logic if role got deleted
                
        if not owned:
            price = role_info["price"]
            data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
            if data.get("medals", 0) < price:
                return await interaction.response.send_message(f"❌ You need {price:,} Medals to buy this role!", ephemeral=True)
                
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -price)
            await self.bot.db.add_role_purchase(interaction.user.id, interaction.guild_id, role_id)
        
        if not role:
            try:
                role = await interaction.guild.create_role(
                    name=role_info["name"], 
                    color=discord.Color(role_info["color"]),
                    reason="Created for Role Shop"
                )
                alliance_role = discord.utils.get(interaction.guild.roles, name="Alliance")
                if alliance_role:
                    try:
                        await role.edit(position=alliance_role.position + 1)
                    except discord.Forbidden:
                        pass
            except discord.Forbidden:
                return await interaction.response.send_message("✅ Role registered to your account, but I lack permissions to create it in the server.", ephemeral=True)
        
        try:
            await interaction.user.add_roles(role, reason="Purchased from Role Shop")
            if not owned:
                await interaction.response.send_message(f"You successfully purchased and equipped the **{role_info['name']}** role!")
            else:
                await interaction.response.send_message(f"✅ The deleted role was recreated and equipped since you already own it!")
        except discord.Forbidden:
            await interaction.response.send_message("✅ Role registered, but I lack permissions to assign it to you (hierarchy issue).", ephemeral=True)

    @app_commands.command(name="medalleaderboard", description="View the top medal earners in the server.")
    async def medalleaderboard(self, interaction: discord.Interaction):
        top_users = await self.bot.db.get_top_medals(interaction.guild_id, limit=10)
        if not top_users:
            return await interaction.response.send_message("No data found for the leaderboard.")
            
        embed = discord.Embed(title="Medal Leaderboard", color=discord.Colour.gold())
        desc = []
        for i, user_data in enumerate(top_users, 1):
            user_id = user_data["user_id"]
            medals = user_data["medals"]
            user = interaction.guild.get_member(user_id)
            name = user.display_name if user else f"Unknown User ({user_id})"
            desc.append(f"**{i}.** {name} — **{medals:,} Medals**")
            
        embed.description = "\n".join(desc)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="globallb", description="View the top medal earners across all connected clans and servers.")
    async def globallb(self, interaction: discord.Interaction):
        top_users = await self.bot.db.get_global_leaderboard(limit=10)
        if not top_users:
            return await interaction.response.send_message("No data found for the global leaderboard.")
            
        embed = discord.Embed(title="Global Medal Leaderboard", color=0x3498DB)
        desc = []
        for i, user_data in enumerate(top_users, 1):
            user_id = user_data["user_id"]
            medals = user_data["total_medals"]
            user = self.bot.get_user(user_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                except:
                    user = None
            name = user.display_name if user else f"User {user_id}"
            desc.append(f"**{i}.** {name} — **{medals:,} Medals**")
            
        embed.description = "\n".join(desc)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guilds", description="See all servers where this bot is being used")
    async def guilds(self, interaction: discord.Interaction):
        # Dynamically ensure all live guilds from this bot and linked bot are registered
        if hasattr(self.bot, "guilds"):
            bot_tag = "Collation of Rose" if getattr(self.bot, "is_partner", False) else "Phantom Regiment"
            for g in self.bot.guilds:
                try:
                    await self.bot.db.register_guild(g.id, g.name, g.member_count or 0, bot_tag)
                except:
                    pass

        other = getattr(self.bot, "partner_bot", None) or getattr(self.bot, "primary_bot", None)
        if other and hasattr(other, "guilds"):
            other_tag = "Phantom Regiment" if getattr(self.bot, "is_partner", False) else "Collation of Rose"
            for g in other.guilds:
                try:
                    await self.bot.db.register_guild(g.id, g.name, g.member_count or 0, other_tag)
                except:
                    pass

        allied = await self.bot.db.get_allied_guilds()
        if not allied:
            allied = [{"id": g.id, "name": g.name, "member_count": g.member_count, "bot_type": "Phantom Regiment"} for g in self.bot.guilds]

        embed = discord.Embed(
            title="Servers Using This Bot",
            description=f"**Made by Phantom Regiment**\n\nThis bot is currently in **{len(allied)} server(s)**:\n\n",
            color=0x3498DB
        )

        lines = []
        for i, g in enumerate(allied, 1):
            count = f"({g['member_count']:,} members)" if g.get("member_count") else ""
            lines.append(f"**{i}.** **{g['name']}** {count}")

        embed.description += "\n".join(lines)
        embed.set_footer(text="Made By Phantom Regiment")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="datatransfer", description="Check your medals and inventory across servers")
    async def datatransfer(self, interaction: discord.Interaction):
        user_data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        medals = user_data.get("medals", 0) if user_data else 0
        bank_data = await self.bot.db.get_bank(interaction.user.id, interaction.guild_id)
        bank_bal = bank_data.get("balance", 0) if bank_data else 0
        bank_tier = bank_data.get("tier", 1) if bank_data else 1
        streak_data = await self.bot.db.get_streak(interaction.user.id, interaction.guild_id)
        streak = streak_data.get("streak", 0) if streak_data else 0
        inventory = await self.bot.db.get_inventory(interaction.user.id, interaction.guild_id)

        embed = discord.Embed(
            title="Cross-Server Data",
            description=(
                f"**Your medals carry over between servers!**\n\n"
                f"Your balance and items work in both **Phantom Regiment** and **Collation of Rose**:\n\n"
                f"• **Wallet:** **{medals:,} Medals**\n"
                f"• **Bank Vault:** **{bank_bal:,} Medals** (Tier {bank_tier})\n"
                f"• **Items Owned:** **{len(inventory)}**\n"
                f"• **Daily Streak:** **{streak} Days**\n\n"
                f"*Earn medals in either server and spend them anywhere!*"
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="Made By Phantom Regiment")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="balance", description="Check how many Medals you have.")
    async def balance(self, interaction: discord.Interaction):
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(f"You currently have **{data.get('medals', 0):,} Medals**.")

    @app_commands.command(name="coinflip", description="Gamble your Medals against the bot!")
    async def coinflip(self, interaction: discord.Interaction, bet: int):
        if bet <= 0 or bet > 50000: return await interaction.response.send_message("❌ Bet must be between 1 and 50,000 Medals!", ephemeral=True)
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < bet: return await interaction.response.send_message("❌ Not enough Medals!", ephemeral=True)
        if random.choice([True, False]):
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, bet)
            await interaction.response.send_message(f"🪙 **Heads**! Won **{bet:,} Medals**!")
        else:
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -bet)
            await interaction.response.send_message(f"💀 **Tails**... Lost **{bet:,} Medals**.")

    @app_commands.command(name="rps", description="Rock Paper Scissors for Medals!")
    async def rps(self, interaction: discord.Interaction, opponent: discord.Member, bet: int):
        if opponent.id == interaction.user.id or opponent.bot: return await interaction.response.send_message("❌ Invalid opponent!", ephemeral=True)
        if bet <= 0: return await interaction.response.send_message("❌ Bet positive!", ephemeral=True)
        d1 = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        d2 = await self.bot.db.ensure_user(opponent.id, interaction.guild_id)
        if d1.get("medals", 0) < bet or d2.get("medals", 0) < bet:
            return await interaction.response.send_message("❌ Someone doesn't have enough Medals!", ephemeral=True)
            
        embed = discord.Embed(title="✊🤚✌️ RPS Challenge", description=f"**{interaction.user.mention}** challenged **{opponent.mention}** for **{bet:,} Medals**!\nClick below to lock in secretly!", color=discord.Colour.blue())
        await interaction.response.send_message(content=opponent.mention, embed=embed, view=RpsView(interaction.user, opponent, bet, self.bot))

    @app_commands.command(name="shop", description="View the Armory and Banner Shop")
    async def shop(self, interaction: discord.Interaction):
        shop_title = "Collation of Rose" if getattr(self.bot, "is_partner", False) else "Phantom Regiment"
        embed = discord.Embed(title=f"{shop_title} Shop", description="Buy items using `/buy <id>`!", color=0x2ECC71)
        for cat_name, type_id in [("Banners", "banner"), ("Weapons", "weapon"), ("Utility", "utility")]:
            items = []
            for item_id, details in SHOP_ITEMS.items():
                if details["type"] == type_id:
                    items.append(f"**{details['name']}** — {details['price']:,} Medals\nID: `{item_id}`\n*{details['desc']}*")
            if items:
                embed.add_field(name=cat_name, value="\n\n".join(items), inline=False)
        embed.set_footer(text="Made By Phantom Regiment")
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
    @app_commands.describe(opponent="The user to fight", bet="Amount of medals to wager")
    async def fight(self, interaction: discord.Interaction, opponent: discord.Member, bet: int):
        if bet < 0: return await interaction.response.send_message("❌ Bet cannot be negative.", ephemeral=True)
        if opponent.id == interaction.user.id or opponent.bot: return await interaction.response.send_message("❌ Invalid opponent!", ephemeral=True)
        
        # Initial check
        u1 = await self.bot.db.get_user(interaction.user.id, interaction.guild_id)
        u2 = await self.bot.db.get_user(opponent.id, interaction.guild_id)
        u1_medals = u1.get("medals", 0) if u1 else 0
        u2_medals = u2.get("medals", 0) if u2 else 0
        
        if u1_medals < bet:
            return await interaction.response.send_message(f"❌ You don't have enough medals to bet {bet:,}.", ephemeral=True)
        if u2_medals < bet:
            return await interaction.response.send_message(f"❌ {opponent.display_name} doesn't have enough medals to match the bet of {bet:,}.", ephemeral=True)
            
        embed = discord.Embed(title="Arena Challenge", description=f"{interaction.user.mention} has challenged {opponent.mention} to a battle!\n**Wager:** {bet:,} Medals\n\nBoth players: Click your button below to equip your Weapon and Utilities from your inventory!", color=0xE74C3C)
        await interaction.response.send_message(content=opponent.mention, embed=embed, view=ChallengeView(interaction.user, opponent, self.bot, bet))

    @app_commands.command(name="blackjack", description="Play Blackjack against the dealer!")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        if bet <= 0 or bet > 50000: return await interaction.response.send_message("❌ Bet must be between 1 and 50,000 Medals!", ephemeral=True)
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < bet: return await interaction.response.send_message("❌ Not enough Medals!", ephemeral=True)
        
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = [('2', 2), ('3', 3), ('4', 4), ('5', 5), ('6', 6), ('7', 7), ('8', 8), ('9', 9), ('10', 10), ('J', 10), ('Q', 10), ('K', 10), ('A', 11)]
        deck = [(r[0]+s, r[1]) for s in suits for r in ranks]
        random.shuffle(deck)
        
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        
        view = BlackjackView(self.bot, interaction.user, bet, player_hand, dealer_hand, deck)
        
        p_val = calculate_hand(player_hand)
        embed = discord.Embed(title="🃏 Blackjack", color=0x3498DB)
        embed.add_field(name=f"Your Hand ({p_val})", value=format_hand(player_hand), inline=False)
        embed.add_field(name="Dealer's Hand", value=f"{dealer_hand[0][0]} 🂠", inline=False)
        
        if p_val == 21:
            winnings = int(bet * 1.5)
            embed.color = 0x2ECC71
            embed.set_field_at(1, name=f"Dealer's Hand ({calculate_hand(dealer_hand)})", value=format_hand(dealer_hand), inline=False)
            embed.description = f"🎉 **BLACKJACK!** You won **{winnings:,} Medals**!"
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, winnings)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="roulette", description="Bet your Medals on Roulette!")
    @app_commands.choices(bet_type=[
        app_commands.Choice(name="🔴 Red (2x)", value="red"),
        app_commands.Choice(name="⚫ Black (2x)", value="black"),
        app_commands.Choice(name="🟢 Green (36x)", value="green"),
        app_commands.Choice(name="🔢 Even (2x)", value="even"),
        app_commands.Choice(name="🔢 Odd (2x)", value="odd"),
        app_commands.Choice(name="⬆️ High 19-36 (2x)", value="high"),
        app_commands.Choice(name="⬇️ Low 1-18 (2x)", value="low")
    ])
    async def roulette(self, interaction: discord.Interaction, bet: int, bet_type: str):
        if bet <= 0 or bet > 50000: return await interaction.response.send_message("❌ Bet must be between 1 and 50,000 Medals!", ephemeral=True)
        data = await self.bot.db.ensure_user(interaction.user.id, interaction.guild_id)
        if data.get("medals", 0) < bet: return await interaction.response.send_message("❌ Not enough Medals!", ephemeral=True)
        
        # Deduct bet upfront
        await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, -bet)

        reds = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        result = random.randint(0, 36)
        
        is_red = result in reds
        is_black = result != 0 and not is_red
        is_green = result == 0
        is_even = result != 0 and result % 2 == 0
        is_odd = result != 0 and result % 2 != 0
        is_high = 19 <= result <= 36
        is_low = 1 <= result <= 18
        
        won = False
        multiplier = 2
        
        if bet_type == "red" and is_red: won = True
        elif bet_type == "black" and is_black: won = True
        elif bet_type == "green" and is_green: won = True; multiplier = 36
        elif bet_type == "even" and is_even: won = True
        elif bet_type == "odd" and is_odd: won = True
        elif bet_type == "high" and is_high: won = True
        elif bet_type == "low" and is_low: won = True
        
        color_emoji = "🟢" if is_green else ("🔴" if is_red else "⚫")
        
        if won:
            payout = bet * multiplier
            profit = payout - bet
            await self.bot.db.add_medals(interaction.user.id, interaction.guild_id, payout)
            await interaction.response.send_message(f"🎰 The wheel landed on {color_emoji} **{result}**!\n🎉 You won **{payout:,} Medals**! (+{profit:,} profit)")
        else:
            await interaction.response.send_message(f"🎰 The wheel landed on {color_emoji} **{result}**...\n💀 You lost **{bet:,} Medals**.")


    async def _is_owner_or_manager(self, interaction: discord.Interaction) -> bool:
        if await self.bot.is_owner(interaction.user):
            return True
        if interaction.guild and interaction.guild.owner_id == interaction.user.id:
            return True
        perms = getattr(interaction.user, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_guild):
            return True
        roles = {r.name.lower() for r in getattr(interaction.user, "roles", [])}
        if "server manager" in roles or "manager" in roles or any("server manager" in r for r in roles):
            return True
        return False

    @app_commands.command(name="givemedals", description="Give Medals to a user (Owner and Server Manager Only)")
    @app_commands.default_permissions(manage_guild=True)
    async def givemedals(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if not await self._is_owner_or_manager(interaction):
            return await interaction.response.send_message("❌ This command is restricted to the Server Owner and Server Managers.", ephemeral=True)
        if amount <= 0: return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
        await self.bot.db.add_medals(member.id, interaction.guild_id, amount)
        user_data = await self.bot.db.ensure_user(member.id, interaction.guild_id)
        new_balance = user_data.get("medals", 0)
        await interaction.response.send_message(f"✅ Gave **{amount:,} Medals** to {member.mention}. (New balance: **{new_balance:,} Medals**)")

    @app_commands.command(name="removemedals", description="Remove Medals from a user (Owner and Server Manager Only)")
    @app_commands.default_permissions(manage_guild=True)
    async def removemedals(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if not await self._is_owner_or_manager(interaction):
            return await interaction.response.send_message("❌ This command is restricted to the Server Owner and Server Managers.", ephemeral=True)
        if amount <= 0: return await interaction.response.send_message("Amount must be positive.", ephemeral=True)

        user_data = await self.bot.db.ensure_user(member.id, interaction.guild_id)
        current = user_data.get("medals", 0)
        if current <= 0:
            return await interaction.response.send_message(f"❌ {member.mention} has no medals to remove.", ephemeral=True)

        deduct = min(amount, current)
        await self.bot.db.add_medals(member.id, interaction.guild_id, -deduct)
        user_data = await self.bot.db.ensure_user(member.id, interaction.guild_id)
        new_balance = user_data.get("medals", 0)
        await interaction.response.send_message(f"✅ Removed **{deduct:,} Medals** from {member.mention}. (New balance: **{new_balance:,} Medals**)")

    @app_commands.command(name="guide", description="Made by Phantom Regiment")
    async def guide(self, interaction: discord.Interaction):
        header_title = "Collation of Rose" if getattr(self.bot, "is_partner", False) else "Phantom Regiment"
        embed = discord.Embed(
            title=f"{header_title} — Economy & Medal Guide",
            description="**Made by Phantom Regiment**\n\nWelcome to the official economy guide! Here is everything you need to know about earning, storing, upgrading vaults, robbing, and protection.",
            color=0x3498DB
        )
        
        embed.add_field(
            name="Earning Medals",
            value=(
                "• **`/trivia`** *(30m)* — Answer tactical combat questions for **120 – 250** medals.\n"
                "• **`/scavenge`** *(45m)* — Scour warzones for loot (**50 – 500** medals, 10% chance for **1,000** jackpot!)\n"
                "• **`/crime`** *(2h)* — High-risk operations (Pickpocket, ATM hack, Convoy, Base Infiltration) for up to **3,500** medals!\n"
                "• **`/work`** *(4h)* — Do standard garrison duty for **50 – 200** medals.\n"
                "• **`/daily`** *(24h)* — Claim daily medals and build a streak up to 30 days (**100 – 1,000** medals).\n"
                "• **`/weekly`** *(7d)* — Flat **500** medals claim.\n"
                "• **Chatting** — Chatting earns XP and leveling up rewards bonus medals automatically!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Banking & Vault Tiers",
            value=(
                "• **Shared Medals:** Your wallet medals, bank vault, inventory, and streaks carry over between **Phantom Regiment** and **Collation of Rose**! Use `/datatransfer` to check your medals.\n"
                "• **`/bank create`** — Open a bank vault for 500 medals. **Requires setting a password!**\n"
                "• **`/bank deposit` / `/bank withdraw`** — Safely store medals away from wallet loss.\n"
                "• **`/bank upgrade` / `/updatebank`** — Upgrade your vault across **10 Tiers** to increase your daily interest cap!\n"
                "• **2.5% Daily Interest** — Vaults earn 2.5% daily interest, from **1,000 Medals/day** (Tier 1) up to **1,000,000 Medals/day** (Tier 10)!\n"
                "• **`/bank balance`** — Check your wallet, vault balance, current tier, and daily interest cap.\n"
                "• **`/bank changepassword`** — Change your vault password anytime to stay safe."
            ),
            inline=False
        )
        
        embed.add_field(
            name="Bank Robberies (/rob)",
            value=(
                "• **`/rob <user> <password>`** — Try to rob someone's bank vault using their password!\n"
                "• **Successful Rob:** Crack the password and steal their medals into your wallet!\n"
                "• **Bank Insurance:** If someone robs your vault, you immediately get **30%** back into your bank, and the rest (**70%**) is paid back over **7 days** (**10% each day**)!\n"
                "• **Wrong Password:** Gives you a 30-minute cooldown and reveals a password hint in **`XXXHINTXX`** format to help you guess next time!\n"
                "• **Alerts:** You get a DM whenever someone tries to guess your bank password."
            ),
            inline=False
        )
        
        embed.add_field(
            name="Loans",
            value=(
                "• **`/bank loan`** — Borrow up to 5,000 medals from the bank (1 to 30 days).\n"
                "• **`/loan offer <user> <amount> <interest> <days>`** — Offer loans to other players.\n"
                "• **`/loan accept <id>` / `reject <id>`** — Accept or decline loan offers (expires in 24h).\n"
                "• **Late Fee:** If you don't pay back a loan on time, a **20% late fee** is added and any medals you earn will go toward paying it off!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Casino, Battles & Leaderboards",
            value=(
                "• **`/blackjack <bet>`** — Play Blackjack against the dealer (1.5x on 21).\n"
                "• **`/roulette <bet> <type>`** — Bet on Red, Black, Even, Odd, High, Low, or Green (**36x** payout!).\n"
                "• **`/fight <user> <bet>`** — Challenge someone to a 1v1 turn-based battle.\n"
                "• **`/medalleaderboard`** — Top 10 richest players in this server.\n"
                "• **`/globallb`** — Top players across all servers using this bot!\n"
                "• **`/guilds`** — See all servers using this bot!"
            ),
            inline=False
        )
        
        if not getattr(self.bot, "is_partner", False):
            embed.add_field(
                name="Role Shop",
                value=(
                    "• **`/roleshop`** / **`/buyrole`** — Buy prestigious colored cosmetic roles (from Wealthy up to Phantom Regiment Elite) to showcase your wealth and status!"
                ),
                inline=False
            )
        
        embed.set_footer(text="Made By Phantom Regiment")
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))
