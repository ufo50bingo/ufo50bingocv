import json
import numpy as numpy
from paddleocr import PaddleOCR, TableCellsDetection
from PIL import Image, ImageDraw
from typing import Any


def approx(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


class Box:
    def __init__(
        self,
        coords: list[float],
    ):
        [self.x_min, self.y_min, self.x_max, self.y_max] = coords
        self.taxi_dist = (self.x_max + self.x_min) / 2 + (self.y_max + self.y_min) / 2


class Cell(Box):
    def __init__(
        self,
        coords: list[float],
        pos_tolerance: float,
        texts: list["Text"],
        text_tolerance: float,
    ):
        Box.__init__(self, coords)
        self.x_tolerance = (self.x_max - self.x_min) * pos_tolerance
        self.y_tolerance = (self.y_max - self.y_min) * pos_tolerance
        self.text = self.get_contained_text(texts, text_tolerance)

    def is_right_neighbor(self, other: "Cell") -> bool:
        return (
            # this right matches other left
            approx(self.x_max, other.x_min, self.x_tolerance)
            and
            # other right is approx correct distance from other left
            approx(other.x_min + self.x_max - self.x_min, other.x_max, self.x_tolerance)
            and
            # top and bottom match
            approx(self.y_min, other.y_min, self.y_tolerance)
            and approx(self.y_max, other.y_max, self.y_tolerance)
        )

    def is_bottom_neighbor(self, other: "Cell") -> bool:
        return (
            # this bottom matches other top
            approx(self.y_max, other.y_min, self.y_tolerance)
            and
            # other bottom is approx correct distance from other top
            approx(other.y_min + self.y_max - self.y_min, other.y_max, self.y_tolerance)
            and
            # left and right match
            approx(self.x_min, other.x_min, self.x_tolerance)
            and approx(self.x_max, other.x_max, self.x_tolerance)
        )

    def contains(self, other: Box, tolerance: float) -> bool:
        x_tolerance = (self.x_max - self.x_min) * tolerance
        y_tolerance = (self.y_max - self.y_min) * tolerance
        return (
            self.x_min - x_tolerance < other.x_min
            and self.x_max + x_tolerance > other.x_max
            and self.y_min - y_tolerance < other.y_min
            and self.y_max + y_tolerance > other.y_max
        )

    def get_contained_text(self, texts: list["Text"], tolerance: float) -> str:
        return " ".join([t.text for t in texts if self.contains(t, tolerance)])


class Text(Box):
    def __init__(self, coords: list[float], text: str):
        self.text = text
        Box.__init__(self, coords)


def run_table_model(
    img_path: str,
    output_img_path: str | None = None,
    output_json_path: str | None = None,
) -> dict[str, Any]:
    model = TableCellsDetection(model_name="RT-DETR-L_wired_table_cell_det")
    output = model.predict(img_path, threshold=0.5, batch_size=1)
    res = output[0]
    if output_img_path is not None:
        res.save_to_img(output_img_path)
    if output_json_path is not None:
        res.save_to_json(output_json_path)
    return res


def run_ocr_model(
    img_path: str,
    output_img_path: str | None = None,
    output_json_path: str | None = None,
) -> dict[str, Any]:
    ocr = PaddleOCR(
        # trying to fix test2.png processing
        # text_det_limit_side_len=3840,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    output = ocr.predict(input=img_path)

    res = output[0]
    if output_img_path is not None:
        res.save_to_img(output_img_path)
    if output_json_path is not None:
        res.save_to_json(output_json_path)
    return res


def load_json(json_path: str) -> dict[str, Any]:
    with open(json_path, "r") as file:
        return json.load(file)


def get_sorted_cells(
    data: dict[str, Any], pos_tolerance: float, texts: list[Text], text_tolerance: float
) -> list[Cell] | None:
    cells = [
        Cell(box["coordinate"], pos_tolerance, texts, text_tolerance)
        for box in data["boxes"]
        if box["label"] == "cell"
    ]
    if len(cells) < 25:
        return None
    cells.sort(key=lambda cell: cell.taxi_dist)
    return cells


def find_right_cell(cells: list[Cell], index: int) -> int | None:
    cell = cells[index]
    for i in range(index + 1, len(cells)):
        if cell.is_right_neighbor(cells[i]):
            return i
    return None


def find_bottom_cell(cells: list[Cell], index: int) -> int | None:
    cell = cells[index]
    for i in range(index + 1, len(cells)):
        if cell.is_bottom_neighbor(cells[i]):
            return i
    return None


# test if the cell at the given index can be the top left cell of a 5x5 table
def find_table_from_index(cells: list[Cell], index: int) -> None | list[int]:
    table = [index]
    cur_row_start = index
    prev_cell = index
    # try to add 24 more cells
    for i in range(1, 25):
        # every fifth cell should be trying to add a new row instead of a new co
        if i % 5 == 0:
            new_bottom = find_bottom_cell(cells, cur_row_start)
            if new_bottom is None:
                return None
            cur_row_start = new_bottom
            prev_cell = new_bottom
            table.append(new_bottom)
        else:
            new_right = find_right_cell(cells, prev_cell)
            if new_right is None:
                return None
            prev_cell = new_right
            table.append(new_right)
    return table


def find_table(cells: list[Cell]) -> None | list[Cell]:
    # check if each cell can be the top left corner of a table
    best_table = None
    best_count = None
    for i in range(len(cells)):
        table = find_table_from_index(cells, i)
        if table is not None:
            num_with_text = sum(1 for index in table if cells[index].text != "")
            if num_with_text == 25:
                return [cells[index] for index in table]
            elif best_count is None or num_with_text > best_count:
                best_count = num_with_text
                best_table = table
    if best_table is None:
        return None
    return [cells[index] for index in best_table]


def draw_cells(cells: list[Cell], img_path: str, out_path: str):
    with Image.open(img_path) as im:
        red = (255, 0, 0, 255)
        draw = ImageDraw.Draw(im)
        for cell in cells:
            top_left = (round(cell.x_min), round(cell.y_min))
            top_right = (round(cell.x_max), round(cell.y_min))
            bottom_left = (round(cell.x_min), round(cell.y_max))
            bottom_right = (round(cell.x_max), round(cell.y_max))
            draw.line(top_left + top_right, fill=red, width=16)
            draw.line(top_left + bottom_left, fill=red, width=16)
            draw.line(top_right + bottom_right, fill=red, width=16)
            draw.line(bottom_left + bottom_right, fill=red, width=16)
        im.save(out_path, "PNG")


def get_texts(data: dict[str, Any]) -> list[Text]:
    texts = data["rec_texts"]
    boxes = data["rec_boxes"]

    if len(texts) != len(boxes):
        raise Exception("Text and box lengths are different!")

    texts = [Text(boxes[i], texts[i]) for i in range(0, len(texts))]
    texts.sort(key=lambda t: t.taxi_dist)
    return texts


def get_best_table_from_image(img_path: str) -> list[Cell] | None:
    ocr_data = run_ocr_model(img_path)
    texts = get_texts(ocr_data)
    cell_data = run_table_model(img_path, output_img_path="tempimg.png")
    cells = get_sorted_cells(cell_data, 0.2, texts, 0.05)
    if cells is None:
        return None
    return find_table(cells)


# img_path = "videotest.jpg"
# table = get_best_table_from_image(img_path)
# if table is not None:
#     draw_cells(table, img_path, "videotest_out.jpg")
#     for i in range(0, len(table)):
#         print(table[i].text)
#         if i % 5 == 4:
#             print("----------------------------")

# base = "videotest"
# img_path = "./{}.jpg".format(base)
# dir = "./{}/".format(base)

# cell_data = run_table_model(img_path, dir, "{}cell_json.json".format(dir))
# # cell_data = load_json("./tableoutput/tableres.json")
# cells = get_sorted_cells(cell_data, 0.2)
# table = find_table(cells)

# if table is None:
#     raise Exception("could not find table!")

# print(table[4].x_min, table[4].y_min, table[4].x_max, table[4].y_max)

# ocr_data = load_json("./output/test_res.json")
# ocr_data = run_ocr_model(img_path, dir, "{}ocr_json.json".format(dir))
# texts = get_texts(ocr_data)
# print([cell.get_contained_text(texts, 0.05) for cell in table])
