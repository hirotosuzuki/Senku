"""
スキーマ定義

テーブルの構造（カラム名、データ型など）を定義します。
SQLのCREATE TABLE文から生成され、カタログに登録されます。
"""

from dataclasses import dataclass
from typing import List, Optional

from ..types import DataType


@dataclass
class ColumnDefinition:
    """カラム定義
    
    テーブルの1つのカラムを表現します。
    
    Attributes:
        name: カラム名
        data_type: データ型（DataTypeインスタンス）
        nullable: NULL値を許可するか（将来の拡張）
        default_value: デフォルト値（将来の拡張）
    """
    name: str
    data_type: DataType
    nullable: bool = True
    default_value: Optional[any] = None
    
    def __post_init__(self):
        """データ型の型チェック"""
        if not isinstance(self.data_type, DataType):
            raise TypeError(
                f"data_typeはDataTypeインスタンスである必要があります。"
                f"文字列の場合はDataType.from_string()を使用してください。"
                f"受け取った値: {self.data_type} (type: {type(self.data_type)})"
            )
    
    @property
    def data_type_str(self) -> str:
        """データ型を文字列として取得"""
        return str(self.data_type)


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
        return [(col.name, col.data_type_str) for col in self.columns]
    
    def validate_values(self, values: List[any]) -> bool:
        """値のリストがスキーマに適合するか検証
        
        Args:
            values: 値のリスト
            
        Returns:
            適合する場合はTrue
        """
        if len(values) != len(self.columns):
            return False
        
        # 型チェック
        for i, (value, col_def) in enumerate(zip(values, self.columns)):
            if value is None and not col_def.nullable:
                return False
            
            # 型チェック（DataType Enumのvalidateメソッドを使用）
            if value is not None:
                if not col_def.data_type.validate(value):
                    return False
        
        return True

