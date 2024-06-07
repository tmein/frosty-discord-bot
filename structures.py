class Score:

    def __init__(self):
        self.lines: list[str] = []
        self.all_completed: bool = False

    def add_line(self, line: str):
        self.lines.append(line)

    def set_all_completed(self, completed: bool):
        self.all_completed = completed


class Progress:
    def __init__(self):
        self.scores: dict[str, Score] = {}
        self.all_required: bool = True

    def set_all_required(self, required: bool):
        self.all_required = required

    def add_score(self, team: str, score: Score):
        self.scores[team] = score


class DropNotification:
    def __init__(self, rsn: str, header: str, body: str,):
        self.rsn: str = rsn
        self.header: str = header
        self.body: str = body