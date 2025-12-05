# フェーズ1: テーブル管理 詳細シーケンス図（create → insert → select）

本稿ではテーブル管理層を中心に、CREATE/INSERT/SELECT の詳細な呼び出し関係を時系列で示す。
主役は `Catalog`, `Schema`, `Database` であり、必要に応じて `Parser`, `HeapFile` を登場させる。

---

## 0. データベース起動時のカタログ読み込み

目的: データベースを起動する際、カタログファイルから既存のテーブル情報を読み込む。

```mermaid
sequenceDiagram
    participant D as Database
    participant C as Catalog
    participant F as catalog.json

    D->>C: Catalog(catalog_path)
    C->>F: exists()?
    F-->>C: true/false

    alt ファイルが存在する
        C->>F: open('r', encoding='utf-8')
        F-->>C: JSONデータ
        C->>C: json.load()
        C->>C: ColumnMetadataを復元
        C->>C: TableMetadataを復元
        C->>C: self.tables[table_name] = TableMetadata(...)
    else ファイルが存在しない
        C->>C: _save() (空のカタログを作成)
        C->>F: write({ "tables": {} })
    end

    C-->>D: Catalogオブジェクト（メモリ上に展開済み）
```

要点:
- 起動時にカタログファイルを読み込み、メモリ上に展開することで、高速な名前解決が可能になる。
- カタログファイルが存在しない場合は、空のカタログを作成する。

---

## 1. CREATE TABLE（テーブル作成）

目的: カタログ登録とヒープファイルの物理作成。スキーマの生成から永続化まで。

```mermaid
sequenceDiagram
    participant U as User
    participant D as Database
    participant P as Parser
    participant C as Catalog
    participant S as Schema
    participant HF as HeapFile
    participant F as catalog.json

    U->>D: execute("CREATE TABLE users (id INT, name TEXT)")
    D->>P: parse(sql)
    P-->>D: AST(CreateStatement)

    D->>C: table_exists("users")
    C->>C: "users" in self.tables?
    C-->>D: false (存在しない)

    D->>D: ColumnDefinition(name="id", data_type="INT")
    D->>D: ColumnDefinition(name="name", data_type="TEXT")
    D->>S: Schema(table_name="users", columns=[...])
    S-->>D: Schemaオブジェクト

    D->>D: file_path = db_path / "users.heap"
    D->>HF: HeapFile(file_path)
    D->>HF: create()
    HF->>HF: ファイル作成/初期化(page_count=0)
    HF-->>D: OK

    D->>C: create_table("users", schema, file_path)
    C->>C: ColumnMetadata(name="id", data_type="INT", ...)
    C->>C: ColumnMetadata(name="name", data_type="TEXT", ...)
    C->>C: TableMetadata(table_name="users", columns=[...], file_path="users.heap")
    C->>C: self.tables["users"] = TableMetadata(...)
    C->>C: _save()
    C->>F: open('w', encoding='utf-8')
    C->>F: json.dump({ "tables": { "users": {...} } })
    C->>F: flush + close
    C-->>D: catalog updated

    D->>D: self.heap_files["users"] = heap_file
    D-->>U: OK
```

要点:
- パーサから取得したカラム定義を`ColumnDefinition`に変換し、`Schema`オブジェクトを作成。
- カタログに登録する際、`Schema`の`ColumnDefinition`を`ColumnMetadata`に変換して保存。
- カタログファイル（JSON）への書き込みは、`create_table()`内で`_save()`を呼び出して行う。
- ヒープファイルをメモリキャッシュに追加することで、次回アクセス時のパフォーマンスが向上。

---

## 2. INSERT（スキーマ検証と名前解決）

目的: カタログからスキーマを取得し、値の検証を行ってからストレージ層に挿入。

```mermaid
sequenceDiagram
    participant U as User
    participant D as Database
    participant P as Parser
    participant C as Catalog
    participant S as Schema
    participant HF as HeapFile

    U->>D: execute("INSERT INTO users VALUES (1, 'alice')")
    D->>P: parse(sql)
    P-->>D: AST(InsertStatement)

    D->>C: get_schema("users")
    C->>C: get_table_metadata("users")
    C->>C: metadata = self.tables.get("users")
    C-->>C: TableMetadata

    C->>C: ColumnDefinition(name="id", data_type="INT", ...)
    C->>C: ColumnDefinition(name="name", data_type="TEXT", ...)
    C->>S: Schema(table_name="users", columns=[...])
    S-->>C: Schemaオブジェクト
    C-->>D: Schema

    D->>S: validate_values([1, "alice"])
    S->>S: len(values) == len(columns)? → true
    S->>S: isinstance(1, int)? → true (INT型チェック)
    S->>S: isinstance("alice", str)? → true (TEXT型チェック)
    S-->>D: true (検証成功)

    D->>D: _get_heap_file("users")
    D->>D: "users" in self.heap_files?
    
    alt メモリキャッシュに存在
        D->>D: return self.heap_files["users"]
    else メモリキャッシュに存在しない
        D->>C: get_table_metadata("users")
        C-->>D: TableMetadata(file_path="users.heap")
        D->>D: file_path = db_path / metadata.file_path
        D->>HF: HeapFile(file_path)
        D->>D: self.heap_files["users"] = heap_file
    end

    D->>HF: insert_tuple(tuple_bytes)
    HF-->>D: (page_id, slot_id)
    D-->>U: OK
```

要点:
- `get_schema()`は、カタログの`TableMetadata`から`Schema`オブジェクトを復元する。
- `ColumnMetadata`を`ColumnDefinition`に変換して`Schema`を作成する。
- スキーマ検証では、値の数、型、NULL値の許可などをチェックする。
- ヒープファイルの取得は、メモリキャッシュを優先し、なければカタログから情報を取得して作成する。

---

## 3. SELECT（スキーマ取得と名前解決）

目的: カタログからスキーマを取得し、名前解決を行ってから実行エンジンに渡す。

```mermaid
sequenceDiagram
    participant U as User
    participant D as Database
    participant P as Parser
    participant C as Catalog
    participant S as Schema
    participant HF as HeapFile
    participant E as Executor

    U->>D: execute("SELECT * FROM users WHERE id = 1")
    D->>P: parse(sql)
    P-->>D: AST(SelectStatement)

    D->>C: get_schema("users")
    C->>C: get_table_metadata("users")
    C->>C: metadata = self.tables.get("users")
    C-->>C: TableMetadata

    C->>C: ColumnDefinition(name="id", data_type="INT", ...)
    C->>C: ColumnDefinition(name="name", data_type="TEXT", ...)
    C->>S: Schema(table_name="users", columns=[...])
    S-->>C: Schemaオブジェクト
    C-->>D: Schema

    D->>D: _get_heap_file("users")
    D->>D: "users" in self.heap_files?
    
    alt メモリキャッシュに存在
        D->>D: return self.heap_files["users"]
    else メモリキャッシュに存在しない
        D->>C: get_table_metadata("users")
        C-->>D: TableMetadata(file_path="users.heap")
        D->>D: file_path = db_path / metadata.file_path
        D->>HF: HeapFile(file_path)
        D->>D: self.heap_files["users"] = heap_file
    end

    D->>D: schema.get_column_index("id")
    S->>S: カラム名からインデックスを検索
    S-->>D: 0 (idのインデックス)

    D->>E: ScanOperator(heap_file, schema)
    D->>E: FilterOperator(scan, predicate)
    E->>E: open()
    loop next()
        E->>HF: scan_tuples(schema)
        HF-->>E: HeapTuple
        E->>E: predicate(tuple)でフィルタ
        E-->>D: filtered tuple
    end
    E->>E: close()
    D-->>U: results
```

要点:
- SELECT操作でも、INSERTと同様にカタログからスキーマを取得する。
- WHERE句のカラム名解決は、`schema.get_column_index()`で行う。
- 実行エンジンには、スキーマ情報とヒープファイルの両方を渡す。

---

## 4. カタログの永続化（_save()の詳細）

目的: メモリ上のカタログ情報をJSONファイルに書き込む。

```mermaid
sequenceDiagram
    participant C as Catalog
    participant TM as TableMetadata
    participant CM as ColumnMetadata
    participant F as catalog.json

    C->>C: _save()
    C->>C: catalog_path.parent.mkdir(parents=True, exist_ok=True)

    loop 各テーブル
        C->>TM: table_meta (TableMetadata)
        TM->>CM: columns (List[ColumnMetadata])
        
        loop 各カラム
            C->>CM: asdict(col)
            CM-->>C: カラム辞書データ
        end
        
        C->>C: テーブル辞書データを構築<br/>(columns, file_path, row_count)
    end

    C->>C: 全体のJSONデータ構造を構築<br/>(tables配下に全テーブル情報)

    C->>F: open('w', encoding='utf-8')
    C->>F: json.dump(data, indent=2, ensure_ascii=False)
    C->>F: flush + close
```

要点:
- `TableMetadata`を`asdict()`で辞書に変換し、JSON形式で保存する。
- `ensure_ascii=False`により、日本語などの非ASCII文字も正しく保存される。
- `indent=2`により、人間が読みやすい形式で保存される。

---

## 5. スキーマの復元（get_schema()の詳細）

目的: カタログの`TableMetadata`から`Schema`オブジェクトを復元する。

```mermaid
sequenceDiagram
    participant D as Database
    participant C as Catalog
    participant TM as TableMetadata
    participant CM as ColumnMetadata
    participant CD as ColumnDefinition
    participant S as Schema

    D->>C: get_schema("users")
    C->>C: get_table_metadata("users")
    C->>TM: self.tables.get("users")
    TM-->>C: TableMetadata

    alt テーブルが存在しない
        C-->>D: None
    else テーブルが存在する
        C->>TM: columns (List[ColumnMetadata])
        
        loop 各カラム
            TM->>CM: ColumnMetadata取得
            C->>CD: ColumnDefinition作成<br/>(name, data_type, nullable, default_value)
            CM-->>CD: ColumnDefinitionオブジェクト
        end

        C->>S: Schema作成<br/>(table_name="users", columns=[...])
        S-->>C: Schemaオブジェクト
        C-->>D: Schema
    end
```

要点:
- `ColumnMetadata`（カタログ用）を`ColumnDefinition`（スキーマ用）に変換する。
- 両者は同じ情報を持つが、用途が異なる（カタログは永続化、スキーマは実行時検証）。

---

## 付記: 役割分担の復習

- **Catalog**: メタデータの永続化と名前解決。JSONファイルへの読み書きを担当。
- **Schema**: テーブル構造の定義と値の検証。実行時に使用される。
- **Database**: カタログとストレージ層を橋渡し。テーブル作成、名前解決、スキーマ検証を統合的に管理。
- **TableMetadata**: カタログに保存されるテーブル情報（永続化用）。
- **ColumnMetadata**: カタログに保存されるカラム情報（永続化用）。
- **ColumnDefinition**: スキーマで使用されるカラム定義（実行時用）。

この分業により、「メタデータの永続化」と「実行時のスキーマ検証」を分離し、それぞれの責務を明確にできる。将来的にシステムカタログテーブルに移行する際も、この分離により影響範囲を最小限に抑えられる。

