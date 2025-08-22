import difflib
import os
import json


def get_all_goals() -> list[str]:
    with open("all_goals.txt", "r", encoding="utf8") as f:
        return f.read().splitlines()


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


def add_correction(bad_text: str, good_text: str):
    corrections[bad_text] = good_text
    with open("corrections.json", "w") as f:
        f.write(json.dumps(corrections, indent=2))


def get_confirmed_text(text: str) -> str | None:
    stripped = strip_text(text)
    if stripped in stripped_goal_to_goal:
        return stripped_goal_to_goal[stripped]
    if text in corrections:
        return corrections[text]
    return None


def get_best_matches(text: str, num_matches: int) -> list[str]:
    best_matches = difflib.get_close_matches(
        strip_text(text), stripped_goals, num_matches, 0.2
    )
    return [stripped_goal_to_goal[stripped] for stripped in best_matches]
