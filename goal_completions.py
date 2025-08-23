import csv
import os
from changelog import deserialize_changelog_file
from make_url import get_url_at_time
from match import GoalCompletion
from parse_csv import get_all_matches
from square import deserialize_board_file
from text_correction import get_confirmed_text


def get_all_games() -> list[str]:
    with open("all_games.txt", "r", encoding="utf8") as f:
        all_games = f.read()
    return [game.strip() for game in all_games.splitlines()]


all_games = get_all_games()

lowercase_game_to_game = {game.lower(): game for game in all_games}


def get_game_from_goal(goal: str) -> str:
    parts = goal.split(":")
    if len(parts) < 2:
        return "General"
    start = parts[0].lower()
    if start in lowercase_game_to_game:
        return lowercase_game_to_game[start]
    return "General"

    # week, tier, date, player name, opponent name, goal, time(mins), start_url, end_url


def get_csv_row(gc: GoalCompletion) -> list[str]:
    confirmed_text = get_confirmed_text(gc.text)
    if confirmed_text is None:
        raise Exception(f"Trying to write unconfirmed text to csv: {gc.text}")
    return [
        gc.match.week,
        gc.match.tier,
        gc.match.date,
        gc.player_name,
        gc.opponent_name,
        get_game_from_goal(confirmed_text),
        confirmed_text,
        f"{(gc.end_time - gc.start_time) / 60:.1f}",
        get_url_at_time(gc.match.vod, gc.start_time),
        get_url_at_time(gc.match.vod, gc.end_time),
    ]


matches = get_all_matches()
all_games = get_all_games()
all_goal_completions: list[list[str]] = []
for match in matches:
    changelog_name = os.path.join(match.dir, "changelog.txt")
    if not os.path.isfile(changelog_name):
        print(f"No changelog found for ID {match.id}")
        continue
    changelog = deserialize_changelog_file(changelog_name)
    table = deserialize_board_file(os.path.join(match.dir, "table.json"))
    goal_completions = GoalCompletion.get_from_changelog(changelog, table, match)
    all_goal_completions.extend([get_csv_row(gc) for gc in goal_completions])

with open("goal_completions.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "Week",
            "Tier",
            "Date",
            "Player",
            "Opponent",
            "Game",
            "Goal",
            "Time (mins)",
            "Start URL",
            "End URL",
        ]
    )
    writer.writerows(all_goal_completions)
