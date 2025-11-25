"""
チェックポイント機能

定期的にデータの整合性を確保するためのチェックポイント機能を実装します。
チェックポイント時には、WALにチェックポイントログを記録します。
"""

from pathlib import Path
from typing import Optional
from .writer import WALWriter
from .reader import WALReader


class CheckpointManager:
    """チェックポイントマネージャ
    
    チェックポイントの実行と管理を担当します。
    WAL層の責任として、チェックポイントログの記録のみを行います。
    データファイルへの書き込みは、上位層（Database層）がオーケストレーションします。
    """
    
    def __init__(self, wal_writer: WALWriter, db_path: Path):
        """チェックポイントマネージャを初期化
        
        Args:
            wal_writer: WALライター
            db_path: データベースのパス
        """
        self.wal_writer = wal_writer
        self.db_path = db_path
    
    def checkpoint(self) -> int:
        """チェックポイントログを記録
        
        WALにチェックポイントログを書き込みます。
        データファイルへの書き込みは、呼び出し元（Database層）が行います。
        
        Returns:
            チェックポイントのLSN
        """
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

