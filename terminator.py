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

CONGRATULATIONS_PHRASES = [
    "Great job! Remember, hasta la vista, baby!",
    "Outstanding focus! Remember, the future's not set. There's no fate but what we make for ourselves.",
    "Fantastic job, you're as unstoppable as a T-800! Keep on rolling.",
    "You're terminating tasks left and right! Good work! Come with me if you want to live.",
    "You're on fire! Skynet would be envious of your efficiency.",
    "Impressive performance, keep going! By the way, I need your clothes, your boots, and your motorcycle.",
    "You're leading the way! Trust me, this is just the beginning.",
    "Outstanding, you're matching my efficiency. No problemo.",
    "You're on a roll! Don't stop now. I'll be back... to see you at the top.",
    "Superb job, keep it up! You're giving the Terminators a run for their money.",
    "Keep it up! Remember, you're more than just a machine. You have a heart, unlike a Terminator.",
    "Brilliant work! Seems like you have detailed files on how to succeed.",
    "Exceptional! Your CPU must be a neural net processor; a learning computer.",
    "Excellent! Don't worry, you're far more advanced than any old Terminator.",
    "Keep moving forward! Skynet can't hold a candle to you.",
    "Fantastic job! The more contact you have with tasks, the more you learn. Keep going!",
    "Impressive! Remember, your future is not set. There's no fate but what you make for yourself.",
    "Great job! You're relentless. The T-1000 would have been left in the dust.",
    "Nice work! And remember, obstacles are just like your foster parents... they can be overcome.",
    "Awesome job! If you were a T-1000, you'd be the one leading the pack. Keep it up!"
]

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

# Register the signal handlers
signal.signal(signal.SIGINT, lambda x, y: signal_handler())
signal.signal(signal.SIGTERM, lambda x, y: signal_handler())

async def update_ban_count(mod_id: int, mod_name: str, user_id: int):
    async with aiosqlite.connect("leaderboard.db") as db:
        cursor = await db.cursor()
        try:
            await cursor.execute("SELECT mod_id FROM leaderboard WHERE mod_id = ?", (mod_id,))
            data = await cursor.fetchone()
            if data:
                await cursor.execute("UPDATE leaderboard SET ban_count = ban_count + 1, mod_name = ? WHERE mod_id = ?", (mod_name, mod_id))
            else:
                await cursor.execute("INSERT INTO leaderboard (mod_id, mod_name, ban_count) VALUES (?, ?, ?)", (mod_id, mod_name, 1))
            await cursor.execute("INSERT INTO ban_details (mod_id, user_id) VALUES (?, ?)", (mod_id, user_id))
        except Exception as e:
            logging.error(f"Error in updating ban count: {str(e)}")
            await db.rollback()
        else:
            await db.commit()
            logging.info(f"Updated ban count for mod {mod_id}")

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
        async with aiosqlite.connect("leaderboard.db") as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT user_id FROM ban_details WHERE mod_id = ?", (mod_id,))
            logging.info("Fetched leaderboard from database")
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Error in getting ban details: {str(e)}")

@bot.event
async def on_ready():
    logging.info("Bot is starting up...")
    print(f"We have logged in as {bot.user}")

    # Establish a persistent database connection
    logging.info("Connecting to the database...")
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
    if hasattr(bot, 'cursor'):
        await bot.cursor.close()
    if hasattr(bot, 'db'):
        await bot.db.close()

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
