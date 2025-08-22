import json
from typing import Any


class Square:
    def __init__(
        self, x_min: float, y_min: float, x_max: float, y_max: float, text: str
    ):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.text = text


def square_to_jsonable(square: Square) -> dict[str, Any]:
    return {
        "x_min": square.x_min,
        "y_min": square.y_min,
        "x_max": square.x_max,
        "y_max": square.y_max,
        "text": square.text,
    }


def get_square_from_json(from_json: dict[str, Any]) -> Square:
    return Square(
        x_min=from_json["x_min"],
        x_max=from_json["x_max"],
        y_min=from_json["y_min"],
        y_max=from_json["y_max"],
        text=from_json["text"],
    )


def serialize_board(board: list[Square]) -> str:
    return json.dumps([square_to_jsonable(square) for square in board])


def deserialize_board(serialized: str) -> list[Square]:
    from_json: list[dict[str, Any]] = json.loads(serialized)
    return [get_square_from_json(j) for j in from_json]
