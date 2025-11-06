"""
AST（抽象構文木）定義

パースされたSQL文を表現するデータ構造です。
実行エンジンがこのASTを解釈してクエリを実行します。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any


class StatementType(Enum):
    """SQLステートメントの種類"""
    CREATE = "CREATE"
    INSERT = "INSERT"
    SELECT = "SELECT"
    UPDATE = "UPDATE"  # 将来の拡張
    DELETE = "DELETE"  # 将来の拡張
    DROP = "DROP"  # 将来の拡張


@dataclass
class WhereClause:
    """WHERE句のAST表現"""
    column: str
    operator: str  # "=", ">", "<", ">=", "<=", "!=", etc.
    value: Any


@dataclass
class ColumnDefinition:
    """カラム定義のAST表現"""
    name: str
    data_type: str  # "INT", "TEXT", "FLOAT", etc.


class ParsedStatement:
    """パースされたSQL文のAST表現
    
    後方互換性のため、従来のpayloadも保持していますが、
    より構造化された属性を優先的に使用することを推奨します。
    """
    
    def __init__(self, kind: StatementType, payload: dict):
        self.kind = kind
        self.payload = payload
        
        # CREATE TABLE用の構造化データ
        self.table_name: Optional[str] = payload.get("table")
        self.columns: Optional[List[ColumnDefinition]] = None
        
        # INSERT用の構造化データ
        self.insert_table: Optional[str] = payload.get("table")
        self.insert_values: Optional[List[Any]] = None
        
        # SELECT用の構造化データ
        self.select_columns: Optional[List[str]] = None
        self.select_table: Optional[str] = None
        self.where_clause: Optional[WhereClause] = None

