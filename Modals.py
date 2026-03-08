import GlobalValues
import json
import asyncio

import discord
from discord import ui, app_commands
from discord.ext import commands
from discord.ui import Modal, Button, View, TextInput

user_bios_lock = asyncio.Lock()

class EditCharacterModal(Modal):
    def __init__(self, category, user_id, character):
        super().__init__(title=f"5 MINUTES MAX. SAVE INFO")
        self.category = category
        self.user_id = user_id
        self.character = character

        with open("UserBiosDatabase.json", "r") as file:
            self.charDatabase = json.load(file)
        

        textStyle = discord.TextStyle.short
        max_length_text = 20

        if self.category in ["talents","personality","strengths_weaknesses","extra_info"]:
            textStyle = discord.TextStyle.paragraph
            max_length_text = 950
            
        if self.category == "extra_info":
            max_length_text = 3900

        self.add_item(
            TextInput(
                label=f"Current description for {category}:",
                default = self.charDatabase[self.user_id][self.character][self.category],
                style = textStyle,
                max_length = max_length_text,
                placeholder="Enter your edit here",
                required=True,
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        # Save the updated value
        updated_value = self.children[0].value

        if self.category == "color":
            if updated_value is not None:
                cleaned_color = updated_value.replace("#", "").strip()
                try:
                    updated_value = int(cleaned_color, 16) 
                except ValueError:
                    updated_value = None
            else:
                updated_value = None
        async with user_bios_lock:
            with open("UserBiosDatabase.json", "r") as file:
                bioData = json.load(file)

            bioData[self.user_id][self.character][self.category] = updated_value
            bioData[self.user_id][self.character]["verified"] = False

            with open("UserBiosDatabase.json", "w") as file:
                json.dump(bioData, file)
            
        await interaction.response.send_message(
            f"{self.category} updated to:\n{self.children[0].value}", ephemeral=True
        )







class CharacterBioModal(Modal, title="5 MINUTES MAX. SAVE INFO"):
    talents = ui.TextInput(label="Talents", style=discord.TextStyle.paragraph, required=False, max_length=950)
    personality = ui.TextInput(label="Personality", style=discord.TextStyle.paragraph, required=False, max_length=950)
    strengths_weaknesses = ui.TextInput(label="Strengths and Weaknesses", style=discord.TextStyle.paragraph, required=False, max_length=950)
    extra_info = ui.TextInput(label="Extra Information", style=discord.TextStyle.paragraph, required=False, max_length=3900)

    def __init__(self, name, age, gender, species, sexuality, sign = None, image_url = None, color = None):
        super().__init__()
        self.name = name
        self.age = age
        self.gender = gender
        self.species = species
        self.sexuality = sexuality
        self.image_url = image_url
        self.sign = sign

        if color is not None:
            cleaned_color = color.replace("#", "").strip()
            try:
                self.color = int(cleaned_color, 16) 
            except ValueError:
                self.color = None
        else:
            self.color = None
            

    async def on_submit(self, interaction: discord.Interaction):
        # Combine initial character details with the modal inputs
        charname = self.name
        character_details = {
            "age": self.age,
            "gender": self.gender,
            "species": self.species,
            "sexuality": self.sexuality,
            "talents": self.talents.value,
            "personality": self.personality.value,
            "strengths_weaknesses": self.strengths_weaknesses.value,
            "extra_info": self.extra_info.value,
            "image_url": self.image_url,
            "verified": False,
            "color": self.color,
            "sign": self.sign,
        }
        async with user_bios_lock:
            with open("UserBiosDatabase.json", "r") as file:
                bioData = json.load(file)

            uid = str(interaction.user.id)
            if uid not in bioData:
                bioData[uid] = {}
                
            bioData[str(interaction.user.id)][charname] = character_details

            with open("UserBiosDatabase.json", "w") as fileWrite:
                json.dump(bioData, fileWrite)

            
        await interaction.response.send_message(f"Character bio complete for {charname}!\nUse /displaycharacter to see them!")

        


class VerificationModal(Modal):
    def __init__(self, callback, guild, interaction):
        super().__init__(title="User Verification:")

        self.guild = guild
        #self.interaction = interaction
        
        self.age = discord.ui.TextInput(
            label=GlobalValues.VERIFICATION_QUESTIONS[0],
            required=True,
            max_length=10,
            style=discord.TextStyle.short
        )
        
        self.question1 = discord.ui.TextInput(
            label=GlobalValues.VERIFICATION_QUESTIONS[1],
            placeholder="",
            required=True,
            max_length = 20,
            style=discord.TextStyle.short
        )

        self.question2 = discord.ui.TextInput(
            label=GlobalValues.VERIFICATION_QUESTIONS[2],
            placeholder="",
            required=True,
            max_length = 10,
            style=discord.TextStyle.short
        )

        self.question3 = discord.ui.TextInput(
            label=GlobalValues.VERIFICATION_QUESTIONS[3],
            placeholder="",
            required=True,
            max_length = 10,
            style=discord.TextStyle.short
        )

        self.question4 = discord.ui.TextInput(
            label=GlobalValues.VERIFICATION_QUESTIONS[4],
            placeholder="",
            required=True,
            max_length = 10,
            style=discord.TextStyle.short
        )

        self.add_item(self.age)
        self.add_item(self.question1)
        self.add_item(self.question2)
        self.add_item(self.question3)
        self.add_item(self.question4)

        self.callback = callback
    
    async def on_submit(self, interaction: discord.Interaction):
        q1 = self.question1.value
        q2 = self.question2.value
        q3 = self.question3.value
        q4 = self.question4.value
        await self.callback([self.age.value, q1, q2, q3, q4], self.guild, interaction)
        await interaction.response.send_message("Forum submitted!", ephemeral=True)
    
        

    
        
