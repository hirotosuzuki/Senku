import re


class SQLParser:
    def parse(self, query: str):
        q = query.strip()
        up = q.upper()

        if up.startswith("CREATE TABLE"):
            m = re.match(r"CREATE TABLE (\w+) \((.+)\)", up)
            if not m:
                raise ValueError("Invalid CREATE TABLE syntax")
            name = m.group(1)
            cols = [c.strip() for c in m.group(2).split(",")]
            return {"type": "create_table", "table": name, "columns": cols}

        if up.startswith("INSERT INTO"):
            m = re.match(r"INSERT INTO (\w+) VALUES \((.+)\)", up)
            if not m:
                raise ValueError("Invalid INSERT INTO syntax")
            name = m.group(1)
            raw = m.group(2)
            values = [v.strip().strip("'") for v in raw.split(",")]
            return {"type": "insert", "table": name, "values": values}

        if up.startswith("SELECT"):
            m = re.match(r"SELECT \* FROM (\w+)", up)
            if not m:
                raise ValueError("Invalid SELECT syntax")
            name = m.group(1)
            return {"type": "select", "table": name}

        raise ValueError(f"Unsupported query: {query}")

