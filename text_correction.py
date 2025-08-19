import csv
import difflib
import os
import pickle
from find_table import Cell
from match import GoalCompletion
import json

from match import Match
from video import Color


def get_all_goals() -> list[str]:
    with open("all_goals.txt", "r", encoding="utf8") as f:
        return f.read().splitlines()


def get_all_matches() -> list[Match]:
    with open("all_matches.csv", newline="") as file:
        matches = csv.reader(file)
        # skip header
        next(matches)
        return [Match(row) for row in matches]


def strip_text(input: str) -> str:
    return "".join(x.lower() for x in input if x.isalpha() or x.isdigit())


if os.path.isfile("corrections.json"):
    with open("corrections.json", "r") as f:
        corrections: dict[str, str] = json.load(f)
else:
    corrections: dict[str, str] = {}

goals_list = get_all_goals()
stripped_goals = [strip_text(goal) for goal in goals_list]
stripped_goal_to_goal = {strip_text(goal): goal for goal in goals_list}

matches = get_all_matches()

for match in matches:
    changelog_path = os.path.join(match.dir, "changelog.pickle")
    if not os.path.isfile(changelog_path):
        continue
    with open(changelog_path, "rb") as f:
        changelog: list[tuple[float, int, Color]] = pickle.load(f)
    with open(os.path.join(match.dir, "table.pickle"), "rb") as f:
        table: list[Cell] = pickle.load(f)
    final_board = GoalCompletion.get_final_board_from_changelog(changelog)
    has_change = False
    for i in range(0, 25):
        if final_board[i] != Color.BLACK:
            text = table[i].text
            stripped = strip_text(text)
            if stripped in stripped_goal_to_goal:
                continue
            if text in corrections:
                continue
            print(f"For frame {os.path.join(match.dir, "frame.png")}")
            best_matches = difflib.get_close_matches(stripped, stripped_goals, 3, 0.2)
            print("   " + text)
            for i in range(len(best_matches)):
                print(f"{i+1}. {stripped_goal_to_goal[best_matches[i]]}")
            best = input("Which is best? ")
            if best != "1" and best != "2" and best != "3":
                print("Skipping...")
                continue
            has_change = True
            best_index = int(best) - 1
            corrections[text] = stripped_goal_to_goal[best_matches[best_index]]
    if has_change:
        print("Updating corrections.json...")
        with open("corrections.json", "w") as f:
            f.write(json.dumps(corrections, indent=2))
