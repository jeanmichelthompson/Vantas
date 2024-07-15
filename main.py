import discord
import os
from discord.ext import commands
from discord.ui import Button, View
from keep_alive import keep_alive
from replit import db

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)
games = ["overwatch", 'league']

# Dictionary to hold queue information for each channel
queues = {}

# Define a custom view for the queue buttons
class QueueView(View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id  # Store the channel ID for context

    # Button for joining the queue
    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_queue")
    async def join_queue_button(self, interaction: discord.Interaction, button: Button):
        await handle_join_queue(interaction, self.channel_id)

    # Button for leaving the queue
    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, custom_id="leave_queue")
    async def leave_queue_button(self, interaction: discord.Interaction, button: Button):
        await handle_leave_queue(interaction, self.channel_id)

    # Placeholder button for the leaderboard (not implemented)
    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.secondary, custom_id="leaderboard")
    async def leaderboard_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Leaderboard feature not implemented yet.", ephemeral=True)

# Event handler for when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # List of channel information for different queues
    channel_info = [
        {"title": "Overwatch 5v5 Matchmaking Queue", "channel_id": 1262418283613917204, "max_players": 10},
        {"title": "Overwatch 6v6 Matchmaking Queue", "channel_id": 1262418824456699934, "max_players": 12},
        {"title": "League of Legends Matchmaking Queue", "channel_id": 1262419859413663775, "max_players": 10}
    ]

    # Initialize queues for each channel
    for info in channel_info:
        channel = bot.get_channel(info["channel_id"])
        await delete_bot_messages(channel)  # Delete previous bot messages
        queues[info["channel_id"]] = {
            "title": info["title"],
            "queue": [],
            "max_players": info["max_players"],
            "message_id": None
        }
        # Send the initial queue message and store its ID
        message = await channel.send(embed=create_queue_embed(info["channel_id"]), view=QueueView(info["channel_id"]))
        queues[info["channel_id"]]["message_id"] = message.id

# Function to delete previous messages sent by the bot
async def delete_bot_messages(channel):
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()

# Function to create an embed for the queue status
def create_queue_embed(channel_id):
    queue_info = queues[channel_id]
    embed = discord.Embed(title=queue_info["title"], color=discord.Color.red())
    embed.add_field(name="Players In Queue:", value=format_queue(channel_id), inline=False)
    return embed

# Function to format the queue into a readable string
def format_queue(channel_id):
    queue = queues[channel_id]["queue"]
    if not queue:
        return "Queue is empty."
    return "\n".join(f"<@{member.id}>" for member in queue)

# Function to handle a user joining the queue
async def handle_join_queue(interaction: discord.Interaction, channel_id):
    user = interaction.user
    queue_info = queues[channel_id]
    queue = queue_info["queue"]
    max_players = queue_info["max_players"]

    if user not in queue:
        queue.append(user)
        await update_queue_message(interaction.channel, channel_id)
        if len(queue) == max_players:
            await interaction.channel.send("Match is ready! " + ", ".join(member.mention for member in queue))
            queue.clear()
            await update_queue_message(interaction.channel, channel_id)
    await interaction.response.send_message("You have joined the queue.", ephemeral=True)

# Function to handle a user leaving the queue
async def handle_leave_queue(interaction: discord.Interaction, channel_id):
    user = interaction.user
    queue = queues[channel_id]["queue"]
    if user in queue:
        queue.remove(user)
        await update_queue_message(interaction.channel, channel_id)
    await interaction.response.send_message("You have left the queue.", ephemeral=True)

# Function to update the queue message with the current queue status
async def update_queue_message(channel, channel_id):
    message_id = queues[channel_id]["message_id"]
    message = await channel.fetch_message(message_id)
    await message.edit(embed=create_queue_embed(channel_id), view=QueueView(channel_id))

# Event handler for when a message is received
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    msg = message.content
    user_id = str(message.author.id)
    
    # Respond to messages that contain 'genji'
    if 'genji' in msg.lower():
        await message.channel.send('buff genji')

    if msg.startswith("!win"):
        game_name = msg.split("!win ", 1)[1]
        if game_name.lower() in games:
            log_win(user_id, game_name)
            await message.channel.send(f"Win logged for {game_name}!")
        else:
            await message.channel.send(f"Invalid game name. Available games: {', '.join(games)}")

    if msg.startswith("!loss"):
        game_name = msg.split("!loss ", 1)[1]
        if game_name.lower() in games:
            log_loss(user_id, game_name)
            await message.channel.send(f"Loss logged for {game_name}!")
        else:
            await message.channel.send(f"Invalid game name. Available games: {', '.join(games)}")

    if msg.startswith("!leaderboard"):
        game_name = msg.split("!leaderboard ", 1)[1]
        leaderboard_data = get_leaderboard(game_name)
        if not leaderboard_data:
            await message.channel.send(f"No data available for the {game_name} leaderboard.")
        else:
            leaderboard_message = f"**{game_name} Leaderboard**\n"
            for user_id, wins in leaderboard_data:
                user = await bot.fetch_user(user_id)
                leaderboard_message += f"{user.name}: {wins} wins\n"
            await message.channel.send(leaderboard_message)

# Function to add a win to a player's win count
def log_win(user_id: str, game_name: str):
    # Check if the user has a win count in the database
    if user_id in db.keys():
        user_data = db[user_id]
        if game_name in user_data.keys():
            user_data[game_name] += 25
        else:
            user_data[game_name] = 25
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: 25}

# Function to reduce a win from a player's win counter
def log_loss(user_id: str, game_name: str):
    # Check if the user has a win count in the database
    if user_id in db.keys():
        user_data = db[user_id]
        if game_name in user_data.keys():
            user_data[game_name] -= 25
        else:
            user_data[game_name] = -25
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: -25}
        
# Function to get the leaderboard
def get_leaderboard(game_name: str):
    leaderboard_data = []
    for user_id in db.keys():
        user_data = db[user_id]
        if game_name in user_data:
            leaderboard_data.append((user_id, user_data[game_name]))
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)
    return leaderboard_data

# Keep the bot alive (necessary for hosting on Replit)
keep_alive()
# Run the bot with the token from environment variables
bot.run(os.getenv('DISCORD_TOKEN'))
