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
    def __init__(self, team_a, team_b):
        super().__init__()
        self.team_a = team_a
        self.team_b = team_b
        self.update_buttons()

    def update_buttons(self):
        # Clear existing buttons
        self.clear_items()

        # Add buttons for each player
        for player, _ in self.team_a:
            self.add_item(MovePlayerButton(player, "A", "B", self))
        
        for player, _ in self.team_b:
            self.add_item(MovePlayerButton(player, "B", "A", self))

        # Add the confirm button
        self.add_item(ConfirmTeamsButton(self))

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
    def __init__(self, team_view):
        super().__init__(label="Confirm Teams", style=discord.ButtonStyle.success)
        self.team_view = team_view

    async def callback(self, interaction: discord.Interaction):
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
            description=f"**Rank Range:** {min_rank} -> {max_rank}\n\n\n\n",
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

        # Send the confirmation embed
        await interaction.response.send_message(embed=embed, ephemeral=False)

        # Delete the original team management message
        await interaction.message.delete()

def create_team_embed(team_a, team_b):
    embed = discord.Embed(title="Team Management", color=discord.Color.blue())
    embed.add_field(name="**Team A**", value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in team_a]), inline=True)
    embed.add_field(name="**Team B**", value="\n".join([f"{player.mention} (Rank: {rank})" for player, rank in team_b]), inline=True)
    embed.set_footer(text="Use the buttons below to edit teams or confirm when ready.")
    return embed