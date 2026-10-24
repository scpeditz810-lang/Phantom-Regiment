"""
All configurable values for the Command an Army bot.
Role definitions, channel layout, XP formula, in-game role requirements.
"""

import discord

# ─── XP & Leveling ─────────────────────────────────────────────────────────────
XP_PER_MESSAGE = (15, 25)  # Random range per qualifying message
XP_COOLDOWN = 60           # Seconds between XP gains

def xp_for_level(level: int) -> int:
    """XP required to advance FROM the given level to the next."""
    return 300 * (level + 1)


# ─── Level Roles (auto-assigned purely by XP level) ────────────────────────────
LEVEL_ROLES = [
    {"name": "Recruit",    "level": 0,  "color": 0x95A5A6},
    {"name": "Private",    "level": 5,  "color": 0x4D96FF},
    {"name": "Corporal",   "level": 10, "color": 0x6BCB77},
    {"name": "Sergeant",   "level": 15, "color": 0xFFD93D},
    {"name": "Lieutenant", "level": 20, "color": 0xFCBAD3},
    {"name": "Captain",    "level": 25, "color": 0xAA96DA},
    {"name": "Major",      "level": 30, "color": 0xA8D8EA},
    {"name": "Colonel",    "level": 35, "color": 0xC0C0C0},
]


# ─── In-Game Roles (require ONLY wins) ─────────────────────────────────────────
IN_GAME_ROLES = [
    {"name": "Rookie",       "wins": 120, "color": 0x57F287},
    {"name": "Veteran",      "wins": 160, "color": 0x3498DB},
    {"name": "Experienced",  "wins": 230, "color": 0x9B59B6},
    {"name": "Elite",        "wins": 310, "color": 0xFF8C00},
    {"name": "Legend",       "wins": 400, "color": 0xFFD700},
]


# ─── Commander Role ────────────────────────────────────────────────────────────
COMMANDER_ROLE = {
    "name": "Commander",
    "color": 0xDAA520,
    "permissions": discord.Permissions.none(),
}


# ─── Staff Roles (ascending order of power) ────────────────────────────────────
STAFF_ROLES = [
    {
        "name": "Trial Mod",
        "color": 0x3498DB,
        "permissions": discord.Permissions(
            moderate_members=True,
            manage_messages=True,
        ),
    },
    {
        "name": "Moderator",
        "color": 0x2ECC71,
        "permissions": discord.Permissions(
            moderate_members=True,
            manage_messages=True,
        ),
    },
    {
        "name": "Senior Mod",
        "color": 0xF1C40F,
        "permissions": discord.Permissions(
            moderate_members=True,
            manage_messages=True,
            ban_members=True,
            kick_members=True,
        ),
    },
    {
        "name": "Admin",
        "color": 0xE67E22,
        "permissions": discord.Permissions(
            moderate_members=True,
            manage_messages=True,
            ban_members=True,
            kick_members=True,
            manage_channels=True,
            manage_roles=True,
        ),
    },
    {
        "name": "Server Manager",
        "color": 0xE74C3C,
        "permissions": discord.Permissions.all(),
    },
]

# ─── Management Roles (between Commander and Staff) ────────────────────────────
MANAGEMENT_ROLES = [
    {"name": "Recruitment",                "color": 0x1ABC9C, "permissions": discord.Permissions.none()},
    {"name": "Events/Giveaway Management", "color": 0xE91E63, "permissions": discord.Permissions.none()},
    {"name": "Head of Recruitment",        "color": 0x00BCD4, "permissions": discord.Permissions.none()},
]


# Interleave Level Roles and In-Game Roles as requested
INTERLEAVED_ROLES = []
for i in range(max(len(LEVEL_ROLES), len(IN_GAME_ROLES))):
    if i < len(LEVEL_ROLES):
        INTERLEAVED_ROLES.append(LEVEL_ROLES[i])
    if i < len(IN_GAME_ROLES):
        INTERLEAVED_ROLES.append(IN_GAME_ROLES[i])

# Full hierarchy bottom → top  (creation order for proper positioning)
ROLE_HIERARCHY = (
    [
        {"name": "Unverified", "color": 0x2C2F33, "permissions": discord.Permissions.none()},
        {"name": "Member",     "color": 0x99AAB5, "permissions": discord.Permissions.none()},
    ]
    + INTERLEAVED_ROLES
    + MANAGEMENT_ROLES
    + [COMMANDER_ROLE]
    + STAFF_ROLES
)


# ─── Channels ──────────────────────────────────────────────────────────────────
# member_visible  → Member role can view (all non-staff categories)
# unverified_visible (per channel) → Unverified role can view this channel
CHANNELS = {
    "📁 │ MAIN": {
        "member_visible": True,
        "channels": [
            {"name": "📜│rules",         "type": "text", "readonly": True, "unverified_visible": True},
            {"name": "📢│announcements", "type": "news", "staff_only_send": True, "unverified_visible": True},
            {"name": "📰│side-news",     "type": "text", "staff_only_send": True},
            {"name": "❓│faq",           "type": "text", "readonly": True},
            {"name": "ℹ️│info",          "type": "text", "readonly": True},
            {"name": "🎮│gamenight",     "type": "text"},
        ],
    },
    "💬 │ GENERAL": {
        "member_visible": True,
        "channels": [
            {"name": "💬│general",       "type": "text"},
            {"name": "📷│media",         "type": "text"},
            {"name": "🤖│cmds",          "type": "text"},
        ],
    },
    "🛡️ │ CAA ( Command an Army )": {
        "member_visible": True,
        "channels": [
            {"name": "👥│lfg-team",      "type": "text"},
            {"name": "🧠│strategy",      "type": "text"},
        ],
    },
    "👑 │ STAFF": {
        "staff_only": True,
        "channels": [
            {"name": "📋│app-review",       "type": "text", "extra_roles": ["Commander"]},
            {"name": "🏆│win-verification", "type": "text", "extra_roles": ["Commander"]},
            {"name": "🔒│moderator-only",   "type": "text"},
            {"name": "📓│mod-log",          "type": "text"},
            {"name": "🗣️│staff-chat",       "type": "text"},
            {"name": "🛠️│staff-cmds",       "type": "text"},
        ],
    },
    "📊 │ LEVEL SYSTEM": {
        "member_visible": True,
        "channels": [
            {"name": "🎉│level-up",        "type": "text"},
            {"name": "📚│level-up-guides", "type": "text", "readonly": True},
        ],
    },
}


# ─── Rank Card Rendering ──────────────────────────────────────────────────────
CARD_WIDTH = 934
CARD_HEIGHT = 282
ACCENT_GOLD = (255, 215, 0)
XP_BAR_BG = (60, 60, 60)
XP_BAR_FILL = (255, 215, 0)


# ─── Application ──────────────────────────────────────────────────────────────
APPEAL_COOLDOWN_SECONDS = 5 * 60 * 60   # 5 hours
ACCEPTED_ROLE = "Rookie"                  # Role given on application acceptance

# ─── Role Shop ────────────────────────────────────────────────────────────────
ROLES_SHOP = {
    "role_wealthy": {"name": "💰 Wealthy", "color": 0x2ECC71, "price": 5000},
    "role_rich": {"name": "💸 Rich", "color": 0xF1C40F, "price": 10000},
    "role_investor": {"name": "📈 High Roller", "color": 0x3498DB, "price": 15000},
    "role_millionaire": {"name": "💎 Millionaire", "color": 0x9B59B6, "price": 25000},
    "role_billionaire": {"name": "👑 Billionaire", "color": 0xE74C3C, "price": 50000},
    "role_phantom": {"name": "👻 Phantom Regiment Elite", "color": 0x111111, "price": 100000},
}



# ─── Bank Vault Tiers ─────────────────────────────────────────────────────────

BANK_TIERS = {

    1: {"name": "Basic Vault", "cap": 1000, "upgrade_cost": 0},

    2: {"name": "Iron Vault", "cap": 2500, "upgrade_cost": 2500},

    3: {"name": "Steel Vault", "cap": 7500, "upgrade_cost": 7500},

    4: {"name": "Reinforced Vault", "cap": 20000, "upgrade_cost": 20000},

    5: {"name": "Titanium Vault", "cap": 50000, "upgrade_cost": 50000},

    6: {"name": "Obsidian Vault", "cap": 100000, "upgrade_cost": 120000},

    7: {"name": "Quantum Vault", "cap": 250000, "upgrade_cost": 250000},

    8: {"name": "Cybernetic Vault", "cap": 500000, "upgrade_cost": 500000},

    9: {"name": "Apex Vault", "cap": 750000, "upgrade_cost": 1000000},

    10: {"name": "Phantom Sovereign Vault", "cap": 1000000, "upgrade_cost": 2000000},

}



# ─── E-State Virtual Real Estate & Tycoon ──────────────────────────────────────
MAX_ESTATE_PLOTS_PER_USER = 6

ESTATE_BUILDINGS = {
    "factory": {
        "key": "factory",
        "name": "Factory",
        "emoji": "🏭",
        "desc": "Heavy industrial manufacturing producing consistent medal revenue.",
        "cost_pct": 0.25,     # 25% of base price
        "val_boost": 0.25,    # +25% valuation boost
        "daily_yield": 0.020, # 2.0% daily passive yield in medals
        "growth_mult": 1.2,   # +20% faster land value appreciation
    },
    "hospital": {
        "key": "hospital",
        "name": "Hospital",
        "emoji": "🏥",
        "desc": "Public health sanctuary generating stable community dividends and safety.",
        "cost_pct": 0.30,     # 30% of base price
        "val_boost": 0.30,    # +30% valuation boost
        "daily_yield": 0.022, # 2.2% daily passive yield
        "growth_mult": 1.3,
    },
    "construction": {
        "key": "construction",
        "name": "Construction Site",
        "emoji": "🏗️",
        "desc": "Rapid infrastructure development maximizing land growth rate.",
        "cost_pct": 0.20,     # 20% of base price
        "val_boost": 0.20,    # +20% valuation boost
        "daily_yield": 0.010, # 1.0% daily yield
        "growth_mult": 2.5,   # 2.5x growth rate boost!
    },
    "bunker": {
        "key": "bunker",
        "name": "Bunker",
        "emoji": "🛡️",
        "desc": "Subterranean stronghold shielding plot valuation and providing defense.",
        "cost_pct": 0.35,     # 35% of base price
        "val_boost": 0.35,    # +35% valuation boost
        "daily_yield": 0.015, # 1.5% daily yield
        "growth_mult": 1.1,
    },
    "military": {
        "key": "military",
        "name": "Military Base",
        "emoji": "🪖",
        "desc": "Regiment forward operations outpost with high tactical authority stipends.",
        "cost_pct": 0.45,     # 45% of base price
        "val_boost": 0.45,    # +45% valuation boost
        "daily_yield": 0.028, # 2.8% daily yield
        "growth_mult": 1.4,
    },
    "bank": {
        "key": "bank",
        "name": "Bank",
        "emoji": "🏦",
        "desc": "Central commercial branch producing top-tier financial dividend yields.",
        "cost_pct": 0.50,     # 50% of base price
        "val_boost": 0.60,    # +60% valuation boost
        "daily_yield": 0.035, # 3.5% daily yield
        "growth_mult": 1.5,
    },
    "oil_rig": {
        "key": "oil_rig",
        "name": "Offshore Oil Rig",
        "emoji": "🛢️",
        "desc": "Deepwater petroleum extraction rig generating immense crude oil dividend yields.",
        "cost_pct": 0.60,     # 60% of base price
        "val_boost": 0.70,    # +70% valuation boost
        "daily_yield": 0.040, # 4.0% daily passive yield (Highest in city!)
        "growth_mult": 1.6,
    }
}

DEFAULT_ESTATE_PLOTS = [
    # Row 1 (Outer Greenery - 10k to 50k)
    {"id": 1, "x": 1, "y": 1, "name": "Verdant Outpost Alpha", "district": "The Outskirts", "terrain": "plains", "price": 10000},
    {"id": 2, "x": 1, "y": 2, "name": "Pinecrest Glade", "district": "The Outskirts", "terrain": "forest", "price": 15000},
    {"id": 3, "x": 1, "y": 3, "name": "Whispering Woods", "district": "The Outskirts", "terrain": "forest", "price": 20000},
    {"id": 4, "x": 1, "y": 4, "name": "Mossy Ridge", "district": "The Outskirts", "terrain": "plains", "price": 25000},
    {"id": 5, "x": 1, "y": 5, "name": "Wildflower Meadow", "district": "The Outskirts", "terrain": "plains", "price": 35000},
    {"id": 6, "x": 1, "y": 6, "name": "Evergreen Foothills", "district": "The Outskirts", "terrain": "forest", "price": 50000},
    # Row 2 (Greenery into Riverfront - 12k to 110k)
    {"id": 7, "x": 2, "y": 1, "name": "Sunlit Orchard", "district": "The Outskirts", "terrain": "plains", "price": 12000},
    {"id": 8, "x": 2, "y": 2, "name": "Clover Basin", "district": "The Outskirts", "terrain": "plains", "price": 18000},
    {"id": 9, "x": 2, "y": 3, "name": "Riverbend Crossing", "district": "Riverside Commons", "terrain": "riverfront", "price": 75000},
    {"id": 10, "x": 2, "y": 4, "name": "Azure Basin East", "district": "Riverside Commons", "terrain": "riverfront", "price": 90000},
    {"id": 11, "x": 2, "y": 5, "name": "Silverwater Bay", "district": "Riverside Commons", "terrain": "riverfront", "price": 110000},
    {"id": 12, "x": 2, "y": 6, "name": "Old Mill Copse", "district": "The Outskirts", "terrain": "forest", "price": 45000},
    # Row 3 (Riverfront & High Bastion - 125k to 2M)
    {"id": 13, "x": 3, "y": 1, "name": "Twin Bridges Marina", "district": "Riverside Commons", "terrain": "riverfront", "price": 125000},
    {"id": 14, "x": 3, "y": 2, "name": "Delta Wharf", "district": "Riverside Commons", "terrain": "riverfront", "price": 150000},
    {"id": 15, "x": 3, "y": 3, "name": "Highland Bastion", "district": "Shadow Citadel", "terrain": "citadel", "price": 2000000},
    {"id": 16, "x": 3, "y": 4, "name": "Imperial Garrison Reserve", "district": "Shadow Citadel", "terrain": "citadel", "price": 3000000},
    {"id": 17, "x": 3, "y": 5, "name": "Apex Foundry Plot", "district": "Ironworks District", "terrain": "industrial", "price": 350000},
    {"id": 18, "x": 3, "y": 6, "name": "Fisherman's Reach", "district": "Riverside Commons", "terrain": "riverfront", "price": 180000},
    # Row 4 (Riverfront, Citadel Core & Industrial - 200k to 6M)
    {"id": 19, "x": 4, "y": 1, "name": "Riverbank Commons", "district": "Riverside Commons", "terrain": "riverfront", "price": 200000},
    {"id": 20, "x": 4, "y": 2, "name": "Heron's Lagoon", "district": "Riverside Commons", "terrain": "riverfront", "price": 250000},
    {"id": 21, "x": 4, "y": 3, "name": "Crown Plaza Central", "district": "Shadow Citadel", "terrain": "citadel", "price": 4500000},
    {"id": 22, "x": 4, "y": 4, "name": "Obsidian Boulevard", "district": "Shadow Citadel", "terrain": "citadel", "price": 6000000},
    {"id": 23, "x": 4, "y": 5, "name": "Cybernetic Depot", "district": "Ironworks District", "terrain": "industrial", "price": 450000},
    {"id": 24, "x": 4, "y": 6, "name": "Titan Machine Works", "district": "Ironworks District", "terrain": "industrial", "price": 600000},
    # Row 5 (Industrial & Citadel Peak - 750k to 10M)
    {"id": 25, "x": 5, "y": 1, "name": "Vanguard Tech Yard", "district": "Ironworks District", "terrain": "industrial", "price": 750000},
    {"id": 26, "x": 5, "y": 2, "name": "Ironclad Terminal", "district": "Ironworks District", "terrain": "industrial", "price": 850000},
    {"id": 27, "x": 5, "y": 3, "name": "Grand Regent Spire", "district": "Shadow Citadel", "terrain": "citadel", "price": 7500000},
    {"id": 28, "x": 5, "y": 4, "name": "Sovereign Apex Plaza", "district": "Shadow Citadel", "terrain": "citadel", "price": 8500000},
    {"id": 29, "x": 5, "y": 5, "name": "Citadel Supreme Monolith", "district": "Shadow Citadel", "terrain": "citadel", "price": 10000000},
    {"id": 30, "x": 5, "y": 6, "name": "Silicon Valley Lot", "district": "Ironworks District", "terrain": "industrial", "price": 1000000},
    # Row 6 (Highlands & Faction Peak - 1.25M to 10M)
    {"id": 31, "x": 6, "y": 1, "name": "Reactor Point", "district": "Ironworks District", "terrain": "industrial", "price": 1250000},
    {"id": 32, "x": 6, "y": 2, "name": "Overlook Ridge", "district": "Highland Outpost", "terrain": "highlands", "price": 1500000},
    {"id": 33, "x": 6, "y": 3, "name": "Paladin Enclave", "district": "Shadow Citadel", "terrain": "citadel", "price": 2500000},
    {"id": 34, "x": 6, "y": 4, "name": "Monarch Square", "district": "Shadow Citadel", "terrain": "citadel", "price": 5000000},
    {"id": 35, "x": 6, "y": 5, "name": "Phantom Vanguard Keep", "district": "Shadow Citadel", "terrain": "citadel", "price": 8000000},
    {"id": 36, "x": 6, "y": 6, "name": "Zenith Citadel Peak", "district": "Shadow Citadel", "terrain": "citadel", "price": 10000000},
    # Row 7 (Deepwater Basin & Offshore Waters - 150k to 3.5M)
    {"id": 37, "x": 7, "y": 1, "name": "Deepwater Platform Alpha", "district": "Deepwater Basin", "terrain": "ocean", "price": 150000},
    {"id": 38, "x": 7, "y": 2, "name": "Neptune Crude Rig", "district": "Deepwater Basin", "terrain": "ocean", "price": 220000},
    {"id": 39, "x": 7, "y": 3, "name": "Kraken Offshore Station", "district": "Deepwater Basin", "terrain": "ocean", "price": 300000},
    {"id": 40, "x": 7, "y": 4, "name": "Black Gold Shoals", "district": "Deepwater Basin", "terrain": "ocean", "price": 380000},
    {"id": 41, "x": 7, "y": 5, "name": "Poseidon Drilling Array", "district": "Deepwater Basin", "terrain": "ocean", "price": 450000},
    {"id": 42, "x": 7, "y": 6, "name": "Leviathan Extraction Deck", "district": "Deepwater Basin", "terrain": "ocean", "price": 600000},
    # Row 8 (Deepwater Apex Zone - 750k to 3.5M)
    {"id": 43, "x": 8, "y": 1, "name": "Abyssal Reef Station", "district": "Deepwater Basin", "terrain": "ocean", "price": 750000},
    {"id": 44, "x": 8, "y": 2, "name": "Triton Marine Facility", "district": "Deepwater Basin", "terrain": "ocean", "price": 900000},
    {"id": 45, "x": 8, "y": 3, "name": "Oceanic Refinery Platform", "district": "Deepwater Basin", "terrain": "ocean", "price": 1200000},
    {"id": 46, "x": 8, "y": 4, "name": "Atlantic Apex Rig", "district": "Deepwater Basin", "terrain": "ocean", "price": 1500000},
    {"id": 47, "x": 8, "y": 5, "name": "Sovereign Deepwater Spire", "district": "Deepwater Basin", "terrain": "ocean", "price": 2000000},
    {"id": 48, "x": 8, "y": 6, "name": "Grand Leviathan Rig 01", "district": "Deepwater Basin", "terrain": "ocean", "price": 3500000},
]


# ===============================================================================
# 🌍 VIRTUAL EARTH: 3D GLOBAL GEOPOLITICS SIMULATION CONSTANTS
# ===============================================================================

EARTH_CABINET_ROLES = {
    "defense": {
        "key": "defense",
        "title": "Minister of Defense and Supreme Army Commander",
        "short_title": "Army Commander",
        "emoji": "⚔️",
        "desc": "Commands national armed divisions, fortifies military defenses, deploys troops and directs conquests.",
        "icon": "shield-halved"
    },
    "diplomat": {
        "key": "diplomat",
        "title": "Chief Diplomat and Minister of Foreign Affairs",
        "short_title": "Chief Diplomat",
        "emoji": "📜",
        "desc": "Negotiates international treaties, forms custom sovereign coalitions, and signs ocean trade routes.",
        "icon": "handshake"
    },
    "economy": {
        "key": "economy",
        "title": "Minister of Economy and National Treasury",
        "short_title": "Finance Minister",
        "emoji": "🏦",
        "desc": "Directs domestic infrastructure development (schools, hospitals, mines, oil rigs) and tax policy.",
        "icon": "coins"
    },
    "intelligence": {
        "key": "intelligence",
        "title": "Director of Secret Intelligence and Espionage",
        "short_title": "Spy Chief",
        "emoji": "🕵️",
        "desc": "Recruits covert field operatives, coordinates espionage operations, and monitors foreign state secrets.",
        "icon": "user-secret"
    }
}

EARTH_BUILDINGS = {
    "school": {
        "key": "school",
        "name": "Public School and University Campus",
        "emoji": "🏫",
        "desc": "Educates citizens, boosting national technological output, civic harmony, and sovereign stability.",
        "base_cost": 100000,
        "cost_multiplier": 1.5,
        "stability_bonus": 6,
        "unrest_reduction": 5,
        "hourly_yield": 2500,
        "military_power": 0,
        "defense_power": 0
    },
    "hospital": {
        "key": "hospital",
        "name": "Regional Hospital and Medical Complex",
        "emoji": "🏥",
        "desc": "Provides universal medical infrastructure, drastically lowering citizen unrest, disease, and mortality.",
        "base_cost": 150000,
        "cost_multiplier": 1.5,
        "stability_bonus": 8,
        "unrest_reduction": 12,
        "hourly_yield": 3000,
        "military_power": 0,
        "defense_power": 0
    },
    "gold_mine": {
        "key": "gold_mine",
        "name": "Sovereign Gold and Mineral Mine",
        "emoji": "⛏️",
        "desc": "Deep subterranean extraction shafts mining precious metals directly into the national treasury.",
        "base_cost": 250000,
        "cost_multiplier": 1.6,
        "stability_bonus": 0,
        "unrest_reduction": 0,
        "hourly_yield": 8500,
        "military_power": 0,
        "defense_power": 0
    },
    "oil_rig": {
        "key": "oil_rig",
        "name": "Offshore and Inland Petroleum Rig",
        "emoji": "🛢️",
        "desc": "Extracts high-grade crude petroleum for massive commercial export revenues and strategic sovereignty.",
        "base_cost": 450000,
        "cost_multiplier": 1.7,
        "stability_bonus": 0,
        "unrest_reduction": 0,
        "hourly_yield": 16000,
        "military_power": 0,
        "defense_power": 0
    },
    "heavy_factory": {
        "key": "heavy_factory",
        "name": "Heavy Industrial Complex and Yard",
        "emoji": "🏭",
        "desc": "Mass-produces mechanized armor, steel armaments, and accelerates national construction projects.",
        "base_cost": 350000,
        "cost_multiplier": 1.6,
        "stability_bonus": 2,
        "unrest_reduction": 0,
        "hourly_yield": 7000,
        "military_power": 25,
        "defense_power": 15
    },
    "bunker": {
        "key": "bunker",
        "name": "Fortified Citadel Bunker and SAM Array",
        "emoji": "🏰",
        "desc": "Reinforced underground command bastion with surface-to-air missile defenses against foreign invasions.",
        "base_cost": 300000,
        "cost_multiplier": 1.5,
        "stability_bonus": 4,
        "unrest_reduction": 3,
        "hourly_yield": 2000,
        "military_power": 10,
        "defense_power": 65
    },
    "naval_port": {
        "key": "naval_port",
        "name": "Deepwater Commercial and Naval Port",
        "emoji": "⚓",
        "desc": "World-class container port required to inaugurate high-yield bilateral Ocean Trade Routes across the seas.",
        "base_cost": 400000,
        "cost_multiplier": 1.6,
        "stability_bonus": 3,
        "unrest_reduction": 0,
        "hourly_yield": 12000,
        "military_power": 15,
        "defense_power": 25
    }
}

EARTH_WAR_SCALES = {
    "border": {
        "key": "border",
        "name": "Border Skirmish",
        "emoji": "⚔️",
        "duration_hours": 24,
        "duration_seconds": 86400,
        "desc": "Tactical skirmish along national frontier. Low risk, fast resolution.",
        "treasury_plunder_pct": 0.15,
        "min_divisions": 5,
        "reparations": 100000
    },
    "annexation": {
        "key": "annexation",
        "name": "Strategic Annexation Campaign",
        "emoji": "🚩",
        "duration_hours": 72,
        "duration_seconds": 259200,
        "desc": "Large-scale strategic campaign to seize key resource nodes and cripple enemy defenses.",
        "treasury_plunder_pct": 0.40,
        "min_divisions": 15,
        "reparations": 500000
    },
    "world_war": {
        "key": "world_war",
        "name": "Total Sovereign Conquest",
        "emoji": "💥",
        "duration_hours": 120,
        "duration_seconds": 432000,
        "desc": "All-out existential war spanning five full days! Devastates target nation, seizing 75% treasury.",
        "treasury_plunder_pct": 0.75,
        "min_divisions": 30,
        "reparations": 1500000
    }
}

EARTH_SPY_MISSIONS = {
    "intel": {
        "key": "intel",
        "name": "Infiltrate and Gather Intelligence",
        "emoji": "🛰️",
        "desc": "Infiltrate government ministries to uncover hidden army strength, treasury funds, and active war orders.",
        "duration_seconds": 1800,
        "capture_risk": 0.20
    },
    "sabotage": {
        "key": "sabotage",
        "name": "Covert Infrastructure Sabotage",
        "emoji": "💣",
        "desc": "Detonate tactical charges on rival gold mines, oil rigs, or factories to paralyze revenue for 12 hours.",
        "duration_seconds": 3600,
        "capture_risk": 0.35
    },
    "incite_riot": {
        "key": "incite_riot",
        "name": "Fund Dissidents and Incite Riots",
        "emoji": "🔥",
        "desc": "Fund radical dissident groups to spike target nation unrest by +25%, driving them toward revolution!",
        "duration_seconds": 5400,
        "capture_risk": 0.40
    }
}

EARTH_DOCTRINES = {
    "economic": {
        "free_market": {
            "name": "Free Market Capitalism",
            "desc": "+25% trade route and resource yield, +5% unrest volatility.",
            "yield_mult": 1.25,
            "unrest_delta": 5
        },
        "mixed": {
            "name": "Mixed Social Welfare",
            "desc": "Balanced economic model. +10% yield, +5% stability bonus.",
            "yield_mult": 1.10,
            "unrest_delta": -5
        },
        "command": {
            "name": "State Command Economy",
            "desc": "+25% military division production, -10% trade tariff revenue.",
            "yield_mult": 0.90,
            "unrest_delta": 0
        }
    },
    "military": {
        "volunteer": {
            "name": "Professional Standing Army",
            "desc": "+15% division combat efficiency and discipline. Low civil strain.",
            "power_mult": 1.15,
            "unrest_delta": 0
        },
        "conscription": {
            "name": "Universal Military Conscription",
            "desc": "+40% total military division numbers, but +10% citizen unrest.",
            "power_mult": 1.40,
            "unrest_delta": 10
        },
        "mechanized": {
            "name": "Advanced Mechanized Armor",
            "desc": "+60% assault power in conquests, requires 5,000 Medals/hr equipment upkeep.",
            "power_mult": 1.60,
            "unrest_delta": 0
        }
    },
    "diplomatic": {
        "neutral": {
            "name": "Non-Aligned Neutrality",
            "desc": "Standard diplomatic relations with all global sovereign powers."
        },
        "interventionist": {
            "name": "Global Interventionism",
            "desc": "Can intervene directly to defend allied coalition members in multi-day conquests."
        },
        "isolationist": {
            "name": "Sovereign Isolationism",
            "desc": "Immune to foreign spy incitement. Cannot sign ocean trade routes."
        }
    }
}

EARTH_COUNTRIES = [
    {
        "id": 1,
        "code": "RUS",
        "name": "Russian Federation",
        "flag": "🇷🇺",
        "lat": 61.5240,
        "lng": 105.3188,
        "gdp": 120000000,
        "is_coastal": 1,
        "initial_owner_id": 429350468796416013,
        "desc": "Vast transcontinental Eurasian superpower with massive mineral wealth and formidable armed forces.",
        "capital": "Moscow"
    },
    {
        "id": 2,
        "code": "IND",
        "name": "Republic of India",
        "flag": "🇮🇳",
        "lat": 20.5937,
        "lng": 78.9629,
        "gdp": 110000000,
        "is_coastal": 1,
        "initial_owner_id": 828513350883213342,
        "desc": "Rapidly surging democratic giant and economic titan with extensive Indian Ocean maritime trade lanes.",
        "capital": "New Delhi"
    },
    {
        "id": 3,
        "code": "USA",
        "name": "United States of America",
        "flag": "🇺🇸",
        "lat": 37.0902,
        "lng": -95.7129,
        "gdp": 135000000,
        "is_coastal": 1,
        "initial_owner_id": 1134511531468525589,
        "desc": "Preeminent global financial and naval powerhouse with multi-ocean carrier fleets.",
        "capital": "Washington, D.C."
    },
    {
        "id": 4,
        "code": "CHN",
        "name": "People's Republic of China",
        "flag": "🇨🇳",
        "lat": 35.8617,
        "lng": 104.1954,
        "gdp": 125000000,
        "is_coastal": 1,
        "initial_owner_id": 1291083270426988544,
        "desc": "Global manufacturing juggernaut with sprawling technological and industrial infrastructure.",
        "capital": "Beijing"
    },
    {
        "id": 5,
        "code": "GBR",
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "lat": 55.3781,
        "lng": -3.4360,
        "gdp": 85000000,
        "is_coastal": 1,
        "initial_owner_id": 1486122404102013050,
        "desc": "Historic maritime empire and global financial capital with elite intelligence networks.",
        "capital": "London"
    },
    {
        "id": 6,
        "code": "DEU",
        "name": "Federal Republic of Germany",
        "flag": "🇩🇪",
        "lat": 51.1657,
        "lng": 10.4515,
        "gdp": 80000000,
        "is_coastal": 1,
        "initial_owner_id": 1280141055265865732,
        "desc": "Industrial and technological powerhouse at the core of European continental trade.",
        "capital": "Berlin"
    },
    {
        "id": 7,
        "code": "JPN",
        "name": "State of Japan",
        "flag": "🇯🇵",
        "lat": 36.2048,
        "lng": 138.2529,
        "gdp": 75000000,
        "is_coastal": 1,
        "initial_owner_id": 1162404296097275904,
        "desc": "High-tech archipelago possessing advanced robotics, naval fleets, and dense mega-cities.",
        "capital": "Tokyo"
    },
    {
        "id": 8,
        "code": "FRA",
        "name": "French Republic",
        "flag": "🇫🇷",
        "lat": 46.2276,
        "lng": 2.2137,
        "gdp": 70000000,
        "is_coastal": 1,
        "initial_owner_id": 1370437656755834970,
        "desc": "Sovereign European diplomatic hub with formidable aerospace, nuclear energy, and cultural influence.",
        "capital": "Paris"
    },
    {
        "id": 9,
        "code": "BRA",
        "name": "Federative Republic of Brazil",
        "flag": "🇧🇷",
        "lat": -14.2350,
        "lng": -51.9253,
        "gdp": 60000000,
        "is_coastal": 1,
        "initial_owner_id": 1248327898901774356,
        "desc": "Dominant South American giant blessed with immense agricultural and natural resource reserves.",
        "capital": "Brasília"
    },
    {
        "id": 10,
        "code": "CAN",
        "name": "Dominion of Canada",
        "flag": "🇨🇦",
        "lat": 56.1304,
        "lng": -106.3468,
        "gdp": 55000000,
        "is_coastal": 1,
        "initial_owner_id": 829919098506444820,
        "desc": "Northern realm of immense oil sands, mineral wealth, and extensive Arctic coastlines.",
        "capital": "Ottawa"
    },
    {
        "id": 11,
        "code": "AUS",
        "name": "Commonwealth of Australia",
        "flag": "🇦🇺",
        "lat": -25.2744,
        "lng": 133.7751,
        "gdp": 50000000,
        "is_coastal": 1,
        "initial_owner_id": 1327273793650950216,
        "desc": "Island continent endowed with rich mineral deposits and strategic Indo-Pacific naval ports.",
        "capital": "Canberra"
    },
    {
        "id": 12,
        "code": "ITA",
        "name": "Italian Republic",
        "flag": "🇮🇹",
        "lat": 41.8719,
        "lng": 12.5674,
        "gdp": 45000000,
        "is_coastal": 1,
        "initial_owner_id": 1423907121229074452,
        "desc": "Mediterranean maritime hub boasting high-precision manufacturing and ancient cultural prestige.",
        "capital": "Rome"
    },
    {
        "id": 13,
        "code": "SAU",
        "name": "Kingdom of Saudi Arabia",
        "flag": "🇸🇦",
        "lat": 23.8859,
        "lng": 45.0792,
        "gdp": 40000000,
        "is_coastal": 1,
        "initial_owner_id": 1119603544635482163,
        "desc": "Global energy titan with massive petroleum sovereign wealth reserves and ambitious megaprojects.",
        "capital": "Riyadh"
    },
    {
        "id": 14,
        "code": "KOR",
        "name": "Republic of Korea",
        "flag": "🇰🇷",
        "lat": 35.9078,
        "lng": 127.7669,
        "gdp": 38000000,
        "is_coastal": 1,
        "initial_owner_id": 1289659139659792519,
        "desc": "Technological high-density republic with world-leading semiconductor foundries and defense industries.",
        "capital": "Seoul"
    },
    {
        "id": 15,
        "code": "TUR",
        "name": "Republic of Türkiye",
        "flag": "🇹🇷",
        "lat": 38.9637,
        "lng": 35.2433,
        "gdp": 25000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Geopolitical bridge linking Europe and Asia with control over crucial maritime straits.",
        "capital": "Ankara"
    },
    {
        "id": 16,
        "code": "EGY",
        "name": "Arab Republic of Egypt",
        "flag": "🇪🇬",
        "lat": 26.8206,
        "lng": 30.8025,
        "gdp": 18000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Custodian of the Suez Canal, a vital artery of global international maritime commerce.",
        "capital": "Cairo"
    },
    {
        "id": 17,
        "code": "ZAF",
        "name": "Republic of South Africa",
        "flag": "🇿🇦",
        "lat": -30.5595,
        "lng": 22.9375,
        "gdp": 16000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Mineral-rich nation commanding the strategic Cape maritime shipping routes.",
        "capital": "Pretoria"
    },
    {
        "id": 18,
        "code": "MEX",
        "name": "United Mexican States",
        "flag": "🇲🇽",
        "lat": 23.6345,
        "lng": -102.5528,
        "gdp": 22000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Thriving North American industrial manufacturing hub with access to both the Pacific and Atlantic.",
        "capital": "Mexico City"
    },
    {
        "id": 19,
        "code": "IDN",
        "name": "Republic of Indonesia",
        "flag": "🇮🇩",
        "lat": -0.7893,
        "lng": 113.9213,
        "gdp": 20000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Expansive Southeast Asian archipelago commanding the strategic Malacca shipping choke-points.",
        "capital": "Jakarta"
    },
    {
        "id": 20,
        "code": "ESP",
        "name": "Kingdom of Spain",
        "flag": "🇪🇸",
        "lat": 40.4637,
        "lng": -3.7492,
        "gdp": 24000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Iberian maritime gateway between the Atlantic Ocean and the Mediterranean Sea.",
        "capital": "Madrid"
    },
    {
        "id": 21,
        "code": "ARG",
        "name": "Argentine Republic",
        "flag": "🇦🇷",
        "lat": -38.4161,
        "lng": -63.6167,
        "gdp": 15000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Southern Cone agricultural breadbasket with extensive South Atlantic coastline.",
        "capital": "Buenos Aires"
    },
    {
        "id": 22,
        "code": "UKR",
        "name": "Ukraine",
        "flag": "🇺🇦",
        "lat": 48.3794,
        "lng": 31.1656,
        "gdp": 12000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Resilient Eastern European granary and metallurgy center on the Black Sea coast.",
        "capital": "Kyiv"
    },
    {
        "id": 23,
        "code": "POL",
        "name": "Republic of Poland",
        "flag": "🇵🇱",
        "lat": 51.9194,
        "lng": 19.1451,
        "gdp": 19000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Central European logistics and military bastion with rapid modernization programs.",
        "capital": "Warsaw"
    },
    {
        "id": 24,
        "code": "NOR",
        "name": "Kingdom of Norway",
        "flag": "🇳🇴",
        "lat": 60.4720,
        "lng": 8.4689,
        "gdp": 28000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Nordic oil and gas titan with deep fjords and world's largest sovereign wealth fund.",
        "capital": "Oslo"
    },
    {
        "id": 25,
        "code": "CHE",
        "name": "Swiss Confederation",
        "flag": "🇨🇭",
        "lat": 46.8182,
        "lng": 8.2275,
        "gdp": 30000000,
        "is_coastal": 0,
        "initial_owner_id": None,
        "desc": "Alpine fortress of global neutrality and ultra-secure private financial banking vaults.",
        "capital": "Bern"
    },
    {
        "id": 26,
        "code": "IRN",
        "name": "Islamic Republic of Iran",
        "flag": "🇮🇷",
        "lat": 32.4279,
        "lng": 53.6880,
        "gdp": 17000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Ancient Persian plateau nation commanding the strategic Strait of Hormuz oil routes.",
        "capital": "Tehran"
    },
    {
        "id": 27,
        "code": "PAK",
        "name": "Islamic Republic of Pakistan",
        "flag": "🇵🇰",
        "lat": 30.3753,
        "lng": 69.3451,
        "gdp": 14000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "South Asian military powerhouse with deepwater Arabian Sea ports at Gwadar.",
        "capital": "Islamabad"
    },
    {
        "id": 28,
        "code": "VNM",
        "name": "Socialist Republic of Vietnam",
        "flag": "🇻🇳",
        "lat": 14.0583,
        "lng": 108.2772,
        "gdp": 13000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Fast-growing Indo-Pacific tech manufacturing base with a long tropical maritime coastline.",
        "capital": "Hanoi"
    },
    {
        "id": 29,
        "code": "SGP",
        "name": "Republic of Singapore",
        "flag": "🇸🇬",
        "lat": 1.3521,
        "lng": 103.8198,
        "gdp": 32000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Ultra-wealthy maritime city-state and apex global financial trading capital.",
        "capital": "Singapore"
    },
    {
        "id": 30,
        "code": "NGA",
        "name": "Federal Republic of Nigeria",
        "flag": "🇳🇬",
        "lat": 9.0820,
        "lng": 8.6753,
        "gdp": 11000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Demographic and petroleum powerhouse of West Africa on the Gulf of Guinea.",
        "capital": "Abuja"
    },
    {
        "id": 31,
        "code": "ARE",
        "name": "United Arab Emirates",
        "flag": "🇦🇪",
        "lat": 23.4241,
        "lng": 53.8478,
        "gdp": 35000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Hyper-modern desert oasis of skyscraper luxury, global aviation, and petroleum wealth.",
        "capital": "Abu Dhabi"
    },
    {
        "id": 32,
        "code": "COL",
        "name": "Republic of Colombia",
        "flag": "🇨🇴",
        "lat": 4.5709,
        "lng": -74.2973,
        "gdp": 10000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Equatorial republic touching both the Pacific Ocean and the Caribbean Sea.",
        "capital": "Bogotá"
    },
    {
        "id": 33,
        "code": "CHL",
        "name": "Republic of Chile",
        "flag": "🇨🇱",
        "lat": -35.6751,
        "lng": -71.5430,
        "gdp": 12000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Long Pacific coastal ribbon possessing the world's premier copper and lithium reserves.",
        "capital": "Santiago"
    },
    {
        "id": 34,
        "code": "GRC",
        "name": "Hellenic Republic",
        "flag": "🇬🇷",
        "lat": 39.0742,
        "lng": 21.8243,
        "gdp": 11000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Cradle of Western civilization commanding one of the world's largest merchant cargo fleets.",
        "capital": "Athens"
    },
    {
        "id": 35,
        "code": "SWE",
        "name": "Kingdom of Sweden",
        "flag": "🇸🇪",
        "lat": 60.1282,
        "lng": 18.6435,
        "gdp": 26000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Nordic innovation capital with world-class engineering, defense, and high-tech sectors.",
        "capital": "Stockholm"
    },
    {
        "id": 36,
        "code": "NLD",
        "name": "Kingdom of the Netherlands",
        "flag": "🇳🇱",
        "lat": 52.1326,
        "lng": 5.2913,
        "gdp": 29000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Low-countries commercial juggernaut hosting Rotterdam, the largest maritime port in Europe.",
        "capital": "Amsterdam"
    },
    {
        "id": 37,
        "code": "THA",
        "name": "Kingdom of Thailand",
        "flag": "🇹🇭",
        "lat": 15.8700,
        "lng": 100.9925,
        "gdp": 14000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Southeast Asian economic powerhouse and central automotive/electronics manufacturing center.",
        "capital": "Bangkok"
    },
    {
        "id": 38,
        "code": "PHL",
        "name": "Republic of the Philippines",
        "flag": "🇵🇭",
        "lat": 12.8797,
        "lng": 121.7740,
        "gdp": 12000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Archipelago of over 7,000 islands strategically positioned across western Pacific sealanes.",
        "capital": "Manila"
    },
    {
        "id": 39,
        "code": "NZL",
        "name": "New Zealand",
        "flag": "🇳🇿",
        "lat": -40.9006,
        "lng": 174.8860,
        "gdp": 15000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Isolated South Pacific haven blessed with pristine renewable resources and high civic trust.",
        "capital": "Wellington"
    },
    {
        "id": 40,
        "code": "KEN",
        "name": "Republic of Kenya",
        "flag": "🇰🇪",
        "lat": -0.0236,
        "lng": 37.9062,
        "gdp": 8000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "East African technological 'Silicon Savannah' hub anchored by the port of Mombasa.",
        "capital": "Nairobi"
    },
    {
        "id": 41,
        "code": "MAR",
        "name": "Kingdom of Morocco",
        "flag": "🇲🇦",
        "lat": 31.7917,
        "lng": -7.0926,
        "gdp": 9000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "North African kingdom controlling the world's largest phosphate reserves and Tanger Med port.",
        "capital": "Rabat"
    },
    {
        "id": 42,
        "code": "ISR",
        "name": "State of Israel",
        "flag": "🇮🇱",
        "lat": 31.0461,
        "lng": 34.8516,
        "gdp": 27000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Technological and cyber-defense powerhouse with elite military R&D capabilities.",
        "capital": "Jerusalem"
    },
    {
        "id": 43,
        "code": "DNK",
        "name": "Kingdom of Denmark",
        "flag": "🇩🇰",
        "lat": 55.6761,
        "lng": 12.5683,
        "gdp": 23000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Maritime Nordic nation controlling the Danish straits and high-efficiency wind and green technology grids.",
        "capital": "Copenhagen"
    },
    {
        "id": 44,
        "code": "FIN",
        "name": "Republic of Finland",
        "flag": "🇫🇮",
        "lat": 60.1699,
        "lng": 24.9384,
        "gdp": 21000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "High-tech Nordic republic boasting elite cyber-defense networks and arctic resilience fortresses.",
        "capital": "Helsinki"
    },
    {
        "id": 45,
        "code": "PRT",
        "name": "Portuguese Republic",
        "flag": "🇵🇹",
        "lat": 38.7223,
        "lng": -9.1393,
        "gdp": 19000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Atlantic coastal gateway to Europe, connecting maritime commerce routes across continents.",
        "capital": "Lisbon"
    },
    {
        "id": 46,
        "code": "MYS",
        "name": "Federation of Malaysia",
        "flag": "🇲🇾",
        "lat": 3.1390,
        "lng": 101.6869,
        "gdp": 22000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Southeast Asian economic powerhouse commanding key trade routes along the Strait of Malacca.",
        "capital": "Kuala Lumpur"
    },
    {
        "id": 47,
        "code": "QAT",
        "name": "State of Qatar",
        "flag": "🇶🇦",
        "lat": 25.2854,
        "lng": 51.5310,
        "gdp": 28000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "Resource-wealthy Gulf sovereign state and premier global liquefied natural gas exporter.",
        "capital": "Doha"
    },
    {
        "id": 48,
        "code": "IRL",
        "name": "Republic of Ireland",
        "flag": "🇮🇪",
        "lat": 53.3498,
        "lng": -6.2603,
        "gdp": 25000000,
        "is_coastal": 1,
        "initial_owner_id": None,
        "desc": "European financial and multinational tech hub bridging Atlantic commerce with the Continent.",
        "capital": "Dublin"
    }
]


EARTH_ADVANCED_TOOLS = {
    "sat_recon": {
        "key": "sat_recon",
        "name": "Orbital Reconnaissance Satellite Grid",
        "emoji": "🛰️",
        "category": "intelligence",
        "price": 250000,
        "desc": "High-altitude surveillance satellites providing real-time strategic intelligence on foreign military movements.",
        "military_power": 40,
        "defense_power": 35,
        "hourly_yield": 4000,
        "perk": "+20% Infiltration Stealth & Early Attack Warnings"
    },
    "drone_swarm": {
        "key": "drone_swarm",
        "name": "Autonomous AI Strike Drone Swarm",
        "emoji": "🛸",
        "category": "military",
        "price": 450000,
        "desc": "Armada of low-observable loitering munitions capable of precision strikes against enemy frontline divisions.",
        "military_power": 95,
        "defense_power": 45,
        "hourly_yield": 6000,
        "perk": "Bypasses 25% of Enemy Bunker Fortifications in Wars"
    },
    "iron_dome": {
        "key": "iron_dome",
        "name": "Iron Dome & Aegis Ballistic Shield",
        "emoji": "🛡️",
        "category": "defense",
        "price": 550000,
        "desc": "Multi-tier layered air and missile defense grid intercepting hostile artillery, rockets, and foreign saboteurs.",
        "military_power": 30,
        "defense_power": 130,
        "hourly_yield": 5000,
        "perk": "+130 National Defense Power & -50% Bombardment Damage"
    },
    "cyber_grid": {
        "key": "cyber_grid",
        "name": "Cyber-Warfare & Jamming Citadel",
        "emoji": "⚡",
        "category": "intelligence",
        "price": 380000,
        "desc": "Centralized cyber operations warfare center executing electronic jamming against foreign espionage networks.",
        "military_power": 45,
        "defense_power": 60,
        "hourly_yield": 7500,
        "perk": "+15% Spy Capture Rate & Protects Infrastructure from Sabotage"
    },
    "hypersonic_battery": {
        "key": "hypersonic_battery",
        "name": "Hypersonic Cruise Missile Battery",
        "emoji": "🚀",
        "category": "military",
        "price": 950000,
        "desc": "Mach 8+ glide missile launch batteries designed to neutralize heavy enemy armor formations and command bastions.",
        "military_power": 210,
        "defense_power": 70,
        "hourly_yield": 10000,
        "perk": "Devastating Frontline Offense (+210 Military Power)"
    },
    "tactical_nuke": {
        "key": "tactical_nuke",
        "name": "Tactical Nuclear Deterrence Complex",
        "emoji": "☢️",
        "category": "superweapon",
        "price": 2500000,
        "desc": "Supreme sovereign deterrence silo complex. Hostile invaders face catastrophic retaliation.",
        "military_power": 380,
        "defense_power": 260,
        "hourly_yield": 20000,
        "perk": "Ultimate Sovereign Deterrence (+380 Attack, +260 Defense)"
    },
    "industrial_core": {
        "key": "industrial_core",
        "name": "Automated Mega-Industrial Core",
        "emoji": "🔬",
        "category": "economy",
        "price": 600000,
        "desc": "Robotic super-factories that fast-track national construction, turbocharge GDP, and accelerate dividend production.",
        "military_power": 50,
        "defense_power": 40,
        "hourly_yield": 38000,
        "perk": "Fast-Track Economic Growth (+38k/hr Yield, +15M GDP)"
    }
}
