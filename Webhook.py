import GlobalValues
import json
import asyncio
from discord.ext import tasks

global firstRun
firstRun = False

@tasks.loop(seconds = 5)
async def delete_message(msg):
    global firstRun
    print(firstRun)
    if firstRun:
        print("in: ", firstRun)
        await msg.delete()
        delete_message.stop()
    firstRun = True
    

async def process_message_webhook_command(ctx, channel, user_id):
    if channel.category.id in GlobalValues.RPCHANNELS or channel.category.name.startswith("❤ Private RP"):
        with open("UserBiosDatabase.json", "r") as file:
            userBiosData = json.load(file)
        uid = str(user_id)

        if uid not in userBiosData:
            return

        for character in userBiosData[uid]:
            characterDict = userBiosData[uid][character]
            sign = characterDict.get('sign')
            if sign and ctx.message.content.lower().startswith(sign.lower()):

                if not(userBiosData[uid][character]["verified"]):
                    msg = await ctx.send("Character must be verified before use")
                    global firstRun
                    firstRun = False
                    delete_message.start(msg)
                    return True, ctx.message, ctx.message.id
                
                webhook = await get_webhook(channel)
                length = len(sign)

                imageurl = characterDict.get('image_url')
                
                await webhook.send(
                    content=ctx.message.content[length:],  # Remove prefix from message
                    username=character,
                    avatar_url=imageurl,
                    )

                return True, ctx.message, ctx.message.id
            
    return False, None, None


async def get_webhook(channel):
    """Get an existing webhook for a channel or create a new one if none exists."""
    webhooks = await channel.webhooks()
    if webhooks:
        return webhooks[0]
    else:
        return await channel.create_webhook(name="SukiBot Webhook")
