"""
AST（抽象構文木）定義

パースされたSQL文を表現するデータ構造です。
実行エンジンがこのASTを解釈してクエリを実行します。

各ステートメントタイプごとに専用のクラスを定義することで、
型安全性とコードの可読性を向上させています。

共通のインターフェースはProtocolで定義し、mixin的な役割を果たします。
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any, Union, Protocol


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


class StatementProtocol(Protocol):
    """すべてのステートメントが実装すべき共通インターフェース
    
    このProtocolは、すべてのステートメントクラスが
    共通して持つべき属性とメソッドを定義します。
    """
    
    original_sql: str
    """元のSQL文（デバッグやログ出力用）"""
    
    @property
    def kind(self) -> StatementType:
        """ステートメントタイプを返す"""
        ...


@dataclass
class CreateStatement(StatementProtocol):
    """CREATE TABLE文のAST表現"""
    table_name: str
    columns: List[ColumnDefinition]
    original_sql: str = ""
    
    @property
    def kind(self) -> StatementType:
        """ステートメントタイプを返す"""
        return StatementType.CREATE


@dataclass
class InsertStatement(StatementProtocol):
    """INSERT INTO文のAST表現"""
    table_name: str
    values: List[Any]
    original_sql: str = ""
    
    @property
    def kind(self) -> StatementType:
        """ステートメントタイプを返す"""
        return StatementType.INSERT


@dataclass
class SelectStatement(StatementProtocol):
    """SELECT文のAST表現"""
    columns: List[str]  # ["*"] またはカラム名のリスト
    table_name: str
    where_clause: Optional[WhereClause] = None
    original_sql: str = ""
    
    @property
    def kind(self) -> StatementType:
        """ステートメントタイプを返す"""
        return StatementType.SELECT


# ParsedStatementは、すべてのステートメントタイプのUnion型
ParsedStatement = Union[CreateStatement, InsertStatement, SelectStatement]

