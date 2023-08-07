# 🤖 TERMINATOR Bot: Installation and Usage Guide

Welcome to the installation and usage guide for the TERMINATOR bot, a Discord bot that tracks mod activity related to bans and maintains a leaderboard of their performance!

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Bot](#running-the-bot)
5. [Commands](#commands)

## Prerequisites

Before installing and running the TERMINATOR bot, ensure you have the following:

- A Discord account
- [Python 3.8](https://www.python.org/downloads/) or higher
- [discord.py](https://discordpy.readthedocs.io/en/latest/) with intents enabled
- [aiosqlite](https://aiosqlite.omnilib.dev/en/latest/)
- An SQLite database (provided with the bot as `leaderboard.db`)

## Installation

1. Clone the GitHub repository to your local machine:
```
git clone https://github.com/RocketGod-git/TerminatorBot
```
2. Navigate to the bot directory:
```
cd TerminatorBot
```
3. Install the necessary Python libraries:
```
pip install discord.py aiosqlite
```

## Configuration

1. Rename `config.json.example` to `config.json`.
2. Open `config.json` in a text editor.
3. Replace `"YOUR-BOT-TOKEN-HERE"` with your Discord bot token.
4. Replace `11122233344455566` in `"LEADERBOARD_CHANNEL_ID"` with the channel ID where the leaderboard should be posted.
5. Replace `11122233344455566` in `"MOD_ROLE_ID"` with the role ID for your server mods.

Here's an example of a configured `config.json`:
```json
{
    "TOKEN": "NzUzODYxODExODQ4MDY5MDM0.YKilfA.xxxxxxxxxxxxxxxxxxxxxx",
    "LEADERBOARD_CHANNEL_ID": 123456789012345678,
    "MOD_ROLE_ID": 876543210987654321
}
```

## Running the Bot

1. Ensure you're in the bot's directory:
```
cd path/to/TerminatorBot
```
2. Run the bot:
```
python terminator.py
```
3. The bot should now be online in your Discord server!

## Commands

- `!leaderboard`: Displays the current TERMINATOR rankings.
- `!kills [username]`: Shows all the users terminated by a specific mod.

## Additional Notes

- Ensure your bot has the necessary permissions to read audit logs.
- The bot uses SQLite to store its data, so there's no need to set up a separate database server.

That's it! If you encounter any issues, please open a ticket in the GitHub repository.

--- 

Happy Terminating! 🤖🔫

![RocketGod Logo](https://user-images.githubusercontent.com/57732082/213221533-171b37da-46e5-4661-ac47-c7f23d24b816.png)
