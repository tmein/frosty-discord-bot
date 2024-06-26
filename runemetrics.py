import requests
import datetime
import pytz
from constants import DATETIME_FORMAT
from models import Task, Player, Drop, Team, LastEntry

type EventLogEntry = dict[str, str]


# https://secure.runescape.com/m=avatar-rs/Sportoftran/chat.png

def get_event_log(rsn: str) -> list[EventLogEntry]:
    response = requests.get(f'https://apps.runescape.com/runemetrics/profile/profile?user={rsn}&activities=20',
                            headers={'content-type': 'application/json'})
    activities = response.json().get("activities")
    return activities if activities else []


def extract_relevant_activities(player: Player, last_entry: LastEntry) -> list[Drop]:
    drops: list[Drop] = []
    if player.rsn.startswith("*"):
        return []
    else:
        event_log = get_event_log(player.rsn)
        for activity in event_log:
            if last_entry.date and last_entry.date == activity["date"]:
                break
            elif "I found" in activity["text"]:
                utc_date = datetime.datetime.strptime(activity["date"], DATETIME_FORMAT)
                utc_date = pytz.timezone('Europe/London').localize(utc_date).astimezone(pytz.utc)
                drops.append(
                    Drop(player_id=player.player_id, player=player, message=activity["text"], date=utc_date))
        if not event_log or len(event_log) == 0:
            print(f"No activity found for {player.rsn}")
        else:
            last_entry.date = event_log[0]["date"]
        return drops
