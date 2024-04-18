import re
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import create_engine, select, Select
from sqlalchemy.orm import sessionmaker
from models import Team, Player, Drop, Task, Day, Base, LastEntry
import runemetrics


def periodic_update() -> list[str]:
    with Session.begin() as session:
        notifiable_drops: list[str] = []
        current_day: str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        current_regex: str = get_regex(session, current_day)
        players: Sequence[Player] = session.execute(select(Player)).scalars().all()
        for player in players:
            process_player(session, current_regex, notifiable_drops, player)
        session.commit()
        return notifiable_drops


def process_player(session, current_regex: str, notifiable_drops: list[str], player: Player):
    print(f"Processing {player.rsn}")
    query: Select = select(LastEntry).where(LastEntry.player_id == player.player_id)
    last_entry: LastEntry = session.execute(query).scalars().one_or_none()
    if not last_entry:
        last_entry: LastEntry = LastEntry(player_id=player.player_id, date="")
        session.add(last_entry)
    drops: list[Drop] = runemetrics.extract_relevant_activities(player, last_entry)
    for drop in drops:
        if re.match(current_regex, drop.message):
            notifiable_drops.append(f"{drop.player.rsn} {drop.message[2:]}")
        print(f"registering drop {drop.message} for {drop.player.rsn}")
        session.add(drop)
    print("Done")


def get_regex(session, day: str) -> str:
    tasks: Sequence[Task] = session.execute(select(Task).join(Day).where(Day.date == day)).scalars().all()
    task_regexes: list[str] = [task.regex_search for task in tasks]
    regex: str = "(" + ")|(".join(task_regexes) + ")"
    return regex


def add_team(team_name):
    with Session.begin() as session:
        team = session.query(Team).filter(Team.name == team_name).one_or_none()
        if team:
            return f"Team name {team_name} is already in use"
        new_team = Team(name=team_name)
        session.add(new_team)


def rename_team(old_name, new_name):
    with Session.begin() as session:
        team_to_rename = session.query(Team).filter(Team.name == old_name).one_or_none()
        if not team_to_rename:
            return f"Could not rename {old_name}, this team does not exist"
        if session.query(Team).filter(Team.name == new_name).one_or_none():
            return f"Team name {new_name} is already in use"
        team_to_rename.name = new_name


def add_player(rsn, team_name):
    with Session.begin() as session:
        team = session.query(Team).filter(Team.name == team_name).one_or_none()
        if not team:
            return f"Could not create {rsn}, team {team_name} was not found"
        player = Player(rsn=rsn, team_id=team.team_id)
        session.add(player)


def change_rsn(old_rsn, new_rsn):
    with Session.begin() as session:
        old_player = session.query(Player).filter(Player.rsn == old_rsn).one_or_none()
        if not old_player:
            return f"Could not update rsn for {old_rsn}, this player does not exist"
        if session.query(Player).filter(Player.rsn == new_rsn).one_or_none():
            return f"RSN {new_rsn} is already in use"
        old_player.rsn = new_rsn


def list_teams():
    with Session.begin() as session:
        teams = {}
        for team in session.query(Team).all():
            players = ""
            for player in session.query(Player).join(Team).filter(Team.name == team.name).all():
                players += f"{player.rsn}\n"
            teams[team.name] = players[0:-1]
        return teams


def add_task(task_day: str, description: str, regex_search: str, number_required: int):
    with Session.begin() as session:
        day = session.query(Day).filter(Day.date == task_day).one_or_none()
        if not day:
            day = Day(date=task_day)
            session.add(day)
        new_task = Task(description=description, regex_search=regex_search, number_required=number_required, day=day.date)
        session.add(new_task)


engine = create_engine("sqlite:///database/database.sqlite")
Base.metadata.create_all(bind=engine)
Session = sessionmaker(engine)
