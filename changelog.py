import math
from color import Color


class Change:
    def __init__(
        self,
        time: float,
        square_index: int,
        color: Color,
    ):
        self.time = time
        self.color = color
        self.square_index = square_index


def get_changelog_from_tuples(tuples: list[tuple[float, int, Color]]) -> list[Change]:
    return [
        Change(time=tuple[0], square_index=tuple[1], color=tuple[2]) for tuple in tuples
    ]


def serialize_changelog(changelog: list[Change]) -> str:
    lines: list[str] = []
    for change in changelog:
        hrs = math.trunc(change.time / 3600)
        remaining = change.time - 3600 * hrs
        mins = math.trunc(remaining / 60)
        remaining = remaining - 60 * mins
        secs = round(remaining)
        lines.append(
            f"{hrs}:{mins:02d}:{secs:05.2f} - {change.square_index} - {change.color.value}"
        )
    return "\n".join(lines)


def deserialize_changelog_file(filename: str) -> list[Change]:
    with open(filename, "r") as f:
        changelog = deserialize_changelog(f.read())
    return changelog


def serialize_changelog_to_file(changelog: list[Change], filename: str):
    serialized = serialize_changelog(changelog)
    with open(filename, "w") as f:
        f.write(serialized)


def deserialize_changelog(serialized: str) -> list[Change]:
    lines = serialized.splitlines()
    changes: list[Change] = []
    for line in lines:
        parts = line.split("-")
        if len(parts) != 3:
            raise Exception("Too many parts found when deserializing changelog")
        [time_str, square_index_str, color_value] = parts
        time_parts = time_str.strip().split(":")
        if len(time_parts) != 3:
            raise Exception("Too many time parts found when deserializing changelog")
        time = (
            int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + float(time_parts[2])
        )
        square_index = int(square_index_str.strip())
        color = Color(color_value.strip())
        changes.append(Change(time=time, square_index=square_index, color=color))
    return changes


def get_final_board_from_changelog(
    changelog: list[Change],
) -> list[Color]:
    final_board = [Color.BLACK for _ in range(0, 25)]
    for c in changelog:
        final_board[c.square_index] = c.color
    return final_board
