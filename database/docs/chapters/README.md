# 3,000行で作るミニRDB教材（BYODB準拠・Python版）

### ゴール

- 約3,000行で、単一ノードのミニRDBをゼロから実装し、SQLサブセットで CRUD が動く。
- 各章で“動くデモ”と“最小テスト”を付け、累積で完成させる。

### 想定構成（合計〜3,000行目安）

- `database/senku-db-python/main.py`（REPL/CLI）: ~250
- `db/table.py`（行/テーブルAPI）: ~450
- `db/storage.py`（スナップショット/ページI/O）: ~550
- `db/wal.py`（追記ログ/リプレイ）: ~300
- `db/index.py`（単一列ハッシュ/ソート索引）: ~300
- `db/parser.py`（簡易SQL→AST）: ~400
- `db/executor/`（Iterator: Scan/Filter/Project）: ~400
- `db/catalog.py`（メタデータ最小）: ~150
- `tests/`（各章ごと最小）: ~200（テストは簡素）

### ファイル・ディレクトリ

- `database/senku-db-python/`
  - `main.py`
  - `db/`
    - `table.py`, `storage.py`, `wal.py`, `index.py`, `parser.py`, `catalog.py`
    - `executor/scan.py`, `executor/filter.py`, `executor/project.py`
  - `notebook/note1.ipynb`（可視化/デモ）

### 章構成（各章1–3h、各章で動くCLI/テスト付）

1. 最小REPLとInMemoryテーブル（スクーター）

   - 目的: メモリ上で `CREATE TABLE/INSERT/SELECT *` を動かす
   - 実装: `main.py`（簡易REPL/`-e`）、`table.py`（InMemoryTable）
   - デモ:
     ```bash
     python database/senku-db-python/main.py \
       -e "CREATE TABLE users(id INT, name TEXT);" \
       -e "INSERT INTO users VALUES (1, 'alice');" \
       -e "SELECT * FROM users;"
     ```

   - テスト: usersに2件挿入→SELECT件数=2
   - LOC: ~250

2. JSONスナップショット保存/ロード（自転車）

   - 目的: 終了時保存・起動時復元で永続化の初体験
   - 実装: `storage.py` に `save_table/load_table`、`main.py`から呼び出し
   - 仕様: 1テーブル=1 JSON（行は辞書配列）
   - デモ: 起動→INSERT→再起動→SELECTで復元
   - テスト: 再起動後の件数一致
   - LOC: +200（累計450）

3. 固定長ページ“風”の抽象（キックボード）

   - 目的: 8KBページ、スロット配列モデルをメモリ上で導入
   - 実装: `storage.py` に `Page`/`SlottedPage` 雛形、`table.py` が利用
   - 仕様: 可変長行、削除穴は未再利用でOK
   - デモ: メトリクス（使用ページ数/空きバイト）を `main.py` に表示
   - テスト: 1,000件挿入でページ数の下限チェック
   - LOC: +250（累計700）

4. 追記型WAL（ミニバイク）

   - 目的: クラッシュ後に `redo` で復元
   - 実装: `wal.py` に `append(record)` と `replay()`、`storage.py` から呼ぶ
   - 仕様: 1操作=1行JSON、redoのみ、fsync順序は簡易
   - デモ: スナップショット無効→WALだけで復元
   - テスト: クラッシュ相当（プロセスkill後）で整合性
   - LOC: +300（累計1,000）

5. 単一列インメモリ索引（プッシュバイク）

   - 目的: WHERE 同値を高速化
   - 実装: `index.py` に `HashIndex`（id→RIDセット） or `SortedIndex`
   - 仕様: ユニーク前提で簡素、永続化は後回し
   - デモ: 1万件ベンチで索引ON/OFF比較
   - テスト: WHERE id=… のレイテンシ比/ヒット件数
   - LOC: +300（累計1,300）

6. 超簡易SQLパーサ/AST（ランナー）

   - 目的: 文字列→AST→実行の導線確立
   - 実装: `parser.py` に `parse()`、`main.py` でAST分岐
   - 仕様: SELECT/INSERT/CREATE/DELETE（WHERE=単一列一致）
   - デモ: NGケース含むパーサ単体テスト
   - LOC: +400（累計1,700）

7. Iterator実行器（Scan/Filter/Project）（エンジン拡張①）

   - 目的: Volcanoモデルの基本
   - 実装: `executor/scan.py` `executor/filter.py` `executor/project.py`
   - 仕様: `open/next/close` の最小プロトコル
   - デモ: EXPLAIN風のオペレータツリー文字出力
   - テスト: フィルタとプロジェクションの組合せ
   - LOC: +400（累計2,100）

8. カタログ最小（テーブル/カラム/索引メタ）（インターフェース整備）

   - 目的: メタデータの一元管理と起動時ブート
   - 実装: `catalog.py` に最小 `tables/columns/indexes`
   - デモ: CREATE TABLEでカタログ更新→再起動で反映
   - テスト: カタログ整合チェック
   - LOC: +150（累計2,250）

9. 実ファイルページI/Oとチェックポイント（コンパクトカー）

   - 目的: 8KB固定ページをファイル化し、WAL+CPで安定化
   - 実装: `storage.py` ファイルI/O、WALローテ、`main.py` に `CHECKPOINT`
   - デモ: クラッシュ→再起動→WAL+CPで復元
   - テスト: 大量INSERT後の復元整合
   - LOC: +550（累計2,800）

10. トランザクション雛形/MVCCの種（ツーリング）

    - 目的: READ COMMITTED相当（xmin/xmax風フラグ）
    - 実装: `table.py` 行ヘッダに可視性、`main.py` に BEGIN/COMMIT/ROLLBACK（単純）
    - デモ: 2セッション相当シナリオ（ノートで再現）
    - テスト: 同時系の基本整合
    - LOC: +200（累計3,000）

### 仕様の最小化ポリシー

- 型: INT/TEXTに寄せる（NULL/型変換は限定）
- エラー: 章ごとに想定内のみ丁寧に扱い、想定外は例外
- 競合: シングルスレッドで排他は省略

### 進め方（毎章の共通テンプレ）

- コード: 目安100–400行（差分）
- デモ: `-e` で最小シナリオ実行
- テスト: 2–5ケース
- ドキュメント: `database/docs/0001-データベースの全体像.md` に到達点/制約を追記

### 参考（BYO Database ToCへのマッピング）

- ストレージ→3,4,9章
- インデックス→5章
- パーサ/実行器→6,7章
- WAL/CP→4,9章
- トランザクション入門→10章