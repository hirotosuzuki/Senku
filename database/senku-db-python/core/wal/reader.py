"""
WALリーダー

WALファイルからログレコードを読み込む機能を提供します。
障害復旧時に使用されます。
"""

import struct
from pathlib import Path
from typing import Iterator, Optional
from .record import LogRecord, LogType, InsertLogData


class WALReader:
    """WALリーダー
    
    WALファイルからログレコードを読み込むクラスです。
    障害復旧時に、WALファイルを読み込んでデータを復元します。
    """
    
    def __init__(self, wal_path: Path):
        """WALリーダーを初期化
        
        Args:
            wal_path: WALファイルのパス
        """
        self.wal_path = Path(wal_path)
    
    def read_all(self) -> Iterator[LogRecord]:
        """WALファイルからすべてのログレコードを読み込む
        
        Yields:
            LogRecordオブジェクト
        """
        if not self.wal_path.exists():
            return
        
        with open(self.wal_path, 'rb') as f:
            while True:
                record = self._read_next_record(f)
                if record is None:
                    break
                yield record
    
    def _read_next_record(self, f) -> Optional[LogRecord]:
        """次のログレコードを読み込む
        
        Args:
            f: ファイルオブジェクト
            
        Returns:
            LogRecordオブジェクト（EOFの場合はNone）
        """
        # LSNを読み込む（8バイト）
        lsn_bytes = f.read(8)
        if len(lsn_bytes) < 8:
            return None
        
        # 現在の位置を記録
        record_start = f.tell() - 8
        
        # ヘッダーの残りを読み込む
        header_rest = f.read(9)  # Type (1 byte) + Transaction ID (4 bytes) + Data Length (4 bytes)
        if len(header_rest) < 9:
            return None
        
        log_type_val = header_rest[0]
        transaction_id, data_len = struct.unpack(">II", header_rest[1:9])
        
        # データを読み込む
        data = f.read(data_len)
        if len(data) < data_len:
            return None
        
        # レコード全体を読み込んで復元
        f.seek(record_start)
        record_bytes = f.read(LogRecord.header_size() + data_len)
        
        try:
            return LogRecord.from_bytes(record_bytes)
        except ValueError:
            return None
    
    def read_from_lsn(self, from_lsn: int) -> Iterator[LogRecord]:
        """指定されたLSN以降のログレコードを読み込む
        
        Args:
            from_lsn: 開始LSN
            
        Yields:
            LogRecordオブジェクト
        """
        for record in self.read_all():
            if record.lsn >= from_lsn:
                yield record
    
    def find_last_checkpoint(self) -> Optional[int]:
        """最後のチェックポイントのLSNを取得
        
        Returns:
            最後のチェックポイントのLSN（存在しない場合はNone）
        """
        last_checkpoint_lsn = None
        
        for record in self.read_all():
            if record.log_type == LogType.CHECKPOINT:
                last_checkpoint_lsn = record.lsn
        
        return last_checkpoint_lsn

