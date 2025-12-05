"""
WALライター

WALファイルにログレコードを書き込む機能を提供します。
Write-Ahead Loggingの「Write-Ahead」部分を担当します。
"""

import os
import struct
from pathlib import Path
from .record import LogRecord, LogType, InsertLogData


class WALWriter:
    """WALライター
    
    WALファイルにログレコードを書き込むクラスです。
    すべてのデータ変更操作は、実際のデータファイルに書き込む前に、
    このWALファイルに記録されます。
    """
    
    def __init__(self, wal_path: Path):
        """WALライターを初期化
        
        Args:
            wal_path: WALファイルのパス
        """
        self.wal_path = Path(wal_path)
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 現在のLSN（Log Sequence Number）
        self.current_lsn = 0
        
        # WALファイルを開く（追記モード）
        self._init_wal_file()
    
    def _init_wal_file(self):
        """WALファイルを初期化
        
        既存のWALファイルがある場合は、最後のLSNを読み込んで続きから開始します。
        """
        if self.wal_path.exists():
            # 既存のWALファイルから最後のLSNを読み込む
            self.current_lsn = self._read_last_lsn()
        else:
            # 新しいWALファイルを作成
            self.wal_path.touch()
            self.current_lsn = 0
    
    def _read_last_lsn(self) -> int:
        """既存のWALファイルから最後のLSNを読み込む
        
        Returns:
            最後のLSN（ファイルが空の場合は0）
        """
        try:
            with open(self.wal_path, 'rb') as f:
                last_lsn = 0
                while True:
                    # LSNを読み込む（8バイト）
                    lsn_bytes = f.read(8)
                    if len(lsn_bytes) < 8:
                        break
                    
                    lsn = struct.unpack(">Q", lsn_bytes)[0]
                    last_lsn = max(last_lsn, lsn)
                    
                    # レコードの残りを読み込んでスキップ
                    type_byte = f.read(1)
                    if len(type_byte) < 1:
                        break
                    
                    transaction_id, data_len = struct.unpack(">II", f.read(8))
                    f.seek(data_len, os.SEEK_CUR)
            
            return last_lsn
        except Exception:
            return 0
    
    def write_log(self, log_type: LogType, data: bytes, transaction_id: int = 0) -> int:
        """ログレコードを書き込む
        
        Args:
            log_type: ログタイプ
            data: ログデータ
            transaction_id: トランザクションID（将来の拡張用）
            
        Returns:
            書き込まれたLSN
        """
        self.current_lsn += 1
        
        log_record = LogRecord(
            lsn=self.current_lsn,
            log_type=log_type,
            transaction_id=transaction_id,
            data=data
        )
        
        # WALファイルに追記
        with open(self.wal_path, 'ab') as f:
            f.write(log_record.to_bytes())
            f.flush()
            os.fsync(f.fileno())  # ディスクへの確実な書き込み
        
        return self.current_lsn
    
    def write_insert_log(self, table_name: str, page_id: int, slot_id: int, tuple_data: bytes) -> int:
        """INSERT操作のログを書き込む
        
        Args:
            table_name: テーブル名
            page_id: ページID
            slot_id: スロットID
            tuple_data: タプルのバイト列
            
        Returns:
            書き込まれたLSN
        """
        insert_data = InsertLogData(
            table_name=table_name,
            page_id=page_id,
            slot_id=slot_id,
            tuple_data=tuple_data
        )
        
        return self.write_log(LogType.INSERT, insert_data.to_bytes())
    
    def write_checkpoint(self) -> int:
        """チェックポイントログを書き込む
        
        Returns:
            書き込まれたLSN
        """
        # チェックポイントには特別なデータは不要
        return self.write_log(LogType.CHECKPOINT, b'')
    
    def get_current_lsn(self) -> int:
        """現在のLSNを取得
        
        Returns:
            現在のLSN
        """
        return self.current_lsn
    
    def flush(self):
        """WALファイルをフラッシュ
        
        すべてのバッファされたデータをディスクに書き込みます。
        """
        # ファイルを開き直してフラッシュ（既にfsyncしているが、念のため）
        if self.wal_path.exists():
            with open(self.wal_path, 'ab') as f:
                f.flush()
                os.fsync(f.fileno())

