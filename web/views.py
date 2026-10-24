import asyncio
from flask import Blueprint, render_template, session, current_app, request, redirect, url_for
from web.auth import login_required, admin_required, mayor_required

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

    db = current_app.config["DB"]
    try:
        stock_tax_pct = int(round(run_async(db.get_stock_tax_rate()) * 100))
    except Exception:
        stock_tax_pct = 15

    return render_template(
        "medals.html",
        user=user,
        user_data=user_data,
        bank_data=bank_data,
        tier_info=tier_info,
        streak_val=streak_val,
        claimed_today=claimed_today,
        stock_tax_pct=stock_tax_pct
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

@views_bp.route("/estate")
@views_bp.route("/earth")
def estate_page():
    user = session.get("user")
    user_data = None
    user_country = None
    db = current_app.config["DB"]
    if user:
        raw_uid = user.get("id")
        uid = int(raw_uid) if str(raw_uid).isdigit() else raw_uid
        user_data = run_async(db.get_global_economy(uid))
        user_country = run_async(db.get_user_earth_country(uid))

    return render_template(
        "estate.html",
        user=user,
        user_data=user_data,
        user_country=user_country
    )

@views_bp.route("/mayor")
@mayor_required
def mayor_page():
    db = current_app.config["DB"]
    user = session.get("user")
    plots = run_async(db.get_estate_plots())
    stocks = run_async(db.get_all_stocks())
    raw_raids = run_async(db.get_recent_raids(8))
    bot = current_app.config.get("DISCORD_BOT")
    from web.api import _resolve_discord_user
    enriched_raids = []
    for r in raw_raids:
        item = dict(r)
        atk_name, atk_av = _resolve_discord_user(r.get("attacker_id"), bot=bot, db=db)
        def_name, def_av = _resolve_discord_user(r.get("defender_id"), bot=bot, db=db)
        item["attacker_name"] = atk_name
        item["attacker_avatar"] = atk_av
        item["defender_name"] = def_name
        item["defender_avatar"] = def_av
        enriched_raids.append(item)
    raids = enriched_raids
    try:
        tax_pct = int(round(run_async(db.get_stock_tax_rate()) * 100))
    except Exception:
        tax_pct = 15

    from web.auth import get_oauth_config
    cfg = get_oauth_config()
    latest_ele = run_async(db.get_latest_election(cfg["guild_id"]))
    import time
    term_end = latest_ele.get("term_end", 0) if latest_ele else 0
    now = time.time()
    term_days_left = max(0, int((term_end - now) // 86400))
    term_hours_left = max(0, int(((term_end - now) % 86400) // 3600))

    total_land_val = sum(p.get("current_value", 0) for p in plots)
    owned_plots = [p for p in plots if p.get("owner_id")]
    zoning_quota = run_async(db.get_mayor_weekly_zoning_quota())
    un_status = run_async(db.get_earth_un_status())
    countries = run_async(db.get_earth_countries())
    active_wars = un_status.get("active_wars", []) if un_status else []

    return render_template(
        "mayor.html",
        user=user,
        plots=plots,
        stocks=stocks,
        raids=raids,
        tax_pct=tax_pct,
        term_days_left=term_days_left,
        term_hours_left=term_hours_left,
        total_land_val=total_land_val,
        owned_count=len(owned_plots),
        total_plots=len(plots),
        zoning_quota=zoning_quota,
        un_status=un_status,
        countries=countries,
        active_wars=active_wars
    )

@views_bp.route("/admin")
@admin_required
def admin_page():
    return render_template("admin.html")


@views_bp.route("/leaderboard")
@views_bp.route("/leaderboards")
def leaderboard_page():
    guild = get_pr_guild()
    ROLE_TOP_1 = 1560533558286745672
    ROLE_TOP_2 = 1560533684141035530
    ROLE_TOP_3 = 1560533774201266247

    top_1_members = []
    top_2_members = []
    top_3_members = []

    def format_member(m, rank_num, role_title, badge_icon):
        name = m.global_name or m.display_name or m.name
        pfp = m.display_avatar.url if hasattr(m, 'display_avatar') else (m.avatar.url if m.avatar else "https://cdn.discordapp.com/embed/avatars/0.png")
        joined = m.joined_at.strftime("%b %d, %Y") if hasattr(m, 'joined_at') and m.joined_at else "Sep 18, 2026"
        return {
            "id": m.id,
            "name": name,
            "username": m.name,
            "avatar": pfp,
            "rank": rank_num,
            "role_title": role_title,
            "badge": badge_icon,
            "joined_at": joined
        }

    if guild:
        r1 = guild.get_role(ROLE_TOP_1)
        r2 = guild.get_role(ROLE_TOP_2)
        r3 = guild.get_role(ROLE_TOP_3)

        if r1:
            top_1_members = [format_member(m, 1, "TOP 1 // SUPREME VICTOR", "👑") for m in r1.members]
        if r2:
            top_2_members = [format_member(m, 2, "TOP 2 // VANGUARD MASTER", "⭐") for m in r2.members]
        if r3:
            top_3_members = [format_member(m, 3, "TOP 3 // COMBAT SPECIALIST", "🛡️") for m in r3.members]

    # Fallbacks if Discord is caching or offline
    if not top_1_members:
        top_1_members = [{
            "id": 1500570205443588317,
            "name": "dred",
            "username": "dred0166_36052",
            "avatar": "https://cdn.discordapp.com/avatars/1500570205443588317/2e4deeb9b1759d49cf72095df99055e3.png?size=1024",
            "rank": 1,
            "role_title": "TOP 1 // SUPREME VICTOR",
            "badge": "👑",
            "joined_at": "Sep 18, 2026"
        }]
    if not top_2_members:
        top_2_members = [{
            "id": 828513350883213342,
            "name": "AkSparkz",
            "username": "arvindkarthick",
            "avatar": "https://cdn.discordapp.com/avatars/828513350883213342/ead6a2c4f0a8e2b3d44f46889144efa8.png?size=1024",
            "rank": 2,
            "role_title": "TOP 2 // VANGUARD MASTER",
            "badge": "⭐",
            "joined_at": "Sep 19, 2026"
        }]
    if not top_3_members:
        top_3_members = [{
            "id": 1386072706298155068,
            "name": "Dr. Calico",
            "username": "lostrawberrys",
            "avatar": "https://cdn.discordapp.com/avatars/1386072706298155068/493d0db0e01161022ee94457027b9e62.png?size=1024",
            "rank": 3,
            "role_title": "TOP 3 // COMBAT SPECIALIST",
            "badge": "🛡️",
            "joined_at": "Sep 19, 2026"
        }]

    all_champions = top_1_members + top_2_members + top_3_members

    return render_template(
        "leaderboard.html",
        top_1_members=top_1_members,
        top_2_members=top_2_members,
        top_3_members=top_3_members,
        all_champions=all_champions,
        guild_name=guild.name if guild else "Phantom Regiment"
    )



@views_bp.route("/elections")
@views_bp.route("/election")
def elections_page():
    import time
    guild = get_pr_guild()
    db = current_app.config.get("DB")
    gid = guild.id if guild else 0

    active_election = run_async(db.get_active_election(gid)) if (db and gid) else None
    candidates = []
    total_votes = 0
    time_remaining_str = ""
    if active_election:
        cands_raw = run_async(db.get_election_candidates(active_election["id"])) if db else []
        candidates = [dict(c) for c in cands_raw] if cands_raw else []
        total_votes = sum(c.get("votes", 0) for c in candidates)
        candidates.sort(key=lambda x: x.get("votes", 0), reverse=True)
        for idx, c in enumerate(candidates, 1):
            c["rank"] = idx
            cid = c.get("candidate_id")
            member = guild.get_member(cid) if guild else None
            c["name"] = (member.global_name or member.display_name) if member else f"Candidate {cid}"
            c["avatar"] = member.display_avatar.url if (member and hasattr(member, "display_avatar")) else "https://cdn.discordapp.com/embed/avatars/0.png"
            c["pct"] = round((c.get("votes", 0) / max(total_votes, 1)) * 100, 1)

        end_time = active_election.get("end_time", 0)
        rem_sec = max(0, int(end_time - time.time()))
        rem_h = rem_sec // 3600
        rem_m = (rem_sec % 3600) // 60
        time_remaining_str = f"{rem_h}h {rem_m}m"

    current_commander = run_async(db.get_current_commander(gid)) if (db and gid) else None
    mayor_info = None
    if current_commander and current_commander.get("winner_id"):
        wid = current_commander["winner_id"]
        member = guild.get_member(wid) if guild else None
        term_end = current_commander.get("term_end", 0)
        rem_term_sec = max(0, int(term_end - time.time()))
        rem_days = rem_term_sec // 86400
        rem_term_hours = (rem_term_sec % 86400) // 3600
        mayor_info = {
            "id": wid,
            "name": (member.global_name or member.display_name) if member else f"Mayor {wid}",
            "avatar": member.display_avatar.url if (member and hasattr(member, "display_avatar")) else "https://cdn.discordapp.com/embed/avatars/0.png",
            "term_end": term_end,
            "term_days_left": rem_days,
            "term_hours_left": rem_term_hours
        }

    double_xp_active = run_async(db.is_double_xp_active(gid)) if (db and gid) else False
    double_xp_remaining = run_async(db.get_double_xp_remaining(gid)) if (db and gid) else 0.0
    double_xp_hours_left = round(double_xp_remaining / 3600, 1) if double_xp_remaining > 0 else 0

    return render_template(
        "elections.html",
        active_election=active_election,
        candidates=candidates,
        total_votes=total_votes,
        time_remaining_str=time_remaining_str,
        mayor_info=mayor_info,
        double_xp_active=double_xp_active,
        double_xp_hours_left=double_xp_hours_left,
        guild_name=guild.name if guild else "Phantom Regiment"
    )

@views_bp.route("/unauthorized")
def unauthorized():
    return render_template("unauthorized.html"), 403

@views_bp.route("/verify")
def verify():
    if "user" in session:
        return redirect(url_for("views.index"))
    from web.auth import get_clean_next
    next_url = get_clean_next(request.args.get("next")) or "/"
    guild = get_pr_guild()
    member_count = guild.member_count if guild else 0
    return render_template("verify.html", next_url=next_url, member_count=member_count)

