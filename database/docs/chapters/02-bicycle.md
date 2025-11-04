### 02: 自転車 — JSONスナップショット保存/ロード

目的
- 終了時に各テーブルをJSON保存、起動時にロードして復元

到達基準
- `data/` に `table.json` が保存される
- 再起動後に `SELECT` で前回データが見える

作業ファイル（exercise: 章共通の単一ワークスペース）
- `database/senku-db-python/lessons/exercise/main.py`
- `database/senku-db-python/lessons/exercise/db/{database.py, storage.py}`

タスク
1. `save_table_json(dir, table, columns, rows)` を実装
2. `load_table_json(dir, table)` を実装
3. `Database._load_existing()` でJSONから復元
4. `main.py` で実行終了時に `save_all()` を呼び出し

動作確認
```bash
python database/senku-db-python/lessons/exercise/main.py \
  -e "CREATE TABLE users(id, name)" \
  -e "INSERT INTO users VALUES (1, 'alice')"

# 2回目起動
python database/senku-db-python/lessons/ch02/exercise/main.py \
  -e "SELECT * FROM users"
```

答え合わせ
- `database/senku-db-python/lessons/ch02/solution/` とdiffを取る

