import os
import pickle
from square import serialize_board, deserialize_board
from find_table import Cell, get_square_from_cell
from parse_csv import get_all_matches

all_matches = get_all_matches()
for i in range(len(all_matches)):
    match = all_matches[i]
    pickle_name = os.path.join(match.dir, "table.pickle")
    if not os.path.isfile(pickle_name):
        continue
    with open(pickle_name, "rb") as file:
        cells: list[Cell] = pickle.load(file)
    squares = [get_square_from_cell(cell) for cell in cells]
    serialized = serialize_board(squares)
    deserialized = deserialize_board(serialized)
    re_serialized = serialize_board(deserialized)

    if serialized != re_serialized:
        raise Exception("Oops!")

    with open(os.path.join(match.dir, "table.json"), "w") as f:
        f.write(serialized)
