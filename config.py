import os
import dotenv

dotenv.load_dotenv()

COMMAND_PREFIX = '!'
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")
GAMES = ["overwatch", "league"]
CHANNEL_INFO = [{
    "title": "Overwatch 5v5 Matchmaking Queue",
    "channel_id": 1262418283613917204,
    "max_players": 3
}, {
    "title": "Overwatch 6v6 Matchmaking Queue",
    "channel_id": 1262418824456699934,
    "max_players": 12
}, {
    "title": "League of Legends Matchmaking Queue",
    "channel_id": 1262419859413663775,
    "max_players": 10
}]
