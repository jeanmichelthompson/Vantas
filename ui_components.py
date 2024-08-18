import discord
from discord.ui import Button, View

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
        from matchmaking import handle_join_queue
        await handle_join_queue(interaction, self.channel_id)

    @discord.ui.button(label="Leave Queue",
                       style=discord.ButtonStyle.danger,
                       custom_id="leave_queue")
    async def leave_queue_button(self, interaction: discord.Interaction,
                                 button: Button):
        from matchmaking import handle_leave_queue
        await handle_leave_queue(interaction, self.channel_id)

    @discord.ui.button(label="Leaderboard",
                       style=discord.ButtonStyle.secondary,
                       custom_id="leaderboard")
    async def leaderboard_button(self, interaction: discord.Interaction,
                                 button: Button):
        from matchmaking import handle_leaderboard
        await handle_leaderboard(interaction, self.channel_id)

class TeamManagementView(View):
    def __init__(self, team_a, team_b, game_name: str):
        super().__init__()
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name  # Store the game name
        self.update_buttons()

    def update_buttons(self):
        # Clear existing buttons
        self.clear_items()

        # Add buttons for each player
        for player, _ in self.team_a:
            self.add_item(MovePlayerButton(player, "A", "B", self))
        
        for player, _ in self.team_b:
            self.add_item(MovePlayerButton(player, "B", "A", self))

        # Add the confirm button and pass the game name
        self.add_item(ConfirmTeamsButton(self, self.game_name))

class MovePlayerButton(Button):
    def __init__(self, player, from_team, to_team, team_view):
        self.player = player
        self.from_team = from_team
        self.to_team = to_team
        self.team_view = team_view  # Renamed to avoid conflict
        label = f"Move {player.display_name}"
        super().__init__(label=label, style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
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
    def __init__(self, team_view, game_name: str):
        super().__init__(label="Confirm Teams", style=discord.ButtonStyle.success)
        self.team_view = team_view
        self.game_name = game_name

    async def callback(self, interaction: discord.Interaction):
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
        embed.set_footer(text="Good luck to both teams!")

        # Insert match details into Supabase and store the match ID
        from supabase_client import insert_match
        team1 = [str(player.id) for player, _ in self.team_view.team_a]
        team2 = [str(player.id) for player, _ in self.team_view.team_b]
        match_id = insert_match(team1, team2, self.game_name)  # Store the match ID

        # Use followup.send to capture the message ID correctly
        match_message = await interaction.followup.send(embed=embed, ephemeral=False)
        match_message_id = match_message.id  # Store the Discord message ID

        # Now pass the match_message_id when creating MatchCompleteView
        await match_message.edit(view=MatchCompleteView(match_id, self.team_view.team_a, self.team_view.team_b, self.game_name, match_message_id))

        # Delete the original team management message
        await interaction.message.delete()

class MatchCompleteView(View):
    def __init__(self, match_id, team_a, team_b, game_name, match_message_id):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.match_message_id = match_message_id  # Store the Discord message ID
        self.add_item(MatchCompleteButton(match_id, team_a, team_b, game_name, match_message_id))

class MatchCompleteButton(Button):
    def __init__(self, match_id, team_a, team_b, game_name, match_message_id):
        super().__init__(label="Match Complete", style=discord.ButtonStyle.primary)
        self.match_id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.match_message_id = match_message_id  # Store the Discord message ID

    async def callback(self, interaction: discord.Interaction):
        # Create the embed to ask which team won
        embed = discord.Embed(
            title="Select the Winning Team",
            description="Please select the team that won the match.",
            color=discord.Color.gold()
        )
        # Provide buttons to select the winning team
        await interaction.response.send_message(
            embed=embed,
            view=SelectWinnerView(self.team_a, self.team_b, self.match_message_id, self.game_name, self.match_id),
            ephemeral=False
        )

class SelectWinnerView(View):
    def __init__(self, team_a, team_b, match_message_id, game_name, match_id):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.team_a = team_a
        self.team_b = team_b
        self.match_message_id = match_message_id  # Store the Discord message ID
        self.add_item(SelectWinnerButton("Team A", self.team_a, self.team_a, self.team_b, match_message_id, game_name, self.match_id))
        self.add_item(SelectWinnerButton("Team B", self.team_b, self.team_a, self.team_b, match_message_id, game_name, self.match_id))

class SelectWinnerButton(Button):
    def __init__(self, team_name, team, team_a, team_b, match_message_id, game_name, match_id):
        super().__init__(label=f"{team_name} Wins", style=discord.ButtonStyle.success)
        self.team_name = team_name
        self.team = team
        self.team_a = team_a
        self.team_b = team_b
        self.match_message_id = match_message_id
        self.game_name = game_name
        self.match_id = match_id

    async def callback(self, interaction: discord.Interaction):
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
        await interaction.channel.send(embed=embed, view=RequeueView(self.team_a, self.team_b, self.game_name))

        # Update the match in the database as complete
        from supabase_client import update_match, update_rank

        update_match(self.match_id, self.team_name)

        for player, _ in self.team:
            update_rank(player.id, self.game_name, "win")

        losing_team = self.team_b if self.team_name == "Team A" else self.team_a
        for player, _ in losing_team:
            update_rank(player.id, self.game_name, "lose")

class RequeueView(View):
    def __init__(self, team_a, team_b, game_name):
        super().__init__(timeout=None)
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name
        self.add_item(RequeueButton(self.team_a, self.team_b, self.game_name))
        self.add_item(FinishButton())  # Add the Finish button

class RequeueButton(Button):
    def __init__(self, team_a, team_b, game_name):
        super().__init__(label="Requeue", style=discord.ButtonStyle.primary)
        self.team_a = team_a
        self.team_b = team_b
        self.game_name = game_name

    async def callback(self, interaction: discord.Interaction):
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
        await interaction.response.send_message("Requeued! Please confirm the teams.", embed=embed, view=TeamManagementView(new_team_a, new_team_b, self.game_name))
        await interaction.message.delete()

class FinishButton(Button):
    def __init__(self):
        super().__init__(label="Finish", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        # Remove the Requeue and Finish buttons by editing the view
        await interaction.message.edit(view=None)
        await interaction.response.send_message("Match process finished.", ephemeral=True)


def create_team_embed(team_a, team_b):
    embed = discord.Embed(title="Team Management", color=discord.Color.blue())
    embed.add_field(name="**Team A**", value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in team_a]), inline=True)
    embed.add_field(name="**Team B**", value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in team_b]), inline=True)
    embed.set_footer(text="Use the buttons below to edit teams or confirm when ready.")
    return embed
