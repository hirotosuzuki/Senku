"""
リカバリ（障害復旧）機能

WALファイルを読み込んで、障害発生時のデータを復元します。
チェックポイント以降のログを再実行（REDO）することで、データを復元します。
"""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 型チェック時のみインポート（循環依存を避ける）
    from ..storage.buffer import BufferManager

from .reader import WALReader
from .record import LogRecord, LogType, InsertLogData
from .checkpoint import CheckpointManager
from ..storage.heap import HeapFile
from ..catalog import Catalog


class RecoveryManager:
    """リカバリマネージャ
    
    障害発生時のデータ復元を担当します。
    WALファイルを読み込んで、チェックポイント以降の操作を再実行します。
    
    一般的なDBMSの実装に従い、リカバリ時はバッファマネージャーを通して
    ページにアクセスし、メモリ上で更新します。ディスクへの書き込みは
    リカバリ完了後、チェックポイント時にまとめて行われます。
    """
    
    def __init__(self, db_path: Path, catalog: Catalog, checkpoint_manager: CheckpointManager,
                 buffer_manager: "BufferManager"):
        """リカバリマネージャを初期化
        
        Args:
            db_path: データベースのパス
            catalog: カタログ
            checkpoint_manager: チェックポイントマネージャ
            buffer_manager: バッファマネージャ（必須）
                           バッファマネージャーを通してページにアクセスし、
                           メモリ上で更新します
        """
        self.db_path = db_path
        self.catalog = catalog
        self.checkpoint_manager = checkpoint_manager
        self.buffer_manager = buffer_manager
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
        
        一般的なDBMSの実装に従い、以下のように動作します：
        1. バッファマネージャーを通してページを取得（メモリ上）
        2. ページをメモリ上で更新
        3. ページをダーティとしてマーク（まだディスクには書き込まない）
        
        リカバリ完了後、通常の動作に戻り、チェックポイント時に
        ダーティページをまとめてディスクに書き込みます。
        
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
            
            # バッファマネージャーを通してページを取得（メモリ上）
            try:
                page = self.buffer_manager.fetch_page(heap_file, insert_data.page_id)
            except ValueError:
                # ページが存在しない場合は、新しいページを割り当て
                if insert_data.page_id >= heap_file.page_count:
                    while heap_file.page_count <= insert_data.page_id:
                        heap_file.allocate_page()
                # 再度取得を試みる
                page = self.buffer_manager.fetch_page(heap_file, insert_data.page_id)
            
            # タプルが既に存在するかチェック（冪等性）
            existing_tuple = page.get_tuple(insert_data.slot_id)
            if existing_tuple is not None:
                # 既に存在する場合はスキップ（冪等性）
                return
            
            # ページをメモリ上で更新
            slot_id = page.insert_tuple(insert_data.tuple_data)
            if slot_id is None:
                return
            
            # ページをダーティとしてマーク
            # リカバリ中はディスクに書き込まない（リカバリ完了後、チェックポイント時にまとめて書き込む）
            self.buffer_manager.mark_dirty(heap_file, page)
        
        except Exception as e:
            # エラーが発生した場合はログを出力して続行
            print(f"Warning: Failed to redo INSERT at LSN {record.lsn}: {e}")

