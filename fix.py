with open('cogs/economy.py', 'r', encoding='utf-8') as f:
    text = f.read()

banner_classes = """
class BannerSelect(discord.ui.Select):
    def __init__(self, owned_items: list[str]):
        options = [discord.SelectOption(label="Default Gradient", value="default", description="Equip the standard background")]
        for item_id in owned_items:
            if item_id in SHOP_ITEMS:
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
"""

# Put classes before EconomyCog
text = text.replace('class EconomyCog(commands.Cog):', banner_classes + '\nclass EconomyCog(commands.Cog):')

# Replace equip with changebanner
equip_def = """    @app_commands.command(name="equip", description="Equip a purchased banner to your rank card")
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
        await interaction.response.send_message(f"✅ Successfully equipped **{SHOP_ITEMS[item_id]['name']}**! Run `/rank` to see it.")"""

changebanner_def = """    @app_commands.command(name="changebanner", description="Equip a custom banner that you have purchased!")
    async def changebanner(self, interaction: discord.Interaction):
        owned_items = await self.bot.db.get_inventory(interaction.user.id, interaction.guild_id)
        if not owned_items:
            return await interaction.response.send_message("❌ You don't own any custom banners yet! Buy some using `/shop`.", ephemeral=True)
            
        view = BannerView(owned_items)
        await interaction.response.send_message("Select a banner from your inventory below to equip it:", view=view, ephemeral=True)"""

text = text.replace(equip_def, changebanner_def)

with open('cogs/economy.py', 'w', encoding='utf-8') as f:
    f.write(text)
