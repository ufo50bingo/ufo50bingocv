import os
import time
from match import Match
import csv


def get_all_matches() -> list[Match]:
    with open("all_matches.csv", newline="") as file:
        matches = csv.reader(file)
        # skip header
        next(matches)
        return [Match(row) for row in matches]


all_matches = get_all_matches()
for i in range(len(all_matches)):
    match = all_matches[i]
    if os.path.isfile(os.path.join(match.dir, "changelog.pickle")):
        continue
    print(f"Starting match {match.id} ({i+1} of {len(all_matches)})")
    start_time = time.time()
    with_video = match.get_match_with_video()
    _ = with_video.get_changelog()

    # delete video
    with_video.cap.release()
    os.remove(with_video.video_filename)

    elapsed_time = time.time() - start_time
    print(
        f"Finished {match.id} ({i+1} of {len(all_matches)}) in {elapsed_time / 60} mins"
    )
