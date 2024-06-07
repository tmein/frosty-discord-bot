import re
from datetime import date, datetime, timezone
from typing import Sequence, Type

from sqlalchemy import create_engine, select, Select
from sqlalchemy.orm import sessionmaker
from models import Team, Player, Drop, Task, Day, Base, LastEntry, LastDay

from constants import *
import runemetrics
from structures import Score, Progress, DropNotification


def get_last_day() -> date:
    with Session.begin() as session:
        day_object: LastDay = session.execute(select(LastDay).where(LastDay.id == 0)).scalars().one_or_none()
        return None if day_object is None else day_object.day


def set_new_day(new_day: date):
    with Session.begin() as session:
        last_day: LastDay = session.execute(select(LastDay).where(LastDay.id == 0)).scalars().one_or_none()
        if last_day:
            last_day.day = new_day
        else:
            last_day = LastDay(id=0, day=new_day)
            session.add(last_day)
        session.commit()


def periodic_update(current_day: date) -> list[DropNotification]:
    with Session.begin() as session:
        notifiable_drops: list[DropNotification] = []
        players: Sequence[Player] = session.execute(select(Player)).scalars().all()
        for player in players:
            process_player(session, current_day, notifiable_drops, player)
        session.commit()
        return notifiable_drops


def process_player(session, current_day: date, notifiable_drops: list[DropNotification], player: Player):
    query: Select = select(LastEntry).where(LastEntry.player_id == player.player_id)
    last_entry: LastEntry = session.execute(query).scalars().one_or_none()
    if not last_entry:
        last_entry: LastEntry = LastEntry(player_id=player.player_id, date="")
        session.add(last_entry)
    drops: list[Drop] = runemetrics.extract_relevant_activities(player, last_entry)
    for drop in drops:
        session.add(drop)
        day = get_day(session, current_day)
        if day:
            for task in day.tasks:
                if re.search(task.regex_search, drop.message):
                    completed = len(
                        get_drops_for_team_day(session, drop.player.team, current_day, task.regex_search))
                    notifiable_drops.append(DropNotification(drop.player.rsn,
                                                             f"{drop.player.rsn} {drop.message[2:]} for {drop.player.team.name}",
                                                             f"{task.description}: {completed}/{task.number_required}"))


def get_drops_for_team_day(session, team: Team, day: date, regex_search: str):
    return session.query(Drop).join(Player).join(Team).filter(
        Drop.date.startswith(day)).filter(
        Team.team_id == team.team_id).filter(
        Drop.message.regexp_match(regex_search)).all()


def get_day(session, day: date) -> Day:
    return session.execute(select(Day).where(Day.date == day)).scalars().one_or_none()


def get_regex(session, day: date) -> str:
    tasks: Sequence[Task] = session.execute(select(Task).join(Day).where(Day.date == day)).scalars().all()
    task_regexes: list[str] = [task.regex_search for task in tasks]
    regex: str = "(" + ")|(".join(task_regexes) + ")"
    return regex


def update_lives(team: str, all_completed: bool) -> int:
    with Session.begin() as session:
        team: Team = session.execute(select(Team).where(Team.name == team)).scalars().one_or_none()
        lives: int = team.lives
        if not all_completed:
            team.lives -= 1
            lives = lives
            session.commit()
        return lives


def get_day_task_description(day: date) -> (str, str):
    with Session.begin() as session:
        day_object: Day = session.execute(select(Day).where(Day.date == day)).scalars().one_or_none()
        if not day_object:
            return f"{day} was not found", None
        joiner: str = " and " if day_object.all_required else " or "
        tasks_description: str = joiner.join([task.description for task in day_object.tasks])
        password: str = "" if day_object.password is None else "\n\nToday's password: " + day_object.password
        return None, tasks_description + password


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
            teams[team.name] = players[0:-1] + f"\n{team.lives * '❤️'}"
        return teams


def add_task(task_day: date, description: str, regex_search: str, number_required: int):
    with Session.begin() as session:
        day = session.query(Day).filter(Day.date == task_day).one_or_none()
        if not day:
            day = Day(date=task_day)
            session.add(day)
        new_task = Task(description=description, regex_search=regex_search, number_required=number_required,
                        day=day.date)
        session.add(new_task)


def edit_task(identifier: int, description: str, regex_search: str, number_required: int):
    with Session.begin() as session:
        task = session.query(Task).filter(Task.task_id == identifier).one_or_none()
        if not task:
            return f"Could not edit task {identifier}, this task does not exist"
        task.description = description
        task.regex_search = regex_search
        task.number_required = number_required
        session.commit()


def remove_task(identifier: int):
    with Session.begin() as session:
        task = session.query(Task).filter(Task.task_id == identifier).one_or_none()
        if task:
            session.delete(task)


def change_all_required(day: date, all_required: bool):
    with Session.begin() as session:
        day_object: Type[Day] = session.query(Day).filter(Day.date == day).one_or_none()
        if not day_object:
            return f"Day {day.strftime(DAY_FORMAT)} was not found"
        day_object.all_required = all_required


def set_password(day: date, password: str):
    with Session.begin() as session:
        day_object: Type[Day] = session.query(Day).filter(Day.date == day).one_or_none()
        if not day_object:
            return f"Day {day.strftime(DAY_FORMAT)} was not found"
        day_object.password = password


def add_drop(rsn: str, message: str, timestamp: datetime) -> (str, DropNotification):
    with Session.begin() as session:
        player = session.query(Player).filter(Player.rsn == rsn).one_or_none()
        if not player:
            return f"Could not add drop, {rsn} does not exist in database", None
        else:
            drop = Drop(player_id=player.player_id, player=player, message=message, date=timestamp)
            day = get_day(session, timestamp.date())
            if day:
                for task in day.tasks:
                    if re.search(task.regex_search, drop.message):
                        completed = len(
                            get_drops_for_team_day(session, drop.player.team, timestamp.date(), task.regex_search))
                        notification: DropNotification = (DropNotification(drop.player.rsn,
                                                                           f"{drop.player.rsn} {drop.message[2:]} for {drop.player.team.name}",
                                                                           f"{task.description}: {completed}/{task.number_required}"))
                if notification is None:
                    error = f"Drop was added successfully, but it did not match any task"
            else:
                error = f"Drop was added successfully, but it did not match a day with tasks"
            session.add(drop)
            return error,


def delete_drop(identifier: str):
    with Session.begin() as session:
        drop = session.query(Drop).filter(Drop.drop_id == identifier).one_or_none()
        if not drop:
            return f"Could not delete drop, {identifier} does not exist in database"
        else:
            session.delete(drop)


def admin_day_view(day: date):
    with Session.begin() as session:
        day_object = session.query(Day).filter(Day.date == day).one_or_none()
        if not day_object:
            return f"Day {day.strftime(DAY_FORMAT)} was not found", None, None
        lines: list[list] = []
        for task in day_object.tasks:
            lines.append([f"{task.task_id}", f"{task.description}", f"{task.number_required}", f"{task.regex_search}"])
        return None, f"All required: {bool(day_object.all_required)}", lines


def check_day(day: date, progress: Progress):
    with Session.begin() as session:
        day_object: Type[Day] = session.query(Day).filter(Day.date == day).one_or_none()
        if not day_object:
            return f"Day {day.strftime(DAY_FORMAT)} was not found"
        progress.set_all_required(day_object.all_required)
        for team in session.query(Team).all():
            completions: list[bool] = []
            score: Score = Score()
            for task in day_object.tasks:
                drops: list[Type[Drop]] = get_drops_for_team_day(session, team, day, task.regex_search)
                drops_number: int = len(drops)
                completed: bool = drops_number >= task.number_required
                check: str = '✅️' if completed else '❌'
                score.add_line(f'{task.description} - {drops_number}/{task.number_required} - {check}')
                for drop in drops:
                    score.add_line(f'- *{drop.player.rsn}{drop.message[1:]}*')
                completions.append(completed)
            all_complete = all(completions) if day_object.all_required else any(completions)
            score.set_all_completed(all_complete)
            progress.add_score(team.name, score)


engine = create_engine("sqlite:///database/database.sqlite")
Base.metadata.create_all(bind=engine)
Session = sessionmaker(engine)
