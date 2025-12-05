"""
実行エンジン

SQLクエリを実行するエンジンです。
Iteratorモデル（Volcanoモデル）を採用し、各演算子をパイプラインで実行します。

Iteratorモデルの利点:
- 各演算子が独立して実装できる
- メモリ効率が良い（必要なデータだけを処理）
- 並列化が容易（将来の拡張）
- PostgreSQLやMySQLでも採用されている実績のあるアーキテクチャ
"""

from .iterator import Iterator, Tuple
from .operators import (
    ScanOperator,
    FilterOperator,
    ProjectOperator,
    JoinOperator,
    AggregateOperator,
    SortOperator,
)

__all__ = [
    "Iterator",
    "Tuple",
    "ScanOperator",
    "FilterOperator",
    "ProjectOperator",
    "JoinOperator",
    "AggregateOperator",
    "SortOperator",
]

