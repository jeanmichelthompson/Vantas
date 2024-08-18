import config
from supabase import create_client, Client
from datetime import datetime, timedelta, timezone

url = config.SUPABASE_URL
key = config.SUPABASE_KEY
supabase: Client = create_client(url, key)

# Function to update the rank (score) of a user in a specific game based on the action (win or lose)
def update_rank(user_id: str, game_name: str, action: str):
    print(f"Updating rank for user_id: {user_id}, game_name: {game_name}, action: {action}")

    # Determine the change in score based on the action
    score_change = 25 if action == "win" else -25

    # Fetch the current rank of the user for the game
    response = supabase.table('users').select(game_name).eq('user_id', user_id).execute()

    if len(response.data) == 0:  # User does not exist
        # Insert new user data
        new_data = { "user_id": user_id, game_name: score_change }
        supabase.table('users').insert(new_data).execute()
    else:
        # Update existing user data
        current_rank = response.data[0][game_name] if game_name in response.data[0] else 0
        new_rank = current_rank + score_change
        supabase.table('users').update({ game_name: new_rank }).eq('user_id', user_id).execute()

def get_leaderboard(game_name: str):
    response = supabase.table('users').select('user_id', game_name).order(game_name, desc=True).execute()
    leaderboard_data = [(record['user_id'], record[game_name]) for record in response.data]
    return leaderboard_data

def check_rank(user_id: str):
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

# Function to fetch all user data from the users table
def check_database():
    try:
        response = supabase.table("users").select("*").execute()
        return response.data
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return []
    
# Function to get queue data
def get_queue_data(channel_id):
    response = supabase.table('queues').select('*').eq('channel_id', channel_id).execute()
    return response.data[0] if response.data else None

# Function to update queue data
def update_queue_data(channel_id, data):
    response = supabase.table('queues').upsert(data).execute()
    return response

def increment_ping_if_due():
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
        "winner": None  # Winner will be set once the match is complete
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
    
    if len(response.data) == 0:  # User does not exist
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
            "replay": match_data.get("replay")
        }
    return None

# Function to update the replay code for a specific match
def update_replay_code(match_id: str, replay_code: str):
    response = supabase.table('matches').update({
        "replay": replay_code
    }).eq('id', match_id).execute()
    return response





