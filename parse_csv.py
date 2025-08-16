from match import Match
import csv


def get_all_matches() -> list[Match]:
    with open("all_matches.csv", newline="") as file:
        matches = csv.reader(file)
        # skip header
        next(matches)
        return [Match(row) for row in matches]


test_match = get_all_matches()[134]
test = test_match.get_match_with_video()
print(test.find_end())
