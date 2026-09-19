with open('cogs/economy.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_items = """
    "berserker_axe": {"name": "🪓 Berserker's Axe", "price": 1800, "type": "weapon", "min_dmg": 20, "max_dmg": 35, "dodge": 0, "acc": 0, "speed": 0, "desc": "20-35 DMG"},
    "spartans_shield": {"name": "🛡️ Spartan's Shield", "price": 2200, "type": "utility", "desc": "Passive: +30% Dodge (Block Chance)"},
    "immortals_mask": {"name": "🎭 Immortal's Mask", "price": 2800, "type": "utility", "desc": "Passive: +35% Accuracy"},
"""

text = text.replace(
    '    "lancers_horse": {"name": "🐎 Lancer\'s Horse", "price": 3000, "type": "utility", "desc": "Passive: +15 Speed, +10% Dodge, +10% Accuracy"},',
    '    "lancers_horse": {"name": "🐎 Lancer\'s Horse", "price": 3000, "type": "utility", "desc": "Passive: +15 Speed, +10% Dodge, +10% Accuracy"},' + new_items
)

logic = """
            elif item_id == "spartans_shield":
                self.dodge += 30
            elif item_id == "immortals_mask":
                self.accuracy += 35"""

text = text.replace(
    '                self.accuracy += 10',
    '                self.accuracy += 10' + logic
)

with open('cogs/economy.py', 'w', encoding='utf-8') as f:
    f.write(text)
