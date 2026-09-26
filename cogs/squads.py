import asyncio
import time
import discord
from discord import app_commands
from discord.ext import commands

SQUADS = {
    0: {
        "name": "Frontline", 
        "commander_id": 1319203870681071679, 
        "invite_link": "https://discord.gg/Buu6Xvr83x",
        "emoji": "⚔️",
        "short_desc": "Highly Adaptable Combat",
        "description": "**Specialty: Highly Adaptable Combat**\nThe Frontline squad is tactically fluid and plays strictly according to the situation. Whether the battle requires an aggressive push, a tactical retreat, or holding a choke point, they are the versatile backbone of the regiment that constantly adapts to overcome the enemy."
    },
    1: {
        "name": "Los Bluchigis", 
        "commander_id": 1431779664140959836, 
        "invite_link": "https://discord.gg/9Hv5rAaUkz",
        "emoji": "🐎",
        "short_desc": "Elite Cavalry Masters",
        "description": "**Specialty: Elite Cavalry Masters**\nLos Bluchigis consists of riders who have mastered every single horse unit in the game. They specialize in devastating cavalry charges, lightning-fast flanking maneuvers, and dominating the battlefield with unmatched speed and mobility."
    },
    2: {
        "name": "Ignite's squad", 
        "commander_id": 754264189601710100, 
        "invite_link": "https://discord.gg/NrgbGCDEwU",
        "emoji": "🏹",
        "short_desc": "Archery & Shield Formations",
        "description": "**Specialty: Archery & Shield Formations**\nIgnite's squad are the undisputed masters of ranged combat and defensive lines. They specialize in raining down devastating arrow fire from afar, all while being protected behind an impenetrable wall of elite shield-holders that no enemy can break through."
    }
}

QUESTIONS = [
    "How many **wins** do you currently have?",
    "How many **kills** do you currently have?",
    "What is your current in-game **level**?",
    "How long have you been a member of the Phantom Regiment?",
    "Please upload a **screenshot** of your current in-game stats.",
    "What is your **timezone**?",
    "Do you agree to strictly follow the orders of your Squad Commander? (Yes/No)"
]


# ════════════════════════════════════════════════════════════════════════════════
# Commander Approval Buttons (Persistent)
# ════════════════════════════════════════════════════════════════════════════════

class _SquadApproveBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"sqd:acc:(?P<uid>\d+):(?P<gid>\d+):(?P<sqd>\d+)",
):
    def __init__(self, uid: int, gid: int, sqd: int):
        super().__init__(discord.ui.Button(
            label="✅ Accept",
            style=discord.ButtonStyle.success,
            custom_id=f"sqd:acc:{uid}:{gid}:{sqd}",
        ))
        self.uid, self.gid, self.sqd = uid, gid, sqd

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]), int(match["sqd"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Make sure only the commander or an admin can click
        commander_id = SQUADS[self.sqd]["commander_id"]
        is_admin = interaction.user.guild_permissions.administrator if hasattr(interaction.user, 'guild_permissions') else False
        if interaction.user.id != commander_id and not is_admin:
            return await interaction.followup.send("❌ Only the Commander of this squad can approve applications.", ephemeral=True)

        squad_info = SQUADS[self.sqd]
        guild = interaction.client.get_guild(self.gid)
        
        # 1. Update embed message
        embed = interaction.message.embeds[0].copy()
        embed.colour = discord.Colour.green()
        embed.add_field(name="✅ Result", value="Approved", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        
        # 2. Get user and assign role
        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        
        if guild:
            member = guild.get_member(self.uid)
            if not member:
                try:
                    member = await guild.fetch_member(self.uid)
                except discord.HTTPException:
                    pass
            
            if member:
                # Find or create role
                role = discord.utils.get(guild.roles, name=squad_info["name"])
                if not role:
                    try:
                        role = await guild.create_role(name=squad_info["name"], reason="Squad application approved", colour=discord.Colour.random())
                    except discord.Forbidden:
                        role = None
                
                if role:
                    try:
                        await member.add_roles(role, reason="Joined squad")
                    except discord.Forbidden:
                        pass
        
        # 3. DM User
        if user:
            try:
                await user.send(
                    f"🎉 **Congratulations!** Your application to **{squad_info['name']}** has been accepted by the Commander!\n\n"
                    f"Join your squad's server here: {squad_info['invite_link']}"
                )
            except discord.Forbidden:
                pass


class _SquadDenyBtn(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"sqd:den:(?P<uid>\d+):(?P<gid>\d+):(?P<sqd>\d+)",
):
    def __init__(self, uid: int, gid: int, sqd: int):
        super().__init__(discord.ui.Button(
            label="❌ Deny",
            style=discord.ButtonStyle.danger,
            custom_id=f"sqd:den:{uid}:{gid}:{sqd}",
        ))
        self.uid, self.gid, self.sqd = uid, gid, sqd

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(int(match["uid"]), int(match["gid"]), int(match["sqd"]))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        commander_id = SQUADS[self.sqd]["commander_id"]
        is_admin = interaction.user.guild_permissions.administrator if hasattr(interaction.user, 'guild_permissions') else False
        if interaction.user.id != commander_id and not is_admin:
            return await interaction.followup.send("❌ Only the Commander of this squad can deny applications.", ephemeral=True)

        squad_info = SQUADS[self.sqd]
        
        # Update embed message
        embed = interaction.message.embeds[0].copy()
        embed.colour = discord.Colour.red()
        embed.add_field(name="❌ Result", value="Denied", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        
        # Set cooldown
        db = getattr(interaction.client, "db", None)
        if db and hasattr(db, "_db"):
            await db._db.execute(
                "INSERT OR REPLACE INTO squad_cooldowns (user_id, squad_idx, denied_at) VALUES (?, ?, ?)",
                (self.uid, self.sqd, time.time())
            )
            await db._db.commit()
            
        # DM User
        user = interaction.client.get_user(self.uid) or await interaction.client.fetch_user(self.uid)
        if user:
            try:
                await user.send(f"❌ Your application to join **{squad_info['name']}** was denied by the Commander. You may try again in 24 hours.")
            except discord.Forbidden:
                pass


# ════════════════════════════════════════════════════════════════════════════════
# DM Dropdown & Application Loop
# ════════════════════════════════════════════════════════════════════════════════

class _SquadSelect(discord.ui.Select):
    def __init__(self, cog, guild: discord.Guild):
        self.cog = cog
        self.guild = guild
        options = [
            discord.SelectOption(
                label=sqd["name"], 
                value=str(idx), 
                emoji=sqd["emoji"],
                description=sqd["short_desc"]
            ) 
            for idx, sqd in SQUADS.items()
        ]
        super().__init__(placeholder="Choose your Squad...", options=options)

    async def callback(self, interaction: discord.Interaction):
        sqd_idx = int(self.values[0])
        squad_name = SQUADS[sqd_idx]["name"]
        
        # Check cooldown
        db = getattr(interaction.client, "db", None)
        if db and hasattr(db, "_db"):
            async with db._db.execute("SELECT denied_at FROM squad_cooldowns WHERE user_id = ? AND squad_idx = ?", (interaction.user.id, sqd_idx)) as cur:
                row = await cur.fetchone()
                if row:
                    last_denied = row[0]
                    if time.time() - last_denied < 86400: # 24 hours
                        return await interaction.response.send_message("⏳ You were recently denied from this squad. Please wait 24 hours before applying again.", ephemeral=True)
        
        await interaction.response.send_message(f"✅ You selected **{squad_name}**. Let's begin the interview!", ephemeral=True)
        
        # Disable the dropdown
        for child in self.view.children:
            child.disabled = True
        try:
            await interaction.message.edit(view=self.view)
        except discord.HTTPException:
            pass

        # Start the question loop in the background
        asyncio.create_task(self.cog._run_squad_application(interaction.user, self.guild, sqd_idx))


class _SquadSelectView(discord.ui.View):
    def __init__(self, cog, guild: discord.Guild):
        super().__init__(timeout=300)
        self.add_item(_SquadSelect(cog, guild))


# ════════════════════════════════════════════════════════════════════════════════
# Cog
# ════════════════════════════════════════════════════════════════════════════════

class SquadsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._active: set[int] = set()

    async def cog_load(self):
        self.bot.add_dynamic_items(_SquadApproveBtn, _SquadDenyBtn)

    async def _run_squad_application(self, user: discord.User, guild: discord.Guild, sqd_idx: int):
        squad_info = SQUADS[sqd_idx]
        
        if user.id in self._active:
            self._active.remove(user.id)
        self._active.add(user.id)
        
        try:
            intro = discord.Embed(
                title=f"📝 {squad_info['name']} Application",
                description=(
                    f"I'll ask you **{len(QUESTIONS)} questions** one at a time.\n"
                    "Just type your answer after each question.\n"
                    "You have **5 minutes** per question — take your time!"
                ),
                colour=discord.Colour.blue(),
            )
            try:
                await user.send(embed=intro)
            except discord.Forbidden:
                return

            def check(m: discord.Message) -> bool:
                return m.author.id == user.id and m.guild is None

            answers = []
            for i, q in enumerate(QUESTIONS, start=1):
                if user.id not in self._active:
                    return

                embed = discord.Embed(description=f"**{i}** {q}")
                embed.set_footer(text=f"Question {i} of {len(QUESTIONS)} • Type your answer below")
                embed.colour = discord.Colour.gold()

                await user.send(embed=embed)

                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=300)
                except asyncio.TimeoutError:
                    if user.id in self._active:
                        self._active.remove(user.id)
                    try:
                        await user.send("⏰ Application timed out. Use `/joinsquad` in the server to try again.")
                    except discord.HTTPException:
                        pass
                    return

                content = msg.content
                if not content and msg.attachments:
                    content = msg.attachments[0].url
                elif not content:
                    content = "*(No text provided)*"
                    
                answers.append(content)
                try:
                    await msg.add_reaction("✅")
                except Exception:
                    pass

            # Done asking
            if user.id in self._active:
                self._active.remove(user.id)

            await user.send("✅ **Application complete!** I am sending it to the Commander right now.")

            # Build submission embed
            roblox_link = await self.bot.db.get_roblox_link(user.id)
            roblox_txt = "Not Linked"
            if roblox_link:
                r_disp = roblox_link.get('roblox_display', 'Unknown')
                r_user = roblox_link.get('roblox_username', 'Unknown')
                roblox_txt = f"{r_disp} (@{r_user})"
                
            embed = discord.Embed(
                title=f"New Application: {squad_info['name']}",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.add_field(name="Roblox Account", value=roblox_txt, inline=False)
            
            for i, (q, a) in enumerate(zip(QUESTIONS, answers), start=1):
                embed.add_field(name=f"Q{i}. {q.replace('*', '')}", value=str(a)[:1024], inline=False)

            view = discord.ui.View(timeout=None)
            view.add_item(_SquadApproveBtn(user.id, guild.id, sqd_idx))
            view.add_item(_SquadDenyBtn(user.id, guild.id, sqd_idx))
            
            # Send to Commander
            commander = self.bot.get_user(squad_info["commander_id"]) or await self.bot.fetch_user(squad_info["commander_id"])
            if commander:
                try:
                    await commander.send(embed=embed, view=view)
                except discord.Forbidden:
                    await user.send("❌ Error: I cannot DM the Commander. They might have DMs disabled!")
            else:
                await user.send("❌ Error: Could not find the Commander. Contact an admin.")

        except Exception as e:
            if user.id in self._active:
                self._active.remove(user.id)
            print(f"Squad application error for {user}: {e}")

    # ── Commands ────────────────────────────────────────────────────────────

    @app_commands.command(name="joinsquad", description="Apply to join one of the elite squads")
    async def joinsquad(self, interaction: discord.Interaction):
        if not interaction.guild or isinstance(interaction.user, discord.User):
            return await interaction.response.send_message("❌ Please run this command inside the server, not in DMs.", ephemeral=True)

        # 1. Verify Roblox Link
        roblox_link = await self.bot.db.get_roblox_link(interaction.user.id)
        if not roblox_link:
            return await interaction.response.send_message("❌ You must connect your Roblox account using `/verify` before applying to a squad.", ephemeral=True)
            
        # 2. Exclusivity check
        squad_names = [s["name"] for s in SQUADS.values()]
        user_squads = [r.name for r in interaction.user.roles if r.name in squad_names]
        if user_squads:
            return await interaction.response.send_message(f"❌ You are already a member of **{user_squads[0]}**. You must `/leavesquad` before applying to a new one.", ephemeral=True)
            
        # Send dropdown
        view = _SquadSelectView(self, interaction.guild)
        try:
            embed = discord.Embed(
                title="🛡️ Enlist in a Squad",
                description="**Select a Squad, check their specialty, and choose for yourself!**",
                color=discord.Color.blurple()
            )
            await interaction.user.send(embed=embed, view=view)
            await interaction.response.send_message("📬 I've sent you a DM to start the application process!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I cannot DM you. Please enable your DMs in privacy settings.", ephemeral=True)


    @app_commands.command(name="squads", description="View information about the 3 elite squads")
    async def squads_info(self, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Please run this command inside the server.", ephemeral=True)

        embeds = []
        for idx, sqd in SQUADS.items():
            # Find the role to get member count
            role = discord.utils.get(interaction.guild.roles, name=sqd["name"])
            member_count = len(role.members) if role else 0
            
            embed = discord.Embed(
                title=f"🛡️ {sqd['name']}",
                description=sqd["description"],
                color=discord.Color.blurple()
            )
            embed.add_field(name="Commander", value=f"<@{sqd['commander_id']}>", inline=True)
            embed.add_field(name="Members", value=f"{member_count} Troops", inline=True)
            embeds.append(embed)
            
        await interaction.response.send_message(embeds=embeds)


    @app_commands.command(name="leavesquad", description="Officially resign from your current squad")
    async def leavesquad(self, interaction: discord.Interaction):
        if not interaction.guild or isinstance(interaction.user, discord.User):
            return await interaction.response.send_message("❌ Please run this command inside the server.", ephemeral=True)

        squad_names = {s["name"]: s for s in SQUADS.values()}
        user_roles = [r for r in interaction.user.roles if r.name in squad_names]
        
        if not user_roles:
            return await interaction.response.send_message("❌ You are not in any squad.", ephemeral=True)
            
        role_to_remove = user_roles[0]
        squad_info = squad_names[role_to_remove.name]
        
        try:
            await interaction.user.remove_roles(role_to_remove, reason="User resigned from squad")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ I do not have permission to remove your squad role.", ephemeral=True)
            
        await interaction.response.send_message(f"✅ You have officially left **{role_to_remove.name}**.", ephemeral=True)
        
        # Notify Commander
        commander = self.bot.get_user(squad_info["commander_id"]) or await self.bot.fetch_user(squad_info["commander_id"])
        if commander:
            try:
                await commander.send(f"⚠️ **Notice:** {interaction.user.mention} ({interaction.user.display_name}) has resigned and left **{role_to_remove.name}**.")
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(SquadsCog(bot))
