import csv
import pickle
import os
from match import GoalCompletion, Match


# TODO: import from parse_csv
def get_all_matches() -> list[Match]:
    with open("all_matches.csv", newline="") as file:
        matches = csv.reader(file)
        # skip header
        next(matches)
        return [Match(row) for row in matches]


matches = get_all_matches()
match = matches[1]
with open(os.path.join(match.dir, "changelog.pickle"), "rb") as f:
    changelog = pickle.load(f)
with open(os.path.join(match.dir, "table.pickle"), "rb") as f:
    table = pickle.load(f)
goal_completions = GoalCompletion.get_from_changelog(changelog, table, match)
for gc in goal_completions:
    print(gc.get_csv_row())
