# フェーズ1: ストレージ層 詳細シーケンス図（create → insert → select）

本稿ではストレージ層を中心に, CREATE/SELECT/INSERT の詳細な呼び出し関係を時系列で示す。
主役は `HeapFile`, `Page`, `HeapTuple` であり, 必要に応じて `Database`, `Parser`, `Catalog` を登場させる。

---

## 1. CREATE TABLE（テーブル作成）

目的: カタログ登録とヒープファイルの物理作成。

```mermaid
sequenceDiagram
    participant U as User
    participant D as Database
    participant P as Parser
    participant C as Catalog
    participant HF as HeapFile

    U->>D: execute("CREATE TABLE t (id INT, name TEXT)")
    D->>P: parse(sql)
    P-->>D: AST(Create)

    D->>C: create_table(name, schema)
    C-->>D: catalog updated

    D->>HF: create()
    HF->>HF: ファイル作成/初期化(page_count=0)
    HF-->>D: OK

    D-->>U: OK
```

要点:
- カタログと物理ファイルを同期して初期化する。
- まだページは割り当てない（`page_count=0`）。

---

## 2. INSERT（ストレージ層内の書き込みフロー）

目的: 値をシリアライズし, 空きのあるページへ格納。無ければ新規ページを割り当てる。

```mermaid
sequenceDiagram
    participant D as Database
    participant HT as HeapTuple
    participant HF as HeapFile
    participant P as Page

    D->>HT: HeapTuple(values=[1, "alice"])
    D->>HT: to_bytes()
    HT->>HT: 各値を型に応じてシリアライズ（例: INT→>i, TEXT→len+bytes）
    HT-->>D: tuple_data(bytes)

    D->>HF: insert_tuple(tuple_data)

    loop 既存ページを確認
        HF->>HF: get_page(page_id)
        HF->>P: from_bytes(page_data, page_id)
        P-->>HF: Pageオブジェクト

        HF->>P: get_free_space()
        P-->>HF: free_space

        alt 空きあり
            HF->>P: insert_tuple(tuple_data)
            P->>P: data領域に追記, スロット配列/ヘッダ更新
            P-->>HF: slot_id

            HF->>P: to_bytes()
            P-->>HF: page_bytes
            HF->>HF: write_page(page_bytes) + flush + fsync
            HF-->>D: (page_id, slot_id)
        end
    end

    alt どのページにも空きなし
        HF->>HF: allocate_page()
        HF->>P: Page(page_id=page_count)
        P-->>HF: 新規ページ

        HF->>P: insert_tuple(tuple_data)
        P-->>HF: slot_id

        HF->>P: to_bytes()
        P-->>HF: page_bytes
        HF->>HF: write_page(page_bytes) + flush + fsync
        HF-->>D: (page_id, slot_id)
    end
```

要点:
- 可変長タプルを「先頭から順配置」, スロット配列は「末尾から逆配置」。
- 書き込みは `write_page → flush → fsync` で永続化を保証（簡易実装）。


## 3. SELECT（ストレージ層内の読み取りフロー）

目的: 全ページ/全スロットをスキャンし, タプルをデシリアライズして返す。

```mermaid
sequenceDiagram
    participant D as Database
    participant HF as HeapFile
    participant P as Page
    participant HT as HeapTuple

    D->>HF: scan_tuples(schema)

    loop 全ページをスキャン
        HF->>HF: get_page(page_id)
        HF->>P: from_bytes(page_data, page_id)
        P-->>HF: Pageオブジェクト

        loop スロットを順に読む
            HF->>P: get_tuple(slot_id)
            P-->>HF: tuple_data(bytes) or None

            alt データあり
                HF->>HT: from_bytes(tuple_data, schema)
                HT->>HT: デシリアライズ（型に応じて復元）
                HT->>HT: tuple_id=(page_id, slot_id)を設定
                HT-->>HF: HeapTuple
                HF-->>D: yield HeapTuple
            else データなし
                HF-->>D: skip
            end
        end
    end

    D-->>D: 結果リストを構築（必要に応じてFilter/Project適用）
```

要点:
- `get_page → Page.from_bytes` でページを復元してから, スロット配列経由でタプルを抽出。
- `HeapTuple.from_bytes` はスキーマの型情報に従い復元する。

---

## 付記: 役割分担の復習

- **HeapTuple**: 値⇔バイト列の相互変換（シリアライズ/デシリアライズ）と `tuple_id` の保持。
- **Page**: 8KB固定長ページ内での配置管理（データ領域/スロット配列/ヘッダ更新）。
- **HeapFile**: ページの読み書き・割当・全体スキャン, ディスクI/Oのトリガ。

この三者分業により, 「柔らかい可変長のレコード」を「堅牢な固定長ページ」に収め, ディスクI/Oを抑えつつ正しく永続化できる。


