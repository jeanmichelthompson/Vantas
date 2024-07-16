from replit import db


# Function to update the rank (score) of a user in a specific game based on the action (win or lose)
def update_rank(user_id: str, game_name: str, action: str):
    # Print log message
    print(f"Updating rank for user_id: {user_id}, game_name: {game_name}, action: {action}")

    # Determine the change in score based on the action
    score_change = 25 if action == "win" else -25

    # Check if the user exists in the database and update their rank
    if user_id in db.keys():
        user_data = db[user_id]
        print(f"Existing data for user {user_id}: {user_data}")
        if game_name in user_data.keys():
            user_data[game_name] += score_change
        else:
            user_data[game_name] = score_change
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: score_change}

    print(f"Updated data for user {user_id}: {db[user_id]}")


# Function to get the leaderboard for a specific game
def get_leaderboard(game_name: str):
    print(f"Fetching leaderboard for game_name: {game_name}")
    # Initialize the leaderboard data list
    leaderboard_data = []
    # Iterate through all users in the database and display their rank
    for user_id in db.keys():
        user_data = db[user_id]
        if game_name in user_data:
            leaderboard_data.append((user_id, user_data[game_name]))
    # Sort the leaderboard by score in descending order and return
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)
    print(f"Leaderboard data: {leaderboard_data}")
    return leaderboard_data

# Function to check the rank (score) of a specific user
def check_rank(user_id: str):
    print(f"Checking rank for user_id: {user_id}")
    # Check if the user exists in the database and return
    if user_id in db.keys():
        return db[user_id]
    # Return None if the user does not exist in the database
    return None

# Function to clear the rank (score) of a specific user
def clear_rank(user_id: str):
    print(f"Clearing wins for user_id: {user_id}")
    # Check if the user exists in the database and delete their rank
    if user_id in db.keys():
        del db[user_id]

# Function to set the rank (score) of a specific user in a specific game
def set_rank(user_id: str, game_name: str, rank: int):
    print(
        f"Setting rank for user_id: {user_id}, game_name: {game_name}, rank: {rank}"
    )
    # Check if the user exists in the database and update their rank
    if user_id in db.keys():
        user_data = db[user_id]
        user_data[game_name] = rank
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: rank}
    print(f"Updated data for user {user_id}: {db[user_id]}")
