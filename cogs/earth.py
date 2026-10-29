# -*- coding: utf-8 -*-
"""
Virtual Earth: 3D Global Geopolitics MMO Simulation Cog
Commands for national governance, cabinet appointments, infrastructure, espionage, and conquest.
"""

import time
import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.earth_anim import (
    create_war_declared_gif,
    create_war_declared_media,
    create_war_ended_gif,
    create_war_ended_media,
    create_new_ruler_gif,
    create_country_fallen_gif,
    create_country_fallen_media,
    create_country_allied_gif,
    create_country_allied_media,
    create_new_commander_gif,
    create_new_commander_media,
    generate_tactical_audio,
    generate_voice_narration,
    generate_ruler_speech,
    generate_war_speech,
    generate_surrender_speech,
    generate_victory_speech,
    generate_country_fallen_speech,
    generate_alliance_speech,
    generate_commander_speech,
)

from utils.constants import (
    EARTH_CABINET_ROLES,
    EARTH_BUILDINGS,
    EARTH_WAR_SCALES,
    EARTH_SPY_MISSIONS,
    EARTH_DOCTRINES
)

from cogs.earth_dashboards import (
    build_defense_embed,
    build_economy_embed,
    build_diplomacy_embed,
    build_intelligence_embed,
    build_president_embed,
    DefenseDashboardView,
    EconomyDashboardView,
    DiplomacyDashboardView,
    IntelligenceDashboardView,
    PresidentDashboardView,
    MinistryHubView
)

WEB_URL = "https://phantomregiment.apps.bot-hosting.cloud/earth"
EARTH_NEWS_CHANNEL_ID = 1565082328550613083
EARTH_NEWS_ROLE_ID = 1565081681495597217


class CabinetInviteView(discord.ui.View):
    def __init__(self, bot, invite_id: int, target_user_id: int, president_id: int, role_title: str, country_name: str, country_flag: str):
        super().__init__(timeout=86400)
        self.bot = bot
        self.invite_id = invite_id
        self.target_user_id = target_user_id
        self.president_id = president_id
        self.role_title = role_title
        self.country_name = country_name
        self.country_flag = country_flag

    @discord.ui.button(label="Accept Appointment", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user_id:
            await interaction.response.send_message("❌ This ministerial appointment was offered to someone else!", ephemeral=True)
            return
        await interaction.response.defer()
        success, msg = await self.bot.db.respond_earth_cabinet_invite(self.target_user_id, self.invite_id, accept=True)
        if success:
            for child in self.children:
                child.disabled = True
            embed = discord.Embed(
                title="🏛️ Cabinet Decree Accepted",
                description=(
                    f"🎉 **<@{self.target_user_id}>** has formally accepted the appointment!\n\n"
                    f"**Portfolio:** {self.role_title}\n"
                    f"**Sovereign Nation:** {self.country_flag} {self.country_name}\n\n"
                    f"*The minister now shares executive portfolio authority with the President.*"
                ),
                color=0x2ECC71
            )
            embed.set_footer(text="Virtual Earth Cabinet • Oath of office formally taken.")
            await interaction.message.edit(embed=embed, view=self)
            await interaction.followup.send(f"✅ You have officially assumed office as **{self.role_title}** of **{self.country_name}**!", ephemeral=True)
            if "defense" in str(getattr(self, "role_title", "")).lower() or "commander" in str(getattr(self, "role_title", "")).lower():
                earth_cog = self.bot.get_cog("Virtual Earth") or self.bot.get_cog("EarthCog")
                if earth_cog:
                    await earth_cog.broadcast_commander_news(self.country_name, self.country_flag, interaction.user.display_name)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target_user_id:
            await interaction.response.send_message("❌ This ministerial appointment was offered to someone else!", ephemeral=True)
            return
        await interaction.response.defer()
        success, msg = await self.bot.db.respond_earth_cabinet_invite(self.target_user_id, self.invite_id, accept=False)
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="🏛️ Cabinet Decree Declined",
            description=f"**<@{self.target_user_id}>** has turned down the nomination for **{self.role_title}** of **{self.country_name}**.",
            color=0x95A5A6
        )
        embed.set_footer(text="Virtual Earth Cabinet • Decree vacated.")
        await interaction.message.edit(embed=embed, view=self)
        await interaction.followup.send("Appointment decree declined.", ephemeral=True)


class WarSurrenderView(discord.ui.View):
    def __init__(self, bot, war_id: int, atk_id: int, atk_owner: int, atk_name: str, atk_flag: str,
                 dfn_id: int, dfn_owner: int, dfn_name: str, dfn_flag: str):
        super().__init__(timeout=86400 * 7)
        self.bot = bot
        self.war_id = war_id
        self.atk_id = atk_id
        self.atk_owner = atk_owner
        self.atk_name = atk_name
        self.atk_flag = atk_flag
        self.dfn_id = dfn_id
        self.dfn_owner = dfn_owner
        self.dfn_name = dfn_name
        self.dfn_flag = dfn_flag
        self.add_item(discord.ui.Button(label="🌍 Open 3D War Room", url=WEB_URL, style=discord.ButtonStyle.link))

    @discord.ui.button(label="🏳️ Surrender / Concede War", style=discord.ButtonStyle.danger, emoji="🏳️", custom_id="earth_war_surrender_btn")
    async def surrender_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        is_atk = (user_id == self.atk_owner)
        is_dfn = (user_id == self.dfn_owner)

        if not (is_atk or is_dfn):
            c = await self.bot.db.get_user_earth_country(user_id)
            if c:
                if c["id"] == self.atk_id and c.get("owner_id") == user_id:
                    is_atk = True
                elif c["id"] == self.dfn_id and c.get("owner_id") == user_id:
                    is_dfn = True
                else:
                    roles = await self.bot.db.get_user_cabinet_roles(user_id, c["id"])
                    if any(r in roles for r in ("defense", "general", "president", "marshal")):
                        if c["id"] == self.atk_id:
                            is_atk = True
                        elif c["id"] == self.dfn_id:
                            is_dfn = True

        if not (is_atk or is_dfn):
            await interaction.response.send_message(
                "❌ Only the sovereign ruler or Minister of Defense of the warring countries can surrender this campaign!",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        success, msg, res_data = await self.bot.db.surrender_earth_war(user_id, self.war_id)
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        if is_dfn:
            winner_name, winner_flag = self.atk_name, self.atk_flag
            loser_name, loser_flag = self.dfn_name, self.dfn_flag
        else:
            winner_name, winner_flag = self.dfn_name, self.dfn_flag
            loser_name, loser_flag = self.atk_name, self.atk_flag

        loot = res_data.get("loot", 0)
        annexed = res_data.get("annexed", False)

        speech_buf = generate_surrender_speech(winner_name, loser_name, loot)
        gif, mp4_buf = create_war_ended_media(winner_name, loser_name, reason="SURRENDER CONCEDED", reparations=loot, audio_bytes=speech_buf)

        desc = (
            f"👑 **Victor:** {winner_flag} **{winner_name}**\n"
            f"🏳️ **Surrendered:** {loser_flag} **{loser_name}** (Conceded by {interaction.user.mention})\n"
            f"💰 **Indemnity Awarded:** `+{loot:,} Medals`\n"
            f"🌐 **Territorial State:** {'Annexed into imperial dominion!' if annexed else 'Territory borders stabilized.'}\n\n"
            f"🕊️ Armistice signed! War operations have terminated immediately."
        )

        button.disabled = True
        button.label = "🏳️ Concluded via Surrender"
        button.style = discord.ButtonStyle.secondary
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        res_files = []
        res_embed = discord.Embed(
            title="🏳️ FORMAL SURRENDER ACCEPTED // CONFLICT CONCLUDED",
            description=desc,
            color=0xEAB308
        )
        if mp4_buf:
            mp4_buf.seek(0)
            res_files.append(discord.File(mp4_buf, filename="surrender_concluded.mp4"))
            res_embed.set_footer(text="Virtual Earth 3D Geopolitics • Deep Voice Video Player Attached 🎬🎙️")
        else:
            if gif is not None:
                gif.seek(0)
                res_files.append(discord.File(gif, filename="surrender.gif"))
                res_embed.set_image(url="attachment://surrender.gif")
            if speech_buf:
                speech_buf.seek(0)
                res_files.append(discord.File(speech_buf, filename="voice_announcement.mp3"))
            res_embed.set_footer(text="Virtual Earth Geopolitics • Voice Narration Attached 🎙️")

        await interaction.followup.send(embed=res_embed, files=res_files)

        # Broadcast to news channel
        earth_cog = self.bot.get_cog("Virtual Earth") or self.bot.get_cog("EarthCog")
        if earth_cog:
            await earth_cog.broadcast_surrender_news(
                winner_name=winner_name,
                winner_flag=winner_flag,
                loser_name=loser_name,
                loser_flag=loser_flag,
                loot=loot,
                annexed=annexed,
                conceded_by=interaction.user.mention
            )


class EarthCog(commands.Cog, name="Virtual Earth"):
    """Global sovereign governance, cabinet appointments, and military conquests."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not self.earth_war_checker.is_running():
            self.earth_war_checker.start()

    def cog_unload(self):
        if self.earth_war_checker.is_running():
            self.earth_war_checker.cancel()

    async def broadcast_news(
        self,
        title: str,
        description: str,
        gif_bytes=None,
        filename: str = "news.gif",
        color: int = 0x38BDF8,
        audio_type: str = None,
        voice_speech: str = None,
        speech_bytes=None,
        video_bytes=None,
        view: discord.ui.View = None
    ):
        try:
            channel = self.bot.get_channel(EARTH_NEWS_CHANNEL_ID)
            if not channel:
                channel = await self.bot.fetch_channel(EARTH_NEWS_CHANNEL_ID)
            if channel:
                files_to_send = []
                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=color
                )

                if video_bytes is not None:
                    # Send actual playable video player with deep male announcer voice!
                    video_bytes.seek(0)
                    files_to_send.append(discord.File(video_bytes, filename="broadcast_video.mp4"))
                    embed.set_footer(text="Virtual Earth 3D Geopolitics • Deep Voice Video Player Attached 🎬🎙️")
                else:
                    # Fallback to GIF + audio if video rendering wasn't generated
                    if gif_bytes is not None:
                        gif_bytes.seek(0)
                        files_to_send.append(discord.File(gif_bytes, filename=filename))
                        embed.set_image(url=f"attachment://{filename}")

                    # Spoken Announcer Voice Narration (TTS)
                    if speech_bytes is not None:
                        speech_bytes.seek(0)
                        files_to_send.append(discord.File(speech_bytes, filename="voice_announcement.mp3"))
                    elif voice_speech:
                        try:
                            voice_buf = generate_voice_narration(voice_speech)
                            voice_buf.seek(0)
                            files_to_send.append(discord.File(voice_buf, filename="voice_announcement.mp3"))
                        except Exception as voice_err:
                            print(f"⚠️ Voice narration notice: {voice_err}", flush=True)

                    if audio_type and not (speech_bytes or voice_speech):
                        try:
                            audio_buf = generate_tactical_audio(audio_type)
                            files_to_send.append(discord.File(audio_buf, filename=f"{audio_type}.wav"))
                        except Exception as sound_err:
                            print(f"⚠️ Sound synthesis notice: {sound_err}", flush=True)

                    embed.set_footer(text="Virtual Earth 3D Geopolitics • Spoken Narration Attached 🎙️")

                await channel.send(
                    content=f"<@&{EARTH_NEWS_ROLE_ID}> 🚨 **SOVEREIGN GEOPOLITICAL DISPATCH!**",
                    embed=embed,
                    files=files_to_send,
                    view=view
                )
        except Exception as e:
            print(f"⚠️ Failed to broadcast Earth News: {e}", flush=True)

    async def broadcast_alliance_news(self, country_a_name: str, country_a_flag: str, country_b_name: str, country_b_flag: str, alliance_name: str):
        """Broadcast international alliance formation / accession to #earth-news with animated card & audio."""
        try:
            speech_buf = generate_alliance_speech(country_a_name, country_b_name, alliance_name)
            gif_buf, mp4_buf = create_country_allied_media(country_a_name, country_a_flag, country_b_name, country_b_flag, alliance_name, audio_bytes=speech_buf)
            title = f"🤝 STRATEGIC ALLIANCE RATIFIED // {alliance_name.upper()}"
            desc = (
                f"**Strategic Alliance Formed!**\n\n"
                f"🏛️ **Treaty Coalition:** `{alliance_name}`\n"
                f"🤝 **Allied Nations:** {country_a_flag} **{country_a_name}** ⮂ **{country_b_flag} {country_b_name}**\n\n"
                f"🛡️ **Mutual Defense Pact:** All allied states receive collective security guarantees (+25 Defense per ally).\n"
                f"🌐 *Sovereign borders and mutual trade are officially ratified under international accord.*"
            )
            await self.broadcast_news(
                title=title,
                description=desc,
                gif_bytes=gif_buf,
                filename="alliance_news.gif",
                color=0x10B981,
                speech_bytes=speech_buf,
                video_bytes=mp4_buf
            )
        except Exception as e:
            print(f"⚠️ Error broadcasting alliance news: {e}", flush=True)

    async def broadcast_commander_news(self, country_name: str, country_flag: str, commander_name: str):
        """Broadcast supreme army commander / defense minister appointment to #earth-news with animated card & audio."""
        try:
            speech_buf = generate_commander_speech(country_name, commander_name)
            gif_buf, mp4_buf = create_new_commander_media(country_name, country_flag, commander_name, audio_bytes=speech_buf)
            title = f"⚔️ SUPREME COMMAND APPOINTMENT // {country_name.upper()}"
            desc = (
                f"**New Supreme Military Commander Appointed!**\n\n"
                f"🏛️ **Sovereign Nation:** {country_flag} **{country_name}**\n"
                f"⭐ **Supreme Army Commander & Defense Minister:** **{commander_name}**\n\n"
                f"🛡️ **High Command Authority:** Strategic control over Armored Divisions, Air Defense, Navy & Nuclear Deterrence.\n"
                f"⚡ *All territorial defense forces and border garrisons are mobilized under direct supreme command.*"
            )
            await self.broadcast_news(
                title=title,
                description=desc,
                gif_bytes=gif_buf,
                filename="commander_news.gif",
                color=0xE11D48,
                speech_bytes=speech_buf,
                video_bytes=mp4_buf
            )
        except Exception as e:
            print(f"⚠️ Error broadcasting commander news: {e}", flush=True)

    async def broadcast_war_declared(self, attacker_c: dict, defender_c: dict, scale_name: str, duration_hours: int, war_id: int, domain: str = "land", aggressor_mention: str = None):
        """Broadcast sovereign war declaration to #earth-news with animated card, announcer voice & surrender controls."""
        try:
            news_speech_buf = generate_war_speech(attacker_c["name"], defender_c["name"], scale_name)
            news_gif, news_mp4 = create_war_declared_media(attacker_c["name"], defender_c["name"], scale_name, domain, audio_bytes=news_speech_buf)
            news_view = WarSurrenderView(
                self.bot, war_id,
                attacker_c["id"], attacker_c.get("owner_id"), attacker_c["name"], attacker_c["flag"],
                defender_c["id"], defender_c.get("owner_id"), defender_c["name"], defender_c["flag"]
            )
            agg_str = aggressor_mention or f"<@{attacker_c.get('owner_id')}>"
            tgt_owner = defender_c.get("owner_id")
            def_str = f"<@{tgt_owner}>" if tgt_owner else "*State Trust*"
            news_desc = (
                f"⚔️ **Aggressor State:** {attacker_c['flag']} **{attacker_c['name']}** (Leader: {agg_str})\n"
                f"🛡️ **Target State:** {defender_c['flag']} **{defender_c['name']}** (Leader: {def_str})\n"
                f"🌐 **Conflict Scale:** `{scale_name}` ({duration_hours} Hours)\n\n"
                f"⚠️ Active combat hostilities are declared! Leaders may mobilize divisions or concede via the surrender button below."
            )
            await self.broadcast_news(
                title="🚨 SOVEREIGN WAR COMMENCED // ACTIVE FRONTLINE",
                description=news_desc,
                gif_bytes=news_gif,
                filename="war_news.gif",
                color=0xDC2626,
                speech_bytes=news_speech_buf,
                video_bytes=news_mp4,
                view=news_view
            )
        except Exception as e:
            print(f"⚠️ Error broadcasting war declared news: {e}", flush=True)

    async def broadcast_surrender_news(
        self,
        winner_name: str,
        winner_flag: str,
        loser_name: str,
        loser_flag: str,
        loot: int = 0,
        annexed: bool = False,
        conceded_by: str = None
    ):
        """Broadcast sovereign war surrender concession to #earth-news with animated video & audio."""
        try:
            speech_buf = generate_surrender_speech(winner_name, loser_name, loot)
            gif_buf, mp4_buf = create_war_ended_media(winner_name, loser_name, reason="SURRENDER CONCEDED", reparations=loot, audio_bytes=speech_buf)
            conceded_suffix = f" (Conceded by {conceded_by})" if conceded_by else ""
            desc = (
                f"👑 **Victor:** {winner_flag} **{winner_name}**\n"
                f"🏳️ **Surrendered:** {loser_flag} **{loser_name}**{conceded_suffix}\n"
                f"💰 **Indemnity Awarded:** `+{loot:,} Medals`\n"
                f"🌐 **Territorial State:** {'Annexed into imperial dominion!' if annexed else 'Territory borders stabilized.'}\n\n"
                f"🕊️ Armistice signed! War operations have terminated immediately."
            )
            await self.broadcast_news(
                title="🏳️ SOVEREIGN SURRENDER // WAR TERMINATED",
                description=desc,
                gif_bytes=gif_buf,
                filename="surrender_news.gif",
                color=0xEAB308,
                speech_bytes=speech_buf,
                video_bytes=mp4_buf
            )
            if annexed:
                fallen_speech = generate_country_fallen_speech(loser_name, winner_name)
                fallen_gif, fallen_mp4 = create_country_fallen_media(loser_name, winner_name, audio_bytes=fallen_speech)
                fallen_desc = (
                    f"🏚️ **Fallen Nation:** {loser_flag} **{loser_name}**\n"
                    f"👑 **Conquering Empire:** {winner_flag} **{winner_name}**\n"
                    f"🌐 **Sovereign Status:** Annexed! National sovereignty extinguished and integrated into imperial dominion."
                )
                await self.broadcast_news(
                    title="⚠️ SOVEREIGN STATE FALLEN // ANNEXATION COMPLETE",
                    description=fallen_desc,
                    gif_bytes=fallen_gif,
                    filename="country_fallen.gif",
                    color=0xDC2626,
                    speech_bytes=fallen_speech,
                    video_bytes=fallen_mp4
                )
        except Exception as e:
            print(f"⚠️ Error broadcasting surrender news: {e}", flush=True)

    @tasks.loop(seconds=60)
    async def earth_war_checker(self):
        try:
            concluded = await self.bot.db.resolve_concluded_earth_wars()
            for res in concluded:
                if res.get("status") in ("attacker_won", "defender_won"):
                    war = await self.bot.db.get_earth_war(res["war_id"])
                    if war:
                        is_atk_win = res["status"] == "attacker_won"
                        winner_name = war["attacker_name"] if is_atk_win else war["defender_name"]
                        winner_flag = war["attacker_flag"] if is_atk_win else war["defender_flag"]
                        loser_name = war["defender_name"] if is_atk_win else war["attacker_name"]
                        loser_flag = war["defender_flag"] if is_atk_win else war["attacker_flag"]
                        reparations = war.get("reparations", 100000)
                        annexed = res.get("annexed", False) or (war.get("scale") == "annexation")

                        speech_buf = generate_victory_speech(winner_name, loser_name, reparations)
                        gif, mp4_buf = create_war_ended_media(
                            winner_name=winner_name,
                            loser_name=loser_name,
                            reason="CAMPAIGN VICTORY",
                            reparations=reparations,
                            audio_bytes=speech_buf
                        )
                        desc = (
                            f"**Victorious Empire:** {winner_flag} **{winner_name}**\n"
                            f"**Defeated State:** {loser_flag} **{loser_name}**\n"
                            f"⚔️ **Campaign Duration:** Elapsed full duration\n"
                            f"💰 **Indemnity Awarded:** `+{reparations:,} Medals`\n\n"
                            f"🏆 Frontline military victory achieved! Troops return home."
                        )
                        await self.broadcast_news(
                            title="🏆 CONFLICT CONCLUDED // CAMPAIGN DECISIVE VICTORY",
                            description=desc,
                            gif_bytes=gif,
                            filename="war_ended.gif",
                            color=0x10B981,
                            speech_bytes=speech_buf,
                            video_bytes=mp4_buf
                        )

                        # If state fell / annexed, broadcast country fallen card & speech!
                        if annexed:
                            fallen_speech = generate_country_fallen_speech(loser_name, winner_name)
                            fallen_gif, fallen_mp4 = create_country_fallen_media(loser_name, winner_name, audio_bytes=fallen_speech)
                            fallen_desc = (
                                f"🏚️ **Fallen Nation:** {loser_flag} **{loser_name}**\n"
                                f"👑 **Conquering Empire:** {winner_flag} **{winner_name}**\n"
                                f"🌐 **Sovereign Status:** Annexed! National sovereignty extinguished and integrated into imperial dominion."
                            )
                            await self.broadcast_news(
                                title="⚠️ SOVEREIGN STATE FALLEN // ANNEXATION COMPLETE",
                                description=fallen_desc,
                                gif_bytes=fallen_gif,
                                filename="country_fallen.gif",
                                color=0xDC2626,
                                speech_bytes=fallen_speech,
                                video_bytes=fallen_mp4
                            )
        except Exception as e:
            print(f"⚠️ Error checking concluded earth wars: {e}", flush=True)

    earth_group = app_commands.Group(name="earth", description="🌍 Virtual Earth: Global Geopolitics Simulation")
    cabinet_group = app_commands.Group(name="cabinet", parent=earth_group, description="🏛️ Sovereign Cabinet & Ministers")
    # Discord allows at most 25 direct child commands per slash-command group.
    # Keep UN, security, and broadcast actions under subgroups so all Earth commands register cleanly within Discord's 25-child limit.
    un_group = app_commands.Group(name="un", parent=earth_group, description="🇺🇳 United Nations peacekeeping actions")
    security_group = app_commands.Group(name="security", parent=earth_group, description="🛡️ Counter-intelligence and detainee operations")
    broadcast_group = app_commands.Group(name="broadcast", parent=earth_group, description="📢 Official Sovereign Broadcasts & News Media")

    # ─── Country Overview ─────────────────────────────────────────────────────

    @earth_group.command(name="view", description="View sovereign dossier and status of an Earth nation.")
    @app_commands.describe(country="3-letter country code or name (e.g. RUS, IND, USA)")
    async def earth_view(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer()
        code = country.strip().upper()
        c = await self.bot.db.get_earth_country_by_code(code)
        if not c:
            # Try searching by name substring
            countries = await self.bot.db.get_earth_countries()
            for cand in countries:
                if country.lower() in cand["name"].lower():
                    c = await self.bot.db.get_earth_country(cand["id"])
                    break

        if not c:
            await interaction.followup.send(f"❌ Sovereign country `{country}` not found. Try codes like `RUS`, `IND`, `USA`, `CHN`, `GBR`, `DEU`, etc.")
            return

        leader_str = f"<@{c['owner_id']}>" if c.get("owner_id") else "🏛️ *Sovereign State Trust (Unclaimed)*"
        stability = c.get("stability", 80)
        unrest = c.get("unrest", 10)
        stab_bar = "🟩" * (stability // 10) + "⬛" * (10 - (stability // 10))
        unrest_bar = "🟥" * (unrest // 10) + "⬛" * (10 - (unrest // 10))

        riot_alert = ""
        if unrest >= 85:
            riot_alert = "\n🔥 **IMMINENT REVOLUTION RISK!** Unrest >= 85% — Citizens are storming the palace!"
        elif unrest >= 60:
            riot_alert = "\n🔥 **ACTIVE RIOTS!** City violence is halving national economic production!"

        embed = discord.Embed(
            title=f"{c['flag']} {c['name']} ({c['code']})",
            description=f"{c.get('desc', '')}\n\n**Capital:** `{c.get('capital', 'N/A')}` | **Maritime Coast:** `{'Yes (Ocean Access)' if c.get('is_coastal') else 'No (Landlocked)'}`{riot_alert}",
            color=0x3B82F6
        )

        embed.add_field(name="👑 Sovereign Ruler", value=leader_str, inline=True)
        embed.add_field(name="💰 GDP Valuation", value=f"`{c.get('gdp', 0):,} Medals`", inline=True)
        embed.add_field(name="🏦 State Treasury", value=f"`{c.get('treasury', 0):,} Medals`", inline=True)

        embed.add_field(name=f"🛡️ National Stability ({stability}%)", value=stab_bar, inline=True)
        embed.add_field(name=f"⚡ Civil Unrest ({unrest}%)", value=unrest_bar, inline=True)
        embed.add_field(name="🤝 Global Alliance", value=f"`{c.get('alliance_name') or 'Non-Aligned'}`", inline=True)

        # Cabinet summary
        cab = c.get("cabinet", {})
        cab_lines = []
        for rk, rm in EARTH_CABINET_ROLES.items():
            cab_info = cab.get(rk, {})
            u_id = cab_info.get("user_id")
            val = f"<@{u_id}>" if u_id else "*Vacant*"
            cab_lines.append(f"• **{rm['emoji']} {rm['short_title']}:** {val}")
        embed.add_field(name="🏛️ Sovereign Cabinet", value="\n".join(cab_lines), inline=False)

        # Buildings count
        b_count = len(c.get("buildings", []))
        tr_count = len(c.get("trade_routes", []))
        embed.add_field(name="🏗️ Infrastructure & Trade", value=f"• **Buildings:** `{b_count}` operational facilities\n• **Ocean Trade Routes:** `{tr_count}` active sealanes", inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🌍 View on 3D Earth Globe", url=WEB_URL, style=discord.ButtonStyle.link))

        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="my_country", description="View your governed country and ministerial duties.")
    async def earth_my_country(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"You do not currently lead an Earth nation or hold a cabinet ministry. Visit the [3D Virtual Earth Globe]({WEB_URL}) to acquire sovereign territory or get appointed by a President!",
                ephemeral=True
            )
            return

        role_title = c.get("role_title", "Leader")
        embed = discord.Embed(
            title=f"🌍 Your Sovereign State: {c['flag']} {c['name']}",
            description=f"**Your Portfolio:** `{role_title}`\n\n**Stability:** `{c.get('stability', 80)}%` | **Unrest:** `{c.get('unrest', 10)}%`\n**National Treasury:** `{c.get('treasury', 0):,} Medals`",
            color=0x22C55E
        )

        # Buildings summary
        b_lines = [f"{b['emoji']} **{b['name']}**: Lvl {b['level']}" for b in c.get("buildings", [])[:6]]
        if b_lines:
            embed.add_field(name="🏗️ Domestic Infrastructure", value="\n".join(b_lines), inline=False)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🌍 Open 3D Virtual Earth Console", url=WEB_URL, style=discord.ButtonStyle.link))
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ─── Ministerial Dashboards ───────────────────────────────────────────────

    @earth_group.command(name="defense", description="⚔️ Ministry of Defense & Supreme Army Command Dashboard")
    async def earth_defense(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"❌ You do not currently lead an Earth nation or hold a cabinet ministry. Visit the [3D Virtual Earth Globe]({WEB_URL}) to acquire sovereign territory or get appointed by a President!",
                ephemeral=True
            )
            return

        embed = await build_defense_embed(self.bot, c, interaction.user.id)
        view = DefenseDashboardView(self.bot, c, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="economy", description="🏦 Ministry of Economy & National Treasury Dashboard")
    async def earth_economy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"❌ You do not currently lead an Earth nation or hold a cabinet ministry. Visit the [3D Virtual Earth Globe]({WEB_URL}) to acquire sovereign territory!",
                ephemeral=True
            )
            return

        embed = await build_economy_embed(self.bot, c, interaction.user.id)
        view = EconomyDashboardView(self.bot, c, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="diplomacy", description="📜 Ministry of Foreign Affairs & Diplomatic Corps Dashboard")
    async def earth_diplomacy(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"❌ You do not currently lead an Earth nation or hold a cabinet ministry. Visit the [3D Virtual Earth Globe]({WEB_URL}) to acquire sovereign territory!",
                ephemeral=True
            )
            return

        embed = await build_diplomacy_embed(self.bot, c, interaction.user.id)
        view = DiplomacyDashboardView(self.bot, c, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="intelligence", description="🕵️ Directorate of Secret Intelligence & Espionage Dashboard")
    async def earth_intelligence(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"❌ You do not currently lead an Earth nation or hold a cabinet ministry. Visit the [3D Virtual Earth Globe]({WEB_URL}) to acquire sovereign territory!",
                ephemeral=True
            )
            return

        embed = await build_intelligence_embed(self.bot, c, interaction.user.id)
        view = IntelligenceDashboardView(self.bot, c, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="president", description="👑 Presidential High Command & Imperial Sovereign Dashboard")
    async def earth_president(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"❌ You do not currently lead an Earth nation. Visit the [3D Virtual Earth Globe]({WEB_URL}) to claim or buy an available sovereign state!",
                ephemeral=True
            )
            return

        embed = await build_president_embed(self.bot, c, interaction.user.id)
        view = PresidentDashboardView(self.bot, c, interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="ministry", description="🏛️ Sovereign Ministry Hub — Switch between Cabinet Portfolios")
    @app_commands.describe(department="Optional ministerial portfolio to open directly")
    @app_commands.choices(department=[
        app_commands.Choice(name="⚔️ Ministry of Defense (Army Commander)", value="defense"),
        app_commands.Choice(name="🏦 Ministry of Economy (Finance Minister)", value="economy"),
        app_commands.Choice(name="📜 Ministry of Foreign Affairs (Chief Diplomat)", value="diplomat"),
        app_commands.Choice(name="🕵️ Directorate of Intelligence (Spy Chief)", value="intelligence"),
        app_commands.Choice(name="👑 Presidential High Command (Sovereign)", value="president"),
    ])
    async def earth_ministry(self, interaction: discord.Interaction, department: app_commands.Choice[str] = None):
        if department:
            dep_val = department.value
            if dep_val == "defense":
                await self.earth_defense(interaction)
            elif dep_val == "economy":
                await self.earth_economy(interaction)
            elif dep_val == "diplomat":
                await self.earth_diplomacy(interaction)
            elif dep_val == "intelligence":
                await self.earth_intelligence(interaction)
            elif dep_val == "president":
                await self.earth_president(interaction)
            return

        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send(
                f"❌ You do not currently lead an Earth nation or hold a cabinet ministry. Visit the [3D Virtual Earth Globe]({WEB_URL}) to acquire sovereign territory!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🏛️ Sovereign Ministry Hub: {c['flag']} {c['name']} ({c['code']})",
            description=(
                f"**Your Governed Portfolio:** `{c.get('role_title', 'Citizen')}`\n"
                f"**National Treasury:** `{c.get('treasury', 0):,} Medals` | **GDP:** `{c.get('gdp', 0):,} Medals`\n"
                f"**Stability:** `{c.get('stability', 80)}%` | **Unrest:** `{c.get('unrest', 10)}%`\n\n"
                f"Use the interactive dropdown below to access your department dashboard directly."
            ),
            color=0x3B82F6
        )
        hub_view = MinistryHubView(self.bot, c, interaction.user.id)
        await interaction.followup.send(embed=embed, view=hub_view)

    # ─── Cabinet Appointments ─────────────────────────────────────────────────

    @cabinet_group.command(name="appoint", description="Appoint a fellow server member to your ministerial cabinet.")
    @app_commands.describe(
        role="Cabinet Portfolio",
        member="Discord member to appoint"
    )
    @app_commands.choices(role=[
        app_commands.Choice(name="⚔️ Minister of Defense (Army Commander)", value="defense"),
        app_commands.Choice(name="📜 Chief Diplomat (Foreign Affairs)", value="diplomat"),
        app_commands.Choice(name="🏦 Minister of Economy (Treasury & Building)", value="economy"),
        app_commands.Choice(name="🕵️ Director of Secret Intelligence (Spy Chief)", value="intelligence"),
    ])
    async def cabinet_appoint(self, interaction: discord.Interaction, role: app_commands.Choice[str], member: discord.Member):
        await interaction.response.defer()
        # Find country owned by interaction.user
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c or c.get("user_role") != "president":
            await interaction.followup.send("❌ Only the President/PM of a sovereign nation can issue Cabinet appointments!", ephemeral=True)
            return

        success, msg, data = await self.bot.db.appoint_earth_cabinet(interaction.user.id, c["id"], role.value, member.id)
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        if data.get("auto_accepted"):
            embed = discord.Embed(
                title="🏛️ Executive Portfolio Assumed",
                description=f"**President <@{interaction.user.id}>** has taken direct charge of **{role.name}** for **{c['flag']} {c['name']}**.",
                color=0xF1C40F
            )
            embed.set_footer(text="Virtual Earth Cabinet • Sitting President exercised sovereign authority.")
            await interaction.followup.send(embed=embed)
            if role.value == "defense":
                await self.broadcast_commander_news(c["name"], c["flag"], interaction.user.display_name)
            return

        # Nomination decree pending candidate acceptance
        view = CabinetInviteView(
            bot=self.bot,
            invite_id=data["invite_id"],
            target_user_id=member.id,
            president_id=interaction.user.id,
            role_title=data.get("role_title", role.name),
            country_name=c["name"],
            country_flag=c["flag"]
        )
        embed = discord.Embed(
            title="📜 Presidential Cabinet Decree Issued",
            description=(
                f"**President <@{interaction.user.id}>** has appointed **<@{member.id}>** to the national cabinet!\n\n"
                f"**Portfolio:** {role.name}\n"
                f"**Sovereign Nation:** {c['flag']} {c['name']}\n\n"
                f"⚠️ **Nominee Action Required:** <@{member.id}> must click **[Accept Appointment]** below or run `/earth cabinet accept` to assume office."
            ),
            color=0xF1C40F
        )
        embed.set_footer(text="Virtual Earth Cabinet • Ministers exercise portfolio authority alongside the President.")
        await interaction.followup.send(content=f"<@{member.id}>", embed=embed, view=view)

    @cabinet_group.command(name="dismiss", description="Dismiss a minister from your cabinet.")
    @app_commands.describe(role="Cabinet Portfolio to vacate")
    @app_commands.choices(role=[
        app_commands.Choice(name="⚔️ Minister of Defense", value="defense"),
        app_commands.Choice(name="📜 Chief Diplomat", value="diplomat"),
        app_commands.Choice(name="🏦 Minister of Economy", value="economy"),
        app_commands.Choice(name="🕵️ Director of Intelligence", value="intelligence"),
    ])
    async def cabinet_dismiss(self, interaction: discord.Interaction, role: app_commands.Choice[str]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c or c.get("user_role") != "president":
            await interaction.followup.send("❌ Only the President can dismiss Cabinet ministers!", ephemeral=True)
            return

        success, msg = await self.bot.db.dismiss_earth_cabinet(interaction.user.id, c["id"], role.value)
        await interaction.followup.send(f"🏛️ {msg}" if success else f"❌ {msg}")

    @cabinet_group.command(name="accept", description="Accept a pending appointment decree to a ministerial cabinet.")
    async def cabinet_accept(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        invites = await self.bot.db.get_user_pending_cabinet_invites(interaction.user.id)
        if not invites:
            await interaction.followup.send("❌ You do not have any pending cabinet appointment decrees awaiting your acceptance.", ephemeral=True)
            return
        inv = invites[0]
        success, msg = await self.bot.db.respond_earth_cabinet_invite(interaction.user.id, inv["id"], accept=True)
        if success:
            embed = discord.Embed(
                title="🎉 Oath of Office Sworn",
                description=f"You have officially assumed office as **{inv['role_emoji']} {inv['role_title']}** of **{inv['country_flag']} {inv['country_name']}**!\n\nYou now share executive ministerial authority with the President.",
                color=0x2ECC71
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            if inv.get("role") == "defense" or "commander" in str(inv.get("role_title", "")).lower():
                await self.broadcast_commander_news(inv["country_name"], inv["country_flag"], interaction.user.display_name)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    @cabinet_group.command(name="decline", description="Decline a pending appointment decree to a ministerial cabinet.")
    async def cabinet_decline(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        invites = await self.bot.db.get_user_pending_cabinet_invites(interaction.user.id)
        if not invites:
            await interaction.followup.send("❌ You do not have any pending cabinet appointment decrees.", ephemeral=True)
            return
        inv = invites[0]
        success, msg = await self.bot.db.respond_earth_cabinet_invite(interaction.user.id, inv["id"], accept=False)
        await interaction.followup.send(f"🏛️ {msg}", ephemeral=True)

    @cabinet_group.command(name="pending", description="View pending ministerial cabinet appointments offered to you.")
    async def cabinet_pending(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        invites = await self.bot.db.get_user_pending_cabinet_invites(interaction.user.id)
        if not invites:
            await interaction.followup.send("📜 You have no pending cabinet appointments awaiting your acceptance.", ephemeral=True)
            return
        lines = []
        for inv in invites:
            lines.append(f"• **{inv['role_emoji']} {inv['role_title']}** — {inv['country_flag']} **{inv['country_name']}** (Appointed by <@{inv['president_id']}>)")
        embed = discord.Embed(
            title="📜 Pending Cabinet Decrees",
            description="\n\n".join(lines) + "\n\nUse `/earth cabinet accept` to take office or `/earth cabinet decline` to refuse.",
            color=0xF1C40F
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @cabinet_group.command(name="resign", description="Resign from your current ministerial cabinet portfolio.")
    async def cabinet_resign(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.resign_earth_cabinet(interaction.user.id)
        await interaction.followup.send(f"🏛️ {msg}" if success else f"❌ {msg}", ephemeral=True)

    # ─── Infrastructure Construction ──────────────────────────────────────────

    @earth_group.command(name="build", description="Construct or upgrade realistic domestic infrastructure in your nation.")
    @app_commands.describe(building="Infrastructure type to construct or upgrade")
    @app_commands.choices(building=[
        app_commands.Choice(name="🏫 Public School & University (+Stability, +GDP)", value="school"),
        app_commands.Choice(name="🏥 Regional Hospital Complex (-Unrest, Quells Riots)", value="hospital"),
        app_commands.Choice(name="⛏️ Sovereign Gold Mine (+Hourly Medals Yield)", value="gold_mine"),
        app_commands.Choice(name="🛢️ Offshore & Inland Petroleum Rig (+High Yield)", value="oil_rig"),
        app_commands.Choice(name="🏭 Heavy Industrial Complex (+Military Power)", value="heavy_factory"),
        app_commands.Choice(name="🏰 Fortified Citadel Bunker (+Massive Defense)", value="bunker"),
        app_commands.Choice(name="⚓ Deepwater Commercial & Naval Port (Enables Ocean Trade)", value="naval_port"),
        app_commands.Choice(name="🛟 Offshore Sovereign Ocean Base (+Defense & GDP)", value="ocean_base"),
    ])
    @app_commands.describe(country_code="Optional code of a country/state you rule, including a conquered state")
    async def earth_build(self, interaction: discord.Interaction, building: app_commands.Choice[str], country_code: str = None):
        await interaction.response.defer()
        if country_code:
            c = await self.bot.db.get_earth_country_by_code(country_code.strip().upper())
        else:
            c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ Country/state not found. Use /earth my_country to see your current nation.", ephemeral=True)
            return

        success, msg, cost = await self.bot.db.build_earth_infrastructure(interaction.user.id, c["id"], building.value)
        if success:
            embed = discord.Embed(
                title="🏗️ Infrastructure Project Commissioned",
                description=f"**{c['flag']} {c['name']}** has upgraded **{building.name}**!\n\n• **Expenditure:** `-{cost:,} Medals`\n• {msg}",
                color=0x22C55E
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── Espionage & Intelligence ─────────────────────────────────────────────

    @earth_group.command(name="spy", description="Dispatch a covert operative on an espionage mission against a foreign nation.")
    @app_commands.describe(
        target_country="Target country code (e.g. USA, CHN, RUS)",
        mission="Espionage mission objective"
    )
    @app_commands.choices(mission=[
        app_commands.Choice(name="🛰️ Infiltrate & Gather Intelligence Dossier", value="intel"),
        app_commands.Choice(name="💣 Covert Infrastructure Sabotage (Disable Mine/Rig)", value="sabotage"),
        app_commands.Choice(name="🔥 Fund Dissidents & Incite Limited Unrest (+8 max)", value="incite_riot"),
    ])
    async def earth_spy(self, interaction: discord.Interaction, target_country: str, mission: app_commands.Choice[str]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ You must govern a sovereign nation or be Spy Chief to dispatch operatives!", ephemeral=True)
            return

        tgt = await self.bot.db.get_earth_country_by_code(target_country.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Target country `{target_country}` not found.")
            return

        # Check spies
        spies = await self.bot.db.get_earth_spies(c["id"])
        idle_spies = [s for s in spies if s.get("status") == "idle"]
        if not idle_spies:
            await interaction.followup.send("❌ No idle field operatives available! Recruit an operative first on the web console or recruit one.")
            return

        spy = idle_spies[0]
        success, msg, m_data = await self.bot.db.dispatch_earth_spy(interaction.user.id, c["id"], spy["id"], tgt["id"], mission.value)

        if success:
            embed = discord.Embed(
                title="🕵️ Field Operation Underway",
                description=f"**Agent '{spy['codename']}'** is conducting a timed operation inside **{tgt['flag']} {tgt['name']}**.\n\n{msg}",
                color=0x3B82F6
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="⛔ ESPIONAGE ORDER REJECTED",
                description=f"{msg}",
                color=0xEF4444
            )
            await interaction.followup.send(embed=embed)

    # ─── Multi-Day Military Conquest ──────────────────────────────────────────

    @earth_group.command(name="war", description="Declare a strategic multi-day military conquest campaign (1 to 5 Days).")
    @app_commands.describe(
        target_country="Target country code (e.g. USA, CHN, RUS)",
        scale="Scale and duration of conquest campaign"
    )
    @app_commands.choices(scale=[
        app_commands.Choice(name="⚔️ Border Skirmish (1 Day / 24 Hours)", value="border"),
        app_commands.Choice(name="🚩 Strategic Annexation Campaign (3 Days / 72 Hours)", value="annexation"),
        app_commands.Choice(name="💥 Total Sovereign Conquest (5 Days / 120 Hours)", value="world_war"),
    ])
    async def earth_war(self, interaction: discord.Interaction, target_country: str, scale: app_commands.Choice[str]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ Only a sovereign leader or Minister of Defense can declare military conquests!", ephemeral=True)
            return

        tgt = await self.bot.db.get_earth_country_by_code(target_country.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Target country `{target_country}` not found.")
            return

        success, msg, war_data = await self.bot.db.declare_earth_war(interaction.user.id, c["id"], tgt["id"], scale.value)
        if success:
            war_id = war_data.get("war_id") or 0
            war_speech_buf = generate_war_speech(c["name"], tgt["name"], scale.name)
            gif, mp4_buf = create_war_declared_media(c["name"], tgt["name"], scale.name, "land", audio_bytes=war_speech_buf)

            embed = discord.Embed(
                title="🚨 DECLARATION OF SOVEREIGN WAR",
                description=f"**{c['flag']} {c['name']}** has officially declared war on **{tgt['flag']} {tgt['name']}**!\n\n"
                            f"🌐 **Campaign Scale:** {scale.name}\n"
                            f"⏳ **Duration:** `{war_data.get('duration_hours')} Hours`\n"
                            f"⚔️ **Front Line Active:** Armored divisions clashing along the border! Follow the front on the 3D globe.",
                color=0xDC2626
            )
            view = WarSurrenderView(
                self.bot, war_id,
                c["id"], c.get("owner_id"), c["name"], c["flag"],
                tgt["id"], tgt.get("owner_id"), tgt["name"], tgt["flag"]
            )
            files = []
            if mp4_buf:
                mp4_buf.seek(0)
                files.append(discord.File(mp4_buf, filename="war_declared.mp4"))
                embed.set_footer(text="Virtual Earth 3D Geopolitics • Deep Voice Video Player Attached 🎬🎙️")
            else:
                gif.seek(0)
                files.append(discord.File(gif, filename="war_declared.gif"))
                embed.set_image(url="attachment://war_declared.gif")
                if war_speech_buf:
                    war_speech_buf.seek(0)
                    files.append(discord.File(war_speech_buf, filename="voice_announcement.mp3"))
                embed.set_footer(text="Virtual Earth 3D Geopolitics • Voice Narration Attached 🎙️")

            await interaction.followup.send(embed=embed, view=view, files=files)

            await self.broadcast_war_declared(
                attacker_c=c,
                defender_c=tgt,
                scale_name=scale.name,
                duration_hours=war_data.get('duration_hours', 24),
                war_id=war_id,
                domain="land",
                aggressor_mention=interaction.user.mention
            )
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── Quell Unrest & Riots ─────────────────────────────────────────────────

    @earth_group.command(name="quell", description="Deploy resources to quell civil unrest and suppress riots.")
    @app_commands.describe(method="Pacification strategy")
    @app_commands.choices(method=[
        app_commands.Choice(name="🪖 Deploy Military / Martial Law (50k M + 2 Divs: -45% Unrest, -12% Stability)", value="military"),
        app_commands.Choice(name="🏥 Emergency Civilian Stimulus (150k M: -25% Unrest, +15% Stability)", value="relief"),
        app_commands.Choice(name="🛡️ Tactical Police Suppression (80k M: -35% Unrest, -8% Liberty)", value="police"),
        app_commands.Choice(name="🎉 Sovereign Jubilee (60k M: -15% Unrest, +20% Stability)", value="festival"),
    ])
    async def earth_quell(self, interaction: discord.Interaction, method: app_commands.Choice[str]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ You do not govern an Earth nation!", ephemeral=True)
            return

        success, msg = await self.bot.db.quell_earth_unrest(interaction.user.id, c["id"], method.value)
        if success:
            await interaction.followup.send(msg)
            if method.value in ("military", "martial_law"):
                try:
                    await self.broadcast_news(
                        title="🪖 STATE OF EMERGENCY // MARTIAL LAW ENFORCED",
                        description=(
                            f"🚨 **National Emergency:** {c.get('flag', '🏳️')} **{c.get('name', 'Nation')}** has mobilized armed military divisions to quell severe street riots and enforce strict emergency curfews!\n\n"
                            f"🕊️ Armed patrols deployed across major city centres. Civilians instructed to remain indoors."
                        ),
                        color=0xDC2626
                    )
                except Exception as b_err:
                    print(f"⚠️ Failed to broadcast martial law: {b_err}", flush=True)
        else:
            await interaction.followup.send(f"❌ {msg}")

    @earth_group.command(name="martial_law", description="Mobilize armed military divisions to impose emergency curfews and crush civil unrest.")
    async def earth_martial_law(self, interaction: discord.Interaction):
        """Deploy armed military divisions to enforce state emergency curfews and crush riots."""
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ You do not govern an Earth nation!", ephemeral=True)
            return

        success, msg = await self.bot.db.quell_earth_unrest(interaction.user.id, c["id"], "military")
        if success:
            await interaction.followup.send(msg)
            try:
                await self.broadcast_news(
                    title="🪖 STATE OF EMERGENCY // MARTIAL LAW ENFORCED",
                    description=(
                        f"🚨 **National Emergency:** {c.get('flag', '🏳️')} **{c.get('name', 'Nation')}** has mobilized armed military divisions to quell severe street riots and enforce strict emergency curfews!\n\n"
                        f"🕊️ Armed patrols deployed across major city centres. Civilians instructed to remain indoors."
                    ),
                    color=0xDC2626
                )
            except Exception as b_err:
                print(f"⚠️ Failed to broadcast martial law: {b_err}", flush=True)
        else:
            await interaction.followup.send(f"❌ {msg}")


    # ??? Custom Country Creation & Unowned Nation Claims ?????????????????????????

    @earth_group.command(name="claim", description="Claim an unowned country from the State Trust for any medal offer (0-inf, 0% tax).")
    @app_commands.describe(
        country="3-letter code or country name",
        offer="Medals offered to acquire sovereignty (0 to inf, no tax applied)"
    )
    async def earth_claim(
        self,
        interaction: discord.Interaction,
        country: str,
        offer: int = 0
    ):
        await interaction.response.defer()
        code = country.strip().upper()
        c = await self.bot.db.get_earth_country_by_code(code)
        if not c:
            countries = await self.bot.db.get_earth_countries()
            for cand in countries:
                if country.lower() in cand["name"].lower():
                    c = await self.bot.db.get_earth_country(cand["id"])
                    break

        if not c:
            await interaction.followup.send(f"? Sovereign country `{country}` not found.")
            return

        if c.get("owner_id"):
            await interaction.followup.send(f"? {c['flag']} **{c['name']}** is already governed by <@{c['owner_id']}>! Use the website to submit a diplomatic buyout offer.")
            return

        success, msg = await self.bot.db.buy_earth_country(interaction.user.id, c["id"], offer=offer)
        if not success:
            await interaction.followup.send(f"? {msg}")
            return

        desc_claim = (
            f"President: {interaction.user.mention}\n"
            f"Medals Offered: **{max(0, offer):,} Medals**\n"
            f"Treaty Tax: **0% (Free of tax)**\n\n"
            f"{msg}"
        )

        gif = create_new_ruler_gif(c["name"], c["flag"], interaction.user.display_name)
        speech_buf = generate_ruler_speech(c["name"], interaction.user.display_name)
        embed = discord.Embed(
            title=f"👑 Sovereignty Acquired: {c['flag']} {c['name']}",
            description=desc_claim,
            color=0x10B981
        )
        gif.seek(0)
        speech_buf.seek(0)
        files = [
            discord.File(gif, filename="new_ruler.gif"),
            discord.File(speech_buf, filename="voice_announcement.mp3")
        ]
        embed.set_image(url="attachment://new_ruler.gif")
        embed.set_footer(text="Virtual Earth 3D Geopolitics • Spoken Narration Attached 🎙️")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open 3D Command Deck", url=WEB_URL, style=discord.ButtonStyle.link, emoji="🏛️"))
        await interaction.followup.send(embed=embed, view=view, files=files)

        news_gif = create_new_ruler_gif(c["name"], c["flag"], interaction.user.display_name)
        news_speech = generate_ruler_speech(c["name"], interaction.user.display_name)
        news_desc = (
            f"🏛️ **Sovereign Nation:** {c['flag']} **{c['name']}**\n"
            f"👑 **Supreme Sovereign / President:** {interaction.user.mention} (`{interaction.user.display_name}`)\n"
            f"💰 **Treasury & Starting Reserves:** In full sovereign control\n\n"
            f"🌐 A new era begins! Citizens and foreign allies can pledge allegiance or propose ocean trade lanes."
        )
        await self.broadcast_news(
            title="👑 NEW SUPREME RULER INAUGURATED // SOVEREIGNTY ASSUMED",
            description=news_desc,
            gif_bytes=news_gif,
            filename="ruler_news.gif",
            color=0xF59E0B,
            speech_bytes=news_speech
        )


    # ??? Citizenship, Allegiance & Counter-Intelligence ??????????????????????????

    @earth_group.command(name="join", description="Pledge allegiance to an existing sovereign country as a citizen.")
    @app_commands.describe(country="3-letter country code or name (e.g. RUS, IND, USA)")
    async def earth_join(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer()
        code = country.strip().upper()
        c = await self.bot.db.get_earth_country_by_code(code)
        if not c:
            countries = await self.bot.db.get_earth_countries()
            for cand in countries:
                if country.lower() in cand["name"].lower():
                    c = await self.bot.db.get_earth_country(cand["id"])
                    break

        if not c:
            await interaction.followup.send(f"? Country `{country}` not found.")
            return

        success, msg = await self.bot.db.join_earth_country(interaction.user.id, c["id"])
        if not success:
            await interaction.followup.send(f"? {msg}")
            return

        embed = discord.Embed(
            title=f"??? Allegiance Pledged: {c['flag']} {c['name']}",
            description=(
                f"{interaction.user.mention} has officially joined **{c['name']}** as a registered citizen!\n\n"
                f"? **National GDP:** {c['gdp']:,} Medals\n"
                f"? **Ruler:** <@{c['owner_id']}>\n"
                f"? **Career:** Eligible for Presidential appointment as Prime Minister, Defense General, Diplomat, or Economy Director."
            ),
            color=0x3B82F6
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open 3D Realm Console", url=WEB_URL, style=discord.ButtonStyle.link, emoji="??"))
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="leave", description="Renounce your citizenship and become a stateless free agent.")
    async def earth_leave(self, interaction: discord.Interaction):
        await interaction.response.defer()
        success, msg = await self.bot.db.leave_earth_country(interaction.user.id)
        await interaction.followup.send(f"{msg}" if success else f"? {msg}")

    @earth_group.command(name="citizens", description="View all registered citizens of a sovereign country.")
    @app_commands.describe(country="3-letter code or country name (defaults to your country)")
    async def earth_citizens(self, interaction: discord.Interaction, country: str = None):
        await interaction.response.defer()
        if country:
            code = country.strip().upper()
            c = await self.bot.db.get_earth_country_by_code(code)
            if not c:
                countries = await self.bot.db.get_earth_countries()
                for cand in countries:
                    if country.lower() in cand["name"].lower():
                        c = await self.bot.db.get_earth_country(cand["id"])
                        break
        else:
            c = await self.bot.db.get_user_earth_country(interaction.user.id)

        if not c:
            await interaction.followup.send("? Sovereign country not found or you have not joined a realm!")
            return

        citizens = await self.bot.db.get_earth_country_citizens(c["id"])
        embed = discord.Embed(
            title=f"??? Citizens & Patriots of {c['flag']} {c['name']}",
            description=f"Total Registered Citizens: **{len(citizens)}**",
            color=0x38BDF8
        )
        if citizens:
            lines = []
            for cz in citizens[:15]:
                role_badge = f" ? *{cz['cabinet_role'].title()}*" if cz.get("cabinet_role") else ""
                lines.append(f"? <@{cz['user_id']}> ({cz['username']}){role_badge}")
            embed.add_field(name="Citizen Roster", value="\n".join(lines), inline=False)
        else:
            embed.description += "\n\n*No citizens registered yet. Other players can use `/earth join` or the website to enlist.*"

        await interaction.followup.send(embed=embed)

    @security_group.command(name="sweep", description="Run a Counter-Intelligence Security Sweep to detect spies and review detained operatives.")
    async def earth_sweep(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("? You do not govern an Earth nation!", ephemeral=True)
            return

        success, msg, report = await self.bot.db.counter_intel_sweep(interaction.user.id, c["id"])
        if not success:
            await interaction.followup.send(f"? {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"??? Counter-Intelligence Security Report: {c['flag']} {c['name']}",
            description=(
                f"? **Counter-Intel Detection Grid:** `{report['counter_intel_rating']}`\n"
                f"? **Bunker Fortifications:** `{report['bunkers_count']} Installations` (+3% spy catch risk per level)\n"
                f"? **Detained Hostile Operatives:** `{report['detained_spies_count']} In Custody`\n\n"
                f"{msg}"
            ),
            color=0x10B981
        )
        detained = report.get("detained_spies", [])
        if detained:
            lines = [f"? **Agent {s['codename']}** (From {s['origin_country_flag']} {s['origin_country_name']}) ? ID: `{s['id']}`" for s in detained[:5]]
            embed.add_field(name="Detained Prisoners of War", value="\n".join(lines) + "\n*Use `/earth security interrogate <id>` or the website to question them.*", inline=False)

        await interaction.followup.send(embed=embed)

    @security_group.command(name="interrogate", description="Interrogate a captured foreign spy held in military custody.")
    @app_commands.describe(spy_id="ID of the captured foreign agent")
    async def earth_interrogate(self, interaction: discord.Interaction, spy_id: int):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("? You do not govern an Earth nation!", ephemeral=True)
            return

        success, msg, intel = await self.bot.db.interrogate_captured_spy(interaction.user.id, c["id"], spy_id)
        if not success:
            await interaction.followup.send(f"? {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"??? Interrogation Record: Confession Extracted",
            description=(
                f"? **Operative Codename:** `{intel['codename']}`\n"
                f"? **Sponsoring Nation:** {intel['origin_flag']} **{intel['origin_country']}**\n"
                f"? **Enemy Treasury Intercepted:** `{intel['origin_treasury']:,} Medals`\n"
                f"? **Enemy GDP:** `{intel['origin_gdp']:,} Medals`\n\n"
                f"? Confession logged! Your nation's stability increased by +5%."
            ),
            color=0xF59E0B
        )
        await interaction.followup.send(embed=embed)

    @security_group.command(name="execute", description="Execute a convicted foreign spy held in custody.")
    @app_commands.describe(spy_id="ID of the captured foreign agent")
    async def earth_execute(self, interaction: discord.Interaction, spy_id: int):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("? You do not govern an Earth nation!", ephemeral=True)
            return

        success, msg = await self.bot.db.execute_captured_spy(interaction.user.id, c["id"], spy_id)
        await interaction.followup.send(f"{msg}" if success else f"? {msg}")


    # ??? Advanced Military Tools & High-Tech Arsenal ?????????????????????????????

    @earth_group.command(name="arsenal", description="View advanced high-tech tools, missile shields, drone swarms, and superweapons.")
    async def earth_arsenal(self, interaction: discord.Interaction):
        await interaction.response.defer()
        from utils.constants import EARTH_ADVANCED_TOOLS
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        country_id = c["id"] if c else 0

        owned_tools = await self.bot.db.get_country_tools(country_id) if country_id else []
        owned_keys = {t["tool_key"] for t in owned_tools}

        embed = discord.Embed(
            title="?? Advanced Military Arsenal & Strategic Defense Suite",
            description=(
                "Nations grow slowly and naturally over time, or you can **procure Advanced Tools with Medals** "
                "to fast-track military power, ballistic interception, and economic yields!\n\n"
                "*Use `/earth buy_tool <tool_key>` or the website command deck to procure assets.*"
            ),
            color=0xF59E0B
        )

        for key, tool in EARTH_ADVANCED_TOOLS.items():
            status = "? **DEPLOYED**" if key in owned_keys else f"?? **{tool['price']:,} Medals**"
            stats = f"?? +{tool['military_power']} Atk ? ??? +{tool['defense_power']} Def"
            if tool.get("hourly_yield"):
                stats += f" ? ?? +{tool['hourly_yield']:,} M/hr"
            embed.add_field(
                name=f"{tool['emoji']} {tool['name']} (`{key}`)",
                value=f"? **Status:** {status}\n? **Combat:** {stats}\n? **Perk:** *{tool['perk']}*\n? *{tool['desc']}*",
                inline=False
            )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open 3D High-Tech Deck", url=WEB_URL, style=discord.ButtonStyle.link, emoji="??"))
        await interaction.followup.send(embed=embed, view=view)

    @earth_group.command(name="buy_tool", description="Procure an advanced military tool, missile defense shield, or drone swarm with Medals.")
    @app_commands.describe(tool_key="Asset key (e.g. drone_swarm, iron_dome, hypersonic_battery, tactical_nuke, sat_recon)")
    async def earth_buy_tool(self, interaction: discord.Interaction, tool_key: str):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("? You do not govern an Earth nation! Claim an empty country for free or found a custom nation first.", ephemeral=True)
            return

        key = tool_key.strip().lower()
        success, msg, res = await self.bot.db.buy_country_tool(interaction.user.id, c["id"], key)
        if not success:
            await interaction.followup.send(f"? {msg}", ephemeral=True)
            return

        tool = res["tool"]
        embed = discord.Embed(
            title=f"?? Advanced Asset Deployed: {tool['emoji']} {tool['name']}",
            description=(
                f"Supreme Sovereign: {interaction.user.mention}\n"
                f"Host Nation: **{c['flag']} {c['name']}**\n"
                f"Procurement Cost: **{tool['price']:,} Medals**\n\n"
                f"? **Military Attack Boost:** `+{tool['military_power']}`\n"
                f"? **National Defense Boost:** `+{tool['defense_power']}`\n"
                f"? **Special Capability:** *{tool['perk']}*\n\n"
                f"{msg}"
            ),
            color=0x10B981
        )
        embed.set_footer(text="Virtual Earth 3D Simulation ? High-Tech Warfare Suite")
        await interaction.followup.send(embed=embed)


    @security_group.command(name="train_spy", description="Enroll an operative in the National Intelligence Academy to rank up.")
    @app_commands.describe(
        spy_id="ID of the idle operative to train",
        target_level="Target rank level (2: Field Operative, 3: Sabotage Specialist, 4: Cyber Infiltrator, 5: Phantom Ghost)"
    )
    @app_commands.choices(target_level=[
        app_commands.Choice(name="Level 2: Field Operative (20,000 M)", value=2),
        app_commands.Choice(name="Level 3: Sabotage Specialist (45,000 M)", value=3),
        app_commands.Choice(name="Level 4: Cyber Infiltrator (80,000 M)", value=4),
        app_commands.Choice(name="Level 5: Master Phantom Ghost (130,000 M)", value=5),
    ])
    async def earth_train_spy(self, interaction: discord.Interaction, spy_id: int, target_level: app_commands.Choice[int]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("⛔ You do not govern or lead an Earth nation!", ephemeral=True)
            return

        success, msg, res = await self.bot.db.train_earth_spy(interaction.user.id, c["id"], spy_id, target_level.value)
        if not success:
            await interaction.followup.send(f"{msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎓 Intelligence Academy: Operative Graduated!",
            description=(
                f"**Operative Codename:** Agent '{res['codename']}'\n"
                f"**New Sovereign Rank:** 🎖️ **{res['rank_title']}** (Level {res['new_level']}/5)\n"
                f"**Clearance Authority:** {interaction.user.mention}\n"
                f"**Host Nation:** {c['flag']} **{c['name']}**\n\n"
                f"{msg}"
            ),
            color=0x38BDF8
        )
        embed.set_footer(text="Virtual Earth 3D • Covert Operations Bureau")
        await interaction.followup.send(embed=embed)

    @security_group.command(name="buy_intel", description="Purchase classified foreign intelligence dossiers from intelligence brokers.")
    @app_commands.describe(
        target_country="3-letter code or name of target country",
        intel_type="Type of classified intelligence dossier to procure"
    )
    @app_commands.choices(intel_type=[
        app_commands.Choice(name="Covert Operations & Sabotage History (35,000 M)", value="covert_history"),
        app_commands.Choice(name="Military Arsenal & Tool Readiness (50,000 M)", value="military_readiness"),
        app_commands.Choice(name="Treasury Reserves & Yield Audit (25,000 M)", value="economic_vault"),
    ])
    async def earth_buy_intel(self, interaction: discord.Interaction, target_country: str, intel_type: app_commands.Choice[str]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("⛔ You do not govern or lead an Earth nation!", ephemeral=True)
            return

        target_c = await self.bot.db.get_earth_country_by_code_or_name(target_country)
        if not target_c:
            await interaction.followup.send(f"❌ Country '{target_country}' was not found in the global registry.", ephemeral=True)
            return

        if target_c["id"] == c["id"]:
            await interaction.followup.send("❌ You cannot buy intelligence dossiers on your own sovereign nation.", ephemeral=True)
            return

        success, msg, dossier = await self.bot.db.buy_earth_intel_dossier(interaction.user.id, c["id"], target_c["id"], intel_type.value)
        if not success:
            await interaction.followup.send(f"{msg}", ephemeral=True)
            return

        summary_text = dossier.get("summary", "")
        embed = discord.Embed(
            title=f"📑 Classified Intelligence Dossier: {target_c['flag']} {target_c['name']}",
            description=f"**Category:** {dossier.get('category', 'Espionage Report')}\n**Briefing:** *{summary_text}*",
            color=0xF59E0B
        )

        if intel_type.value == "military_readiness":
            embed.add_field(name="Active War Theaters", value=str(dossier.get("active_wars", 0)), inline=True)
            embed.add_field(name="Fortification Bunkers", value=f"Lvl {dossier.get('bunker_defense', 0)}", inline=True)
            arsenal = dossier.get("installed_arsenal", [])
            embed.add_field(name="Installed Weapon Systems", value=", ".join(arsenal) if arsenal else "None detected", inline=False)
        elif intel_type.value == "economic_vault":
            embed.add_field(name="Confirmed Treasury", value=f"{dossier.get('treasury', 0):,} Medals", inline=True)
            embed.add_field(name="National GDP", value=f"{dossier.get('gdp', 0):,} Medals", inline=True)
            embed.add_field(name="Domestic Tax Rate", value=str(dossier.get("tax_rate", "10%")), inline=True)
        elif intel_type.value == "covert_history":
            embed.add_field(name="Domestic Unrest", value=f"{dossier.get('unrest', 0)}%", inline=True)
            embed.add_field(name="Civil Rioting", value="🔥 ACTIVE" if dossier.get("is_rioting") else "Peaceful", inline=True)

        embed.set_footer(text="Virtual Earth 3D • Top Secret Clearance")
        await interaction.followup.send(embed=embed)


    # ══════════════════════════════════════════════════════════════════════════
    # 🇺🇳 UNITED NATIONS (UN) & MAYOR GLOBAL PEACEKEEPING COMMANDS
    # ══════════════════════════════════════════════════════════════════════════

    async def _is_un_mayor(self, interaction: discord.Interaction) -> bool:
        """Verify if caller is the active Mayor / UN Secretary-General or Server Owner."""
        if interaction.user.id == 429350468796416013:
            return True
        if hasattr(interaction.user, "roles") and any(r.name == "🏛️ Mayor" for r in interaction.user.roles):
            return True
        if interaction.guild and interaction.guild.owner_id == interaction.user.id:
            return True
        curr = await self.bot.db.get_current_commander(interaction.guild_id or 0)
        if curr and curr.get("winner_id") == interaction.user.id:
            return True
        return False

    @un_group.command(name="status", description="View United Nations (UN) Secretary-General status and active global sanctions.")
    async def earth_un_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        status = await self.bot.db.get_earth_un_status()
        mayor_id = status.get("mayor_id")
        sanctions = status.get("active_sanctions", [])
        ceasefires = status.get("recent_ceasefires", [])

        sec_gen = f"<@{mayor_id}>" if mayor_id else "UN Security Council High Command"
        embed = discord.Embed(
            title="🇺🇳 United Nations Security Council • Global Peacekeeping Directorate",
            description=(
                f"**Secretary-General / High Office:** {sec_gen}\n"
                f"**Mandate:** Supreme diplomatic authority to enforce ceasefires, impose economic sanctions, and dispatch humanitarian relief on Virtual Earth.\n"
                f"**Peacekeeping Reserve:** `500,000 Medals`\n\n"
                f"🌐 *Active International Sanctions:* **{len(sanctions)}**\n"
                f"🕊️ *Enforced Ceasefires:* **{len(ceasefires)}**"
            ),
            color=0x38BDF8
        )

        if sanctions:
            s_text = ""
            for s in sanctions[:5]:
                s_text += f"• {s['flag']} **{s['name']}**: *{s['reason']}* ({s['hours_left']}h left)\n"
            embed.add_field(name="🚫 Active UN Economic Sanctions", value=s_text, inline=False)
        else:
            embed.add_field(name="🚫 Active UN Economic Sanctions", value="*No nations currently under international embargo.*", inline=False)

        if ceasefires:
            c_text = ""
            for c in ceasefires[:3]:
                c_text += f"• **War #{c['war_id']}**: {c['details']}\n"
            embed.add_field(name="🕊️ Recent UN Armistice Decrees", value=c_text, inline=False)

        embed.set_footer(text="Virtual Earth 3D • United Nations Diplomatic Suite")
        await interaction.followup.send(embed=embed)

    @un_group.command(name="ceasefire", description="[Mayor / UN] Enforce an immediate binding UN Ceasefire decree halting an active war.")
    @app_commands.describe(war_id="ID of the active war to halt")
    async def earth_un_ceasefire(self, interaction: discord.Interaction, war_id: int):
        await interaction.response.defer()
        if not await self._is_un_mayor(interaction):
            await interaction.followup.send("⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) or High Council can enforce international ceasefires.", ephemeral=True)
            return

        success, msg, res = await self.bot.db.un_issue_ceasefire(interaction.user.id, war_id)
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title="🕊️ United Nations Emergency Ceasefire Enacted!",
            description=(
                f"**Issuing Authority:** UN Secretary-General {interaction.user.mention}\n"
                f"**Active War Terminated:** #{war_id}\n\n"
                f"{msg}"
            ),
            color=0x10B981
        )
        embed.set_footer(text="Virtual Earth 3D • UN Security Council Resolution")
        await interaction.followup.send(embed=embed)

    @un_group.command(name="sanction", description="[Mayor / UN] Impose international trade embargo and warfare sanctions on a rogue country.")
    @app_commands.describe(
        country="Country code or name to sanction",
        reason="Official reason for UN Security Council sanctions"
    )
    async def earth_un_sanction(self, interaction: discord.Interaction, country: str, reason: str):
        await interaction.response.defer()
        if not await self._is_un_mayor(interaction):
            await interaction.followup.send("⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) can impose international sanctions.", ephemeral=True)
            return

        target_c = await self.bot.db.get_earth_country_by_code_or_name(country)
        if not target_c:
            await interaction.followup.send(f"❌ Country '{country}' not found in the global registry.", ephemeral=True)
            return

        success, msg = await self.bot.db.un_impose_sanctions(interaction.user.id, target_c["id"], reason)
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🚫 UN Security Council Sanctions Imposed: {target_c['flag']} {target_c['name']}",
            description=(
                f"**Signatory Authority:** UN Secretary-General {interaction.user.mention}\n"
                f"**Sanction Term:** 48 Hours\n"
                f"**Official Justification:** *{reason}*\n\n"
                f"⚠️ *Penalties Applied: National trade yields halved and all offensive warfare declarations suspended.*"
            ),
            color=0xEF4444
        )
        embed.set_footer(text="Virtual Earth 3D • United Nations Diplomatic Suite")
        await interaction.followup.send(embed=embed)

    @un_group.command(name="aid", description="[Mayor / UN] Disburse 50,000 Medals in UN emergency relief to quell riots and rebuild stability.")
    @app_commands.describe(country="Country code or name to receive humanitarian aid")
    async def earth_un_aid(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer()
        if not await self._is_un_mayor(interaction):
            await interaction.followup.send("⛔ Supreme Authority Required: Only the UN Secretary-General (Mayor) can deploy UN Humanitarian Relief Grants.", ephemeral=True)
            return

        target_c = await self.bot.db.get_earth_country_by_code_or_name(country)
        if not target_c:
            await interaction.followup.send(f"❌ Country '{country}' not found in the global registry.", ephemeral=True)
            return

        success, msg = await self.bot.db.un_send_humanitarian_aid(interaction.user.id, target_c["id"])
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📦 UN Humanitarian Relief Grant Delivered: {target_c['flag']} {target_c['name']}",
            description=(
                f"**Disbursing Authority:** UN Secretary-General {interaction.user.mention}\n"
                f"**Relief Grant:** `50,000 Medals`\n"
                f"**Stability Impact:** -25% Civil Unrest, All Rioting Extinguished\n\n"
                f"{msg}"
            ),
            color=0x10B981
        )
        embed.set_footer(text="Virtual Earth 3D • UN Peacekeeping Mission")
        await interaction.followup.send(embed=embed)



    @earth_group.command(name="surrender", description="Concede and formally surrender in an active war.")
    @app_commands.describe(country="Opponent country code or name")
    async def earth_surrender(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer()
        my_c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not my_c:
            await interaction.followup.send("❌ Only a sovereign ruler or Minister of Defense can surrender an active campaign!", ephemeral=True)
            return

        opp = await self.bot.db.get_earth_country_by_code_or_name(country)
        if not opp:
            await interaction.followup.send(f"❌ Opponent country `{country}` not found in the global registry.")
            return

        active_wars = await self.bot.db.get_active_earth_wars()
        target_war = None
        for w in active_wars:
            if (w["attacker_country_id"] == my_c["id"] and w["defender_country_id"] == opp["id"]) or \
               (w["defender_country_id"] == my_c["id"] and w["attacker_country_id"] == opp["id"]):
                target_war = w
                break

        if not target_war:
            await interaction.followup.send(f"❌ No active war found between **{my_c['flag']} {my_c['name']}** and **{opp['flag']} {opp['name']}**.", ephemeral=True)
            return

        success, msg, res_data = await self.bot.db.surrender_earth_war(interaction.user.id, target_war["id"])
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        winner = res_data.get("winner_country", {})
        loser = res_data.get("loser_country", {})
        winner_name = winner.get("name", "Victor")
        winner_flag = winner.get("flag", "👑")
        loser_name = loser.get("name", "Conceded")
        loser_flag = loser.get("flag", "🏳️")
        loot = res_data.get("loot", 0)
        annexed = res_data.get("annexed", False)

        speech_buf = generate_surrender_speech(winner_name, loser_name, loot)
        gif, mp4_buf = create_war_ended_media(
            winner_name=winner_name,
            loser_name=loser_name,
            reason="SURRENDER CONCEDED",
            reparations=loot,
            audio_bytes=speech_buf
        )

        desc = (
            f"👑 **Victor:** {winner_flag} **{winner_name}**\n"
            f"🏳️ **Surrendered:** {loser_flag} **{loser_name}** (Conceded by {interaction.user.mention})\n"
            f"💰 **Indemnity Awarded:** `+{loot:,} Medals`\n"
            f"🌐 **Annexation:** {'Yes, annexed into imperial dominion!' if annexed else 'Territory borders held.'}\n\n"
            f"🕊️ Armistice signed! War operations have terminated immediately."
        )

        embed = discord.Embed(
            title="🏳️ FORMAL SURRENDER ACCEPTED // CONFLICT CONCLUDED",
            description=desc,
            color=0xEAB308
        )
        files = []
        if mp4_buf:
            mp4_buf.seek(0)
            files.append(discord.File(mp4_buf, filename="surrender_concluded.mp4"))
            embed.set_footer(text="Virtual Earth 3D Geopolitics • Deep Voice Video Player Attached 🎬🎙️")
        else:
            gif.seek(0)
            files.append(discord.File(gif, filename="surrender.gif"))
            embed.set_image(url="attachment://surrender.gif")
            if speech_buf:
                speech_buf.seek(0)
                files.append(discord.File(speech_buf, filename="voice_announcement.mp3"))
            embed.set_footer(text="Virtual Earth Geopolitics • Voice Narration Attached 🎙️")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="🌍 Open 3D Earth Globe", url=WEB_URL, style=discord.ButtonStyle.link))
        await interaction.followup.send(embed=embed, view=view, files=files)

        await self.broadcast_surrender_news(
            winner_name=winner_name,
            winner_flag=winner_flag,
            loser_name=loser_name,
            loser_flag=loser_flag,
            loot=loot,
            annexed=annexed,
            conceded_by=interaction.user.mention
        )

    @broadcast_group.command(name="speech", description="Broadcast an official presidential voice announcement to Earth News.")
    @app_commands.describe(speech="Official speech text to be spoken by the global news announcer")
    async def earth_announce_speech(self, interaction: discord.Interaction, speech: str):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ Only a sovereign leader or Minister can issue presidential dispatches!", ephemeral=True)
            return

        speech_text = speech.strip()
        if len(speech_text) < 5 or len(speech_text) > 400:
            await interaction.followup.send("❌ Speech text must be between 5 and 400 characters.", ephemeral=True)
            return

        clean = clean_for_speech(speech_text)
        speech_buf = generate_voice_narration(f"Presidential address from {c['name']}. {clean}")
        gif = create_new_ruler_gif(c["name"], c["flag"], interaction.user.display_name)

        desc = (
            f"🏛️ **Sovereign Nation:** {c['flag']} **{c['name']}**\n"
            f"👑 **Addressed By:** {interaction.user.mention} (`{interaction.user.display_name}`)\n"
            f"📜 **Official Dispatch:** \"*{speech_text}*\"\n\n"
            f"🎙️ *Spoken audio broadcast transmitted across all sovereign frequencies.*"
        )

        embed = discord.Embed(
            title=f"🎙️ PRESIDENTIAL DISPATCH // {c['name'].upper()}",
            description=desc,
            color=0x38BDF8
        )
        gif.seek(0)
        speech_buf.seek(0)
        files = [
            discord.File(gif, filename="address.gif"),
            discord.File(speech_buf, filename="voice_announcement.mp3")
        ]
        embed.set_image(url="attachment://address.gif")
        embed.set_footer(text="Virtual Earth Geopolitics • Voice Narration Transmitted 🎙️")
        await interaction.followup.send(embed=embed, files=files)

        # Broadcast to #earth-news
        news_gif = create_new_ruler_gif(c["name"], c["flag"], interaction.user.display_name)
        speech_buf2 = generate_voice_narration(f"Presidential address from {c['name']}. {clean}")
        await self.broadcast_news(
            title=f"🎙️ PRESIDENTIAL DISPATCH // {c['name'].upper()}",
            description=desc,
            gif_bytes=news_gif,
            filename="address_news.gif",
            color=0x38BDF8,
            speech_bytes=speech_buf2
        )

    @broadcast_group.command(name="commander", description="Broadcast an official military commander appointment video to Earth News.")
    @app_commands.describe(commander="Discord member serving as Supreme Military Commander")
    async def earth_announce_commander(self, interaction: discord.Interaction, commander: discord.Member):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ You do not govern a sovereign Earth nation!", ephemeral=True)
            return
        await self.broadcast_commander_news(c["name"], c["flag"], commander.display_name)
        await interaction.followup.send(f"⚔️ Military commander appointment video and spoken dispatch broadcasted to <#{EARTH_NEWS_CHANNEL_ID}> for **{commander.display_name}**!")

    @broadcast_group.command(name="alliance", description="Broadcast an official strategic alliance video to Earth News.")
    @app_commands.describe(partner="Partner allied country code or name")
    async def earth_announce_alliance(self, interaction: discord.Interaction, partner: str):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ You do not govern a sovereign Earth nation!", ephemeral=True)
            return
        
        partner_code = partner.strip().upper()
        p_c = await self.bot.db.get_earth_country_by_code(partner_code)
        if not p_c:
            all_c = await self.bot.db.get_earth_countries()
            for cand in all_c:
                if partner.lower() in cand["name"].lower():
                    p_c = await self.bot.db.get_earth_country(cand["id"])
                    break
        partner_name = p_c["name"] if p_c else partner.strip()
        partner_flag = p_c["flag"] if p_c else "🌐"
        al_name = c.get("alliance_name") or f"{c['name']}-{partner_name} Strategic Accord"

        await self.broadcast_alliance_news(c["name"], c["flag"], partner_name, partner_flag, al_name)
        await interaction.followup.send(f"🤝 Strategic alliance video and spoken dispatch broadcasted to <#{EARTH_NEWS_CHANNEL_ID}> for **{c['name']}** & **{partner_name}**!")


async def setup(bot: commands.Bot):
    await bot.add_cog(EarthCog(bot))
