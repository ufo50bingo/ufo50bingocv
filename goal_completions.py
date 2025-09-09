import csv
import json
import os
from changelog import deserialize_changelog_file
from color import Color
from make_url import get_url_at_time
from match import GoalCompletion
from parse_csv import get_all_matches
from square import deserialize_board_file
from text_correction import get_confirmed_text
from datetime import datetime
from zoneinfo import ZoneInfo


old_week_to_new_week = {
    "1": "Week 1",
    "2": "Week 2",
    "3": "Week 3",
    "4": "Week 4",
    "5": "Week 5",
    "6": "Week 6",
    "7": "Week 7",
    "8": "Week 8",
    "Bye": "Bye",
    "QTR": "Quarterfinals",
    "SEMI": "Semifinals",
    "3rd Place": "Third Place",
    "FINAL": "Championship",
}


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


def get_unixtime(date: str, time: str) -> int:
    date_str = date + " " + time
    dt_naive = datetime.strptime(date_str, "%m/%d/%Y %I:%M %p")
    dt_aware = dt_naive.replace(tzinfo=ZoneInfo("America/New_York"))
    return int(dt_aware.timestamp())


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
final = []
for match in matches:
    unixtime = get_unixtime(match.date, match.timestr)
    #     {
    #   "reveals": [
    #     {
    #       "time": 1746227589,
    #       "name": "Spooty"
    #     },
    #     {
    #       "time": 1746227589,
    #       "name": "Cosmoing"
    #     }
    #   ],
    #   "changes": [
    #     {
    #       "time": 1746227729,
    #       "name": "Spooty",
    #       "color": "teal",
    #       "index": 12
    #     },
    match_start_time = unixtime + 30

    changelog_name = os.path.join(match.dir, "changelog.txt")
    if not os.path.isfile(changelog_name):
        print(f"No changelog found for ID {match.id}")
        continue
    changelog = deserialize_changelog_file(changelog_name)
    final_stats = GoalCompletion.get_final_stats(changelog, match.id)
    if final_stats is None:
        raise Exception("failed to get final stats")
    winning_color = final_stats[0]
    losing_color = final_stats[3]
    color_to_name = {
        winning_color: match.p1_name if match.p1_is_winner else match.p2_name,
        losing_color: match.p2_name if match.p1_is_winner else match.p1_name,
    }

    wip_board = [Color.BLACK] * 25
    changes_for_json = []

    for c in changelog:
        prev_color = wip_board[c.square_index]
        name = "Unknown"
        if c.color != Color.BLACK:
            name = color_to_name[c.color]
        elif prev_color != Color.BLACK:
            name = color_to_name[prev_color]
        changes_for_json.append(
            {
                "time": int(match_start_time + c.time - match.start),
                "name": name,
                "color": "blank" if c.color == "black" else c.color,
                "index": c.square_index,
            }
        )

    reveals = [
        {
            "time": unixtime,
            "name": match.p1_name,
        },
        {
            "time": unixtime,
            "name": match.p2_name,
        },
    ]

    changelog_for_json = {"reveals": reveals, "changes": changes_for_json}
    table = deserialize_board_file(os.path.join(match.dir, "table.json"))

    final_board_from_changes = GoalCompletion.get_final_board_from_changelog(changelog)

    board_for_json = []
    for idx, t in enumerate(table):
        final_color = final_board_from_changes[idx]
        color_to_use = final_color.value if final_color != Color.BLACK else "blank"

        board_for_json.append(
            {
                "name": get_confirmed_text(t.text),
                "color": color_to_use,
            }
        )

    board_json = json.dumps(board_for_json, separators=(",", ":"))
    changelog_json = json.dumps(changelog_for_json, separators=(",", ":"))

    final.append(
        {
            "board_json": board_json,
            "changelog_json": changelog_json,
            "date_created": unixtime,
            "id": f"S1__{match.id}",
            "name": f"{match.p1_name} vs {match.p2_name}",
            "week": old_week_to_new_week[match.week],
            "tier": match.tier,
            "p1": match.p1_name,
            "p2": match.p2_name,
            "vod_url": match.vod,
            "vod_match_start_seconds": int(match.start),
        }
    )
with open("migration.json", "w") as f:
    f.write(json.dumps(final, indent=2))

# with open("goal_completions.csv", "w", encoding="utf8", newline="") as f:
#     writer = csv.writer(f)
#     writer.writerow(
#         [
#             "Week",
#             "Tier",
#             "Date",
#             "Player",
#             "Opponent",
#             "Game",
#             "Goal",
#             "Time (mins)",
#             "Start URL",
#             "End URL",
#         ]
#     )
#     writer.writerows(all_goal_completions)
