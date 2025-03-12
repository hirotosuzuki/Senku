class Table:
    def __init__(self, name, columns):
        self.name = name
        self.columns = columns
        self.rows = []  # データをメモリ上に保存

    def insert(self, values):
        """データを追加"""
        if len(values) != len(self.columns):
            raise ValueError("Column count does not match value count")
        self.rows.append(values)

    def select_all(self):
        """全データを取得"""
        return self.rows
