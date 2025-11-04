### 01: スクーター — InMemoryテーブルと最小REPL

目的
- メモリ上の単一テーブルで `CREATE TABLE/INSERT/SELECT *` を動かす

到達基準
- CLIの `-e` で複数SQLを順次実行できる
- REPLで対話実行できる
- エラーメッセージが出る（未定義テーブルなど）

作業ファイル（exercise: 章共通の単一ワークスペース）
- `database/senku-db-python/lessons/exercise/main.py`
- `database/senku-db-python/lessons/exercise/db/{database.py, table.py, parser.py}`

タスク
1. `Table` に `insert(values)` と `select_all()` を実装
2. `Database.execute(sql)` で create/insert/select を分岐処理
3. `main.py` で `-e` オプションとREPLを実装

動作確認
```bash
python database/senku-db-python/lessons/exercise/main.py \
  -e "CREATE TABLE users(id, name)" \
  -e "INSERT INTO users VALUES (1, 'alice')" \
  -e "SELECT * FROM users"
```

答え合わせ
- `database/senku-db-python/lessons/ch01/solution/` とdiffを取る

