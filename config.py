import os
import dotenv

dotenv.load_dotenv()

COMMAND_PREFIX = '!'
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_KEY = os.getenv("OPENAI_KEY")
GAMES = ["overwatch", "league"]
GUILD_ID = 1262417429305360395
CHANNEL_INFO = [{
    "title": "Overwatch 5v5 Matchmaking Queue",
    "channel_id": 1262418283613917204,
    "max_players": 10,
    "lobby_channel_id": 1262418541378928680,
    "team_a_channel_id": 1262418597171564566,
    "team_b_channel_id": 1262418624694714469
}, {
    "title": "Overwatch 6v6 Matchmaking Queue",
    "channel_id": 1262418824456699934,
    "max_players": 12,
    "lobby_channel_id": 1262418541378928680,
    "team_a_channel_id": 1262418597171564566,
    "team_b_channel_id": 1262418624694714469
}, {
    "title": "League of Legends Matchmaking Queue",
    "channel_id": 1262419859413663775,
    "max_players": 10,
    "lobby_channel_id": 1262420021313802240,
    "team_a_channel_id": 1262420040549142548,
    "team_b_channel_id": 1262420062543810673
}, {
    "title": "Marvel Rivals Matchmaking Queue",
    "channel_id": 1312242484083949698,
    "max_players": 12,
    "lobby_channel_id": 1312242536357560401,
    "team_a_channel_id": 1312242571128602644,
    "team_b_channel_id": 1312242592750239765
}]
