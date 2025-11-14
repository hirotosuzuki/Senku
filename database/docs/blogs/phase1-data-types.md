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
from core.types import INT

col = ColumnDefinition(name="id", data_type=INT)
```

INT型は、ID、カウント、年齢など、整数値が必要な場面で使用されます。

### 2. TEXT - 文字列型

可変長の文字列を表現します。UTF-8エンコーディングで保存されます。

```python
from core.types import TEXT

col = ColumnDefinition(name="name", data_type=TEXT)
```

TEXT型は、名前、説明、コメントなど、文字列データが必要な場面で使用されます。

### 3. FLOAT - 浮動小数点数型

64ビット（8バイト）の倍精度浮動小数点数を表現します。IEEE 754標準に準拠しています。

```python
from core.types import FLOAT

col = ColumnDefinition(name="price", data_type=FLOAT)
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

## 歴史的な背景：データ型とストレージ効率の進化

### 1960年代：型なしの時代とその問題

1960年代の初期のデータベースシステムでは、データ型の概念がまだ明確ではありませんでした。データは単なるバイト列として扱われ、アプリケーション側で解釈する必要がありました。

この時代、同じバイト列でも、アプリケーションによって異なる解釈がされることがありました。例えば、`[0x41, 0x42, 0x43]`というバイト列は、文字列として解釈すれば`"ABC"`ですが、整数として解釈すれば`4,276,995`になってしまいます。この曖昧さが、多くのバグの原因となりました。

### 1970年代：型安全性の重要性が認識される

1970年代になると、プログラミング言語の世界で「型安全性」の重要性が認識されるようになりました。Pascal（1970年）やC（1972年）などの言語が、コンパイル時に型チェックを行うようになりました。

データベースの世界でも、同じ動きが起こりました。データ型を明示的に定義することで、以下のメリットが得られることがわかりました：

1. **ストレージ効率**: 型がわかれば、最適なサイズで保存できる（整数は4バイト、浮動小数点数は8バイトなど）
2. **検証の自動化**: INSERT時に型チェックを自動で行える
3. **エラーの早期発見**: 実行前に型の不一致を検出できる

### 1980年代：エンコーディングの標準化と可変長データ

1980年代になると、文字列の扱いが大きな課題となりました。ASCII（7ビット、128文字）では不十分で、各国の文字を扱う必要がありました。

この時代、以下のような進化がありました：

- **固定長 vs 可変長**: CHAR（固定長）とVARCHAR（可変長）の使い分けが重要になった
- **エンコーディングの多様化**: ASCII、EBCDIC、各国の文字コード（Shift-JIS、EUC-JPなど）が混在
- **可変長データの効率的な保存**: 長さ情報を先頭に付ける方式が標準化された

可変長データを扱う際、先に長さを記録してからデータを記録する方式が確立されました。これにより、デシリアライズ時に正確に復元できるようになりました。

### 1990年代：UTF-8の登場と国際化

1990年代になると、UTF-8エンコーディングが登場しました。UTF-8は、以下の特徴を持っていました：

- **後方互換性**: ASCII文字はそのまま使用できる
- **可変長**: 1文字が1〜4バイト（必要に応じて）
- **効率性**: 英語圏の文字は1バイト、日本語は3バイトと、使用頻度に応じて最適化

現代のデータベースシステムでは、UTF-8が標準となっています。これにより、世界中の文字を統一的な方法で扱えるようになりました。

### 現代：型システムの多様化

現代のデータベースシステムでは、以下のような進化が起こっています：

- **PostgreSQL**: 100種類以上のデータ型をサポート（INT、TEXT、FLOAT、DATE、TIMESTAMP、JSON、ARRAYなど）
- **MySQL**: 30種類以上のデータ型をサポート
- **SQLite**: 動的型付けを採用（型の概念が緩い）

また、型システムの設計思想も多様化しています：

- **静的型付け**: PostgreSQL、MySQLのように、スキーマ定義時に型を固定
- **動的型付け**: SQLiteのように、実行時に型を決定
- **型推論**: 一部のNoSQLデータベースでは、値から型を自動推論

これらの実績により、データ型システムは「実証済みのアーキテクチャ」として確立されています。しかし、どのアプローチを選ぶかは、システムの要件によって異なります。

## 技術的な詳細：データ型の実装

### 1. データ型の定義

データ型は、基底クラス`DataType`を継承した個別のクラスとして定義されます。各データ型（`IntType`、`TextType`、`FloatType`）は、`@dataclass(frozen=True)`で定義され、ポリモーフィズムを活用します。

```python
@dataclass
class ColumnDefinition:
    """カラム定義
    
    テーブルの1つのカラムを表現します。
    
    Attributes:
        name: カラム名
        data_type: データ型（DataTypeインスタンス）
        nullable: NULL値を許可するか（将来の拡張）
        default_value: デフォルト値（将来の拡張）
    """
    name: str
    data_type: DataType
    nullable: bool = True
    default_value: Optional[any] = None
    
    def __post_init__(self):
        """データ型の型チェック"""
        if not isinstance(self.data_type, DataType):
            raise TypeError(
                f"data_typeはDataTypeインスタンスである必要があります。"
                f"文字列の場合はDataType.from_string()を使用してください。"
                f"受け取った値: {self.data_type} (type: {type(self.data_type)})"
            )
    
    @property
    def data_type_str(self) -> str:
        """データ型を文字列として取得"""
        return str(self.data_type)
```

`ColumnDefinition`は、`DataType`インスタンスのみを受け入れます。文字列を渡すと`TypeError`が発生します。これにより、型安全性が向上し、実行時エラーを防ぐことができます。

データ型は、`core/types/`ディレクトリに定義されており、シングルトンインスタンス（`INT`、`TEXT`、`FLOAT`）として提供されます。

### 2. データ型の検証

INSERT操作の際に、値がスキーマに適合するかを検証します。検証ロジックは、各データ型クラスの`validate()`メソッドに実装されています：

```python
def validate_values(self, values: List[any]) -> bool:
    """値のリストがスキーマに適合するか検証
    
    Args:
        values: 値のリスト
        
    Returns:
        適合する場合はTrue
    """
    if len(values) != len(self.columns):
        return False
    
    # 型チェック
    for i, (value, col_def) in enumerate(zip(values, self.columns)):
        if value is None and not col_def.nullable:
            return False
        
        # 型チェック（DataType Enumのvalidateメソッドを使用）
        if value is not None:
            if not col_def.data_type.validate(value):
                return False
    
    return True
```

各データ型クラスは、`validate()`メソッドを実装しています：

```python
def validate(self, value: Any) -> bool:
    """値が整数として有効か検証"""
    if value is None:
        return True  # NULL値は許可
    
    if isinstance(value, int):
        return True
    
    try:
        int(value)  # 変換可能かチェック
        return True
    except (ValueError, TypeError):
        return False
```

**実装のポイント**:

1. **ポリモーフィズム**: `col_def.data_type.validate(value)`のように、型ごとの処理を分岐なしで実行できます。各データ型クラスが独自の`validate()`メソッドを実装しているため、コードが簡潔になります。

2. **INT型の検証**: 値が`int`型であるか、または`int()`で変換可能かをチェックします。これにより、文字列の`"1"`も整数として扱えます。

3. **FLOAT型の検証**: 値が`int`または`float`型であるか、または`float()`で変換可能かをチェックします。これにより、整数値も浮動小数点数として扱えます。

4. **TEXT型の検証**: 任意の値を文字列として扱えるため、常に`True`を返します。

### 3. データ型のシリアライズ

データをディスクに保存する際、メモリ上の値をバイト列に変換します。シリアライズロジックは、各データ型クラスの`serialize()`メソッドに実装されています：

```python
def to_bytes(self, schema: Optional[List[tuple[str, str]]] = None) -> bytes:
    """タプルをバイト列にシリアライズ
    
    簡易的な実装: 各値を型に応じてシリアライズ
    将来的にはより効率的なフォーマット（列指向など）を検討
    
    Args:
        schema: スキーマ情報 [(column_name, data_type), ...]
               指定されない場合は、値の型から推論
    """
    parts = []
    
    if schema:
        # スキーマが指定されている場合は、それを使用
        for (col_name, col_type_str), value in zip(schema, self.values):
            col_type = DataType.from_string(col_type_str)
            parts.append(col_type.serialize(value))
    else:
        # スキーマが指定されていない場合は、値の型から推論（後方互換性）
        for value in self.values:
            if isinstance(value, int):
                parts.append(INT.serialize(value))
            elif isinstance(value, str):
                parts.append(TEXT.serialize(value))
            elif isinstance(value, float):
                parts.append(FLOAT.serialize(value))
            else:
                # その他の型は文字列として扱う
                parts.append(TEXT.serialize(str(value)))
    
    return b''.join(parts)
```

各データ型クラスは、`serialize()`メソッドを実装しています：

```python
def serialize(self, value: Any) -> bytes:
    """整数を4バイトのバイト列にシリアライズ"""
    if not isinstance(value, int):
        raise TypeError(f"INT型には整数が必要です: {type(value)}")
    return struct.pack(">i", value)  # 4バイト整数（ビッグエンディアン）
```

**実装のポイント**:

1. **ポリモーフィズム**: `col_type.serialize(value)`のように、型ごとの処理を分岐なしで実行できます。各データ型クラスが独自の`serialize()`メソッドを実装しているため、コードが簡潔になります。

2. **INT型**: `struct.pack(">i", value)`で4バイトの符号付き整数に変換します。`>`はビッグエンディアン（ネットワークバイトオーダー）を意味します。

3. **TEXT型**: まず文字列をUTF-8でエンコードし、その長さ（4バイト）を先頭に付けてから、データを追加します。これにより、可変長の文字列を正しく保存・復元できます。

4. **FLOAT型**: `struct.pack(">d", value)`で8バイトの倍精度浮動小数点数に変換します。

5. **ビッグエンディアン**: `>`を使用することで、異なるアーキテクチャ間でもデータの互換性が保たれます。

### 4. データ型のデシリアライズ

ディスクから読み込んだバイト列を、メモリ上の値に変換します。デシリアライズロジックは、各データ型クラスの`deserialize()`メソッドに実装されています：

```python
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
    
    for col_name, col_type_str in schema:
        try:
            col_type = DataType.from_string(col_type_str)
            value, offset = col_type.deserialize(data, offset)
            values.append(value)
        except ValueError:
            # 未知の型はTEXTとして扱う（後方互換性）
            value, offset = TEXT.deserialize(data, offset)
            values.append(value)
    
    return cls(values=values)
```

各データ型クラスは、`deserialize()`メソッドを実装しています：

```python
def deserialize(self, data: bytes, offset: int) -> tuple[int, int]:
    """バイト列から整数を復元"""
    value = struct.unpack_from(">i", data, offset)[0]
    return value, offset + 4
```

**実装のポイント**:

1. **ポリモーフィズム**: `col_type.deserialize(data, offset)`のように、型ごとの処理を分岐なしで実行できます。各データ型クラスが独自の`deserialize()`メソッドを実装しているため、コードが簡潔になります。

2. **スキーマ情報の必要性**: デシリアライズには、各カラムの型情報（スキーマ）が必要です。型がわからなければ、バイト列を正しく解釈できません。

3. **オフセット管理**: `deserialize()`メソッドは、`(値, 次のオフセット)`のタプルを返します。これにより、可変長データも正しく処理できます。

4. **可変長データの復元**: TEXT型の場合、まず長さを読み込み、その長さ分だけデータを読み込んでからUTF-8デコードします。

5. **デフォルト動作**: 未知の型はTEXT型として扱います。これにより、将来新しい型を追加しても、既存のデータを壊さずに読み込めます。

## 実装のポイント

### 1. Dataclassベースの実装

データ型は、基底クラス`DataType`を継承した個別のクラスとして定義されます。これにより、ポリモーフィズムを活用し、型ごとの処理を分岐なしで実行できます。

```python
@dataclass(frozen=True)
class IntType(DataType):
    """整数型（32ビット符号付き整数）
    
    範囲: -2,147,483,648 から 2,147,483,647
    サイズ: 4バイト（固定長）
    """
    
    @property
    def name(self) -> str:
        return "INT"
    
    def serialize(self, value: Any) -> bytes:
        """整数を4バイトのバイト列にシリアライズ"""
        if not isinstance(value, int):
            raise TypeError(f"INT型には整数が必要です: {type(value)}")
        return struct.pack(">i", value)  # 4バイト整数（ビッグエンディアン）
    
    def deserialize(self, data: bytes, offset: int) -> tuple[int, int]:
        """バイト列から整数を復元"""
        value = struct.unpack_from(">i", data, offset)[0]
        return value, offset + 4
    
    def validate(self, value: Any) -> bool:
        """値が整数として有効か検証"""
        if value is None:
            return True  # NULL値は許可
        
        if isinstance(value, int):
            return True
        
        try:
            int(value)  # 変換可能かチェック
            return True
        except (ValueError, TypeError):
            return False
```

`@dataclass(frozen=True)`により、各データ型インスタンスは不変で、シングルトンとして使用できます。`INT`、`TEXT`、`FLOAT`という定数として提供され、メモリ効率も良いです。

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

