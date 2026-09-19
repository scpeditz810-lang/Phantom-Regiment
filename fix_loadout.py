import re

with open('cogs/economy.py', 'r', encoding='utf-8') as f:
    text = f.read()

new_on_submit = """
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
"""

find_on_submit = r'    async def on_submit\(self, interaction: discord\.Interaction\):.*?await self\.callback_fn\(self\.member, loadout\)'
text = re.sub(find_on_submit, new_on_submit.strip(), text, flags=re.DOTALL)

with open('cogs/economy.py', 'w', encoding='utf-8') as f:
    f.write(text)
