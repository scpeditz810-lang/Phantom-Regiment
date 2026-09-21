import discord
from discord.ext import commands

FORUM_CHANNEL_ID = 1551718423036428320
STARBOARD_CHANNEL_ID = 1551719286890827796
STAR_THRESHOLD = 10
STAR_EMOJI = "⭐"

class SuggestionsCog(commands.Cog):
    """Handles the starboard suggestion system for the forum channel."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        # Ignore bots reacting
        if payload.member and payload.member.bot:
            return

        # Only care about the star emoji
        if str(payload.emoji) != STAR_EMOJI:
            return

        # Fetch the channel
        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except discord.HTTPException:
                return

        # We only care if the reaction is inside a Thread that belongs to our Forum channel
        if not isinstance(channel, discord.Thread) or channel.parent_id != FORUM_CHANNEL_ID:
            return

        # We only care about reactions to the ORIGINAL post (first message in the thread)
        # The first message ID in a thread is always the same as the thread ID.
        if payload.message_id != channel.id:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return

        # 1. Prevent self-voting
        if payload.user_id == message.author.id:
            try:
                await message.remove_reaction(payload.emoji, payload.member or discord.Object(payload.user_id))
            except discord.HTTPException:
                pass
            return

        # 2. Count valid stars (excluding the author if they somehow sneaked one in)
        reaction = discord.utils.get(message.reactions, emoji=STAR_EMOJI)
        if not reaction:
            return

        # Start with the raw count
        count = reaction.count

        # If the author reacted, subtract 1 from the count for logic purposes
        # (Though we actively remove it, sometimes discord caching makes it show up)
        users = [u async for u in reaction.users()]
        if any(u.id == message.author.id for u in users):
            count -= 1

        # 3. Update or post to the starboard if it hits the threshold
        if count >= STAR_THRESHOLD:
            await self._update_starboard(message, channel, count)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle people un-starring a suggestion to lower the count."""
        if str(payload.emoji) != STAR_EMOJI:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        if not isinstance(channel, discord.Thread) or channel.parent_id != FORUM_CHANNEL_ID:
            return

        if payload.message_id != channel.id:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return

        reaction = discord.utils.get(message.reactions, emoji=STAR_EMOJI)
        count = reaction.count if reaction else 0

        # If the author is in there, subtract 1
        if reaction:
            users = [u async for u in reaction.users()]
            if any(u.id == message.author.id for u in users):
                count -= 1

        # If it's already on the starboard, we need to update it (even if it drops below threshold)
        starboard_msg_id = await self.bot.db.get_starboard_msg(message.id)
        if starboard_msg_id:
            await self._update_starboard(message, channel, count, starboard_msg_id)

    async def _update_starboard(self, message: discord.Message, thread: discord.Thread, count: int, starboard_msg_id: int | None = None) -> None:
        """Post a new starboard message or update an existing one."""
        starboard_channel = self.bot.get_channel(STARBOARD_CHANNEL_ID)
        if not starboard_channel:
            return

        content_str = f"{STAR_EMOJI} **{count}** | [**{thread.name}**]({message.jump_url})"

        embed = discord.Embed(
            description=message.content,
            color=0xFFAC33,  # Star gold color
            timestamp=message.created_at
        )
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)

        # Handle attachments (images)
        if message.attachments:
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    embed.set_image(url=attachment.url)
                    break # Only one main image

        if not starboard_msg_id:
            starboard_msg_id = await self.bot.db.get_starboard_msg(message.id)

        if starboard_msg_id:
            # Edit existing
            try:
                starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                await starboard_msg.edit(content=content_str, embed=embed)
            except discord.NotFound:
                # Message was deleted from starboard, post a new one
                new_msg = await starboard_channel.send(content=content_str, embed=embed)
                await self.bot.db.link_starboard_msg(message.id, new_msg.id)
            except discord.HTTPException:
                pass
        else:
            # Post new
            new_msg = await starboard_channel.send(content=content_str, embed=embed)
            await self.bot.db.link_starboard_msg(message.id, new_msg.id)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SuggestionsCog(bot))
