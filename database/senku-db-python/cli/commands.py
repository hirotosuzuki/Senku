"""
メタコマンド

REPLで使用するメタコマンド（.で始まるコマンド）を定義します。
"""

from abc import ABC, abstractmethod
from typing import Any


class MetaCommand(ABC):
    """メタコマンドの基底クラス"""
    
    @abstractmethod
    def execute(self, args: list[str], context: Any) -> str:
        """メタコマンドを実行
        
        Args:
            args: コマンド引数
            context: 実行コンテキスト（Databaseオブジェクトなど）
            
        Returns:
            実行結果の文字列
        """
        pass

