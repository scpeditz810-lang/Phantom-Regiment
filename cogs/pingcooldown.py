"""
Ping Cooldown Cog — prevents spam-pinging a specific role.

Rules:
  • Role 1553465190648119378 may only be pinged in channel 1550657825045221457.
  • If pinged elsewhere → delete message, tell user to use the correct channel, auto-delete warning after 5s.
  • If pinged more than once in 5 minutes in the correct channel → delete message, tell user when they can ping again.
"""

import asyncio
import time
import discord
from discord.ext import commands

PING_ROLE_ID = 1553465190648119378
ALLOWED_CHANNEL_ID = 1550657825045221457
COOLDOWN_SECONDS = 300  # 5 minutes


class PingCooldownCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # user_id -> last ping timestamp
        self._last_ping: dict[int, float] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Check if the message mentions the specific role
        if not any(r.id == PING_ROLE_ID for r in message.role_mentions):
            return

        # ── Wrong channel ──────────────────────────────────────────────
        if message.channel.id != ALLOWED_CHANNEL_ID:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            warning = await message.channel.send(
                f"{message.author.mention} ❌ You can only ping that role in <#{ALLOWED_CHANNEL_ID}>. "
                f"Please use it there instead."
            )

            await asyncio.sleep(5)
            try:
                await warning.delete()
            except discord.HTTPException:
                pass
            return

        # ── Correct channel — check cooldown ───────────────────────────
        now = time.time()
        last = self._last_ping.get(message.author.id, 0)
        remaining = COOLDOWN_SECONDS - (now - last)

        if remaining > 0:
            try:
                await message.delete()
            except discord.Forbidden:
                pass

            ready_at = int(now + remaining)
            await message.channel.send(
                f"{message.author.mention} ⏳ You already pinged that role recently. "
                f"You can ping again <t:{ready_at}:R> (at <t:{ready_at}:T>).",
                delete_after=10,
            )
            return

        # ── Valid ping — record timestamp ──────────────────────────────
        self._last_ping[message.author.id] = now


async def setup(bot: commands.Bot):
    await bot.add_cog(PingCooldownCog(bot))
