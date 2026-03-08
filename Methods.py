import GlobalValues
import Modals
from datetime import datetime, timedelta
import random
import time
import json
from collections import OrderedDict
import asyncio
import re

import discord
from discord import Embed, Color, ui, ButtonStyle, Message
from discord.ext import commands, tasks
from discord.ui import Button, View, Select

ButtonVoteOne = GlobalValues.VOTEONE
ButtonVoteTwo = GlobalValues.VOTETWO

global base_coinage
base_coinage = 0.4


database_lock = asyncio.Lock()

class VerifyAgeView(View):
    def __init__(self, originalInteraction, botinfo, guild):
        super().__init__(timeout = None)
        self.inter = originalInteraction
        self.botinfo = botinfo

        self.eightteenRole = guild.get_role(GlobalValues.EIGHTTEENROLE)

        self.button_activation_time = datetime.now()
        self.check_button_stat.start()

        
    # Confirm button that triggers the callback when clicked
    @discord.ui.button(label="Verify", style=discord.ButtonStyle.green)
    async def confirm_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.inter.user.add_roles(self.eightteenRole)
        await self.inter.followup.send(f"You have been verified!", ephemeral=True)
        await self.botinfo.send(f"{button.user.display_name} verified {self.inter.user.display_name}")
        await button.response.defer()
        

    # Cancel button that just cancels the action
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red)
    async def cancel_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.inter.user.remove_roles(self.eightteenRole)
        await self.botinfo.send(f"{button.user.display_name} rejected {self.inter.user.display_name}")
        await button.response.defer()
        


    @tasks.loop(hours=24)
    async def check_button_stat(self):
        if (datetime.now() - self.button_activation_time) >= timedelta(days=7):
            self.approve_button.disabled = True
            self.decline_button.disabled = True
            await interaction.message.edit(view=self)
            self.check_button_stat.stop()



class ConfirmView(View):
    def __init__(self, birthday: datetime, callback, originalInteraction):
        super().__init__(timeout = 180)
        self.birthday = birthday
        self.callback = callback # Callback function to be called on confirmation
        self.inter = originalInteraction

        

    # Confirm button that triggers the callback when clicked
    @discord.ui.button(label="Yes, set my birthday!", style=discord.ButtonStyle.green)
    async def confirm_button(self, button: Button, interaction: discord.Interaction):
        # Call the provided callback to update the database (or perform any action)
        
        await self.callback(self.inter.user.id, self.birthday)
        await self.inter.followup.send(f"Your birthday has been set to {self.birthday.strftime('%B %d, %Y')}!", ephemeral=True)

    # Cancel button that just cancels the action
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel_button(self, button: Button, interaction: discord.Interaction):
        await self.inter.followup.send("Birthday setting canceled.", ephemeral=True)




async def getSortedCoinData():
    with open('CoinDatabase.json', 'r') as f:
        coinData = json.load(f)

    sorted_data = OrderedDict(sorted(coinData.items(), key=lambda item: (item[1][1], item[1][0]), reverse=True))

    with open('CoinDatabase.json', 'w') as f:
        json.dump(sorted_data, f)

    return sorted_data


async def update_member_role(member, new_role):
    # Remove all existing tier roles
    tier_roles = [role for role_name in GlobalValues.TIERS.keys()
        if (role := discord.utils.get(member.guild.roles, name=role_name))]
    
    # Remove any roles the member has that are in the tiers list
    for role in member.roles:
        if role in tier_roles and role != new_role:
            await member.remove_roles(role)

    if new_role:
        # Assign the new role if the member doesn't already have it
        if new_role not in member.roles:
            await member.add_roles(new_role)



async def get_user_or_nick(guild, uid):
    member = guild.get_member(uid)
    if member is None:
        member = await guild.fetch_member(uid)

    return member.display_name



async def list_to_string(listToConvert):
    cList = listToConvert
    retStr = ''
    for i in cList:
        retStr = retStr + str(i) + ", "

    return retStr[:-2]


async def check_channel(interaction, target_channel_id):
    if interaction.channel.id not in target_channel_id:
        await interaction.response.send_message(f"Please send this in <#{target_channel_id[0]}>", ephemeral = True)
        return True
    else:
        return False




class ConfirmDeleteView(ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @ui.button(label="Confirm", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Deleting roleplay...", ephemeral=True)

        with open('RPChannels.json', 'r') as file:
            channelData = json.load(file)

        del channelData[str(interaction.channel.id)]

        # Perform the deletion here
        await interaction.channel.delete(reason="Roleplay deleted by host.")
        with open('RPChannels.json', 'w') as file:
           json.dump(channelData, file)
           
        self.stop()  # Stop the view to disable buttons after deletion
        

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("Roleplay deletion canceled.", ephemeral=True)
        self.stop()  # Stop the view to disable buttons

    

###########################################################################
#                               CHARACTER METHODS
###########################################################################

class CharacterVerificationButtonView(View):
    def __init__(self, userCharacter, characterKey, channel, user, originalInteraction):
        super().__init__(timeout=None)
        self.button_activation_time = datetime.now()
        self.originalInteraction = originalInteraction
        
        self.userCharacter = userCharacter
        self.characterKey = characterKey
        self.channel = channel
        self.user = user

        # Create the buttons
        self.approve_button = Button(label="Approve", style=ButtonStyle.success)
        self.decline_button = Button(label="Decline", style=ButtonStyle.danger)

        # Assign the callbacks
        self.approve_button.callback = self.approve_callback
        self.decline_button.callback = self.deny_callback

        # Add buttons to the view
        self.add_item(ExtraInfoButton(userCharacter))
        self.add_item(self.approve_button)
        self.add_item(self.decline_button)

        self.check_button_stat.start()

    async def approve_callback(self, interaction: discord.Interaction):
        self.approve_button.disabled = True
        self.decline_button.disabled = False

        async with database_lock:
            with open("UserBiosDatabase.json", "r") as file:
                charDatabase = json.load(file)

            charDatabase[str(self.user.id)][self.characterKey]['verified'] = True

            with open("UserBiosDatabase.json", "w") as file:
                json.dump(charDatabase, file)

        await self.channel.send(f"{interaction.user.display_name} verified {self.characterKey}!")
        await self.originalInteraction.followup.send(f"{self.characterKey} was verified!", ephemeral=True)
        await interaction.response.defer()  
        await interaction.message.edit(view=self)  # Update the view

    async def deny_callback(self, interaction: discord.Interaction):
        self.approve_button.disabled = False
        self.decline_button.disabled = True
        
        async with database_lock:
            with open("UserBiosDatabase.json", "r") as file:
                charDatabase = json.load(file)
                
            charDatabase[str(self.user.id)][self.characterKey]['verified'] = False

            with open("UserBiosDatabase.json", "w") as file:
                json.dump(charDatabase, file)

        await self.channel.send(f"{interaction.user.display_name} declined {self.characterKey}.")
        await self.originalInteraction.followup.send(f"{self.characterKey} was declined. Check <#{GlobalValues.SERVER_INFO}> for what is allowed and what isn't allowed.", ephemeral=True)
        await interaction.response.defer()
        await interaction.message.edit(view=self)  # Update the view


    @tasks.loop(hours=24)
    async def check_button_stat(self):
        if (datetime.now() - self.button_activation_time) >= timedelta(days=7):
            self.approve_button.disabled = True
            self.decline_button.disabled = True
            await interaction.message.edit(view=self)
            self.check_button_stat.stop()




async def verify_character_display(interaction, character, channel, charDatabase):
        characterKey = character
        userCharacter = charDatabase[str(interaction.user.id)][characterKey]
        embedDisplay = ["Age","Gender","Species","Sexuality", "Personality", "Talents", "Strengths and Weaknesses", "Verified"]
        charColor = 0xff0000

        if userCharacter["verified"]:
            charColor = 0x00ff00

        if userCharacter["color"] is not None:
            charColor = userCharacter["color"]

        charEmbed = discord.Embed(title = "Verification Request: ", description = f"__**User:** {interaction.user.display_name}__\n\n**Character name:** {characterKey}", color = discord.Color(charColor))

        for category in embedDisplay:
            charInfo = userCharacter[str(category).lower().replace(' and ', '_')]
            if charInfo is not None or charInfo.strip() != "":  
                charEmbed.add_field(name = "", value = f"**{category}:** {charInfo}", inline = False)

        if userCharacter["image_url"] is not None:
            charEmbed.set_image(url = userCharacter["image_url"])

        view = CharacterVerificationButtonView(userCharacter, characterKey, channel, interaction.user, interaction)
        
        message = await channel.send(embed = charEmbed, view = view)



async def character_selector(interaction, member, charDatabase, callback, verification = False):
    member_characters = charDatabase[str(member.id)]

    # Filter options based on verification status
    if verification:
        options = [
            discord.SelectOption(label=char_name)
            for char_name, character_data in member_characters.items()
            if not character_data['verified']
        ]
        
        # If no unverified characters are found, inform the user and return
        if not options:
            await interaction.response.send_message("You have no unverified characters.", ephemeral=True)
            return
    else:
        options = [discord.SelectOption(label=char_name) for char_name in member_characters.keys()]

    select = Select(placeholder = "Choose a character:", options = options)

    select.callback = callback
    view = View()
    view.add_item(select)
    await interaction.response.send_message("Select a character:", view=view, ephemeral=True)


###########################################################################
#                               COIN CALC.
###########################################################################


def is_spam_message(message):
    """
    Enhanced spam check that first uses quick heuristics and then,
    if needed, runs a GPT-2 based perplexity check.
    """
    text = message.content

    # Preliminary filters (fast checks):
    if len(text) < 50:
        # Too short to be worth a complex check
        return False

    # Check for long sequences of repeated characters (e.g. "!!!!!!")
    if re.search(r"(.)\1{5,}", text):
        return True

    # Check for repeated words consecutively (e.g. "hello hello hello")
    if re.search(r"\b(\w+)(\s+\1){2,}", text, flags=re.IGNORECASE):
        return True

    # Check for a low ratio of alphanumeric characters
    if len(text) > 0:
        alnum_ratio = sum(c.isalnum() for c in text) / len(text)
        if alnum_ratio < 0.3:
            return True

    # Check for excessive whitespace
    if text.count(" ") > len(text) * 0.7:
        return True

    # Check for insufficient spaces (words being too long on average)
    words = text.split()
    avg_word_length = sum(len(word) for word in words) / max(len(words), 1)  # Avoid division by zero
    if avg_word_length > 8:  # Adjust this threshold as needed
        return True

    return False



def calculate_coins(message, user_last_message_time, user_messages_sent, user_prestige):
    current_time = time.time()
    message_length = len(message.content.replace("\t", "").replace("\n", ""))

    len_factor = max(min(message_length / 1000, 1.5), .15)

    time_factor = max(min((time.time() - user_last_message_time) / 120, 1.0), .5)


    if is_spam_message(message):
        return 0.0
    
    # Calculate time since last message was sent
    time_since_last_message = current_time - user_last_message_time

    time_penalty = 1  # No penalty if sufficient time has passed
    
    base_reward = 1.0

    # Time multiplier based on time since the last message
    if time_since_last_message < 15:  # Spamming
        time_multiplier = 0.01
    elif time_since_last_message < 30:  # Rapid messages
        time_multiplier = 0.4
    elif time_since_last_message < 60:  # Regular activity
        time_multiplier = .8
    elif time_since_last_message < 240:  # Regular activity
        time_multiplier = 1.0
    else:  # Long wait
        time_multiplier = 1.5

    # Message length multiplier
    if message_length < 10:  # Very short messages
        length_multiplier = 0.01
    elif message_length < 100:  # Short messages
        length_multiplier = 0.5
    elif message_length < 500:  # Moderate messages
        length_multiplier = 1.0
    elif message_length < 1000:  # Long messages
        length_multiplier = 1.15
    else:  # Very long messages
        length_multiplier = 1.25

    # Reward calculation
    reward = base_reward * time_multiplier * length_multiplier

    # Optional: Apply a cap or floor to the reward
    reward = max(0.01, min(reward, 1.5))

    if message.content.startswith("https:\\"):
        reward = 0.1
        
        
    words = message.content.split()
    avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
    complexity_factor = min(1.0, avg_word_length / 6)  # Maxes at 1 for word length >= 8

    random_factor = random.uniform(0.50, 1.5)

    #print(str(base_coinage) + "* (" + str(len_factor)+ "*" +str(time_factor)+ "*" +str(time_penalty)+ "*" +str(complexity_factor)+ "*" +str(random_factor)+"))*(" + str(user_prestige) + "+1)")

    coins = (base_coinage*(len_factor*time_factor*reward*complexity_factor*random_factor))*(user_prestige+1)

    # Message history boost (subtle)
    boost = 1 + (user_messages_sent * 0.0005)
    coins *= boost

    return round(coins, 6)


 
###########################################################################
#                               EXTRA INFO BUTTON
###########################################################################

class ExtraInfoButton(ui.Button):
    def __init__(self, user_character):
        super().__init__(label="Extra Info", style=discord.ButtonStyle.primary)
        self.user_character = user_character  # Store the user character data

    async def callback(self, interaction: discord.Interaction):
        extra_info = self.user_character['extra_info']

        if len(extra_info) > 1950:
            split_point = extra_info.rfind(" ", 0, 1950)
            if split_point == -1:
                split_point = 1950

            part1 = extra_info[:split_point]
            part2 = extra_info[split_point:].strip()

            await interaction.response.send_message(f"**Extra Info (Part 1):**\n{part1}", ephemeral=True)
            await interaction.followup.send(f"**Extra Info (Part 2):**\n{part2}", ephemeral=True)
        else:
            await interaction.response.send_message(f"**Extra Info:**\n {self.user_character['extra_info']}", ephemeral=True)



###########################################################################
#                               POLLS
###########################################################################


class PollView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.voted = False
        self.members_voted = {}

        self.results = {ButtonVoteOne: 0, ButtonVoteTwo: 0}  

        self.button_activation_time = datetime.now()
        
        self.button_one = Button(label=ButtonVoteOne, style=discord.ButtonStyle.success)
        self.button_one.callback = self.button_one_callback  # Assign the callback for button 1
        self.add_item(self.button_one)  # Add button 1 to the view

        self.button_two = Button(label=ButtonVoteTwo, style=discord.ButtonStyle.danger)
        self.button_two.callback = self.button_two_callback  # Assign the callback for button 2
        self.add_item(self.button_two)  # Add button 2 to the view


        self.button_three = Button(label="See Votes", style=discord.ButtonStyle.secondary)
        self.button_three.callback = self.button_three_callback
        self.add_item(self.button_three)



        self.check_button_status.start()


        
    async def poll_tally(self, interaction: discord.Interaction, UsersVote):
        vTitle = "***__" + ButtonVoteOne + " Or " + ButtonVoteTwo + "?__***"                             
        voted = discord.Embed(title = vTitle, color=0xff178e)

        voted.add_field(name = ButtonVoteOne, value = str(self.results[ButtonVoteOne]))
        voted.add_field(name = ButtonVoteTwo, value = str(self.results[ButtonVoteTwo]))


        await interaction.message.edit(embed=voted)
        await interaction.response.send_message("You voted " + UsersVote + "!", ephemeral=True)
        
    
    async def button_one_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in self.members_voted:
            self.results[ButtonVoteOne] += 1
            self.members_voted[interaction.user.id] = ButtonVoteOne
        else:
            if self.members_voted[interaction.user.id] != ButtonVoteOne:
                self.results[ButtonVoteOne] += 1
                self.results[ButtonVoteTwo] -= 1
                self.members_voted[interaction.user.id] = ButtonVoteOne
            else:
                return
            
        await self.poll_tally(interaction, ButtonVoteOne)

    
    async def button_two_callback(self, interaction: discord.Interaction):
        if interaction.user.id not in self.members_voted:
            self.results[ButtonVoteTwo] += 1
            self.members_voted[interaction.user.id] = ButtonVoteTwo
        else:
            if self.members_voted[interaction.user.id] != ButtonVoteTwo:
                self.results[ButtonVoteOne] -= 1
                self.results[ButtonVoteTwo] += 1
                self.members_voted[interaction.user.id] = ButtonVoteTwo
            else:
                return
        await self.poll_tally(interaction, ButtonVoteTwo)


    async def button_three_callback(self, interaction: discord.Interaction):

        voteOne = []
        voteTwo = []

        for i in self.members_voted:
            if self.members_voted[i] == ButtonVoteOne:
                voteOne.append(await get_user_or_nick(interaction.guild, i))
            else:
                voteTwo.append(await get_user_or_nick(interaction.guild, i))

        voteOneStr = await list_to_string(voteOne)
        voteTwoStr = await list_to_string(voteTwo)
                
        pollEmbed = discord.Embed(title = "**__User Votes!__**", color=0xff178e)
        pollEmbed.add_field(name = "__" + ButtonVoteOne + "__", value= voteOneStr.replace(", ", "\n"), inline=False)
        pollEmbed.add_field(name = "__" + ButtonVoteTwo + "__", value= voteTwoStr.replace(", ", "\n"), inline=False)

        await interaction.response.send_message(embed = pollEmbed, ephemeral=True)



    @tasks.loop(hours=24)
    async def check_button_status(self):
        if (datetime.now() - self.button_activation_time) >= timedelta(days=7):
            self.disabled = True
            await interaction.message.edit(view=self)
            self.check_button_status.stop()



###########################################################################
#                               VERIFICATION
###########################################################################

class VerificationButtonView(discord.ui.View):
    def __init__(self, guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="Verify Here", style=discord.ButtonStyle.primary, custom_id="verify_button")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Modals.VerificationModal(VerificationResponse, self.guild, interaction))



async def VerificationResponse(response, guild, interaction):
    bot_channel = guild.get_channel(GlobalValues.VERIFY_RESPONSES)

    embed = discord.Embed(
    color=discord.Color.green()
    )
    
    for i,q in enumerate(GlobalValues.VERIFICATION_QUESTIONS):
        count = str(i+1)
        embed.add_field(name="Q" + count + ": " + q, value=response[i], inline=False)

    view = VerificationModButtons(interaction)

    await bot_channel.send("New application from: " + interaction.user.mention + "        ||@here||")
    await bot_channel.send(embed=embed, view=view)


async def addVerificationButton(guild):
    guild = guild
    # Assuming you have message_id and channel_id as global variables
    channel = guild.get_channel(GlobalValues.VERIFY)  # Get the channel using the channel ID
    
    if channel is None:
        print(f"Channel with ID {channel_id} not found.")
        return

    await channel.purge(limit = 1)
    
    message = await channel.send(GlobalValues.VERIFY_MESSAGE)
    
    # Create a view with a button and add it to the existing message
    view = VerificationButtonView(guild)
    await message.edit(content=message.content, view=view)



class VerificationModButtons(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout = None)

        self.button_activation_time = datetime.now()
        self.user = interaction

        self.role = interaction.guild.get_role(GlobalValues.TRUSTED)
    
        # Create the first button
        self.verify_button = Button(label="Approve", style=discord.ButtonStyle.primary)
        self.verify_button.callback = self.verify_approve_callback  # Assign the callback for button 1
        self.add_item(self.verify_button)  # Add button 1 to the view

        # Create the second button
        self.decline_button = Button(label="Decline", style=discord.ButtonStyle.danger)
        self.decline_button.callback = self.decline_button_callback  # Assign the callback for button 2
        self.add_item(self.decline_button)  # Add button 2 to the view

        self.check_button_status.start()

    async def decline_button_callback(self, interaction: discord.Interaction):
        self.decline_button.disabled = True
        self.verify_button.disabled = False
        await interaction.message.edit(view=self)

        modNick = interaction.user.nick if interaction.user.nick else interaction.user.display_name

        await self.user.user.remove_roles(self.role)
        await interaction.response.send_message(modNick + " declined " + self.user.user.display_name)

    async def verify_approve_callback(self, interaction: discord.Interaction):
        self.verify_button.disabled = True
        self.decline_button.disabled = False
        await interaction.message.edit(view=self)

        modNick = interaction.user.nick if interaction.user.nick else interaction.user.display_name

        await self.user.user.add_roles(self.role)
        await interaction.response.send_message(modNick + " verified " + self.user.user.display_name)

        
    @tasks.loop(hours=24)
    async def check_button_status(self):
        if (datetime.now() - self.button_activation_time) >= timedelta(days=7):
            self.disabled = True
            await interaction.message.edit(view=self)
            self.check_button_status.stop()














        
