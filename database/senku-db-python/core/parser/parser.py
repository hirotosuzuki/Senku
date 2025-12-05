"""
SQLパーサ

SQL文をパースしてASTに変換します。
既存のlessons/ch01/solution/db/parser.pyをベースに実装しています。

パーサの役割:
- 字句解析器（Lexer）が生成したトークン列を受け取る
- トークン列を構文規則に従って解析（構文解析）
- AST（抽象構文木）を生成

コンパイラ理論における「構文解析（Parsing）」の段階を担当します。
"""

from typing import List
from .ast import (
    ParsedStatement,
    CreateStatement,
    InsertStatement,
    SelectStatement,
    WhereClause,
    ColumnDefinition,
)
from .lexer import Lexer


class SqlParser:
    """SQL文をパースするクラス
    
    関数ベースの実装からクラスベースに移行することで、
    将来的な拡張（エラー履歴、設定の保持など）が容易になります。
    
    字句解析はLexerクラスに分離され、パーサは構文解析に専念します。
    """
    
    def __init__(self, lexer: Lexer = None):
        """パーサを初期化
        
        Args:
            lexer: 字句解析器（Noneの場合は新規作成）
        """
        self.lexer = lexer or Lexer()
    
    def parse(self, line: str) -> ParsedStatement:
        """SQL文をパースしてParsedStatementに変換する
        
        Args:
            line: 入力SQL文
            
        Returns:
            パースされたステートメント
            
        Raises:
            ValueError: 空のステートメントや未対応のステートメントの場合
        """
        toks = self.lexer.tokenize(line)
        if not toks:
            raise ValueError("empty statement")
        
        head = toks[0].upper()
        
        if head == "CREATE" and len(toks) >= 3 and toks[1].upper() == "TABLE":
            return self._parse_create(toks, line)
        if head == "INSERT" and len(toks) >= 3 and toks[1].upper() == "INTO":
            return self._parse_insert(toks, line)
        if head == "SELECT":
            return self._parse_select(toks, line)
        
        raise ValueError(f"unsupported statement: {line}")
    
    def _parse_create(self, toks: List[str], original_line: str) -> ParsedStatement:
        """CREATE TABLE文をパースする
        
        Args:
            toks: トークンリスト
            original_line: 元のSQL文
            
        Returns:
            ParsedStatement (CREATE)
            
        Raises:
            ValueError: 構文が不正な場合
        """
        # 例: CREATE TABLE users(id INT, name TEXT)
        if len(toks) < 3:
            raise ValueError("CREATE TABLE statement requires table name")
        
        table_name = toks[2]
        
        # カラム定義を抽出（括弧内の内容）
        columns = []
        if len(toks) > 3:
            # 括弧の開始位置を探す
            paren_start = None
            for i, tok in enumerate(toks):
                if tok == '(':
                    paren_start = i
                    break
            
            if paren_start is not None:
                # 括弧内のトークンを抽出
                col_tokens = []
                paren_count = 0
                for i in range(paren_start + 1, len(toks)):
                    if toks[i] == '(':
                        paren_count += 1
                    elif toks[i] == ')':
                        if paren_count == 0:
                            break
                        paren_count -= 1
                    col_tokens.append(toks[i])
                
                # カンマで分割してカラム定義を解析
                current_col = []
                for tok in col_tokens:
                    if tok == ',':
                        if len(current_col) >= 2:
                            col_name = current_col[0]
                            col_type = current_col[1].upper()
                            columns.append(ColumnDefinition(col_name, col_type))
                        current_col = []
                    else:
                        current_col.append(tok)
                
                # 最後のカラム
                if len(current_col) >= 2:
                    col_name = current_col[0]
                    col_type = current_col[1].upper()
                    columns.append(ColumnDefinition(col_name, col_type))
        
        return CreateStatement(
            table_name=table_name,
            columns=columns,
            original_sql=original_line
        )
    
    def _parse_insert(self, toks: List[str], original_line: str) -> ParsedStatement:
        """INSERT INTO文をパースする
        
        Args:
            toks: トークンリスト
            original_line: 元のSQL文
            
        Returns:
            ParsedStatement (INSERT)
            
        Raises:
            ValueError: 構文が不正な場合
        """
        # 例: INSERT INTO users VALUES (1, 'alice')
        if len(toks) < 4 or toks[3].upper() != "VALUES":
            raise ValueError("INSERT statement requires 'VALUES' keyword")
        
        table = toks[2]
        
        # VALUES句から値を抽出
        values = []
        paren_start = None
        for i, tok in enumerate(toks):
            if tok == '(' and i > 3:  # VALUESの後の括弧
                paren_start = i
                break
        
        if paren_start is not None:
            # 括弧内の値を抽出
            for i in range(paren_start + 1, len(toks)):
                tok = toks[i]
                if tok == ')':
                    break
                if tok != ',':
                    # クォートを除去して値に変換
                    if tok.startswith("'") and tok.endswith("'"):
                        values.append(tok[1:-1])
                    elif tok.startswith('"') and tok.endswith('"'):
                        values.append(tok[1:-1])
                    else:
                        # 数値として解釈を試みる
                        try:
                            values.append(int(tok))
                        except ValueError:
                            try:
                                values.append(float(tok))
                            except ValueError:
                                values.append(tok)
        
        return InsertStatement(
            table_name=table,
            values=values,
            original_sql=original_line
        )
    
    def _parse_select(self, toks: List[str], original_line: str) -> ParsedStatement:
        """SELECT文をパースする
        
        Args:
            toks: トークンリスト
            original_line: 元のSQL文
            
        Returns:
            ParsedStatement (SELECT)
            
        Raises:
            ValueError: 構文が不正な場合
        """
        # 例: SELECT * FROM users WHERE id = 1
        if len(toks) < 4 or toks[2].upper() != "FROM":
            raise ValueError("SELECT statement requires 'FROM' keyword")
        
        # SELECT句のカラムを抽出
        columns = []
        if toks[1] == "*":
            columns = ["*"]
        else:
            # カンマ区切りのカラムリスト（簡易版）
            col_part = toks[1]
            if ',' in col_part:
                columns = [c.strip() for c in col_part.split(',')]
            else:
                columns = [col_part]
        
        # FROM句のテーブル名を抽出
        table_name = toks[3] if len(toks) > 3 else None
        
        # WHERE句を抽出（簡易版：WHERE column = value のみ対応）
        where_clause = None
        where_idx = None
        for i, tok in enumerate(toks):
            if tok.upper() == "WHERE":
                where_idx = i
                break
        
        if where_idx is not None and len(toks) > where_idx + 3:
            column = toks[where_idx + 1]
            operator = toks[where_idx + 2]
            value_str = toks[where_idx + 3]
            
            # 値の型を推論
            if value_str.startswith("'") and value_str.endswith("'"):
                value = value_str[1:-1]
            elif value_str.startswith('"') and value_str.endswith('"'):
                value = value_str[1:-1]
            else:
                try:
                    value = int(value_str)
                except ValueError:
                    try:
                        value = float(value_str)
                    except ValueError:
                        value = value_str
            
            where_clause = WhereClause(column, operator, value)
        
        return SelectStatement(
            columns=columns,
            table_name=table_name,
            where_clause=where_clause,
            original_sql=original_line
        )

