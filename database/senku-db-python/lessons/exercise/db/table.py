class Table:
    def __init__(self, name, columns):
        self.name = name
        self.columns = columns
        self.rows = []

    def insert(self, values):
        # ch01: 列数チェック→挿入
        if len(values) != len(self.columns):
            raise ValueError("Column count does not match value count")
        self.rows.append(values)

    def select_all(self):
        # ch01: 全件返す（WHEREは後続）
        return self.rows

