### lessons ディレクトリの使い方

- exercise: 章共通の単一ワークスペース（自分で実装する場所）
- chXX/solution: 各章の参考解答（最小実装）

実行例（exercise）
```bash
# 章1〜2は共通exerciseでOK
python database/senku-db-python/lessons/exercise/main.py \
  -e "CREATE TABLE users(id, name)" \
  -e "INSERT INTO users VALUES (1, 'alice')" \
  -e "SELECT * FROM users"
```

実行例（solution）
```bash
# 章2のソリューション（保存/復元）
python database/senku-db-python/lessons/ch02/solution/main.py \
  -e "SELECT * FROM users"
```

