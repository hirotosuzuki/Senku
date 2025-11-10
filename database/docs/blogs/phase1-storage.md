# フェーズ1: ストレージ層 - データベースの「倉庫」を作る

## はじめに

こんにちは、古の老賢者です。前回は実行エンジンについて語りましたが、今回はデータを実際に保存する「ストレージ層」について語りましょう。

実行エンジンが「実行者」なら、ストレージ層は「倉庫」です。実行者がデータを処理するためには、そのデータをどこかに保存しておく必要があります。その「どこか」がストレージ層です。

まるで、工場で製品を作るには、原材料を保管する倉庫が必要なのと同じですね。どんなに優れた製造ライン（実行エンジン）があっても、原材料（データ）を保管する場所がなければ、何も作ることができません。

## 何をやるのか：フェーズ1のストレージ層の役割

フェーズ1では、最小限の機能を持つストレージ層を実装します。具体的には、以下の3つのコンポーネントを実装します：

### 1. Page - 固定長ページ

データベースの基本単位である「ページ」を管理します。1ページは8KBの固定長で、PostgreSQLと同じサイズを採用しています。

```python
PAGE_SIZE = 8192  # 8KB
```

ページは、データベースがディスクとやり取りする最小単位です。なぜ固定長なのか？それは、ディスクI/Oを効率化するためです。可変長だと、どこから読み始めればいいかわからなくなってしまいます。

### 2. HeapFile - ヒープファイル

テーブルのデータを物理的に保存するファイルを管理します。各テーブルは1つのヒープファイルに対応します。

```python
heap_file = HeapFile(file_path)
heap_file.create()  # 新しいヒープファイルを作成
```

ヒープファイルは複数のページから構成され、タプル（行）を順次追加していく方式です。

#### 余談：なぜ「Heap」という名前なのか？

「ヒープ」という名前は、データ構造の「ヒープ」（優先度付きキュー）とは異なります。データベースの「ヒープファイル」は、以下の特徴から「ヒープ」と呼ばれます：

1. **任意の順序で格納される**: データは挿入された順番に、空きスペースがあればそこに格納されます。ソートされた順序や特定の構造は持たず、単に「積み重ね」られていきます。

2. **インデックスがない**: ヒープファイルは、インデックスを持たない基本的なストレージ形式です。データを検索するには、全ページをスキャンする必要があります。これが「フルテーブルスキャン」の基礎となります。

3. **「積み重ね」のイメージ**: 英語の「heap」には「積み重ね」「山積み」という意味があります。データが順番に積み重ねられていく様子を表現しています。

PostgreSQLでも、テーブルのメインデータは「ヒープファイル」に格納されます。インデックスは別のファイルとして管理され、ヒープファイルへのポインタを保持します。

### ページとヒープファイルの関係

ページとヒープファイルの違いがわかりにくいかもしれません。簡単に言うと：

- **ページ（Page）**: データベースの基本単位。8KBの固定長のデータブロック。1つのページには複数のタプル（行）が格納される。
- **ヒープファイル（HeapFile）**: 複数のページを管理するファイル。1つのテーブル = 1つのヒープファイル。

例えるなら：
- **ページ** = 本の1ページ
- **ヒープファイル** = 本全体（複数のページからなる）

具体例を見てみましょう。`users`テーブルを作成した場合：

```
users.heap (ヒープファイル)
├── Page 0 (8KB) - タプル1, タプル2, タプル3, ...
├── Page 1 (8KB) - タプル100, タプル101, ...
├── Page 2 (8KB) - タプル200, ...
└── ...
```

データが増えると、新しいページが追加されていきます。ヒープファイルは、これらのページを管理し、必要なページを読み書きする役割を担います。

### 3. HeapTuple - タプル（行）の表現

データベースの1行を表現します。メモリ上のデータ構造とディスク上のバイト列を相互変換する役割を担います。

```python
tuple_obj = HeapTuple(values=[1, "alice"])
tuple_data = tuple_obj.to_bytes()  # バイト列に変換
```

## なぜやるのか：ストレージ層の存在意義

### 1. データの永続化

データベースの最大の使命は、データを永続化することです。プログラムを終了しても、データは残り続けなければなりません。ストレージ層は、メモリ上のデータをディスクに書き込み、次回起動時に読み込む役割を担います。

### 2. 効率的なI/O

ディスクI/Oは、メモリアクセスの約10万倍遅いと言われています。そのため、効率的なI/Oがデータベースの性能を左右します。固定長ページを使うことで、ランダムアクセスが可能になり、必要なページだけを読み込むことができます。

### 3. 将来の拡張性

フェーズ1では最小限の機能しか実装しませんが、この基盤があれば、将来的に以下のような機能を追加することが容易になります：

- **バッファマネージャ**: ページキャッシュによるI/O最適化（フェーズ2）
- **WAL**: トランザクションログによる障害復旧（フェーズ2）
- **インデックス**: B+木による高速検索（フェーズ3）
- **VACUUM**: ガベージコレクション（フェーズ5）

## 歴史的な背景：ページベースストレージの確立

### 1970年代：リレーショナルデータベースの誕生

1970年代にエドガー・コッドがリレーショナルデータベースの概念を提唱しました。当時、データをどのようにディスクに保存するかが大きな課題でした。

### 1980年代：ページベースストレージの標準化

1980年代になると、多くのデータベースシステムが「ページベースストレージ」を採用するようになりました。これは、以下の理由からです：

- **効率的なI/O**: 固定長ページを使うことで、ランダムアクセスが可能
- **メモリ管理の容易さ**: ページ単位でメモリを管理できる
- **キャッシュの効率化**: ページ単位でキャッシュできる

### 現代のデータベースでの採用

ページベースストレージは、現代の多くのデータベースシステムで採用されています：

- **PostgreSQL**: 8KBの固定長ページを採用
- **MySQL (InnoDB)**: 16KBの固定長ページを採用
- **SQLite**: 可変長ページを採用（特殊なケース）

これらの実績により、ページベースストレージは「実証済みのアーキテクチャ」として確立されています。

## 技術的な詳細：ストレージ層の実装

### 1. ページの構造

ページは8KB（8192バイト）の固定長です。この中に、複数のタプル（行）を効率的に格納する必要があります。

#### ページのレイアウト

ページは、以下の4つの領域に分かれています：

```
┌─────────────────────────────────────────────────────────┐
│ Header (24 bytes)                                       │ ← ページのメタデータ
├─────────────────────────────────────────────────────────┤
│ Data (タプル1, タプル2, タプル3, ...)                  │ ← 実際のデータ
│                                                         │
│ ...Free Space...                                        │ ← 未使用領域
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Slot Array (スロット配列)                                │ ← タプルの位置情報
│ [offset1, length1], [offset2, length2], ...            │
└─────────────────────────────────────────────────────────┘
         ↑ 先頭から順に配置              ↑ 末尾から逆順に配置
```

#### なぜこの構造なのか？

タプル（行）のサイズは可変です。例えば：
- `(1, "alice")` → 小さい
- `(2, "very long name that takes more space")` → 大きい

固定長のページに可変長のデータを格納するには、どこに何があるかを記録する必要があります。それが「スロット配列」です。

#### 具体例：3つのタプルを格納したページ

実際のページの中身を見てみましょう：

```
ページ全体（8KB = 8192バイト）

[0-23]     Header: 空きスペース、スロット数など
[24-100]   タプル1: (1, "alice") → 76バイト
[101-200]  タプル2: (2, "bob") → 99バイト
[201-350]  タプル3: (3, "charlie") → 149バイト
[351-8150] Free Space（未使用領域）
[8151-8183] スロット配列:
            - スロット0: offset=24, length=76  (タプル1の位置)
            - スロット1: offset=101, length=99 (タプル2の位置)
            - スロット2: offset=201, length=149 (タプル3の位置)
[8184-8191] 予約領域
```

#### スロット配列の役割

スロット配列は、ページの末尾から逆順に配置されます。各スロットは「このタプルは、ページの何バイト目から始まって、何バイトの長さか」を記録します。

- **スロット0**: `(offset=24, length=76)` → タプル1は24バイト目から始まり、76バイトの長さ
- **スロット1**: `(offset=101, length=99)` → タプル2は101バイト目から始まり、99バイトの長さ
- **スロット2**: `(offset=201, length=149)` → タプル3は201バイト目から始まり、149バイトの長さ

これにより、タプルを読み込む際は「スロット2を見る → 201バイト目から149バイト読み込む」という手順で、正確にデータを取得できます。

#### なぜ末尾から配置するのか？

スロット配列をページの末尾から配置する理由は、データとスロット配列が衝突しないようにするためです。データは先頭から、スロット配列は末尾から、それぞれ成長していくため、中央の空きスペースを効率的に使えます。

### 2. ヒープファイルの管理

ヒープファイルは、複数のページから構成されます。タプルを挿入する際は、以下の手順を踏みます：

1. 既存のページに空きがあるか確認
2. 空きがあれば、そのページにタプルを挿入
3. 空きがなければ、新しいページを割り当ててタプルを挿入

```python
def insert_tuple(self, tuple_data: bytes) -> tuple[int, int]:
    # 既存のページに空きがあるか確認
    for page_id in range(self.page_count):
        page = self.get_page(page_id)
        if page and page.get_free_space() >= len(tuple_data) + 8:
            slot_id = page.insert_tuple(tuple_data)
            if slot_id is not None:
                self.write_page(page)
                return (page_id, slot_id)
    
    # 既存ページに空きがない場合は新しいページを割り当て
    page = self.allocate_page()
    slot_id = page.insert_tuple(tuple_data)
    self.write_page(page)
    return (page.page_id, slot_id)
```

### 3. タプルのシリアライズ

タプル（行）をディスクに保存するためには、メモリ上のデータ構造をバイト列に変換する必要があります。これを「シリアライズ」と呼びます。

```python
def to_bytes(self) -> bytes:
    """タプルをバイト列にシリアライズ"""
    parts = []
    for value in self.values:
        if isinstance(value, int):
            parts.append(struct.pack(">i", value))  # 4バイト整数
        elif isinstance(value, str):
            encoded = value.encode('utf-8')
            parts.append(struct.pack(">I", len(encoded)))  # 長さ
            parts.append(encoded)  # データ
        # ...
    return b''.join(parts)
```

逆に、ディスクから読み込んだバイト列をメモリ上のデータ構造に変換することを「デシリアライズ」と呼びます。

## 実装のポイント

### 1. ページサイズの選択

ページサイズは、パフォーマンスに大きな影響を与えます：

- **小さすぎる**: I/O回数が増える
- **大きすぎる**: メモリ効率が悪くなる

PostgreSQLでは8KBを採用していますが、これは多くの環境で最適なバランスを取った結果です。

### 2. スロット配列方式

可変長のタプルを効率的に管理するため、スロット配列方式を採用しています。これにより、タプルの削除や更新が容易になります（将来的な拡張）。

### 3. ディスクへの確実な書き込み

データの整合性を保つため、`os.fsync()`を使用してディスクへの確実な書き込みを行います。これにより、システムクラッシュ時でもデータが失われにくくなります。

```python
def write_page(self, page: Page):
    with open(self.file_path, 'r+b') as f:
        f.seek(page.page_id * PAGE_SIZE)
        f.write(page.to_bytes())
        f.flush()
        os.fsync(f.fileno())  # ディスクへの確実な書き込み
```

## 実装の詳細解説：各クラスの実装を見る

それでは、実際のコードを見ながら、各クラスの実装を詳しく解説していきましょう。コードを読むことで、理論がどのように実装されているかが理解できるはずです。

### 1. HeapTuple - タプルのシリアライズとデシリアライズ

`HeapTuple`は、データベースの1行を表現するクラスです。メモリ上のデータ構造とディスク上のバイト列を相互変換する役割を担います。

#### シリアライズ：メモリからディスクへ

```py
    def to_bytes(self) -> bytes:
        """タプルをバイト列にシリアライズ
        
        簡易的な実装: 各値を型に応じてシリアライズ
        将来的にはより効率的なフォーマット（列指向など）を検討
        """
        parts = []
        for value in self.values:
            if isinstance(value, int):
                parts.append(struct.pack(">i", value))  # 4バイト整数
            elif isinstance(value, str):
                encoded = value.encode('utf-8')
                parts.append(struct.pack(">I", len(encoded)))  # 長さ
                parts.append(encoded)  # データ
            elif isinstance(value, float):
                parts.append(struct.pack(">d", value))  # 8バイト浮動小数点数
            else:
                # その他の型は文字列として扱う
                encoded = str(value).encode('utf-8')
                parts.append(struct.pack(">I", len(encoded)))
                parts.append(encoded)
        
        return b''.join(parts)
```

**実装のポイント**:

1. **型ごとの処理**: 各値の型に応じて、適切なバイト列に変換します
   - `int`: 4バイトの整数（ビッグエンディアン）
   - `str`: 長さ（4バイト）+ UTF-8エンコードされた文字列データ
   - `float`: 8バイトの浮動小数点数

2. **ビッグエンディアン（`>`）**: `struct.pack(">i", value)`の`>`は、ビッグエンディアン（ネットワークバイトオーダー）を意味します。これにより、異なるアーキテクチャ間でもデータの互換性が保たれます。

3. **可変長データの扱い**: 文字列は可変長なので、先に長さを記録してからデータを記録します。これにより、デシリアライズ時に正確に復元できます。

#### デシリアライズ：ディスクからメモリへ

```py
    @classmethod
    def from_bytes(cls, data: bytes, schema: List[tuple[str, str]]) -> "HeapTuple":
        """バイト列からタプルを復元
        
        Args:
            data: タプルのバイト列
            schema: スキーマ情報 [(column_name, data_type), ...]
            
        Returns:
            復元されたHeapTuple
        """
        values = []
        offset = 0
        
        for col_name, col_type in schema:
            if col_type == "INT":
                value = struct.unpack_from(">i", data, offset)[0]
                offset += 4
            elif col_type == "TEXT":
                length = struct.unpack_from(">I", data, offset)[0]
                offset += 4
                value = data[offset:offset + length].decode('utf-8')
                offset += length
            elif col_type == "FLOAT":
                value = struct.unpack_from(">d", data, offset)[0]
                offset += 8
            else:
                # デフォルトはTEXTとして扱う
                length = struct.unpack_from(">I", data, offset)[0]
                offset += 4
                value = data[offset:offset + length].decode('utf-8')
                offset += length
            
            values.append(value)
        
        return cls(values=values)
```

**実装のポイント**:

1. **スキーマ情報の必要性**: デシリアライズには、各カラムの型情報（スキーマ）が必要です。型がわからなければ、バイト列を正しく解釈できません。

2. **オフセット管理**: `offset`変数を使って、現在読み込んでいる位置を追跡します。各値を読み込んだ後、オフセットを進めます。

3. **可変長データの復元**: 文字列の場合、まず長さを読み込み、その長さ分だけデータを読み込んでからUTF-8デコードします。

### 2. Page - ページの内部構造と操作

`Page`クラスは、8KBの固定長ページを管理します。可変長のタプルを効率的に格納するため、スロット配列方式を採用しています。

#### ページの初期化

```py
    def __init__(self, page_id: int = 0):
        """ページを初期化
        
        Args:
            page_id: ページID（ファイル内でのページ番号）
        """
        self.page_id = page_id
        self.header = PageHeader()
        self.data = bytearray(PAGE_SIZE)
        self.slots: List[tuple[int, int]] = []  # (offset, length) のリスト
        
        # ヘッダーをページの先頭に書き込む
        header_bytes = self.header.to_bytes()
        self.data[:PAGE_HEADER_SIZE] = header_bytes
```

**実装のポイント**:

1. **bytearrayの使用**: `bytearray(PAGE_SIZE)`で8KBの固定長バッファを確保します。これにより、メモリ上でページ全体を操作できます。

2. **スロット配列**: `self.slots`は、各タプルの位置情報`(offset, length)`を保持するリストです。メモリ上ではリストとして管理し、ディスクに書き込む際にページの末尾に配置します。

#### タプルの挿入

```py
    def insert_tuple(self, tuple_data: bytes) -> Optional[int]:
        """タプルをページに挿入
        
        Args:
            tuple_data: タプルのバイト列
            
        Returns:
            スロット番号（失敗時はNone）
        """
        tuple_size = len(tuple_data)
        required_space = tuple_size + SLOT_SIZE  # タプル + スロットエントリ
        
        # 空きスペースをチェック
        if self.header.free_space < required_space:
            return None  # ページに空きがない
        
        # データを挿入する位置を決定（ヘッダーの後から順に）
        data_start = PAGE_HEADER_SIZE
        current_offset = data_start
        
        # 既存のタプルの最大オフセットを計算
        for offset, length in self.slots:
            current_offset = max(current_offset, offset + length)
        
        # タプルを書き込む
        offset = current_offset
        self.data[offset:offset + tuple_size] = tuple_data
        
        # スロットを追加（ページの末尾から逆順に配置）
        slot_offset = PAGE_SIZE - (len(self.slots) + 1) * SLOT_SIZE
        struct.pack_into(">II", self.data, slot_offset, offset, tuple_size)
        self.slots.append((offset, tuple_size))
        
        # ヘッダーを更新
        self.header.slot_count = len(self.slots)
        self.header.free_space = PAGE_SIZE - current_offset - tuple_size - len(self.slots) * SLOT_SIZE
        
        # ヘッダーを再書き込み
        header_bytes = self.header.to_bytes()
        self.data[:PAGE_HEADER_SIZE] = header_bytes
        
        return len(self.slots) - 1
```

**実装のポイント**:

1. **空きスペースのチェック**: タプルとスロットエントリ（8バイト）の両方のスペースが必要です。空きがなければ`None`を返します。

2. **挿入位置の決定**: 既存のタプルの最大オフセットを計算し、その後に新しいタプルを配置します。これにより、データは先頭から順に詰められていきます。

3. **スロット配列の配置**: スロットはページの末尾から逆順に配置されます。`PAGE_SIZE - (len(self.slots) + 1) * SLOT_SIZE`で計算することで、末尾から順に配置できます。

4. **ヘッダーの更新**: タプルを挿入した後、スロット数と空きスペースを更新し、ヘッダーを再書き込みします。

#### タプルの取得

```py
    def get_tuple(self, slot_id: int) -> Optional[bytes]:
        """スロットIDからタプルを取得
        
        Args:
            slot_id: スロット番号
            
        Returns:
            タプルのバイト列（存在しない場合はNone）
        """
        if slot_id < 0 or slot_id >= len(self.slots):
            return None
        
        offset, length = self.slots[slot_id]
        return bytes(self.data[offset:offset + length])
```

**実装のポイント**:

1. **スロット配列の参照**: スロットIDから`(offset, length)`を取得し、その位置からデータを読み込みます。

2. **範囲チェック**: スロットIDが有効な範囲内かチェックします。

#### ページのシリアライズ

```py
    def to_bytes(self) -> bytes:
        """ページ全体をバイト列に変換（ディスクへの書き込み用）"""
        # スロット配列をページの末尾に書き込む
        slot_start = PAGE_SIZE - len(self.slots) * SLOT_SIZE
        for i, (offset, length) in enumerate(self.slots):
            slot_offset = slot_start + i * SLOT_SIZE
            struct.pack_into(">II", self.data, slot_offset, offset, length)
        
        return bytes(self.data)
```

**実装のポイント**:

1. **スロット配列の書き込み**: メモリ上では`self.slots`としてリストで管理していますが、ディスクに書き込む際はページの末尾に配置します。

2. **`struct.pack_into`の使用**: 既存の`bytearray`の特定位置に直接書き込むため、`struct.pack_into`を使用します。

#### ページのデシリアライズ

```py
    @classmethod
    def from_bytes(cls, data: bytes, page_id: int = 0) -> "Page":
        """バイト列からページを復元（ディスクからの読み込み用）
        
        Args:
            data: ページのバイト列（PAGE_SIZE長）
            page_id: ページID
            
        Returns:
            復元されたPageオブジェクト
        """
        page = cls(page_id)
        page.data = bytearray(data)
        
        # ヘッダーを読み込む
        page.header = PageHeader.from_bytes(data[:PAGE_HEADER_SIZE])
        
        # スロット配列を読み込む
        slot_count = page.header.slot_count
        slot_start = PAGE_SIZE - slot_count * SLOT_SIZE
        page.slots = []
        
        for i in range(slot_count):
            slot_offset = slot_start + i * SLOT_SIZE
            offset, length = struct.unpack_from(">II", data, slot_offset)
            page.slots.append((offset, length))
        
        return page
```

**実装のポイント**:

1. **ヘッダーから情報を取得**: ヘッダーからスロット数を取得し、それに基づいてスロット配列を読み込みます。

2. **スロット配列の復元**: ページの末尾からスロット配列を読み込み、`self.slots`リストに復元します。

### 3. HeapFile - ヒープファイルの管理

`HeapFile`クラスは、複数のページから構成されるヒープファイルを管理します。テーブルのデータを物理的に保存する役割を担います。

#### ヒープファイルの初期化

```py
    def __init__(self, file_path: Path):
        """ヒープファイルを初期化
        
        Args:
            file_path: ヒープファイルのパス
        """
        self.file_path = Path(file_path)
        self.page_count = 0
        
        # ファイルが存在する場合はページ数を計算
        if self.file_path.exists():
            file_size = self.file_path.stat().st_size
            self.page_count = file_size // PAGE_SIZE
```

**実装のポイント**:

1. **既存ファイルの検出**: ファイルが存在する場合、ファイルサイズからページ数を計算します。これにより、既存のデータを読み込むことができます。

#### ページの読み込み

```py
    def get_page(self, page_id: int) -> Optional[Page]:
        """ページを読み込む
        
        Args:
            page_id: ページID（0始まり）
            
        Returns:
            Pageオブジェクト（存在しない場合はNone）
        """
        if page_id >= self.page_count:
            return None
        
        with open(self.file_path, 'rb') as f:
            f.seek(page_id * PAGE_SIZE)
            page_data = f.read(PAGE_SIZE)
        
        if len(page_data) < PAGE_SIZE:
            return None
        
        return Page.from_bytes(page_data, page_id)
```

**実装のポイント**:

1. **ランダムアクセス**: `f.seek(page_id * PAGE_SIZE)`で、ページIDに応じた位置にシークします。固定長ページだからこそ、このようなランダムアクセスが可能です。

2. **エラーハンドリング**: ページが存在しない場合や、データが不完全な場合は`None`を返します。

#### ページの書き込み

```py
    def write_page(self, page: Page):
        """ページを書き込む
        
        Args:
            page: 書き込むPageオブジェクト
        """
        with open(self.file_path, 'r+b') as f:
            f.seek(page.page_id * PAGE_SIZE)
            f.write(page.to_bytes())
            f.flush()
            os.fsync(f.fileno())  # ディスクへの確実な書き込み
```

**実装のポイント**:

1. **`os.fsync()`の重要性**: `flush()`だけでは、OSのバッファに書き込まれるだけで、実際のディスクには書き込まれない可能性があります。`os.fsync()`を呼ぶことで、確実にディスクに書き込まれます。これは、システムクラッシュ時のデータ保護に重要です。

#### タプルの挿入

```py
    def insert_tuple(self, tuple_data: bytes) -> tuple[int, int]:
        """タプルを挿入
        
        Args:
            tuple_data: タプルのバイト列
            
        Returns:
            (page_id, slot_id) のタプル
        """
        # 既存のページに空きがあるか確認
        for page_id in range(self.page_count):
            page = self.get_page(page_id)
            if page and page.get_free_space() >= len(tuple_data) + 8:  # タプル + スロット
                slot_id = page.insert_tuple(tuple_data)
                if slot_id is not None:
                    self.write_page(page)
                    return (page_id, slot_id)
        
        # 既存ページに空きがない場合は新しいページを割り当て
        page = self.allocate_page()
        slot_id = page.insert_tuple(tuple_data)
        if slot_id is None:
            raise RuntimeError("タプルが大きすぎて1ページに収まりません")
        
        self.write_page(page)
        return (page.page_id, slot_id)
```

**実装のポイント**:

1. **空きスペースの探索**: 既存のページを順に確認し、空きがあるページにタプルを挿入します。これにより、ページの利用率が向上します。

2. **新しいページの割り当て**: 既存のページに空きがない場合、新しいページを割り当てます。`allocate_page()`が新しいページを作成し、`write_page()`でディスクに書き込みます。

3. **タプルIDの返却**: `(page_id, slot_id)`のタプルを返すことで、後でこのタプルを特定できます。これが、データベースの「行ID（RID: Record ID）」の基礎となります。

#### フルテーブルスキャン

```py
    def scan_tuples(self, schema: List[tuple[str, str]]) -> Iterator[HeapTuple]:
        """全タプルをスキャン（フルテーブルスキャン）
        
        Args:
            schema: スキーマ情報
            
        Yields:
            HeapTupleオブジェクト
        """
        for page_id in range(self.page_count):
            page = self.get_page(page_id)
            if page:
                for slot_id in range(page.header.slot_count):
                    tuple_data = page.get_tuple(slot_id)
                    if tuple_data:
                        tuple_obj = HeapTuple.from_bytes(tuple_data, schema)
                        tuple_obj.tuple_id = (page_id, slot_id)
                        yield tuple_obj
```

**実装のポイント**:

1. **イテレータパターン**: `yield`を使うことで、メモリ効率的にタプルを順次返します。全タプルを一度にメモリに読み込む必要がありません。

2. **二重ループ**: 外側のループでページを、内側のループでスロットを順に処理します。これが「フルテーブルスキャン」の実装です。

3. **タプルIDの設定**: 各タプルに`tuple_id`を設定することで、後でこのタプルを特定できるようにします。

## 実装の全体像：データの流れ

最後に、INSERT操作とSELECT操作のデータの流れを見てみましょう。

### INSERT操作の流れ

1. **タプルの作成**: `HeapTuple(values=[1, "alice"])`でタプルオブジェクトを作成
2. **シリアライズ**: `to_bytes()`でバイト列に変換
3. **ページへの挿入**: `HeapFile.insert_tuple()`が適切なページを見つけて挿入
4. **ディスクへの書き込み**: `write_page()`で`os.fsync()`まで実行して確実に書き込み

### SELECT操作の流れ

1. **ページの読み込み**: `get_page()`でページをディスクから読み込む
2. **タプルの取得**: `get_tuple()`でスロットIDからタプルを取得
3. **デシリアライズ**: `HeapTuple.from_bytes()`でバイト列からタプルオブジェクトに復元
4. **結果の返却**: イテレータとして順次返す

このように、ストレージ層は「メモリ上のデータ構造」と「ディスク上のバイト列」を橋渡しする役割を担っています。この基盤があれば、実行エンジンはデータの永続化を意識せずに、メモリ上のデータ構造として扱うことができます。

