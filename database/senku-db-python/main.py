import argparse
from db.database import Database

def main():
    # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(description='Simple SQL database')
    parser.add_argument('query', help='SQL query to execute')
    args = parser.parse_args()

    # データベースを初期化して、与えられたクエリを実行
    db = Database()
    try:
        result = db.execute(args.query)
        print(result)
    except Exception as e:
        print(f"エラー: {str(e)}")

if __name__ == "__main__":
    main()
