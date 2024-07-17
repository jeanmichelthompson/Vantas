import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
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
    leaderboard_data = [(record['user_id'], record[game_name]) for record in response.data if record[game_name] > 0]
    return leaderboard_data

def check_rank(user_id: str):
    response = supabase.table('users').select('*').eq('user_id', user_id).single().execute()
    return response.data if response.data else None

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

