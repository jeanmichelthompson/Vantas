import config
from supabase_client import check_database, update_rank, get_leaderboard, check_rank, clear_rank, set_rank

# Main function to handle incoming messages
async def handle_message(bot, message):
    msg = message.content
    
    # Define a dictionary to map keywords to their respective responses
    keyword_responses = {
        'genji': 'buff genji',
        'mercy': 'boosted',
        'ridge': 'i miss that guy',
    }

    # Check for keywords in the message and respond accordingly
    for keyword, response in keyword_responses.items():
        if keyword in msg.lower():
            await message.channel.send(response)
    
    # Define a dictionary to map commands to their respective handler functions
    commands = {
        "!win": log_win_command,
        "!loss": log_loss_command,
        "!leaderboard": leaderboard_command,
        "!checkdb": checkdb_command,
        "!rank": rank_command,
        "!clearrank": clearrank_command,
        "!setrank": setrank_command,
        "!help": help_command,
        "!test": test_command,
    }

    # Split the message to get the command and arguments
    command = msg.split()[0]

    # Check if the command exists in the dictionary
    if command in commands:
        # Call the appropriate function from the dictionary
        await commands[command](bot, message)

# Function to test the bot
async def test_command(bot, message):
    await message.channel.send("Test!")

# Function to log a win
async def log_win_command(bot, message):
    msg = message.content
    user_id = str(message.author.id)
    if len(msg.split()) > 1:
        game_name = msg.split("!win ", 1)[1].lower()
        game_name_display = game_name.capitalize()
        if game_name in config.GAMES:
            update_rank(user_id, game_name, "win")
            await message.channel.send(f"Win logged for {game_name_display}!")
        else:
            await message.channel.send(f"Invalid game name. Available games: {', '.join(g.capitalize() for g in config.GAMES)}")
    else:
        await message.channel.send("Game name not provided. Usage: !win <game_name>")

# Function to log a loss
async def log_loss_command(bot, message):
    msg = message.content
    user_id = str(message.author.id)
    if len(msg.split()) > 1:
        game_name = msg.split("!loss ", 1)[1].lower()
        game_name_display = game_name.capitalize()
        if game_name in config.GAMES:
            update_rank(user_id, game_name, "loss")
            await message.channel.send(f"Loss logged for {game_name_display}!")
        else:
            await message.channel.send(f"Invalid game name. Available games: {', '.join(g.capitalize() for g in config.GAMES)}")
    else:
        await message.channel.send("Game name not provided. Usage: !loss <game_name>")

# Function to show the leaderboard
async def leaderboard_command(bot, message):
    msg = message.content
    if len(msg.split()) > 1:
        game_name = msg.split("!leaderboard ", 1)[1].lower()
        game_name_display = game_name.capitalize()
        leaderboard_data = get_leaderboard(game_name)
        if not leaderboard_data:
            await message.channel.send(f"No data available for the {game_name_display} leaderboard.")
        else:
            leaderboard_message = f"**{game_name_display} Leaderboard**\n"
            for user_id, rank in leaderboard_data:
                display_name = (await bot.fetch_user(int(user_id))).global_name
                leaderboard_message += f"{display_name}: {rank}\n"
            await message.channel.send(leaderboard_message)
    else:
        await message.channel.send("Game name not provided. Usage: !leaderboard <game_name>")

# Function to check the current database
async def checkdb_command(bot, message):
    if has_og_role(message.author):
        try:
            users = check_database()
            if users:
                for user in users:
                    await message.channel.send(f"{user}")
            else:
                await message.channel.send("No data found in the database.")
        except Exception as e:
            await message.channel.send(f"An error occurred: {str(e)}")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to check individual rank for a player by user ID
async def rank_command(bot, message):
    msg = message.content
    if len(msg.split()) > 1:
        target_user_id = msg.split("!rank ", 1)[1]
    else:
        target_user_id = str(message.author.id)

    # Validate that target_user_id is a valid snowflake
    if not target_user_id.isdigit() or not (17 <= len(target_user_id) <= 19):
        await message.channel.send("Invalid user ID.")
        return

    rank_data = check_rank(target_user_id)
    display_name = (await bot.fetch_user(target_user_id)).global_name
    if rank_data:
        rank_message = f"**{display_name}**\n"
        for game, rank in rank_data.items():
            rank_message += f"{game.capitalize()}: {rank}\n"
        await message.channel.send(rank_message)
    else:
        await message.channel.send(f"No data available for user {display_name}.")

# Function to clear individual rank for a player by user ID
async def clearrank_command(bot, message):
    msg = message.content
    if has_og_role(message.author):
        if len(msg.split()) > 1:
            target_user_id = msg.split("!clearrank ", 1)[1]
            clear_rank(target_user_id)
            await message.channel.send(f"Rank cleared for user {target_user_id}.")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to set individual rank for a player by user ID
async def setrank_command(bot, message):
    msg = message.content
    if has_og_role(message.author):
        parts = msg.split()
        if len(parts) == 4:
            target_user_id = parts[1]
            display_name = (await bot.fetch_user(target_user_id)).global_name
            game_name = parts[2].lower()
            rank = int(parts[3])
            if game_name in config.GAMES:
                set_rank(target_user_id, game_name, rank)
                await message.channel.send(f"Rank set to {rank} for user {display_name} in game {game_name.capitalize()}.")
            else:
                await message.channel.send(f"Invalid game name. Available games: {', '.join(g.capitalize() for g in config.GAMES)}")
        else:
            await message.channel.send("Invalid usage. Usage: !setrank <user_id> <game_name> <rank>")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to show the help message
async def help_command(bot, message):
    help_message = (
        "**Available Commands:**\n"
        "!help - Show this help message\n"
        "!win <game_name> - Log a win for a game\n"
        "!loss <game_name> - Log a loss for a game\n"
        "!leaderboard <game_name> - Show the leaderboard for a game\n"
        "!rank <user_id> - Check individual rank for a player\n"
        "!setrank <user_id> <game_name> <rank> - Set rank for a player (Admin)\n"
        "!clearrank <user_id> - Clear individual rank for a player (Admin)\n"
        "!checkdb - Check the current database (Admin)\n"
    )
    await message.channel.send(help_message)

# Function to check if the user has the "OG" role
def has_og_role(member):
    role_names = [role.name for role in member.roles]
    return "OG" in role_names
    
