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
