import re

with open('cogs/setup.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add Combat to options
options_old = """            discord.SelectOption(label="Medal Economy", description="How to earn and spend Medals", emoji="🏅"),
            discord.SelectOption(label="Bot Commands", description="A detailed list of all bot commands", emoji="🤖")"""
options_new = """            discord.SelectOption(label="Medal Economy", description="How to earn and spend Medals", emoji="🏅"),
            discord.SelectOption(label="Bot Commands", description="A detailed list of all bot commands", emoji="🤖"),
            discord.SelectOption(label="Arena Combat", description="How the Pokétwo style /fight system works!", emoji="⚔️")"""
text = text.replace(options_old, options_new)

# 2. Add Combat callback
combat_callback = """
        elif self.values[0] == "Arena Combat":
            embed = discord.Embed(
                title="⚔️ Arena Combat System",
                description="Challenge other members to a deathmatch in the Arena! We use a highly detailed, turn-based combat system similar to Pokétwo.",
                color=0xE74C3C
            )
            embed.add_field(name="1. The Loadout", value="Use `/shop` to browse Weapons and Utility items. You can equip 1 Weapon and up to 2 Utilities before a fight begins!", inline=False)
            embed.add_field(name="2. Base Stats", value="Every fighter starts with **100 HP**, **10 Speed**, and **70% Base Accuracy**.", inline=False)
            embed.add_field(name="3. Stat Modifiers", value="• **Weapons** alter your attack damage. (e.g., Swords grant +40% Dodge, Bows grant +30% Accuracy).\\n• **Lancer's Horse** grants +15 Speed (making you strike first!) +10% Dodge, and +10% Accuracy.\\n• **Heal Potion** gives you an extra button during the fight to heal 30 HP!", inline=False)
            embed.add_field(name="4. Turn Resolution", value="During the fight, both players secretly click `[⚔️ Attack]` or `[🧪 Heal]`. Once both choose, the player with the highest Speed executes their move first! If your Accuracy rolls higher than their Dodge, you deal damage!", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
"""
# find where Bot Commands block ends
find_str = """            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif self.values[0] == "Role Information":"""
replace_str = """            await interaction.response.send_message(embed=embed, ephemeral=True)""" + combat_callback + """            
        elif self.values[0] == "Role Information":"""
text = text.replace(find_str, replace_str)

# 3. Update Medal Economy
medal_old = """                    "Use `/shop` to browse the Armory. Currently, you can spend Medals to buy **Custom Rank Banners**. "
                    "Once purchased, use `/changebanner` to permanently equip it to your `/rank` card!" """
medal_new = """                    "Use `/shop` to browse the Armory and Banner shop! You can buy **Custom Rank Banners**, **Weapons**, and **Utility Items** for the Arena.\\n"
                    "Once purchased, use `/changebanner` to equip a banner to your `/rank` card, or use `/fight` to test out your new weapons!" """
text = text.replace(medal_old, medal_new)

# 4. Update Bot Commands
cmd_old = """            embed.add_field(
                name="🏅 Economy & Shop",
                value="`/daily` - Claim 100 free Medals every 24h.\\n`/balance` - Check your wallet.\\n`/shop` - View purchasable custom banners.\\n`/buy` - Buy an item from the shop.\\n`/changebanner` - Equip a purchased banner to your rank card.",
                inline=False
            )"""
cmd_new = """            embed.add_field(
                name="🏅 Economy & Shop",
                value="`/daily` - Claim 100 free Medals every 24h.\\n`/balance` - Check your wallet.\\n`/shop` - View purchasable banners and weapons.\\n`/buy <item_id>` - Buy an item.\\n`/changebanner` - Equip a purchased banner to your rank card.",
                inline=False
            )
            embed.add_field(
                name="⚔️ Combat",
                value="`/fight <@user>` - Challenge a user to a turn-based Arena battle! Winners steal Medals from the loser.",
                inline=False
            )"""
text = text.replace(cmd_old, cmd_new)

with open('cogs/setup.py', 'w', encoding='utf-8') as f:
    f.write(text)
