import requests
from models import Task, Player, Drop, Team, LastEntry

type EventLogEntry = dict[str, str]

last_entries = {}


# https://secure.runescape.com/m=avatar-rs/Sportoftran/chat.png


def get_event_log(rsn: str) -> list[EventLogEntry]:
    response = requests.get(f'https://apps.runescape.com/runemetrics/profile/profile?user={rsn}&activities=20',
                            headers={'content-type': 'application/json'})
    return response.json()["activities"]


def extract_relevant_activities(player: Player, last_entry: LastEntry) -> list[Drop]:
    drops: list[Drop] = []
    event_log = get_event_log(player.rsn)
    for activity in event_log:
        if last_entry.date and last_entry.date == activity["date"]:
            break
        elif "I found a" in activity["text"]:
            drops.append(
                Drop(player_id=player.player_id, player=player, message=activity["text"], date=activity["date"]))
    last_entry.date = event_log[0]["date"]
    return drops
