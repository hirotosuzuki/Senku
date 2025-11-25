"""
チェックポイント機能

定期的にデータの整合性を確保するためのチェックポイント機能を実装します。
チェックポイント時には、すべてのダーティページをディスクに書き込み、
WALにチェックポイントログを記録します。
"""

from pathlib import Path
from typing import Optional
from .writer import WALWriter
from .reader import WALReader
from ..storage.heap import HeapFile
from ..storage.buffer import BufferManager


class CheckpointManager:
    """チェックポイントマネージャ
    
    チェックポイントの実行と管理を担当します。
    チェックポイントは、データの整合性を確保するために定期的に実行されます。
    """
    
    def __init__(self, wal_writer: WALWriter, db_path: Path, buffer_manager: Optional[BufferManager] = None):
        """チェックポイントマネージャを初期化
        
        Args:
            wal_writer: WALライター
            db_path: データベースのパス
            buffer_manager: バッファマネージャ（Noneの場合は使用しない）
        """
        self.wal_writer = wal_writer
        self.db_path = db_path
        self.buffer_manager = buffer_manager
    
    def checkpoint(self, heap_files: dict[str, HeapFile]) -> int:
        """チェックポイントを実行
        
        すべてのダーティページをディスクに書き込み、
        WALにチェックポイントログを記録します。
        
        Args:
            heap_files: ヒープファイルの辞書（テーブル名 -> HeapFile）
            
        Returns:
            チェックポイントのLSN
        """
        # BufferManagerが利用可能な場合は、ダーティページのみを書き込む
        if self.buffer_manager:
            for heap_file in heap_files.values():
                self.buffer_manager.flush_all(heap_file)
        else:
            # BufferManagerが利用できない場合は、すべてのページを書き込む（簡易実装）
            for heap_file in heap_files.values():
                for page_id in range(heap_file.page_count):
                    page = heap_file.get_page(page_id)
                    if page:
                        heap_file.write_page(page)
        
        # チェックポイントログを書き込む
        checkpoint_lsn = self.wal_writer.write_checkpoint()
        
        return checkpoint_lsn
    
    def get_last_checkpoint_lsn(self) -> Optional[int]:
        """最後のチェックポイントのLSNを取得
        
        Returns:
            最後のチェックポイントのLSN（存在しない場合はNone）
        """
        wal_path = self.db_path / "wal.log"
        if not wal_path.exists():
            return None
        
        reader = WALReader(wal_path)
        return reader.find_last_checkpoint()

