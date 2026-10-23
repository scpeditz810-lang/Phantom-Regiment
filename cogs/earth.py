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

WEB_URL = "https://phantom-regiment-1.onrender.com/estate"


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

        success, msg = await self.bot.db.appoint_earth_cabinet(interaction.user.id, c["id"], role.value, member.id)
        if success:
            embed = discord.Embed(
                title="🏛️ Presidential Decree Issued",
                description=f"**President <@{interaction.user.id}>** has appointed **<@{member.id}>** to the national cabinet!\n\n**Portfolio:** {role.name}\n**Nation:** {c['flag']} {c['name']}",
                color=0xF1C40F
            )
            embed.set_footer(text="Virtual Earth Cabinet • Ministers exercise portfolio authority alongside the President.")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)

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
    ])
    async def earth_build(self, interaction: discord.Interaction, building: app_commands.Choice[str]):
        await interaction.response.defer()
        c = await self.bot.db.get_user_earth_country(interaction.user.id)
        if not c:
            await interaction.followup.send("❌ You do not govern a sovereign nation or hold the Economy portfolio!", ephemeral=True)
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


async def setup(bot: commands.Bot):
    await bot.add_cog(EarthCog(bot))
