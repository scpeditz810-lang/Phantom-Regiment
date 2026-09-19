import discord
from discord.ext import commands
from discord import app_commands
import datetime

class GamenightCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gamenight", description="Schedule and announce a gamenight! (Staff Only)")
    @app_commands.describe(
        game="The game we are playing (e.g., Phantom Forces, Arsenal)",
        time_str="When is it? (e.g., 'In 30 minutes', 'At 5 PM EST')",
        description="Any extra details?"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def gamenight(
        self, 
        interaction: discord.Interaction, 
        game: str, 
        time_str: str, 
        description: str = "Join voice chat and let's play!"
    ):
        # Double check roles (Commanders, Senior Mod, Admin, Server Manager)
        allowed_roles = {"Commander", "Senior Mod", "Admin", "Server Manager"}
        user_roles = {r.name for r in interaction.user.roles}
        
        if not allowed_roles.intersection(user_roles) and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("❌ You do not have permission to host a gamenight.", ephemeral=True)
            
        embed = discord.Embed(
            title="🎮 GAMENIGHT ANNOUNCEMENT 🎮",
            description=f"A new official gamenight has been scheduled by {interaction.user.mention}!",
            color=0xE74C3C,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="🎯 Game", value=f"**{game}**", inline=False)
        embed.add_field(name="⏰ Time", value=f"**{time_str}**", inline=False)
        embed.add_field(name="📝 Details", value=description, inline=False)
        embed.set_footer(text="Join the Gamenight VC when it starts!")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Ping @everyone
        await interaction.channel.send(content="@everyone", embed=embed)
        await interaction.response.send_message("✅ Gamenight successfully announced!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(GamenightCog(bot))
