import config
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone

url = config.SUPABASE_URL
key = config.SUPABASE_KEY
supabase: Client = create_client(url, key) # type: ignore # type: ignore

# Function to update the rank (score) of a user in a specific game based on the action (win or lose)
def update_rank(user_id: str, game_name: str, action: str):
    print(f"Updating rank for user_id: {user_id}, game_name: {game_name}, action: {action}")

    # Determine the change in score based on the action
    score_change = 25 if action == "win" else -25

    # Fetch the current rank of the user for the game
    response = supabase.table('users').select(game_name).eq('user_id', user_id).execute()

    if len(response.data) == 0: 
        # Insert new user data
        new_data = { "user_id": user_id, game_name: score_change }
        supabase.table('users').insert(new_data).execute()
    else:
        # Update existing user data
        current_rank = response.data[0][game_name] if game_name in response.data[0] else 0
        new_rank = current_rank + score_change
        supabase.table('users').update({ game_name: new_rank }).eq('user_id', user_id).execute()

# Function to get the leaderboard for a specific game
def get_leaderboard(game_name: str):
    try:
        # Attempt to select the column associated with the game_name
        response = supabase.table('users').select('user_id', game_name).order(game_name, desc=True).execute()
        
        # Check if there is any data returned
        if not response.data:
            return None
        
        # Process the data if available
        leaderboard_data = [(record['user_id'], record[game_name]) for record in response.data]
        return leaderboard_data
    except Exception as e:
        # Handle the case where the column does not exist
        if 'column' in str(e) and 'does not exist' in str(e):
            return None
        else:
            # Re-raise the exception if it's something unexpected
            raise e
        
def get_user_leaderboard_position(game_name: str, user_id: str):
    leaderboard_data = get_leaderboard(game_name)
    
    if leaderboard_data is None:
        print(f"Debug: No leaderboard data found for game '{game_name}'")
        return None, None

    for position, (uid, mmr) in enumerate(leaderboard_data, start=1):
        if uid == user_id:
            return position, mmr
    
    return None, None

def get_user(user_id: str):
    response = supabase.table('users').select('*').eq('user_id', user_id).execute()
    return response.data[0] if response.data else None

def clear_rank(user_id: str):
    # Set all game columns to 0 for the specified user
    supabase.table('users').update({
        'overwatch': 0,
        'league': 0,
        # Add more game columns as needed
    }).eq('user_id', user_id).execute()

def set_rank(user_id: str, game_name: str, rank: int):
    supabase.table('users').upsert({
        'user_id': user_id,
        game_name: rank
    }).execute()
    
# Function to get queue data
def get_queue_data(channel_id):
    response = supabase.table('queues').select('*').eq('channel_id', channel_id).execute()
    return response.data[0] if response.data else None

# Function to update queue data
def update_queue_data(channel_id, data):
    response = supabase.table('queues').upsert(data).execute()
    return response

def increment_ping_if_due(bot):
    try:
        # Fetch the latest ping record
        response = supabase.table('ping').select('*').order('updated_at', desc=True).limit(1).execute()

        if response.data:
            ping_record = response.data[0]
            updated_at = datetime.fromisoformat(ping_record['updated_at'].replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            
            # Check if more than a day has passed
            if current_time > updated_at + timedelta(days=1):
                # Update the ping count and updated_at timestamp
                new_ping_value = ping_record['ping'] + 1
                supabase.table('ping').update({
                    'ping': new_ping_value,
                    'updated_at': 'now()',
                }).eq('id', ping_record['id']).execute()
                print(f"Ping incremented to {new_ping_value} and updated_at set to current time.")
            else:
                print("Less than a day has passed since the last update. No update necessary.")
        else:
            # No records exist, so insert a new record
            supabase.table('ping').insert({
                'ping': 1,
                'created_at': 'now()',
                'updated_at': 'now()'
            }).execute()
            print("No records found. New ping record created with ping = 1.")

    except Exception as e:
        print(f"Error updating ping: {e}")

# Function to insert a new match into the matches table
def insert_match(team1: list, team2: list, game: str, status: str = "ongoing"):
    new_match = {
        "team1": team1,
        "team2": team2,
        "game": game,
        "status": status,
        "winner": None
    }
    response = supabase.table('matches').insert(new_match).execute()
    
    if response.data:
        match_id = response.data[0]["id"]

        # Update the matches column for each user in both teams
        for user_id in team1 + team2:
            update_user_matches(user_id, match_id)
        
        return match_id
    return None

# Function to update the match as complete and set the winner
def update_match(match_id: str, winner: str):
    response = supabase.table('matches').update({
        "status": "complete",
        "winner": winner
    }).eq('id', match_id).execute()
    return response

def update_user_matches(user_id: str, match_id: str):
    # Fetch the current matches array for the user
    response = supabase.table('users').select('matches').eq('user_id', user_id).execute()
    
    if len(response.data) == 0:
        # Insert new user data with the match ID
        new_data = {"user_id": user_id, "matches": [match_id]}
        supabase.table('users').insert(new_data).execute()
    else:
        current_matches = response.data[0].get('matches', [])
        if current_matches is None:
            current_matches = []

        # Append the new match ID
        updated_matches = current_matches + [match_id]

        # Update the user's matches array
        supabase.table('users').update({"matches": updated_matches}).eq('user_id', user_id).execute()

# Function to get match details, including the replay code
def get_match_details(match_id: str):
    response = supabase.table('matches').select('*').eq('id', match_id).execute()
    if response.data:
        match_data = response.data[0]
        return {
            "team1": match_data["team1"],
            "team2": match_data["team2"],
            "winner": match_data["winner"],
            "game": match_data["game"],
            "created_at": match_data["created_at"],
            "map": match_data.get("map"),
            "replay": match_data.get("replay")
        }
    return None

# Function to update the replay code for a specific match
def update_replay_code(match_id: str, replay_code: str):
    response = supabase.table('matches').update({
        "replay": replay_code
    }).eq('id', match_id).execute()
    return response

# Function to check if a user is an organizer
def is_organizer(user_id: str):
    response = supabase.table('organizers').select('users').execute()
    if response.data:
        for record in response.data:
            if user_id in record['users']:
                return True
    return False

# Function to get the map pool for a specific game
def get_map_pool(game_name: str):
    response = supabase.table('maps').select('map_pool').eq('id', game_name).execute()
    if response.data:
        return response.data[0]['map_pool']
    return []

# Function to update the map for a specific match
def update_match_map(match_id: str, map_name: str):
    response = supabase.table('matches').update({
        "map": map_name
    }).eq('id', match_id).execute()
    return response

# Function to clear all active queues
async def clear_all_queues(bot):
    from matchmaking import queues, update_queue_message
    for channel_info in config.CHANNEL_INFO:
        channel_id = channel_info['channel_id']
        queue_info = queues.get(channel_id)
        
        if queue_info:
            # Clear the in-memory queue
            queue_info["queue"].clear()

            # Update the queue state in Supabase
            update_queue_data(channel_id, {
                "channel_id": channel_id,
                "title": queue_info["title"],
                "queue": [],
                "max_players": queue_info["max_players"],
                "message_id": queue_info["message_id"]
            })

            channel = bot.get_channel(channel_id)
            await update_queue_message(channel, channel_id)

    print("All active queues have been cleared.")

# Function to clear the replay codes for all matches
def clear_all_replays():
    try:
        # Set the replay column to NULL (or None in Python) for all matches
        supabase.table('matches').update({
            "replay": None
        }).execute()
        print("All replay codes have been cleared.")
    except Exception as e:
        print(f"Error clearing replay codes: {e}")

def get_wins_and_losses(user_id: str):
    # Fetch all match IDs associated with the user
    user_data = supabase.table('users').select('matches').eq('user_id', user_id).execute()

    if not user_data.data:
        return None

    matches = user_data.data[0].get('matches', [])
    if not matches:
        return None

    wins_losses = {}

    # Iterate through each match to determine win/loss
    for match_id in matches:
        match_data = supabase.table('matches').select('*').eq('id', match_id).execute()

        if not match_data.data:
            continue

        match = match_data.data[0]

        # Determine if the user was on Team A or Team B
        if user_id in match['team1']:
            user_team = 'Team A'
        elif user_id in match['team2']:
            user_team = 'Team B'
        else:
            continue  # User was not part of this match

        # Check which team won and update the wins/losses count
        game_name = match['game'].lower()
        if game_name not in wins_losses:
            wins_losses[game_name] = {'wins': 0, 'losses': 0}

        if match['winner'] == user_team:
            wins_losses[game_name]['wins'] += 1
        else:
            wins_losses[game_name]['losses'] += 1

    return wins_losses

def delete_match(match_id: str):
    try:
        # Delete the match from the matches table
        supabase.table('matches').delete().eq('id', match_id).execute()

        # Fetch all users that have the match_id in their matches array
        users_with_match = supabase.table('users').select('user_id', 'matches').execute()

        # Iterate through users and update their matches array
        for user in users_with_match.data:
            if match_id in user['matches']:
                updated_matches = [mid for mid in user['matches'] if mid != match_id]

                # Update the user's matches array
                supabase.table('users').update({'matches': updated_matches}).eq('user_id', user['user_id']).execute()

        print(f"Match {match_id} and associated references in user matches have been deleted.")
    
    except Exception as e:
        print(f"Error deleting match {match_id}: {e}")

# Function to get the head-to-head record between two users
def get_head_to_head_record(user1_id: str, user2_id: str):
    # Fetch all matches where both users participated on opposing teams
    response = supabase.table('matches').select('*').execute()

    if not response.data:
        return None

    wins_losses = {'user1_wins': 0, 'user2_wins': 0}

    for match in response.data:
        if (user1_id in match['team1'] and user2_id in match['team2']) or (user1_id in match['team2'] and user2_id in match['team1']):
            # Determine which user was on the winning team
            if match['winner'] == 'Team A' and user1_id in match['team1']:
                wins_losses['user1_wins'] += 1
            elif match['winner'] == 'Team B' and user1_id in match['team2']:
                wins_losses['user1_wins'] += 1
            elif match['winner'] == 'Team A' and user2_id in match['team1']:
                wins_losses['user2_wins'] += 1
            elif match['winner'] == 'Team B' and user2_id in match['team2']:
                wins_losses['user2_wins'] += 1

    return wins_losses

def get_head_to_head_record_against_all(user_id: str):
    # Fetch all matches where the user participated
    response = supabase.table('matches').select('*').execute()

    if not response.data:
        return None

    h2h_records = {}

    for match in response.data:
        # Determine if the user was on Team A or Team B
        if user_id in match['team1']:
            user_team = 'Team A'
            opponent_team = 'Team B'
            opponents = match['team2']
        elif user_id in match['team2']:
            user_team = 'Team B'
            opponent_team = 'Team A'
            opponents = match['team1']
        else:
            continue  # User was not part of this match

        # Check the result and update the head-to-head records
        for opponent_id in opponents:
            if opponent_id not in h2h_records:
                h2h_records[opponent_id] = {'wins': 0, 'losses': 0}

            if match['winner'] == user_team:
                h2h_records[opponent_id]['wins'] += 1
            else:
                h2h_records[opponent_id]['losses'] += 1

    # Filter out records with no wins or losses
    filtered_records = {k: v for k, v in h2h_records.items() if v['wins'] > 0 or v['losses'] > 0}

    # Sort by win/loss ratio
    sorted_records = sorted(filtered_records.items(), key=lambda x: (x[1]['wins'] / max(x[1]['losses'], 1)), reverse=True)

    return sorted_records