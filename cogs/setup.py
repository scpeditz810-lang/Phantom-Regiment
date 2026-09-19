"""
Setup cog — one-time  !setup  command that creates every role and channel.

Permission model:
  • @everyone — denied view on ALL categories (locked by default)
  • Member role — allowed view on non-staff categories (full access)
  • Unverified role — allowed view ONLY on channels marked unverified_visible
  • Staff roles — allowed view on staff-only categories
  • Commander — extra access to specific channels (app-review, win-verification)

Run once by the server owner / admin.  Idempotent: skips existing items.
"""

from __future__ import annotations

import discord
from discord.ext import commands

from utils.constants import (
    CHANNELS, ROLE_HIERARCHY,
    STAFF_ROLES, LEVEL_ROLES, IN_GAME_ROLES, COMMANDER_ROLE,
    INTERLEAVED_ROLES
)


class InfoDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Server Information", 
                description="Information regarding the server", 
                emoji="📖"
            ),
            discord.SelectOption(
                label="Game Information", 
                description="Information regarding the game", 
                emoji="ℹ️"
            ),
            discord.SelectOption(
                label="Role Information", 
                description="How level system works etc", 
                emoji="📰"
            )
        ]
        super().__init__(placeholder="Make a selection", options=options, custom_id="persistent_info_dropdown")

class RulesDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Minor Offenses", emoji="🟢"),
            discord.SelectOption(label="Moderate Offenses", emoji="🟠"),
            discord.SelectOption(label="Major Offenses", emoji="🔴"),
        ]
        super().__init__(placeholder="Rules", options=options, custom_id="persistent_rules_dropdown")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Minor Offenses":
            embed = discord.Embed(
                title="Minor Offences",
                description="All rules listed below are classified as \"Minor offenses\" without too heavy punishment.\n\n"
                            "```text\n"
                            "• Spamming emojis, reactions or bot commands\n\n"
                            "• Channel Misuse - Posting content in the wrong channels or ignoring channel rules\n\n"
                            "• Spoilers\n\n"
                            "• Mild Toxicity - Minor trash talk, rude comments or negative behavior that causes minor disruption\n\n"
                            "• Ghost Pings - Pinging a member and then deleting the message repeatedly\n\n"
                            "• XP Farming\n\n"
                            "• Chaining - Sending multiple short messages in a row instead of one message\n\n"
                            "• Attempt to bypass word filters (symbols, spacing etc...)\n\n"
                            "• Light Trolling/Ragebaiting\n"
                            "```\n"
                            "> These offences will result in either a verbal warning, logged warning, or a direct mute depending on the severity of the action.",
                color=0x2b2d31
            )
        elif self.values[0] == "Moderate Offenses":
            embed = discord.Embed(
                title="Moderate Offenses",
                description="All rules listed below are classified as \"Moderate offenses\" and may result in harsh moderation actions.\n\n"
                            "```text\n"
                            "• Nsfw Comments/References - Any sort of NSFW action/behavior or content\n\n"
                            "• Not listening to staff orders, arguing or ignoring staff orders when they warn you to stop doing something\n\n"
                            "• Inappropriate pfp/banner/guild tag/display name - Having inappropriate content as discord banner or profile picture\n\n"
                            "• Inciting drama - Causing problems and drama in chat\n\n"
                            "• Encouraging members to break rules\n\n"
                            "• Arguments - Must be avoided or moved to DMs or punishments will be taken.\n\n"
                            "• Mass pinging a large number of people or a single person multiple times.\n\n"
                            "• Advertising - Sharing discord invites, social media links, or promotions for others servers/games & indirect advertising asking users to DM you or check your status or bio\n"
                            "```",
                color=0x2b2d31
            )
        else:
            embed = discord.Embed(
                title="Major Offenses",
                description="All rules listed below are classified as \"Major offenses\" and will result in immediate, permanent removal from the server.\n\n"
                            "```text\n"
                            "• Extreme Toxicity / Slurs / Hate Speech - Zero tolerance for discrimination or severe harassment\n\n"
                            "• Scamming / Fraud / Phishing - Attempting to steal accounts, items, or money\n\n"
                            "• Doxxing / Leaking Personal Information - Sharing private info of others\n\n"
                            "• Exploiting / Hacking - Using or distributing cheats in-game\n\n"
                            "• Severe NSFW - Posting explicit imagery, gore, or illegal content\n\n"
                            "• Ban Evasion - Using an alt account to bypass a punishment\n\n"
                            "• Raiding - Organizing or participating in server attacks\n\n"
                            "• Impersonating Staff - Pretending to be a moderator or administrator\n"
                            "```\n"
                            "> These offences will result in an immediate Permanent Ban without warning.",
                color=0x2b2d31
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Discord ToS", url="https://discord.com/terms"))
        self.add_item(discord.ui.Button(label="Roblox ToS", url="https://en.help.roblox.com/hc/en-us/articles/115004647846-Roblox-Terms-of-Use"))
        self.add_item(RulesDropdown())


class InfoDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Server Information", description="Information regarding the server", emoji="📖"),
            discord.SelectOption(label="Game Information", description="Information regarding the game", emoji="ℹ️"),
            discord.SelectOption(label="Role Information", description="How roles work", emoji="📰"),
            discord.SelectOption(label="Level System", description="How the XP/Level system works in detail", emoji="⭐"),
            discord.SelectOption(label="Medal Economy", description="How to earn and spend Medals", emoji="🏅"),
            discord.SelectOption(label="Bot Commands", description="A detailed list of all bot commands", emoji="🤖")
        ]
        super().__init__(placeholder="Make a selection", options=options, custom_id="persistent_info_dropdown_v2")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Server Information":
            rules_ch = discord.utils.get(interaction.guild.channels, name="📜│rules")
            faq_ch = discord.utils.get(interaction.guild.channels, name="❓│faq")
            ann_ch = discord.utils.get(interaction.guild.channels, name="📢│announcements")
            
            rules_str = rules_ch.mention if rules_ch else "#📜│rules"
            faq_str = faq_ch.mention if faq_ch else "#❓│faq"
            ann_str = ann_ch.mention if ann_ch else "#📢│announcements"
            
            embed = discord.Embed(
                title="📖 Server Information",
                description=(
                    "Welcome to the clan! Our server is designed to reward activity and participation.\n\n"
                    f"• Please read the {rules_str} carefully to avoid moderation actions.\n"
                    f"• Check {faq_str} if you have any immediate questions.\n"
                    f"• Keep an eye on {ann_str} for major clan updates."
                ),
                color=0x3498DB
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif self.values[0] == "Level System":
            embed = discord.Embed(
                title="⭐ Level System",
                description=(
                    "We feature a fully custom, global XP and Leveling system designed to reward active members!\n\n"
                    "**How it works:**\n"
                    "• Every message you send in the server grants you **XP**.\n"
                    "• There is a short cooldown between messages to prevent spamming.\n"
                    "• As you accumulate XP, you will **Level Up**!\n"
                    "• Reaching specific levels automatically unlocks new **Server Ranks** (like Recruit, Private, Corporal, etc).\n\n"
                    "**Commands:**\n"
                    "• Use `/level` or `/rank` to view your current XP, level, and a beautiful custom rank card!\n"
                    "• Use `/leaderboard` to view the top 10 most active members in the server and compete for the #1 spot!\n\n"
                    "Stay active, help others, and watch your rank climb!"
                ),
                color=0xF1C40F
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif self.values[0] == "Game Information":
            embed = discord.Embed(
                title="ℹ️ Game Information",
                description=(
                    "Command an Army is a tactical strategy game. Join our clan, coordinate with your teammates, and climb the leaderboards. "
                    "Use the CAA channels to find a team or discuss strategy!"
                ),
                color=0x3498DB
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif self.values[0] == "Medal Economy":
            embed = discord.Embed(
                title="🏅 Medal Economy",
                description=(
                    "Medals are the official currency of the Phantom Regiment. You can earn them, gamble them, and spend them in the shop!\n\n"
                    "**How to earn Medals:**\n"
                    "• **Daily Claim**: Use the `/daily` command to instantly claim 100 Medals every 24 hours.\n"
                    "• **Leveling Up**: You get 50 Medals every time you level up by chatting!\n"
                    "• **Gambling**: Challenge the bot with `/coinflip` or fight other players in Rock Paper Scissors with `/rps`!\n\n"
                    "**The Shop:**\n"
                    "Use `/shop` to browse the Armory. Currently, you can spend Medals to buy **Custom Rank Banners**. "
                    "Once purchased, use `/changebanner` to permanently equip it to your `/rank` card!"
                ),
                color=0xE67E22
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif self.values[0] == "Bot Commands":
            embed = discord.Embed(
                title="🤖 Bot Commands Guide",
                description="Here is a detailed list of all essential commands you can use in the server:",
                color=0x2ECC71
            )
            embed.add_field(
                name="📈 Progression",
                value="`/rank` - View your beautiful rank card, Level, XP, and Wins.\n`/leaderboard` - View the top 10 most active chatters.\n`/submit-wins` - Submit an in-game screenshot to get verified for Game Roles.",
                inline=False
            )
            embed.add_field(
                name="🏅 Economy & Shop",
                value="`/daily` - Claim 100 free Medals every 24h.\n`/balance` - Check your wallet.\n`/shop` - View purchasable custom banners.\n`/buy` - Buy an item from the shop.\n`/changebanner` - Equip a purchased banner to your rank card.",
                inline=False
            )
            embed.add_field(
                name="🎲 Gambling",
                value="`/coinflip <bet>` - 50/50 chance to double your bet against the bot.\n`/rps <player> <bet>` - Challenge another player to Rock Paper Scissors for a winner-takes-all pot!",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        elif self.values[0] == "Role Information":
            embed = discord.Embed(
                title="📰 Role Information",
                color=0x9B59B6
            )
            
            server_roles_text = ""
            from utils.constants import LEVEL_ROLES, IN_GAME_ROLES
            for r in LEVEL_ROLES:
                server_roles_text += f"**Level {r['level']}**\n╰─ @ {r['name']}\n"
                
            embed.add_field(
                name="💬 Server Ranks (XP)",
                value=(
                    "Earned automatically by chatting in the server. Use `/rank` to check your progress and `/leaderboard` to view global rankings.\n\n"
                    + server_roles_text
                ),
                inline=False
            )
            
            game_roles_text = ""
            for r in IN_GAME_ROLES:
                game_roles_text += f"**Wins {r['wins']}**\n╰─ @ {r['name']}\n"
                
            embed.add_field(
                name="🏆 Game Ranks (Wins)",
                value=(
                    "Take a screenshot of your stats in-game. Use `/submit-wins` and attach your screenshot. "
                    "Staff will review it, which will automatically grant you your new role!\n\n"
                    + game_roles_text
                ),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


class InfoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(InfoDropdown())


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(InfoView())
        self.bot.add_view(RulesView())

    @commands.command(name="infoposts")
    @commands.has_permissions(administrator=True)
    async def infoposts(self, ctx: commands.Context):
        """Post static informational messages to the rules, faq, and info channels."""
        rules_ch = discord.utils.get(ctx.guild.text_channels, name="📜│rules")
        faq_ch = discord.utils.get(ctx.guild.text_channels, name="❓│faq")
        info_ch = discord.utils.get(ctx.guild.text_channels, name="ℹ️│info")

        if rules_ch:
            await rules_ch.purge(limit=10)
            
            rules_embed = discord.Embed(
                color=0x2b2d31,
                description=(
                    "All Members of this discord server must follow both Discord Terms "
                    "of Service and Roblox Terms of Service. Violating one of these "
                    "terms will result in severe consequences.\n\n"
                    "» Staff decisions are final, any rule breaking that was not "
                    "listed here you can still be punished. Use common sense at all times.\n"
                    "» Any Behaviour not mentioned that could harm others or "
                    "may be seen as a problem in the future.\n\n"
                    "**Warning System**\n"
                    "```text\n"
                    "• 1 warn - Depending on infraction/case: 0-2h mute\n"
                    "• 2 warn - 4h mute\n"
                    "• 3 warn - 8h mute\n"
                    "• 4 warn - 12h mute\n"
                    "• 5 warn - Ban\n"
                    "```"
                )
            )
            rules_embed.set_author(name="Phantom Regiment Rules", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            
            await rules_ch.send(embed=rules_embed, view=RulesView())
        
        if faq_ch:
            await faq_ch.purge(limit=10)
            
            faq_embed = discord.Embed(
                title="❓ Frequently Asked Questions",
                color=0xFEE75C
            )
            faq_embed.add_field(
                name="How do I get Server Ranks?",
                value="Simply by chatting in the server! You gain XP for every message you send. Use `/rank` to check your progress.",
                inline=False
            )
            faq_embed.add_field(
                name="How do I get Game Ranks (Rookie, Legend, etc.)?",
                value="Game ranks are based entirely on your in-game wins. Take a screenshot of your wins and use the `/submit-wins` command. Staff will review it and approve it, which will automatically grant you the appropriate role!",
                inline=False
            )
            faq_embed.add_field(
                name="What are Medals and how do I use them?",
                value=f"Medals are the official server currency! You can get them by using `/daily`, leveling up, or gambling with `/coinflip` and `/rps`. You can spend them in the `/shop`. Check the **Medal Economy** section in the <#{info_ch.id if info_ch else '0'}> channel for full details!",
                inline=False
            )
            faq_embed.add_field(
                name="Where can I see a full list of roles and commands?",
                value=f"Visit the <#{info_ch.id if info_ch else '0'}> channel and use the dropdown menu! It has everything you need to know.",
                inline=False
            )
            
            await faq_ch.send(embed=faq_embed)

        if info_ch:
            await info_ch.purge(limit=10)
            embed = discord.Embed(
                title="Phantom Regiment Information",
                description="Select an option from the dropdown menu below to learn more about our Server, Game, and Role progression system.",
                color=0x3498DB
            )
            await info_ch.send(embed=embed, view=InfoView())

        await ctx.send("✅ Cleared old messages and posted all new informational messages!")

    @commands.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_server(self, ctx: commands.Context):
        """Create all roles and channels.  Admin / Owner only."""
        guild = ctx.guild
        status = await ctx.send("⏳ Setting up server…")

        # ────────────────────────────────────────────────────────────────────
        # 1.  ROLES
        # ────────────────────────────────────────────────────────────────────
        await ctx.send("🔧  Creating roles…")

        hoist_names = {r["name"] for r in STAFF_ROLES} | {COMMANDER_ROLE["name"]}

        for rdef in ROLE_HIERARCHY:
            if discord.utils.get(guild.roles, name=rdef["name"]):
                continue
            try:
                await guild.create_role(
                    name=rdef["name"],
                    colour=discord.Colour(rdef["color"]),
                    permissions=rdef.get("permissions", discord.Permissions.none()),
                    hoist=True,  # Hoist ALL managed roles
                    mentionable=False,
                )
            except Exception as e:
                await ctx.send(f"⚠️  Role `{rdef['name']}`: {e}")

        # ── reorder roles ───────────────────────────────────────────────
        await ctx.send("📊  Reordering roles…")
        await self._do_shuffle(ctx)

    @commands.command(name="hoistall")
    @commands.has_permissions(administrator=True)
    async def hoist_all(self, ctx: commands.Context):
        """Enable 'Display separately' for all managed roles."""
        await ctx.send("🔄 Enabling 'Display separately' for all roles...")
        
        from utils.constants import INTERLEAVED_ROLES
        all_defs = (
            [{"name": "Unverified"}, {"name": "Member"}]
            + INTERLEAVED_ROLES
            + [COMMANDER_ROLE]
            + STAFF_ROLES
        )
        target_order = [rd["name"] for rd in all_defs]
        
        count = 0
        for role in ctx.guild.roles:
            if role.name in target_order and not role.hoist:
                try:
                    await role.edit(hoist=True)
                    count += 1
                except:
                    pass
                    
        await ctx.send(f"✅ Enabled 'Display separately' for {count} roles!")

    @commands.command(name="shuffle")
    @commands.has_permissions(administrator=True)
    async def shuffle_roles(self, ctx: commands.Context):
        """Standalone command to fix role hierarchy order."""
        await ctx.send("🔀 Shuffling roles into correct order...")
        await self._do_shuffle(ctx)

    async def _do_shuffle(self, ctx: commands.Context):
        guild = ctx.guild
        from utils.constants import INTERLEAVED_ROLES
        all_defs = (
            [{"name": "Unverified"}, {"name": "Member"}]
            + INTERLEAVED_ROLES
            + [COMMANDER_ROLE]
            + STAFF_ROLES
        )
        
        target_order = [rd["name"] for rd in all_defs]
        
        managed_roles = [r for r in guild.roles if r.name in target_order]
        
        if not managed_roles:
            return await ctx.send("⚠️ No roles found to shuffle!")
            
        # 1. Ensure the bot can actually move these roles
        bot_top = guild.me.top_role
        for r in managed_roles:
            if r >= bot_top:
                return await ctx.send(
                    f"❌ **Missing Permissions!**\n"
                    f"Your bot's highest role ({bot_top.mention}) is currently BELOW `{r.name}`.\n"
                    f"Please go to Server Settings → Roles, and drag the bot's role to the absolute top!"
                )
                
        # 2. Extract the exact positions currently occupied by our roles
        available_slots = sorted([r.position for r in managed_roles])
        
        # 3. Sort the roles in our desired hierarchy (lowest to highest)
        managed_roles.sort(key=lambda r: target_order.index(r.name))
        
        # 4. Map the sorted roles perfectly back into the available slots
        positions = {}
        for role, slot in zip(managed_roles, available_slots):
            positions[role] = slot
            
        try:
            await guild.edit_role_positions(positions)
            await ctx.send("✅ Roles perfectly sorted!")
        except Exception as e:
            await ctx.send(f"⚠️ Failed to sort roles: {e}")

        # ────────────────────────────────────────────────────────────────────
        # 2.  CHANNELS
        # ────────────────────────────────────────────────────────────────────
        await ctx.send("📂  Creating channels…")

        # Collect role objects
        staff_objs = [
            discord.utils.get(guild.roles, name=r["name"])
            for r in STAFF_ROLES
        ]
        staff_objs = [r for r in staff_objs if r]
        commander_obj = discord.utils.get(guild.roles, name=COMMANDER_ROLE["name"])
        member_obj    = discord.utils.get(guild.roles, name="Member")
        unverified_obj = discord.utils.get(guild.roles, name="Unverified")

        for cat_name, cat_data in CHANNELS.items():
            # ── category overwrites ─────────────────────────────────────
            cat_ow: dict = {
                # Lock everything from @everyone by default
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
            }

            if cat_data.get("member_visible") and member_obj:
                # Members can see all channels in this category
                cat_ow[member_obj] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    read_message_history=True,
                )

            if cat_data.get("staff_only"):
                # Only staff roles can see
                for sr in staff_objs:
                    cat_ow[sr] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True,
                        read_message_history=True,
                    )

            # ── create or get category ──────────────────────────────────
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                try:
                    category = await guild.create_category(
                        name=cat_name, overwrites=cat_ow)
                except Exception as e:
                    await ctx.send(f"⚠️  Category `{cat_name}`: {e}")
                    continue

            # ── channels inside category ────────────────────────────────
            for ch_cfg in cat_data.get("channels", []):
                name = ch_cfg["name"]
                if discord.utils.get(guild.text_channels,
                                     name=name, category=category):
                    continue

                ch_ow: dict = {}

                # Read-only for everyone who can view
                if ch_cfg.get("readonly"):
                    ch_ow[guild.default_role] = discord.PermissionOverwrite(
                        send_messages=False)
                    if member_obj:
                        ch_ow[member_obj] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=False,
                            read_message_history=True,
                        )

                # Staff-only send (announcements, side-news)
                if ch_cfg.get("staff_only_send"):
                    ch_ow[guild.default_role] = discord.PermissionOverwrite(
                        send_messages=False)
                    if member_obj:
                        ch_ow[member_obj] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=False,
                            read_message_history=True,
                        )
                    for sr in staff_objs:
                        ch_ow[sr] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=True)

                # Unverified can see this channel (welcome, rules, announcements)
                if ch_cfg.get("unverified_visible") and unverified_obj:
                    ch_ow[unverified_obj] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=False,
                        read_message_history=True,
                    )

                # Extra roles (Commander access for app-review, win-verification)
                for extra_name in ch_cfg.get("extra_roles", []):
                    extra_role = discord.utils.get(guild.roles, name=extra_name)
                    if extra_role:
                        ch_ow[extra_role] = discord.PermissionOverwrite(
                            view_channel=True, send_messages=True,
                            read_message_history=True,
                        )

                try:
                    created = await guild.create_text_channel(
                        name=name, category=category, overwrites=ch_ow)

                    if ch_cfg["type"] == "news":
                        try:
                            await created.edit(type=discord.ChannelType.news)
                        except Exception:
                            pass
                except Exception as e:
                    await ctx.send(f"⚠️  Channel `{name}`: {e}")

        await status.edit(
            content=(
                "✅ **Server setup complete!**  All roles & channels created.\n\n"
                "💡 **Important next steps:**\n"
                "1. Move the **bot's role** above all created roles in "
                "Server Settings → Roles.\n"
                "2. New members now get **Unverified** (can only see "
                "#welcome, #rules, #announcements).\n"
                "3. They must complete the DM application to get **Rookie** + full access."
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
