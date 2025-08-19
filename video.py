import cv2
from enum import StrEnum

from find_table import Cell, get_best_table_from_image


class Color(StrEnum):
    BLACK = "black"
    ORANGE = "orange"
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    NAVY = "navy"
    TEAL = "teal"
    BROWN = "brown"
    PINK = "pink"
    YELLOW = "yellow"


def get_reference_colors() -> dict[Color, list[cv2.typing.Scalar]]:
    files = {
        Color.BLACK: ["./colors/black.png", "./colors/black_highlight.png"],
        Color.ORANGE: ["./colors/orange.png", "./colors/orange_highlight.png"],
        Color.RED: ["./colors/red.png", "./colors/red_highlight.png"],
        Color.BLUE: ["./colors/blue.png", "./colors/blue_highlight.png"],
        Color.GREEN: ["./colors/green.png", "./colors/green_highlight.png"],
        Color.PURPLE: ["./colors/purple.png", "./colors/purple_highlight.png"],
        Color.NAVY: ["./colors/navy.png", "./colors/navy_highlight.png"],
        Color.TEAL: ["./colors/teal.png", "./colors/teal_highlight.png"],
        Color.BROWN: ["./colors/brown.png", "./colors/brown_highlight.png"],
        Color.PINK: ["./colors/pink.png", "./colors/pink_highlight.png"],
        Color.YELLOW: ["./colors/yellow.png", "./colors/yellow_highlight.png"],
    }
    return {
        name: [cv2.mean(cv2.imread(img)) for img in imgs]
        for name, imgs in files.items()
    }


reference_colors = get_reference_colors()


def get_closest_color_name(
    all_colors: dict[Color, list[cv2.typing.Scalar]], color: cv2.typing.Scalar
) -> Color:
    best_dist = None
    best_name = Color.BLACK

    for name, bgrs in all_colors.items():
        for bgr in bgrs:
            dist = (
                (color[0] - bgr[0]) ** 2
                + (color[1] - bgr[1]) ** 2
                + (color[2] - bgr[2]) ** 2
            )
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_name = name

    return best_name


def find_table_from_video(cap: cv2.VideoCapture) -> list[Cell] | None:
    fps = cap.get(cv2.CAP_PROP_FPS)
    ten_mins = fps * 60 * 10
    cur_frame = ten_mins
    while cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, cur_frame)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite("temp_frame.jpg", frame)
            table = get_best_table_from_image("temp_frame.jpg")
            if table is not None:
                return table
            cur_frame += ten_mins
        else:
            cap.release()
            break
    return None


# get a 1/4 size rectangle with the same center as Cell
def get_center_rect(cell: Cell, frame: cv2.typing.MatLike) -> cv2.typing.MatLike:
    x_delta = (cell.x_max - cell.x_min) / 8
    y_delta = (cell.y_max - cell.y_min) / 8

    x_min = round(cell.x_min + x_delta)
    x_max = round(cell.x_max - x_delta)
    y_min = round(cell.y_min + y_delta)
    y_max = round(cell.y_max - y_delta)

    return frame[
        y_min:y_max,
        x_min:x_max,
    ]


# color is bgr instead of rgb
def get_raw_colors(
    table: list[Cell], frame: cv2.typing.MatLike
) -> list[cv2.typing.Scalar]:
    return [
        cv2.mean(
            # the detected cell bounday might include some extra pixels from
            # the border, so instead of getting the mean color across the
            # whole cell, we shrink to a cell 1/4 the size
            get_center_rect(cell, frame)
        )
        for cell in table
    ]


def get_named_colors(
    table: list[Cell], frame: cv2.typing.MatLike, color_restrictions: None | set[Color]
) -> list[Color]:
    raw_colors = get_raw_colors(table, frame)
    valid_colors = (
        reference_colors
        if color_restrictions is None
        else {
            color: avgs
            for color, avgs in reference_colors.items()
            if color in color_restrictions
        }
    )
    return [get_closest_color_name(valid_colors, rc) for rc in raw_colors]


# SHOULDN'T NEED THIS!! yt-dlp handles twitch also
# twitch
# url = "https://www.twitch.tv/videos/2413007870"
# title = "test_download.mp4"
# cmd = ["twitch-dl", "download", url, "-q", "source", "--output", title]

# youtube
# url = "https://www.youtube.com/watch?v=YuiX19wZRcg"
# cmd = ["yt-dlp", "--quiet", "--no-warnings", "--get-filename", "--no-simulate", url]
# video_filename = subprocess.getoutput(cmd)
# video_filename = "[UFO 50] BINGO LEAGUE WEEK 8 ! Frank VS Pizza ! OCTAVIO GOT SNIPED... [YuiX19wZRcg].mkv"

# cap = cv2.VideoCapture(video_filename)
# table = find_table_from_video(cap)

# file = open("table.pickle", "wb")
# pickle.dump(table, file)
# file.close()

# file = open("table.pickle", "rb")
# table = pickle.load(file)
# file.close()


# if table is None:
#     print("Could not find table!")
# else:
#     for i in range(0, len(table)):
#         print(table[i].text)
#         if i % 5 == 4:
#             print("----------------------------")
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     cap.set(cv2.CAP_PROP_POS_FRAMES, fps * 60 * 30)
#     ret, frame = cap.read()
#     raw_colors = get_colors(table, frame)
#     for i in range(0, len(raw_colors)):
#         # print(raw_colors[i])
#         print(get_closest_color_name(reference_colors, raw_colors[i]))
#         if i % 5 == 4:
#             print("----------------------------")


# cap = cv2.VideoCapture(title)

# cur_frame = 0
# frame_count = 0

# while cap.isOpened():
#     ret, frame = cap.read()
#     if ret:
#         # frame[ymin:ymax, xmin:xmax]
#         color = cv2.mean(frame[642:730, 1106:1208])
#         print(frame_count, color)
#         # cv2.imwrite("./testframes/frame{:03d}.jpg".format(frame_count), frame)
#         frame_count += 1
#         # 30 fps, 60 seconds per min, 10 min
#         # cur_frame += 30 * 60 * 10
#         cur_frame += 30 * 5
#         cap.set(cv2.CAP_PROP_POS_FRAMES, cur_frame)
#     else:
#         cap.release()
#         break
