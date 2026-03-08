import GlobalValues
import json
import time
import random
import discord

global StartTime
StartTime = None


async def createEvent(Event, reset, bot):
    global StartTime
    StartTime = time.time()
    print(f"creating {Event}")
    if reset:
        emptyDic = {}
        with open("event_data.json", "w") as file:
            json.dump(emptyDic, file)


    if Event == "Server-Milestone":
        StartTime = time.time()
        
        botChannel = bot.get_channel(GlobalValues.BOT_INFO)
        goal_value = random.randint(2000, 20000)
        time_limit = random.randint(86400, 604800)

        difficulty = determine_difficulty(goal_value, time_limit)
        print(time_limit)

        timestamp = time_limit
        days = timestamp // (24 * 3600)
        timestamp %= (24 * 3600)
        hours = timestamp // 3600
        timestamp %= 3600
        minutes = timestamp // 60
        seconds = timestamp % 60

        formatted_time = f"{days} days, {hours:02}:{minutes:02}:{seconds:02}"

        # Create the message for the milestone event
        message = f"**Server Milestone!**\n"
        message += f"Goal: {goal_value} coins\n"
        message += f"Time limit: {formatted_time} (Days:HH:MM:SS)\n"
        message += f"Difficulty: {difficulty}\n"

        await botChannel.send(message)
        

    if Event == "Random-Quest":
        botChannel = bot.get_channel(GlobalValues.BOT_INFO)

    if Event == "Boss-Fight":
        botChannel = bot.get_channel(GlobalValues.BOT_INFO)

    if Event == "Lottery":
        botChannel = bot.get_channel(GlobalValues.BOT_INFO)

        




async def processEvent(Event, coins, message, channel):
    if Event == "None":
        return coins
    
    if Event == "Double-EXP":
        return coins * 2

    if Event == "Server-Milestone":
        return await serverMilestone(coins)

    if Event == "Random-Quest":
        return await randomQuest(coins)

    if Event == "Public-RP-Boost":
        return await publicRPBoost(coins, channel)

    if Event == "Private-RP-Boost":
        return await privateRPBoost(coins, channel)

    if Event == "RP-Boost":
        return await RPBoost(coins, channel)

    if Event == "Boss-Fight":
        return await bossFight(coins)

    if Event == "Lottery":
        return await Lottery(coins)

    if Event == "Booster-Boost":
        return await boosterBoost(coins, message)

        
    return coins

    
async def serverMilestone(coins):
    print("got 1")
    return coins

async def randomQuest(coins):
    print("got 2")

async def publicRPBoost(coins, channel):
    if channel.category.id in GlobalValues.RPCHANNELS:
        print("got 3")
        return coins*1.5
    else:
        return coins

async def privateRPBoost(coins, channel):
    if channel.category.name.startswith("❤ Private RP"): 
        print("got 4")
        return coins*1.5
    else:
        return coins

async def RPBoost(coins, channel):
    if channel.category.id in GlobalValues.RPCHANNELS or channel.category.name.startswith("❤ Private RP"):
        print("got 5")
        return coins*1.5
    else:
        return coins

async def bossFight(coins):
    print("got 6")

async def Lottery(coins):
    print("got 7")


async def boosterBoost(coins, message):
    addCoins = coins
    author = message.guild.get_member(message.author.id)
    if author is not None:
        booster_role = discord.utils.get(author.roles, id=GlobalValues.SERVER_BOOSTER)
        if booster_role:
            addCoins = coins*1.5

    return addCoins



###########################################################################################################


def determine_difficulty(goal_value, time_limit):
    """Determine the difficulty of the milestone based on the goal value and time limit"""
    
    # If time is shorter, it's harder; if time is longer, it's easier
    time_in_days = time_limit / 86400  # Convert seconds to days (1 day = 86400 seconds)

    # Difficulty is primarily based on time, with goal value also playing a role
    if time_in_days <= 2:  # 1-2 days, very short time (hard)
        if goal_value <= 3000:
            return "Normal"
        elif goal_value <= 6000:
            return "Hard"
        else:
            return "Extreme"
    elif time_in_days <= 4:  # 3-4 days, moderately short time (harder)
        if goal_value <= 6000:
            return "Easy"
        elif goal_value <= 10000:
            return "Normal"
        else:
            return "Hard"
    elif time_in_days <= 6:  # 5-6 days, longer time (easier)
        if goal_value <= 8000:
            return "Easy"
        elif goal_value <= 15000:
            return "Normal"
        else:
            return "Hard"
    else:  # 7 days, maximum time (easiest)
        if goal_value <= 5000:
            return "Easy"
        elif goal_value <= 15000:
            return "Easy"
        else:
            return "Normal"





