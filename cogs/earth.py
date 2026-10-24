# -*- coding: utf-8 -*-
"""
Virtual Earth: 3D Global Geopolitics MMO Simulation Cog
Commands for national governance, cabinet appointments, infrastructure, espionage, and conquest.
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

WEB_URL = "https://phantom-regiment-1.onrender.com/earth"


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


class EarthCog(commands.Cog, name="Virtual Earth"):
    """Global sovereign governance, cabinet appointments, and military conquests."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    earth_group = app_commands.Group(name="earth", description="🌍 Virtual Earth: Global Geopolitics Simulation")
    cabinet_group = app_commands.Group(name="cabinet", parent=earth_group, description="🏛️ Sovereign Cabinet & Ministers")

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

    @earth_group.command(name="commanders", description="⚔️ Supreme Army Command & Defense Forces")
    async def earth_commanders(self, interaction: discord.Interaction):
        await self.earth_defense(interaction)

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

    @earth_group.command(name="alliance", description="🤝 International Coalitions & Diplomatic Treaties")
    async def earth_alliance(self, interaction: discord.Interaction):
        await self.earth_diplomacy(interaction)

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
        app_commands.Choice(name="🔥 Fund Dissidents & Incite Urban Riots (+25% Unrest)", value="incite_riot"),
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
                title="🕵️ Espionage Operation Successful",
                description=f"**Agent '{spy['codename']}'** infiltrated **{tgt['flag']} {tgt['name']}**!\n\n{msg}",
                color=0x3B82F6
            )
            await interaction.followup.send(embed=embed)
        else:
            embed = discord.Embed(
                title="🚨 ESPIONAGE OPERATION COMPROMISED",
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
            embed = discord.Embed(
                title="🚨 DECLARATION OF SOVEREIGN WAR",
                description=f"**{c['flag']} {c['name']}** has officially declared war on **{tgt['flag']} {tgt['name']}**!\n\n"
                            f"• **Campaign Scale:** {scale.name}\n"
                            f"• **Duration:** `{war_data.get('duration_hours')} Hours`\n"
                            f"• **Front Line Active:** Follow the campaign and deploy division reinforcements on the 3D globe!",
                color=0xDC2626
            )
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="⚔️ Open 3D War Room", url=WEB_URL, style=discord.ButtonStyle.link))
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

    # ─── Quell Unrest & Riots ─────────────────────────────────────────────────

    @earth_group.command(name="quell", description="Deploy resources to quell civil unrest and suppress riots.")
    @app_commands.describe(method="Pacification strategy")
    @app_commands.choices(method=[
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
        await interaction.followup.send(f"{msg}" if success else f"❌ {msg}")


    # ??? Custom Country Creation & Unowned Nation Claims ?????????????????????????

    @earth_group.command(name="found", description="Charter and buy a custom sovereign nation for any medal offer (0-inf, 0% tax).")
    @app_commands.describe(
        name="Official sovereign name of your new nation",
        flag="Flag or icon emoji (e.g. ?????, ??, ??, ??, ??, ???, ??, ??)",
        capital="Name of your capital city",
        offer="Medals offered to charter (0 to inf, no tax). Offer directly funds treasury",
        replace_current="Relinquish leadership of your current nation if you already govern one"
    )
    async def earth_found(
        self,
        interaction: discord.Interaction,
        name: str,
        flag: str = "???",
        capital: str = "Capital City",
        offer: int = 0,
        replace_current: bool = False
    ):
        await interaction.response.defer()
        success, msg, c = await self.bot.db.create_custom_country(
            user_id=interaction.user.id,
            name=name,
            flag=flag,
            capital=capital,
            offered_medals=offer,
            replace_current=replace_current
        )
        if not success:
            await interaction.followup.send(f"? {msg}")
            return

        desc_text = (
            f"Supreme Sovereign: {interaction.user.mention}\n"
            f"Capital City: **{c['capital']}**\n"
            f"National Treasury: **{c['treasury']:,} Medals** (0% Treaty Tax applied)\n"
            f"Sovereign GDP: **{c['gdp']:,} Medals**\n"
            f"Geographic Coordinates: `Lat {c['lat']}, Lng {c['lng']}`\n\n"
            f"Your sovereign nation is now live on the 3D globe! Manage your cabinet, military, industry, and espionage from the interactive command room."
        )

        embed = discord.Embed(
            title=f"?? Sovereign Nation Proclaimed: {c['flag']} {c['name']} ({c['code']})",
            description=desc_text,
            color=0xF59E0B
        )
        embed.set_footer(text="Virtual Earth 3D Simulation ? 0% Treaty Tax Applied")
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open 3D Command Deck", url=WEB_URL, style=discord.ButtonStyle.link, emoji="??"))
        await interaction.followup.send(embed=embed, view=view)

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

        embed = discord.Embed(
            title=f"?? Sovereignty Acquired: {c['flag']} {c['name']}",
            description=desc_claim,
            color=0x10B981
        )
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open 3D Command Deck", url=WEB_URL, style=discord.ButtonStyle.link, emoji="??"))
        await interaction.followup.send(embed=embed, view=view)


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

    @earth_group.command(name="sweep", description="Run a Counter-Intelligence Security Sweep to detect spies and review detained operatives.")
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
            embed.add_field(name="Detained Prisoners of War", value="\n".join(lines) + "\n*Use `/earth interrogate <id>` or the website to question them.*", inline=False)

        await interaction.followup.send(embed=embed)

    @earth_group.command(name="interrogate", description="Interrogate a captured foreign spy held in military custody.")
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

    @earth_group.command(name="execute", description="Execute a convicted foreign spy held in custody.")
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


    @earth_group.command(name="train_spy", description="Enroll an operative in the National Intelligence Academy to rank up.")
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

    @earth_group.command(name="buy_intel", description="Purchase classified foreign intelligence dossiers from intelligence brokers.")
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

    @earth_group.command(name="un_status", description="View United Nations (UN) Secretary-General status and active global sanctions.")
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

    @earth_group.command(name="un_ceasefire", description="[Mayor / UN] Enforce an immediate binding UN Ceasefire decree halting an active war.")
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

    @earth_group.command(name="un_sanction", description="[Mayor / UN] Impose international trade embargo and warfare sanctions on a rogue country.")
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

    @earth_group.command(name="un_aid", description="[Mayor / UN] Disburse 50,000 Medals in UN emergency relief to quell riots and rebuild stability.")
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


async def setup(bot: commands.Bot):
    await bot.add_cog(EarthCog(bot))
