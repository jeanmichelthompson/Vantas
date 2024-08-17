import discord
from discord.ext import commands
from matchmaking import initialize_queues
from commands import handle_message
import asyncio
from supabase_client import increment_ping_if_due
import config

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=config.COMMAND_PREFIX, intents=intents)

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await initialize_queues(bot, config.CHANNEL_INFO)
    bot.loop.create_task(schedule_ping_update())

async def schedule_ping_update():
    while True:
        increment_ping_if_due()
        await asyncio.sleep(86400) 

# Event handler for when a message is received
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await handle_message(bot, message)

# Run the bot with the token from environment variables
bot.run(config.DISCORD_TOKEN)
