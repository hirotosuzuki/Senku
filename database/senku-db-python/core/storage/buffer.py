"""
バッファマネージャ

ページキャッシュを管理し、ディスクI/Oを最適化します。
頻繁にアクセスされるページをメモリに保持することで、パフォーマンスを大幅に向上させます。

バッファプールの重要性:
- ディスクI/Oはメモリアクセスの約10万倍遅い
- 適切なキャッシュ戦略により、クエリ性能が劇的に改善します
- PostgreSQLではshared_buffersという設定でバッファプールサイズを調整できます
"""

from typing import Optional, Dict
from pathlib import Path
import threading

from .page import Page
from .heap import HeapFile


class BufferPool:
    """バッファプール
    
    ページをキャッシュするメモリ領域です。
    簡易的な実装として、固定サイズの辞書を使用します。
    将来的にはLRUやClockアルゴリズムによる置換を実装します。
    """
    
    def __init__(self, capacity: int = 100):
        """バッファプールを初期化
        
        Args:
            capacity: キャッシュできるページ数（デフォルト100ページ = 約800KB）
        """
        self.capacity = capacity
        self.pages: Dict[tuple[Path, int], Page] = {}  # (file_path, page_id) -> Page
        self.lock = threading.Lock()  # スレッドセーフティのため（将来の並行処理対応）
    
    def get(self, file_path: Path, page_id: int) -> Optional[Page]:
        """キャッシュからページを取得
        
        Args:
            file_path: ヒープファイルのパス
            page_id: ページID
            
        Returns:
            Pageオブジェクト（キャッシュにない場合はNone）
        """
        with self.lock:
            key = (file_path, page_id)
            return self.pages.get(key)
    
    def put(self, file_path: Path, page_id: int, page: Page):
        """ページをキャッシュに追加
        
        Args:
            file_path: ヒープファイルのパス
            page_id: ページID
            page: Pageオブジェクト
        """
        with self.lock:
            key = (file_path, page_id)
            
            # 容量制限チェック（簡易版: 最初に到達したらクリア）
            if len(self.pages) >= self.capacity:
                # 簡易的なクリア（将来はLRU等で置換）
                self.pages.clear()
            
            self.pages[key] = page
    
    def evict(self, file_path: Path, page_id: int):
        """ページをキャッシュから削除
        
        Args:
            file_path: ヒープファイルのパス
            page_id: ページID
        """
        with self.lock:
            key = (file_path, page_id)
            self.pages.pop(key, None)
    
    def clear(self):
        """キャッシュをクリア"""
        with self.lock:
            self.pages.clear()


class BufferManager:
    """バッファマネージャ
    
    バッファプールを管理し、ページの読み書きを最適化します。
    ヒープファイルとバッファプールの間のインターフェースとして機能します。
    """
    
    def __init__(self, buffer_pool: Optional[BufferPool] = None):
        """バッファマネージャを初期化
        
        Args:
            buffer_pool: バッファプール（Noneの場合は新規作成）
        """
        self.buffer_pool = buffer_pool or BufferPool()
        self.dirty_pages: Dict[tuple[Path, int], Page] = {}  # ダーティページの追跡
    
    def fetch_page(self, heap_file: HeapFile, page_id: int) -> Page:
        """ページを取得（キャッシュ優先）
        
        Args:
            heap_file: ヒープファイル
            page_id: ページID
            
        Returns:
            Pageオブジェクト
        """
        # キャッシュを確認
        cached_page = self.buffer_pool.get(heap_file.file_path, page_id)
        if cached_page:
            return cached_page
        
        # キャッシュにない場合はディスクから読み込む
        page = heap_file.get_page(page_id)
        if page is None:
            raise ValueError(f"ページ {page_id} が存在しません")
        
        # キャッシュに追加
        self.buffer_pool.put(heap_file.file_path, page_id, page)
        return page
    
    def mark_dirty(self, heap_file: HeapFile, page: Page):
        """ページをダーティとしてマーク（変更済み）
        
        Args:
            heap_file: ヒープファイル
            page: 変更されたPageオブジェクト
        """
        key = (heap_file.file_path, page.page_id)
        self.dirty_pages[key] = page
    
    def flush_page(self, heap_file: HeapFile, page: Page):
        """ページをディスクに書き込む
        
        Args:
            heap_file: ヒープファイル
            page: 書き込むPageオブジェクト
        """
        heap_file.write_page(page)
        key = (heap_file.file_path, page.page_id)
        self.dirty_pages.pop(key, None)
    
    def flush_all(self, heap_file: HeapFile):
        """指定されたヒープファイルの全ダーティページをフラッシュ
        
        Args:
            heap_file: ヒープファイル
        """
        keys_to_flush = [
            key for key in self.dirty_pages.keys()
            if key[0] == heap_file.file_path
        ]
        
        for key in keys_to_flush:
            page = self.dirty_pages[key]
            self.flush_page(heap_file, page)
    
    def get_cache_hit_rate(self) -> float:
        """キャッシュヒット率を計算（将来の最適化用）
        
        Returns:
            ヒット率（0.0-1.0）
        """
        # 簡易実装: 将来的に統計情報を追加
        return 0.0

