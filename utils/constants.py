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
