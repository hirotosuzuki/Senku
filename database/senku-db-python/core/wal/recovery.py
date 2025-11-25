"""
リカバリ（障害復旧）機能

WALファイルを読み込んで、障害発生時のデータを復元します。
チェックポイント以降のログを再実行（REDO）することで、データを復元します。
"""

from pathlib import Path
from .reader import WALReader
from .record import LogRecord, LogType, InsertLogData
from .checkpoint import CheckpointManager
from ..storage.heap import HeapFile
from ..catalog import Catalog


class RecoveryManager:
    """リカバリマネージャ
    
    障害発生時のデータ復元を担当します。
    WALファイルを読み込んで、チェックポイント以降の操作を再実行します。
    """
    
    def __init__(self, db_path: Path, catalog: Catalog, checkpoint_manager: CheckpointManager):
        """リカバリマネージャを初期化
        
        Args:
            db_path: データベースのパス
            catalog: カタログ
            checkpoint_manager: チェックポイントマネージャ
        """
        self.db_path = db_path
        self.catalog = catalog
        self.checkpoint_manager = checkpoint_manager
        self.wal_path = db_path / "wal.log"
    
    def recover(self) -> int:
        """リカバリを実行
        
        WALファイルを読み込んで、チェックポイント以降の操作を再実行します。
        
        Returns:
            復元されたログレコード数
        """
        if not self.wal_path.exists():
            return 0
        
        reader = WALReader(self.wal_path)
        
        # 最後のチェックポイントを取得（CheckpointManagerを使用）
        last_checkpoint_lsn = self.checkpoint_manager.get_last_checkpoint_lsn()
        
        # チェックポイント以降のログを読み込む
        if last_checkpoint_lsn is not None:
            records = list(reader.read_from_lsn(last_checkpoint_lsn + 1))
        else:
            # チェックポイントがない場合は、すべてのログを再実行
            records = list(reader.read_all())
        
        # ログを再実行（REDO）
        recovered_count = 0
        for record in records:
            if record.log_type == LogType.INSERT:
                self._redo_insert(record)
                recovered_count += 1
            # 将来の拡張: UPDATE, DELETE等
        
        return recovered_count
    
    def _redo_insert(self, record: LogRecord):
        """INSERT操作を再実行（REDO）
        
        Args:
            record: INSERTログレコード
        """
        try:
            insert_data = InsertLogData.from_bytes(record.data)
            
            # ヒープファイルを取得
            heap_file_path = self.db_path / f"{insert_data.table_name}.heap"
            if not heap_file_path.exists():
                # テーブルが存在しない場合はスキップ
                return
            
            heap_file = HeapFile(heap_file_path)
            
            # ページを取得
            page = heap_file.get_page(insert_data.page_id)
            if page is None:
                # ページが存在しない場合は、新しいページを割り当て
                if insert_data.page_id >= heap_file.page_count:
                    # 必要なページ数を確保
                    while heap_file.page_count <= insert_data.page_id:
                        heap_file.allocate_page()
                    page = heap_file.get_page(insert_data.page_id)
            
            if page is None:
                return
            
            # タプルが既に存在するかチェック
            existing_tuple = page.get_tuple(insert_data.slot_id)
            if existing_tuple is not None:
                # 既に存在する場合はスキップ（冪等性）
                return
            
            # タプルを挿入
            slot_id = page.insert_tuple(insert_data.tuple_data)
            if slot_id is not None:
                heap_file.write_page(page)
        
        except Exception as e:
            # エラーが発生した場合はログを出力して続行
            print(f"Warning: Failed to redo INSERT at LSN {record.lsn}: {e}")

