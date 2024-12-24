from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
from discord.utils import get
import asyncio
import subprocess

# Load environment variables from .env file
load_dotenv()

# Get the token from the environment
TOKEN = os.getenv('DISCORD_TOKEN')

# Make sure the token is loaded correctly
if TOKEN is None:
    print("Token is not loaded! Please check your .env file.")
    exit()

# Configure the bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Allows access to message content
bot = commands.Bot(command_prefix="!", intents=intents)

# Category IDs for duo, squad, and no-limit channels
DUO_CATEGORY_ID = 1318188721639526420
SQUAD_CATEGORY_ID = 1317501506861400094
NO_LIMIT_CATEGORY_ID = 1316851346317770819

# Main voice channel IDs for creating temporary channels
DUO_MAIN_VOICE_CHANNEL_ID = 1320345888639680634
SQUAD_MAIN_VOICE_CHANNEL_ID = 1320347193747570709
NO_LIMIT_MAIN_VOICE_CHANNEL_ID = 1316851346317770820

# Text channel IDs for bot and log channels
BOT_TEXT_CHANNEL_ID = 1316851346317770818
LOG_CHANNEL_ID = 1319010633928146965

# Dictionary to track created channels
created_channels = {}

# Setting up asyncio for Windows
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    if bot.user:
        print(f"Bot connected as {bot.user}")

@bot.event
async def on_voice_state_update(member, before, after):
    log_channel = get(member.guild.text_channels, id=LOG_CHANNEL_ID)
    print(f"Voice state update triggered by {member.name}. Before: {before.channel}, After: {after.channel}")

    if after.channel and after.channel.id in [DUO_MAIN_VOICE_CHANNEL_ID, SQUAD_MAIN_VOICE_CHANNEL_ID, NO_LIMIT_MAIN_VOICE_CHANNEL_ID]:
        if after.channel.id == DUO_MAIN_VOICE_CHANNEL_ID:
            category_id = DUO_CATEGORY_ID
            channel_limit = 2
        elif after.channel.id == SQUAD_MAIN_VOICE_CHANNEL_ID:
            category_id = SQUAD_CATEGORY_ID
            channel_limit = 4
        elif after.channel.id == NO_LIMIT_MAIN_VOICE_CHANNEL_ID:
            category_id = NO_LIMIT_CATEGORY_ID
            channel_limit = None
        else:
            return

        category = get(member.guild.categories, id=category_id)
        if category:
            if after.channel is not None:
                channel_name = f"{member.display_name}'s Channel"
                temp_channel = await category.create_voice_channel(channel_name, user_limit=channel_limit)
                print(f"Temporary channel created: {temp_channel.name}")

                await member.move_to(temp_channel)

                created_channels[temp_channel.id] = member.id

                if log_channel:
                    await log_channel.send(f"{member.display_name} created channel {temp_channel.name} in category {category.name}.")

    if before.channel and before.channel.id in created_channels:
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del created_channels[before.channel.id]
            print(f"Temporary channel deleted: {before.channel.name}")

            if log_channel:
                await log_channel.send(f"Temporary channel {before.channel.name} has been deleted as it was empty.")

@bot.command()
async def private(ctx):
    print(f"private command triggered by {ctx.author.name}")
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if channel.id in created_channels and created_channels[channel.id] == ctx.author.id:
            overwrite = discord.PermissionOverwrite()
            overwrite.connect = False
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

            bot_channel = get(ctx.guild.text_channels, id=BOT_TEXT_CHANNEL_ID)
            if bot_channel:
                await bot_channel.send(f"Channel {channel.name} is now private.")

            log_channel = get(ctx.guild.text_channels, id=LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"{ctx.author.display_name} made the channel {channel.name} private.")
        else:
            await ctx.author.send("Only the channel owner can make it private.")
    else:
        await ctx.author.send("You must be in your channel to make it private.")

@bot.command()
async def open_channel(ctx):
    print(f"open_channel command triggered by {ctx.author.name}")

    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
        if channel.id in created_channels and created_channels[channel.id] == ctx.author.id:
            overwrite = discord.PermissionOverwrite()
            overwrite.connect = True
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

            bot_channel = get(ctx.guild.text_channels, id=BOT_TEXT_CHANNEL_ID)
            if bot_channel:
                await bot_channel.send(f"Channel {channel.name} is now open to everyone.")

            log_channel = get(ctx.guild.text_channels, id=LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"{ctx.author.display_name} opened the channel {channel.name} to everyone.")
        else:
            await ctx.author.send("Only the channel owner can open it to others.")
    else:
        await ctx.author.send("You must be in your channel to open it.")

@bot.command()
async def clear(ctx):
    print(f"clear command triggered by {ctx.author.name}")
    if ctx.author.guild_permissions.manage_messages:
        deleted = await ctx.channel.purge(limit=100)
        delete_msg = await ctx.send(f"Deleted {len(deleted)} messages.")

        # Delete the message after 5 seconds
        await asyncio.sleep(5)
        await delete_msg.delete()

        log_channel = get(ctx.guild.text_channels, id=LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"{ctx.author.display_name} cleared {len(deleted)} messages in {ctx.channel.name}.")
    else:
        await ctx.send("You do not have permission to clear messages.")

# Command for restarting the bot
@bot.command()
@commands.has_permissions(administrator=True)
async def restart(ctx):
    await ctx.send("Restarting bot...")

    # Restart the bot process
    subprocess.call(["pm2", "restart", "discord-bot"])

    # Close the bot session
    await bot.close()

# Start the bot
bot.run(TOKEN)
