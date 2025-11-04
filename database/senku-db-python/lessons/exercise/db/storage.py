import os
import json


def save_table_json(dir_path: str, table_name: str, columns, rows):
    # ch02: JSONでスナップショット保存
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, f"{table_name}.json")
    payload = {"columns": columns, "rows": rows}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def load_table_json(dir_path: str, table_name: str):
    path = os.path.join(dir_path, f"{table_name}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("columns", []), payload.get("rows", [])

