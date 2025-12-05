"""
REPL（Read-Eval-Print Loop）

対話型のSQL実行環境を提供します。
PostgreSQLのpsqlやMySQLのmysqlクライアントに相当する機能です。
"""

import sys
from pathlib import Path
from typing import Optional

from core.database import Database
from core.parser import SqlParser


class REPL:
    """REPLクラス
    
    対話型のSQL実行環境を提供します。
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """REPLを初期化
        
        Args:
            db_path: データベースファイルの保存先ディレクトリ
        """
        self.database = Database(db_path)
        self.parser = SqlParser()
    
    def run(self):
        """REPLを開始"""
        print("SenkuDB REPL")
        print("Type '.exit' to quit, '.help' for help")
        print()
        
        while True:
            try:
                line = input("senku> ").strip()
            except EOFError:
                print()
                break
            
            if not line:
                continue
            
            # メタコマンドの処理
            if line.startswith("."):
                if line == ".exit":
                    print("Goodbye!")
                    break
                elif line == ".help":
                    self._print_help()
                elif line.startswith(".tables"):
                    self._list_tables()
                else:
                    print(f"Unknown command: {line}")
                continue
            
            # SQL文の実行
            try:
                result = self.database.execute(line)
                if result is not None:
                    self._print_result(result)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
    
    def _print_help(self):
        """ヘルプを表示"""
        print("Meta commands:")
        print("  .exit     - Exit the REPL")
        print("  .help     - Show this help message")
        print("  .tables   - List all tables")
        print()
        print("SQL statements:")
        print("  CREATE TABLE table_name (col1 TYPE, col2 TYPE, ...)")
        print("  INSERT INTO table_name VALUES (val1, val2, ...)")
        print("  SELECT * FROM table_name [WHERE col = value]")
    
    def _list_tables(self):
        """テーブル一覧を表示"""
        tables = self.database.catalog.list_tables()
        if tables:
            print("Tables:")
            for table in tables:
                print(f"  - {table}")
        else:
            print("No tables found.")
    
    def _print_result(self, result):
        """クエリ結果を表示
        
        Args:
            result: クエリ結果（行のリスト）
        """
        if not result:
            print("(0 rows)")
            return
        
        # 簡易的な表形式で表示
        for i, row in enumerate(result, 1):
            print(f"Row {i}: {row}")
        
        print(f"({len(result)} row(s))")

