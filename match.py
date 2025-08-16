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

        self.move_to_sec(self.start)
        ret, frame = self.cap.read()
        if not ret:
            raise Exception(f"Failed to read video for ID: {self.id}")
        cv2.imwrite(self.frame_name, frame)
        table = get_best_table_from_image(self.frame_name)

        if table is None:
            raise Exception(f"Failed to find table for ID: {self.id}")

        with open(pickle_name, "wb") as file:
            pickle.dump(table, file)

        return table

    def is_done(self, frame: cv2.typing.MatLike) -> bool:
        colors = get_named_colors(self.table, frame)
        counter = Counter([c for c in colors if c != Color.BLACK])
        # this can happen if there are stream effects like sub notifications
        # that render on top of the table
        if len(counter) > 3:
            return False
        winner_first = counter.most_common()
        high_score = 0
        low_score = 0
        if len(winner_first) > 0:
            high_score = winner_first[0][1]
        if len(winner_first) > 1:
            low_score = winner_first[1][1]
        return (self.p1_score == high_score and self.p2_score == low_score) or (
            self.p1_score == low_score and self.p2_score == high_score
        )

    def find_end(self) -> float | None:
        time = self.start
        while True:
            self.move_to_sec(time)
            has_frame, frame = self.cap.read()
            if not has_frame:
                return None
            cv2.imwrite(self.frame_name, frame)
            if self.is_done(frame):
                return time
            time += 1
