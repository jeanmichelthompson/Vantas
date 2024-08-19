This Discord bot is designed to facilitate competitive gaming within a Discord server. It automates the process of creating and managing matches, maintaining leaderboards, handling real-time queues, and tracking player performance. The bot is highly customizable and integrates deeply with Supabase to store and retrieve match data, player ranks, and more.

Features
1. Real-Time Matchmaking
Users can join and leave queues for various games.
The bot notifies queued players when a match is ready.
It designates an organizer for each match and provides team suggestions based on player ranks.

2. Leaderboard Management
Tracks player performance and ranks across multiple games.
Displays leaderboards in an embedded format, with pagination support to navigate through ranks.
Supports multiple games, and users are ranked based on their in-game performance.

3. Match Tracking and History
Stores match data, including teams, winners, and replay codes.
Users can view their match history with pagination, sorted by the most recent matches.

4. Player Rank Management
Automatically updates player ranks based on match outcomes.
Supports manual rank adjustments by administrators.
Allows users to view their rank profiles, including stats for different games.

5. Queue and Match Management
Automatically clears queues and resets match data on a daily basis.
Provides commands for administrators to manually clear queues or reset replay codes.
Maintains a persistent state of active queues, even after bot restarts.

6. Integration with Supabase
All match data, ranks, and queues are stored in Supabase, ensuring data persistence and easy retrieval.
The bot leverages Supabase's capabilities to manage player data, ensuring scalability and reliability.