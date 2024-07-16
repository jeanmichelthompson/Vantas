import discord
import os
from discord.ext import commands
from keep_alive import keep_alive
from matchmaking import QueueView, initialize_queues
from replitdb import log_win, log_loss, get_leaderboard, check_rank, clear_rank, set_rank
from replit import db

# Initialize the bot with necessary intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='$', intents=intents)

games = ["overwatch", "league"]


# Event handler for when the bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

    # List of channel information for different queues
    channel_info = [{
        "title": "Overwatch 5v5 Matchmaking Queue",
        "channel_id": 1262418283613917204,
        "max_players": 10
    }, {
        "title": "Overwatch 6v6 Matchmaking Queue",
        "channel_id": 1262418824456699934,
        "max_players": 12
    }, {
        "title": "League of Legends Matchmaking Queue",
        "channel_id": 1262419859413663775,
        "max_players": 10
    }]

    await initialize_queues(bot, channel_info)


# Event handler for when a message is received
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    msg = message.content
    user_id = str(message.author.id)

    # Respond to messages that contain keywords
    if 'genji' in msg.lower():
        await message.channel.send('buff genji')

    if 'mercy' in msg.lower():
        await message.channel.send('boosted')

    # Command to log a win
    if msg.startswith("!win"):
        if len(msg.split()) > 1:
            game_name = msg.split("!win ", 1)[1].lower()
            game_name_display = game_name.capitalize()
            if game_name in games:
                log_win(user_id, game_name)
                await message.channel.send(
                    f"Win logged for {game_name_display}!")
            else:
                await message.channel.send(
                    f"Invalid game name. Available games: {', '.join(g.capitalize() for g in games)}"
                )
        else:
            await message.channel.send(
                "Game name not provided. Usage: !win <game_name>")

    # Command to log a loss
    if msg.startswith("!loss"):
        if len(msg.split()) > 1:
            game_name = msg.split("!loss ", 1)[1].lower()
            game_name_display = game_name.capitalize()
            if game_name in games:
                log_loss(user_id, game_name)
                await message.channel.send(
                    f"Loss logged for {game_name_display}!")
            else:
                await message.channel.send(
                    f"Invalid game name. Available games: {', '.join(g.capitalize() for g in games)}"
                )
        else:
            await message.channel.send(
                "Game name not provided. Usage: !loss <game_name>")

    # Command to show the leaderboard
    if msg.startswith("!leaderboard"):
        if len(msg.split()) > 1:
            game_name = msg.split("!leaderboard ", 1)[1].lower()
            game_name_display = game_name.capitalize(
            )  # Convert to first letter uppercase for display
            leaderboard_data = get_leaderboard(game_name)
            if not leaderboard_data:
                await message.channel.send(
                    f"No data available for the {game_name_display} leaderboard."
                )
            else:
                leaderboard_message = f"**{game_name_display} Leaderboard**\n"
                for user_id, wins in leaderboard_data:
                    display_name = (await bot.fetch_user(user_id)).global_name
                    leaderboard_message += f"{display_name}: {wins} wins\n"
                await message.channel.send(leaderboard_message)
        else:
            await message.channel.send(
                "Game name not provided. Usage: !leaderboard <game_name>")

    # Command to check the current database
    if msg.startswith("!checkdb"):
        if has_og_role(message.author):
            for key in db.keys():
                await message.channel.send(f"{key}: {db[key]}")
        else:
            await message.channel.send(
                "You do not have permission to use this command.")

    # Command to clear the database
    if msg.startswith("!cleardb"):
        if has_og_role(message.author):
            for key in db.keys():
                del db[key]
            await message.channel.send("Database cleared.")
        else:
            await message.channel.send(
                "You do not have permission to use this command.")

    # Command to check individual rank for a player by user ID
    if msg.startswith("!rank"):
        if len(msg.split()) > 1:
            target_user_id = msg.split("!rank ", 1)[1]
        else:
            target_user_id = str(message.author.id)
        rank_data = check_rank(target_user_id)
        display_name = (await bot.fetch_user(target_user_id)).global_name
        if rank_data:
            rank_message = f"**{display_name}**\n"
            for game, rank in rank_data.items():
                rank_message += f"{game.capitalize()}: {rank}\n"
            await message.channel.send(rank_message)
        else:
            await message.channel.send(
                f"No data available for user {display_name}.")

    # Command to clear individual rank for a player by user ID
    if msg.startswith("!clearrank"):
        if has_og_role(message.author):
            if len(msg.split()) > 1:
                target_user_id = msg.split("!clearrank ", 1)[1]
                clear_rank(target_user_id)
                await message.channel.send(
                    f"Rank cleared for user {target_user_id}.")
        else:
            await message.channel.send(
                "You do not have permission to use this command.")

    # Command to set individual rank for a player by user ID
    if msg.startswith("!setrank"):
        if has_og_role(message.author):
            parts = msg.split()
            if len(parts) == 4:
                target_user_id = parts[1]
                display_name = (await bot.fetch_user(target_user_id)).global_name
                game_name = parts[2].lower()
                rank = int(parts[3])
                if game_name in games:
                    set_rank(target_user_id, game_name, rank)
                    await message.channel.send(
                        f"Rank set to {rank} for user {display_name} in game {game_name.capitalize()}."
                    )
                else:
                    await message.channel.send(
                        f"Invalid game name. Available games: {', '.join(g.capitalize() for g in games)}"
                    )
            else:
                await message.channel.send(
                    "Invalid usage. Usage: !setrank <user_id> <game_name> <rank>"
                )
        else:
            await message.channel.send(
                "You do not have permission to use this command.")


# Check if the user has the "OG" role
def has_og_role(member):
    role_names = [role.name for role in member.roles]
    return "OG" in role_names


# Keep the bot alive (necessary for hosting on Replit)
keep_alive()
# Run the bot with the token from environment variables
bot.run(os.getenv('DISCORD_TOKEN'))
