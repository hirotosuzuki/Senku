from dataclasses import dataclass
from typing import Optional


@dataclass
class ColumnDefinition:
    name: str # カラム名
    data_type: str # データ型
    nullable: bool = True # NULL値を許可するか
    default_value: Optional[any] = None # デフォルト値

    def __post_init__(self):
        """データ型を正規化（大文字に変換）"""
        self.data_type = self.data_type.upper()


class Schema:
    def __init__(self, table_name: str, columns: list[ColumnDefinition]):
        self.table_name = table_name
        self.columns = columns
        self.primary_key: Optional[list[str]] = None # 主キー
        self.indexes: list[str] = [] # インデックス

    def get_column_index(self, column_name: str) -> Optional[int]:
        """カラム名からインデックスを取得"""
        for i, col in enumerate(self.columns):
            if col.name == column_name:
                return i
        return None