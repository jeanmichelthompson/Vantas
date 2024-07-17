import discord
from discord.ui import Button, View
from supabase_client import get_queue_data, update_queue_data, get_leaderboard

# Dictionary to hold queue information for each channel
queues = {}


# Define a custom view for the queue buttons
class QueueView(View):

    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id  # Store the channel ID for context

    # Button for joining the queue
    @discord.ui.button(label="Join Queue",
                       style=discord.ButtonStyle.primary,
                       custom_id="join_queue")
    async def join_queue_button(self, interaction: discord.Interaction,
                                button: Button):
        await handle_join_queue(interaction, self.channel_id)

    # Button for leaving the queue
    @discord.ui.button(label="Leave Queue",
                       style=discord.ButtonStyle.danger,
                       custom_id="leave_queue")
    async def leave_queue_button(self, interaction: discord.Interaction,
                                 button: Button):
        await handle_leave_queue(interaction, self.channel_id)

    # Button for viewing the leaderboard
    @discord.ui.button(label="Leaderboard",
                       style=discord.ButtonStyle.secondary,
                       custom_id="leaderboard")
    async def leaderboard_button(self, interaction: discord.Interaction,
                                 button: Button):
        await handle_leaderboard(interaction, self.channel_id)


# Function to initialize queues for each channel
# Function to initialize queues for each channel
async def initialize_queues(bot, channel_info):
    for info in channel_info:
        channel = bot.get_channel(info["channel_id"])
        await delete_bot_messages(channel)  # Delete previous bot messages

        # Load the queue state from Supabase if it exists
        queue_state = get_queue_data(info["channel_id"])
        if queue_state:
            queue_members = [await bot.fetch_user(user_id) for user_id in queue_state["queue"] if await bot.fetch_user(user_id)]
        else:
            queue_state = []
            queue_members = []

        # Store the queue information in the queues dictionary
        queues[info["channel_id"]] = {
            "title": info["title"],
            "queue": queue_members,
            "max_players": info["max_players"],
            "message_id": None
        }

        # Send the initial queue message and store its ID
        message = await channel.send(embed=create_queue_embed(info["channel_id"]), view=QueueView(info["channel_id"]))
        queues[info["channel_id"]]["message_id"] = message.id

# Function to delete previous bot messages in a channel
async def delete_bot_messages(channel):
    async for message in channel.history(limit=100):
        if message.author == channel.guild.me:
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
        # Save the updated queue state to Supabase
        update_queue_data(channel_id, {"channel_id": channel_id, "title": queue_info["title"], "queue": [member.id for member in queue], "max_players": max_players, "message_id": queue_info["message_id"]})
        await update_queue_message(interaction.channel, channel_id)
        if len(queue) == max_players:
            await interaction.channel.send("Match is ready! " + ", ".join(member.mention for member in queue))
            queue.clear()
            # Clear the queue state in Supabase
            update_queue_data(channel_id, {"channel_id": channel_id, "title": queue_info["title"], "queue": [], "max_players": max_players, "message_id": queue_info["message_id"]})
            await update_queue_message(interaction.channel, channel_id)
    await interaction.response.send_message("You have joined the queue.", ephemeral=True)

# Function to handle a user leaving the queue
async def handle_leave_queue(interaction: discord.Interaction, channel_id):
    user = interaction.user
    queue_info = queues[channel_id]  # Add this line to get the correct queue_info
    queue = queue_info["queue"]
    if user in queue:
        queue.remove(user)
        # Save the updated queue state to Supabase
        update_queue_data(channel_id, {
            "channel_id": channel_id,
            "title": queue_info["title"],
            "queue": [member.id for member in queue],
            "max_players": queue_info["max_players"],
            "message_id": queue_info["message_id"]
        })
        await update_queue_message(interaction.channel, channel_id)
    await interaction.response.send_message("You have left the queue.", ephemeral=True)

# Function to update the queue message with the current queue status
async def update_queue_message(channel, channel_id):
    message_id = queues[channel_id]["message_id"]
    message = await channel.fetch_message(message_id)
    await message.edit(embed=create_queue_embed(channel_id), view=QueueView(channel_id))

# Function to handle displaying the leaderboard
async def handle_leaderboard(interaction: discord.Interaction, channel_id):
    queue_info = queues[channel_id]
    game_name = queue_info["title"].split()[0].lower()  # Extract the game name from the title
    leaderboard_data = get_leaderboard(game_name)
    if not leaderboard_data:
        await interaction.response.send_message(f"No data available for the {game_name.capitalize()} leaderboard.", ephemeral=True)
    else:
        leaderboard_message = f"**{game_name.capitalize()} Leaderboard**\n"
        for user_id, rank in leaderboard_data:
            user = await interaction.client.fetch_user(user_id)
            display_name = user.global_name
            leaderboard_message += f"{display_name}: {rank}\n"
        await interaction.response.send_message(leaderboard_message, ephemeral=True)
