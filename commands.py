import random
import config
import discord
from discord.ui import Button, View
from supabase_client import clear_all_queues, clear_all_replays, delete_match, get_head_to_head_record, get_head_to_head_record_against_all, get_match_details, get_leaderboard, get_user, clear_rank, get_user_leaderboard_position, get_wins_and_losses, set_rank, update_replay_code
from openai_client import gpt_response, store_message
from datetime import datetime, timedelta

from ui_components import Paginator


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
        "!h2h": h2h_command,
        "!clearchat": clearchat_command,
        "!clearrank": clearrank_command,
        "!setrank": setrank_command,
        "!clearqueue": clearqueue_command,
        "!clearreplay": clear_replay_command,
        "!deletematch": delete_match_command,
        "!vantas": gpt_command,
        "!help": help_command,
        "!test": test_command,
        "!sigma": sigma_command
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

# Function to display the leaderboard for a specific game
async def leaderboard_command(bot, message):
    msg = message.content
    parts = msg.split()

    if len(parts) > 1:
        game_name = parts[1].lower()
        game_name_display = game_name.capitalize()
        page = 1
        
        if len(parts) > 2 and parts[2].isdigit():
            page = int(parts[2])

        leaderboard_data = get_leaderboard(game_name)
        if not leaderboard_data:
            await message.channel.send(f"{game_name_display} is not a supported game. Supported games: Overwatch, League")
            return

        players_per_page = 10
        total_players = len(leaderboard_data)
        total_pages = (total_players + players_per_page - 1) // players_per_page

        # Create an embed directly
        embed = discord.Embed(
            title=f"{game_name_display} Leaderboard",
            color=discord.Color.green()
        )
        start_index = (page - 1) * players_per_page
        end_index = start_index + players_per_page
        leaderboard_page = leaderboard_data[start_index:end_index]

        await update_leaderboard_embed(embed, leaderboard_page, bot, game_name, page, players_per_page)

        embed.set_footer(text=f"Page {page} of {total_pages}")

        paginator = Paginator(
            bot=bot,
            title=f"{game_name_display} Leaderboard",
            data=leaderboard_data,
            page=page,
            total_pages=total_pages,
            page_size=players_per_page,
            update_func=update_leaderboard_embed,
            game_name=game_name
        )

        # Send the message with the initial embed and the paginator buttons
        await message.channel.send(embed=embed, view=paginator)
    else:
        await message.channel.send("Game name not provided. Usage: !leaderboard <game_name> <page_number>*")

async def update_leaderboard_embed(embed, leaderboard_data, bot, game_name, page, page_size):
    # Calculate the correct starting index for the current page
    start_index = (page - 1) * page_size
    
    for index, (user_id, rank) in enumerate(leaderboard_data, start=start_index + 1):
        user_mention = (await bot.fetch_user(int(user_id))).mention
        embed.add_field(
            name="",
            value=f"{index}. {user_mention}: {rank}",
            inline=False
        )

# Function to display player profile with ranks for each game
async def rank_command(bot, message):
    msg = message.content
    parts = msg.split()
    
    if len(parts) > 1:
        user_identifier = parts[1]
    else:
        user_identifier = str(message.author.id)

    # Resolve user ID from the identifier
    target_user_id = await resolve_user(bot, user_identifier)
    
    if not target_user_id:
        await message.channel.send("User not found or invalid identifier.")
        return

    rank_data = get_user(target_user_id)
    wins_losses_data = get_wins_and_losses(target_user_id)
    user = await bot.fetch_user(target_user_id)
    display_name = user.global_name
    avatar_url = user.avatar.url
    
    if rank_data:
        rank_embed = discord.Embed(
            description=f"User ID: {target_user_id}",
            color=discord.Color.blue()
        )

        # Add the avatar
        rank_embed.set_author(name=display_name + "'s Profile", icon_url=avatar_url)

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

# Function to clear individual rank for a player by user ID or name
async def clearrank_command(bot, message):
    msg = message.content
    if has_og_role(message.author):
        if len(msg.split()) > 1:
            user_identifier = msg.split("!clearrank ", 1)[1]
            
            # Resolve user ID from the identifier
            target_user_id = await resolve_user(bot, user_identifier)
            
            if target_user_id:
                clear_rank(target_user_id)
                await message.channel.send(f"Rank cleared for user {target_user_id}.")
            else:
                await message.channel.send("User not found or invalid identifier.")
        else:
            await message.channel.send("Usage: !clearrank <user_id or username>")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to set individual rank for a player by user ID or name
async def setrank_command(bot, message):
    msg = message.content
    if has_og_role(message.author):
        parts = msg.split()
        if len(parts) == 4:
            user_identifier = parts[1]
            game_name = parts[2].lower()
            rank = int(parts[3])
            
            # Resolve user ID from the identifier
            target_user_id = await resolve_user(bot, user_identifier)
            
            if target_user_id:
                display_name = (await bot.fetch_user(target_user_id)).global_name
                if game_name in config.GAMES:
                    set_rank(target_user_id, game_name, rank)
                    await message.channel.send(f"Rank set to {rank} for user {display_name} in game {game_name.capitalize()}.")
                else:
                    await message.channel.send(f"Invalid game name. Available games: {', '.join(g.capitalize() for g in config.GAMES)}")
            else:
                await message.channel.send("User not found or invalid identifier.")
        else:
            await message.channel.send("Invalid usage. Usage: !setrank <user_id or username> <game_name> <rank>")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to display the match history for a player
async def history_command(bot, message):
    msg = message.content
    parts = msg.split()

    user_identifier = str(message.author.id)
    page = 1

    if len(parts) == 2:
        if parts[1].isdigit():
            page = int(parts[1])
        else:
            user_identifier = parts[1]
    elif len(parts) > 2:
        user_identifier = parts[1]
        if parts[2].isdigit():
            page = int(parts[2])

    target_user_id = await resolve_user(bot, user_identifier)
    if not target_user_id:
        await message.channel.send("User not found or invalid identifier.")
        return

    rank_data = get_user(target_user_id)
    display_name = (await bot.fetch_user(int(target_user_id))).global_name
    if not rank_data or not rank_data.get("matches"):
        await message.channel.send(f"No match history found for user {display_name}.")
        return

    matches_with_time = []
    for match_id in rank_data["matches"]:
        match_details = get_match_details(match_id)
        if match_details:
            match_time = datetime.fromisoformat(match_details["created_at"].replace('Z', '+00:00'))
            matches_with_time.append((match_id, match_time))

    matches_with_time.sort(key=lambda x: x[1], reverse=True)
    sorted_match_ids = [match_id for match_id, _ in matches_with_time]

    matches_per_page = 10
    total_matches = len(sorted_match_ids)
    total_pages = (total_matches + matches_per_page - 1) // matches_per_page

    # Create an embed directly
    embed = discord.Embed(
        title=f"{display_name}'s Match History",
        color=discord.Color.blue()
    )

    start_index = (page - 1) * matches_per_page
    end_index = start_index + matches_per_page
    match_ids_page = sorted_match_ids[start_index:end_index]

    await update_history_embed(embed, match_ids_page, target_user_id)

    embed.set_footer(text=f"Page {page} of {total_pages}")

    paginator = Paginator(
        bot=bot,
        title=f"{display_name}'s Match History",
        data=sorted_match_ids,
        page_size=matches_per_page,
        page=page,
        total_pages=total_pages,
        update_func=update_history_embed,
        target_user_id=target_user_id
    )
    
    # Send the message with the initial embed and the paginator buttons
    await message.channel.send(embed=embed, view=paginator)

async def update_history_embed(embed, match_ids, target_user_id):
    for match_id in match_ids:
        match_details = get_match_details(match_id)
        if not match_details:
            continue

        if target_user_id in match_details["team1"]:
            status = "Win" if match_details["winner"] == "Team A" else "Loss"
        elif target_user_id in match_details["team2"]:
            status = "Win" if match_details["winner"] == "Team B" else "Loss"
        else:
            status = "Unknown"

        match_time = datetime.fromisoformat(match_details["created_at"].replace('Z', '+00:00'))
        match_time_adjusted = match_time - timedelta(hours=4)
        formatted_time = match_time_adjusted.strftime("%B %d, %I:%M%p").replace('AM', 'am').replace('PM', 'pm')
        formatted_time = formatted_time.replace(" 0", " ")

        replay_code = match_details.get("replay")
        replay_text = f"**Replay Code:** {replay_code}\n" if replay_code else ""

        embed.add_field(
            name=f"-----------------------------------------------------------\n{match_details['game'].capitalize()}: {match_id}",
            value=(
                f"**Map:** {match_details['map']}\n"
                f"**Result:** {status}\n"
                f"{replay_text}**Time:** {formatted_time}"
            ),
            inline=False
        )

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

# Function to delete a match by match ID (OG role only)
async def delete_match_command(bot, message):
    msg = message.content
    if has_og_role(message.author):
        parts = msg.split()
        if len(parts) == 2:
            match_id = parts[1]
            try:
                delete_match(match_id)
                await message.channel.send(f"Match {match_id} and associated references have been deleted.")
            except Exception as e:
                await message.channel.send(f"An error occurred while deleting match {match_id}: {e}")
        else:
            await message.channel.send("Invalid usage. Usage: !deletematch <match_id>")
    else:
        await message.channel.send("You do not have permission to use this command.")

# Function to handle the get head-to-head record
async def h2h_command(bot, message):
    msg = message.content
    parts = msg.split()

    if len(parts) == 1:  # Just !h2h, show user's H2H against everyone
        user_identifier = str(message.author.id)

        user_id = await resolve_user(bot, user_identifier)
        if not user_id:
            await message.channel.send("User not found or invalid identifier.")
            return

        records = get_head_to_head_record_against_all(user_id)
        if not records:
            await message.channel.send("No matches found against any players.")
            return

        records_per_page = 15
        total_records = len(records)
        total_pages = (total_records + records_per_page - 1) // records_per_page

        # Create an embed directly
        embed = discord.Embed(
            title=f"{(await bot.fetch_user(user_id)).global_name}'s Head-to-Head Record",
            color=discord.Color.purple()
        )

        start_index = (1 - 1) * records_per_page
        end_index = start_index + records_per_page
        records_page = records[start_index:end_index]

        await update_h2h_embed(embed, records_page, bot)

        embed.set_footer(text=f"Page 1 of {total_pages}")

        paginator = Paginator(
            bot=bot,
            title=f"{(await bot.fetch_user(user_id)).global_name}'s Head-to-Head Record",
            data=records,
            page_size=records_per_page,
            page=1,
            total_pages=total_pages,
            update_func=update_h2h_embed
        )

        # Send the message with the initial embed and the paginator buttons
        await message.channel.send(embed=embed, view=paginator)

    elif len(parts) == 2:  # !h2h <user>
        user_identifier1 = str(message.author.id)
        user_identifier2 = parts[1]

        user1_id = await resolve_user(bot, user_identifier1)
        user2_id = await resolve_user(bot, user_identifier2)

        if not user1_id or not user2_id:
            await message.channel.send("One or both users could not be found.")
            return

        record = get_head_to_head_record(user1_id, user2_id)
        if not record:
            await message.channel.send("No matches found between these two users.")
            return

        h2h_embed = discord.Embed(
            title=f"Head-to-Head: {(await bot.fetch_user(user1_id)).global_name} vs {(await bot.fetch_user(user2_id)).global_name}",
            color=discord.Color.purple()
        )
        h2h_embed.add_field(
            name=f"{(await bot.fetch_user(user1_id)).global_name} Wins",
            value=f"{record['user1_wins']}",
            inline=True
        )
        h2h_embed.add_field(
            name=f"{(await bot.fetch_user(user2_id)).global_name} Wins",
            value=f"{record['user2_wins']}",
            inline=True
        )
        await message.channel.send(embed=h2h_embed)

    elif len(parts) == 3:  # !h2h <user1> <user2>
        user_identifier1 = parts[1]
        user_identifier2 = parts[2]

        user1_id = await resolve_user(bot, user_identifier1)
        user2_id = await resolve_user(bot, user_identifier2)

        if not user1_id or not user2_id:
            await message.channel.send("One or both users could not be found.")
            return

        record = get_head_to_head_record(user1_id, user2_id)
        if not record:
            await message.channel.send("No matches found between these two users.")
            return

        h2h_embed = discord.Embed(
            title=f"Head-to-Head: {(await bot.fetch_user(user1_id)).global_name} vs {(await bot.fetch_user(user2_id)).global_name}",
            color=discord.Color.purple()
        )
        h2h_embed.add_field(
            name=f"{(await bot.fetch_user(user1_id)).global_name} Wins",
            value=f"{record['user1_wins']}",
            inline=True
        )
        h2h_embed.add_field(
            name=f"{(await bot.fetch_user(user2_id)).global_name} Wins",
            value=f"{record['user2_wins']}",
            inline=True
        )
        await message.channel.send(embed=h2h_embed)

    else:
        await message.channel.send("Invalid usage. Usage: !h2h, !h2h <user>, or !h2h <user1> <user2>")

async def update_h2h_embed(embed, records, bot):
    for opponent_id, record in records:
        opponent_name = (await bot.fetch_user(int(opponent_id))).mention
        embed.add_field(
            name="",
            value=f"{opponent_name}: {record['wins']}-{record['losses']}",
            inline=False
        )

# Function to clear the chat in the channel
async def clearchat_command(bot, message):
    msg = message.content
    parts = msg.split()

    # Ensure the user has the OG role
    if not has_og_role(message.author):
        await message.channel.send("You do not have permission to use this command.")
        return

    # Ensure the command is being used correctly
    if len(parts) != 2 or not parts[1].isdigit():
        await message.channel.send("Usage: !clearchat <number>")
        return

    # Get the number of messages to delete
    num_messages = int(parts[1])

    # Limit the number of messages to delete to avoid accidental large deletions
    if num_messages > 100:
        await message.channel.send("You can only delete up to 100 messages at a time.")
        return

    # Delete the messages
    try:
        # Bulk delete messages, including the command message itself
        deleted = await message.channel.purge(limit=num_messages + 1)
        confirmation_msg = await message.channel.send(f"Deleted {len(deleted) - 1} messages.")
        await confirmation_msg.delete(delay=5)  # Delete the confirmation message after 5 seconds
    except discord.Forbidden:
        await message.channel.send("I do not have permission to delete messages in this channel.")
    except discord.HTTPException as e:
        await message.channel.send(f"An error occurred: {str(e)}")

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
        "!history <user>* <page>* - Show the match history for a player. Default is you\n"
        "!match <match_id> - Show details for a specific match\n"
        "!replay <match_id> <replay_code> - Store a replay code for a match\n"
        "!leaderboard <game_name> <page>* - Show the leaderboard for a game\n"
        "!rank <user>* - Check individual rank for a player. Default is you\n"
        "!h2h <user>* <user>* - Show head-to-head record for users. Default is you\n"
        "!setrank <user> <game_name> <rank> - Set rank for a player (Admin)\n"
        "!clearchat <number> - Clear chat messages (Admin)\n"
        "!clearrank <user> - Clear individual rank for a player (Admin)\n"
        "!clearqueue - Clear all active queues (Admin)\n"
        "!clearreplay - Clear all replay codes (Admin)\n"
        "!deletematch <match_id> - Delete a match by ID (Admin)\n"
        "!help - Show this help message\n"
        "*Commands marked with * are optional*"
    )
    await message.channel.send(help_message)

# Function to check if the user has the "OG" role
def has_og_role(member):
    role_names = [role.name for role in member.roles]
    return "OG" in role_names

# Function to resolve a user identifier to a user ID
async def resolve_user(bot, user_identifier):
    guild = bot.get_guild(config.GUILD_ID)
    
    # Fetch all members manually using an async generator
    members = [member async for member in guild.fetch_members(limit=None)]

    if user_identifier.isdigit():
        # Check if it's a user ID
        user = discord.utils.get(members, id=int(user_identifier))
    else:
        # Otherwise, try to find by name
        user = discord.utils.find(lambda m: m.name == user_identifier or m.global_name == user_identifier, members)
    
    return str(user.id) if user else None

# pugx function
async def sigma_command(bot, message):
    await message.channel.send("erm what the sigma")