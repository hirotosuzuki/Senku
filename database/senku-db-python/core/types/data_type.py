"""
データ型の定義

各データ型を個別のクラスとして定義します。
基底クラス`DataType`を継承することで、ポリモーフィズムを活用します。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
import struct


class DataType(ABC):
    """データ型の基底クラス
    
    各データ型はこのクラスを継承して実装します。
    ポリモーフィズムにより、型ごとの処理を分岐なしで実行できます。
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """データ型の名前（"INT", "TEXT", "FLOAT"など）"""
        pass
    
    def __str__(self) -> str:
        """文字列表現を返す（シリアライズ用）"""
        return self.name
    
    @abstractmethod
    def serialize(self, value: Any) -> bytes:
        """値をバイト列にシリアライズ
        
        Args:
            value: シリアライズする値
            
        Returns:
            バイト列
        """
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes, offset: int) -> tuple[Any, int]:
        """バイト列から値をデシリアライズ
        
        Args:
            data: バイト列
            offset: 読み込み開始位置
            
        Returns:
            (値, 次のオフセット) のタプル
        """
        pass
    
    @abstractmethod
    def validate(self, value: Any) -> bool:
        """値がこのデータ型に適合するか検証
        
        Args:
            value: 検証する値
            
        Returns:
            適合する場合はTrue
        """
        pass


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


@dataclass(frozen=True)
class TextType(DataType):
    """文字列型（可変長、UTF-8エンコーディング）
    
    サイズ: 可変長（長さ + データ）
    エンコーディング: UTF-8
    """
    
    @property
    def name(self) -> str:
        return "TEXT"
    
    def serialize(self, value: Any) -> bytes:
        """文字列をバイト列にシリアライズ（長さ + UTF-8エンコードされたデータ）"""
        if not isinstance(value, str):
            value = str(value)  # 文字列に変換
        
        encoded = value.encode('utf-8')
        return struct.pack(">I", len(encoded)) + encoded  # 長さ（4バイト）+ データ
    
    def deserialize(self, data: bytes, offset: int) -> tuple[str, int]:
        """バイト列から文字列を復元"""
        length = struct.unpack_from(">I", data, offset)[0]
        offset += 4
        value = data[offset:offset + length].decode('utf-8')
        return value, offset + length
    
    def validate(self, value: Any) -> bool:
        """値が文字列として有効か検証（任意の値を文字列として扱える）"""
        return True  # 任意の値を文字列として扱える


@dataclass(frozen=True)
class FloatType(DataType):
    """浮動小数点数型（64ビット倍精度浮動小数点数）
    
    範囲: IEEE 754標準に準拠
    サイズ: 8バイト（固定長）
    """
    
    @property
    def name(self) -> str:
        return "FLOAT"
    
    def serialize(self, value: Any) -> bytes:
        """浮動小数点数を8バイトのバイト列にシリアライズ"""
        if not isinstance(value, (int, float)):
            raise TypeError(f"FLOAT型には数値が必要です: {type(value)}")
        return struct.pack(">d", float(value))  # 8バイト浮動小数点数（ビッグエンディアン）
    
    def deserialize(self, data: bytes, offset: int) -> tuple[float, int]:
        """バイト列から浮動小数点数を復元"""
        value = struct.unpack_from(">d", data, offset)[0]
        return value, offset + 8
    
    def validate(self, value: Any) -> bool:
        """値が浮動小数点数として有効か検証"""
        if value is None:
            return True  # NULL値は許可
        
        if isinstance(value, (int, float)):
            return True
        
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False


# 型のインスタンス（シングルトン的な使用）
# frozen=Trueにより、これらのインスタンスは不変で、同一性が保証される
INT = IntType()
TEXT = TextType()
FLOAT = FloatType()

# 型名から型インスタンスへのマッピング（シングルトン）
_TYPE_REGISTRY = {
    "INT": INT,
    "TEXT": TEXT,
    "FLOAT": FLOAT,
}


def from_string(value: str) -> DataType:
    """文字列からDataTypeを取得
    
    Args:
        value: データ型の文字列（"INT", "TEXT", "FLOAT"など）
        
    Returns:
        DataTypeインスタンス（シングルトン）
        
    Raises:
        ValueError: 未知のデータ型の場合
    """
    value_upper = value.upper()
    
    if value_upper not in _TYPE_REGISTRY:
        raise ValueError(f"未知のデータ型: {value}")
    
    return _TYPE_REGISTRY[value_upper]


# DataTypeクラスにfrom_stringメソッドを追加（後方互換性のため）
DataType.from_string = classmethod(lambda cls, value: from_string(value))
