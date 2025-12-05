"""
カタログ層

データベースのメタデータ（スキーマ情報）を管理します。
PostgreSQLのpg_class、pg_attribute、pg_indexに相当する機能を提供します。

カタログの重要性:
- データベースの「設計図」を保持します
- テーブル名、カラム名、データ型などの情報を管理
- クエリ実行時にスキーマ情報が必要になります
"""

from .metadata import Catalog, TableMetadata, ColumnMetadata
from .schema import Schema, ColumnDefinition

__all__ = [
    "Catalog",
    "TableMetadata",
    "ColumnMetadata",
    "Schema",
    "ColumnDefinition",
]

