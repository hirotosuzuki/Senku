import os
from .parser import SQLParser
from .table import Table
from .storage import save_table_json, load_table_json


class Database:
    def __init__(self, data_dir: str = "data"):
        self.tables = {}
        self.data_dir = data_dir
        # ch02以降: 起動時に復元
        self._load_existing()

    def _load_existing(self):
        os.makedirs(self.data_dir, exist_ok=True)
        for filename in os.listdir(self.data_dir):
            if not filename.endswith(".json"):
                continue
            name = filename[:-5]
            loaded = load_table_json(self.data_dir, name)
            if not loaded:
                continue
            columns, rows = loaded
            tbl = Table(name, columns)
            for r in rows:
                tbl.insert(r)
            self.tables[name] = tbl

    def execute(self, query: str):
        p = SQLParser().parse(query)
        t = p["type"]

        if t == "create_table":
            name = p["table"]
            cols = p["columns"]
            self.tables[name] = Table(name, cols)
            return f"Table {name} created."

        if t == "insert":
            name = p["table"]
            vals = p["values"]
            if name not in self.tables:
                raise ValueError(f"Table {name} does not exist")
            self.tables[name].insert(vals)
            return f"Inserted into {name}."

        if t == "select":
            name = p["table"]
            if name not in self.tables:
                raise ValueError(f"Table {name} does not exist")
            return self.tables[name].select_all()

        raise ValueError("Unsupported query type")

    def save_all(self):
        for name, tbl in self.tables.items():
            save_table_json(self.data_dir, name, tbl.columns, tbl.rows)

