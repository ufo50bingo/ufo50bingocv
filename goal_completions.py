import csv
import pickle
import os
from match import GoalCompletion
from parse_csv import get_all_matches

matches = get_all_matches()
all_goal_completions: list[list[str]] = []
for match in matches:
    changelog_name = os.path.join(match.dir, "changelog.pickle")
    if not os.path.isfile(changelog_name):
        print(f"No changelog found for ID {match.id}")
        continue
    with open(os.path.join(match.dir, "changelog.pickle"), "rb") as f:
        changelog = pickle.load(f)
    with open(os.path.join(match.dir, "table.pickle"), "rb") as f:
        table = pickle.load(f)
    goal_completions = GoalCompletion.get_from_changelog(changelog, table, match)
    all_goal_completions.extend([gc.get_csv_row() for gc in goal_completions])

with open("goal_completions.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(
        f,
    )
    writer.writerow(
        [
            "Week",
            "Tier",
            "Player",
            "Opponent",
            "Goal",
            "Time (mins)",
            "Start URL",
            "End URL",
        ]
    )
    writer.writerows(all_goal_completions)
