import discord
from discord.ui import Button, View
from replit import db

queues = {}


# Define a custom view for the queue buttons
class QueueView(View):

    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id  # Store the channel ID for context

    @discord.ui.button(label="Join Queue",
                       style=discord.ButtonStyle.primary,
                       custom_id="join_queue")
    async def join_queue_button(self, interaction: discord.Interaction,
                                button: Button):
        await handle_join_queue(interaction, self.channel_id)

    @discord.ui.button(label="Leave Queue",
                       style=discord.ButtonStyle.danger,
                       custom_id="leave_queue")
    async def leave_queue_button(self, interaction: discord.Interaction,
                                 button: Button):
        await handle_leave_queue(interaction, self.channel_id)

    @discord.ui.button(label="Leaderboard",
                       style=discord.ButtonStyle.secondary,
                       custom_id="leaderboard")
    async def leaderboard_button(self, interaction: discord.Interaction,
                                 button: Button):
        await interaction.response.send_message(
            "Leaderboard feature not implemented yet.", ephemeral=True)


async def initialize_queues(bot, channel_info):
    for info in channel_info:
        channel = bot.get_channel(info["channel_id"])
        await delete_bot_messages(channel)  # Delete previous bot messages

        # Load the queue state from the database if it exists
        if str(info["channel_id"]) in db.keys():
            queue_state = db[str(info["channel_id"])]
        else:
            queue_state = []

        # Ensure user IDs are integers and filter out any None values (users that could not be found)
        queue_members = []
        for user_id in queue_state:
            user = await bot.fetch_user(int(user_id))
            if user is not None:
                queue_members.append(user)

        queues[info["channel_id"]] = {
            "title": info["title"],
            "queue": queue_members,
            "max_players": info["max_players"],
            "message_id": None
        }
        message = await channel.send(embed=create_queue_embed(
            info["channel_id"]),
                                     view=QueueView(info["channel_id"]))
        queues[info["channel_id"]]["message_id"] = message.id


async def delete_bot_messages(channel):
    async for message in channel.history(limit=100):
        if message.author == channel.guild.me:
            await message.delete()


def create_queue_embed(channel_id):
    queue_info = queues[channel_id]
    embed = discord.Embed(title=queue_info["title"], color=discord.Color.red())
    embed.add_field(name="Players In Queue:",
                    value=format_queue(channel_id),
                    inline=False)
    return embed


def format_queue(channel_id):
    queue = queues[channel_id]["queue"]
    if not queue:
        return "Queue is empty."
    return "\n".join(f"<@{member.id}>" for member in queue)


async def handle_join_queue(interaction: discord.Interaction, channel_id):
    user = interaction.user
    queue_info = queues[channel_id]
    queue = queue_info["queue"]
    max_players = queue_info["max_players"]

    if user not in queue:
        queue.append(user)
        # Save the updated queue state to the database
        db[str(channel_id)] = [member.id for member in queue]
        await update_queue_message(interaction.channel, channel_id)
        if len(queue) == max_players:
            await interaction.channel.send("Match is ready! " +
                                           ", ".join(member.mention
                                                     for member in queue))
            queue.clear()
            # Clear the queue state in the database
            db[str(channel_id)] = []
            await update_queue_message(interaction.channel, channel_id)
    await interaction.response.send_message("You have joined the queue.",
                                            ephemeral=True)


async def handle_leave_queue(interaction: discord.Interaction, channel_id):
    user = interaction.user
    queue = queues[channel_id]["queue"]
    if user in queue:
        queue.remove(user)
        # Save the updated queue state to the database
        db[str(channel_id)] = [member.id for member in queue]
        await update_queue_message(interaction.channel, channel_id)
    await interaction.response.send_message("You have left the queue.",
                                            ephemeral=True)


async def update_queue_message(channel, channel_id):
    message_id = queues[channel_id]["message_id"]
    message = await channel.fetch_message(message_id)
    await message.edit(embed=create_queue_embed(channel_id),
                       view=QueueView(channel_id))
