"""
クエリ実行演算子

Iteratorモデルに基づく各種演算子を実装します。
各演算子は独立して動作し、パイプラインで組み合わせることができます。

演算子の種類:
- Scan: テーブルスキャン（フルテーブルスキャン）
- Filter: WHERE句によるフィルタリング
- Project: SELECT句による射影
- Join: テーブル結合
- Aggregate: 集約関数（COUNT, SUM等）
- Sort: ソート
"""

from typing import Optional, List, Callable, Any

from .iterator import Iterator, Tuple
from ..storage.heap import HeapFile
from ..catalog.schema import Schema


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


class JoinOperator(Iterator):
    """結合演算子（JOIN）
    
    2つのテーブルを結合する演算子です。
    現在はNested Loop Joinのみを実装しています。
    
    結合アルゴリズムの種類:
    - Nested Loop Join: 最もシンプルだが、大規模データでは遅い
    - Hash Join: ハッシュテーブルを使用（将来実装）
    - Sort-Merge Join: ソート済みデータのマージ（将来実装）
    """
    
    def __init__(self, left: Iterator, right: Iterator, 
                 left_key_index: int, right_key_index: int):
        """結合演算子を初期化
        
        Args:
            left: 左側のイテレータ
            right: 右側のイテレータ
            left_key_index: 左側の結合キーのカラムインデックス
            right_key_index: 右側の結合キーのカラムインデックス
        """
        self.left = left
        self.right = right
        self.left_key_index = left_key_index
        self.right_key_index = right_key_index
        self.current_left: Optional[Tuple] = None
        self.right_reset_needed = False
    
    def open(self):
        """結合を開始"""
        self.left.open()
        self.right.open()
        self.current_left = self.left.next()
        self.right_reset_needed = False
    
    def next(self) -> Optional[Tuple]:
        """結合された次のタプルを取得"""
        if self.current_left is None:
            return None
        
        while True:
            right_tuple = self.right.next()
            
            if right_tuple is None:
                # 右側が終了したら、左側を進める
                self.current_left = self.left.next()
                if self.current_left is None:
                    return None
                
                # 右側をリセット（簡易実装: 実際はキャッシュが必要）
                self.right.close()
                self.right.open()
                right_tuple = self.right.next()
            
            if right_tuple is None:
                return None
            
            # 結合条件をチェック
            left_key = self.current_left.get_value(self.left_key_index)
            right_key = right_tuple.get_value(self.right_key_index)
            
            if left_key == right_key:
                # 結合成功: 両方のタプルを結合
                combined_values = self.current_left.values + right_tuple.values
                return Tuple(values=combined_values)
    
    def close(self):
        """結合を終了"""
        self.left.close()
        self.right.close()


class AggregateOperator(Iterator):
    """集約演算子（GROUP BY, COUNT, SUM等）
    
    集約関数を実行する演算子です。
    現在は簡易実装で、COUNTのみをサポートしています。
    
    集約関数の種類:
    - COUNT: 行数のカウント
    - SUM: 合計
    - AVG: 平均
    - MAX/MIN: 最大値/最小値
    """
    
    def __init__(self, child: Iterator, aggregate_func: str, column_index: Optional[int] = None):
        """集約演算子を初期化
        
        Args:
            child: 子イテレータ（入力）
            aggregate_func: 集約関数名（"COUNT", "SUM", "AVG"等）
            column_index: 集約対象のカラムインデックス（COUNTの場合はNone）
        """
        self.child = child
        self.aggregate_func = aggregate_func.upper()
        self.column_index = column_index
        self.result: Optional[Tuple] = None
        self.computed = False
    
    def open(self):
        """集約を開始"""
        self.child.open()
        self.computed = False
    
    def next(self) -> Optional[Tuple]:
        """集約結果を取得（1回のみ）"""
        if self.computed:
            return None
        
        if self.aggregate_func == "COUNT":
            count = 0
            while True:
                tuple_obj = self.child.next()
                if tuple_obj is None:
                    break
                count += 1
            self.result = Tuple(values=[count])
        elif self.aggregate_func == "SUM" and self.column_index is not None:
            total = 0
            while True:
                tuple_obj = self.child.next()
                if tuple_obj is None:
                    break
                value = tuple_obj.get_value(self.column_index)
                if isinstance(value, (int, float)):
                    total += value
            self.result = Tuple(values=[total])
        else:
            raise ValueError(f"未対応の集約関数: {self.aggregate_func}")
        
        self.computed = True
        return self.result
    
    def close(self):
        """集約を終了"""
        self.child.close()


class SortOperator(Iterator):
    """ソート演算子（ORDER BY）
    
    タプルをソートする演算子です。
    現在はメモリ内ソートのみを実装しています（小規模データ用）。
    
    大規模データへの対応:
    - 外部ソート（External Sort）が必要
    - マージソートアルゴリズムを使用
    - ディスクへの一時ファイルの書き込みが必要
    """
    
    def __init__(self, child: Iterator, sort_key_index: int, ascending: bool = True):
        """ソート演算子を初期化
        
        Args:
            child: 子イテレータ（入力）
            sort_key_index: ソートキーのカラムインデックス
            ascending: 昇順かどうか
        """
        self.child = child
        self.sort_key_index = sort_key_index
        self.ascending = ascending
        self.sorted_tuples: List[Tuple] = []
        self.current_index = 0
    
    def open(self):
        """ソートを開始"""
        self.child.open()
        
        # 全タプルを読み込んでソート（メモリ内ソート）
        tuples = []
        while True:
            tuple_obj = self.child.next()
            if tuple_obj is None:
                break
            tuples.append(tuple_obj)
        
        # ソート実行
        self.sorted_tuples = sorted(
            tuples,
            key=lambda t: t.get_value(self.sort_key_index),
            reverse=not self.ascending
        )
        self.current_index = 0
    
    def next(self) -> Optional[Tuple]:
        """ソートされた次のタプルを取得"""
        if self.current_index >= len(self.sorted_tuples):
            return None
        
        result = self.sorted_tuples[self.current_index]
        self.current_index += 1
        return result
    
    def close(self):
        """ソートを終了"""
        self.child.close()
        self.sorted_tuples = []
        self.current_index = 0

