import os
from changelog import (
    deserialize_changelog,
    get_changelog_from_pickle,
    serialize_changelog,
)
from parse_csv import get_all_matches

all_matches = get_all_matches()
for i in range(len(all_matches)):
    match = all_matches[i]
    pickle_name = os.path.join(match.dir, "changelog.pickle")
    if not os.path.isfile(pickle_name):
        continue
    changelog = get_changelog_from_pickle(pickle_name)
    serialized = serialize_changelog(changelog)
    deserialized = deserialize_changelog(serialized)
    re_serialized = serialize_changelog(deserialized)

    if serialized != re_serialized:
        raise Exception("Oops!")

    with open(os.path.join(match.dir, "changelog.txt"), "w") as f:
        f.write(serialized)
