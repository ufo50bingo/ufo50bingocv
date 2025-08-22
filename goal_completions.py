import csv
import os
from changelog import deserialize_changelog_file
from match import GoalCompletion
from parse_csv import get_all_matches
from square import deserialize_board_file

matches = get_all_matches()
all_goal_completions: list[list[str]] = []
for match in matches:
    changelog_name = os.path.join(match.dir, "changelog.txt")
    if not os.path.isfile(changelog_name):
        print(f"No changelog found for ID {match.id}")
        continue
    changelog = deserialize_changelog_file(changelog_name)
    table = deserialize_board_file(os.path.join(match.dir, "table.json"))
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
