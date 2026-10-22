import os
import time
import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands

MAIN_GUILD_ID = int(os.environ.get("GUILD_ID", 1550544659217125467))

CANDIDATE_COST = 400_000
MAX_CANDIDATES = 5
ELECTION_DURATION_HOURS = 48.0
MAX_AWARDS_PER_TERM = 3
MAX_DOUBLE_XP_PER_TERM = 3
MAX_PARDONS_PER_TERM = 3
MAX_STIMULUS_PER_TERM = 2
AWARD_AMOUNT = 15_000
MAYOR_DAILY_SALARY = 12_500


class StimulusClaimView(discord.ui.View):
    def __init__(self, bot, mayor_id: int, max_claims: int = 4, grant_amount: int = 2500):
        super().__init__(timeout=300)
        self.bot = bot
        self.mayor_id = mayor_id
        self.max_claims = max_claims
        self.grant_amount = grant_amount
        self.claimed_users = set()

    @discord.ui.button(label="🏛️ Claim Mayoral Stimulus (2,500 M)", style=discord.ButtonStyle.success)
    async def claim_stimulus(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user

        # Anti-self-claim rule: Mayor cannot claim their own stimulus
        if user.id == self.mayor_id:
            return await interaction.response.send_message(
                "⛔ **Anti-Corruption Law:** As Mayor, you released this stimulus for your citizens. You cannot claim it yourself!",
                ephemeral=True
            )

        if user.id in self.claimed_users:
            return await interaction.response.send_message("⚠️ You have already claimed from this stimulus package!", ephemeral=True)

        if len(self.claimed_users) >= self.max_claims:
            button.disabled = True
            await interaction.response.edit_message(view=self)
            return await interaction.followup.send("❌ All stimulus packages have already been claimed!", ephemeral=True)

        self.claimed_users.add(user.id)
        await self.bot.db.add_medals(user.id, interaction.guild_id, self.grant_amount)

        remaining = self.max_claims - len(self.claimed_users)
        if remaining <= 0:
            button.disabled = True
            button.label = "🏛️ All Stimulus Claimed"
            button.style = discord.ButtonStyle.secondary
            await interaction.response.edit_message(view=self)
        else:
            button.label = f"🏛️ Claim Stimulus ({remaining} Left)"
            await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            f"🎉 **Stimulus Received!** `+{self.grant_amount:,} Medals` from the City Budget deposited into your wallet!",
            ephemeral=True
        )


class ElectionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.election_loop.start()

    def cog_unload(self):
        self.election_loop.cancel()

    async def get_or_create_roles(self, guild: discord.Guild) -> tuple[discord.Role, discord.Role]:
        """Fetch or automatically create the required Mayor and Candidate roles."""
        mayor_role = discord.utils.get(guild.roles, name="🏛️ Mayor")
        if not mayor_role:
            try:
                mayor_role = await guild.create_role(
                    name="🏛️ Mayor",
                    color=discord.Color.from_rgb(241, 196, 15),
                    hoist=True,
                    reason="Phantom Regiment City Mayor Role"
                )
            except discord.Forbidden:
                mayor_role = None

        candidate_role = discord.utils.get(guild.roles, name="🗳️ Mayoral Candidate")
        if not candidate_role:
            try:
                candidate_role = await guild.create_role(
                    name="🗳️ Mayoral Candidate",
                    color=discord.Color.from_rgb(52, 152, 219),
                    hoist=False,
                    reason="Phantom Regiment Mayoral Candidate Role"
                )
            except discord.Forbidden:
                candidate_role = None

        return mayor_role, candidate_role

    async def _resolve_election(self, interaction: discord.Interaction) -> dict | None:
        """Fetch active election for the current guild or fall back to main Regiment guild."""
        gid = interaction.guild_id or MAIN_GUILD_ID
        ele = await self.bot.db.get_active_election(gid)
        if not ele and gid != MAIN_GUILD_ID:
            ele = await self.bot.db.get_active_election(MAIN_GUILD_ID)
        return ele

    async def is_mayor(self, member: discord.Member) -> bool:
        """Verify if a member is the active, officially crowned Mayor."""
        if hasattr(member, "roles") and any(r.name == "🏛️ Mayor" for r in member.roles):
            return True
        gid = member.guild.id if hasattr(member, "guild") and member.guild else MAIN_GUILD_ID
        curr = await self.bot.db.get_current_commander(gid)
        if curr and curr.get("winner_id") == member.id:
            return True
        if gid != MAIN_GUILD_ID:
            curr_main = await self.bot.db.get_current_commander(MAIN_GUILD_ID)
            if curr_main and curr_main.get("winner_id") == member.id:
                return True
        return False

    @tasks.loop(seconds=60)
    async def election_loop(self):
        """Automated background loop that concludes elections when the 48-hour timer expires."""
        try:
            active_elections = await self.bot.db.get_active_elections_all_guilds()
            now = time.time()
            for ele in active_elections:
                if now >= ele["end_time"]:
                    success, finished_ele, msg = await self.bot.db.conclude_election(ele["id"])
                    if not success or not finished_ele:
                        continue

                    guild = self.bot.get_guild(ele["guild_id"])
                    if not guild:
                        continue

                    mayor_role, candidate_role = await self.get_or_create_roles(guild)
                    winner_id = finished_ele.get("winner_id")

                    # Remove old mayor role from previous holders
                    if mayor_role:
                        for m in mayor_role.members:
                            if m.id != winner_id:
                                try:
                                    await m.remove_roles(mayor_role, reason="Mayoral term ended.")
                                except Exception:
                                    pass

                    # Clean up candidate roles from all candidates
                    if candidate_role:
                        for m in candidate_role.members:
                            try:
                                await m.remove_roles(candidate_role, reason="Election cycle concluded.")
                            except Exception:
                                pass

                    winner_member = guild.get_member(winner_id) if winner_id else None
                    if winner_member and mayor_role:
                        try:
                            await winner_member.add_roles(mayor_role, reason="Won Mayoral Election!")
                        except Exception:
                            pass

                    # Announce election results in server
                    channel = guild.system_channel or next(
                        (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages), None
                    )
                    if channel:
                        if winner_member:
                            cands = await self.bot.db.get_election_candidates(ele["id"])
                            top_cand = next((c for c in cands if c["candidate_id"] == winner_id), None)
                            votes = top_cand["votes"] if top_cand else 0
                            embed = discord.Embed(
                                title="🎉 THE VOTES ARE IN — OUR NEW MAYOR IS ELECTED!",
                                description=(
                                    f"The 48-hour election polls have closed!\n\n"
                                    f"🎩 **Congratulations to our new Mayor:** {winner_member.mention}!\n\n"
                                    f"• **Winning Ballots:** `{votes}` votes\n"
                                    f"• **Term Length:** 14 Days\n"
                                    f"• **Executive Mayoral Powers:**\n"
                                    f"  - ⚡ **2X Double XP Days:** Can activate server-wide 2X XP for 24h (3 times per term)!\n"
                                    f"  - 💰 **Executive Daily Salary:** Earns 12,500 M/day from the City Treasury!\n"
                                    f"  - 🎖️ **Key to the City:** Can grant +15,000 M honors to citizens!\n"
                                    f"  - 🏛️ **Mayoral Stimulus:** Release public medal grants in chat!\n"
                                    f"  - 📈 **Tax Policy:** Tune stock market transaction taxes (10% to 20%)!\n"
                                    f"  - ⚖️ **Mayoral Pardon:** Clear robbery cooldowns for citizens!\n\n"
                                    f"*\"Congratulations to our new civic leader!\"*"
                                ),
                                color=0xF1C40F
                            )
                            embed.set_thumbnail(url=winner_member.display_avatar.url)
                            embed.set_footer(text="Phantom Regiment City Hall")
                            await channel.send(content=f"🎉 Congratulations {winner_member.mention}!", embed=embed)
                        else:
                            embed = discord.Embed(
                                title="🏛️ ELECTION CONCLUDED — NO CANDIDATES",
                                description="The 48-hour election cycle ended with zero registered candidates. The Mayoral seat remains vacant until the next election.",
                                color=0x95A5A6
                            )
                            await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Error in election loop: {e}", flush=True)

    @election_loop.before_loop
    async def before_election_loop(self):
        await self.bot.wait_until_ready()

    # ── Election Command Group ────────────────────────────────────────────────
    election = app_commands.Group(name="election", description="City Mayoral democratic elections")

    @election.command(name="status", description="View current Mayoral election status, countdown, registered candidates, and ballots")
    async def election_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild or self.bot.get_guild(MAIN_GUILD_ID)
        gid = guild.id if guild else MAIN_GUILD_ID
        ele = await self._resolve_election(interaction)
        now = time.time()

        if not ele or now > ele["end_time"]:
            latest = await self.bot.db.get_latest_election(gid)
            if not latest and gid != MAIN_GUILD_ID:
                latest = await self.bot.db.get_latest_election(MAIN_GUILD_ID)
            winner_id = latest.get("winner_id") if latest else None
            winner_member = guild.get_member(winner_id) if winner_id else None
            term_end = latest.get("term_end", 0) if latest else 0

            embed = discord.Embed(
                title="🏛️ City Hall — Mayoral Status",
                description=(
                    "There is currently **no active voting in progress**.\n\n"
                    + (
                        f"🎩 **Current Mayor:** {winner_member.mention if winner_member else f'<@{winner_id}>'}\n"
                        f"⏳ **Term Expiration:** <t:{int(term_end)}:R> (<t:{int(term_end)}:F>)\n\n"
                        if winner_id and now < term_end
                        else "🎩 **Current Mayor:** *Vacant — Ready for a new election!*\n\n"
                    )
                    + f"To run for Mayor and trigger a 48-hour election cycle, run `/election register <slogan>` (Filing Fee: **{CANDIDATE_COST:,} Medals**)."
                ),
                color=0xF1C40F if (winner_id and now < term_end) else 0x3498DB
            )
            if winner_member:
                embed.set_thumbnail(url=winner_member.display_avatar.url)
            embed.set_footer(text="Max 5 candidates per cycle • 48-Hour voting window • Anti-self-vote enforced")
            return await interaction.followup.send(embed=embed)

        # Active election in progress
        cands = await self.bot.db.get_election_candidates(ele["id"])
        total_votes = sum(c.get("votes", 0) for c in cands)
        end_time_ts = int(ele["end_time"])

        embed = discord.Embed(
            title="🗳️ MAYORAL ELECTION — VOTING IN PROGRESS",
            description=(
                f"Mayoral election is live! The winner leads the server with real executive powers for 2 weeks.\n\n"
                f"⏳ **Voting Closes:** <t:{end_time_ts}:R> (<t:{end_time_ts}:F>)\n"
                f"📊 **Total Ballots Cast:** `{total_votes:,}`\n"
                f"👥 **Candidate Slots:** `{len(cands)} / {MAX_CANDIDATES}` filled\n"
                f"💰 **Filing Fee to Run:** `{CANDIDATE_COST:,} Medals`\n\n"
                f"Vote using: `/election vote @candidate`\n"
                f"Register using: `/election register <slogan>`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x2ECC71
        )

        if not cands:
            embed.add_field(
                name="📋 Registered Candidates",
                value="*No candidates have registered yet! Be the first to run with `/election register <slogan>`!*",
                inline=False
            )
        else:
            for idx, c in enumerate(cands, 1):
                member = guild.get_member(c["candidate_id"])
                name = member.display_name if member else f"Candidate {c['candidate_id']}"
                votes = c.get("votes", 0)
                pct = round((votes / total_votes) * 100, 1) if total_votes > 0 else 0.0
                bar_len = int(round(pct / 10))
                bar = "█" * bar_len + "░" * (10 - bar_len)

                embed.add_field(
                    name=f"#{idx} {name} — `{votes}` votes ({pct}%)",
                    value=f"`[{bar}]`\n💬 *\"{c.get('slogan') or 'Vote for me, I got big plans for the server!'}\"*",
                    inline=False
                )

        has_voted = await self.bot.db.has_user_voted(ele["id"], interaction.user.id)
        status_text = "✅ You have already cast your ballot in this election." if has_voted else "⚠️ You have not voted yet! Use `/election vote @candidate` to vote."
        embed.set_footer(text=f"{status_text} • Anti-self-vote enforced")
        await interaction.followup.send(embed=embed)

    @election.command(name="register", description="Register as an official candidate for Mayor (Cost: 400,000 Medals, Max 5)")
    @app_commands.describe(slogan="Your official campaign motto or policy promise (max 120 chars)")
    async def election_register(self, interaction: discord.Interaction, slogan: str):
        await interaction.response.defer()
        guild = interaction.guild
        user = interaction.user

        ele = await self._resolve_election(interaction)
        now = time.time()
        if not ele or now > ele["end_time"]:
            gid = guild.id if guild else MAIN_GUILD_ID
            ele = await self.bot.db.create_election(gid, duration_hours=ELECTION_DURATION_HOURS)

        end_time_ts = int(ele["end_time"])

        cands = await self.bot.db.get_election_candidates(ele["id"])
        if len(cands) >= MAX_CANDIDATES:
            return await interaction.followup.send(
                f"❌ **Registration Closed:** Candidate slots are full! Only **{MAX_CANDIDATES} candidates** can run per election cycle.",
                ephemeral=True
            )

        if any(c["candidate_id"] == user.id for c in cands):
            return await interaction.followup.send(
                "⚠️ You are already officially registered as a candidate in this election!",
                ephemeral=True
            )

        econ = await self.bot.db.get_global_economy(user.id)
        wallet = econ.get("medals", 0)
        if wallet < CANDIDATE_COST:
            return await interaction.followup.send(
                f"❌ **Insufficient Wallet Medals:** Registering for Mayor requires **{CANDIDATE_COST:,} Medals** in your wallet. (You currently hold: `{wallet:,} Medals`). Withdraw from `/bank` if needed!",
                ephemeral=True
            )

        # Deduct registration fee
        await self.bot.db.add_medals(user.id, guild.id, -CANDIDATE_COST)

        # Register candidate
        success, msg = await self.bot.db.register_candidate(ele["id"], user.id, slogan)
        if not success:
            await self.bot.db.add_medals(user.id, guild.id, CANDIDATE_COST)
            return await interaction.followup.send(f"❌ Registration failed: {msg}", ephemeral=True)

        # Assign Mayoral Candidate role
        _, candidate_role = await self.get_or_create_roles(guild)
        if candidate_role:
            try:
                await user.add_roles(candidate_role, reason="Registered as Mayoral Candidate")
            except Exception:
                pass

        # DM candidate with their benefits & campaign tips
        try:
            dm_lines = [
                f"Yo {user.display_name}, you just locked in your spot as an official candidate for Mayor of **{guild.name}**!",
                "",
                f"Your **{CANDIDATE_COST:,} Medals** filing fee is confirmed. Voting is live for **48 hours**.",
                "",
                "### 🏆 What You Get If You Win (14-Day Term):",
                "• ⚡ **`/mayor doublexp`** — Drop server-wide **2X Double XP for 24 hours** (use up to 3 times). Whole server will love you for this.",
                f"• 💰 **`/mayor salary`** — Collect **{MAYOR_DAILY_SALARY:,} Medals every 24 hours** from City Hall (makes back up to **175,000 Medals** across your term!).",
                f"• 🔑 **`/mayor award @member`** — Hand out **+{AWARD_AMOUNT:,} Medals** + Key to the City to your best supporters (3 times; cannot self-award).",
                "• 📦 **`/mayor stimulus`** — Drop a **10,000 Medal** crate in chat for 4 people to claim 2.5k each (2 times).",
                "• ⚖️ **`/mayor pardon @member`** — Clear someone's robbery cooldown or jail time clean (3 times).",
                "• 📈 **`/mayor tax <10-20>`** — Set the stock market transaction tax rate (10% to 20%).",
                "• 🏛️ **Golden Hoisted Role** — Unique `🏛️ Mayor` role placed at the very top of the Discord member list.",
                "",
                "### 🗳️ How to Win:",
                f"1. Get people to vote for you: `/election vote {user.mention}`",
                f'2. Your slogan: *"{slogan}"*',
                "3. **Remember:** You can't vote for yourself, so get your friends & squad to back you!",
                "",
                "Good luck on the campaign trail!"
            ]
            dm_embed = discord.Embed(
                title="🎩 You're Officially Running for Mayor!",
                description="\n".join(dm_lines),
                color=0xF1C40F
            )
            dm_embed.set_footer(text="Mayoral Elections • Phantom Regiment")
            await user.send(embed=dm_embed)
        except Exception:
            pass

        embed = discord.Embed(
            title="📢 NEW MAYORAL CANDIDATE DECLARED!",
            description=(
                f"{user.mention} has paid the **{CANDIDATE_COST:,} Medals** filing fee and is officially running for **Mayor**!\n\n"
                f"💬 **Campaign Slogan:**\n*\"{slogan}\"*\n\n"
                f"👥 **Candidate Slots:** `{len(cands) + 1} / {MAX_CANDIDATES}` Filled\n"
                f"⏳ **Voting Closes:** <t:{end_time_ts}:R>\n\n"
                f"Vote for your Mayor now using `/election vote {user.mention}`!"
            ),
            color=0x3498DB
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Phantom Regiment Elections • 1 Vote Per Member")
        await interaction.followup.send(embed=embed)

    @election.command(name="vote", description="Cast your ballot for a registered Mayoral candidate")
    @app_commands.describe(candidate="The registered candidate you wish to vote for")
    async def election_vote(self, interaction: discord.Interaction, candidate: discord.User):
        await interaction.response.defer(ephemeral=True)
        user = interaction.user

        # Anti-self-vote rule
        if candidate.id == user.id:
            return await interaction.followup.send(
                "❌ **Anti-Corruption Rule:** You cannot vote for yourself! You gotta get other members to vote for you!",
                ephemeral=True
            )

        ele = await self._resolve_election(interaction)
        now = time.time()
        if not ele or now > ele["end_time"]:
            return await interaction.followup.send(
                "⚠️ There is currently no active voting cycle. Check `/election status` for updates.",
                ephemeral=True
            )

        success, msg = await self.bot.db.vote_candidate(ele["id"], user.id, candidate.id)
        if not success:
            return await interaction.followup.send(f"❌ {msg}", ephemeral=True)

        await interaction.followup.send(
            f"✅ **Ballot Cast!** You have successfully voted for {candidate.mention} as Mayor! Thanks for voting!",
            ephemeral=True
        )

    @election.command(name="start", description="[Admin/Staff] Manually trigger a fresh 48-hour Mayoral election cycle")
    @app_commands.describe(duration_hours="Duration of voting window in hours (default: 48)")
    @app_commands.default_permissions(manage_guild=True)
    async def election_start(self, interaction: discord.Interaction, duration_hours: int = 48):
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ You do not have permission to trigger city elections.", ephemeral=True)

        await interaction.response.defer()
        guild = interaction.guild or self.bot.get_guild(MAIN_GUILD_ID)
        gid = guild.id if guild else MAIN_GUILD_ID
        ele = await self._resolve_election(interaction)
        now = time.time()

        if ele and now < ele["end_time"]:
            return await interaction.followup.send(
                f"⚠️ An election is already actively underway! It concludes <t:{int(ele['end_time'])}:R>.",
                ephemeral=True
            )

        new_ele = await self.bot.db.create_election(gid, duration_hours=float(duration_hours))
        end_time_ts = int(new_ele["end_time"])

        embed = discord.Embed(
            title="🏛️ MAYORAL ELECTIONS ARE NOW OPEN!",
            description=(
                f"A new **{duration_hours}-Hour Election Cycle** has officially begun for the office of **Mayor**!\n\n"
                f"⏳ **Voting Deadline:** <t:{end_time_ts}:R> (<t:{end_time_ts}:F>)\n"
                f"💰 **Filing Fee to Run:** `{CANDIDATE_COST:,} Medals`\n"
                f"👥 **Candidate Limit:** Maximum `{MAX_CANDIDATES}` Candidates\n\n"
                f"**How to Participate:**\n"
                f"• Run for Mayor: `/election register <slogan>`\n"
                f"• Cast your Vote: `/election vote @candidate`\n"
                f"• View Polls: `/election status`\n\n"
                f"*Strict anti-self-vote and anti-corruption regulations are actively enforced.*"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text="Phantom Regiment Elections")
        await interaction.followup.send(embed=embed)

    # ── Mayoral Powers Group ──────────────────────────────────────────────────
    mayor = app_commands.Group(name="mayor", description="Executive powers reserved exclusively for the reigning Mayor")

    @mayor.command(name="doublexp", description="[Mayor Only] Activate server-wide 2X Double XP for 24 hours (Max 3 times per 2 weeks)")
    async def mayor_doublexp(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        if not await self.is_mayor(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Mayor holding the `🏛️ Mayor` role can activate Mayoral executive powers.",
                ephemeral=True
            )

        # Check if already active
        remaining = await self.bot.db.get_double_xp_remaining(guild.id)
        if remaining > 0:
            hrs = int(remaining // 3600)
            mins = int((remaining % 3600) // 60)
            return await interaction.response.send_message(
                f"⚠️ **2X XP is already running!** Time remaining: `{hrs}h {mins}m`. Wait until this surge ends before triggering another.",
                ephemeral=True
            )

        latest = await self.bot.db.get_latest_election(guild.id)
        ele_id = latest["id"] if latest else 0

        # Term limit: Max 3 times in 2 weeks
        uses = await self.bot.db.get_commander_action_count(ele_id, user.id, "doublexp")
        if uses >= MAX_DOUBLE_XP_PER_TERM:
            return await interaction.response.send_message(
                f"❌ **Term Quota Reached:** You have already used all **{MAX_DOUBLE_XP_PER_TERM} Double XP surges** for this 14-day Mayoral term.",
                ephemeral=True
            )

        await interaction.response.defer()
        expires_at = await self.bot.db.set_double_xp(guild.id, duration_seconds=86400.0)
        await self.bot.db.log_commander_action(
            ele_id, user.id, "doublexp", details=f"Activated 24h 2X XP surge ({uses + 1}/{MAX_DOUBLE_XP_PER_TERM})"
        )

        remaining_uses = MAX_DOUBLE_XP_PER_TERM - (uses + 1)
        embed = discord.Embed(
            title="⚡ MAYORAL SURGE: 2X DOUBLE XP ACTIVATED FOR 24 HOURS!",
            description=(
                f"Mayor {user.mention}:\n\n"
                f"🔥 **All chat XP earned across the entire server is DOUBLED (2x) for the next 24 hours!**\n\n"
                f"⏳ **Surge Concludes:** <t:{int(expires_at)}:R> (<t:{int(expires_at)}:F>)\n"
                f"🎩 **Mayoral 2XP Activations Left:** `{remaining_uses} / {MAX_DOUBLE_XP_PER_TERM}` this term.\n\n"
                f"*\"Get active, level up, and celebrate the Mayoral administration!\"*"
            ),
            color=0xF1C40F
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Decreed by Mayor {user.display_name} • City Hall Executive Office")
        await interaction.followup.send(content="@everyone ⚡ **2X DOUBLE XP IS LIVE!**", embed=embed)

    @mayor.command(name="salary", description="[Mayor Only] Collect your daily Mayoral executive salary (+12,500 Medals / day)")
    async def mayor_salary(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        if not await self.is_mayor(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Mayor can collect the Mayoral executive salary.",
                ephemeral=True
            )

        last_claimed = await self.bot.db.get_last_mayor_salary(user.id)
        now = time.time()
        cooldown = 86400.0  # 24 hours
        if now - last_claimed < cooldown:
            remaining = int(cooldown - (now - last_claimed))
            hrs = remaining // 3600
            mins = (remaining % 3600) // 60
            return await interaction.response.send_message(
                f"⏳ **Salary Cooldown:** You already collected today's salary! Next check available in `{hrs}h {mins}m`.",
                ephemeral=True
            )

        await self.bot.db.add_medals(user.id, guild.id, MAYOR_DAILY_SALARY)
        await self.bot.db.set_last_mayor_salary(user.id)

        econ = await self.bot.db.get_global_economy(user.id)
        embed = discord.Embed(
            title="💰 CITY HALL PAYROLL DISBURSED",
            description=(
                f"Mayor {user.mention}, your daily executive compensation has been disbursed from the City Treasury!\n\n"
                f"• **Salary Credited:** `+{MAYOR_DAILY_SALARY:,} Medals`\n"
                f"• **Current Wallet:** `{econ.get('medals', 0):,} Medals`\n"
                f"• **Next Disbursal:** In 24 hours\n\n"
                f"*Thank you for your dedicated public service to the city.*"
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="City Hall Payroll • Executive Compensation")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @mayor.command(name="award", description="[Mayor Only] Bestow the Key to the City (+15,000 Medals) upon a citizen")
    @app_commands.describe(member="The citizen to honor (Max 3 awards per term; CANNOT award to yourself)")
    async def mayor_award(self, interaction: discord.Interaction, member: discord.Member):
        guild = interaction.guild
        user = interaction.user

        if not await self.is_mayor(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Mayor can grant Mayoral honors.",
                ephemeral=True
            )

        # STRICT ANTI-SELF-ENRICHMENT LAW
        if member.id == user.id:
            return await interaction.response.send_message(
                "⛔ **Anti-Corruption Law:** Mayors cannot award city funds or honors to themselves! This power exists to reward your citizens.",
                ephemeral=True
            )

        if member.bot:
            return await interaction.response.send_message("❌ You cannot grant city awards to bots.", ephemeral=True)

        latest = await self.bot.db.get_latest_election(guild.id)
        ele_id = latest["id"] if latest else 0

        awards_count = await self.bot.db.get_commander_action_count(ele_id, user.id, "award")
        if awards_count >= MAX_AWARDS_PER_TERM:
            return await interaction.response.send_message(
                f"❌ **Term Quota Reached:** You have already issued the maximum allowed **{MAX_AWARDS_PER_TERM} Key to the City awards** for this term.",
                ephemeral=True
            )

        await interaction.response.defer()
        await self.bot.db.add_medals(member.id, guild.id, AWARD_AMOUNT)
        await self.bot.db.log_commander_action(
            ele_id, user.id, "award", target_id=member.id,
            details=f"Granted Key to the City (+{AWARD_AMOUNT:,} Medals)"
        )

        remaining = MAX_AWARDS_PER_TERM - (awards_count + 1)
        embed = discord.Embed(
            title="🔑 MAYORAL KEY TO THE CITY BESTOWED!",
            description=(
                f"Mayor {user.mention}:\n\n"
                f"Citizen {member.mention} has been honored with the prestigious **Key to the City** for outstanding civic contribution and loyalty!\n\n"
                f"💰 **City Bounty:** `+{AWARD_AMOUNT:,} Medals` transferred to {member.mention}'s wallet!\n"
                f"🎖️ **Mayoral Awards Left:** `{remaining} / {MAX_AWARDS_PER_TERM}` this term.\n\n"
                f"*\"A grateful city salutes its finest citizens!\"*"
            ),
            color=0xF1C40F
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Decreed by Mayor {user.display_name}")
        await interaction.followup.send(content=f"🎖️ Attention citizens: {member.mention}!", embed=embed)

    @mayor.command(name="stimulus", description="[Mayor Only] Release a public stimulus crate in chat for active citizens (Max 2 per term)")
    async def mayor_stimulus(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        if not await self.is_mayor(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Mayor can release city stimulus funds.",
                ephemeral=True
            )

        latest = await self.bot.db.get_latest_election(guild.id)
        ele_id = latest["id"] if latest else 0

        uses = await self.bot.db.get_commander_action_count(ele_id, user.id, "stimulus")
        if uses >= MAX_STIMULUS_PER_TERM:
            return await interaction.response.send_message(
                f"❌ **Term Quota Reached:** You have already released all **{MAX_STIMULUS_PER_TERM} stimulus packages** for this term.",
                ephemeral=True
            )

        await self.bot.db.log_commander_action(
            ele_id, user.id, "stimulus", details=f"Released public stimulus drop ({uses + 1}/{MAX_STIMULUS_PER_TERM})"
        )

        view = StimulusClaimView(self.bot, mayor_id=user.id, max_claims=4, grant_amount=2500)
        embed = discord.Embed(
            title="🏛️ MAYORAL STIMULUS PACKAGE RELEASED!",
            description=(
                f"Mayor {user.mention} has authorized a **10,000 Medal City Stimulus Package**!\n\n"
                f"• **Grants Available:** `4 Packages` of **2,500 Medals** each!\n"
                f"• **Eligibility:** First 4 citizens to click the button below claim the funds!\n"
                f"• **Anti-Corruption Rule:** The Mayor cannot claim their own stimulus!\n\n"
                f"*Click the button below before it runs out!*"
            ),
            color=0x2ECC71
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="City Hall Treasury • Public Economic Relief")
        await interaction.response.send_message(content="📦 **PUBLIC STIMULUS AIRDROP!**", embed=embed, view=view)

    @mayor.command(name="pardon", description="[Mayor Only] Issue a Mayoral Pardon to immediately clear a citizen's robbery cooldown")
    @app_commands.describe(member="The citizen to pardon (Max 3 per term; CANNOT pardon yourself)")
    async def mayor_pardon(self, interaction: discord.Interaction, member: discord.Member):
        user = interaction.user
        guild = interaction.guild

        if not await self.is_mayor(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Mayor can issue executive pardons.",
                ephemeral=True
            )

        if member.id == user.id:
            return await interaction.response.send_message(
                "⛔ **Anti-Corruption Law:** Mayors cannot pardon themselves!",
                ephemeral=True
            )

        if member.bot:
            return await interaction.response.send_message("❌ Cannot pardon bot systems.", ephemeral=True)

        latest = await self.bot.db.get_latest_election(guild.id)
        ele_id = latest["id"] if latest else 0

        uses = await self.bot.db.get_commander_action_count(ele_id, user.id, "pardon")
        if uses >= MAX_PARDONS_PER_TERM:
            return await interaction.response.send_message(
                f"❌ **Term Quota Reached:** You have already issued all **{MAX_PARDONS_PER_TERM} Mayoral Pardons** for this term.",
                ephemeral=True
            )

        await self.bot.db.mayoral_pardon(member.id, guild.id)
        await self.bot.db.log_commander_action(
            ele_id, user.id, "pardon", target_id=member.id, details="Cleared robbery and crime cooldowns"
        )

        remaining = MAX_PARDONS_PER_TERM - (uses + 1)
        embed = discord.Embed(
            title="⚖️ OFFICIAL MAYORAL PARDON GRANTED!",
            description=(
                f"By executive clemency of Mayor {user.mention}:\n\n"
                f"Citizen {member.mention} has received a full **Mayoral Pardon**!\n\n"
                f"• All criminal and robbery cooldowns have been cleared.\n"
                f"• Record wiped clean with immediate effect.\n"
                f"• **Mayoral Pardons Left:** `{remaining} / {MAX_PARDONS_PER_TERM}` this term.\n\n"
                f"*\"Justice tempered with mercy.\"*"
            ),
            color=0x3498DB
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Decreed by Mayor {user.display_name}")
        await interaction.response.send_message(embed=embed)

    @mayor.command(name="tax", description="[Mayor Only] Adjust the Stock Market transaction tax rate (10% to 20%)")
    @app_commands.describe(tax_pct="New tax percentage on stock sales (e.g. 10 to 20)")
    async def mayor_tax(self, interaction: discord.Interaction, tax_pct: int):
        user = interaction.user
        if not await self.is_mayor(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Mayor can adjust city tax policy.",
                ephemeral=True
            )

        if tax_pct < 10 or tax_pct > 20:
            return await interaction.response.send_message(
                "⚠️ Constitution limits: The Mayor can only set the stock market transaction tax between **10%** and **20%**.",
                ephemeral=True
            )

        latest = await self.bot.db.get_latest_election(interaction.guild_id)
        ele_id = latest["id"] if latest else 0
        await self.bot.db.log_commander_action(
            ele_id, user.id, "tax_policy", details=f"Adjusted stock brokerage tax to {tax_pct}%"
        )

        embed = discord.Embed(
            title="📈 MAYORAL EXECUTIVE ORDER: MARKET TRANSACTION TAX ADJUSTED",
            description=(
                f"Mayor {user.mention} has enacted a new fiscal tax regulation:\n\n"
                f"• **New Transaction Tax:** `{tax_pct}%`\n"
                f"• **Effective:** Immediate on all corporate stock transactions.\n\n"
                f"*Policy set under executive authority of the City Mayor.*"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text=f"Fiscal Policy • Mayor {user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ElectionsCog(bot))
