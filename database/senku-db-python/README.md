# senku-db-python
```
senku-db-python/
│── main.py              # エントリーポイント (CLI)
│── db/
│   ├── __init__.py
│   ├── database.py
│   ├── parser.py
│   ├── table.py
│   ├── storage.py
│   ├── wal.py
│   ├── index.py
│── lessons/
│   ├── README.md        # 章ごとのexercise/solutionの実行方法
│   ├── ch01/
│   │   ├── exercise/
│   │   └── solution/
│   └── ch02/
│       ├── exercise/
│       └── solution/
│── notebook/
│   └── note1.ipynb
│── README.md
```

## 学習の進め方（lessons/）

`lessons/README.md` を参照してください。

クイックスタート:
```bash
# Chapter 1 exercise
python database/senku-db-python/lessons/ch01/exercise/main.py \
  -e "CREATE TABLE users(id, name)" \
  -e "INSERT INTO users VALUES (1, 'alice')" \
  -e "SELECT * FROM users"

# Chapter 2 solution（JSON永続化で再起動後も復元）
python database/senku-db-python/lessons/ch02/solution/main.py \
  -e "SELECT * FROM users"
```