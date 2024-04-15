from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey

Base = declarative_base()


class Team(Base):
    __tablename__ = "team"
    team_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    lives = Column(Integer, default=2)


class Player(Base):
    __tablename__ = "player"
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    rsn = Column(String, unique=True)
    team = Column(Integer, ForeignKey("team.team_id"))


class Drop(Base):
    __tablename__ = "drop"
    drop_id = Column(Integer, primary_key=True, autoincrement=True)
    player = Column(Integer, ForeignKey("player.player_id"))
    date = Column(String)
    task = Column(Integer, ForeignKey("task.task_id"))


class Task(Base):
    __tablename__ = "task"
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String)
    regex_search = Column(String)
    number_required = Column(Integer)


class Day(Base):
    __tablename__ = "day"
    date = Column(String, primary_key=True)
    task_1 = Column(Integer, ForeignKey("task.task_id"))
    both_required = Column(Integer)
    task_2 = Column(Integer, ForeignKey("task.task_id"))
