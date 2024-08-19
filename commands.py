import random
import config
import discord
from supabase_client import clear_all_queues, clear_all_replays, get_match_details, get_leaderboard, get_user, clear_rank, get_user_leaderboard_position, get_wins_and_losses, set_rank, update_replay_code
from openai_client import gpt_response, store_message
from datetime import datetime, timedelta


# Main function to handle incoming messages
async def handle_message(bot, message):
    msg = message.content

    # Define a dictionary to map commands to their respective handler functions
    commands = {
        "!win": log_win_command,
        "!loss": log_loss_command,
        "!leaderboard": leaderboard_command,
        "!match": match_command,
        "!history": history_command,
        "!replay": replay_command,
        "!rank": rank_command,
        "!clearrank": clearrank_command,
        "!setrank": setrank_command,
        "!clearqueue": clearqueue_command,
        "!clearreplay": clear_replay_command,
        "!vantas": gpt_command,
        "!help": help_command,
        "!test": test_command,
    }

    # Split the message to get the command and arguments
    command = msg.split()[0]

    # Check if the command exists in the dictionary
    if command in commands:
        # Call the appropriate function from the dictionary
        await commands[command](bot, message)
        return

    # Define a dictionary to map keywords to their respective response types
    keyword_response_types = {
        'genji': 'genji',
        'mercy': 'mercy',
        'ridge': 'ridge',
        'gpttest': 'chat',
    }

    # Check for keywords in the message and respond accordingly
    for keyword, response_type in keyword_response_types.items():
        if keyword in msg.lower():
            response = gpt_response(msg, message.author.global_name, response_type)
            await message.channel.send(response)
            return

    # If the message is a reply to another message
    if message.reference:
        # Retrieve the original message
        original_message = await message.channel.fetch_message(message.reference.message_id)
        # Check if the original message was sent by the bot
        if original_message.author == bot.user:
            response = gpt_response(msg, message.author.global_name, "reply", original_message.content)
            await message.channel.send(response)
            return

    # If the message is neither a command nor a keyword, give it a one in fifty chance to call gpt_response
    if random.randint(1, 50) == 1:
        response = gpt_response(msg, message.author.global_name, "chat")
        await message.channel.send(response)
    
    # Store the message in the conversation history
    store_message(msg, message.author.global_name)

# Function to test the bot
async def test_command(bot, message):
    await message.channel.send("Test!")

# Function to log a win
async def log_win_command(bot, message):
    await message.channel.send("Command has been deprecated. Ranking is now updated automatically based on match results.")

# Function to log a loss
async def log_loss_command(bot, message):
    await message.channel.send("Command has been deprecated. Ranking is now updated automatically based on match results.")

# Function to show the leaderboard with pagination
async def leaderboard_command(bot, message):
    msg = message.content
    parts = msg.split()

    # Determine the game name and page number
    if len(parts) > 1:
        game_name = parts[1].lower()
        game_name_display = game_name.capitalize()
        page = 1
        
        if len(parts) > 2 and parts[2].isdigit():  # Check if a page number is provided
            page = int(parts[2])

        leaderboard_data = get_leaderboard(game_name)
        if not leaderboard_data:
            await message.channel.send(f"{game_name_display} is not a supported game. Supported games: Overwatch, League")
            return

        players_per_page = 10
        total_players = len(leaderboard_data)
        total_pages = (total_players + players_per_page - 1) // players_per_page

        # Validate the page number
        if page < 1 or page > total_pages:
            await message.channel.send(f"Page {page} is out of range. There are only {total_pages} pages available.")
            return

        start_index = (page - 1) * players_per_page
        end_index = start_index + players_per_page
        leaderboard_page = leaderboard_data[start_index:end_index]

        # Create an embed for the leaderboard
        embed = discord.Embed(
            title=f"{game_name_display} Leaderboard",
            color=discord.Color.green()
        )

        # Add each user and their rank to the embed, mentioning the user
        for index, (user_id, rank) in enumerate(leaderboard_page, start=start_index + 1):
            user_mention = (await bot.fetch_user(int(user_id))).mention
            embed.add_field(
                name="",
                value=f"{index}. {user_mention}: {rank}",
                inline=False
            )
        embed.set_footer(text=f"Page {page} of {total_pages}")
        # Send the embed
        await message.channel.send(embed=embed)
    else:
        await message.channel.send("Game name not provided. Usage: !leaderboard <game_name> <page_number>*")

# Function to check individual MMR for a player by user ID
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

    rank_data = get_user(target_user_id)
    wins_losses_data = get_wins_and_losses(target_user_id)
    display_name = (await bot.fetch_user(target_user_id)).global_name
    
    if rank_data:
        rank_embed = discord.Embed(
            title=f"{display_name}'s Profile",
            description=f"User ID: {target_user_id}",
            color=discord.Color.blue()
        )

        # Loop through the rank data, excluding the 'matches' and 'user_id' fields
        for game, rank in rank_data.items():
            if game != "matches" and game != "user_id":
                position, mmr = get_user_leaderboard_position(game.lower(), target_user_id)
                if position is not None and mmr is not None:
                    wins_losses = wins_losses_data.get(game.lower(), {'wins': 0, 'losses': 0})
                    rank_embed.add_field(
                        name=f"{game.capitalize()}",
                        value=f"Rank: {position}\nMMR: {mmr}\nWL: {wins_losses['wins']}-{wins_losses['losses']}",
                        inline=True
                    )
                else:
                    rank_embed.add_field(
                        name=f"{game.capitalize()}",
                        value="No leaderboard data available.",
                        inline=True
                    )

        await message.channel.send(embed=rank_embed)
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

# Function to display match history for a user with pagination
async def history_command(bot, message):
    msg = message.content
    parts = msg.split()

    # Determine the target_user_id and page number
    target_user_id = str(message.author.id)
    page = 1

    if len(parts) == 2:
        if parts[1].isdigit() and len(parts[1]) <= 3:  # Check if it's a page number (up to 999 pages)
            page = int(parts[1])
        else:
            target_user_id = parts[1]
    elif len(parts) > 2:
        target_user_id = parts[1]
        if parts[2].isdigit():
            page = int(parts[2])

    # Validate the page number
    if page < 1:
        await message.channel.send("Page number must be 1 or greater.")
        return

    # Fetch the user's data
    rank_data = get_user(target_user_id)
    display_name = (await bot.fetch_user(int(target_user_id))).global_name
    if not rank_data or not rank_data.get("matches"):
        await message.channel.send(f"No match history found for user {display_name}.")
        return

    # Fetch and sort match IDs by their corresponding match creation time
    matches_with_time = []
    for match_id in rank_data["matches"]:
        match_details = get_match_details(match_id)
        if match_details:
            match_time = datetime.fromisoformat(match_details["created_at"].replace('Z', '+00:00'))
            matches_with_time.append((match_id, match_time))

    # Sort matches by time (most recent first)
    matches_with_time.sort(key=lambda x: x[1], reverse=True)
    sorted_match_ids = [match_id for match_id, _ in matches_with_time]

    matches_per_page = 10
    total_matches = len(sorted_match_ids)
    total_pages = (total_matches + matches_per_page - 1) // matches_per_page

    # Check if the page is within the valid range
    if page > total_pages:
        await message.channel.send(f"Page {page} is out of range. There are only {total_pages} pages available.")
        return

    match_ids = sorted_match_ids[(page-1)*matches_per_page:page*matches_per_page]  # Get matches for the requested page

    # Create the embed for the match history
    history_embed = discord.Embed(
        title=f"{display_name}'s Match History",
        description=f"Showing matches {((page-1)*matches_per_page)+1}-{page*matches_per_page} out of {total_matches} matches",
        color=discord.Color.blue()
    )

    for match_id in match_ids:
        match_details = get_match_details(match_id)
        if not match_details:
            continue

        # Determine if the user won or lost the match
        if target_user_id in match_details["team1"]:
            status = "Win" if match_details["winner"] == "Team A" else "Loss"
        elif target_user_id in match_details["team2"]:
            status = "Win" if match_details["winner"] == "Team B" else "Loss"
        else:
            status = "Unknown"

        # Adjust the created_at timestamp by subtracting 4 hours
        match_time = datetime.fromisoformat(match_details["created_at"].replace('Z', '+00:00'))
        match_time_adjusted = match_time - timedelta(hours=4)

        # Format the adjusted time
        formatted_time = match_time_adjusted.strftime("%B %d, %I:%M%p").replace('AM', 'am').replace('PM', 'pm')
        
        # Remove leading zero from the day
        formatted_time = formatted_time.replace(" 0", " ")

        # Add replay code if available
        replay_code = match_details.get("replay")
        replay_text = f"**Replay Code:** {replay_code}\n" if replay_code else ""

        # Add a field to the embed for each match
        history_embed.add_field(
            name=f"-----------------------------------------------------------\n{match_details['game'].capitalize()}: {match_id}",
            value=(
                f"**Map:** {match_details['map']}\n"
                f"**Result:** {status}\n"
                f"{replay_text}**Time:** {formatted_time}"
            ),
            inline=False
        )

    # Include pagination info in the footer
    history_embed.set_footer(text=f"Page {page} of {total_pages}")

    await message.channel.send(embed=history_embed)

# Function to fetch and display match details based on match ID
async def match_command(bot, message):
    msg = message.content
    if len(msg.split()) > 1:
        match_id = msg.split("!match ", 1)[1].strip()
    else:
        await message.channel.send("Match ID not provided. Usage: !match <match_id>")
        return

    try:
        # Attempt to get match details
        match_details = get_match_details(match_id)
        if not match_details:
            await message.channel.send("No match found with the provided ID.")
            return

        # Parse the created_at timestamp and adjust by subtracting 4 hours
        match_time = datetime.fromisoformat(match_details["created_at"].replace('Z', '+00:00'))
        match_time_adjusted = match_time - timedelta(hours=4)

        # Format the adjusted time
        formatted_time = match_time_adjusted.strftime("%B %d, %I:%M%p").replace('AM', 'am').replace('PM', 'pm')

        # Remove leading zero from day
        formatted_time = formatted_time.replace(" 0", " ")

        # Fetch the global names of the players on both teams
        team1_mentions = [await bot.fetch_user(int(user_id)) for user_id in match_details["team1"]]
        team2_mentions = [await bot.fetch_user(int(user_id)) for user_id in match_details["team2"]]
        team1_mentions = "\n".join([user.mention for user in team1_mentions])
        team2_mentions = "\n".join([user.mention for user in team2_mentions])

        # Add replay code if available
        replay_code = match_details.get("replay")
        replay_text = f"**Replay Code:** {replay_code}\n" if replay_code else ""

        # Prepare and send match details as an embed
        embed = discord.Embed(
            title=f"{match_details['game'].capitalize()}: {match_id}",
            description=f"{formatted_time}",
            color=discord.Color.blue()
        )
        embed.add_field(name="**Map**", value=match_details['map'], inline=False)
        embed.add_field(name="**Team A**", value=team1_mentions, inline=True)
        embed.add_field(name="**Team B**", value=team2_mentions, inline=True)
        embed.add_field(name="**Winner**", value=match_details['winner'], inline=False)
        if replay_text:
            embed.add_field(name="Replay Code", value=replay_code, inline=False)

        await message.channel.send(embed=embed)

    except Exception as e:
        # Handle any errors (e.g., invalid match ID)
        await message.channel.send("Invalid match ID or an error occurred while retrieving match details.")

# Function to handle the replay command
async def replay_command(bot, message):
    msg = message.content
    parts = msg.split()

    if len(parts) < 3:
        await message.channel.send("Invalid usage. Usage: !replay <match_id> <replay_code>")
        return

    match_id = parts[1]
    replay_code = parts[2]

    # Verify the match exists
    match_details = get_match_details(match_id)
    if not match_details:
        await message.channel.send(f"No match found with ID {match_id}.")
        return

    # Update the replay column in the matches table
    update_replay_code(match_id, replay_code)

    await message.channel.send(f"Replay code '{replay_code}' stored for match ID: {match_id}.")

# Function to clear all active queues for each game
async def clearqueue_command(bot, message):
    if has_og_role(message.author):
        await clear_all_queues(bot)
        await message.channel.send("All active queues have been cleared.")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to clear the replay code for all matches
async def clear_replay_command(bot, message):
    if has_og_role(message.author):
        clear_all_replays()
        await message.channel.send("Replay codes have been cleared for all matches.")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to handle the gpt command
async def gpt_command(bot, message):
    msg = message.content
    prompt = msg[len("!vantas "):].strip()
    response = gpt_response(prompt, message.author.global_name)
    await message.channel.send(response)

# Function to show the help message
async def help_command(bot, message):
    help_message = (
        "**Available Commands:**\n"
        "!vantas <message> - Talk to Vantas directly"
        "!history <user_id>* <page>* - Show the match history for a player. Default is you\n"
        "!match <match_id> - Show details for a specific match\n"
        "!replay <match_id> <replay_code> - Store a replay code for a match\n"
        "!leaderboard <game_name> <page>* - Show the leaderboard for a game\n"
        "!rank <user_id>* - Check individual rank for a player. Default is you\n"
        "!setrank <user_id> <game_name> <rank> - Set rank for a player (Admin)\n"
        "!clearrank <user_id> - Clear individual rank for a player (Admin)\n"
        "!clearqueue - Clear all active queues (Admin)\n"
        "!clearreplay - Clear all replay codes (Admin)\n"
        "!help - Show this help message\n"
        "*Commands marked with * are optional*"
    )
    await message.channel.send(help_message)

# Function to check if the user has the "OG" role
def has_og_role(member):
    role_names = [role.name for role in member.roles]
    return "OG" in role_names