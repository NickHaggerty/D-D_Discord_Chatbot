import GlobalValues
import Modals
import Methods
import Webhook
import Events

from datetime import datetime, timedelta
import random
import time
import json
import asyncio
from typing import List
from collections import OrderedDict
import re
import os


from io import BytesIO

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select


# Initialize bot with the necessary intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='~', intents=intents, case_insensitive=True,)


global user_data
user_data = {}

global startup
startup = True

global webhookMessageDel
webhookMessageDel = None

global lbSize
lbSize = 20

global Event
Event = "None"



###########################################################################
#                               TIMERS
###########################################################################

@tasks.loop(hours = 48)
async def private_chat_checker():
    global startup
    if startup:
        return
    
    RPChannels = await get_RPChannels()
    currentTime = time.time()
    seconds_in_month = 30 * 24 * 60 * 60
    seconds_in_month_n_ten_days = (10 * 24 * 60 * 60) + seconds_in_month
    BotInfo = bot.get_channel(GlobalValues.BOT_INFO)
    delRPs = []

    for channel in RPChannels:
        if currentTime - RPChannels[channel]['last_reply_timestamp'] > seconds_in_month_n_ten_days:
            delRPs.append(channel)
            
        
        elif currentTime - RPChannels[channel]['last_reply_timestamp'] > seconds_in_month:
            channelObject = bot.get_channel(int(channel))
            await channelObject.send("This channel is inactive. Continue the RP to avoid auto deletion. (Deletes in 10 days from this first message.) @here")
     
    for rp in delRPs:
        channelObject = bot.get_channel(int(rp))

        if channelObject != None:
            await BotInfo.send(f"The private RP {channelObject.name} has been deleted due to inactivity.")
            del RPChannels[str(channelObject.id)]
            await channelObject.delete()
        
    with open('RPChannels.json', 'w') as file:
        json.dump(RPChannels, file)        



@tasks.loop(hours = 24)
async def verification_looper():
    global startup
    if startup:
        return
    
    reminders = bot.get_channel(GlobalValues.VERIFYREMINDER)
    alerts = GlobalValues.ALERTS
    
    await reminders.send(alerts[random.randint(0, len(alerts)-1)])

@tasks.loop(minutes = 1)
async def auto_save_user_data():
    #print("Autosaved...")
    with open('user_data.json', 'w') as file:
        json.dump(user_data, file)


@tasks.loop(hours = 1)
async def auto_update_all_users():
    guild = bot.get_guild(GlobalValues.GUILD)
    all_tiers = GlobalValues.TIERS
    coinDatabase = await get_coin_database()

    for member in coinDatabase:
        assigned_role = None
        for tier_name, threshold in all_tiers.items():
            if coinDatabase[member][0] > threshold * (coinDatabase[member][1] + 1):
                 assigned_role = discord.utils.get(guild.roles, name=tier_name)

        mem = guild.get_member(int(member))
        if mem:
            await Methods.update_member_role(mem, assigned_role)


@tasks.loop(hours = 24)
async def purge_all_databases():
    global startup
    if startup:
        startup = False
        return
    
    print("PURGING")
    global user_data
    guild = bot.get_guild(GlobalValues.GUILD)
    guildMembers = [str(member.id) for member in guild.members]
    one_week_seconds = 7 * 24 * 60 * 60
    
    coinDatabase = await get_coin_database()
    

    for uid in guildMembers:
        suid = str(uid)
        if suid in coinDatabase and suid in user_data:
            if time.time() - user_data[suid]["last_message_time"] >= one_week_seconds:
                await add_coins(-10, uid)
                
    for user in coinDatabase:
        if user not in guildMembers:
            del coinDatabase[user]

    for user in user_data:
        if user not in guildMembers:
            del user_data[user]

    with open("CoinDatabase.json", "w") as file:
        json.dump(coinDatabase, file)
    with open('user_data.json', 'w') as file:
        json.dump(user_data, file)
    

@tasks.loop(hours=48)
async def cleanup_webhooks():
    global startup
    if startup:
        return
    
    guild = bot.get_guild(GlobalValues.GUILD)
    webhooks = await guild.webhooks()

    for webhook in webhooks:
        try:
            await webhook.delete(reason="Periodic cleanup of old webhooks.")
            print(f"Deleted webhook: {webhook.name}")
        except Exception as e:
            print(f"Failed to delete webhook {webhook.name}: {e}")



###########################################################################
#                               EVENTS
###########################################################################

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(GlobalValues.WELCOME)  #welcome
    await channel.send("Welcome to the server " + member.mention + "!\n\n" + GlobalValues.WELCOME_MESSAGE)

    print("Adding Roles...")
    role = discord.utils.get(member.guild.roles, name='Unverified')
    await member.add_roles(role)


@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(GlobalValues.WELCOME)  #welcome
    await channel.send(member.name + " has left the server.")


@bot.event
async def on_command_error(ctx, error):
    if "not found" not in str(error):
        print(f"\n\nAn error occured: {str(error)}\n\n")
        await ctx.send("Error: " + str(error))
        channel = bot.get_channel(GlobalValues.BOT_INFO)
        await channel.send("Error occured: " + str(error))


@bot.event
async def on_member_ban(guild, member):
    channel = bot.get_channel(GlobalValues.WELCOME)   #welcome
    await channel.send(member.name + " has been banned.")




highlighted_messages = set()

@bot.event
async def on_reaction_add(reaction, user):

    if isinstance(reaction.emoji, str):
        return
    
    # Ensure it's the specified emote
    if reaction.emoji.id != GlobalValues.PILLOW_EMOTE:
        return

    # Check if the reaction is in an ignored category
    if reaction.message.channel.category and reaction.message.channel.category.id == 807680815424733184:
        return

    # Check if the reaction count is at least 3
    if reaction.count >= 3:

        # Check if the message has already been highlighted
        if reaction.message.id in highlighted_messages:
            return  # Skip processing if it's already been highlighted

        
        # Fetch the moments channel
        moments_channel = discord.utils.get(
            reaction.message.guild.text_channels, id=GlobalValues.SERVER_MOMENTS
        )
        
        # Create an embed to highlight the message
        embed = discord.Embed(
            title="Highlighted Message:",
            color=discord.Color.gold(),
        )

        # Add message content or handle attachments
        if reaction.message.content:
            embed.description = reaction.message.content

        if reaction.message.attachments:
            # Include the first valid image attachment
            for attachment in reaction.message.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                    embed.set_image(url=attachment.url)
                    break

        embed.set_author(
            name=reaction.message.author.display_name,
            icon_url=reaction.message.author.display_avatar.url,
        )
        embed.add_field(
            name="Jump to Message", value=f"[Click here]({reaction.message.jump_url})"
        )
        embed.set_footer(text=f"In #{reaction.message.channel}")

        # Send the embed to the moments channel
        await moments_channel.send(embed=embed)

        # Add the message ID to the set of highlighted messages
        highlighted_messages.add(reaction.message.id)
    

@bot.event
async def on_member_update(before, after):
    channel = bot.get_channel(GlobalValues.BOT_INFO)  #bot-info
    if str(before.nick) != str(after.nick):
        print("user made nickname changes")
        await channel.send(sep + "\n" + str(before.mention) +
                           " updated their nickname\nBefore: " +
                           str(before.nick) + "\nAfter: " + str(after.nick))


    if "Trusted" in str(after.roles):
        role = discord.utils.get(after.guild.roles, name='Unverified')
        if "Unverified" in str(after.roles):
            await after.remove_roles(role)

    else:
        role = discord.utils.get(after.guild.roles, name='Unverified')
        if "Unverified" not in str(after.roles):
            await after.add_roles(role)


@bot.event
async def on_message_delete(message):
    if message.author.id == GlobalValues.MYID:
        return
    
    if message.author == bot.user:
        return

    global webhookMessageDel
    if message.id == webhookMessageDel:
        return

    channel = bot.get_channel(GlobalValues.BOT_INFO)  # bot-info

    delEmbed = discord.Embed(
        title=f"{message.author.display_name}'s message was deleted from {message.channel.mention}",
        color=0xff178e
    )

    guild = message.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
        if entry.target.id == message.author.id and entry.created_at > message.created_at:
            # Get the user who deleted the message
            delEmbed.add_field(name="Deleted by:", value=entry.user.display_name, inline=False)
            break

    webCheck = ["www.", "https:"]
    message_content = message.content or "(No content)"
    
    # Check for links and send separately
    if any(i in message_content for i in webCheck):
        delEmbed.add_field(name="__Message:__", value='', inline=False)
        await channel.send(embed=delEmbed)
        
        for part in split_message(message_content):
            await channel.send(part)
    else:
        delEmbed.add_field(name="__Message:__", value=truncate_message(message_content), inline=False)
        await channel.send(embed=delEmbed)

        if len(message_content) > 1024:
            for part in split_message(message_content):
                await channel.send(part)
    
    # Handle attachments
    for attachment in message.attachments:
        try:
            await channel.send(f"Image: {attachment.proxy_url}")
        except:
            pass

def split_message(text, limit=2000):
    """Splits a message into chunks that fit within Discord's limits."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def truncate_message(text, limit=1024):
    """Truncates the message to fit in an embed field, adding '...' if necessary."""
    return text[:limit-3] + "..." if len(text) > limit else text



@bot.event
async def on_message_edit(before, after):
    if before.author.bot or after.author.bot:
        return

    if str(before.author.id) == str(GlobalValues.MYID):
        return

    if str(before.content) == str(after.content):
        return

    botInfo = bot.get_channel(GlobalValues.BOT_INFO)
    messageEdit = discord.Embed(
        title=f"{before.author.display_name} edited a message in {before.channel.mention}",
        color=0xff178e
    )
    
    # Function to truncate content to fit within the specified limit
    def truncate_content(content, limit):
        return content[:limit-3] + "..." if len(content) > limit else content

    # Truncate before and after content to fit within the embed field limit
    before_content = truncate_content(before.content or "(No content)", 1024)
    after_content = truncate_content(after.content or "(No content)", 1024)

    # Add before and after content to the embed
    messageEdit.add_field(name="Before:", value=before_content, inline=False)
    messageEdit.add_field(name="After:", value=after_content, inline=False)
    await botInfo.send(embed=messageEdit)



    
@bot.event
async def on_invite_create(invite):
    channel = bot.get_channel(GlobalValues.BOT_INFO)  #bot-info
    await channel.send(GlobalValues.SEPERATOR + "\n" + str(invite.inviter.mention) + " made an invite")


@bot.event
async def on_message(message):
    global user_data
    global adjustment
    await bot.process_commands(message)
    ctx = await bot.get_context(message)
    channel = ctx.channel
    user_id = message.author.id

    if message.author.id == GlobalValues.BOTID:
        return

    if ctx.message.webhook_id:
        return
    
    #function to prepare to calculate coin earnings
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {
                'last_message_time': time.time(),
                'messages_sent': 0,
                'last_logged_in': time.time() - 86400,
                'custom_role_id': None,
                'log_in_streak': 0,
                'birthdate': None,
            }
    user_info = user_data[str(user_id)]

    last_message_time = user_info['last_message_time']
    time_since_last_message = time.time() - last_message_time

    user_info['messages_sent'] += 1
    user_info['last_message_time'] = time.time()
    
    user_prestige = await get_coin_array(str(user_id))
    
    coinAdd = Methods.calculate_coins(message, last_message_time, user_info['messages_sent'], user_prestige[1])
    print("Coins alloted: ", coinAdd)

    #event method to calculate new coins given the event.
    global Event
    coinAdd = await Events.processEvent(Event, coinAdd, message, channel)
    #Add the coins
    print("Event Calculated Coins added: ", coinAdd)
    await add_coins(coinAdd, message.author.id)


    result = await Webhook.process_message_webhook_command(ctx, channel, user_id)
    if result:  # Check if result is not None
        worked, ctxMessage, msgID = result
        if worked:
            global webhookMessageDel
            webhookMessageDel = msgID
            await ctxMessage.delete()

    #Timestamp Update
    RPChannels = await get_RPChannels()
    if str(channel.id) in RPChannels:
        RPChannels[str(channel.id)]["last_reply_timestamp"] = round(time.time())
        with open('RPChannels.json', 'w') as file:
            json.dump(RPChannels, file)  
    

    #image rater
    rater = GlobalValues.CHARRATE.lower()
    if str(channel) == str(rater):
        if message.attachments:
            view = Methods.PollView()
            await ctx.reply(view=view)

    


###########################################################################
#                               COMMANDS
###########################################################################

class HelpPagination(View):
    def __init__(self, pages: list):
        super().__init__()
        self.pages = pages
        self.current_page = 0
        self.message = None  # To store the sent message

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary, disabled=True)
    async def prev_page(self, button: Button, interaction: discord.Interaction):
        """Go to the previous page."""
        self.current_page -= 1
        await self.update_page(interaction)
        

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, button: Button, interaction: discord.Interaction):
        """Go to the next page."""
        self.current_page += 1
        await self.update_page(interaction)
        

    async def send(self, interaction: discord.Interaction):
        """Send the initial message and store the reference."""
        embed = self.pages[self.current_page]
        self.update_buttons()

        # Send the initial response and fetch the message
        await interaction.response.send_message(embed=embed, view=self)
        self.message = await interaction.original_response()  # Get the sent message

    async def update_page(self, interaction: discord.Interaction):
        """Update the message with the current page."""
        self.update_buttons()
        embed = self.pages[self.current_page]

        # Use the stored message for editing
        await self.message.edit(embed=embed, view=self)
        

    def update_buttons(self):
        """Update the button states based on the current page."""
        self.children[0].disabled = self.current_page == 0
        self.children[1].disabled = self.current_page == len(self.pages) - 1


@bot.tree.command(name="help", description="Displays help information")
async def help_command(interaction: discord.Interaction):
    """Send a paginated help message."""
    pages = [
        discord.Embed(title=page["title"], description=page["description"], color=discord.Color.blue())
        for page in GlobalValues.COMMAND_PAGES
    ]
    view = HelpPagination(pages)
    await view.send(interaction)


    


@bot.tree.command(name="login", description="Login for your daily coins")
async def login_command(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.DAILY_LOGIN]):
        return

    global user_data

    if str(interaction.user.id) not in user_data:
           await interaction.response.send_message("Please send a normal message first, then try to log in.", ephemeral = True)     

    current_time = time.time()
    last_logged_time = user_data[str(interaction.user.id)]["last_logged_in"]
    
    time_elapsed = current_time - last_logged_time
    time_limit = 20 * 3600
    full_two_days = 2*24*60*60

    if time_elapsed > full_two_days:
        user_data[str(interaction.user.id)]["log_in_streak"] = 0
        
    if time_elapsed > time_limit:
        user_data[str(interaction.user.id)]["log_in_streak"] += 1
        coins = min(10, 1 + ((user_data[str(interaction.user.id)]["log_in_streak"] **  0.537)))
        global Events
        if Events == "Double-EXP":
            coins = coins*2
        await add_coins(coins, interaction.user.id)
        login = discord.Embed(title = f"+{round(coins,2)} Coins!", color = interaction.guild.get_member(interaction.user.id).color)
        user_data[str(interaction.user.id)]["last_logged_in"] = current_time
        user_coins = await get_coin_array(interaction.user.id)
        login.add_field(name = '', value = "Your new balance is: " + str(round(user_coins[0], 2)), inline = False)
        login.set_footer(text = "You are prestige: " + str(user_coins[1]) + "\nLog-in streak: " + str(user_data[str(interaction.user.id)]["log_in_streak"]))
        await interaction.response.send_message(embed = login)
    else:
        time_remaining = time_limit - time_elapsed
        
        hours = int(time_remaining // 3600)
        minutes = int((time_remaining % 3600) // 60)
        seconds = int(time_remaining % 60)
        
        await interaction.response.send_message(
            f"You already logged in. Next login available in: {hours} hours, {minutes} minutes, and {seconds} seconds.",
            ephemeral = True
        )
        return

    





@bot.tree.command(name="tiers", description="See the tiers in the server!")
async def tiers(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.COMMANDS, GlobalValues.DAILY_LOGIN]):
        return

    prestige = await get_coin_array(interaction.user.id)
    prestige[1] += 1
    
    tierembed = discord.Embed(title = f"***__Role Tier List For Prestige: {prestige[1]-1}__***", color = 0xff178e)
    guild = interaction.guild

    for num, tier in enumerate(GlobalValues.TIERS):
        role = discord.utils.get(guild.roles, name=tier)
        if num + 1 == len(GlobalValues.TIERS):
            tierembed.add_field(
                name = "",
                value = "Tier MAX: <@&" + str(role.id) + "> [" + str(GlobalValues.TIERS[tier]*prestige[1])[:-2] + " coins]",
                inline = False
                    )
        else:
            tierembed.add_field(
                name = "",
                value = "Tier " + str(num + 1) + ": <@&" + str(role.id) + "> [" + str(GlobalValues.TIERS[tier]*prestige[1])[:-2] + " coins]",
                inline = False
                    )

    tierembed.set_footer(text= "Use /update to update your role!\nUse /prestige to prestige!\n\nAll members who have prestiged have access to /customrole!")

    await interaction.response.send_message(embed = tierembed)


@bot.tree.command(name="leaderboard", description="See the top members of the server!")
async def leaderboard(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.COMMANDS, GlobalValues.DAILY_LOGIN]):
        return
    await interaction.response.defer()

    global lbSize
    
    sorted_data = await Methods.getSortedCoinData()

    
    embed = discord.Embed(
        title="**Leaderboard**", 
        description="Top members of the server!", 
        color=0xff178e 
    )

    
    # Keep track of how many users we've added
    added_users = 0
    # Iterate through the sorted data
    for idx, (user_id, data) in enumerate(sorted_data.items()):
        if added_users >= lbSize:
            break  # Stop once we've added 10 users
        
        try:
            user = await interaction.guild.fetch_member(user_id)  # Fetch user details
        except discord.NotFound:
            # If the user is not found (e.g., not in the server), skip to the next one
            continue
        
        coins, prestige = data
        coins = round(coins, 2)
        embed.add_field(
            name=f"{idx+1}. {user.display_name}",
            value=f"{coins} coins | Prestige Level: {prestige}",
            inline=False
        )

        # Increment the counter for added users
        added_users += 1

    await interaction.followup.send(embed=embed)

    

@bot.tree.command(name="jackpot")
async def jackpot(interaction: discord.Interaction):
    await interaction.response.send_message("Coming soon...")


@bot.tree.command(name="balance", description="View your account balance!")
async def balance(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.COMMANDS, GlobalValues.DAILY_LOGIN]):
        return
    
    coinBal = await get_coin_array(interaction.user.id)
    coinEmb = discord.Embed(title = f"***__{interaction.user.display_name}'s balance__***", color = interaction.guild.get_member(interaction.user.id).color)
    coinEmb.add_field(name = '', value = f"**Prestige:** {coinBal[1]}", inline = False)
    coinEmb.add_field(name = '', value = f"**Total {GlobalValues.COINS}:** {round(coinBal[0],2)}", inline = False)
    await interaction.response.send_message(embed = coinEmb)




@bot.tree.command(name="leaderboardposition", description="Shows where you are positioned in the server leaderboard!")
async def leaderboard_position(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.COMMANDS, GlobalValues.DAILY_LOGIN]):
        return
    await interaction.response.defer()
    
    sorted_data = await Methods.getSortedCoinData()

     # Get the user ID of the person calling the command
    user_id = str(interaction.user.id)

    # Find the user's position in the sorted leaderboard
    position = None
    for idx, (uid, data) in enumerate(sorted_data.items()):
        if uid == user_id:
            position = idx
            break

    # If the user is not found in the leaderboard, handle it (just a safeguard)
    if position is None:
        await interaction.followup.send("You are not on the leaderboard.", ephemeral = True)
        return

    embed = discord.Embed(title="Leaderboard Position", description=f"Here is your position on the leaderboard, {interaction.user.mention}!", color=0xff178e)

    # Calculate the range of positions to display
    start = max(0, position - 3)
    end = min(len(sorted_data), position + 4)

     # Add positions to the embed
    for idx in range(start, end):
        uid, (coins, prestige) = list(sorted_data.items())[idx]
        coins = round(coins)
        user = await bot.fetch_user(uid)
        embed.add_field(
            name=f"**{idx + 1}.** {user.display_name}",
            value=f"{coins} Coins | Prestige: {prestige}",
            inline=False
        )

    # Send the leaderboard
    await interaction.followup.send(embed=embed)




@bot.tree.command(name="setbirthday", description="Set your birthday for a little birthday surprise.")
async def set_birthday(interaction: discord.Interaction, day: int, month: int, year: int):
    global user_data

    if user_data[str(interaction.user.id)]["birthdate"]:
        retrieved_birthday = datetime.fromisoformat(user_data[str(interaction.user.id)]["birthdate"])
        await interaction.response.send_message(f"You have already set your birthday to {retrieved_birthday.strftime('%B %d, %Y')}. Please contact the owner if this is incorrect.", ephemeral=True)
        return
    
     # Validate month
    if month < 1 or month > 12:
        await interaction.response.send_message("Invalid month. Please choose a month between 1 and 12.", ephemeral=True)
        return
    
    # Validate day based on the month and year (leap year check included)
    try:
        birthday = datetime(year, month, day)
    except ValueError:
        await interaction.response.send_message("Invalid day for the selected month/year. Please check your date and try again.", ephemeral=True)
        return

    # Send a confirmation message with buttons
    confirm_view = Methods.ConfirmView(birthday, update_user_birthday, interaction)
    await interaction.response.send_message(
        f"Are you sure you would like to set **{birthday.strftime('%B %d, %Y')}** as your birthday? Once it is set, you can never change it.",
        view=confirm_view,
        ephemeral = True
    )
    


@bot.tree.command(name="update", description="Updates your role!")
async def update_user(interaction: discord.Interaction):
    guild = bot.get_guild(GlobalValues.GUILD)
    coins = await get_coin_array(interaction.user.id)
    all_tiers = GlobalValues.TIERS
    
    assigned_role = None
    for tier_name, threshold in all_tiers.items():
        if coins[0] > threshold * (coins[1] + 1):
            assigned_role = discord.utils.get(guild.roles, name=tier_name)

    
    await Methods.update_member_role(interaction.user, assigned_role)
    await interaction.response.send_message("You have been updated!", ephemeral = True)


@bot.tree.command(name="prestige", description="Once your reach prestige tier, use this to go to the next level.")
async def prestige_user(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.COMMANDS]):
        return
    
    userPrestige = await get_coin_array(interaction.user.id)
    if userPrestige[0] >= list(GlobalValues.TIERS.values())[-1]:
        database = await get_coin_database()
        database[interaction.user.id] = [0, userPrestige[1] + 1]

        with open("CoinDatabase.json", "w") as file:
            json.dump(database, file)

        assigned_role = interaction.guild.get_role(GlobalValues.STARTING_ROLE)
    
        await Methods.update_member_role(interaction.user, assigned_role)
        await interaction.response.send_message(f"You are now prestige {userPrestige[1] + 1}!")
    else:
        await interaction.response.send_message("You have not earned enough to prestige.", ephemeral = True)



@bot.tree.command(name="customrole", description="Create a custom role! (For all users prestige 1+)")
@app_commands.describe(name = "Set the name of your role.", color = "Set the color of your role. (Needs HEX code)")
async def custom_role(interaction: discord.Interaction, name: str, color: str = None):
    if await Methods.check_channel(interaction, [GlobalValues.COMMANDS]):
        return

    global user_data
    userPrestige = await get_coin_array(interaction.user.id)

    if userPrestige[1] == 0:
        await interaction.response.send_message("You must be prestige 1 or above to use this...")
        return

    guild = interaction.guild
    
    if user_data[str(interaction.user.id)]['custom_role_id'] is not None:
        role = interaction.guild.get_role(user_data[str(interaction.user.id)]["custom_role_id"])
        kwargs = {}
        if name is not None:
            kwargs['name'] = name
        if color is not None:
            kwargs['color'] = discord.Color(int(color.replace("#", ""), 16))  # Convert hex string to Color object

        await role.edit(**kwargs)
        await interaction.response.send_message(f"Custom role '{role.name}' edited!")
        return
    else:
        if name is None:
            await interaction.response.send_message("You must provide a name for the custom role.")
            return

        if color is None:
            color = "#FFFFFF"

        role = await guild.create_role(
            name=name, 
            color=discord.Color(int(color.replace("#", ""), 16)), 
            mentionable=False, 
            hoist=True
            )
           

        
        await interaction.user.add_roles(role)
        user_data[str(interaction.user.id)]['custom_role_id'] = role.id

        
        with open('user_data.json', 'w') as file:
            json.dump(user_data, file)

        await interaction.response.send_message(f"Custom role '{role.name}' created!")
        rolePosition = guild.get_role(GlobalValues.TIERS_ROLE).position
        
        while guild.get_role(role.id).position == 1:
            await role.edit(position = (rolePosition + 1))
            await asyncio.sleep(5)
            

@bot.tree.command(name="verifyage", description="Send your ID to verify your age and gain access to extra channels!")
@app_commands.describe(
    image="A picture of your own legal ID. Please censor personal information other then your Date Of Birth. Also include paper with your Username written on it in the photo.",
)
async def verifyage(interaction: discord.Interaction, image: discord.Attachment):
        guild = bot.get_guild(GlobalValues.GUILD)
        channel = bot.get_channel(GlobalValues.VERIFY_RESPONSES)
    
        await interaction.response.send_message("Thank you. Your ID has been sent to moderaters for verification.", ephemeral = True)    
    
        embed = discord.Embed(title = "ID Age Verification Request: ", description = f"__**User:** {interaction.user.mention}__")
        embed.set_image(url = image.url)

        verify_age_view = Methods.VerifyAgeView(interaction, channel, guild)
        
        await channel.send(embed=embed, view = verify_age_view)
    



@bot.tree.command(name="exportrp", description="Export your RP as a text file!")
async def export_rp(interaction: discord.Interaction):
    rpChannels = await get_RPChannels()
    rpCategories = await get_rp_categories()

    if interaction.user.id != GlobalValues.MYID:
        # Ensure the command is run in a private RP channel
        if interaction.channel.category not in rpCategories:
            await interaction.response.send_message("Must be sent in a private RP channel.", ephemeral=True)
            return

        # Check if the user is the host of the RP in the current channel
        if rpChannels.get(str(interaction.channel.id), {}).get("host") != interaction.user.id:
            await interaction.response.send_message(
                f"Only the host <@{rpChannels[str(interaction.channel.id)]['host']}> can use this command.", 
                ephemeral=True
            )
            return

    await interaction.response.defer()
    # Prepare to fetch messages from the current channel
    messages = []
    try:
        async for message in interaction.channel.history(limit=5000, oldest_first=True):  # You can adjust the limit
            messages.append(message)
    except discord.HTTPException as e:
        await interaction.followup.send(f"Error fetching messages: {e}", ephemeral=True)
        return

    # Start building the text content
    text_content = ""

    # Add each message to the text content
    for message in messages:
        text_content += f"{message.author}:\n{message.content}\n\n"

    # Create the text file
    file_name = f"rp_chat_log_{interaction.channel.name}.txt"
    try:
        with open(file_name, "w", encoding="utf-8") as file:
            file.write(text_content)
    except Exception as e:
        await interaction.followup.send(f"Error saving the text file: {e}", ephemeral=True)
        return

    # Send the text file to the user
    await interaction.followup.send(f"Here is the exported RP chat log for the channel '{interaction.channel.name}'.", file=discord.File(file_name))

    # Clean up by deleting the file after sending
    os.remove(file_name)



@bot.tree.command(name="roll", description="Rolls multiple dice using NdM format, like 3d6 or 2d20.")
@app_commands.describe(dice="Dice to roll in NdM format (e.g., 3d6, 2d20, 1d100)")
async def roll(interaction: discord.Interaction, dice: str):
    # Validate and parse format
    match = re.fullmatch(r"(\d{1,4})d(\d{1,4})", dice.lower())
    if not match:
        await interaction.response.send_message("Invalid format. Use NdM (e.g., 3d6 or 2d20).", ephemeral=True)
        return

    num_dice, sides = map(int, match.groups())

    # Reasonable limits
    if num_dice < 1 or sides < 2:
        await interaction.response.send_message("Number of dice must be at least 1 and each die must have at least 2 sides.", ephemeral=True)
        return
    if num_dice > 1000:
        await interaction.response.send_message("Too many dice! Please roll 1000 or fewer at a time.", ephemeral=True)
        return

    # Roll the dice
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    total = sum(rolls)

    # Only show individual rolls if there are fewer than 50
    if num_dice <= 50:
        rolls_str = ", ".join(map(str, rolls))
        msg = f"🎲 You rolled **{dice}**\nTotal: **{total}**\nIndividual rolls: {rolls_str}"
    else:
        msg = f"🎲 You rolled **{dice}**\nTotal: **{total}** (individual rolls hidden for large counts)"

    await interaction.response.send_message(msg)


    

###########################################################################
#                               CHARACTER COMMANDS
###########################################################################

@bot.tree.command(name="createcharacter", description="Create A Character Bio!")
@app_commands.describe(
    name="Character's full name", 
    age="Character's age (Must be a number)", 
    gender="Character's gender", 
    species="Character's species", 
    sexuality="Character's sexuality",
    image="Character Image",
    color="Character's Color (hex code)",
    sign = "Characters command sign. (put this at the front of a message in a public RP to play as this character)",
)
async def create_character(interaction: discord.Interaction, name: str, age: int, gender: str, species: str, sexuality: str, sign: str = None, image: discord.Attachment = None, color: str = None):
    if await Methods.check_channel(interaction, [GlobalValues.CHARACTER_BIOS]):
        return
    image_url = None
    if image:
        if image.content_type.startswith("image/"):

            img_data = await image.read()
            img_file = BytesIO(img_data)
            img_file.seek(0)
            file = discord.File(fp=img_file, filename="character_image.jpg")

            # Send a regular message with the image URL
            msg = await interaction.channel.send(f"Character Image for {name}\nThis is required to save the character image.", file=file)
        
            image_url = msg.attachments[0].url

    charData = await get_character_database()
    if str(interaction.user.id) in charData:
        if any(existing_name.lower() == name.lower() for existing_name in charData[str(interaction.user.id)]):
            await interaction.response.send_message(f"You already have a character named {name}.", ephemeral=True)
            return

    await interaction.response.send_modal(Modals.CharacterBioModal(name, age, gender, species, sexuality, sign, image_url, color))


@bot.tree.command(name="editcharacter", description="Edit an existing character.")
@app_commands.describe(image="You can add an image to edit for a character!")
async def edit_character(interaction: discord.Interaction, image: discord.Attachment = None):
    if await Methods.check_channel(interaction, [GlobalValues.CHARACTER_BIOS]):
        return
    
    user_id = str(interaction.user.id)
    charDatabase = await get_character_database()

    if user_id not in charDatabase:
        await interaction.response.send_message(f"{member.display_name} does not have any characters.", ephemeral=True)
        return

    async def edit_character_machine(interaction: discord.Interaction):
        if image:
            if image.content_type.startswith("image/"):
                with open("UserBiosDatabase.json", "r") as file:
                    charDatabase_ = json.load(file)
                
                img_data = await image.read()
                img_file = BytesIO(img_data)
                img_file.seek(0)
                file = discord.File(fp=img_file, filename="character_image.jpg")
                
                message = await interaction.channel.send(
                    f"Character Image Edited.\nThis is required to save the character image.",
                    file=file
                )

                charDatabase_[user_id][interaction.data["values"][0]]["image_url"] = message.attachments[0].url

                
                with open("UserBiosDatabase.json", "w") as file:
                    json.dump(charDatabase_, file)
                return
                

        charData = charDatabase[user_id][interaction.data["values"][0]]
        options = [
                discord.SelectOption(label=key)
                for key in charData.keys()
                if key not in {"verified", "image_url"}  # Exclude these keys
                    ]

        select = Select(placeholder = f"Choose a category.", options = options)

        async def edit_callback(edit_interaction: discord.Interaction):
            selected = edit_interaction.data["values"][0]
            await edit_interaction.response.send_modal(Modals.EditCharacterModal(selected, user_id, interaction.data["values"][0]))


        select.callback = edit_callback
        view = View()
        view.add_item(select)
        await interaction.response.send_message(f"Choose what to edit for {interaction.data['values'][0]}:", view=view, ephemeral = True)
    
    await Methods.character_selector(interaction, interaction.user, charDatabase, edit_character_machine)


    
@bot.tree.command(name="displaycharacter", description="See yours, or others characters.")
@app_commands.describe(member="The owner of the character to display")
async def display_character(interaction: discord.Interaction, member: discord.Member = None):
    if await Methods.check_channel(interaction, [GlobalValues.CHARACTER_BIOS, GlobalValues.COMMANDS]):
        return

    memUser = interaction.user
    user_id = str(interaction.user.id)
    if member:
        memUser = member
        user_id = str(member.id)
    charDatabase = await get_character_database()

    if user_id not in charDatabase:
        await interaction.response.send_message(f"{memUser.display_name} does not have any characters.", ephemeral=True)
        return

    async def make_char_display(interaction: discord.Interaction):
        characterKey = interaction.data["values"][0]
        userCharacter = charDatabase[user_id][characterKey]
        embedDisplay = ["Age","Gender","Species","Sexuality", "Personality", "Talents", "Strengths and Weaknesses", "Verified"]
        charColor = 0xff0000

        if userCharacter["verified"]:
            charColor = 0x00ff00

        if userCharacter["color"] is not None:
            charColor = userCharacter["color"]

        charEmbed = discord.Embed(title = characterKey, color = discord.Color(charColor))

        for category in embedDisplay:
            charInfo = userCharacter[str(category).lower().replace(' and ', '_')]
            if charInfo is not None and str(charInfo).strip() != "":  
                charEmbed.add_field(name = "", value = f"**{category}:** {charInfo}", inline = False)

        if userCharacter["image_url"] != None:
            charEmbed.set_image(url = userCharacter["image_url"])

        if userCharacter["sign"]:
            charEmbed.set_footer(text = f"Command sign: {userCharacter['sign']}")
        view = discord.ui.View()
        view.add_item(Methods.ExtraInfoButton(userCharacter))

        await interaction.response.send_message(f"<@{interaction.user.id}> displayed this character __**owned by: {memUser.display_name}**__", embed = charEmbed, view=view)


    await Methods.character_selector(interaction, memUser, charDatabase, make_char_display)

    


@bot.tree.command(name="deletecharacter", description="Forever deletes a character.")
async def delete_character(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.CHARACTER_BIOS]):
        return
    charDatabase = await get_character_database()

    async def remove_character(interaction: discord.Interaction):
        character_name = interaction.data['values'][0]
        view = View()
        
        async def confirm_callback(yes_interaction: discord.Interaction):
            del charDatabase[str(interaction.user.id)][character_name]
            await yes_interaction.response.send_message(f"Character {character_name} deleted.", ephemeral=True)
            with open("UserBiosDatabase.json", "w") as file:
                json.dump(charDatabase, file)
            view.stop()

        
        async def cancel_callback(no_interaction: discord.Interaction):
            await no_interaction.response.send_message("Character deletion canceled.", ephemeral=True)
            view.stop()

        yes_button = Button(label="Yes", style=discord.ButtonStyle.danger)
        yes_button.callback = confirm_callback
        view.add_item(yes_button)

        no_button = Button(label="No", style=discord.ButtonStyle.secondary)
        no_button.callback = cancel_callback
        view.add_item(no_button)

        # Send the confirmation message with buttons
        await interaction.response.send_message(
            f"Are you sure you want to delete {character_name}?",
            view=view,
            ephemeral=True
        )
        
        
    
    await Methods.character_selector(interaction, interaction.user, charDatabase, remove_character)


@bot.tree.command(name="verifycharacter", description="Request for a character to be verified! (make sure all sections are filled out.)")
async def request_verification_character(interaction: discord.Interaction):
    if await Methods.check_channel(interaction, [GlobalValues.CHARACTER_BIOS]):
        return
    
    charDatabase = await get_character_database()

    if str(interaction.user.id) not in charDatabase:
        await interaction.response.send_message("You must make a character first...", ephemeral=True)
        return

    async def verify_character(interaction: discord.Interaction):
        characterKey = interaction.data['values'][0]
        channel = bot.get_channel(GlobalValues.VERIFY_RESPONSES)
        isVerification = True
        
        await Methods.verify_character_display(interaction, characterKey, channel, charDatabase)
        await interaction.response.send_message(f"{interaction.data['values'][0]} is being reviewed for verification.", ephemeral=True)

    
    await Methods.character_selector(interaction, interaction.user, charDatabase, verify_character, True)


###########################################################################
#                               ROLEPLAY COMMANDS
###########################################################################


@bot.tree.command(name="createroleplay", description="Creates a new roleplay.")
@app_commands.describe(rp_name="Name of the channel you want to make!", member="Must add one member. Use /addusertoroleplay after creation to add more members.")
async def create_roleplay(interaction: discord.Interaction, rp_name: str, member: discord.Member):
    rpCategories = await get_rp_categories()
    guild = bot.get_guild(GlobalValues.GUILD)
    rpChannels = await get_RPChannels()

    if member.id == GlobalValues.BOTID:
        await interaction.response.send_message("You can't add the bot you hekken silly.")
        return

    all_full = all(len(category.channels) >= 50 for category in rpCategories)
        
    if all_full:
        last_category_position = rpCategories[-1].position
        romanNum = int_to_roman(len(rpCategories)+1)
        catName = "❤ Private RP " + romanNum + " ❤"
        new_category = await guild.create_category(catName, position=last_category_position + 1)
        rpCategories.append(new_category)  # Add the new category to the list
    

    for category in rpCategories:
        if len(category.channels) < 50:

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True)  # Grant the command user access
            }
            
            overwrites[member] = discord.PermissionOverwrite(read_messages=True)  # Grant specified member access

            name = rp_name.lower().replace(" ", "-")
            name = re.sub(r'[^a-z0-9\-_]', '', name)
    
            rp_channel = await guild.create_text_channel(name[:100], overwrites=overwrites, category=category)
            await rp_channel.send(f"Roleplay successfully made! {interaction.user.mention} & {member.mention}")

            rpChannels[rp_channel.id] = {
                            "host": interaction.user.id,
                            "last_reply_timestamp": int(time.time()),
                            "users": [interaction.user.id, member.id],
                                        }
            with open('RPChannels.json', 'w') as file:
                json.dump(rpChannels, file)

            await interaction.response.send_message(f"Made new roleplay: {rp_channel.mention}", ephemeral = True)
            
            return

    await interaction.response.send_message("Command failed, and it shouldn't even be possible to get this message so...- ping owner cuz they suck at coding.")


@bot.tree.command(name="addusertoroleplay", description="Adds member to roleplay.")
async def add_user_roleplay(interaction: discord.Interaction, member: discord.Member):
    rpChannels = await get_RPChannels()
    rpCategories = await get_rp_categories()

    channel = interaction.channel
    guild = interaction.guild
    
    if interaction.channel.category not in rpCategories:
        await interaction.response.send_message("Must be sent in a private RP channel.", ephemeral = True)
        return

    if rpChannels[str(interaction.channel.id)]["host"] != interaction.user.id:
        host = guild.get_member(rpChannels[str(interaction.channel.id)]['host'])
        await interaction.response.send_message(f"Must be the channel host to add members. The host is {host.display_name}.", ephemeral = True)
        return

    if member.id in rpChannels[str(interaction.channel.id)]['users']:
        await interaction.response.send_message("Member is already in this channel.", ephemeral = True)
        return
        
    await channel.set_permissions(member, read_messages=True)
    rpChannels[str(interaction.channel.id)]['users'].append(member.id)
    with open('RPChannels.json', 'w') as file:
        json.dump(rpChannels, file)
    await interaction.response.send_message(f"{member.mention} has been added to this roleplay channel.")
    


@bot.tree.command(name="leaveroleplay", description="Remove yourself from a roleplay.")
async def leave_roleplay(interaction: discord.Interaction):
    rpChannels = await get_RPChannels()
    rpCategories = await get_rp_categories()

    if interaction.channel.category not in rpCategories:
        await interaction.response.send_message("Must be sent in a private RP channel.", ephemeral = True)
        return

    if rpChannels[str(interaction.channel.id)]["host"] == interaction.user.id:
        await interaction.response.send_message(f"Channel host cannot leave the roleplay. Maybe use /deleteroleplay instead?", ephemeral = True)
        return

    await interaction.response.send_message("You left this roleplay.", ephemeral = True)
    
    await interaction.channel.set_permissions(interaction.user, read_messages=False)

    rpChannels[str(interaction.channel.id)]['users'].remove(interaction.user.id)
    with open('RPChannels.json', 'w') as file:
        json.dump(rpChannels, file)


@bot.tree.command(name="deleteroleplay", description="Delete roleplay. (Only the creator of the chat can use this)")
async def delete_roleplay(interaction: discord.Interaction):
    rpChannels = await get_RPChannels()
    rpCategories = await get_rp_categories()

    if interaction.channel.category not in rpCategories:
        await interaction.response.send_message("Must be sent in a private RP channel.", ephemeral = True)
        return

    if rpChannels[str(interaction.channel.id)]["host"] != interaction.user.id:
        await interaction.response.send_message(f"Only the host <@{rpChannels[str(interaction.channel.id)]['host']}> can use this command.", ephemeral = True)
        return

    view = Methods.ConfirmDeleteView()
    await interaction.response.send_message("Are you sure you want to delete this roleplay? All data from channel will be lost...", view=view, ephemeral=True)
    



@bot.tree.command(name="replyroleplay", description="Gives you a list of your roleplays where the last response was not from you.")
async def reply_roleplay(interaction: discord.Interaction):
    rpChannels = await get_RPChannels()
    uid = interaction.user.id
    needReply = []
    savedInter = interaction
    await savedInter.response.defer()
    User_bios = await get_character_database()

    async def check_last_message(channel_id, User_bio):
        User_bios = User_bio
        channelObject = bot.get_channel(int(channel_id))
        if channelObject is None:
            return None  # Skip if channel not found

        last_message = None
        async for message in channelObject.history(limit=1):
            last_message = message
            break

        webhook_name = last_message.author.name if last_message.author.bot else None

        # Check if the user is in the channel and if they need to reply
        if last_message and last_message.author.id != uid and uid in rpChannels[channel_id]["users"]:
            if webhook_name and webhook_name in User_bios.get(str(uid), {}):
                return None  # Ignore this channel, the webhook message belongs to the user
            return channel_id  # User needs to reply in this channel
        return None

    # Process channels in batches
    BATCH_SIZE = 10  # Number of channels to process at a time
    channel_ids = list(rpChannels.keys())
    for i in range(0, len(channel_ids), BATCH_SIZE):
        batch = channel_ids[i:i + BATCH_SIZE]
        tasks = [check_last_message(channel_id, User_bios) for channel_id in batch]
        results = await asyncio.gather(*tasks)
        needReply.extend([channel_id for channel_id in results if channel_id])
        await asyncio.sleep(0.5)  # Delay between batches

    # Prepare and send the response
    if needReply:
        chats = "***__Roleplay Response Needed:__***" + ''.join(f"\n<#{rpchat}>" for rpchat in needReply)
        await savedInter.followup.send(chats, ephemeral=True)
    else:
        await savedInter.followup.send("All RP's have replies!", ephemeral=True)
   




###########################################################################
#                               ADMIN
###########################################################################

@bot.tree.command(name="adminhelp")
async def adminhelp(interaction: discord.Interaction):
    await interaction.response.send_message("addcoins, checkuserbalance, clear, ~say, leaderboardsize, eventselect", ephemeral = True)

@bot.tree.command(name="whoscharacter", description= "Find who owns a specific character.")
@app_commands.describe(charactername="The character name to search")
async def whos_character(interaction: discord.Interaction, charactername: str):
    charData = await get_character_database()  # Fetch the character database
    characterName = charactername.lower()  # Convert input to lowercase for case-insensitive matching
    
    # Iterate through the data to find the character
    for user_id, characters in charData.items():
        for char_name in characters.keys():
            if char_name.lower() == characterName:  # Compare case-insensitively
                user = await bot.fetch_user(user_id)  # Fetch user object for the ID
                await interaction.response.send_message(
                    f"Character '{char_name}' is owned by: {user.name} (<@{user.id}>)", 
                    ephemeral=True
                )
                return

    # If character is not found
    await interaction.response.send_message(
        f"Character '{characterName}' not found in the database.", 
        ephemeral=True
    )


@bot.tree.command(name="addcoins", description="The amount of coins to add")
@app_commands.describe(user="The user to give the coins to")
async def add_coins_to_user(interaction: discord.Interaction, user: discord.Member, amount: float):
    await add_coins(amount, user.id)
    await interaction.response.send_message(f"Added {amount} coins to {user.display_name}'s balance.", ephemeral=True)


@bot.tree.command(name="checkuserbalance", description="Checks how many coins a user has")
@app_commands.describe(member="The user to check")
async def check_user_balance(interaction: discord.Interaction, member: discord.Member):
    userCoins = await get_coin_array(member.id)[0]
    await interaction.response.send_message(f"{member.display_name} has {userCoins} coins", ephemeral = True)
    

@bot.tree.command(name="clear", description="Clears X messages from the channel the command is sent in.")
@app_commands.describe(messagestoclear="How many messages to remove")
async def clear(interaction: discord.Interaction, messagestoclear: int):
    await interaction.channel.purge(limit = messagestoclear)

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, *, msg):
    await ctx.message.delete()
    await ctx.send(msg)


@bot.tree.command(name="leaderboardsize", description="Changes how many are displayed on the leaderboard.")
async def leaderboard_size(interaction: discord.Interaction, size: int):
    global lbSize
    lbSize = size
    if lbSize > 25 or lbSize <= 0:
        lbSize = 25
    await interaction.response.send_message(f"Leaderboard size updated to {lbSize}")


@bot.tree.command(name="eventselect", description="Select an event you want to run for the server.")
async def eventselect(interaction: discord.Interaction, reset: bool = True):
    EVENTS = GlobalValues.EVENTS
    
    # Create a Select menu for choosing events
    select = Select(
        placeholder="Choose an event",  # Placeholder text
        min_values=1,  # Minimum number of selections
        max_values=1,  # Maximum number of selections
        options=[discord.SelectOption(label=event) for event in EVENTS]  # List of events
    )
    
    # Define the callback for when an option is selected
    async def select_callback(interaction: discord.Interaction):
        global Event
        Event = select.values[0]  # Update Event to the selected option
        await Events.createEvent(Event, reset, bot)
        await interaction.response.send_message(f"Event updated to: {Event}", ephemeral=True)
    
    # Link the callback to the Select menu
    select.callback = select_callback
    
    # Create a View to display the Select menu
    view = View()
    view.add_item(select)
    
    # Send the message with the Select menu
    await interaction.response.send_message("Please select an event:", view=view, ephemeral=True)


###########################################################################
#                               DATABASES
###########################################################################


async def readuser_data():
    global user_data
    with open('user_data.json', 'r') as file:
        user_data = json.load(file)


async def get_RPChannels():
    with open('RPChannels.json', 'r') as file:
        return json.load(file)


async def get_character_database():
    with open("UserBiosDatabase.json", "r") as file:
        return json.load(file)


async def get_coin_database():
    with open("CoinDatabase.json", "r") as file:
        return json.load(file)

###########################################################################
#                               METHODS
###########################################################################


async def update_user_birthday(user_id: int, birthday: datetime):
    # Simulate updating the global user data (this could be a database operation)
    global user_data
    birthday_str = birthday.isoformat()
    user_data[str(user_id)]["birthdate"] = birthday_str


async def get_rp_categories():
    guild = bot.get_guild(GlobalValues.GUILD)
    cats = []

    for category in guild.categories:
         if category.name.startswith("❤ Private RP"):
            cats.append(category)
    return cats
    

async def get_coin_array(uid):
    database = await get_coin_database()

    if str(uid) not in database:
        database[str(uid)] = [0.0, 0]

    with open("CoinDatabase.json", "w") as file:
        json.dump(database, file)
        
    return database[str(uid)]
    

async def add_coins(coins, uid):
    global user_data
    database = await get_coin_database()

    if str(uid) not in database:
        database[str(uid)] = [0.0, 0]
    
    userCoins = database[str(uid)]
    userCoins[0] += coins


    if userCoins[0] <= 0:
        if userCoins[1] > 0:
            userCoins[1] -= 1
            userCoins[0] += GlobalValues.TIERS["PRESTIGE"] * (userCoins[1]+1)
            
        else:
            del database[str(uid)]
            del user_data[str(uid)]
            with open("CoinDatabase.json", "w") as file:
                json.dump(database, file)
            return
            

    database[str(uid)] = userCoins
    with open("CoinDatabase.json", "w") as file:
        json.dump(database, file)


def int_to_roman(num):
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        "Ⅿ", "ⅭⅯ", "Ⅾ", "ⅭⅮ",
        "Ⅽ", "ⅩⅭ", "Ⅼ", "ⅩⅬ",
        "Ⅹ", "Ⅸ", "Ⅴ", "Ⅳ",
        "Ⅰ"
    ]
    roman_numeral = ""
    for i in range(len(val)):
        count = num // val[i]
        roman_numeral += syms[i] * count
        num -= val[i] * count
    return roman_numeral



###########################################################################
#                               TEMPORARY
###########################################################################


@bot.command()
async def addme(ctx):
    # Ensure you only add yourself
    my_id = GlobalValues.MYID
    if ctx.author.id != my_id:
        return
    
    # Get the current RP_Channels data
    RP_Channels = await get_RPChannels()

    # Check if the channel is in the RP_Channels
    if str(ctx.channel.id) in RP_Channels:
        # If the channel exists in RP_Channels, add your ID to the "users" list
        if my_id not in RP_Channels[str(ctx.channel.id)]["users"]:
            RP_Channels[str(ctx.channel.id)]["users"].append(my_id)
            
            # Save the updated data back to the file
            with open('RPChannels.json', 'w') as file:
                json.dump(RP_Channels, file)

            await ctx.send("You have been added to this RP channel!")
        else:
            await ctx.send("You are already added to this RP channel.")
    else:
        await ctx.send("This channel is not a registered RP channel.")




@bot.command()
@commands.has_permissions(administrator=True)
async def getrps(ctx):
    guild = bot.get_guild(GlobalValues.GUILD)
    RP_Channels = await get_RPChannels()

    bot_id = GlobalValues.BOTID
    my_id = GlobalValues.MYID

    # Only allow the command if it is being run by the specified user
    if ctx.author.id != my_id:
        return

    # Set of IDs to exclude
    excluded_ids = {my_id, bot_id, 1222548162741538938, 557628352828014614, 204255221017214977, 
                    861820023353245766, 919707437878091828}

    # Iterate over each category and channel
    for category in guild.categories:
        if str(category)[:12] == "❤ Private RP":
            for channel in category.channels:
                # Get the members with access to the channel
                members_with_access = [
                    member.id for member in ctx.guild.members
                    if channel.permissions_for(member).view_channel and member.id not in excluded_ids
                ]
                
                # Only process channels with members who have access
                if members_with_access:
                    # If the channel is not already in RP_Channels, add it
                    if channel.id not in RP_Channels:
                        RP_Channels[channel.id] = {
                            "host": members_with_access[0],  # Set the first member as the host
                            "last_reply_timestamp": int(time.time()),  # Set the current timestamp
                            "users": members_with_access,  # List of users with access
                        }
                    else:
                        # If the channel is already in RP_Channels, update only if needed
                        RP_Channels[channel.id]["users"] = members_with_access
                        RP_Channels[channel.id]["last_reply_timestamp"] = int(time.time())

    # Save the updated RP_Channels data back to the JSON file
    try:
        with open('RPChannels.json', 'w') as file:
            json.dump(RP_Channels, file)
        await ctx.send("Got RPs")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")




@bot.command()
@commands.has_permissions(administrator=True)
async def bioreformat(ctx):
    guild = bot.get_guild(GlobalValues.GUILD)

    my_id = GlobalValues.MYID
    if ctx.author.id != my_id:
        return
    
    with open("OLD_bios.json", "r") as file:
        oldBios = json.load(file)
    with open("UserBiosDatabase.json", "r") as fileTwo:
        characterBios = json.load(fileTwo)

    
    
    for old_character in oldBios:
        uid = await get_user_id_by_name(guild, oldBios[old_character]['Owner'])
        if uid is not None:
            
            if str(uid) not in characterBios:
                characterBios[str(uid)] = {}
            characterInfo = oldBios[old_character]["Bio"].split("\n")
            charresult = [s.replace("\n", "").split(": ", 1)[1] for s in characterInfo if ": " in s]         
            if characterInfo[0] != 'no Bio':
                character_details = {
                    "age": charresult[1],
                    "gender": charresult[2],
                    "species": charresult[3],
                    "sexuality": charresult[6],
                    "talents": "",
                    "personality": "",
                    "strengths_weaknesses": "",
                    "extra_info": charresult[9],
                    "image_url": oldBios[old_character]["Image"],
                    "verified": False,
                    "color": None,
                    "sign": None,
                    }
                
                name = charresult[0]
                characterBios[str(uid)][name] = character_details

    with open("UserBiosDatabase.json", "w") as file:
        json.dump(characterBios, file)
        
    await ctx.send("Reformated Old Bios.")
            

async def get_user_id_by_name(guild, old_name):
    try:
        username, discriminator = old_name.split('#')
    except:
        username = old_name
        discriminator = ''
    

    # Loop through the members in the guild
    for member in guild.members:
        if member.name == username:
            return member.id  # Return the User ID

    # If the user is not found in the guild
    return None


###########################################################################
#                               STARTUP
###########################################################################

@bot.command()
@commands.has_permissions(administrator=True)
async def sync(ctx):
    my_id = GlobalValues.MYID
    if ctx.author.id != my_id:
        return

    
    await ctx.send("Syncing Commands...")
    try:
        synced = await ctx.bot.tree.sync()#guild=ctx.guild)  # Syncs commands to Discord
        await ctx.send(f"Synced {len(synced)} command(s)")
        print(synced)
    except Exception as e:
       await ctx.send(e)


@bot.event
async def on_ready():
    print(f'Bot is online as {bot.user}')
    guild = bot.get_guild(GlobalValues.GUILD)
    
    ##startup commands
    await Methods.addVerificationButton(guild)
    verification_looper.start()
    await readuser_data()
    auto_save_user_data.start()
    auto_update_all_users.start()
    private_chat_checker.start()
    cleanup_webhooks.start()
    purge_all_databases.start()
    



# Start the bot with your token
bot.run(GlobalValues.BOT_TOKEN)
