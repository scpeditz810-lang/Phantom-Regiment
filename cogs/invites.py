import discord
from discord import app_commands
from discord.ext import commands


class InviteCog(commands.Cog):
    """Tracks which invite link brought each new member and credits the inviter."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # guild_id -> {invite_code: uses}
        self._invite_cache: dict[int, dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Invite cache helpers
    # ------------------------------------------------------------------

    async def _cache_guild_invites(self, guild: discord.Guild) -> None:
        """Fetch and cache all invites for a single guild."""
        try:
            invites = await guild.invites()
            self._invite_cache[guild.id] = {
                invite.code: invite.uses for invite in invites
            }
        except discord.Forbidden:
            self._invite_cache[guild.id] = {}
        except Exception:
            self._invite_cache[guild.id] = {}

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Cache invites for every guild on startup."""
        for guild in self.bot.guilds:
            await self._cache_guild_invites(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite) -> None:
        """Add a newly created invite to the cache."""
        if invite.guild is None:
            return
        cache = self._invite_cache.setdefault(invite.guild.id, {})
        cache[invite.code] = invite.uses

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite) -> None:
        """Remove a deleted invite from the cache."""
        if invite.guild is None:
            return
        cache = self._invite_cache.get(invite.guild.id)
        if cache is not None:
            cache.pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Determine which invite was used and credit the inviter."""
        guild = member.guild
        old_cache = self._invite_cache.get(guild.id, {})

        try:
            new_invites = await guild.invites()
        except discord.Forbidden:
            return
        except Exception:
            return

        inviter: discord.User | discord.Member | None = None

        for invite in new_invites:
            old_uses = old_cache.get(invite.code, 0)
            if invite.uses is not None and invite.uses > old_uses:
                inviter = invite.inviter
                break

        # Update the cache regardless of whether we found the inviter
        self._invite_cache[guild.id] = {
            invite.code: invite.uses for invite in new_invites
        }

        if inviter is not None:
            try:
                await self.bot.db.add_invite(inviter.id, member.id, guild.id)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Deduct invite count and remove history if an invited user leaves."""
        try:
            await self.bot.db.remove_invite(member.id, member.guild.id)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------

    @app_commands.command(name="invite", description="Check how many people a member has invited")
    @app_commands.describe(member="The member to check invites for")
    async def invite_count(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        """Display the invite count for a given member."""
        try:
            count = await self.bot.db.get_invites(member.id, interaction.guild_id)
        except Exception:
            await interaction.response.send_message(
                "⚠️ Failed to fetch invite data.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Invite Tracker",
            description=f"{member.mention} has invited **{count}** member{'s' if count != 1 else ''}.",
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="checkinvite", description="See a list of people a member has invited")
    @app_commands.describe(member="The member to check")
    async def check_invite(self, interaction: discord.Interaction, member: discord.Member) -> None:
        """Display a list of members that this person invited."""
        try:
            invited_ids = await self.bot.db.get_invited_users(member.id, interaction.guild_id)
        except Exception:
            return await interaction.response.send_message("⚠️ Failed to fetch data.", ephemeral=True)

        if not invited_ids:
            return await interaction.response.send_message(f"{member.mention} has not invited anyone yet.", ephemeral=True)

        # Build list of mentions
        mentions = [f"<@{uid}>" for uid in invited_ids]
        
        # Discord embeds max description length is 4096. 
        description = "\n".join(mentions)
        if len(description) > 4000:
            description = description[:4000] + "\n...and more!"

        embed = discord.Embed(
            title=f"People invited by {member.display_name}",
            description=description,
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Total: {len(invited_ids)} invites")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inviteleaderboard", description="Show the top 10 inviters in this server")
    async def invite_leaderboard(self, interaction: discord.Interaction) -> None:
        """Display a leaderboard of the top inviters."""
        try:
            leaderboard = await self.bot.db.get_invite_leaderboard(
                interaction.guild_id, limit=10
            )
        except Exception:
            await interaction.response.send_message(
                "⚠️ Failed to fetch leaderboard data.", ephemeral=True
            )
            return

        if not leaderboard:
            await interaction.response.send_message(
                "No invite data recorded yet.", ephemeral=True
            )
            return

        lines: list[str] = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}

        for rank, entry in enumerate(leaderboard, start=1):
            prefix = medals.get(rank, f"**{rank}.**")
            user_id = entry["user_id"]
            count = entry["invite_count"]
            lines.append(f"{prefix} <@{user_id}> — **{count}** invite{'s' if count != 1 else ''}")

        embed = discord.Embed(
            title="🏆 Invite Leaderboard",
            description="\n".join(lines),
            color=discord.Color.gold(),
        )
        embed.set_footer(
            text=f"Top {len(leaderboard)} inviters • {interaction.guild.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addinvites", description="Manually add invites to a user's count")
    @app_commands.describe(member="The member to add invites to", amount="Number of invites to add")
    @app_commands.guild_only()
    async def add_invites(self, interaction: discord.Interaction, member: discord.Member, amount: int) -> None:
        """Add invites to a user — moderators and above only."""
        # Permission check: Moderator role, Commander, Recruitment Team, or special role
        staff_names = {"Trial Mod", "Moderator", "Senior Mod", "Admin", "Server Manager", "Commander", "Recruitment Team"}
        user_roles = {r.name for r in interaction.user.roles}
        has_role_id = any(r.id == 1551265887934218311 for r in interaction.user.roles)
        if not (user_roles & staff_names) and not has_role_id and not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)

        if amount == 0:
            return await interaction.response.send_message("❌ Amount must not be zero.", ephemeral=True)

        # Directly update the invite count in DB
        await self.bot.db._db.execute(
            "INSERT INTO invites (user_id, guild_id, invite_count) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET invite_count = MAX(0, invite_count + ?)",
            (member.id, interaction.guild_id, max(0, amount), amount),
        )
        await self.bot.db._db.commit()

        new_count = await self.bot.db.get_invites(member.id, interaction.guild_id)

        if amount > 0:
            await interaction.response.send_message(f"✅ Added **{amount}** invite(s) to {member.mention}. They now have **{new_count}** total.")
        else:
            await interaction.response.send_message(f"✅ Removed **{abs(amount)}** invite(s) from {member.mention}. They now have **{new_count}** total.")

    @app_commands.command(name="submitscreenshot", description="Submit proof of inviting a member to the server")
    @app_commands.describe(
        inviting_proof="Screenshot showing you invited the member",
        member_inside="Screenshot showing the member is inside the server",
        extra_proof_1="Additional screenshot (optional)",
        extra_proof_2="Additional screenshot (optional)"
    )
    @app_commands.guild_only()
    async def submit_screenshot(
        self, 
        interaction: discord.Interaction, 
        inviting_proof: discord.Attachment, 
        member_inside: discord.Attachment,
        extra_proof_1: discord.Attachment = None,
        extra_proof_2: discord.Attachment = None
    ) -> None:
        """Submit invite proofs to the review channel."""
        await interaction.response.defer(ephemeral=True)
        
        review_channel = interaction.guild.get_channel(1550657834142793909)
        if not review_channel:
            return await interaction.followup.send("❌ Review channel not found. Please contact staff.")
            
        attachments = [inviting_proof, member_inside]
        if extra_proof_1: attachments.append(extra_proof_1)
        if extra_proof_2: attachments.append(extra_proof_2)
        
        # Download files to re-upload them so links don't expire
        files = []
        import io
        for i, att in enumerate(attachments):
            try:
                data = await att.read()
                files.append(discord.File(io.BytesIO(data), filename=f"proof_{i}_{att.filename}"))
            except Exception:
                pass
                
        embed = discord.Embed(
            title="📥 Invite Proof Submission",
            description=f"**Submitted by:** {interaction.user.mention} (`{interaction.user}`)\n\n"
                        f"Staff can review these screenshots and use `/addinvites {interaction.user.mention} 1` to manually add an invite to their count if valid.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        
        await review_channel.send(embed=embed, files=files)
        await interaction.followup.send("✅ Your proof has been submitted to the Recruitment Team for review!")



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InviteCog(bot))
