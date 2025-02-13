import json
import os
from typing import Optional


def data_load(filename: str) -> Optional[dict]:
    if not os.path.exists(filename):
        return None

    with open(filename, "r") as f:
        return json.load(f)


def data_save(filename: str, data: dict):
    with open(filename, "w") as f:
        json.dump(data, f)
