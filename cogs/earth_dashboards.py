# -*- coding: utf-8 -*-
"""
Virtual Earth: Interactive Discord Ministry Dashboards
Provides rich interactive dashboards, views, modals, and select menus for all 4 ministries + Presidential High Command.
"""

import time
import discord
from discord.ext import commands
from discord import app_commands

from utils.constants import (
    EARTH_CABINET_ROLES,
    EARTH_BUILDINGS,
    EARTH_WAR_SCALES,
    EARTH_SPY_MISSIONS,
    EARTH_DOCTRINES
)

WEB_URL = "https://phantom-regiment-1.onrender.com/estate"


def _parse_user_id(val: str) -> int | None:
    if not val:
        return None
    cleaned = val.strip().replace("<@", "").replace("!", "").replace(">", "").strip()
    try:
        return int(cleaned)
    except ValueError:
        return None


# ─── Embed Builders ──────────────────────────────────────────────────────────

async def build_defense_embed(bot, country: dict, user_id: int) -> discord.Embed:
    c = await bot.db.get_earth_country(country["id"]) or country
    mil_power = c.get("total_military_power", 50)
    def_power = c.get("total_defense_power", 50)

    conquered_count = c.get("conquered_states_count", 0)
    empire_str = f"`{conquered_count}/4 Conquered States`"
    if c.get("is_annexed_state"):
        empire_str += f" *(Annexed State of {c.get('motherland_flag')} {c.get('motherland_name')})*"

    embed = discord.Embed(
        title=f"⚔️ Ministry of Defense: {c['flag']} {c['name']} ({c['code']})",
        description=(
            f"**Supreme Army Commander:** <@{user_id}>\n"
            f"**Military Power:** `{mil_power}` 🪖 | **Defensive Rating:** `{def_power}` 🛡️\n"
            f"**Imperial Commonwealth:** {empire_str}\n"
            f"**Frontline Theaters:** Deploy division reinforcements, declare multi-day conquest campaigns, or conquer frontier lands below."
        ),
        color=0xDC2626
    )

    # Active wars
    active_wars = await bot.db.get_active_earth_wars()
    my_wars = [w for w in active_wars if w.get("attacker_country_id") == c["id"] or w.get("defender_country_id") == c["id"]]

    if my_wars:
        war_lines = []
        for w in my_wars[:4]:
            is_atk = (w.get("attacker_country_id") == c["id"])
            role_icon = "⚔️ Assaulting" if is_atk else "🛡️ Defending"
            opp_name = f"{w.get('defender_flag')} {w.get('defender_name')}" if is_atk else f"{w.get('attacker_flag')} {w.get('attacker_name')}"
            scale_title = EARTH_WAR_SCALES.get(w.get("scale"), {}).get("name", w.get("scale"))
            progress = w.get("progress_pct", 0)
            bar = "🟩" * int(progress // 10) + "⬛" * (10 - int(progress // 10))
            war_lines.append(
                f"• **War #{w['id']}** [{role_icon} vs {opp_name}]\n"
                f"  Scale: `{scale_title}` | Remaining: `{w.get('hours_remaining', 0)}h`\n"
                f"  Front Progress: {bar} `{progress}%`\n"
                f"  Active Divisions: `{w.get('attacker_divisions')} Assault` vs `{w.get('defender_divisions')} Defense`"
            )
        embed.add_field(name="🚨 Active Frontline Campaigns", value="\n\n".join(war_lines), inline=False)
    else:
        embed.add_field(name="🕊️ Frontline Campaign Status", value="All frontiers are currently peaceful. No active war campaigns ongoing.", inline=False)

    # Unclaimed frontier lands preview
    all_countries = await bot.db.get_earth_countries()
    unowned = [cnt for cnt in all_countries if not cnt.get("owner_id")][:5]
    if unowned:
        frontiers = ", ".join([f"{u['flag']} `{u['code']}` ({u['name']})" for u in unowned])
        embed.add_field(name="🚩 Frontier Targets (Unclaimed Lands)", value=f"Army Commander can dispatch armed expeditions to conquer:\n{frontiers}", inline=False)

    embed.set_footer(text="Virtual Earth 3D • Ministry of Defense • Supreme Army Command")
    return embed


async def build_economy_embed(bot, country: dict, user_id: int) -> discord.Embed:
    c = await bot.db.get_earth_country(country["id"]) or country
    treasury = c.get("treasury", 0)
    gdp = c.get("gdp", 0)
    stability = c.get("stability", 80)
    unrest = c.get("unrest", 10)
    stab_bar = "🟩" * (stability // 10) + "⬛" * (10 - (stability // 10))
    unrest_bar = "🟥" * (unrest // 10) + "⬛" * (10 - (unrest // 10))

    riot_warning = ""
    if unrest >= 85:
        riot_warning = "\n🚨 **IMMINENT REVOLUTION!** Unrest >= 85% — Citizens are storming the presidential palace!"
    elif unrest >= 60:
        riot_warning = "\n🔥 **SEVERE RIOTS!** Violent demonstrations are halving national economic production!"

    embed = discord.Embed(
        title=f"🏦 Ministry of Economy: {c['flag']} {c['name']} ({c['code']})",
        description=(
            f"**Finance Minister / Sovereign:** <@{user_id}>\n"
            f"**State Treasury:** `{treasury:,} Medals` (Max 20% Siphon Cap)\n"
            f"**Gross Domestic Product (GDP):** `{gdp:,} Medals`\n"
            f"**National Stability ({stability}%):** {stab_bar}\n"
            f"**Civil Unrest ({unrest}%):** {unrest_bar}{riot_warning}"
        ),
        color=0x22C55E
    )

    buildings = c.get("buildings", [])
    if buildings:
        b_lines = []
        for b in buildings[:7]:
            b_lines.append(f"• {b['emoji']} **{b['name']}**: Lvl `{b['level']}` (+{b.get('hourly_yield', 0):,} M/hr)")
        embed.add_field(name="🏗️ Domestic Infrastructure Facilities", value="\n".join(b_lines), inline=False)
    else:
        embed.add_field(name="🏗️ Domestic Infrastructure", value="No facilities constructed yet. Commission universities, gold mines, or oil rigs below!", inline=False)

    routes = await bot.db.get_earth_trade_routes(c["id"])
    if routes:
        tr_lines = [f"• Maritime Sealane with **{r.get('partner_flag', '')} {r.get('partner_name', 'Partner')}** (+3,500 M/hr tariff)" for r in routes[:4]]
        embed.add_field(name=f"🚢 Maritime Sealanes ({len(routes)} Active)", value="\n".join(tr_lines), inline=False)
    else:
        embed.add_field(name="🚢 Maritime Trade Routes", value="No active maritime sealanes. Construct a Deepwater Port to inaugurate ocean trade!", inline=False)

    embed.set_footer(text="Virtual Earth 3D • Ministry of Economy & National Treasury")
    return embed


async def build_diplomacy_embed(bot, country: dict, user_id: int) -> discord.Embed:
    c = await bot.db.get_earth_country(country["id"]) or country
    alliance_name = c.get("alliance_name") or "Non-Aligned"

    embed = discord.Embed(
        title=f"📜 Ministry of Foreign Affairs: {c['flag']} {c['name']} ({c['code']})",
        description=(
            f"**Chief Diplomat / Sovereign:** <@{user_id}>\n"
            f"**Coalition Alignment:** `{alliance_name}`\n"
            f"**Bilateral Sealanes:** `{len(c.get('trade_routes', []))} Active Trade Treaties`\n"
            f"**Diplomatic Corps:** Charter defensive coalitions, sign accession treaties, establish oceanic trade, or submit state buyout offers."
        ),
        color=0x3B82F6
    )

    if c.get("alliance_id"):
        alliances = await bot.db.get_earth_alliances()
        my_al = next((a for a in alliances if a["id"] == c["alliance_id"]), None)
        if my_al:
            members_str = ", ".join([f"{m['flag']} {m['name']}" for m in my_al.get("members", [])])
            embed.add_field(
                name=f"🤝 Sovereign Coalition: {my_al['name']} (ID: #{my_al['id']})",
                value=f"• **Allied Nations ({my_al.get('member_count', 1)}):** {members_str}\n• **Collective Defense Bonus:** `+{my_al.get('member_count', 1) * 25} Defense Power`",
                inline=False
            )
    else:
        embed.add_field(name="🤝 Collective Security", value="Your nation is currently Non-Aligned. Charter a new coalition or join an existing treaty!", inline=False)

    offers = await bot.db.get_country_offers(user_id)
    pending_in = [o for o in offers if str(o.get("seller_id")) == str(user_id) and o.get("status") == "pending"]
    embed.add_field(name="📬 Sovereign Acquisition Offers", value=f"You have **{len(pending_in)}** pending buyout offer(s) in your diplomatic inbox.", inline=False)

    embed.set_footer(text="Virtual Earth 3D • Ministry of Foreign Affairs")
    return embed


async def build_intelligence_embed(bot, country: dict, user_id: int) -> discord.Embed:
    c = await bot.db.get_earth_country(country["id"]) or country
    spies = await bot.db.get_earth_spies(c["id"])

    embed = discord.Embed(
        title=f"🕵️ Directorate of Secret Intelligence: {c['flag']} {c['name']} ({c['code']})",
        description=(
            f"**Director of Intelligence / Sovereign:** <@{user_id}>\n"
            f"**Operative Force:** `{len(spies)} / 6 Field Agents`\n"
            f"**Counter-Espionage Network:** Active perimeter surveillance and detention facilities."
        ),
        color=0x8B5CF6
    )

    if spies:
        spy_lines = []
        for s in spies:
            st = s.get("status", "idle")
            st_badge = "🟢 Idle" if st == "idle" else ("🟡 Dispatched" if st == "dispatched" else "🔴 Captured")
            tgt = f" [Infiltrating {s.get('target_country_flag', '')} {s.get('target_country_name', 'Foreign State')}]" if st == "dispatched" else ""
            spy_lines.append(f"• **Agent #{s['id']} '{s['codename']}'** (Rank: Lvl `{s.get('skill_level', 1)}`) — {st_badge}{tgt}")
        embed.add_field(name="🕵️ Active Operative Roster", value="\n".join(spy_lines), inline=False)
    else:
        embed.add_field(name="🕵️ Operative Roster", value="No field operatives recruited. Enlist secret agents below!", inline=False)

    intel_logs = await bot.db.get_earth_intelligence(c["id"])
    if intel_logs:
        intel_lines = []
        for log in intel_logs[:3]:
            intel_lines.append(f"• **Dossier on {log.get('target_flag', '')} {log.get('target_name', 'Target')}:** Stolen by Agent `{log.get('agent_name', 'Unknown')}`")
        embed.add_field(name="📂 Classified Stolen Intelligence", value="\n".join(intel_lines), inline=False)

    embed.set_footer(text="Virtual Earth 3D • Directorate of Secret Intelligence")
    return embed


async def build_president_embed(bot, country: dict, user_id: int) -> discord.Embed:
    c = await bot.db.get_earth_country(country["id"]) or country
    cab = c.get("cabinet", {})

    conquered_count = c.get("conquered_states_count", 0)
    empire_str = f"`{conquered_count}/4 Conquered States`"

    embed = discord.Embed(
        title=f"👑 Presidential High Command: {c['flag']} {c['name']} ({c['code']})",
        description=(
            f"**Supreme Sovereign & Head of State:** <@{user_id}>\n"
            f"**State Treasury:** `{c.get('treasury', 0):,} Medals` | **GDP:** `{c.get('gdp', 0):,} Medals`\n"
            f"**Stability:** `{c.get('stability', 80)}%` | **Civil Unrest:** `{c.get('unrest', 10)}%`\n"
            f"**Imperial Realm:** {empire_str}"
        ),
        color=0xF1C40F
    )

    cab_lines = []
    for rk, rm in EARTH_CABINET_ROLES.items():
        cab_info = cab.get(rk, {})
        u_id = cab_info.get("user_id")
        val = f"<@{u_id}>" if u_id else "*Vacant*"
        cab_lines.append(f"• **{rm['emoji']} {rm['short_title']}:** {val}")
    embed.add_field(name="🏛️ Sovereign Cabinet Portfolios", value="\n".join(cab_lines), inline=False)

    empire_states = c.get("empire_states", [])
    if empire_states:
        states_str = "\n".join([f"• {s['flag']} **{s['name']}** (`{s['code']}`) — GDP: `{s.get('gdp', 0):,} M`" for s in empire_states])
        embed.add_field(name=f"🚩 Conquered Imperial States ({len(empire_states)}/4)", value=states_str, inline=False)
    elif conquered_count > 0:
        embed.add_field(name=f"🚩 Conquered Imperial States ({conquered_count}/4)", value="Provinces integrated under imperial crown.", inline=False)

    embed.set_footer(text="Virtual Earth 3D • Presidential High Command")
    return embed


# ─── Modals ──────────────────────────────────────────────────────────────────

class DeclareWarModal(discord.ui.Modal, title="⚔️ Declare Sovereign War Campaign"):
    target_country = discord.ui.TextInput(
        label="Target Country Code (3 letters)",
        placeholder="e.g. USA, CHN, RUS, IND, JPN, GBR",
        min_length=2,
        max_length=10,
        required=True
    )
    scale = discord.ui.TextInput(
        label="War Scale: border (1d), annexation (3d), world_war (5d)",
        placeholder="annexation",
        default="annexation",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tgt = await self.bot.db.get_earth_country_by_code(self.target_country.value.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Sovereign country `{self.target_country.value}` not found.", ephemeral=True)
            return

        scale_val = self.scale.value.strip().lower()
        if scale_val not in EARTH_WAR_SCALES:
            scale_val = "annexation"

        success, msg, data = await self.bot.db.declare_earth_war(interaction.user.id, self.country["id"], tgt["id"], scale_val)
        if success:
            embed = discord.Embed(
                title="🚨 DECLARATION OF MILITARY CONQUEST",
                description=(
                    f"**{self.country['flag']} {self.country['name']}** has declared war on **{tgt['flag']} {tgt['name']}**!\n\n"
                    f"• **Campaign Scale:** `{data.get('scale_name', scale_val)}`\n"
                    f"• **Duration:** `{data.get('duration_hours')} Hours`\n"
                    f"• **Front Line Active:** Mobilize divisions to fortify your front line!"
                ),
                color=0xDC2626
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class AttackFrontierModal(discord.ui.Modal, title="🎖️ Military Frontier Expedition"):
    target_country = discord.ui.TextInput(
        label="Frontier Country Code (Unclaimed Land)",
        placeholder="e.g. MYS, FIN, PRT, DNK, QAT, IRL",
        min_length=2,
        max_length=10,
        required=True
    )
    divisions = discord.ui.TextInput(
        label="Divisions to Deploy (5 - 50 @ 20k M each)",
        placeholder="10",
        default="10",
        max_length=3,
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tgt = await self.bot.db.get_earth_country_by_code(self.target_country.value.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Frontier country `{self.target_country.value}` not found.", ephemeral=True)
            return

        try:
            divs = int(self.divisions.value.strip())
        except ValueError:
            divs = 10

        success, msg, data = await self.bot.db.expedition_attack_unclaimed(interaction.user.id, self.country["id"], tgt["id"], divs)
        if success:
            embed = discord.Embed(
                title="🚩 Frontier Territory Conquered & Annexed!",
                description=msg,
                color=0x22C55E
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class MobilizeDivisionsModal(discord.ui.Modal, title="🪖 Mobilize Division Reinforcements"):
    war_id = discord.ui.TextInput(
        label="Active War Campaign ID",
        placeholder="e.g. 1",
        required=True
    )
    divisions = discord.ui.TextInput(
        label="Divisions to Mobilize (1 - 50 @ 25k M each)",
        placeholder="10",
        default="10",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            wid = int(self.war_id.value.strip())
            divs = int(self.divisions.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter valid integer numbers.", ephemeral=True)
            return

        success, msg = await self.bot.db.reinforce_earth_war(interaction.user.id, wid, divs)
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class SiphonTreasuryModal(discord.ui.Modal, title="💸 Siphon National Treasury Reserves"):
    amount = discord.ui.TextInput(
        label="Withdrawal Amount (Medals, Max 20% Cap)",
        placeholder="e.g. 50000",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            amt = int(self.amount.value.strip().replace(",", ""))
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid numerical medal amount.", ephemeral=True)
            return

        success, msg, data = await self.bot.db.siphon_earth_treasury(interaction.user.id, self.country["id"], amt)
        if success:
            embed = discord.Embed(
                title="💸 Sovereign Treasury Disbursed",
                description=msg,
                color=0xF59E0B
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class CharterCoalitionModal(discord.ui.Modal, title="🤝 Charter International Coalition"):
    name = discord.ui.TextInput(
        label="Alliance Name",
        placeholder="e.g. Northern Defense Pact",
        min_length=3,
        max_length=32,
        required=True
    )
    banner_color = discord.ui.TextInput(
        label="Banner Hex Color",
        placeholder="#3b82f6",
        default="#3b82f6",
        max_length=7,
        required=False
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        color = self.banner_color.value.strip() or "#3b82f6"
        success, msg, aid = await self.bot.db.create_earth_alliance(interaction.user.id, self.country["id"], self.name.value.strip(), color)
        if success:
            embed = discord.Embed(
                title="🤝 International Coalition Established",
                description=f"**{self.name.value}** (Treaty #{aid}) has been chartered by **{self.country['flag']} {self.country['name']}**!\n\nAllied nations gain mutual defense guarantees (+25 defense per ally).",
                color=0x3B82F6
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class JoinCoalitionModal(discord.ui.Modal, title="📜 Join International Coalition"):
    alliance_id = discord.ui.TextInput(
        label="Coalition Treaty ID",
        placeholder="e.g. 1",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            aid = int(self.alliance_id.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid numerical coalition ID.", ephemeral=True)
            return

        success, msg = await self.bot.db.join_earth_alliance(interaction.user.id, self.country["id"], aid)
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class InaugurateSealaneModal(discord.ui.Modal, title="🚢 Inaugurate Ocean Trade Sealane"):
    target_country = discord.ui.TextInput(
        label="Partner Coastal Country Code",
        placeholder="e.g. GBR, JPN, USA, SGP, DEU",
        min_length=2,
        max_length=10,
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tgt = await self.bot.db.get_earth_country_by_code(self.target_country.value.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Partner country `{self.target_country.value}` not found.", ephemeral=True)
            return

        success, msg = await self.bot.db.propose_trade_route(interaction.user.id, self.country["id"], tgt["id"])
        if success:
            embed = discord.Embed(
                title="🚢 Maritime Trade Route Inaugurated",
                description=f"**{self.country['flag']} {self.country['name']}** established a high-yield bilateral sealane with **{tgt['flag']} {tgt['name']}**!\n\nBoth sovereign treasuries receive hourly commercial tariffs.",
                color=0x06B6D4
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class MakeBuyoutOfferModal(discord.ui.Modal, title="🏷️ Submit Diplomatic Buyout Bid"):
    target_country = discord.ui.TextInput(
        label="Target Country Code",
        placeholder="e.g. DEU, RUS, JPN, FRA",
        min_length=2,
        max_length=10,
        required=True
    )
    scope = discord.ui.TextInput(
        label="Scope: state (annexed state) or whole_country",
        placeholder="state or whole_country",
        default="state",
        required=True
    )
    amount = discord.ui.TextInput(
        label="Offer Price in Medals (0% Tax Applied)",
        placeholder="e.g. 1000000",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tgt = await self.bot.db.get_earth_country_by_code(self.target_country.value.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Target country `{self.target_country.value}` not found.", ephemeral=True)
            return

        try:
            amt = int(self.amount.value.strip().replace(",", ""))
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid numerical medal amount.", ephemeral=True)
            return

        sc = "whole_country" if self.scope.value.strip().lower() in ("whole_country", "empire") else "state"
        success, msg = await self.bot.db.create_country_offer(interaction.user.id, tgt["id"], amt, sc)
        if success:
            embed = discord.Embed(
                title="🏷️ Sovereign Buyout Bid Dispatched",
                description=(
                    f"**Purchaser:** <@{interaction.user.id}>\n"
                    f"**Target Sovereign:** {tgt['flag']} {tgt['name']}\n"
                    f"**Scope:** `{sc.upper()}`\n"
                    f"**Offer Amount:** `{amt:,} Medals` (0% Tax)\n\n"
                    f"The sovereign ruler of {tgt['name']} has received this offer in their Foreign Affairs inbox."
                ),
                color=0x3B82F6
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class RecruitSpyModal(discord.ui.Modal, title="🕵️ Enlist Secret Field Operative"):
    codename = discord.ui.TextInput(
        label="Agent Codename (Costs 120,000 Medals)",
        placeholder="e.g. Shadow-07, Viper, Raven, Ghost-Alpha",
        min_length=2,
        max_length=32,
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.recruit_earth_spy(interaction.user.id, self.country["id"], self.codename.value.strip())
        if success:
            embed = discord.Embed(
                title="🕵️ Secret Operative Commissioned",
                description=f"**Agent '{self.codename.value.strip()}'** has sworn allegiance to the Directorate of Intelligence for **{self.country['flag']} {self.country['name']}** (-120,000 Medals).",
                color=0x8B5CF6
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class DispatchSpyModal(discord.ui.Modal, title="🎯 Dispatch Covert Infiltration Mission"):
    spy_id = discord.ui.TextInput(
        label="Agent ID (from Operative Roster)",
        placeholder="e.g. 1",
        required=True
    )
    target_country = discord.ui.TextInput(
        label="Target Foreign Country Code",
        placeholder="e.g. USA, CHN, RUS, IND",
        min_length=2,
        max_length=10,
        required=True
    )
    mission = discord.ui.TextInput(
        label="Mission: intel, sabotage, incite_riot",
        placeholder="intel",
        default="intel",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            sid = int(self.spy_id.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid numerical Agent ID.", ephemeral=True)
            return

        tgt = await self.bot.db.get_earth_country_by_code(self.target_country.value.strip().upper())
        if not tgt:
            await interaction.followup.send(f"❌ Target country `{self.target_country.value}` not found.", ephemeral=True)
            return

        msn = self.mission.value.strip().lower()
        if msn not in EARTH_SPY_MISSIONS:
            msn = "intel"

        success, msg, data = await self.bot.db.dispatch_earth_spy(interaction.user.id, self.country["id"], sid, tgt["id"], msn)
        if success:
            embed = discord.Embed(
                title="🕵️ Espionage Operation Successful",
                description=f"Infiltration of **{tgt['flag']} {tgt['name']}** achieved!\n\n{msg}",
                color=0x3B82F6
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            embed = discord.Embed(
                title="🚨 ESPIONAGE OPERATION COMPROMISED",
                description=f"{msg}",
                color=0xEF4444
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


class TrainSpyModal(discord.ui.Modal, title="🎓 Spy Academy Advanced Training"):
    spy_id = discord.ui.TextInput(
        label="Agent ID (from Operative Roster)",
        placeholder="e.g. 1",
        required=True
    )
    target_level = discord.ui.TextInput(
        label="Target Level: 2 (20k), 3 (45k), 4 (80k), 5 (130k)",
        placeholder="2, 3, 4, or 5",
        default="2",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            sid = int(self.spy_id.value.strip())
            lvl = int(self.target_level.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter valid numbers.", ephemeral=True)
            return

        success, msg, data = await self.bot.db.train_earth_spy(interaction.user.id, self.country["id"], sid, lvl)
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class InterrogateSpyModal(discord.ui.Modal, title="⚖️ Interrogate Detained Enemy Spy"):
    spy_id = discord.ui.TextInput(
        label="Detained Enemy Agent ID",
        placeholder="e.g. 1",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            sid = int(self.spy_id.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid Agent ID.", ephemeral=True)
            return

        success, msg, data = await self.bot.db.interrogate_captured_spy(interaction.user.id, self.country["id"], sid)
        if success:
            embed = discord.Embed(
                title="⚖️ Confession & Intelligence Extracted",
                description=f"Captured enemy operative confessed all strategic secrets!\n\n{msg}",
                color=0x8B5CF6
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class ExecuteSpyModal(discord.ui.Modal, title="⚡ Execute Foreign Spy"):
    spy_id = discord.ui.TextInput(
        label="Convicted Spy ID to Execute",
        placeholder="e.g. 1",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            sid = int(self.spy_id.value.strip())
        except ValueError:
            await interaction.followup.send("❌ Please enter a valid Agent ID.", ephemeral=True)
            return

        success, msg = await self.bot.db.execute_captured_spy(interaction.user.id, self.country["id"], sid)
        if success:
            embed = discord.Embed(
                title="⚡ Treasonous Foreign Spy Executed",
                description=f"Execution warrant ratified by the Supreme Command. Civil unrest reduced by -5% across the capital.",
                color=0x111827
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class PresidentAppointModal(discord.ui.Modal, title="🏛️ Issue Cabinet Appointment Decree"):
    role = discord.ui.TextInput(
        label="Portfolio: defense, economy, diplomat, intelligence",
        placeholder="e.g. defense",
        required=True
    )
    nominee = discord.ui.TextInput(
        label="Nominee Discord User ID or @Mention",
        placeholder="e.g. 123456789012345678 or @Member",
        required=True
    )

    def __init__(self, bot, country: dict):
        super().__init__()
        self.bot = bot
        self.country = country

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rk = self.role.value.strip().lower()
        if rk not in EARTH_CABINET_ROLES:
            await interaction.followup.send("❌ Invalid role. Must be one of: `defense`, `economy`, `diplomat`, `intelligence`.", ephemeral=True)
            return

        target_uid = _parse_user_id(self.nominee.value)
        if not target_uid:
            await interaction.followup.send("❌ Could not parse user ID from nominee. Please provide a numeric Discord ID or @mention.", ephemeral=True)
            return

        success, msg, data = await self.bot.db.appoint_earth_cabinet(interaction.user.id, self.country["id"], rk, target_uid)
        if not success:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
            return

        role_meta = EARTH_CABINET_ROLES[rk]
        if data.get("auto_accepted"):
            embed = discord.Embed(
                title="🏛️ Executive Portfolio Assumed",
                description=f"**President <@{interaction.user.id}>** has assumed direct authority over **{role_meta['title']}** for **{self.country['flag']} {self.country['name']}**.",
                color=0xF1C40F
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        # Nomination decree pending candidate acceptance
        from cogs.earth import CabinetInviteView
        view = CabinetInviteView(
            bot=self.bot,
            invite_id=data["invite_id"],
            target_user_id=target_uid,
            president_id=interaction.user.id,
            role_title=role_meta["title"],
            country_name=self.country["name"],
            country_flag=self.country["flag"]
        )
        embed = discord.Embed(
            title="📜 Presidential Cabinet Decree Issued",
            description=(
                f"**President <@{interaction.user.id}>** has appointed **<@{target_uid}>** to the national cabinet!\n\n"
                f"**Portfolio:** {role_meta['emoji']} {role_meta['title']}\n"
                f"**Sovereign Nation:** {self.country['flag']} {self.country['name']}\n\n"
                f"⚠️ **Nominee Action Required:** <@{target_uid}> must click **[Accept Appointment]** below or run `/earth cabinet accept` to assume office."
            ),
            color=0xF1C40F
        )
        await interaction.channel.send(content=f"<@{target_uid}>", embed=embed, view=view)
        await interaction.followup.send("✅ Cabinet decree issued successfully!", ephemeral=True)


# ─── Dashboard Views ─────────────────────────────────────────────────────────

class DefenseDashboardView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int):
        super().__init__(timeout=3600)
        self.bot = bot
        self.country = country
        self.user_id = user_id

    @discord.ui.button(label="Declare War", style=discord.ButtonStyle.danger, emoji="⚔️", row=0)
    async def declare_war_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This defense dashboard is managed by the Commander.", ephemeral=True)
            return
        await interaction.response.send_modal(DeclareWarModal(self.bot, self.country))

    @discord.ui.button(label="Attack Frontier", style=discord.ButtonStyle.primary, emoji="🎖️", row=0)
    async def attack_frontier_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This defense dashboard is managed by the Commander.", ephemeral=True)
            return
        await interaction.response.send_modal(AttackFrontierModal(self.bot, self.country))

    @discord.ui.button(label="Mobilize (+10)", style=discord.ButtonStyle.secondary, emoji="🪖", row=0)
    async def mobilize_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This defense dashboard is managed by the Commander.", ephemeral=True)
            return
        await interaction.response.send_modal(MobilizeDivisionsModal(self.bot, self.country))

    @discord.ui.button(label="Refresh Front", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        c = await self.bot.db.get_earth_country(self.country["id"])
        embed = await build_defense_embed(self.bot, c or self.country, self.user_id)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Ministry Hub", style=discord.ButtonStyle.primary, emoji="🏛️", row=1)
    async def hub_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        hub_view = MinistryHubView(self.bot, self.country, self.user_id)
        embed = discord.Embed(
            title=f"🏛️ Sovereign Ministry Hub: {self.country['flag']} {self.country['name']}",
            description="Select any ministerial department below to access its live interactive dashboard.",
            color=0x3B82F6
        )
        await interaction.edit_original_response(embed=embed, view=hub_view)

    @discord.ui.button(label="Resign Command", style=discord.ButtonStyle.danger, emoji="🚪", row=1)
    async def resign_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.resign_earth_cabinet(self.user_id, self.country["id"])
        await interaction.followup.send(msg, ephemeral=True)


class InfrastructureSelect(discord.ui.Select):
    def __init__(self, bot, country: dict, user_id: int):
        self.bot = bot
        self.country = country
        self.user_id = user_id

        options = [
            discord.SelectOption(label="Public School & University", value="school", emoji="🏫", description="Boosts stability (+6) & lowers unrest (-5)"),
            discord.SelectOption(label="Regional Hospital & Healthcare", value="hospital", emoji="🏥", description="Drastically lowers unrest (-12) & boosts stability"),
            discord.SelectOption(label="Heavy Industrial Complex", value="heavy_factory", emoji="🏭", description="+25 Military & +15 Defense Power, +7,000 M/hr"),
            discord.SelectOption(label="Sovereign Gold & Mineral Mine", value="gold_mine", emoji="⛏️", description="+8,500 M/hr passive revenue directly to treasury"),
            discord.SelectOption(label="Deepwater Petroleum Oil Rig", value="oil_rig", emoji="🛢️", description="+16,000 M/hr massive commercial export yield"),
            discord.SelectOption(label="Fortified Citadel Bunker & SAM", value="bunker", emoji="🏰", description="+65 Defense Power to repel foreign invasions"),
            discord.SelectOption(label="Deepwater Port & Maritime Dock", value="naval_port", emoji="⚓", description="Enables Ocean Trade Routes & bilateral sealanes")
        ]
        super().__init__(placeholder="🏗️ Commission Domestic Infrastructure Project...", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This economy dashboard is managed by the Finance Minister.", ephemeral=True)
            return
        await interaction.response.defer()
        b_type = self.values[0]
        success, msg, cost = await self.bot.db.build_earth_infrastructure(self.user_id, self.country["id"], b_type)
        if success:
            c = await self.bot.db.get_earth_country(self.country["id"])
            embed = await build_economy_embed(self.bot, c or self.country, self.user_id)
            view = EconomyDashboardView(self.bot, c or self.country, self.user_id)
            await interaction.edit_original_response(embed=embed, view=view)
            await interaction.followup.send(f"✅ Commissioned project (-{cost:,} Medals)! {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class QuellUnrestSelect(discord.ui.Select):
    def __init__(self, bot, country: dict, user_id: int):
        self.bot = bot
        self.country = country
        self.user_id = user_id

        options = [
            discord.SelectOption(label="Civilian Emergency Stimulus", value="relief", emoji="🏥", description="Cost: 150k M (-25% Unrest, +15% Stability)"),
            discord.SelectOption(label="Tactical Police Suppression", value="police", emoji="🛡️", description="Cost: 80k M (-35% Unrest, -8% Liberty)"),
            discord.SelectOption(label="Sovereign Jubilee Celebration", value="festival", emoji="🎉", description="Cost: 60k M (-15% Unrest, +20% Stability)")
        ]
        super().__init__(placeholder="🏥 Pacify Civil Unrest & Suppress Riots...", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This economy dashboard is managed by the Finance Minister.", ephemeral=True)
            return
        await interaction.response.defer()
        method = self.values[0]
        success, msg = await self.bot.db.quell_earth_unrest(self.user_id, self.country["id"], method)
        if success:
            c = await self.bot.db.get_earth_country(self.country["id"])
            embed = await build_economy_embed(self.bot, c or self.country, self.user_id)
            view = EconomyDashboardView(self.bot, c or self.country, self.user_id)
            await interaction.edit_original_response(embed=embed, view=view)
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class EconomyDashboardView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int):
        super().__init__(timeout=3600)
        self.bot = bot
        self.country = country
        self.user_id = user_id
        self.add_item(InfrastructureSelect(bot, country, user_id))
        self.add_item(QuellUnrestSelect(bot, country, user_id))

    @discord.ui.button(label="Collect Yield", style=discord.ButtonStyle.success, emoji="💰", row=2)
    async def collect_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        amt, msg = await self.bot.db.collect_earth_yield(self.user_id)
        c = await self.bot.db.get_earth_country(self.country["id"])
        embed = await build_economy_embed(self.bot, c or self.country, self.user_id)
        await interaction.edit_original_response(embed=embed, view=self)
        await interaction.followup.send(f"💰 {msg}", ephemeral=True)

    @discord.ui.button(label="Siphon Treasury", style=discord.ButtonStyle.secondary, emoji="💸", row=2)
    async def siphon_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This economy dashboard is managed by the Finance Minister.", ephemeral=True)
            return
        await interaction.response.send_modal(SiphonTreasuryModal(self.bot, self.country))

    @discord.ui.button(label="Refresh Treasury", style=discord.ButtonStyle.secondary, emoji="🔄", row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        c = await self.bot.db.get_earth_country(self.country["id"])
        embed = await build_economy_embed(self.bot, c or self.country, self.user_id)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Ministry Hub", style=discord.ButtonStyle.primary, emoji="🏛️", row=3)
    async def hub_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        hub_view = MinistryHubView(self.bot, self.country, self.user_id)
        embed = discord.Embed(
            title=f"🏛️ Sovereign Ministry Hub: {self.country['flag']} {self.country['name']}",
            description="Select any ministerial department below to access its live interactive dashboard.",
            color=0x3B82F6
        )
        await interaction.edit_original_response(embed=embed, view=hub_view)

    @discord.ui.button(label="Resign Office", style=discord.ButtonStyle.danger, emoji="🚪", row=3)
    async def resign_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.resign_earth_cabinet(self.user_id, self.country["id"])
        await interaction.followup.send(msg, ephemeral=True)


class DiplomacyDashboardView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int):
        super().__init__(timeout=3600)
        self.bot = bot
        self.country = country
        self.user_id = user_id

    @discord.ui.button(label="Charter Coalition", style=discord.ButtonStyle.primary, emoji="🤝", row=0)
    async def charter_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Chief Diplomat.", ephemeral=True)
            return
        await interaction.response.send_modal(CharterCoalitionModal(self.bot, self.country))

    @discord.ui.button(label="Join Coalition", style=discord.ButtonStyle.secondary, emoji="📜", row=0)
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Chief Diplomat.", ephemeral=True)
            return
        await interaction.response.send_modal(JoinCoalitionModal(self.bot, self.country))

    @discord.ui.button(label="Leave Coalition", style=discord.ButtonStyle.danger, emoji="🚪", row=0)
    async def leave_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Chief Diplomat.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.leave_earth_alliance(self.user_id, self.country["id"])
        await interaction.followup.send(msg, ephemeral=True)

    @discord.ui.button(label="Inaugurate Sealane", style=discord.ButtonStyle.secondary, emoji="🚢", row=1)
    async def sealane_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Chief Diplomat.", ephemeral=True)
            return
        await interaction.response.send_modal(InaugurateSealaneModal(self.bot, self.country))

    @discord.ui.button(label="Make Buyout Bid", style=discord.ButtonStyle.primary, emoji="🏷️", row=1)
    async def offer_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Chief Diplomat.", ephemeral=True)
            return
        await interaction.response.send_modal(MakeBuyoutOfferModal(self.bot, self.country))

    @discord.ui.button(label="Offers Inbox", style=discord.ButtonStyle.secondary, emoji="📬", row=1)
    async def inbox_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        offers = await self.bot.db.get_country_offers(self.user_id)
        pending_in = [o for o in offers if str(o.get("seller_id")) == str(self.user_id) and o.get("status") == "pending"]
        if not pending_in:
            await interaction.followup.send("📬 Your diplomatic inbox has no pending sovereign buyout bids.", ephemeral=True)
            return

        lines = []
        for o in pending_in[:5]:
            lines.append(f"• **Offer #{o['id']}** from <@{o.get('buyer_id')}>: `{o.get('offer_amount', 0):,} Medals` for `{o.get('offer_scope', 'state').upper()}`")
        embed = discord.Embed(
            title="📬 Sovereign Buyout Offers Inbox",
            description="\n".join(lines),
            color=0x3B82F6
        )
        inbox_view = OffersInboxView(self.bot, self.country, self.user_id, pending_in)
        await interaction.followup.send(embed=embed, view=inbox_view, ephemeral=True)

    @discord.ui.button(label="Refresh Diplomacy", style=discord.ButtonStyle.secondary, emoji="🔄", row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        c = await self.bot.db.get_earth_country(self.country["id"])
        embed = await build_diplomacy_embed(self.bot, c or self.country, self.user_id)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Ministry Hub", style=discord.ButtonStyle.primary, emoji="🏛️", row=2)
    async def hub_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        hub_view = MinistryHubView(self.bot, self.country, self.user_id)
        embed = discord.Embed(
            title=f"🏛️ Sovereign Ministry Hub: {self.country['flag']} {self.country['name']}",
            description="Select any ministerial department below to access its live interactive dashboard.",
            color=0x3B82F6
        )
        await interaction.edit_original_response(embed=embed, view=hub_view)

    @discord.ui.button(label="Resign Office", style=discord.ButtonStyle.danger, emoji="🚪", row=2)
    async def resign_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.resign_earth_cabinet(self.user_id, self.country["id"])
        await interaction.followup.send(msg, ephemeral=True)


class OffersInboxView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int, offers: list[dict]):
        super().__init__(timeout=600)
        self.bot = bot
        self.country = country
        self.user_id = user_id
        self.offers = offers

        if offers:
            o = offers[0]
            self.first_offer_id = o["id"]
            self.accept_btn.label = f"Accept Offer #{o['id']}"
            self.reject_btn.label = f"Reject Offer #{o['id']}"

    @discord.ui.button(label="Accept Offer", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        success, msg = await self.bot.db.accept_country_offer(self.user_id, self.first_offer_id)
        if success:
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    @discord.ui.button(label="Reject Offer", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        success, msg = await self.bot.db.reject_country_offer(self.user_id, self.first_offer_id)
        await interaction.followup.send(msg, ephemeral=True)


class IntelligenceDashboardView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int):
        super().__init__(timeout=3600)
        self.bot = bot
        self.country = country
        self.user_id = user_id

    @discord.ui.button(label="Recruit Agent", style=discord.ButtonStyle.primary, emoji="🕵️", row=0)
    async def recruit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Director of Intelligence.", ephemeral=True)
            return
        await interaction.response.send_modal(RecruitSpyModal(self.bot, self.country))

    @discord.ui.button(label="Dispatch Mission", style=discord.ButtonStyle.danger, emoji="🎯", row=0)
    async def dispatch_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Director of Intelligence.", ephemeral=True)
            return
        await interaction.response.send_modal(DispatchSpyModal(self.bot, self.country))

    @discord.ui.button(label="Academy Training", style=discord.ButtonStyle.secondary, emoji="🎓", row=0)
    async def train_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Director of Intelligence.", ephemeral=True)
            return
        await interaction.response.send_modal(TrainSpyModal(self.bot, self.country))

    @discord.ui.button(label="Interrogate Captive", style=discord.ButtonStyle.secondary, emoji="⚖️", row=1)
    async def interrogate_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Director of Intelligence.", ephemeral=True)
            return
        await interaction.response.send_modal(InterrogateSpyModal(self.bot, self.country))

    @discord.ui.button(label="Execute Spy", style=discord.ButtonStyle.danger, emoji="⚡", row=1)
    async def execute_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Managed by Director of Intelligence.", ephemeral=True)
            return
        await interaction.response.send_modal(ExecuteSpyModal(self.bot, self.country))

    @discord.ui.button(label="Refresh Bureau", style=discord.ButtonStyle.secondary, emoji="🔄", row=2)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        c = await self.bot.db.get_earth_country(self.country["id"])
        embed = await build_intelligence_embed(self.bot, c or self.country, self.user_id)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Ministry Hub", style=discord.ButtonStyle.primary, emoji="🏛️", row=2)
    async def hub_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        hub_view = MinistryHubView(self.bot, self.country, self.user_id)
        embed = discord.Embed(
            title=f"🏛️ Sovereign Ministry Hub: {self.country['flag']} {self.country['name']}",
            description="Select any ministerial department below to access its live interactive dashboard.",
            color=0x3B82F6
        )
        await interaction.edit_original_response(embed=embed, view=hub_view)

    @discord.ui.button(label="Resign Office", style=discord.ButtonStyle.danger, emoji="🚪", row=2)
    async def resign_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        success, msg = await self.bot.db.resign_earth_cabinet(self.user_id, self.country["id"])
        await interaction.followup.send(msg, ephemeral=True)


class DismissMinisterSelect(discord.ui.Select):
    def __init__(self, bot, country: dict, user_id: int):
        self.bot = bot
        self.country = country
        self.user_id = user_id

        options = [
            discord.SelectOption(label="Dismiss Minister of Defense", value="defense", emoji="⚔️"),
            discord.SelectOption(label="Dismiss Minister of Economy", value="economy", emoji="🏦"),
            discord.SelectOption(label="Dismiss Chief Diplomat", value="diplomat", emoji="📜"),
            discord.SelectOption(label="Dismiss Director of Intelligence", value="intelligence", emoji="🕵️")
        ]
        super().__init__(placeholder="🚫 Dismiss Cabinet Minister / Vacate Portfolio...", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Only the sitting President can dismiss ministers.", ephemeral=True)
            return
        await interaction.response.defer()
        role_to_dismiss = self.values[0]
        success, msg = await self.bot.db.dismiss_earth_cabinet(self.user_id, self.country["id"], role_to_dismiss)
        if success:
            c = await self.bot.db.get_earth_country(self.country["id"])
            embed = await build_president_embed(self.bot, c or self.country, self.user_id)
            view = PresidentDashboardView(self.bot, c or self.country, self.user_id)
            await interaction.edit_original_response(embed=embed, view=view)
            await interaction.followup.send(f"✅ {msg}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)


class PresidentDashboardView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int):
        super().__init__(timeout=3600)
        self.bot = bot
        self.country = country
        self.user_id = user_id
        self.add_item(DismissMinisterSelect(bot, country, user_id))

    @discord.ui.button(label="Appoint Minister", style=discord.ButtonStyle.primary, emoji="🏛️", row=1)
    async def appoint_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Sovereign executive privilege required.", ephemeral=True)
            return
        await interaction.response.send_modal(PresidentAppointModal(self.bot, self.country))

    @discord.ui.button(label="Ministry Switcher", style=discord.ButtonStyle.secondary, emoji="🌐", row=1)
    async def switcher_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        hub_view = MinistryHubView(self.bot, self.country, self.user_id)
        embed = discord.Embed(
            title=f"🏛️ Sovereign Ministry Hub: {self.country['flag']} {self.country['name']}",
            description="Select any ministerial department below to access its live interactive dashboard.",
            color=0x3B82F6
        )
        await interaction.edit_original_response(embed=embed, view=hub_view)

    @discord.ui.button(label="Refresh Desk", style=discord.ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        c = await self.bot.db.get_earth_country(self.country["id"])
        embed = await build_president_embed(self.bot, c or self.country, self.user_id)
        await interaction.edit_original_response(embed=embed, view=self)


class MinistryHubSelect(discord.ui.Select):
    def __init__(self, bot, country: dict, user_id: int):
        self.bot = bot
        self.country = country
        self.user_id = user_id

        options = [
            discord.SelectOption(label="Ministry of Defense", value="defense", emoji="⚔️", description="Frontlines, War Campaigns, Frontier Conquests, Reinforcements"),
            discord.SelectOption(label="Ministry of Economy", value="economy", emoji="🏦", description="Infrastructure, Treasury Reserves, Dividends, Unrest Relief"),
            discord.SelectOption(label="Ministry of Foreign Affairs", value="diplomat", emoji="📜", description="Coalitions, Bilateral Trade Sealanes, Buyout Offers"),
            discord.SelectOption(label="Directorate of Intelligence", value="intelligence", emoji="🕵️", description="Operative Roster, Training, Espionage Missions, Captives"),
            discord.SelectOption(label="Presidential High Command", value="president", emoji="👑", description="Executive Decrees, Cabinet Appointments, Imperial Realm")
        ]
        super().__init__(placeholder="🏛️ Switch Ministerial Portfolio Dashboard...", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        choice = self.values[0]

        # Permission verification
        if choice == "president":
            is_president = (str(self.country.get("owner_id")) == str(interaction.user.id))
            if not is_president:
                await interaction.followup.send("⛔ Sovereign Privilege Required: Only the sitting President/PM can access Presidential High Command!", ephemeral=True)
                return
            c = await self.bot.db.get_earth_country(self.country["id"])
            embed = await build_president_embed(self.bot, c or self.country, interaction.user.id)
            view = PresidentDashboardView(self.bot, c or self.country, interaction.user.id)
            await interaction.edit_original_response(embed=embed, view=view)
            return

        has_perm = await self.bot.db.has_earth_cabinet_permission(interaction.user.id, self.country["id"], choice)
        if not has_perm:
            role_meta = EARTH_CABINET_ROLES.get(choice, {"title": choice})
            await interaction.followup.send(
                f"⛔ Executive Authorization Required: You must be appointed as **{role_meta.get('title')}** or be the Sovereign President to manage this department!",
                ephemeral=True
            )
            return

        c = await self.bot.db.get_earth_country(self.country["id"])
        if choice == "defense":
            embed = await build_defense_embed(self.bot, c or self.country, interaction.user.id)
            view = DefenseDashboardView(self.bot, c or self.country, interaction.user.id)
        elif choice == "economy":
            embed = await build_economy_embed(self.bot, c or self.country, interaction.user.id)
            view = EconomyDashboardView(self.bot, c or self.country, interaction.user.id)
        elif choice == "diplomat":
            embed = await build_diplomacy_embed(self.bot, c or self.country, interaction.user.id)
            view = DiplomacyDashboardView(self.bot, c or self.country, interaction.user.id)
        elif choice == "intelligence":
            embed = await build_intelligence_embed(self.bot, c or self.country, interaction.user.id)
            view = IntelligenceDashboardView(self.bot, c or self.country, interaction.user.id)
        else:
            return

        await interaction.edit_original_response(embed=embed, view=view)


class MinistryHubView(discord.ui.View):
    def __init__(self, bot, country: dict, user_id: int):
        super().__init__(timeout=3600)
        self.bot = bot
        self.country = country
        self.user_id = user_id
        self.add_item(MinistryHubSelect(bot, country, user_id))
        self.add_item(discord.ui.Button(label="3D Earth Globe", url=WEB_URL, style=discord.ButtonStyle.link, row=1))
