"""
ストレージ層

データの永続化を担当する層です。
- ページ管理: 固定長ページ（8KB）の管理
- ヒープファイル: テーブルデータの物理的な保存
- バッファマネージャ: ページキャッシュによるI/O最適化
"""

from .page import Page, PageHeader, PAGE_SIZE
from .heap import HeapFile, HeapTuple
from .buffer import BufferManager, BufferPool

__all__ = [
    "Page",
    "PageHeader",
    "PAGE_SIZE",
    "HeapFile",
    "HeapTuple",
    "BufferManager",
    "BufferPool",
]

