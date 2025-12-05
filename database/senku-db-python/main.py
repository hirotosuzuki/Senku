"""
SenkuDB メインエントリーポイント

コマンドラインからデータベースを起動します。
"""

import argparse
import sys
from pathlib import Path

from cli.repl import REPL
from core.database import Database


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="SenkuDB - A minimal relational database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start REPL
  python main.py

  # Execute SQL from command line
  python main.py -e "CREATE TABLE users(id INT, name TEXT)"
  python main.py -e "INSERT INTO users VALUES (1, 'alice')"
  python main.py -e "SELECT * FROM users"
        """
    )
    
    parser.add_argument(
        "-e", "--execute",
        action="append",
        help="Execute SQL statement(s)"
    )
    
    parser.add_argument(
        "-d", "--database",
        type=Path,
        default=Path(".senkudb"),
        help="Database directory path (default: .senkudb)"
    )
    
    args = parser.parse_args()
    
    # SQL文が指定されている場合は実行して終了
    if args.execute:
        db = Database(args.database)
        for sql in args.execute:
            try:
                result = db.execute(sql)
                if result is not None:
                    _print_result(result)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        return
    
    # REPLを起動
    repl = REPL(args.database)
    repl.run()


def _print_result(result):
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


if __name__ == "__main__":
    main()

