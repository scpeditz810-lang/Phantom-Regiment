import time
import discord
from discord.ext import commands, tasks
from discord import app_commands

CANDIDATE_COST = 400_000
MAX_CANDIDATES = 5
ELECTION_DURATION_HOURS = 48.0
MAX_AWARDS_PER_TERM = 3
AWARD_AMOUNT = 10_000

class ElectionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.election_loop.start()

    def cog_unload(self):
        self.election_loop.cancel()

    async def get_or_create_roles(self, guild: discord.Guild) -> tuple[discord.Role, discord.Role]:
        """Fetch or automatically create the required Supreme Commander and Candidate roles."""
        commander_role = discord.utils.get(guild.roles, name="🎖️ Supreme Commander")
        if not commander_role:
            try:
                commander_role = await guild.create_role(
                    name="🎖️ Supreme Commander",
                    color=discord.Color.from_rgb(241, 196, 15),
                    hoist=True,
                    reason="Phantom Regiment Supreme Commander Election Role"
                )
            except discord.Forbidden:
                commander_role = None

        candidate_role = discord.utils.get(guild.roles, name="🗳️ Election Candidate")
        if not candidate_role:
            try:
                candidate_role = await guild.create_role(
                    name="🗳️ Election Candidate",
                    color=discord.Color.from_rgb(52, 152, 219),
                    hoist=False,
                    reason="Phantom Regiment Election Candidate Role"
                )
            except discord.Forbidden:
                candidate_role = None

        return commander_role, candidate_role

    async def is_supreme_commander(self, member: discord.Member) -> bool:
        """Verify if a member is the active, officially crowned Supreme Commander."""
        if any(r.name == "🎖️ Supreme Commander" for r in member.roles):
            return True
        curr = await self.bot.db.get_current_commander(member.guild.id)
        if curr and curr.get("winner_id") == member.id:
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

                    commander_role, candidate_role = await self.get_or_create_roles(guild)
                    winner_id = finished_ele.get("winner_id")

                    # Remove old commander role from previous holders
                    if commander_role:
                        for m in commander_role.members:
                            if m.id != winner_id:
                                try:
                                    await m.remove_roles(commander_role, reason="Supreme Commander term ended.")
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
                    if winner_member and commander_role:
                        try:
                            await winner_member.add_roles(commander_role, reason="Won Supreme Commander Election!")
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
                                title="🏛️ ELECTION RESULTS: SUPREME COMMANDER DECLARED!",
                                description=(
                                    f"The 48-hour voting period has concluded!\n\n"
                                    f"🎖️ **All hail the newly elected Supreme Commander:** {winner_member.mention}!\n\n"
                                    f"• **Winning Ballots:** `{votes}` votes\n"
                                    f"• **Official Term:** 14 Days\n"
                                    f"• **Executive Power:** Can issue up to 3 Medals of Honor, set market trade taxes, and rally the troops!\n\n"
                                    f"*\"Salute the Commander, defend the Regiment!\"*"
                                ),
                                color=0xF1C40F
                            )
                            embed.set_thumbnail(url=winner_member.display_avatar.url)
                            embed.set_footer(text="Phantom Regiment High Council • Democratic Command")
                            await channel.send(content=f"🎉 Congratulations {winner_member.mention}!", embed=embed)
                        else:
                            embed = discord.Embed(
                                title="🏛️ ELECTION CONCLUDED — NO CANDIDATES",
                                description="The 48-hour election cycle ended with zero registered candidates. The position remains vacant until the next election.",
                                color=0x95A5A6
                            )
                            await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ Error in election loop: {e}", flush=True)

    @election_loop.before_loop
    async def before_election_loop(self):
        await self.bot.wait_until_ready()

    # ── Election Command Group ────────────────────────────────────────────────
    election = app_commands.Group(name="election", description="Phantom Regiment Supreme Commander democratic elections")

    @election.command(name="status", description="View current election status, countdown, registered candidates, and ballots")
    async def election_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        ele = await self.bot.db.get_active_election(guild.id)
        now = time.time()

        if not ele or now > ele["end_time"]:
            latest = await self.bot.db.get_latest_election(guild.id)
            winner_id = latest.get("winner_id") if latest else None
            winner_member = guild.get_member(winner_id) if winner_id else None
            term_end = latest.get("term_end", 0) if latest else 0

            embed = discord.Embed(
                title="🏛️ Phantom Regiment Supreme Commander — Council Status",
                description=(
                    "There is currently **no active voting in progress**.\n\n"
                    + (
                        f"🎖️ **Current Supreme Commander:** {winner_member.mention if winner_member else f'<@{winner_id}>'}\n"
                        f"⏳ **Term Expiration:** <t:{int(term_end)}:R> (<t:{int(term_end)}:F>)\n\n"
                        if winner_id and now < term_end
                        else "🎖️ **Current Supreme Commander:** *Vacant — Ready for a new election!*\n\n"
                    )
                    + f"To register as a candidate and trigger a 48-hour election cycle, run `/election register <slogan>` (Entry Fee: **{CANDIDATE_COST:,} Medals**)."
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
            title="🗳️ SUPREME COMMANDER ELECTION — VOTING IN PROGRESS",
            description=(
                f"Citizens of the Regiment, cast your ballot! The elected Supreme Commander will lead the military council.\n\n"
                f"⏳ **Voting Closes:** <t:{end_time_ts}:R> (<t:{end_time_ts}:F>)\n"
                f"📊 **Total Ballots Cast:** `{total_votes:,}`\n"
                f"👥 **Candidate Slots:** `{len(cands)} / {MAX_CANDIDATES}` filled\n"
                f"💰 **Candidate Entry Fee:** `{CANDIDATE_COST:,} Medals`\n\n"
                f"Vote using: `/election vote @candidate`\n"
                f"Register using: `/election register <slogan>`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x2ECC71
        )

        if not cands:
            embed.add_field(
                name="📋 Registered Candidates",
                value="*No candidates have registered yet! Be the first to register with `/election register <slogan>`!*",
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
                    value=f"`[{bar}]`\n💬 *\"{c.get('slogan') or 'For the glory of Phantom Regiment!'}\"*",
                    inline=False
                )

        has_voted = await self.bot.db.has_user_voted(ele["id"], interaction.user.id)
        status_text = "✅ You have already cast your ballot in this election." if has_voted else "⚠️ You have not voted yet! Use `/election vote @candidate` to vote."
        embed.set_footer(text=f"{status_text} • Anti-self-vote enforced")
        await interaction.followup.send(embed=embed)

    @election.command(name="register", description="Register as an official candidate for Supreme Commander (Cost: 400,000 Medals, Max 5)")
    @app_commands.describe(slogan="Your official campaign motto or policy promise (max 120 chars)")
    async def election_register(self, interaction: discord.Interaction, slogan: str):
        await interaction.response.defer()
        guild = interaction.guild
        user = interaction.user

        # Fetch or auto-create election
        ele = await self.bot.db.get_active_election(guild.id)
        now = time.time()
        if not ele or now > ele["end_time"]:
            # Auto-start new 48h election cycle
            ele = await self.bot.db.create_election(guild.id, duration_hours=ELECTION_DURATION_HOURS)

        # Check existing candidates count
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

        # Check wallet medals
        econ = await self.bot.db.get_global_economy(user.id)
        wallet = econ.get("medals", 0)
        if wallet < CANDIDATE_COST:
            return await interaction.followup.send(
                f"❌ **Insufficient Wallet Medals:** Registering for Supreme Commander requires **{CANDIDATE_COST:,} Medals** in your wallet. (You currently hold: `{wallet:,} Medals`). Withdraw from `/bank` if needed!",
                ephemeral=True
            )

        # Deduct registration fee
        await self.bot.db.add_medals(user.id, guild.id, -CANDIDATE_COST)

        # Register candidate
        success, msg = await self.bot.db.register_candidate(ele["id"], user.id, slogan)
        if not success:
            # Refund in case of race condition
            await self.bot.db.add_medals(user.id, guild.id, CANDIDATE_COST)
            return await interaction.followup.send(f"❌ Registration failed: {msg}", ephemeral=True)

        # Assign Election Candidate role
        _, candidate_role = await self.get_or_create_roles(guild)
        if candidate_role:
            try:
                await user.add_roles(candidate_role, reason="Registered as Election Candidate")
            except Exception:
                pass

        end_time_ts = int(ele["end_time"])
        embed = discord.Embed(
            title="📢 CANDIDATE REGISTRATION DECLARED!",
            description=(
                f"{user.mention} has paid the **{CANDIDATE_COST:,} Medals** filing fee and is officially running for **Supreme Commander**!\n\n"
                f"💬 **Campaign Slogan:**\n*\"{slogan}\"*\n\n"
                f"👥 **Candidate Slots:** `{len(cands) + 1} / {MAX_CANDIDATES}` Filled\n"
                f"⏳ **Voting Closes:** <t:{end_time_ts}:R>\n\n"
                f"Vote for your commander now using `/election vote {user.mention}`!"
            ),
            color=0x3498DB
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="Democracy in the Regiment • 1 Vote Per Citizen")
        await interaction.followup.send(embed=embed)

    @election.command(name="vote", description="Cast your ballot for a registered Supreme Commander candidate")
    @app_commands.describe(candidate="The registered candidate you wish to vote for")
    async def election_vote(self, interaction: discord.Interaction, candidate: discord.Member):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user

        # Anti-self-vote rule
        if candidate.id == user.id:
            return await interaction.followup.send(
                "❌ **Anti-Corruption Rule:** You cannot vote for yourself! Democracy requires other Regiment citizens to support your candidacy.",
                ephemeral=True
            )

        ele = await self.bot.db.get_active_election(guild.id)
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
            f"✅ **Ballot Cast!** You have successfully voted for {candidate.mention} as Supreme Commander! Thank you for participating in Regiment democracy.",
            ephemeral=True
        )

    @election.command(name="start", description="[Admin/Staff] Manually trigger a fresh 48-hour Supreme Commander election cycle")
    @app_commands.describe(duration_hours="Duration of voting window in hours (default: 48)")
    @app_commands.default_permissions(manage_guild=True)
    async def election_start(self, interaction: discord.Interaction, duration_hours: int = 48):
        if not interaction.user.guild_permissions.manage_guild and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("⛔ You do not have permission to trigger server elections.", ephemeral=True)

        await interaction.response.defer()
        guild = interaction.guild
        ele = await self.bot.db.get_active_election(guild.id)
        now = time.time()

        if ele and now < ele["end_time"]:
            return await interaction.followup.send(
                f"⚠️ An election is already actively underway! It concludes <t:{int(ele['end_time'])}:R>.",
                ephemeral=True
            )

        new_ele = await self.bot.db.create_election(guild.id, duration_hours=float(duration_hours))
        end_time_ts = int(new_ele["end_time"])

        embed = discord.Embed(
            title="🏛️ THE HIGH COUNCIL HAS DECREED: ELECTION SEASON IS OPEN!",
            description=(
                f"A new **{duration_hours}-Hour Election Cycle** has officially begun for the title of **Supreme Commander**!\n\n"
                f"⏳ **Voting Deadline:** <t:{end_time_ts}:R> (<t:{end_time_ts}:F>)\n"
                f"💰 **Filing Fee to Run:** `{CANDIDATE_COST:,} Medals`\n"
                f"👥 **Candidate Limit:** Maximum `{MAX_CANDIDATES}` Candidates\n\n"
                f"**How to Participate:**\n"
                f"• Run for Commander: `/election register <slogan>`\n"
                f"• Cast your Vote: `/election vote @candidate`\n"
                f"• View Polls: `/election status`\n\n"
                f"*Strict anti-self-vote and anti-corruption regulations are actively enforced.*"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text="Phantom Regiment Electoral Commission")
        await interaction.followup.send(embed=embed)

    # ── Supreme Commander Powers Group ────────────────────────────────────────
    commander = app_commands.Group(name="commander", description="Executive powers reserved exclusively for the reigning Supreme Commander")

    @commander.command(name="award", description="[Commander Only] Bestow the Medal of Honor (+10,000 Medals) upon a deserving soldier")
    @app_commands.describe(member="The soldier to honor (Max 3 awards per term; CANNOT award to yourself)")
    async def commander_award(self, interaction: discord.Interaction, member: discord.Member):
        guild = interaction.guild
        user = interaction.user

        if not await self.is_supreme_commander(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Supreme Commander holding the `🎖️ Supreme Commander` title can invoke executive powers.",
                ephemeral=True
            )

        # STRICT ANTI-SELF-ENRICHMENT LAW
        if member.id == user.id:
            return await interaction.response.send_message(
                "⛔ **Anti-Corruption Law:** Supreme Commanders cannot grant state funds or medals to themselves! This power exists to reward your soldiers.",
                ephemeral=True
            )

        if member.bot:
            return await interaction.response.send_message("❌ You cannot grant medals to bot systems.", ephemeral=True)

        latest = await self.bot.db.get_latest_election(guild.id)
        election_id = latest["id"] if latest else 0

        awards_count = await self.bot.db.get_commander_awards_count(election_id, user.id)
        if awards_count >= MAX_AWARDS_PER_TERM:
            return await interaction.response.send_message(
                f"❌ **Term Quota Reached:** You have already issued the maximum allowed **{MAX_AWARDS_PER_TERM} Medals of Honor** for this 14-day administration.",
                ephemeral=True
            )

        await interaction.response.defer()

        # Award medals
        await self.bot.db.add_medals(member.id, guild.id, AWARD_AMOUNT)
        await self.bot.db.log_commander_action(
            election_id, user.id, "award", target_id=member.id,
            details=f"Granted Medal of Honor (+{AWARD_AMOUNT:,} Medals)"
        )

        remaining = MAX_AWARDS_PER_TERM - (awards_count + 1)
        embed = discord.Embed(
            title="🎖️ SUPREME COMMANDER MEDAL OF HONOR BESTOWED!",
            description=(
                f"By official executive decree of Supreme Commander {user.mention}:\n\n"
                f"Soldier {member.mention} has been decorated with the prestigious **Regiment Medal of Honor** for distinguished valor and active service!\n\n"
                f"💰 **State Bounty:** `+{AWARD_AMOUNT:,} Medals` transferred to {member.mention}'s wallet!\n"
                f"🎖️ **Commander Awards Remaining:** `{remaining} / {MAX_AWARDS_PER_TERM}` for this term.\n\n"
                f"*\"Valor recognized, loyalty rewarded.\"*"
            ),
            color=0xF1C40F
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Decreed by Supreme Commander {user.display_name}")
        await interaction.followup.send(content=f"🎖️ Attention on deck: {member.mention}!", embed=embed)

    @commander.command(name="address", description="[Commander Only] Broadcast an official Supreme Commander military address to the Regiment")
    @app_commands.describe(proclamation="Your official decree, battle order, or message to the troops")
    async def commander_address(self, interaction: discord.Interaction, proclamation: str):
        user = interaction.user
        if not await self.is_supreme_commander(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Supreme Commander can broadcast official executive addresses.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🎖️ OFFICIAL COMMUNIQUE FROM THE SUPREME COMMANDER",
            description=f"### Proclamation from {user.mention}:\n\n> *\"{proclamation}\"*\n\n**Stand firm, soldiers of the Phantom Regiment!**",
            color=0xF1C40F
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Decreed by Supreme Commander {user.display_name} • Regiment High Command")
        await interaction.response.send_message(embed=embed)

    @commander.command(name="tax", description="[Commander Only] Adjust the Stock Market transaction tax rate (10% to 20%)")
    @app_commands.describe(tax_pct="New tax percentage on stock sales (e.g. 10 to 20)")
    async def commander_tax(self, interaction: discord.Interaction, tax_pct: int):
        user = interaction.user
        if not await self.is_supreme_commander(user):
            return await interaction.response.send_message(
                "⛔ **Access Denied:** Only the reigning Supreme Commander can adjust state tax policy.",
                ephemeral=True
            )

        if tax_pct < 10 or tax_pct > 20:
            return await interaction.response.send_message(
                "⚠️ Constitution limits: Supreme Commander can only set the stock market transaction tax between **10%** and **20%**.",
                ephemeral=True
            )

        latest = await self.bot.db.get_latest_election(interaction.guild_id)
        ele_id = latest["id"] if latest else 0
        await self.bot.db.log_commander_action(
            ele_id, user.id, "tax_policy", details=f"Adjusted stock brokerage tax to {tax_pct}%"
        )

        embed = discord.Embed(
            title="📈 EXECUTIVE ORDER: STOCK MARKET TRANSACTION TAX ADJUSTED",
            description=(
                f"Supreme Commander {user.mention} has enacted a new fiscal tax regulation:\n\n"
                f"• **New Transaction Tax:** `{tax_pct}%`\n"
                f"• **Effective:** Immediate on all corporate stock transactions.\n\n"
                f"*Policy set under executive authority of the Supreme Commander.*"
            ),
            color=0xF1C40F
        )
        embed.set_footer(text=f"Fiscal Policy • Supreme Commander {user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ElectionsCog(bot))
