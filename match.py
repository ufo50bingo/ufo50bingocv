import os
import pickle
import subprocess
import cv2

from find_table import Cell, get_best_table_from_image
from video import Color, get_named_colors
from collections import Counter


class Match:
    def __init__(
        self,
        row: list[str],
    ):
        self.week = row[0]
        self.tier = row[1]
        self.p1_name = row[2]
        self.p2_name = row[3]
        self.date = row[4]
        self.streamer = row[5]
        self.start = float(row[6])
        self.vod = row[7]
        self.p1_score = int(row[8])
        self.p2_score = int(row[9])
        self.bingo = row[10] == "P1" or row[10] == "P2"
        self.winner_name = row[11]
        self.p1_is_winner = self.winner_name == self.p1_name
        self.id = (self.week + "__" + self.p1_name + "__" + self.p2_name).replace(
            " ", "_"
        )

        self.dir = os.path.join("output", self.id)

        if not os.path.isdir("output"):
            os.mkdir("output")
        if not os.path.isdir(self.dir):
            os.mkdir(self.dir)

    def get_match_with_video(self) -> "MatchWithVideo":
        # we don't know what the video file extension is
        for fname in os.listdir(self.dir):
            if fname.startswith("video"):
                return MatchWithVideo(self, os.path.join(self.dir, fname))

        print(f"Downloading video for {self.id}")
        cmd = [
            "yt-dlp",
            "--quiet",
            "--no-warnings",
            "--get-filename",
            "--no-simulate",
            "--output",
            os.path.join(self.dir, "video.%(ext)s"),
            self.vod,
        ]
        fname = subprocess.getoutput(cmd)
        print(f"Done downloading video for id {self.id}")
        return MatchWithVideo(self, fname)


class MatchWithVideo(Match):
    def __init__(self, match: Match, video_filename: str):
        self.__dict__.update(match.__dict__)
        self.video_filename = video_filename

        self.cap = cv2.VideoCapture(video_filename)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_name = os.path.join(self.dir, "frame.png")

        self.table = self.get_table()

    def move_to_sec(self, sec: float):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.fps * sec)

    def get_table(self) -> list[Cell]:
        pickle_name = os.path.join(self.dir, "table.pickle")
        if os.path.isfile(pickle_name):
            with open(pickle_name, "rb") as file:
                return pickle.load(file)

        print(f"Starting to OCR for id {self.id}")
        time = self.start
        while True:
            self.move_to_sec(time)
            ret, frame = self.cap.read()
            if not ret:
                raise Exception(f"Failed to read video for ID: {self.id}")
            cv2.imwrite(self.frame_name, frame)
            table = get_best_table_from_image(self.frame_name)

            if table is None:
                print(f"Failed to find table at time {time} for id {self.id}")
                time += 5
                continue

            print(f"Done OCRing table for id {self.id}")

            with open(pickle_name, "wb") as file:
                pickle.dump(table, file)

            return table

    def get_colors(self, frame: cv2.typing.MatLike) -> None | list[Color]:
        colors = get_named_colors(self.table, frame)
        counter = Counter([c for c in colors])
        # this can happen if there are stream effects like sub notifications
        # that render on top of the table
        if len(counter) > 3:
            return None
        return colors

    def is_done(self, colors: list[Color]) -> bool:
        counter = Counter([c for c in colors if c != Color.BLACK])
        high_first = counter.most_common()
        high_score = 0
        low_score = 0
        if len(high_first) > 0:
            high_score = high_first[0][1]
        if len(high_first) > 1:
            low_score = high_first[1][1]
        return (self.p1_score <= high_score and self.p2_score <= low_score) or (
            self.p1_score <= low_score and self.p2_score <= high_score
        )

    def get_distinct_states(self) -> tuple[bool, list[tuple[float, list[Color]]]]:
        print(f"Starting to get distinct states for id {self.id}")
        states: list[tuple[float, list[Color]]] = []
        recent_colors = None
        time = self.start
        max_time = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
        while time <= max_time:
            self.move_to_sec(time)
            has_frame, frame = self.cap.read()
            if not has_frame:
                time += 5
                continue
            cv2.imwrite(self.frame_name, frame)
            colors = self.get_colors(frame)
            if colors is None:
                time += 5
                continue
            if recent_colors != colors:
                states.append((time, colors))
                recent_colors = colors
            if self.is_done(colors):
                return (True, states)
            time += 5
        return (False, states)

    def get_changelog(self) -> tuple[bool, list[tuple[float, int, Color]]]:
        is_done, states = self.get_distinct_states()
        changelog: list[tuple[float, int, Color]] = []
        for i in range(1, len(states)):
            old_colors = states[i - 1][1]
            new_colors = states[i][1]
            for j in range(0, 25):
                if old_colors[j] != new_colors[j]:
                    changelog.append((states[i][0], j, new_colors[j]))
        pickle_name = os.path.join(self.dir, "changelog.pickle")
        with open(pickle_name, "wb") as file:
            pickle.dump(changelog, file)
        if not is_done:
            with open(os.path.join(self.dir, "NOT_DONE.txt"), "w") as file:
                file.write("DID NOT FINISH")
        return is_done, changelog
