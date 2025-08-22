import datetime
import os
import time
import traceback
from parse_csv import get_all_matches


all_matches = get_all_matches()
for i in range(len(all_matches)):
    try:
        match = all_matches[i]
        if os.path.isfile(os.path.join(match.dir, "changelog.pickle")):
            continue
        print(
            f"Starting match {match.id} ({i+1} of {len(all_matches)}) at {datetime.datetime.now().time()}"
        )
        start_time = time.time()
        with_video = match.get_match_with_video()
        final_score_matches, _ = with_video.get_changelog()

        with_video.cap.release()
        # if there's a problem with the final score, don't delete the video
        if final_score_matches:
            os.remove(with_video.video_filename)

        elapsed_time = time.time() - start_time
        print(
            f"Finished {match.id} ({i+1} of {len(all_matches)}) in {elapsed_time / 60} mins"
        )
    except Exception as error:
        print(traceback.format_exc())
