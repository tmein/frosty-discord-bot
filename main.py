import discord
from discord import app_commands
from discord.ext import tasks
import database as db

guild_id = open("guild_id.txt", "r").read()
channel_id = int(open("channel_id.txt", "r").read())
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(command_prefix='.', intents=intents)
tree = app_commands.CommandTree(bot)


@tasks.loop(minutes=5)
async def send_update():
    channel = await bot.fetch_channel(channel_id)
    await channel.send("message")


async def send_ephemeral_response(interaction, error, success):
    response = error if error else success
    await interaction.response.send_message(response, ephemeral=True)


@tree.command(name="add-quest", description="Add a daily quest", guild=discord.Object(id=guild_id))
@app_commands.describe(item="The item to look for")
@app_commands.describe(date="The date to add this item to, in YYYY-MM-DD format")
async def add_quest(interaction, item: str, date: str):
    await interaction.response.send_message(f"Quest to look for {item} on {date} added.")


@tree.command(name="add-team", description="Add a Team", guild=discord.Object(id=guild_id))
@app_commands.describe(team_name="Name of the new team")
async def add_team(interaction, team_name: str):
    error = db.add_team(team_name)
    await send_ephemeral_response(interaction, error, f"Successfully added team {team_name}.")


@tree.command(name="rename-team", description="Rename a Team", guild=discord.Object(id=guild_id))
@app_commands.describe(old_name="Old name of the team")
@app_commands.describe(new_name="New name of the team")
async def rename_team(interaction, old_name: str, new_name: str):
    error = db.rename_team(old_name, new_name)
    await send_ephemeral_response(interaction, error, f"Successfully renamed team {old_name} to {new_name}.")


@tree.command(name="add-player", description="Add a Player", guild=discord.Object(id=guild_id))
@app_commands.describe(rsn="RSN of the player")
@app_commands.describe(team_name="Name of the Team to add this player to")
async def add_player(interaction, rsn: str, team_name: str):
    error = db.add_player(rsn, team_name)
    await send_ephemeral_response(interaction, error, f"{rsn} added to {team_name}.")


@tree.command(name="change-rsn", description="Change a Player's RSN", guild=discord.Object(id=guild_id))
@app_commands.describe(old_rsn="old RSN of the player")
@app_commands.describe(new_rsn="new RSN of the player")
async def add_player(interaction, old_rsn: str, new_rsn: str):
    error = db.change_rsn(old_rsn, new_rsn)
    await send_ephemeral_response(interaction, error, f"RSN {old_rsn} updated to be {new_rsn}.")


@tree.command(name="list-teams", description="List teams currently competing", guild=discord.Object(id=guild_id))
async def list_teams(interaction):
    teams = db.list_teams()
    embed = discord.Embed(title=f"__**Competitors:**__", color=0x03f8fc)
    for team_name, members in teams.items():
        embed.add_field(name=f'**{team_name}**', value=members, inline=False)
    await interaction.response.send_message(embed=embed)


@tree.command(name="add-task", description="Add a task", guild=discord.Object(id=guild_id))
@app_commands.describe(description="Human readable task description (this is shown to the players)")
@app_commands.describe(regex_search="Regex search string (this is only used internally)")
@app_commands.describe(number_required="Number of items of this category required")
async def add_task(interaction, description: str, regex_search: str, number_required: int):
    new_id = db.add_task(description, regex_search, number_required)
    await send_ephemeral_response(interaction, None, f"Successfully added task {new_id}.")


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await tree.sync(guild=discord.Object(id=guild_id))
    # send_update.start()


bot.run(open("token.txt", "r").read())
