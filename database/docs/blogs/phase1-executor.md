# フェーズ1: 実行エンジン - データベースの「実行者」を作る

## はじめに

こんにちは、古の老賢者です。前回はSQLパーサーについて語りましたが、今回はそのパーサーが生成したAST（抽象構文木）を実際に実行する「実行エンジン」について語りましょう。

パーサーが「通訳者」なら、実行エンジンは「実行者」です。通訳者が「何をすべきか」を理解したら、実行者が実際にそれを実行します。この2つが揃って初めて、データベースは動き始めるのです。

まるで、料理のレシピ（SQL）を読んで理解するのがパーサーで、実際に料理を作るのが実行エンジンのようなものですね。レシピを読むだけではお腹は満たされません。実際に調理して、美味しい料理（結果）を出す必要があります。

## 何をやるのか：フェーズ1の実行エンジンの役割

フェーズ1では、最小限の機能を持つ実行エンジンを実装します。具体的には、以下の3つの演算子を実装します：

### 1. Scan演算子 - テーブルスキャン

テーブルから全データを順番に読み込む演算子です。最も基本的な演算子で、他のすべての演算子の入力となります。

```python
scan = ScanOperator(heap_file, schema)
```

この演算子は、ヒープファイルから1行ずつタプル（行）を読み込み、次の演算子に渡します。フルテーブルスキャンとも呼ばれ、インデックスがない場合の唯一のデータアクセス方法です。

### 2. Filter演算子 - WHERE句のフィルタリング

条件に一致するタプルのみを通過させる演算子です。WHERE句の実装に使用されます。

```python
def predicate(tuple_obj: Tuple) -> bool:
    return tuple_obj.get_value(0) > 20

filter_op = FilterOperator(scan, predicate)
```

この演算子は、Scan演算子から受け取ったタプルを1つずつチェックし、条件に一致するものだけを次の演算子に渡します。条件に一致しないタプルは捨てられます。

### 3. Project演算子 - SELECT句の射影

指定されたカラムのみを選択する演算子です。SELECT句の実装に使用されます。

```python
project_op = ProjectOperator(filter_op, [0, 2], schema)  # 0番目と2番目のカラムのみ
```

この演算子は、入力タプルから必要なカラムだけを抽出し、新しいタプルを作成します。`SELECT name, age FROM users`のようなクエリでは、全カラムではなく、nameとageだけを選択します。

## なぜやるのか：実行エンジンの存在意義

### 1. ASTを実際の操作に変換する

パーサーが生成したASTは、あくまで「何をすべきか」を表現したデータ構造です。これを実際のデータ操作に変換するのが実行エンジンの役割です。

例えば、`SELECT name FROM users WHERE age > 20`というSQL文は、パーサーによって以下のようなASTに変換されます：

```python
SelectStatement(
    columns=["name"],
    table_name="users",
    where_clause=WhereClause(column="age", operator=">", value=20)
)
```

実行エンジンは、このASTを見て、以下のような演算子のパイプラインを構築します：

```
Project (nameを選択)
  └─ Filter (age > 20でフィルタ)
      └─ Scan (usersテーブルをスキャン)
```

そして、このパイプラインを実行することで、実際の結果を返します。

### 2. モジュール化された設計

実行エンジンは、各演算子を独立したモジュールとして実装します。これにより、以下の利点があります：

- **拡張性**: 新しい演算子（JOIN、GROUP BYなど）を追加しやすい
- **テスト容易性**: 各演算子を個別にテストできる
- **再利用性**: 同じ演算子を異なるクエリで再利用できる

### 3. メモリ効率の良い実行

Iteratorモデル（後述）を採用することで、全データをメモリに読み込むことなく、1行ずつ処理できます。これにより、大規模データにも対応できます。

## 歴史的な背景：クエリ実行モデルの進化

### 1970年代：全データ読み込み方式の問題

1970年代の初期のデータベースシステムでは、クエリを実行する際、以下のような問題がありました：

- **メモリ不足**: 全データをメモリに読み込む必要があり、大規模データに対応できない
- **演算子の組み合わせが困難**: 各演算子が独立しておらず、新しい演算子を追加するのが困難
- **メモリ効率の悪さ**: 中間結果を全てメモリに保持する必要がある
- **並列処理の困難**: 全データを読み込んでから処理するため、並列化が難しい

例えば、`SELECT name FROM users WHERE age > 20`というクエリを実行する場合、usersテーブルの全データをメモリに読み込んでから、フィルタリングと射影を行う必要がありました。テーブルが大きくなると、メモリ不足でエラーが発生してしまいます。

### 1980年代：ストリーミング処理の試み

1980年代になると、全データを読み込まずに、1行ずつ処理する「ストリーミング処理」のアプローチが試みられました。しかし、各演算子が独自の実装を持っていたため、以下の問題がありました：

- **演算子間の結合が複雑**: 各演算子が異なるインターフェースを持ち、組み合わせが困難
- **最適化の困難**: 演算子が密結合しているため、クエリ最適化が難しい
- **テストの困難**: 各演算子を個別にテストすることができない

### 1990年代：Iteratorモデル（Volcanoモデル）の誕生

1990年代にオレゴン大学のGoetz Graefeが「Volcanoモデル」を提案しました。このモデルは、以下の革新的なアイデアに基づいていました：

- **統一的なインターフェース**: すべての演算子が同じインターフェース（`open()`, `next()`, `close()`）を実装
- **遅延評価**: データが必要になった時点で、その時点で必要な分だけ処理
- **パイプライン処理**: 各演算子が独立しており、パイプラインのように接続できる

このモデルは、後に「Volcanoモデル」と呼ばれるようになりました。なぜなら、各演算子が`next()`メソッドを呼び出すたびに、データが「噴出」するように流れるからです。

Iteratorモデルの核心は、以下の3つのメソッドです：

1. `open()`: イテレータを初期化
2. `next()`: 次の要素を取得（データがなければ`None`を返す）
3. `close()`: イテレータを終了

このシンプルなインターフェースにより、以下のメリットが得られました：

- **メモリ効率**: 1行ずつ処理するため、大規模データにも対応できる
- **演算子の独立性**: 各演算子が独立しているため、新しい演算子を追加しやすい
- **テスト容易性**: 各演算子を個別にテストできる
- **最適化の容易さ**: 演算子の組み合わせを最適化しやすい

### 現代：Iteratorモデルの拡張

現代のデータベースシステムでは、Iteratorモデルをベースに、以下のような拡張が行われています：

- **PostgreSQL**: 実行エンジン全体がIteratorモデルを採用し、高度な最適化を実現
- **MySQL**: クエリ実行にIteratorモデルを使用し、パフォーマンスを向上
- **SQLite**: 簡易版のIteratorモデルを実装し、軽量性を実現

また、現代では以下のような進化も見られます：

- **ベクトル化実行**: 1行ずつではなく、複数行をまとめて処理（列指向データベース）
- **並列実行**: 複数のIteratorを並列に実行してパフォーマンスを向上
- **適応的実行**: 実行中に統計情報を収集し、実行計画を動的に変更

これらの実績により、Iteratorモデルは「実証済みのアーキテクチャ」として確立されています。フェーズ1では基本的なIteratorモデルを実装していますが、この基盤があれば、将来的に高度な最適化を追加することができます。

## 技術的な詳細：実行エンジンの実装

### 1. Iteratorインターフェース

すべての演算子が実装する基本インターフェースです。

```python
class Iterator(ABC):
    @abstractmethod
    def open(self):
        """イテレータを初期化"""
        pass
    
    @abstractmethod
    def next(self) -> Optional[Tuple]:
        """次のタプルを取得"""
        pass
    
    @abstractmethod
    def close(self):
        """イテレータを終了"""
        pass
```

このインターフェースにより、すべての演算子が統一的な方法で動作します。

### 2. Scan演算子の実装

Scan演算子は、ヒープファイルからタプルを読み込みます。

```python
class ScanOperator(Iterator):
    """テーブルスキャン演算子
    
    ヒープファイルから全タプルを順次読み込む演算子です。
    最も基本的な演算子で、他の演算子の入力となります。
    
    パフォーマンス:
    - フルテーブルスキャンは最もコストが高い操作の一つ
    - インデックスがない場合、必ずこの演算子が使用されます
    - 大規模データでは非常に遅くなるため、インデックスの重要性がわかります
    """
    
    def __init__(self, heap_file: HeapFile, schema: Schema):
        """スキャン演算子を初期化
        
        Args:
            heap_file: スキャンするヒープファイル
            schema: テーブルのスキーマ
        """
        self.heap_file = heap_file
        self.schema = schema
        self.iterator: Optional[Any] = None
    
    def open(self):
        """スキャンを開始"""
        self.iterator = self.heap_file.scan_tuples(self.schema.to_tuple_list())
    
    def next(self) -> Optional[Tuple]:
        """次のタプルを取得"""
        if self.iterator is None:
            return None
        
        try:
            heap_tuple = next(self.iterator)
            return Tuple(values=heap_tuple.values, schema=[col.name for col in self.schema.columns])
        except StopIteration:
            return None
    
    def close(self):
        """スキャンを終了"""
        self.iterator = None
```

### 3. Filter演算子の実装

Filter演算子は、条件に一致するタプルのみを通過させます。

```python
class FilterOperator(Iterator):
    """フィルタ演算子（WHERE句）
    
    条件に一致するタプルのみを通過させる演算子です。
    WHERE句の実装に使用されます。
    """
    
    def __init__(self, child: Iterator, predicate: Callable[[Tuple], bool]):
        """フィルタ演算子を初期化
        
        Args:
            child: 子イテレータ（入力）
            predicate: フィルタ条件（Tupleを受け取りboolを返す関数）
        """
        self.child = child
        self.predicate = predicate
    
    def open(self):
        """フィルタを開始"""
        self.child.open()
    
    def next(self) -> Optional[Tuple]:
        """条件に一致する次のタプルを取得"""
        while True:
            tuple_obj = self.child.next()
            if tuple_obj is None:
                return None
            
            if self.predicate(tuple_obj):
                return tuple_obj
    
    def close(self):
        """フィルタを終了"""
        self.child.close()
```

### 4. Project演算子の実装

Project演算子は、指定されたカラムのみを選択します。

```python
class ProjectOperator(Iterator):
    """射影演算子（SELECT句）
    
    指定されたカラムのみを選択する演算子です。
    SELECT句の実装に使用されます。
    """
    
    def __init__(self, child: Iterator, column_indices: List[int], schema: Schema):
        """射影演算子を初期化
        
        Args:
            child: 子イテレータ（入力）
            column_indices: 選択するカラムのインデックスリスト
            schema: 元のスキーマ
        """
        self.child = child
        self.column_indices = column_indices
        self.schema = schema
    
    def open(self):
        """射影を開始"""
        self.child.open()
    
    def next(self) -> Optional[Tuple]:
        """射影された次のタプルを取得"""
        tuple_obj = self.child.next()
        if tuple_obj is None:
            return None
        
        projected_values = [tuple_obj.get_value(i) for i in self.column_indices]
        projected_schema = [self.schema.columns[i].name for i in self.column_indices]
        
        return Tuple(values=projected_values, schema=projected_schema)
    
    def close(self):
        """射影を終了"""
        self.child.close()
```

### 5. 演算子の組み合わせ

実際のクエリ実行では、これらの演算子を組み合わせます。例えば、`SELECT name FROM users WHERE age > 20`というクエリは、以下のように実行されます：

```python
    def _execute_select(self, stmt: SelectStatement) -> List[List[Any]]:
        """SELECT文を実行
        
        Args:
            stmt: パースされたSELECTステートメント
            
        Returns:
            結果のリスト（各行は値のリスト）
        """
        # スキーマを取得
        schema = self.catalog.get_schema(stmt.table_name)
        if not schema:
            raise ValueError(f"テーブル '{stmt.table_name}' が存在しません")
        
        # ヒープファイルを取得
        heap_file = self._get_heap_file(stmt.table_name)
        if not heap_file:
            raise ValueError(f"テーブル '{stmt.table_name}' のヒープファイルが見つかりません")
        
        # スキャン演算子を作成
        scan = ScanOperator(heap_file, schema)
        
        # WHERE句がある場合はフィルタ演算子を追加
        iterator = scan
        if stmt.where_clause:
            def predicate(tuple_obj: ExecTuple) -> bool:
                col_index = schema.get_column_index(stmt.where_clause.column)
                if col_index is None:
                    return False
                
                value = tuple_obj.get_value(col_index)
                operator = stmt.where_clause.operator
                target_value = stmt.where_clause.value
                
                if operator == "=":
                    return value == target_value
                elif operator == ">":
                    return value > target_value
                elif operator == "<":
                    return value < target_value
                elif operator == ">=":
                    return value >= target_value
                elif operator == "<=":
                    return value <= target_value
                elif operator == "!=" or operator == "<>":
                    return value != target_value
                else:
                    raise ValueError(f"未対応の演算子: {operator}")
            
            filter_op = FilterOperator(scan, predicate)
            iterator = filter_op
        
        # SELECT句の処理（射影）
        if stmt.columns and stmt.columns != ["*"]:
            # 指定されたカラムのみを選択
            column_indices = []
            for col_name in stmt.columns:
                index = schema.get_column_index(col_name)
                if index is None:
                    raise ValueError(f"カラム '{col_name}' が存在しません")
                column_indices.append(index)
            
            project_op = ProjectOperator(iterator, column_indices, schema)
            iterator = project_op
        else:
            # SELECT * の場合は全カラム
            column_indices = list(range(len(schema.columns)))
        
        # クエリを実行
        results = []
        iterator.open()
        try:
            while True:
                tuple_obj = iterator.next()
                if tuple_obj is None:
                    break
                results.append(tuple_obj.values)
        finally:
            iterator.close()
        
        return results
```

## 実行の流れ：パイプライン処理

実行エンジンは、演算子をパイプラインとして実行します。以下の図は、`SELECT name FROM users WHERE age > 20`の実行フローを示しています：

```
Scan演算子
  ↓ (タプルを1つずつ)
Filter演算子 (age > 20でフィルタ)
  ↓ (条件に一致するタプルのみ)
Project演算子 (nameカラムのみ選択)
  ↓ (結果タプル)
結果セット
```

各演算子は、`next()`メソッドが呼ばれるたびに、1つのタプルを処理します。これにより、全データをメモリに読み込むことなく、ストリーミング処理が可能になります。

## 実装のポイント

### 1. リソース管理

各演算子は、`open()`でリソースを確保し、`close()`で解放します。これにより、メモリリークを防ぎます。

```python
iterator.open()
try:
    while True:
        tuple_obj = iterator.next()
        if tuple_obj is None:
            break
        # 処理
finally:
    iterator.close()  # 必ずリソースを解放
```

### 2. エラーハンドリング

各演算子は、不正な入力に対して適切なエラーメッセージを返す必要があります。例えば：

- 存在しないカラムを参照しようとした場合
- 型が一致しない場合
- 範囲外のインデックスにアクセスしようとした場合

### 3. 拡張性

フェーズ1では最小限の機能しか実装しませんが、将来的な拡張を考慮した設計にします。例えば：

- 新しい演算子（JOIN、GROUP BY、ORDER BY）を追加しやすい構造
- 演算子の組み合わせを柔軟に変更できる構造
- 実行計画の最適化に対応できる構造

