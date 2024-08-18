import discord
from discord.ui import Button, View

from config import CHANNEL_INFO

# Define a custom view for the queue buttons
class QueueView(View):
    def __init__(self, channel_id):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Join Queue", style=discord.ButtonStyle.primary, custom_id="join_queue")
    async def join_queue_button(self, interaction: discord.Interaction, button: Button):
        from matchmaking import handle_join_queue
        await handle_join_queue(interaction, self.channel_id)

    @discord.ui.button(label="Leave Queue", style=discord.ButtonStyle.danger, custom_id="leave_queue")
    async def leave_queue_button(self, interaction: discord.Interaction, button: Button):
        from matchmaking import handle_leave_queue
        await handle_leave_queue(interaction, self.channel_id)

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.green, custom_id="leaderboard")
    async def leaderboard_button(self, interaction: discord.Interaction, button: Button):
        from matchmaking import handle_leaderboard
        await handle_leaderboard(interaction, self.channel_id)

class TeamManagementView(View):
    def __init__(self, team_a, team_b, game_name: str, organizer_id=None):
        super().__init__()
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id
        self.update_buttons()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow only the organizer to interact with the buttons
        if interaction.user.id != self.organizer_id:
            await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)
            return False
        return True

    def update_buttons(self):
        # Clear existing buttons
        self.clear_items()

        # Add buttons for each player
        for player, _ in self.team_a:
            self.add_item(MovePlayerButton(player, "A", "B", self, self.organizer_id))
        
        for player, _ in self.team_b:
            self.add_item(MovePlayerButton(player, "B", "A", self, self.organizer_id))

        # Add the confirm button and pass the game name
        self.add_item(ConfirmTeamsButton(self, self.game_name, self.organizer_id))

class MovePlayerButton(Button):
    def __init__(self, player, from_team, to_team, team_view, organizer_id=None):
        self.player = player
        self.from_team = from_team
        self.to_team = to_team
        self.team_view = team_view
        self.organizer_id = organizer_id
        label = f"Move {player.display_name}"
        super().__init__(label=label, style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        if not await self.team_view.interaction_check(interaction):
            return
        
        # Find the player's current rank
        if self.from_team == "A":
            player_tuple = next((p, r) for p, r in self.team_view.team_a if p == self.player)
            self.team_view.team_a.remove(player_tuple)
            self.team_view.team_b.append(player_tuple)
        else:
            player_tuple = next((p, r) for p, r in self.team_view.team_b if p == self.player)
            self.team_view.team_b.remove(player_tuple)
            self.team_view.team_a.append(player_tuple)
        
        # Update the buttons in the view
        self.team_view.update_buttons()
        await interaction.response.edit_message(embed=create_team_embed(self.team_view.team_a, self.team_view.team_b), view=self.team_view)

class ConfirmTeamsButton(Button):
    def __init__(self, team_view, game_name: str, organizer_id=None):
        super().__init__(label="Confirm Teams", style=discord.ButtonStyle.success)
        self.team_view = team_view
        self.game_name = game_name
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if not await self.team_view.interaction_check(interaction):
            return 
        
        # Defer the interaction to allow more time to process
        await interaction.response.defer()

        # Combine all players from both teams
        all_players = self.team_view.team_a + self.team_view.team_b

        # Calculate the overall rank range across both teams
        min_rank = min(rank for _, rank in all_players)
        max_rank = max(rank for _, rank in all_players)

        # Calculate the average rank for each team
        avg_rank_a = sum(rank for _, rank in self.team_view.team_a) / len(self.team_view.team_a)
        avg_rank_b = sum(rank for _, rank in self.team_view.team_b) / len(self.team_view.team_b)

        # Create the confirmation embed with the teams, their average ranks, and overall rank range
        embed = discord.Embed(
            title="Match Confirmed!",
            description=f"**Rank Range:** {min_rank} -> {max_rank}",
            color=discord.Color.green()
        )
        embed.add_field(
            name=f"**Team A**\n(Avg Rank: {avg_rank_a:.2f})",
            value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in self.team_view.team_a]),
            inline=True
        )
        embed.add_field(
            name=f"**Team B**\n(Avg Rank: {avg_rank_b:.2f})",
            value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in self.team_view.team_b]),
            inline=True
        )
        embed.set_footer(text="Select a map to proceed.")

        # Insert match details into Supabase and store the match ID
        from supabase_client import insert_match
        team1 = [str(player.id) for player, _ in self.team_view.team_a]
        team2 = [str(player.id) for player, _ in self.team_view.team_b]
        match_id = insert_match(team1, team2, self.game_name)

        # Use followup.send to capture the message ID correctly
        match_message = await interaction.followup.send(embed=embed, ephemeral=False)
        match_message_id = match_message.id

        # Fetch the map pool from Supabase
        from supabase_client import get_map_pool
        map_pool = get_map_pool(self.game_name)

        # Ensure the correct arguments are passed
        select_map_view = SelectMapView(
            maps=map_pool,
            match_id=match_id,
            match_message_id=match_message_id,
            team_a=self.team_view.team_a,
            team_b=self.team_view.team_b,
            game_name=self.game_name,
            organizer_id=self.organizer_id
        )
        
        await match_message.edit(view=select_map_view)

        # Delete the original team management message
        await interaction.message.delete()

class SelectMapView(View):
    def __init__(self, maps, match_id, match_message_id, team_a, team_b, game_name, organizer_id, current_page=1, total_pages=None):
        super().__init__(timeout=None)
        self.maps = maps
        self.match_id = match_id
        self.match_message_id = match_message_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id
        self.current_page = current_page
        self.total_pages = total_pages or (len(maps) + 24) // 25

        # If maps are available, add the map selection dropdown and pagination buttons
        if maps:
            self.add_item(SelectMapDropdown(maps, match_id, match_message_id, team_a, team_b, game_name, organizer_id, current_page, self.total_pages))

            # Add pagination buttons if there are multiple pages
            if self.total_pages > 1:
                self.add_item(PaginationButton("previous", maps, match_id, match_message_id, team_a, team_b, game_name, organizer_id, current_page, self.total_pages))
                self.add_item(PaginationButton("next", maps, match_id, match_message_id, team_a, team_b, game_name, organizer_id, current_page, self.total_pages))
        else:
            # If no maps are available, show the "Match Complete" button directly
            self.add_item(MatchCompleteButton(match_id, team_a, team_b, game_name, match_message_id, organizer_id))

class SelectMapDropdown(discord.ui.Select):
    def __init__(self, maps, match_id, match_message_id, team_a, team_b, game_name, organizer_id, current_page, total_pages):
        super().__init__(
            placeholder=f"Select a map... (Page {current_page}/{total_pages})",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label=map_name) for map_name in maps[(current_page-1)*25 : current_page*25]
            ]
        )
        self.match_id = match_id
        self.match_message_id = match_message_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id
        self.current_page = current_page
        self.total_pages = total_pages

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        selected_map = self.values[0]

        # Update the selected map in the Supabase
        from supabase_client import update_match_map
        update_match_map(self.match_id, selected_map)

        # Fetch the existing embed to update it
        embed = interaction.message.embeds[0]
        embed.description += f"\n**Map:** {selected_map}"
        
        # Acknowledge the interaction and update the message
        await interaction.response.edit_message(embed=embed, view=MatchCompleteView(self.match_id, self.team_a, self.team_b, self.game_name, self.match_message_id, self.organizer_id))

class PaginationButton(discord.ui.Button):
    def __init__(self, direction, maps, match_id, match_message_id, team_a, team_b, game_name, organizer_id, current_page, total_pages):
        super().__init__(label="Previous" if direction == "previous" else "Next", style=discord.ButtonStyle.secondary)
        self.direction = direction
        self.maps = maps
        self.match_id = match_id
        self.match_message_id = match_message_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id
        self.current_page = current_page
        self.total_pages = total_pages

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        if self.direction == "previous":
            new_page = self.current_page - 1 if self.current_page > 1 else self.total_pages
        else:
            new_page = self.current_page + 1 if self.current_page < self.total_pages else 1

        # Create a new SelectMapView with the updated page
        new_view = SelectMapView(self.maps, self.match_id, self.match_message_id, self.team_a, self.team_b, self.game_name, self.organizer_id, new_page, self.total_pages)
        
        # Acknowledge the interaction and update the message
        await interaction.response.edit_message(view=new_view)

class MatchCompleteView(View):
    def __init__(self, match_id, team_a, team_b, game_name, match_message_id, organizer_id=None):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.match_message_id = match_message_id
        self.organizer_id = organizer_id

        # Add the Team Voice button to this view
        self.add_item(TeamVoiceButton(team_a, team_b, game_name, organizer_id))

        # Add the Match Complete button to this view
        self.add_item(MatchCompleteButton(match_id, team_a, team_b, game_name, match_message_id, organizer_id))

class TeamVoiceButton(Button):
    def __init__(self, team_a, team_b, game_name, organizer_id=None):
        super().__init__(label="Team Voice", style=discord.ButtonStyle.primary)
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        # Find the channel info for the game
        channel_info = next((info for info in CHANNEL_INFO if info["title"].lower().startswith(self.game_name.lower())), None)

        if not channel_info:
            return await interaction.response.send_message("Channel information not found for this game.", ephemeral=True)

        # Fetch the voice channel IDs for Team A and Team B
        team_a_channel_id = channel_info["team_a_channel_id"]
        team_b_channel_id = channel_info["team_b_channel_id"]

        # Move Team A members to their voice channel
        team_a_channel = interaction.guild.get_channel(team_a_channel_id)
        if team_a_channel is not None:
            for member, _ in self.team_a:
                if member.voice:  # Check if the member is in a voice channel
                    try:
                        await member.move_to(team_a_channel)
                    except discord.errors.Forbidden:
                        await interaction.response.send_message(f"Could not move {member.mention} to the voice channel. Insufficient permissions.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"{member.mention} is not in a voice channel.", ephemeral=True)

        # Move Team B members to their voice channel
        team_b_channel = interaction.guild.get_channel(team_b_channel_id)
        if team_b_channel is not None:
            for member, _ in self.team_b:
                if member.voice:  # Check if the member is in a voice channel
                    try:
                        await member.move_to(team_b_channel)
                    except discord.errors.Forbidden:
                        await interaction.response.send_message(f"Could not move {member.mention} to the voice channel. Insufficient permissions.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"{member.mention} is not in a voice channel.", ephemeral=True)

        await interaction.response.send_message("Teams have been moved to their respective voice channels.", ephemeral=True)

class MatchCompleteButton(Button):
    def __init__(self, match_id, team_a, team_b, game_name, match_message_id, organizer_id=None):
        super().__init__(label="Match Complete", style=discord.ButtonStyle.green)
        self.match_id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.match_message_id = match_message_id
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        # Create the embed to ask which team won
        embed = discord.Embed(
            title="Select the Winning Team",
            description="Please select the team that won the match.",
            color=discord.Color.gold()
        )
        # Provide buttons to select the winning team
        await interaction.response.send_message(
            embed=embed,
            view=SelectWinnerView(self.team_a, self.team_b, self.match_message_id, self.game_name, self.match_id, self.organizer_id),
            ephemeral=False
        )

class SelectWinnerView(View):
    def __init__(self, team_a, team_b, match_message_id, game_name, match_id, organizer_id=None):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.match_message_id = match_message_id
        self.organizer_id = organizer_id
        self.add_item(SelectWinnerButton("Team A", self.team_a, self.team_a, self.team_b, match_message_id, game_name, self.match_id, self.organizer_id))
        self.add_item(SelectWinnerButton("Team B", self.team_b, self.team_a, self.team_b, match_message_id, game_name, self.match_id, self.organizer_id))

class SelectWinnerButton(Button):
    def __init__(self, team_name, team, team_a, team_b, match_message_id, game_name, match_id, organizer_id=None):
        super().__init__(label=f"{team_name} Wins", style=discord.ButtonStyle.success)
        self.team_name = team_name
        self.team = team
        self.team_a = team_a
        self.team_b = team_b
        self.match_message_id = match_message_id
        self.game_name = game_name
        self.match_id = match_id
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        try:
            # Attempt to delete the "Select Winning Team" embed
            await interaction.message.delete()
        except discord.errors.NotFound:
            pass

        try:
            # Attempt to delete the original "Match Confirmed" embed using the stored Discord message ID
            if self.match_message_id:
                match_message = await interaction.channel.fetch_message(self.match_message_id)
                if match_message:
                    await match_message.delete()
        except discord.errors.NotFound:
            pass
        
        # Announce the winner and print out the teams in an embed
        team_a_names = "\n".join([player.mention for player, _ in self.team_a])
        team_b_names = "\n".join([player.mention for player, _ in self.team_b])

        embed = discord.Embed(
            title=f"**{self.team_name} Wins!**",
            color=discord.Color.gold()
        )
        embed.add_field(name="**Team A**", value=team_a_names, inline=True)
        embed.add_field(name="**Team B**", value=team_b_names, inline=True)
        
        # Send the winner announcement embed with a "Requeue" button
        await interaction.channel.send(embed=embed, view=RequeueView(self.team_a, self.team_b, self.game_name, self.organizer_id))

        # Update the match in the database as complete
        from supabase_client import update_match, update_rank

        update_match(self.match_id, self.team_name)

        for player, _ in self.team:
            update_rank(player.id, self.game_name, "win")

        losing_team = self.team_b if self.team_name == "Team A" else self.team_a
        for player, _ in losing_team:
            update_rank(player.id, self.game_name, "lose")

class RequeueView(View):
    def __init__(self, team_a, team_b, game_name, organizer_id=None):
        super().__init__(timeout=None)
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id

        self.add_item(RequeueButton(self.team_a, self.team_b, self.game_name, self.organizer_id))
        self.add_item(LobbyVoiceButton(self.team_a, self.team_b, self.game_name, self.organizer_id))
        self.add_item(FinishButton(self.organizer_id))

class RequeueButton(Button):
    def __init__(self, team_a, team_b, game_name, organizer_id=None):
        super().__init__(label="Requeue", style=discord.ButtonStyle.green)
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        # Combine players from both teams
        players = self.team_a + self.team_b

        # Fetch the updated ranks from the database
        from supabase_client import check_rank

        updated_players = []
        for player, _ in players:
            rank_data = check_rank(str(player.id))
            if rank_data and self.game_name in rank_data:
                updated_players.append((player, rank_data[self.game_name]))
            else:
                updated_players.append((player, 0))

        # Sort players by rank (optional, depending on your matchmaking logic)
        updated_players.sort(key=lambda x: x[1], reverse=True)

        # Distribute players back into two balanced teams
        new_team_a = []
        new_team_b = []
        for i, (player, rank) in enumerate(updated_players):
            if i % 2 == 0:
                new_team_a.append((player, rank))
            else:
                new_team_b.append((player, rank))

        # Send a message with the new teams
        embed = create_team_embed(new_team_a, new_team_b)
        await interaction.response.send_message("Requeued! Please confirm the teams.", embed=embed, view=TeamManagementView(new_team_a, new_team_b, self.game_name, self.organizer_id))
        await interaction.message.delete()

class LobbyVoiceButton(Button):
    def __init__(self, team_a, team_b, game_name, organizer_id=None):
        super().__init__(label="Move to Lobby", style=discord.ButtonStyle.primary)
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        # Find the channel info for the game
        channel_info = next((info for info in CHANNEL_INFO if info["title"].lower().startswith(self.game_name.lower())), None)

        if not channel_info:
            return await interaction.response.send_message("Channel information not found for this game.", ephemeral=True)

        # Fetch the lobby voice channel ID
        lobby_channel_id = channel_info["lobby_channel_id"]

        # Move all members to the lobby voice channel
        lobby_channel = interaction.guild.get_channel(lobby_channel_id)
        if lobby_channel is not None:
            for member, _ in self.team_a + self.team_b:
                if member.voice:  # Check if the member is in a voice channel
                    try:
                        await member.move_to(lobby_channel)
                    except discord.errors.Forbidden:
                        await interaction.response.send_message(f"Could not move {member.mention} to the lobby voice channel. Insufficient permissions.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"{member.mention} is not in a voice channel.", ephemeral=True)

        await interaction.response.send_message("Teams have been moved back to the lobby voice channel.", ephemeral=True)

class FinishButton(Button):
    def __init__(self, organizer_id=None):
        super().__init__(label="Finish", style=discord.ButtonStyle.danger)
        self.organizer_id = organizer_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.organizer_id:
            return await interaction.response.send_message("You are not the organizer for this game.", ephemeral=True)

        # Get the channel and the queue message ID to exclude from deletion
        channel = interaction.channel

        # Retrieve the original queue message ID from the channel's context
        from matchmaking import queues
        queue_info = queues.get(channel.id)
        if not queue_info or not queue_info.get("message_id"):
            await interaction.response.send_message("Could not find the original queue message.", ephemeral=True)
            return

        original_queue_message_id = queue_info["message_id"]

        # Delete all messages in the channel except the original queue message
        async for message in channel.history(limit=100):
            if message.id != original_queue_message_id and message.author == channel.guild.me:
                try:
                    await message.delete()
                except discord.errors.NotFound:
                    pass 

        # Remove the Requeue and Finish buttons by editing the view
        try:
            await interaction.message.delete()
        except discord.errors.NotFound:
            pass 

        await interaction.response.send_message("Match process finished.", ephemeral=True)

def create_team_embed(team_a, team_b):
    embed = discord.Embed(title="Team Management", color=discord.Color.blue())
    embed.add_field(name="**Team A**", value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in team_a]), inline=True)
    embed.add_field(name="**Team B**", value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in team_b]), inline=True)
    embed.set_footer(text="Use the buttons below to edit teams or confirm when ready.")
    return embed
