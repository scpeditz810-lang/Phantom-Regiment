import asyncio
from flask import Blueprint, render_template, session, current_app
from web.auth import login_required, admin_required

views_bp = Blueprint("views", __name__)

def run_async(coro):
    bot = current_app.config.get("DISCORD_BOT")
    if bot and bot.loop and bot.loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        return future.result(timeout=10)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result(timeout=10)
    return asyncio.run(coro)

def get_pr_guild():
    bot = current_app.config.get("DISCORD_BOT")
    if not bot:
        return None
    from web.auth import get_oauth_config
    cfg = get_oauth_config()
    guild = bot.get_guild(cfg["guild_id"])
    if not guild and bot.guilds:
        guild = bot.guilds[0]
    return guild

@views_bp.route("/")
@views_bp.route("/about")
def index():
    guild = get_pr_guild()
    member_count = guild.member_count if guild else 0
    online_count = sum(1 for m in guild.members if m.status.name != "offline") if guild and hasattr(guild, "members") else 0

    return render_template(
        "index.html",
        member_count=member_count,
        online_count=online_count,
        founding_date="18 Sept 2026",
        clan_parent="TS Clan"
    )


SQUADS_METADATA = [
    {
        "id": 0,
        "name": "Frontline",
        "tagline": "Tactical Combat & Fluid Engagements",
        "commander_id": 1319203870681071679,
        "invite_link": "https://discord.gg/7FjWBvJ4hS",
        "emoji": "⚔️",
        "badge": "VERSATILE COMBAT",
        "specialty": "Highly Adaptable Combat",
        "image": "images/frontline.png",
        "role_name": "Frontline",
        "role_id": 1553644926959624273,
        "description": "The Frontline squad is tactically fluid and plays strictly according to the situation. Whether the battle requires an aggressive push, a tactical retreat, or holding a choke point, they are the versatile backbone of the regiment that constantly adapts to overcome any adversary on the battlefield.",
        "strengths": [
            "Choke point fortification & defense",
            "Aggressive shock counter-attacks",
            "Adaptive frontline tactical flexibility",
            "Synergized unit coordination"
        ]
    },
    {
        "id": 1,
        "name": "Los Bluchigis",
        "tagline": "Elite Cavalry & Rapid Flanking",
        "commander_id": 1431779664140959836,
        "invite_link": "https://discord.gg/9Hv5rAaUkz",
        "emoji": "🐎",
        "badge": "CAVALRY MASTERS",
        "specialty": "Elite Cavalry Masters",
        "image": "images/losbluchigis.png",
        "role_name": "Los Bluchigis",
        "role_id": 1553441301863866457,
        "description": "Los Bluchigis consists of elite riders who have mastered every single horse unit in the game. They specialize in devastating cavalry charges, lightning-fast flanking maneuvers, and dominating wide-open battlefields with unmatched velocity and aggressive mobility.",
        "strengths": [
            "High-speed flanking maneuvers",
            "Crushing heavy cavalry shock charges",
            "Rapid harassment & skirmish breakaways",
            "Mastery of all mounted units"
        ]
    },
    {
        "id": 2,
        "name": "Nocturne Pheonix",
        "tagline": "Long-Range Archery & Shield Formations",
        "commander_id": 754264189601710100,
        "invite_link": "https://discord.gg/NrgbGCDEwU",
        "emoji": "🏹",
        "badge": "ARCHERY & DEFENSE",
        "specialty": "Archery & Shield Formations",
        "image": "images/nocturne.png",
        "role_name": "Nocturne Pheonix",
        "role_id": 1553325301784780870,
        "description": "Nocturne Pheonix are the undisputed masters of ranged combat and fortress defensive lines. They specialize in raining down relentless arrow fire from afar, all while protected behind an impenetrable wall of elite shield-holders that no enemy can penetrate.",
        "strengths": [
            "Sustained long-range arrow barrages",
            "Impenetrable heavy shield formations",
            "Strategic defensive zone control",
            "Anti-charge tactical denial"
        ]
    }
]

def get_squads_data(guild, bot, user):
    user_member = None
    if user and guild:
        user_member = guild.get_member(user["id"])

    from web.api import _DISCORD_PROFILES
    squads_list = []
    user_active_squad = None

    for sq in SQUADS_METADATA:
        s = dict(sq)
        member_count = 0
        if guild:
            role = guild.get_role(s["role_id"])
            if not role:
                for r in guild.roles:
                    if r.name.lower() == s["role_name"].lower():
                        role = r
                        break
            if role:
                member_count = len(role.members)

            if user_member and role and role in user_member.roles:
                s["is_user_squad"] = True
                user_active_squad = s["name"]
            else:
                s["is_user_squad"] = False
        else:
            s["is_user_squad"] = False

        s["member_count"] = member_count

        cid = s["commander_id"]
        commander_name = f"Commander {cid}"
        commander_username = f"commander_{str(cid)[-4:]}"
        commander_avatar = f"https://cdn.discordapp.com/embed/avatars/{(cid >> 22) % 6}.png"

        cm = guild.get_member(cid) if guild else None
        if not cm and bot:
            cm = bot.get_user(cid)
        if cm:
            commander_name = cm.global_name or cm.display_name or cm.name
            commander_username = cm.name
            commander_avatar = cm.display_avatar.url
        elif cid in _DISCORD_PROFILES:
            pname, pav = _DISCORD_PROFILES[cid]
            commander_avatar = pav
            if "(@" in pname and pname.endswith(")"):
                parts = pname.rsplit(" (@", 1)
                commander_name = parts[0]
                commander_username = parts[1][:-1]
            else:
                commander_name = pname

        s["commander"] = {
            "id": cid,
            "name": commander_name,
            "username": commander_username,
            "avatar": commander_avatar
        }
        squads_list.append(s)

    return squads_list, user_active_squad

@views_bp.route("/squads")
def squads_page():
    guild = get_pr_guild()
    bot = current_app.config.get("DISCORD_BOT")
    user = session.get("user")
    squads, user_active_squad = get_squads_data(guild, bot, user)

    return render_template(
        "squads.html",
        squads=squads,
        user_active_squad=user_active_squad,
        guild_name=guild.name if guild else "Phantom Regiment"
    )

@views_bp.route("/medals")
def medals_page():
    user = session.get("user")
    user_data = None
    bank_data = None
    tier_info = None
    streak_val = 0
    claimed_today = False

    if user:
        db = current_app.config["DB"]
        uid = user["id"]
        user_data = run_async(db.get_global_economy(uid))
        bank_data = run_async(db.get_bank(uid, 0))
        from utils.constants import BANK_TIERS
        tier = bank_data.get("tier", 1) if bank_data else 1
        tier_info = BANK_TIERS.get(tier, {"name": f"Tier {tier}", "cap": 1000})

        import time
        streak_record = run_async(db.get_streak(uid))
        if streak_record:
            streak_val = streak_record.get("streak", 0)
            last_claim = streak_record.get("last_claim", 0)
            if (time.time() - last_claim) < 86400:
                claimed_today = True
        elif user_data and user_data.get("last_daily"):
            if (time.time() - user_data["last_daily"]) < 86400:
                claimed_today = True

    return render_template(
        "medals.html",
        user=user,
        user_data=user_data,
        bank_data=bank_data,
        tier_info=tier_info,
        streak_val=streak_val,
        claimed_today=claimed_today
    )

@views_bp.route("/members")
def members_page():
    guild = get_pr_guild()
    owner_info = None
    managers = []

    if guild:
        # 1. Server Owner
        owner = guild.owner
        if not owner and guild.owner_id:
            owner = guild.get_member(guild.owner_id)

        if owner:
            owner_info = {
                "id": owner.id,
                "name": owner.display_name,
                "username": owner.name,
                "avatar": owner.display_avatar.url,
                "role": "Server Owner",
                "joined_at": owner.joined_at.strftime("%b %d, %Y") if owner.joined_at else "Founding Member"
            }

        # 2. Server Managers (Scanned automatically from Discord guild members)
        for member in guild.members:
            if owner and member.id == owner.id:
                continue
            if member.bot:
                continue

            is_manager = False
            manager_role_title = "Server Manager"

            # Check role names
            for r in member.roles:
                r_lower = r.name.lower()
                if "server manager" in r_lower:
                    is_manager = True
                    manager_role_title = r.name
                    break
                elif "manager" in r_lower:
                    is_manager = True
                    manager_role_title = r.name

            # Also check Manage Server or Administrator permissions
            if not is_manager:
                perms = member.guild_permissions
                if perms.administrator:
                    is_manager = True
                    manager_role_title = "Administrator"
                elif perms.manage_guild:
                    is_manager = True
                    manager_role_title = "Server Manager"

            if is_manager:
                managers.append({
                    "id": member.id,
                    "name": member.display_name,
                    "username": member.name,
                    "avatar": member.display_avatar.url,
                    "role": manager_role_title,
                    "joined_at": member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Staff Member"
                })

    return render_template(
        "members.html",
        owner=owner_info,
        managers=managers,
        guild_name=guild.name if guild else "Phantom Regiment"
    )

@views_bp.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html")

@views_bp.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html"), 403
