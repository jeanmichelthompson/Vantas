import discord
from supabase_client import get_queue_data, update_queue_data, get_leaderboard, check_rank
from ui_components import QueueView, TeamManagementView, create_team_embed

# Dictionary to hold queue information for each channel
queues = {}

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
    num_players = len(queue_info["queue"])
    embed = discord.Embed(title=queue_info["title"], color=discord.Color.red())
    embed.add_field(name=f"{num_players} Players In Queue:", value=format_queue(channel_id), inline=False)
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
            await process_full_queue(interaction, channel_id, queue_info)
            queue.clear()
            # Clear the queue state in Supabase
            update_queue_data(channel_id, {"channel_id": channel_id, "title": queue_info["title"], "queue": [], "max_players": max_players, "message_id": queue_info["message_id"]})
            await update_queue_message(interaction.channel, channel_id)

    await interaction.response.send_message("You have joined the queue.", ephemeral=True)

# Function to process the queue when it is full
async def process_full_queue(interaction: discord.Interaction, channel_id, queue_info):
    queue = queue_info["queue"]
    game_name = queue_info["title"].split()[0].lower()  
    
    # Fetch player ranks from the database
    player_ranks = []
    for member in queue:
        rank_data = check_rank(str(member.id))
        if rank_data:
            player_ranks.append((member, rank_data[game_name]))
        else:
            player_ranks.append((member, 0))

    # Sort by rank in descending order
    player_ranks.sort(key=lambda x: x[1], reverse=True)

    # Distribute players into two balanced teams
    team_a = []
    team_b = []
    for i, (player, rank) in enumerate(player_ranks):
        if i % 2 == 0:
            team_a.append((player, rank))
        else:
            team_b.append((player, rank))

    # Send a message with the teams
    team_a_mentions = ", ".join([member.mention for member, _ in team_a])
    team_b_mentions = ", ".join([member.mention for member, _ in team_b])
    await interaction.channel.send(f"Match is ready!\n\n*Suggested Teams*\n**Team A:** {team_a_mentions}\n**Team B:** {team_b_mentions}")

    # Create an embed with the teams
    embed = create_team_embed(team_a, team_b)
    
    # Send the embed with buttons to edit and confirm the teams
    await interaction.channel.send(embed=embed, view=TeamManagementView(team_a, team_b, game_name))

# Function to handle a user leaving the queue
async def handle_leave_queue(interaction: discord.Interaction, channel_id):
    user = interaction.user
    queue_info = queues[channel_id]
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
