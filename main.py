import asyncio
import os
from datetime import date, datetime, timezone
from io import StringIO

import discord
from discord import app_commands, HTTPException
from discord.ext import tasks
import database as db
from constants import DAY_FORMAT, DATETIME_FORMAT
from structures import Progress, DropNotification

guild_id = os.environ["GUILD_ID"]
channel_id = int(os.environ["CHANNEL_ID"])
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(command_prefix='.', intents=intents)
tree = app_commands.CommandTree(bot)


@tasks.loop(minutes=5)
async def send_update():
    print("Beginning periodic update")
    current_day: date = datetime.now(timezone.utc).date()
    channel = await bot.fetch_channel(channel_id)
    last_checked_day = db.get_last_day()
    if last_checked_day is None or last_checked_day < current_day:
        db.set_new_day(current_day)
        embed = discord.Embed(title=f"__**It's a new day!**__", color=0x03f8fc)
        if last_checked_day is not None:
            progress: Progress = Progress()
            error = db.check_day(last_checked_day, progress)
            if not error:
                for team_name, score in progress.scores.items():
                    lives: int = db.update_lives(team_name, score.all_completed)
                    title: str = f'**{team_name} - {lives * '❤️'} **'
                    if score.all_completed:
                        content: str = f'{team_name} completed yesterday\'s quest, congratulations!'
                    elif not score.all_completed and lives > 0:
                        content: str = f'{team_name} failed to complete yesterday\'s quest.'
                    else:
                        content: str = (
                            f'{team_name} failed to complete yesterday\'s quest and dropped to 0 lives. They '
                            f'have been eliminated.')
                    embed.add_field(name=title, value=content, inline=False)
        error, result = db.get_day_task_description(current_day)
        embed.add_field(name="Today's Task", value=result, inline=False)
        await channel.send(embed=embed)

    loop = asyncio.get_running_loop()
    notifications: list[DropNotification] = await loop.run_in_executor(None, db.periodic_update, current_day)
    for notification in notifications:
        embed = discord.Embed(color=0x03f8fc)
        embed.add_field(name=notification.header, value=notification.body, inline=False)
        embed.set_thumbnail(
            url=f"https://secure.runescape.com/m=avatar-rs/{notification.rsn.replace(' ', "_")}/chat.png")
        await channel.send(embed=embed)
    print("Finished periodic update")

async def send_ephemeral_response(interaction, error, success):
    response = error if error else success
    await interaction.send_message(response, ephemeral=True)


@tree.command(name="add-team", description="Add a Team", guild=discord.Object(id=guild_id))
@app_commands.describe(team_name="Name of the new team")
async def add_team(interaction, team_name: str):
    error = db.add_team(team_name)
    await send_ephemeral_response(interaction.response, error, f"Successfully added team {team_name}.")


@tree.command(name="rename-team", description="Rename a Team", guild=discord.Object(id=guild_id))
@app_commands.describe(old_name="Old name of the team")
@app_commands.describe(new_name="New name of the team")
async def rename_team(interaction, old_name: str, new_name: str):
    error = db.rename_team(old_name, new_name)
    await send_ephemeral_response(interaction.response, error, f"Successfully renamed team {old_name} to {new_name}.")


@tree.command(name="add-player", description="Add a Player", guild=discord.Object(id=guild_id))
@app_commands.describe(rsn="RSN of the player")
@app_commands.describe(team_name="Name of the Team to add this player to")
async def add_player(interaction, rsn: str, team_name: str):
    error = db.add_player(rsn, team_name)
    await send_ephemeral_response(interaction.response, error, f"{rsn} added to {team_name}.")


@tree.command(name="change-rsn", description="Change a Player's RSN", guild=discord.Object(id=guild_id))
@app_commands.describe(old_rsn="old RSN of the player")
@app_commands.describe(new_rsn="new RSN of the player")
async def change_rsn(interaction, old_rsn: str, new_rsn: str):
    error = db.change_rsn(old_rsn, new_rsn)
    await send_ephemeral_response(interaction.response, error, f"RSN {old_rsn} updated to be {new_rsn}.")


@tree.command(name="list-teams", description="List teams currently competing", guild=discord.Object(id=guild_id))
async def list_teams(interaction):
    await interaction.response.defer()
    teams = db.list_teams()
    embed = discord.Embed(title=f"__**Competitors:**__", color=0x03f8fc)
    for team_name, members in teams.items():
        embed.add_field(name=f'**{team_name}**', value=members, inline=True)
    await interaction.followup.send(embed=embed)


@tree.command(name="add-task", description="Add a task", guild=discord.Object(id=guild_id))
@app_commands.describe(day="Day to add this task to in DD-mmm-YYYY (e.g. 01-Jan-1970)")
@app_commands.describe(description="Human readable task description (this is shown to the players)")
@app_commands.describe(regex_search="Regex search string (this is only used internally)")
@app_commands.describe(number_required="Number of items of this category required")
async def add_task(interaction, day: str, description: str, regex_search: str, number_required: int):
    date_object: date = datetime.strptime(day, DAY_FORMAT).date()
    db.add_task(date_object, description, regex_search, number_required)
    await send_ephemeral_response(interaction.response, None, f"Successfully added task to {day}.")


@tree.command(name="edit-task", description="Edit a task", guild=discord.Object(id=guild_id))
@app_commands.describe(identifier="ID of the task (can be found with /admin-day-view)")
@app_commands.describe(description="Human readable task description (this is shown to the players)")
@app_commands.describe(regex_search="Regex search string (this is only used internally)")
@app_commands.describe(number_required="Number of items of this category required")
async def edit_task(interaction, identifier: int, description: str = None, regex_search: str = None,
                    number_required: int = None):
    error = db.edit_task(identifier, description, regex_search, number_required)
    await send_ephemeral_response(interaction.response, error, f"Successfully updated task {identifier}.")


@tree.command(name="remove-task", description="Remove a task", guild=discord.Object(id=guild_id))
@app_commands.describe(identifier="ID of the task (can be found with /admin-day-view)")
async def remove_task(interaction, identifier: int):
    error = db.remove_task(identifier)
    await send_ephemeral_response(interaction.response, error, f"Successfully removed {identifier}")


@tree.command(name="set-password", description="Set the password for the given day",
              guild=discord.Object(id=guild_id))
@app_commands.describe(day="Day to change password for in DD-mmm-YYYY (e.g. 01-Jan-1970)")
@app_commands.describe(password="the password to set")
async def set_password(interaction, day: str, password: str):
    date_object: date = datetime.strptime(day, DAY_FORMAT).date()
    error: str = db.set_password(date_object, password)
    await send_ephemeral_response(interaction.response, error,
                                  f"Successfully changed password for {day} to {password}.")


@tree.command(name="set-all-required", description="Set all tasks required for a day",
              guild=discord.Object(id=guild_id))
@app_commands.describe(day="Day to change requirement for in DD-mmm-YYYY (e.g. 01-Jan-1970)")
@app_commands.describe(all_required="true if all are required")
async def set_all_required(interaction, day: str, all_required: bool):
    date_object: date = datetime.strptime(day, DAY_FORMAT).date()
    error = db.change_all_required(date_object, all_required)
    await send_ephemeral_response(interaction.response, error,
                                  f"Successfully changed all required for {day} to {bool}.")


@tree.command(name="admin-day-view", description="Admin view for a day", guild=discord.Object(id=guild_id))
@app_commands.describe(day="Day to query in DD-mmm-YYYY (e.g. 01-Jan-1970)")
async def admin_day_view(interaction, day: str = None):
    if not day:
        day: date = datetime.now(timezone.utc).date()
    else:
        day: date = datetime.strptime(day, DAY_FORMAT).date()
    error, required, password, table = db.admin_day_view(day)
    if error is None:
        embed = discord.Embed(title=f"__**{day}**__", color=0x03f8fc)
        embed.add_field(name=f'**All Required**', value=required, inline=False)
        for task in table:
            content = f"Description: {task[1]}\nRequired: {task[2]}\nRegex: `{task[3]}`"
            embed.add_field(name=f'**Task {task[0]}**', value=content, inline=False)
        embed.add_field(name=f'**Password**', value=password, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await send_ephemeral_response(interaction.response, error, "")


@tree.command(name="register-drop", description="Register a drop manually", guild=discord.Object(id=guild_id))
@app_commands.describe(rsn="Name of the player who got the drop")
@app_commands.describe(message="Drop message")
@app_commands.describe(timestamp="Timestamp for drop in DD-mmm-YYYY HH-MM (e.g. 01-Jan-1970 00:00)")
async def register_drop(interaction, rsn: str, message: str, timestamp: str):
    error, notification = db.add_drop(rsn, message, datetime.strptime(timestamp, DATETIME_FORMAT))
    if notification:
        embed = discord.Embed(color=0x03f8fc)
        embed.add_field(name=notification.header, value=notification.body, inline=False)
        embed.set_thumbnail(
            url=f"https://secure.runescape.com/m=avatar-rs/{notification.rsn.replace(' ', "_")}/chat.png")
        await interaction.response.send_message(embed=embed)
    else:
        await send_ephemeral_response(interaction.response, error, "successfully registered drop")


@tree.command(name="delete-drop", description="Delete a drop", guild=discord.Object(id=guild_id))
@app_commands.describe(identifier="identifier of drop to delete")
async def register_drop(interaction, identifier: str):
    error = db.delete_drop(identifier)
    await send_ephemeral_response(interaction.response, error, "successfully deleted drop")


@tree.command(name="check-progress", description="Check progress on a day", guild=discord.Object(id=guild_id))
@app_commands.describe(day="Day to query in DD-mmm-YYYY (e.g. 01-Jan-1970) - defaults to the current day")
async def check_progress(interaction, day: str = None):
    await interaction.response.defer()
    today: date = datetime.now(timezone.utc).date()
    if not day:
        day: date = today
    else:
        try:
            day: date = datetime.strptime(day, DAY_FORMAT).date()
        except:
            await interaction.followup.send("Invalid day format", ephemeral=True)
            return
    if day > today:
        await interaction.followup.send("You cannot check progress on future days", ephemeral=True)
        return
    progress: Progress = Progress()
    error = db.check_day(day, progress)
    if error:
        await interaction.followup.send(error, ephemeral=True)
    else:
        embed = discord.Embed(title=f"__**Current progress for {day}:**__", color=0x03f8fc)
        for team_name, score in progress.scores.items():
            check: str = '✅️' if score.all_completed else '❌'
            embed.add_field(name=f'**{team_name} - {check} **', value="\n".join(score.lines), inline=False)
        try:
            await interaction.followup.send(embed=embed)
        except HTTPException:
            raw = f"Current progress for {day}:\n"
            for team_name, score in progress.scores.items():
                check: str = '✅️' if score.all_completed else '❌'
                raw += f'{team_name} - {check}\n'
                raw += "\n".join(score.lines)
                raw += "\n\n"
            raw = raw[:-2]
            buffer = StringIO(raw.replace("*", ""))
            f = discord.File(buffer, filename="progress.txt")
            await interaction.followup.send(file=f)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await tree.sync(guild=discord.Object(id=guild_id))
    send_update.start()


bot.run(os.environ["DISCORD_TOKEN"])
