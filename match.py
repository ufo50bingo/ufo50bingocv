import os
import pickle
import subprocess
import cv2

from find_table import Cell, get_best_table_from_image
from video import Color, get_named_colors
from collections import Counter


class GoalCompletion:
    def __init__(
        self,
        match: "Match",
        player_name: str,
        start_time: float,
        end_time: float,
    ):
        self.player_name = player_name
        if match.p1_name != player_name:
            self.opponent_name = match.p1_name
        else:
            self.opponent_name = match.p2_name
        self.start_time = start_time
        self.end_time = end_time

    # (winner color, winner score, has bingo, loser color, loser score)
    @staticmethod
    def get_final_stats(
        changelog: list[tuple[float, int, Color]],
    ) -> tuple[Color, int, bool, Color, int]:
        final_board = [Color.BLACK for _ in range(0, 25)]
        for c in changelog:
            final_board[c[1]] = c[2]
        bingo_lines = [
            # rows
            [0, 1, 2, 3, 4],
            [5, 6, 7, 8, 9],
            [10, 11, 12, 13, 14],
            [15, 16, 17, 18, 19],
            [20, 21, 22, 23, 24],
            # columns
            [0, 5, 10, 15, 20],
            [1, 6, 11, 16, 21],
            [2, 7, 12, 17, 22],
            [3, 8, 13, 18, 23],
            [4, 9, 14, 19, 24],
            # diagonals
            [0, 6, 12, 18, 24],
            [4, 8, 12, 16, 20],
        ]
        bingo_first_square = next(
            (
                line[0]
                for line in bingo_lines
                if final_board[line[0]] != Color.BLACK
                and (
                    final_board[line[0]]
                    == final_board[line[1]]
                    == final_board[line[2]]
                    == final_board[line[3]]
                    == final_board[line[4]]
                )
            ),
            None,
        )
        bingo_winner = None
        if bingo_first_square is not None:
            bingo_winner = final_board[bingo_first_square]
        square_count = Counter(c for c in final_board if c != Color.BLACK)
        most_common = square_count.most_common()
        [color1, color1_score] = most_common[0]
        [color2, color2_score] = most_common[1]

        if bingo_winner is not None:
            if color1 == bingo_winner:
                return (color1, color1_score, True, color2, color2_score)
            else:
                return (color2, color2_score, True, color1, color1_score)
        elif color1_score > color2_score:
            return (color1, color1_score, False, color2, color2_score)
        elif color2_score > color1_score:
            return (color2, color2_score, False, color1, color1_score)
        else:
            losing_color = None
            for c in reversed(changelog):
                if c[2] == Color.BLACK or final_board[c[1]] != c[2]:
                    continue
                losing_color = c[2]
                break
            if losing_color is None:
                raise Exception("No winner found!")
            if losing_color == color1:
                return (color2, color2_score, False, color1, color1_score)
            else:
                return (color1, color1_score, False, color2, color2_score)

    @staticmethod
    def verify_stats(
        stats: tuple[Color, int, bool, Color, int],
        match: "Match",
    ) -> bool:
        _, winner_score, bingo, _, loser_score = stats
        if match.p1_is_winner:
            return (
                match.p1_score == winner_score
                and match.bingo == bingo
                and match.p2_score == loser_score
            )
        else:
            return (
                match.p2_score == winner_score
                and match.bingo == bingo
                and match.p1_score == loser_score
            )

    # @staticmethod
    # def getFromChangelog(
    #     changelog: list[tuple[float, int, Color]],
    # ) -> list["GoalCompletion"]:
    #     index_to_changelog_items: dict[int, list[tuple[float, int, Color]]] = {}
    #     for item in changelog:
    #         index = item[1]
    #         existing = index_to_changelog_items.get(index)
    #         if existing is None:
    #             existing = [item]
    #         else:
    #             existing.append(item)
    #         index_to_changelog_items[index] = existing
    #     # TODO
    #     for goal_number, goal_changelog in index_to_changelog_items.items():
    #         final = goal_changelog[-1]
    #         if final[2] == Color.BLACK:
    #             continue
    #         first_of_same_color = next(gc for gc in goal_changelog if gc[2] == final[2])

    #     return []


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
            if (
                fname.startswith("video")
                and not fname.endswith(".part")
                and not fname.endswith(".ytdl")
            ):
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
        max_time = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
        while time <= max_time:
            self.move_to_sec(time)
            ret, frame = self.cap.read()
            if not ret:
                raise Exception(f"Failed to read video for ID: {self.id}")

            # manual frame in case background is too noisy
            # only relevant for mordaak vs stnfwds
            # frame = cv2.imread("manual_frame.png")
            # frame = cv2.imread("maual_frame_glove_redrobot.png")

            cv2.imwrite(self.frame_name, frame)
            table = get_best_table_from_image(self.frame_name)

            if table is None:
                print(f"Failed to find table at time {time} for id {self.id}")
                time += 120
                continue

            print(f"Done OCRing table for id {self.id}")

            with open(pickle_name, "wb") as file:
                pickle.dump(table, file)

            return table
        raise Exception(f"Failed to find table at ANY time for id {self.id}")

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
        is_exact = (self.p1_score == high_score and self.p2_score == low_score) or (
            self.p1_score == low_score and self.p2_score == high_score
        )
        is_at_least = (self.p1_score <= high_score and self.p2_score <= low_score) or (
            self.p1_score <= low_score and self.p2_score <= high_score
        )
        if is_at_least and not is_exact:
            with open(os.path.join(self.dir, "FINAL_SCORE_WRONG.txt"), "w") as file:
                file.write("FINAL SCORE WRONG")
        return is_at_least

    # return value is
    # (first_done_time, [time, list of colors])
    # we include first_done_time because it's possible we can get to a state
    # where we've already detected a finished state, but the game isn't actually over
    # due to squares being unmarked by refs
    def get_distinct_states(
        self,
    ) -> tuple[None | float, list[tuple[float, list[Color]]]]:
        print(f"Starting to get distinct states for id {self.id}")
        states: list[tuple[float, list[Color]]] = []
        recent_colors = None
        time = self.start
        max_time = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
        first_done_time = None
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
                first_done_time = time
            time += 5
        return (first_done_time, states)

    def get_changelog(self) -> tuple[bool, list[tuple[float, int, Color]]]:
        first_done_time, states = self.get_distinct_states()
        changelog: list[tuple[float, int, Color]] = []
        changelog_after_first_done_time: list[tuple[float, int, Color]] = []
        for i in range(1, len(states)):
            old_colors = states[i - 1][1]
            new_colors = states[i][1]
            for j in range(0, 25):
                if old_colors[j] != new_colors[j]:
                    if first_done_time is not None and states[i][0] > first_done_time:
                        changelog_after_first_done_time.append(
                            (states[i][0], j, new_colors[j])
                        )
                    else:
                        changelog.append((states[i][0], j, new_colors[j]))
        pickle_name = os.path.join(self.dir, "changelog.pickle")
        with open(pickle_name, "wb") as file:
            pickle.dump(changelog, file)
        if len(changelog_after_first_done_time) > 0:
            pickle_name = os.path.join(
                self.dir, "changelog_after_first_done_time.pickle"
            )
            with open(pickle_name, "wb") as file:
                pickle.dump(changelog_after_first_done_time, file)
        if first_done_time is None:
            with open(os.path.join(self.dir, "NOT_DONE.txt"), "w") as file:
                file.write("DID NOT FINISH")
        return first_done_time is not None, changelog
