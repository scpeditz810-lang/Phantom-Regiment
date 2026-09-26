import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


async def fetch_roblox_user(username: str) -> dict | None:
    """Look up a Roblox user by username via the Roblox API.

    Returns a dict with ``id``, ``name``, and ``displayName`` keys,
    or ``None`` if the user was not found.
    """
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                users = data.get("data", [])
                if not users:
                    return None
                entry = users[0]
                return {
                    "id": entry["id"],
                    "name": entry["name"],
                    "displayName": entry["displayName"],
                }
    except (aiohttp.ClientError, KeyError):
        return None


async def set_roblox_nickname(member: discord.Member, display_name: str, username: str) -> None:
    """Set the member's server nickname to ``DisplayName (@Username)``."""
    nick = f"{display_name} (@{username})"
    try:
        await member.edit(nick=nick)
    except discord.Forbidden:
        # Can't change the server owner's nickname or a member with a
        # higher role than the bot.
        pass


class RobloxCog(commands.Cog):
    """Roblox account linking and lookup commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _fetch_avatar_url(self, roblox_id: int) -> str | None:
        """Fetch the Roblox avatar headshot thumbnail URL for a user."""
        url = (
            "https://thumbnails.roblox.com/v1/users/avatar-headshot"
            f"?userIds={roblox_id}&size=150x150&format=Png"
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    entries = data.get("data", [])
                    if not entries:
                        return None
                    return entries[0].get("imageUrl")
        except (aiohttp.ClientError, KeyError):
            return None

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    @app_commands.command(name="verify", description="Link your Roblox account")
    @app_commands.describe(roblox_username="Your Roblox username")
    async def verify(self, interaction: discord.Interaction, roblox_username: str) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            roblox_user = await fetch_roblox_user(roblox_username)
            if roblox_user is None:
                embed = discord.Embed(
                    title="Verification Failed",
                    description=f"Could not find a Roblox user named **{roblox_username}**.",
                    color=discord.Color.red(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            roblox_id: int = roblox_user["id"]
            username: str = roblox_user["name"]
            display_name: str = roblox_user["displayName"]

            # Persist the link in the database.
            await self.bot.db.link_roblox(
                interaction.user.id, username, roblox_id, display_name
            )

            # Attempt to set the member's nickname.
            if interaction.guild and isinstance(interaction.user, discord.Member):
                await set_roblox_nickname(interaction.user, display_name, username)

            # Fetch avatar thumbnail.
            avatar_url = await self._fetch_avatar_url(roblox_id)

            embed = discord.Embed(
                title="Verification Successful",
                description=(
                    f"Linked to **{display_name}** (@{username})\n"
                    f"Roblox ID: `{roblox_id}`"
                ),
                color=discord.Color.green(),
            )
            embed.url = f"https://www.roblox.com/users/{roblox_id}/profile"
            if avatar_url:
                embed.set_thumbnail(url=avatar_url)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Something went wrong: `{e}`",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="whois", description="Look up a member's linked Roblox account")
    @app_commands.describe(member="The server member to look up")
    async def whois(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)

        try:
            link = await self.bot.db.get_roblox_link(member.id)
            if link is None:
                embed = discord.Embed(
                    title="Not Linked",
                    description=f"{member.mention} has not linked a Roblox account.",
                    color=discord.Color.greyple(),
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            roblox_id = link.get("roblox_id")
            username = link.get("roblox_username")
            display_name = link.get("roblox_display")

            avatar_url = await self._fetch_avatar_url(roblox_id) if roblox_id else None

            # Check if they are in a squad
            squad_names = ["Frontline", "Los Bluchigis", "Ignite's squad"]
            member_squads = [r.name for r in member.roles if r.name in squad_names]
            squad_text = f"🛡️ **Squad:** {member_squads[0]}" if member_squads else "🛡️ **Squad:** None"

            embed = discord.Embed(
                title=f"{display_name} (@{username})",
                description=f"Roblox ID: `{roblox_id}`\n\n{squad_text}",
                color=discord.Color.blurple(),
            )
            embed.url = f"https://www.roblox.com/users/{roblox_id}/profile"
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            if avatar_url:
                embed.set_thumbnail(url=avatar_url)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Something went wrong: `{e}`",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RobloxCog(bot))
