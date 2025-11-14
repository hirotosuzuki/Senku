# データ型設計の比較：Enum vs Dataclass

## はじめに

データ型の実装方法として、`Enum`と`dataclass`（基底クラス + 個別クラス）の2つのアプローチがあります。それぞれのメリット・デメリットを比較し、最適な設計を検討します。

## アプローチ1: Enumベースの実装

### 実装例

```python
from enum import Enum

class DataType(Enum):
    INT = "INT"
    TEXT = "TEXT"
    FLOAT = "FLOAT"
    
    def serialize(self, value: Any) -> bytes:
        if self == DataType.INT:
            return struct.pack(">i", value)
        elif self == DataType.TEXT:
            # ...
        elif self == DataType.FLOAT:
            # ...
```

### メリット

1. **シンプル**: 実装が簡潔で理解しやすい
2. **型安全性**: Enumにより、存在しない型は実行時に検出可能
3. **IDE補完**: `DataType.INT`のように補完が効く
4. **比較が容易**: `if data_type == DataType.INT:`のように比較できる
5. **シングルトン**: 各Enum値は1つのインスタンスのみ（メモリ効率が良い）
6. **標準ライブラリ**: Python標準の`enum`モジュールを使用

### デメリット

1. **分岐が多い**: `if self == DataType.INT:`のような分岐が各メソッドに必要
2. **拡張性**: 新しい型を追加する際、すべてのメソッドに分岐を追加する必要がある
3. **型ごとの属性**: 各型の特性（サイズ、エンコーディングなど）を保持しにくい
4. **コードの重複**: 似たような分岐が複数のメソッドに散在

### コード例

```python
def serialize(self, value: Any) -> bytes:
    if self == DataType.INT:
        return struct.pack(">i", value)
    elif self == DataType.TEXT:
        encoded = value.encode('utf-8')
        return struct.pack(">I", len(encoded)) + encoded
    elif self == DataType.FLOAT:
        return struct.pack(">d", float(value))
    else:
        raise ValueError(f"未実装のデータ型: {self}")
```

## アプローチ2: Dataclassベースの実装（基底クラス + 個別クラス）

### 実装例

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

class DataType(ABC):
    @abstractmethod
    def serialize(self, value: Any) -> bytes:
        pass

@dataclass(frozen=True)
class IntType(DataType):
    def serialize(self, value: Any) -> bytes:
        return struct.pack(">i", value)
```

### メリット

1. **ポリモーフィズム**: 分岐なしで型ごとの処理を実行できる
2. **拡張性**: 新しい型を追加する際、新しいクラスを追加するだけ
3. **型ごとの属性**: 各型の特性（サイズ、エンコーディングなど）を保持できる
4. **コードの整理**: 型ごとのロジックが1つのクラスに集約される
5. **テスト容易性**: 各型を個別にテストできる
6. **将来の拡張**: 型ごとに異なるパラメータ（例：VARCHARの最大長）を持たせやすい

### デメリット

1. **複雑性**: 実装がやや複雑になる
2. **メモリ使用**: 各型が個別のインスタンス（ただし、`frozen=True`でシングルトン化可能）
3. **比較**: `isinstance()`や`type()`を使った比較が必要（ただし、`==`でも比較可能）
4. **シングルトン管理**: インスタンスの管理が必要（`INT = IntType()`など）

### コード例

```python
def serialize(self, value: Any) -> bytes:
    # 分岐なし！ポリモーフィズムで自動的に適切なメソッドが呼ばれる
    return self.data_type.serialize(value)
```

## 比較表

| 観点 | Enum | Dataclass |
|------|------|-----------|
| **シンプルさ** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **拡張性** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **型安全性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **コードの整理** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **パフォーマンス** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **テスト容易性** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **将来の拡張** | ⭐⭐ | ⭐⭐⭐⭐⭐ |

## 実際の使用例での比較

### Enumの場合

```python
# 使用例
col = ColumnDefinition(name="id", data_type=DataType.INT)

# シリアライズ
if col.data_type == DataType.INT:
    data = struct.pack(">i", value)
elif col.data_type == DataType.TEXT:
    # ...
```

### Dataclassの場合

```python
# 使用例
col = ColumnDefinition(name="id", data_type=INT)  # または IntType()

# シリアライズ（分岐なし！）
data = col.data_type.serialize(value)
```

## 推奨設計：ハイブリッドアプローチ

両方のアプローチの良い点を組み合わせた「ハイブリッドアプローチ」を推奨します。

### 設計方針

1. **基底クラス + 個別クラス**: ポリモーフィズムを活用
2. **シングルトンインスタンス**: `INT = IntType()`のように定数として提供
3. **Enum風の使用感**: `DataType.INT`のように使える（実際は`INT`インスタンス）
4. **from_string()メソッド**: 文字列から型を取得（既存コードとの互換性）

### 実装例

```python
class DataType(ABC):
    @abstractmethod
    def serialize(self, value: Any) -> bytes:
        pass
    
    @classmethod
    def from_string(cls, value: str) -> "DataType":
        type_map = {
            "INT": INT,
            "TEXT": TEXT,
            "FLOAT": FLOAT,
        }
        return type_map[value.upper()]

@dataclass(frozen=True)
class IntType(DataType):
    def serialize(self, value: Any) -> bytes:
        return struct.pack(">i", value)

# シングルトンインスタンス
INT = IntType()
TEXT = TextType()
FLOAT = FloatType()
```

### 使用例

```python
# 方法1: シングルトンインスタンスを直接使用
col = ColumnDefinition(name="id", data_type=INT)

# 方法2: 文字列から取得（既存コードとの互換性）
col = ColumnDefinition(name="id", data_type=DataType.from_string("INT"))

# 方法3: クラスから直接インスタンス化（柔軟性）
col = ColumnDefinition(name="id", data_type=IntType())
```

## 結論

### フェーズ1（現在）の推奨

**Dataclassベースの実装（ハイブリッドアプローチ）**を推奨します。

理由：
1. **将来の拡張性**: DATE、TIMESTAMP、VARCHAR（最大長付き）など、型ごとに異なるパラメータが必要になる可能性が高い
2. **コードの整理**: 型ごとのロジックが1つのクラスに集約され、保守しやすい
3. **ポリモーフィズム**: 分岐なしで処理できるため、コードが簡潔になる
4. **テスト容易性**: 各型を個別にテストできる

### Enumが適している場合

以下の場合はEnumが適しています：
- 型の数が少なく、今後も大きく増えない
- 型ごとに異なるパラメータが不要
- シンプルさを最優先する

### 実装の注意点

1. **シングルトン管理**: `INT = IntType()`のように定数として提供し、メモリ効率を保つ
2. **後方互換性**: `from_string()`メソッドで文字列からの変換をサポート
3. **比較**: `==`演算子で比較できるようにする（`frozen=True`により自動的に実装される）
4. **型チェック**: `isinstance(data_type, IntType)`のように型チェックも可能

## まとめ

EnumとDataclassの両方にメリットがありますが、データベースシステムのような拡張性が重要なシステムでは、**Dataclassベースの実装（ハイブリッドアプローチ）**が適しています。

特に、将来的に以下のような拡張が予想される場合：
- VARCHAR(255)のようにパラメータ付きの型
- DATE、TIMESTAMPなどの複雑な型
- カスタム型の追加

これらの拡張を考慮すると、Dataclassベースの実装の方が柔軟性が高く、保守しやすいコードになります。

