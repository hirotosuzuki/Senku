import re

class SQLParser:
    def parse(self, query):
        """SQL文を解析して構造化データに変換"""
        query = query.strip().upper()

        if query.startswith("CREATE TABLE"):
            return self._parse_create_table(query)
        elif query.startswith("INSERT INTO"):
            return self._parse_insert(query)
        elif query.startswith("SELECT"):
            return self._parse_select(query)
        else:
            raise ValueError(f"Unsupported query: {query}")

    def _parse_create_table(self, query):
        """CREATE TABLE 文を解析"""
        match = re.match(r"CREATE TABLE (\w+) \((.+)\)", query)
        if not match:
            raise ValueError("Invalid CREATE TABLE syntax")

        table_name = match.group(1)
        columns = [col.strip() for col in match.group(2).split(",")]

        return {"type": "create_table", "table": table_name, "columns": columns}

    def _parse_insert(self, query):
        """INSERT INTO 文を解析"""
        match = re.match(r"INSERT INTO (\w+) VALUES \((.+)\)", query)
        if not match:
            raise ValueError("Invalid INSERT INTO syntax")

        table_name = match.group(1)
        values = [val.strip().strip("'") for val in match.group(2).split(",")]

        return {"type": "insert", "table": table_name, "values": values}

    def _parse_select(self, query):
        """SELECT 文を解析"""
        match = re.match(r"SELECT \* FROM (\w+)", query)
        if not match:
            raise ValueError("Invalid SELECT syntax")

        table_name = match.group(1)
        return {"type": "select", "table": table_name}
