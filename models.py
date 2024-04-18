from typing import List

from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Mapped, DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class Team(Base):
    __tablename__ = "team"
    team_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(unique=True)
    lives: Mapped[int] = mapped_column(default=2)
    #players: Mapped[List["Player"]] = relationship(back_populates="team")


class Player(Base):
    __tablename__ = "player"
    player_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rsn: Mapped[str] = mapped_column(unique=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.team_id"))
    team: Mapped["Team"] = relationship()
    #drops: Mapped[List["Drop"]] = relationship(back_populates="player")


class Drop(Base):
    __tablename__ = "drop"
    drop_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.player_id"))
    player: Mapped["Player"] = relationship()
    message: Mapped[str]
    date: Mapped[str]


class Task(Base):
    __tablename__ = "task"
    task_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    description: Mapped[str]
    regex_search: Mapped[str]
    number_required: Mapped[int]
    day: Mapped[str] = mapped_column(ForeignKey("day.date"))


class Day(Base):
    __tablename__ = "day"
    date: Mapped[str] = mapped_column(primary_key=True)
    all_required: Mapped[int] = mapped_column(default=1)


class LastEntry(Base):
    __tablename__ = "last_entry"
    player_id: Mapped[str] = mapped_column(ForeignKey("player.player_id"), primary_key=True)
    date: Mapped[str]
