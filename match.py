import json
import math
import os
import pickle
import subprocess
import cv2

from find_table import Cell, get_best_table_from_image
from make_url import get_url_at_time
from video import Color, get_named_colors
from collections import Counter


class GoalCompletion:
    def __init__(
        self,
        match: "Match",
        player_name: str,
        text: str,
        start_time: float,
        end_time: float,
    ):
        self.player_name = player_name
        self.match = match
        self.text = text
        if match.p1_name != player_name:
            self.opponent_name = match.p1_name
        else:
            self.opponent_name = match.p2_name
        self.start_time = start_time
        self.end_time = end_time

    @staticmethod
    def print_changelog(changelog: list[tuple[float, int, Color]]):
        for change in changelog:
            hrs = math.trunc(change[0] / 3600)
            remaining = change[0] - 3600 * hrs
            mins = math.trunc(remaining / 60)
            remaining = remaining - 60 * mins
            secs = round(remaining)
            print(f"{hrs}:{mins:02d}:{secs:02d} - {change[1]} - {change[2].value}")

    @staticmethod
    def print_distinct_states(distinct_states: list[tuple[float, list[Color]]]):
        for state in distinct_states:
            hrs = math.trunc(state[0] / 3600)
            remaining = state[0] - 3600 * hrs
            mins = math.trunc(remaining / 60)
            remaining = remaining - 60 * mins
            secs = round(remaining)

            print(f"{hrs}:{mins:02d}:{secs:02d}")
            GoalCompletion.print_board_state(state[1])

    @staticmethod
    def print_board_state(
        board: list[Color],
    ):
        for i in range(0, 5):
            row = board[5 * i : 5 * i + 5]
            # 6 is max length. Add 4 extra spaces for gaps
            print("".join([color.value.ljust(10) for color in row]))

    @staticmethod
    def get_final_board_from_changelog(
        changelog: list[tuple[float, int, Color]],
    ) -> list[Color]:
        final_board = [Color.BLACK for _ in range(0, 25)]
        for c in changelog:
            final_board[c[1]] = c[2]
        return final_board

    # (winner color, winner score, has bingo, loser color, loser score)
    @staticmethod
    def get_final_stats(
        changelog: list[tuple[float, int, Color]],
    ) -> None | tuple[Color, int, bool, Color, int]:
        final_board = GoalCompletion.get_final_board_from_changelog(changelog)
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

        if len(most_common) > 2:
            return None
        [color1, color1_score] = most_common[0]

        # at least one match (QTR_stnfwds_Khana) has only one color on the final board
        if len(most_common) == 1:
            color2_score = 0
            remaining_colors = [
                change[2]
                for change in changelog
                if change[2] != Color.BLACK and change[2] != color1
            ]
            if len(remaining_colors) > 0:
                color2 = remaining_colors[0]
            elif color1 != Color.GREEN:
                color2 = Color.GREEN
            else:
                color2 = Color.NAVY
        else:
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
                return None
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

    @staticmethod
    def get_from_changelog(
        changelog: list[tuple[float, int, Color]],
        table: list[Cell],
        match: "Match",
    ) -> list["GoalCompletion"]:
        goal_index_to_changelog_indices: dict[int, list[int]] = {}
        for changelog_index in range(len(changelog)):
            item = changelog[changelog_index]
            goal_index = item[1]
            existing = goal_index_to_changelog_indices.get(goal_index)
            if existing is None:
                existing = [changelog_index]
            else:
                existing.append(changelog_index)
            goal_index_to_changelog_indices[goal_index] = existing
        completions: list[GoalCompletion] = []
        for goal_index, changelog_indices in goal_index_to_changelog_indices.items():
            final_change = changelog[changelog_indices[-1]]
            final_color = final_change[2]
            # if goal ended black, don't track the completion
            if final_color == Color.BLACK:
                continue
            end_time = final_change[0]
            first_change_of_same_color = next(
                c_index
                for c_index in changelog_indices
                if changelog[c_index][2] == final_color
            )
            c_index = first_change_of_same_color - 1
            start_time = match.start
            while c_index >= 0:
                change = changelog[c_index]
                if change[2] == final_color:
                    start_time = change[0]
                    break
                c_index -= 1

            # TODO: Proper player name
            completions.append(
                GoalCompletion(
                    match, "Unknown", table[goal_index].text, start_time, end_time
                )
            )
        return completions

    # week, tier, player name, opponent name, goal, time(mins), start_url, end_url
    def get_csv_row(self) -> tuple[str, str, str, str, str, str, str, str]:
        return (
            self.match.week,
            self.match.tier,
            self.player_name,
            self.opponent_name,
            self.text,
            f"{(self.end_time - self.start_time) / 60:.1f}",
            get_url_at_time(self.match.vod, self.start_time),
            get_url_at_time(self.match.vod, self.end_time),
        )


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
                and fname.count(".") == 1
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

        # Unfortunately the best video quality for this is 360p.
        if self.id == "2__Marshmallow__CodeMeRight1":
            raise Exception(
                "Video quality too poor for OCR. Create table.pickle manually"
            )

        height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        # for some reason yt-dlp will sometimes download a low quality video even
        # when a higher quality video is available. In that case just throw
        # an exception and we'll retry later
        if height < 700:
            self.cap.release()
            os.remove(self.video_filename)
            raise Exception("Video quality too poor for OCR. Try again")
        print(f"Starting to OCR for id {self.id}")
        time = self.start
        max_time = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps

        override_path = os.path.join(self.dir, "ocr_override_frame.png")
        if os.path.isfile(override_path):
            table = get_best_table_from_image(override_path)

            if table is None:
                raise Exception(
                    f"Failed to find table in override frame for id {self.id}"
                )

            print(f"Done OCRing table for id {self.id}")

            with open(pickle_name, "wb") as file:
                pickle.dump(table, file)
            return table

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

    def get_colors(
        self,
        frame: cv2.typing.MatLike,
        color_restrictions: None | set[Color],
        time: float,
    ) -> None | list[Color]:
        colors = get_named_colors(self.table, frame, color_restrictions)
        # Manual correction. Flesh accidentally marked this as Red instead of Purple
        if self.id == "2__boardsofhannahda__Flesh177" and colors[3] == Color.RED:
            colors[3] = Color.PURPLE
        counter = Counter([c for c in colors])
        # this can happen if there are stream effects like sub notifications
        # that render on top of the table
        if len(counter) > 3:
            print(f"Found more than 3 colors at time {time}: {counter}")
            return None
        return colors

    # def is_done(self, colors: list[Color]) -> bool:
    #     counter = Counter([c for c in colors if c != Color.BLACK])
    #     high_first = counter.most_common()
    #     high_score = 0
    #     low_score = 0
    #     if len(high_first) > 0:
    #         high_score = high_first[0][1]
    #     if len(high_first) > 1:
    #         low_score = high_first[1][1]
    #     is_exact = (self.p1_score == high_score and self.p2_score == low_score) or (
    #         self.p1_score == low_score and self.p2_score == high_score
    #     )
    #     is_at_least = (self.p1_score <= high_score and self.p2_score <= low_score) or (
    #         self.p1_score <= low_score and self.p2_score <= high_score
    #     )
    #     if is_at_least and not is_exact:
    #         with open(os.path.join(self.dir, "FINAL_SCORE_WRONG.txt"), "w") as file:
    #             file.write("FINAL SCORE WRONG")
    #     return is_at_least

    # return value is
    # (first_done_time, [time, list of colors])
    # we include first_done_time because it's possible we can get to a state
    # where we've already detected a finished state, but the game isn't actually over
    # due to squares being unmarked by refs
    def get_distinct_states(
        self,
    ) -> list[tuple[float, list[Color]]]:
        print(f"Starting to get distinct states for id {self.id}")
        color_restrictions = None
        color_restrictions_name = os.path.join(self.dir, "color_restrictions.json")
        if os.path.isfile(color_restrictions_name):
            with open(color_restrictions_name, "r") as file:
                color_name_arr: list[str] = json.load(file)
                color_restrictions = {Color(color_str) for color_str in color_name_arr}

        states: list[tuple[float, list[Color]]] = []
        recent_colors = None
        time = self.start
        max_time = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) / self.fps
        frame = None
        while time <= max_time:
            self.move_to_sec(time)
            has_frame, frame = self.cap.read()
            if not has_frame:
                time += 5
                continue
            # cv2.imwrite(self.frame_name, frame)
            colors = self.get_colors(frame, color_restrictions, time)
            if colors is None:
                time += 5
                continue
            # GoalCompletion.print_distinct_states([(time, colors)])
            if recent_colors != colors:
                num_changes = 0
                if recent_colors is not None:
                    num_changes = sum(
                        1 for idx in range(0, 25) if recent_colors[idx] != colors[idx]
                    )
                # trying to handle cases where the screen transitions to something else
                # after the match is over
                if num_changes < 5:
                    states.append((time, colors))
                    recent_colors = colors
            time += 5
        if frame is not None:
            cv2.imwrite(self.frame_name, frame)
        return states

    def get_changelog(self) -> tuple[bool, list[tuple[float, int, Color]]]:
        states = self.get_distinct_states()
        pickle_name = os.path.join(self.dir, "states.pickle")
        with open(pickle_name, "wb") as file:
            pickle.dump(states, file)
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
        final_stats = GoalCompletion.get_final_stats(changelog)
        wrong_end_state = final_stats is None or not GoalCompletion.verify_stats(
            final_stats, self
        )
        if wrong_end_state:
            with open(os.path.join(self.dir, "FINAL_SCORE_WRONG.txt"), "w") as file:
                file.write(f"Actual stats: {final_stats}\n")
                expected_stats = (
                    (self.p1_score, self.bingo, self.p2_score)
                    if self.p1_is_winner
                    else (self.p2_score, self.bingo, self.p1_score)
                )
                file.write(f"Expected stats: {expected_stats}")
        all_colors = {
            change[2].value for change in changelog if change[2] != Color.BLACK
        }
        if len(all_colors) != 2:
            with open(os.path.join(self.dir, "BAD_COLORS.txt"), "w") as file:
                file.write(f"Found colors {all_colors}\n")
        return not wrong_end_state, changelog
