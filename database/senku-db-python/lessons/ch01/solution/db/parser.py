import sys
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Any

class StatementType(Enum):
    CREATE = "CREATE"
    INSERT = "INSERT"
    SELECT = "SELECT"

@dataclass
class WhereClause:
    """WHERE句のAST表現"""
    column: str
    operator: str  # "=", ">", "<", etc.
    value: Any

@dataclass
class ColumnDefinition:
    """カラム定義のAST表現"""
    name: str
    data_type: str  # "INT", "TEXT", etc.

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

class SqlParser:
    """SQL文をパースするクラス
    
    関数ベースの実装からクラスベースに移行することで、
    将来的な拡張（エラー履歴、設定の保持など）が容易になります。
    """
    
    def tokenize(self, line: str) -> list[str]:
        """SQL文を行単位でトークンに分割する
        
        簡易的な実装ですが、基本的なクォート処理と括弧の扱いに対応しています。
        将来的には本格的な字句解析器（Lexer）に置き換えることができます。
        
        Args:
            line: 入力SQL文
            
        Returns:
            トークンのリスト
        """
        line = line.strip().rstrip(";")
        
        # クォートされた文字列を保護しながら分割
        tokens = []
        current = ""
        in_quotes = False
        quote_char = None
        
        i = 0
        while i < len(line):
            char = line[i]
            
            if char in ("'", '"') and (i == 0 or line[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                    if current.strip():
                        tokens.extend(current.strip().split())
                        current = ""
                    current += char
                elif char == quote_char:
                    in_quotes = False
                    current += char
                    tokens.append(current)
                    current = ""
                    quote_char = None
                else:
                    current += char
            elif in_quotes:
                current += char
            elif char in ('(', ')', ','):
                if current.strip():
                    tokens.extend(current.strip().split())
                    current = ""
                if char != ' ':
                    tokens.append(char)
            else:
                current += char
            i += 1
        
        if current.strip():
            tokens.extend(current.strip().split())
        
        return tokens
    
    def parse(self, line: str) -> ParsedStatement:
        """SQL文をパースしてParsedStatementに変換する
        
        Args:
            line: 入力SQL文
            
        Returns:
            パースされたステートメント
            
        Raises:
            ValueError: 空のステートメントや未対応のステートメントの場合
        """
        toks = self.tokenize(line)
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
    
    def _parse_create(self, toks: list[str], original_line: str) -> ParsedStatement:
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
        
        stmt = ParsedStatement(
            StatementType.CREATE,
            {"table": table_name, "raw": original_line, "columns": columns}
        )
        stmt.table_name = table_name
        stmt.columns = columns
        return stmt
    
    def _parse_insert(self, toks: list[str], original_line: str) -> ParsedStatement:
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
        
        stmt = ParsedStatement(
            StatementType.INSERT,
            {"table": table, "raw": original_line, "values": values}
        )
        stmt.insert_table = table
        stmt.insert_values = values
        return stmt
    
    def _parse_select(self, toks: list[str], original_line: str) -> ParsedStatement:
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
        
        stmt = ParsedStatement(
            StatementType.SELECT,
            {
                "raw": original_line,
                "columns": columns,
                "table": table_name,
                "where": where_clause
            }
        )
        stmt.select_columns = columns
        stmt.select_table = table_name
        stmt.where_clause = where_clause
        return stmt

def handle_create(stmt: ParsedStatement):
    print(f"[CREATE] {stmt.payload}")

def handle_insert(stmt: ParsedStatement):
    print(f"[INSERT] {stmt.payload}")

def handle_select(stmt: ParsedStatement):
    print(f"[SELECT] {stmt.payload}")

def repl():
    print("SenkuDB> type .exit to quit")
    while True:
        try:
            line = input("senku> ").strip()
        except EOFError:
            break

        if not line:
            continue
        if line.startswith("."):
            if line == ".exit":
                print("bye")
                break
            elif line == ".help":
                print("Commands: .exit, .help")
            else:
                print(f"unknown meta command: {line}")
            continue

        try:
            parser = SqlParser()
            stmt = parser.parse(line)
            if stmt.kind == StatementType.CREATE:
                handle_create(stmt)
            elif stmt.kind == StatementType.INSERT:
                handle_insert(stmt)
            elif stmt.kind == StatementType.SELECT:
                handle_select(stmt)
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)

if __name__ == "__main__":
    repl()