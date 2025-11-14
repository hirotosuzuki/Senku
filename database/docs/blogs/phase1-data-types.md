# フェーズ1: データ型 - データベースの「言語」を定義する

## はじめに

こんにちは、古の老賢者です。前回はテーブル管理について語りましたが、今回は「データ型」について語りましょう。

データ型は、データベースの「言語」です。どんな種類のデータを扱えるかを定義します。まるで、人間の言語に「名詞」「動詞」「形容詞」があるように、データベースにも「整数」「文字列」「浮動小数点数」などの型があります。

どんなに優れたストレージ層や実行エンジンがあっても、データ型がなければ、データを正しく解釈することができません。データ型は、データベースが「何を保存しているか」を理解するための基礎となるのです。

## 何をやるのか：フェーズ1のデータ型の役割

フェーズ1では、最小限の機能を持つデータ型システムを実装します。具体的には、以下の3つの基本型をサポートします：

### 1. INT - 整数型

32ビット（4バイト）の符号付き整数を表現します。範囲は-2,147,483,648から2,147,483,647までです。

```python
col = ColumnDefinition(name="id", data_type="INT")
```

INT型は、ID、カウント、年齢など、整数値が必要な場面で使用されます。

### 2. TEXT - 文字列型

可変長の文字列を表現します。UTF-8エンコーディングで保存されます。

```python
col = ColumnDefinition(name="name", data_type="TEXT")
```

TEXT型は、名前、説明、コメントなど、文字列データが必要な場面で使用されます。

### 3. FLOAT - 浮動小数点数型

64ビット（8バイト）の倍精度浮動小数点数を表現します。IEEE 754標準に準拠しています。

```python
col = ColumnDefinition(name="price", data_type="FLOAT")
```

FLOAT型は、価格、重量、温度など、小数点を含む数値が必要な場面で使用されます。

#### 余談：なぜ「TEXT」という名前なのか？

多くのデータベースシステムでは、文字列型を「VARCHAR」「CHAR」「TEXT」など、複数の型で表現します。しかし、フェーズ1では、シンプルさを優先して「TEXT」という1つの型のみをサポートしています。

- **VARCHAR**: 可変長文字列（最大長を指定可能）
- **CHAR**: 固定長文字列（常に指定した長さ）
- **TEXT**: 可変長文字列（長さ制限なし、または非常に大きい）

フェーズ1では、TEXT型で全ての文字列データを扱います。将来的には、VARCHARやCHARなどの型を追加することも可能です。

## なぜやるのか：データ型の存在意義

### 1. データの解釈

ディスクに保存されたバイト列だけでは、それが整数なのか文字列なのかわかりません。データ型があれば、バイト列を正しく解釈できます。

例えば、以下のバイト列を見てみましょう：
```
[0x00, 0x00, 0x00, 0x01]
```

これは、INT型として解釈すれば「1」ですが、TEXT型として解釈すれば意味のない文字列になってしまいます。データ型があれば、正しく「1」として解釈できます。

### 2. データの検証

INSERT操作の際に、値がスキーマに適合するかを検証できます。例えば、INT型のカラムに文字列を挿入しようとした場合、エラーを発生させることができます。

### 3. 効率的なストレージ

データ型がわかれば、最適な形式でデータを保存できます。INT型は4バイト、FLOAT型は8バイトと、固定長で保存できるため、効率的です。

### 4. 将来の拡張性

フェーズ1では最小限の型しかサポートしていませんが、この基盤があれば、将来的に以下のような型を追加することが容易になります：

- **DATE**: 日付型
- **TIMESTAMP**: タイムスタンプ型
- **BOOLEAN**: 真偽値型
- **BLOB**: バイナリデータ型
- **DECIMAL**: 固定小数点型（金額計算などに使用）

## 歴史的な背景：データ型システムの確立

### 1960年代：初期のデータベースシステム

1960年代の初期のデータベースシステムでは、データ型の概念がまだ明確ではありませんでした。データは単なるバイト列として扱われ、アプリケーション側で解釈する必要がありました。

### 1970年代：リレーショナルデータベースの誕生

1970年代にエドガー・コッドがリレーショナルデータベースの概念を提唱しました。コッドは、「データ型」をリレーショナルモデルの重要な要素として位置づけました。

### 1980年代：SQL標準の確立

1980年代になると、SQL標準が確立され、データ型も標準化されました。代表的な型は：

- **INTEGER**: 整数型
- **CHAR**: 固定長文字列
- **VARCHAR**: 可変長文字列
- **FLOAT**: 浮動小数点数
- **DATE**: 日付型

### 現代のデータベースでの採用

現代のデータベースシステムでは、より多くの型がサポートされています：

- **PostgreSQL**: 100種類以上のデータ型をサポート（INT、TEXT、FLOAT、DATE、TIMESTAMP、JSON、ARRAYなど）
- **MySQL**: 30種類以上のデータ型をサポート
- **SQLite**: 動的型付けを採用（型の概念が緩い）

これらの実績により、データ型システムは「実証済みのアーキテクチャ」として確立されています。

## 技術的な詳細：データ型の実装

### 1. データ型の定義

データ型は、`ColumnDefinition`クラスで文字列として定義されます：

```12:31:database/senku-db-python/core/catalog/schema.py
@dataclass
class ColumnDefinition:
    """カラム定義
    
    テーブルの1つのカラムを表現します。
    
    Attributes:
        name: カラム名
        data_type: データ型（"INT", "TEXT", "FLOAT"など）
        nullable: NULL値を許可するか（将来の拡張）
        default_value: デフォルト値（将来の拡張）
    """
    name: str
    data_type: str  # "INT", "TEXT", "FLOAT", etc.
    nullable: bool = True
    default_value: Optional[any] = None
    
    def __post_init__(self):
        """データ型を正規化（大文字に変換）"""
        self.data_type = self.data_type.upper()
```

`__post_init__`メソッドにより、データ型は自動的に大文字に変換されます。これにより、`"int"`、`"Int"`、`"INT"`など、どのような形式で指定しても、統一された形式で保存されます。

### 2. データ型の検証

INSERT操作の際に、値がスキーマに適合するかを検証します：

```91:122:database/senku-db-python/core/catalog/schema.py
    def validate_values(self, values: List[any]) -> bool:
        """値のリストがスキーマに適合するか検証
        
        Args:
            values: 値のリスト
            
        Returns:
            適合する場合はTrue
        """
        if len(values) != len(self.columns):
            return False
        
        # 型チェック（簡易版）
        for i, (value, col_def) in enumerate(zip(values, self.columns)):
            if value is None and not col_def.nullable:
                return False
            
            # 型チェック
            if value is not None:
                if col_def.data_type == "INT" and not isinstance(value, int):
                    try:
                        int(value)  # 変換可能かチェック
                    except (ValueError, TypeError):
                        return False
                elif col_def.data_type == "FLOAT" and not isinstance(value, (int, float)):
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        return False
                # TEXTは任意の値を文字列として扱える
        
        return True
```

**実装のポイント**:

1. **INT型の検証**: 値が`int`型であるか、または`int()`で変換可能かをチェックします。これにより、文字列の`"1"`も整数として扱えます。

2. **FLOAT型の検証**: 値が`int`または`float`型であるか、または`float()`で変換可能かをチェックします。これにより、整数値も浮動小数点数として扱えます。

3. **TEXT型の検証**: 任意の値を文字列として扱えるため、特別な検証は行いません。

### 3. データ型のシリアライズ

データをディスクに保存する際、メモリ上の値をバイト列に変換します：

```32:54:database/senku-db-python/core/storage/heap.py
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

1. **INT型**: `struct.pack(">i", value)`で4バイトの符号付き整数に変換します。`>`はビッグエンディアン（ネットワークバイトオーダー）を意味します。

2. **TEXT型**: まず文字列をUTF-8でエンコードし、その長さ（4バイト）を先頭に付けてから、データを追加します。これにより、可変長の文字列を正しく保存・復元できます。

3. **FLOAT型**: `struct.pack(">d", value)`で8バイトの倍精度浮動小数点数に変換します。

4. **ビッグエンディアン**: `>`を使用することで、異なるアーキテクチャ間でもデータの互換性が保たれます。

### 4. データ型のデシリアライズ

ディスクから読み込んだバイト列を、メモリ上の値に変換します：

```56:91:database/senku-db-python/core/storage/heap.py
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

3. **可変長データの復元**: TEXT型の場合、まず長さを読み込み、その長さ分だけデータを読み込んでからUTF-8デコードします。

4. **デフォルト動作**: 未知の型はTEXT型として扱います。これにより、将来新しい型を追加しても、既存のデータを壊さずに読み込めます。

## 実装のポイント

### 1. 型の正規化

データ型は自動的に大文字に変換されます。これにより、`"int"`、`"Int"`、`"INT"`など、どのような形式で指定しても、統一された形式で保存されます。

```29:31:database/senku-db-python/core/catalog/schema.py
    def __post_init__(self):
        """データ型を正規化（大文字に変換）"""
        self.data_type = self.data_type.upper()
```

### 2. ビッグエンディアン（ネットワークバイトオーダー）

データの保存には、ビッグエンディアンを使用します。これにより、異なるアーキテクチャ（x86、ARMなど）間でもデータの互換性が保たれます。

### 3. UTF-8エンコーディング

TEXT型の文字列は、UTF-8でエンコードされます。これにより、日本語や絵文字など、様々な文字を扱うことができます。

### 4. 可変長データの扱い

TEXT型は可変長なので、先に長さを記録してからデータを記録します。これにより、デシリアライズ時に正確に復元できます。

## 実装の全体像：データ型のデータの流れ

最後に、INSERT操作とSELECT操作でのデータ型の流れを見てみましょう。

### INSERT操作の流れ

1. **SQL文のパース**: `INSERT INTO users VALUES (1, "alice")`をパース
2. **値の検証**: スキーマに対して値のリストを検証（型チェック）
3. **タプルの作成**: 値のリストから`HeapTuple`オブジェクトを作成
4. **シリアライズ**: 各値を型に応じてバイト列に変換
   - INT型: 4バイトの整数
   - TEXT型: 長さ（4バイト）+ UTF-8エンコードされた文字列
   - FLOAT型: 8バイトの浮動小数点数
5. **ヒープファイルへの挿入**: バイト列をヒープファイルに挿入

### SELECT操作の流れ

1. **ページの読み込み**: ヒープファイルからページを読み込む
2. **タプルの取得**: スロットIDからタプルのバイト列を取得
3. **デシリアライズ**: スキーマ情報に基づいて、バイト列を値に変換
   - INT型: 4バイトから整数を復元
   - TEXT型: 長さを読み取り、その長さ分のデータをUTF-8デコード
   - FLOAT型: 8バイトから浮動小数点数を復元
4. **結果の返却**: 復元された値を返す

このように、データ型は「メモリ上の値」と「ディスク上のバイト列」を橋渡しする役割を担っています。この基盤があれば、実行エンジンはデータの型を意識せずに、メモリ上の値として扱うことができます。

## まとめ

データ型は、データベースの「言語」として、以下の役割を担います：

1. **データの解釈**: バイト列を正しい値に変換
2. **データの検証**: 値がスキーマに適合するかを検証
3. **効率的なストレージ**: 最適な形式でデータを保存
4. **将来の拡張性**: 新しい型を追加する基盤

フェーズ1では、INT、TEXT、FLOATの3つの基本型のみをサポートしていますが、この基盤があれば、将来的に様々な型を追加することができます。次回は、実行エンジンについて詳しく見ていきましょう。

