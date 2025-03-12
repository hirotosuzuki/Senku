from .parser import SQLParser
from .table import Table

class Database:
    def __init__(self):
        self.tables = {}

    def execute(self, query):
        """SQL を実行"""
        parsed_query = SQLParser().parse(query)

        if parsed_query["type"] == "create_table":
            table_name = parsed_query["table"]
            columns = parsed_query["columns"]
            self.tables[table_name] = Table(table_name, columns)
            return f"Table {table_name} created."

        elif parsed_query["type"] == "insert":
            table_name = parsed_query["table"]
            values = parsed_query["values"]
            if table_name in self.tables:
                self.tables[table_name].insert(values)
                return f"Inserted into {table_name}."
            else:
                raise ValueError(f"Table {table_name} does not exist")

        elif parsed_query["type"] == "select":
            table_name = parsed_query["table"]
            if table_name in self.tables:
                return self.tables[table_name].select_all()
            else:
                raise ValueError(f"Table {table_name} does not exist")
