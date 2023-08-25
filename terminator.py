import discord
from discord.ext import commands, tasks
import aiosqlite
import logging
import sys
import traceback
import random
import json
from pathlib import Path
import signal
import asyncio


# Setup logging
logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()])

# Load the config file
config_path = Path('config.json')
if not config_path.exists():
    logging.error("Config file not found. Exiting...")
    sys.exit()

try:
    with open(config_path, 'r') as f:
        config = json.load(f)
except json.JSONDecodeError:
    logging.error("Could not parse the config file. Please ensure it is valid JSON. Exiting...")
    sys.exit()

# config is the dict loaded from config.json
TOKEN = config.get("TOKEN")
LEADERBOARD_CHANNEL_ID = int(config.get("LEADERBOARD_CHANNEL_ID"))
MOD_ROLE_ID = int(config.get("MOD_ROLE_ID"))

phrases_path = Path('phrases.json')
if not phrases_path.exists():
    logging.error("Phrases file not found. Exiting...")
    sys.exit()

try:
    with open(phrases_path, 'r') as f:
        phrases = json.load(f)
except json.JSONDecodeError:
    logging.error("Could not parse the phrases file. Please ensure it is valid JSON. Exiting...")
    sys.exit()

CONGRATULATIONS_PHRASES = phrases.get("congratulations_phrases")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, reconnect=True)

async def setup():
    try:
        await bot.cursor.execute("CREATE TABLE IF NOT EXISTS leaderboard (mod_id INT, mod_name TEXT, ban_count INT, UNIQUE(mod_id))")
        await bot.cursor.execute("CREATE TABLE IF NOT EXISTS ban_details (mod_id INT, user_id INT)")
        await bot.db.commit()
        logging.info("Database setup completed successfully")
    except Exception as e:
        logging.error(f"Error in setup: {str(e)}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    try:
        channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
        await channel.send(f'An error occurred: {str(error)}')
    except Exception as e:
        logging.error(f"Failed to send error to Discord channel: {str(e)}")

@bot.event
async def on_error(event, *args, **kwargs):
    error_type, error_value, error_traceback = sys.exc_info()
    error_traceback = ''.join(traceback.format_exception(error_type, error_value, error_traceback))
    logging.error(f"An error occurred in {event}: {error_traceback}")

def signal_handler():
    logging.info("Received exit signal. Shutting down...")
    bot.loop.run_until_complete(on_disconnect())
    bot.loop.stop()
    sys.exit(0)

async def execute_db_query(query, parameters=()):
    try:
        await bot.cursor.execute(query, parameters)
        await bot.db.commit()
    except Exception as e:
        logging.error(f"Database error: {str(e)}")
        await bot.db.rollback()

async def update_leaderboard(mod_id, mod_name):
    await execute_db_query("UPDATE leaderboard SET ban_count = ban_count + 1, mod_name = ? WHERE mod_id = ?", (mod_name, mod_id))

async def insert_into_leaderboard(mod_id, mod_name):
    await execute_db_query("INSERT INTO leaderboard (mod_id, mod_name, ban_count) VALUES (?, ?, ?)", (mod_id, mod_name, 1))

async def insert_into_ban_details(mod_id, user_id):
    await execute_db_query("INSERT INTO ban_details (mod_id, user_id) VALUES (?, ?)", (mod_id, user_id))

async def update_ban_count(mod_id: int, mod_name: str, user_id: int):
    try:
        await bot.cursor.execute("SELECT mod_id FROM leaderboard WHERE mod_id = ?", (mod_id,))
        data = await bot.cursor.fetchone()
        if data:
            await update_leaderboard(mod_id, mod_name)
        else:
            await insert_into_leaderboard(mod_id, mod_name)
        await insert_into_ban_details(mod_id, user_id)
    except Exception as e:
        logging.error(f"Error in updating ban count: {str(e)}")

@bot.event
async def on_member_ban(guild, user):
    logging.info(f"Detected a ban event for user {user.name}. Processing...")
    try:
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id and any([role.id == MOD_ROLE_ID for role in entry.user.roles]):
                mod_name = entry.user.name  # get the name of the mod who performed the ban
                mod_id = entry.user.id
                await update_ban_count(mod_id, mod_name, user.id)
                leaderboard = await get_leaderboard()

                # create the embed object
                embed = discord.Embed(color=discord.Color.dark_magenta())
                embed.set_author(name="💀 TERMINATOR RANKINGS 💀", icon_url="https://images.wallpapersden.com/image/download/terminator-6_a2tlbmiUmZqaraWkpJRmbmdlrWZlbWU.jpg")
                
                for rank, record in enumerate(leaderboard, start=1):
                    mod_id, mod_name, ban_count = record
                    embed.add_field(name=f"{rank}. {mod_name}", value=f"🔥 Terminations: {ban_count} 👤", inline=False)

                embed.set_footer(text="The future is not set. There is no fate but what we make for ourselves. 🤖🔫 \nFor detailed terminations, use !kills [username]")

                channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
                await channel.send(embed=embed)  # send the leaderboard
    except Exception as e:
        logging.error(f"Error in handling member ban: {str(e)}")

async def get_leaderboard():
    try:
        await bot.cursor.execute("SELECT * FROM leaderboard ORDER BY ban_count DESC LIMIT 10")
        return await bot.cursor.fetchall()
    except Exception as e:
        logging.error(f"Error in getting leaderboard: {str(e)}")
        return []

async def get_ban_details(mod_id: int):
    try:
        await bot.cursor.execute("SELECT user_id FROM ban_details WHERE mod_id = ?", (mod_id,))
        logging.info("Fetched leaderboard from database")
        return await bot.cursor.fetchall()
    except Exception as e:
        logging.error(f"Error in getting ban details: {str(e)}")

@bot.event
async def on_ready():
    logging.info("Bot is starting up...")
    print(f"We have logged in as {bot.user}")

    # Establish a persistent database connection
    bot.db = await aiosqlite.connect("leaderboard.db")
    bot.cursor = await bot.db.cursor()

    print("Setting up database tables...")
    await setup()
    print("Setup done!")

    logging.info("Bot is now waiting for events or commands...")
    channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)

    # Show the leaderboard on startup
    leaderboard = await get_leaderboard()

    if leaderboard:
        # Create the embed object
        embed = discord.Embed(color=discord.Color.dark_magenta())
        embed.set_author(name="💀 TERMINATOR RANKINGS 💀", icon_url="https://images.wallpapersden.com/image/download/terminator-6_a2tlbmiUmZqaraWkpJRmbmdlrWZlbWU.jpg")
        
        for rank, record in enumerate(leaderboard, start=1):
            mod_id, mod_name, ban_count = record
            embed.add_field(name=f"{rank}. {mod_name}", value=f"🔥 Terminations: {ban_count} 👤", inline=False)

        embed.set_footer(text="The future is not set. There is no fate but what we make for ourselves. 🤖🔫 \nFor detailed terminations, use !kills [username]")
        
        await channel.send(embed=embed)  # Send the leaderboard

        # Get the first and second places
        leader = leaderboard[0]
        runner_up = leaderboard[1] if len(leaderboard) > 1 else None

        # Generate a random congratulation message
        congrats_message = random.choice(CONGRATULATIONS_PHRASES)

        # Generate the message
        message = f"🎉 Congratulations {leader[1]}! 🎉\n{congrats_message}"
        if runner_up:
            message += f"\n\n👀 Look out {leader[1]}, {runner_up[1]} is right behind you! Better step up your game!"
        
        await channel.send(message)  # Send the congratulatory message after the leaderboard

@bot.command()
async def leaderboard(ctx):
    logging.info("Processing leaderboard command...")
    try:
        leaderboard = await get_leaderboard()

        # create the embed object
        embed = discord.Embed(color=discord.Color.dark_magenta())
        embed.set_author(name="💀 TERMINATOR RANKINGS 💀", icon_url="https://images.wallpapersden.com/image/download/terminator-6_a2tlbmiUmZqaraWkpJRmbmdlrWZlbWU.jpg")
        
        for rank, record in enumerate(leaderboard, start=1):
            mod_id, mod_name, ban_count = record
            embed.add_field(name=f"{rank}. {mod_name}", value=f"🔥 Terminations: {ban_count} 👤", inline=False)

        embed.set_footer(text="The future is not set. There is no fate but what we make for ourselves. 🤖🔫 \nFor detailed terminations, use !kills [username]")

        await ctx.send(embed=embed)
    except Exception as e:
        logging.error(f"Error in leaderboard command: {str(e)}")

@bot.command()
async def kills(ctx, *, user: discord.User = None):
    logging.info(f"Processing kills command for user {user.name if user else 'None'}...")
    try:
        if user is None:
            await ctx.send("You need to specify a mod's username! Try !kills [username].")
            return
        mod_id = user.id
        ban_details = await get_ban_details(mod_id)

        # create the embed object
        embed = discord.Embed(color=discord.Color.dark_magenta())
        embed.set_author(name=f"💀 TERMINATOR DETAILS FOR {user.name.upper()} 💀", icon_url="https://i.stack.imgur.com/8zzel.jpg")
        
        if not ban_details:
            embed.description = f"{user.name} has not terminated any users. 🚫🤖"
        else:
            for record in ban_details:
                banned_user_id = record[0]
                try:
                    banned_user = await bot.fetch_user(banned_user_id)
                except discord.NotFound:
                    banned_user_name = "Unknown user"
                else:
                    banned_user_name = banned_user.name
                embed.add_field(name=f"Terminated: {banned_user_name}", value="🔥👤", inline=False)

        await ctx.send(embed=embed)
    except commands.errors.UserNotFound:
        await ctx.send("User not found. Please make sure you've entered the correct username.")
    except Exception as e:
        logging.error(f"Error in kills command: {str(e)}")

@bot.event
async def on_disconnect():
    try:
        if hasattr(bot, 'cursor') and bot.cursor:
            await bot.cursor.close()
    except ValueError as e:
        logging.warning("Cursor was already closed.")

    try:
        if hasattr(bot, 'db') and bot.db:
            await bot.db.close()
    except ValueError as e:
        logging.warning("Database connection was already closed.")

if __name__ == "__main__":
    def signal_handler():
        logging.info("Received exit signal. Shutting down...")
        bot.loop.run_until_complete(on_disconnect())
        bot.loop.stop()
        sys.exit(0)

    # Register the signal handlers
    signal.signal(signal.SIGINT, lambda x, y: signal_handler())
    signal.signal(signal.SIGTERM, lambda x, y: signal_handler())

    try:
        bot.run(TOKEN)
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        bot.loop.run_until_complete(on_disconnect())
        sys.exit(1)  # Exit with a non-zero code to indicate an error
