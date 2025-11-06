"""
Iteratorモデル（Volcanoモデル）

クエリ実行の基本となるIteratorパターンを実装します。
各演算子はIteratorインターフェースを実装し、パイプラインで実行されます。

Volcanoモデルの歴史:
- 1990年代にGoetz Graefeが提案したクエリ実行モデル
- 各演算子がnext()メソッドで1つのタプルを返す
- メモリ効率が良く、大規模データにも対応可能
- 現代のデータベースでも広く採用されている
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Any
from dataclasses import dataclass


@dataclass
class Tuple:
    """実行時のタプル（行）表現
    
    実行エンジン内で使用されるタプルです。
    ヒープタプルとは異なり、実行時の最適化を考慮した構造になっています。
    """
    values: List[Any]
    schema: Optional[List[str]] = None  # カラム名のリスト（デバッグ用）
    
    def get_value(self, column_index: int) -> Any:
        """インデックスで値を取得"""
        if column_index < 0 or column_index >= len(self.values):
            raise IndexError(f"カラムインデックス {column_index} が範囲外です")
        return self.values[column_index]
    
    def get_value_by_name(self, column_name: str, schema: List[str]) -> Optional[Any]:
        """カラム名で値を取得"""
        if column_name not in schema:
            return None
        index = schema.index(column_name)
        return self.get_value(index)


class Iterator(ABC):
    """Iteratorインターフェース
    
    すべての演算子が実装する基本インターフェースです。
    Volcanoモデルの核心となる部分です。
    """
    
    @abstractmethod
    def open(self):
        """イテレータを初期化
        
        リソースの確保や子イテレータの初期化を行います。
        """
        pass
    
    @abstractmethod
    def next(self) -> Optional[Tuple]:
        """次のタプルを取得
        
        Returns:
            次のTuple（これ以上ない場合はNone）
        """
        pass
    
    @abstractmethod
    def close(self):
        """イテレータを終了
        
        リソースの解放を行います。
        """
        pass
    
    def __iter__(self):
        """Pythonのイテレータプロトコルをサポート"""
        self.open()
        return self
    
    def __next__(self):
        """Pythonのイテレータプロトコルをサポート"""
        result = self.next()
        if result is None:
            self.close()
            raise StopIteration
        return result

