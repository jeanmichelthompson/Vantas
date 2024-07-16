from replit import db


def log_win(user_id: str, game_name: str):
    print(f"Logging win for user_id: {user_id}, game_name: {game_name}")
    if user_id in db.keys():
        user_data = db[user_id]
        print(f"Existing data for user {user_id}: {user_data}")
        if game_name in user_data.keys():
            user_data[game_name] += 25
        else:
            user_data[game_name] = 25
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: 25}
    print(f"Updated data for user {user_id}: {db[user_id]}")


def log_loss(user_id: str, game_name: str):
    print(f"Logging loss for user_id: {user_id}, game_name: {game_name}")
    if user_id in db.keys():
        user_data = db[user_id]
        print(f"Existing data for user {user_id}: {user_data}")
        if game_name in user_data.keys():
            user_data[game_name] -= 25
        else:
            user_data[game_name] = -25
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: -25}
    print(f"Updated data for user {user_id}: {db[user_id]}")


def get_leaderboard(game_name: str):
    print(f"Fetching leaderboard for game_name: {game_name}")
    leaderboard_data = []
    for user_id in db.keys():
        user_data = db[user_id]
        if game_name in user_data:
            leaderboard_data.append((user_id, user_data[game_name]))
    leaderboard_data.sort(key=lambda x: x[1], reverse=True)
    print(f"Leaderboard data: {leaderboard_data}")
    return leaderboard_data

def check_rank(user_id: str):
    print(f"Checking rank for user_id: {user_id}")
    if user_id in db.keys():
        return db[user_id]
    return None

def clear_rank(user_id: str):
    print(f"Clearing wins for user_id: {user_id}")
    if user_id in db.keys():
        del db[user_id]

def set_rank(user_id: str, game_name: str, rank: int):
    print(f"Setting rank for user_id: {user_id}, game_name: {game_name}, rank: {rank}")
    if user_id in db.keys():
        user_data = db[user_id]
        user_data[game_name] = rank
        db[user_id] = user_data
    else:
        db[user_id] = {game_name: rank}
    print(f"Updated data for user {user_id}: {db[user_id]}")
