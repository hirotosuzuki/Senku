"""
メタデータ管理

データベースのメタデータ（テーブル情報、カラム情報など）を管理します。
PostgreSQLのシステムカタログ（pg_class, pg_attribute等）に相当する機能です。

システムカタログの歴史:
- リレーショナルデータベースでは、メタデータもリレーション（テーブル）として管理されます
- これにより、SQLでメタデータを問い合わせることができます（例: SELECT * FROM pg_tables）
- PostgreSQLではpg_で始まるシステムカタログテーブルが多数存在します
"""

import json
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass

from .schema import Schema, ColumnDefinition
from ..types import DataType


@dataclass
class ColumnMetadata:
    """カラムメタデータ
    
    カタログに保存されるカラム情報です。
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
    
    def to_dict(self) -> dict:
        """辞書に変換（JSON保存用）"""
        return {
            "name": self.name,
            "data_type": str(self.data_type),  # DataTypeを文字列に変換
            "nullable": self.nullable,
            "default_value": self.default_value
        }


@dataclass
class TableMetadata:
    """テーブルメタデータ
    
    カタログに保存されるテーブル情報です。
    """
    table_name: str
    columns: List[ColumnMetadata]
    file_path: str  # ヒープファイルのパス
    row_count: int = 0  # 統計情報（将来の最適化に使用）


class Catalog:
    """データベースカタログ
    
    データベース内の全テーブルのメタデータを管理します。
    現在はJSONファイルで永続化していますが、将来的にはシステムカタログテーブルとして実装します。
    
    カタログの役割:
    1. テーブルの存在確認
    2. スキーマ情報の取得
    3. メタデータの永続化
    4. クエリ実行時の名前解決
    """
    
    def __init__(self, catalog_path: Path):
        """カタログを初期化
        
        Args:
            catalog_path: カタログファイルのパス（JSON形式）
        """
        self.catalog_path = Path(catalog_path)
        self.tables: Dict[str, TableMetadata] = {}
        self._load()
    
    def _load(self):
        """カタログをディスクから読み込む"""
        if self.catalog_path.exists():
            with open(self.catalog_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for table_name, table_data in data.get('tables', {}).items():
                    columns = [
                        ColumnMetadata(
                            name=col_data['name'],
                            data_type=DataType.from_string(col_data['data_type']),
                            nullable=col_data.get('nullable', True),
                            default_value=col_data.get('default_value')
                        )
                        for col_data in table_data['columns']
                    ]
                    self.tables[table_name] = TableMetadata(
                        table_name=table_name,
                        columns=columns,
                        file_path=table_data['file_path'],
                        row_count=table_data.get('row_count', 0)
                    )
        else:
            # カタログファイルが存在しない場合は空のカタログを作成
            self._save()
    
    def _save(self):
        """カタログをディスクに保存"""
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'tables': {
                table_name: {
                    'columns': [col.to_dict() for col in table_meta.columns],
                    'file_path': table_meta.file_path,
                    'row_count': table_meta.row_count
                }
                for table_name, table_meta in self.tables.items()
            }
        }
        
        with open(self.catalog_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_table(self, table_name: str, schema: Schema, file_path: Path):
        """テーブルをカタログに登録
        
        Args:
            table_name: テーブル名
            schema: スキーマ定義
            file_path: ヒープファイルのパス
        """
        if table_name in self.tables:
            raise ValueError(f"テーブル '{table_name}' は既に存在します")
        
        columns = [
            ColumnMetadata(
                name=col.name,
                data_type=col.data_type,
                nullable=col.nullable,
                default_value=col.default_value
            )
            for col in schema.columns
        ]
        
        self.tables[table_name] = TableMetadata(
            table_name=table_name,
            columns=columns,
            file_path=str(file_path),
            row_count=0
        )
        
        self._save()
    
    def get_table_metadata(self, table_name: str) -> Optional[TableMetadata]:
        """テーブルメタデータを取得
        
        Args:
            table_name: テーブル名
            
        Returns:
            TableMetadata（存在しない場合はNone）
        """
        return self.tables.get(table_name)
    
    def get_schema(self, table_name: str) -> Optional[Schema]:
        """テーブルのスキーマを取得
        
        Args:
            table_name: テーブル名
            
        Returns:
            Schemaオブジェクト（存在しない場合はNone）
        """
        metadata = self.get_table_metadata(table_name)
        if not metadata:
            return None
        
        columns = [
            ColumnDefinition(
                name=col.name,
                data_type=col.data_type,
                nullable=col.nullable,
                default_value=col.default_value
            )
            for col in metadata.columns
        ]
        
        return Schema(table_name=table_name, columns=columns)
    
    def table_exists(self, table_name: str) -> bool:
        """テーブルが存在するか確認
        
        Args:
            table_name: テーブル名
            
        Returns:
            存在する場合はTrue
        """
        return table_name in self.tables
    
    def list_tables(self) -> List[str]:
        """全テーブル名のリストを取得
        
        Returns:
            テーブル名のリスト
        """
        return list(self.tables.keys())
    
    def update_row_count(self, table_name: str, row_count: int):
        """テーブルの行数を更新（統計情報）
        
        Args:
            table_name: テーブル名
            row_count: 行数
        """
        if table_name in self.tables:
            self.tables[table_name].row_count = row_count
            self._save()

