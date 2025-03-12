# senku-db-python
```
senku-db-python/
│── main.py              # エントリーポイント (CLI や Web API など)
│── db/
│   ├── __init__.py      # パッケージ化
│   ├── database.py      # データベース管理
│   ├── parser.py        # SQL パーサー
│   ├── table.py         # テーブル管理
│   ├── storage.py       # データの永続化 (JSON, ファイル, etc.)
│   ├── wal.py           # Write-Ahead Logging (耐障害性)
│   ├── index.py         # インデックス (B+Tree など)
│── tests/
│   ├── test_parser.py   # パーサーのテスト
│   ├── test_database.py # データベース全体のテスト
│   ├── test_table.py    # テーブルのテスト
│── README.md            # プロジェクト概要
```