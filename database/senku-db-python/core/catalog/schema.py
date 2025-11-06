"""
スキーマ定義

テーブルの構造（カラム名、データ型など）を定義します。
SQLのCREATE TABLE文から生成され、カタログに登録されます。
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ColumnDefinition:
    """カラム定義
    
    テーブルの1つのカラムを表現します。
    
    Attributes:
        name: カラム名
        data_type: データ型（"INT", "TEXT", "FLOAT"など）
        nullable: NULL値を許可するか（将来の拡張）
        default_value: デフォルト値（将来の拡張）
    """
    name: str
    data_type: str  # "INT", "TEXT", "FLOAT", etc.
    nullable: bool = True
    default_value: Optional[any] = None
    
    def __post_init__(self):
        """データ型を正規化（大文字に変換）"""
        self.data_type = self.data_type.upper()


class Schema:
    """テーブルスキーマ
    
    テーブルの構造を表現します。
    カラム定義のリストと、主キーやインデックスなどの制約情報を保持します。
    """
    
    def __init__(self, table_name: str, columns: List[ColumnDefinition]):
        """スキーマを初期化
        
        Args:
            table_name: テーブル名
            columns: カラム定義のリスト
        """
        self.table_name = table_name
        self.columns = columns
        self.primary_key: Optional[List[str]] = None  # 将来の拡張
        self.indexes: List[str] = []  # 将来の拡張
    
    def get_column_index(self, column_name: str) -> Optional[int]:
        """カラム名からインデックスを取得
        
        Args:
            column_name: カラム名
            
        Returns:
            カラムのインデックス（存在しない場合はNone）
        """
        for i, col in enumerate(self.columns):
            if col.name == column_name:
                return i
        return None
    
    def get_column_by_name(self, column_name: str) -> Optional[ColumnDefinition]:
        """カラム名からColumnDefinitionを取得
        
        Args:
            column_name: カラム名
            
        Returns:
            ColumnDefinition（存在しない場合はNone）
        """
        for col in self.columns:
            if col.name == column_name:
                return col
        return None
    
    def to_tuple_list(self) -> List[tuple[str, str]]:
        """スキーマを(カラム名, データ型)のタプルリストに変換
        
        ヒープファイルでのシリアライズ/デシリアライズに使用します。
        
        Returns:
            [(column_name, data_type), ...] のリスト
        """
        return [(col.name, col.data_type) for col in self.columns]
    
    def validate_values(self, values: List[any]) -> bool:
        """値のリストがスキーマに適合するか検証
        
        Args:
            values: 値のリスト
            
        Returns:
            適合する場合はTrue
        """
        if len(values) != len(self.columns):
            return False
        
        # 型チェック（簡易版）
        for i, (value, col_def) in enumerate(zip(values, self.columns)):
            if value is None and not col_def.nullable:
                return False
            
            # 型チェック
            if value is not None:
                if col_def.data_type == "INT" and not isinstance(value, int):
                    try:
                        int(value)  # 変換可能かチェック
                    except (ValueError, TypeError):
                        return False
                elif col_def.data_type == "FLOAT" and not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        return False
                # TEXTは任意の値を文字列として扱える
        
        return True

