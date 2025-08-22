import os
import pickle
from changelog import get_changelog_from_pickle
from find_table import Cell
from match import GoalCompletion
from parse_csv import get_all_matches
from color import Color
from text_correction import add_correction, get_best_matches, get_confirmed_text

matches = get_all_matches()
for match in matches:
    changelog_path = os.path.join(match.dir, "changelog.pickle")
    if not os.path.isfile(changelog_path):
        continue
    changelog = get_changelog_from_pickle(changelog_path)
    with open(os.path.join(match.dir, "table.pickle"), "rb") as f:
        table: list[Cell] = pickle.load(f)
    final_board = GoalCompletion.get_final_board_from_changelog(changelog)
    has_change = False
    for i in range(0, 25):
        # if square is black we won't generate a goal completion, so we don't care about the text
        if final_board[i] == Color.BLACK:
            continue
        text = table[i].text
        if get_confirmed_text(text) is not None:
            continue
        print(f"For frame {os.path.join(match.dir, "frame.png")}")
        best_matches = get_best_matches(text, 3)
        print("   " + text)
        for i in range(len(best_matches)):
            print(f"{i+1}. {best_matches[i]}")
        best = input("Which is best? ")
        if best != "1" and best != "2" and best != "3":
            print("Skipping...")
            continue
        best_index = int(best) - 1
        add_correction(text, best_matches[best_index])
