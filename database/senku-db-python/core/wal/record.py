"""
WALレコード定義

WAL（Write-Ahead Logging）で使用するログレコードを定義します。
各操作（INSERT, UPDATE, DELETE等）は、対応するログレコードとして記録されます。
"""

import struct
from enum import Enum
from dataclasses import dataclass


class LogType(Enum):
    """ログレコードの種類
    
    WALで記録する操作の種類を定義します。
    """
    INSERT = 1
    UPDATE = 2  # 将来の拡張
    DELETE = 3  # 将来の拡張
    CHECKPOINT = 4
    COMMIT = 5  # 将来の拡張
    ABORT = 6   # 将来の拡張


@dataclass
class LogRecord:
    """WALログレコード
    
    データベースの操作を記録するログレコードです。
    各操作は、このレコードとしてWALファイルに書き込まれます。
    
    レコード構造:
    - LSN (Log Sequence Number): 8バイト - ログのシーケンス番号
    - Type: 1バイト - ログタイプ
    - Transaction ID: 4バイト - トランザクションID（将来の拡張）
    - Data Length: 4バイト - データの長さ
    - Data: 可変長 - 操作の詳細データ
    """
    lsn: int  # Log Sequence Number
    log_type: LogType
    transaction_id: int = 0  # 将来の拡張用
    data: bytes = b''  # 操作の詳細データ
    
    def to_bytes(self) -> bytes:
        """ログレコードをバイト列に変換
        
        Returns:
            シリアライズされたログレコード
        """
        data_len = len(self.data)
        # LSN (8 bytes) + Type (1 byte) + Transaction ID (4 bytes) + Data Length (4 bytes) + Data
        header = struct.pack(">QBII", 
                           self.lsn,
                           self.log_type.value,
                           self.transaction_id,
                           data_len)
        return header + self.data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "LogRecord":
        """バイト列からログレコードを復元
        
        Args:
            data: ログレコードのバイト列
            
        Returns:
            復元されたLogRecord
        """
        if len(data) < 17:  # 最小ヘッダーサイズ
            raise ValueError("Invalid log record: too short")
        
        lsn, log_type_val, transaction_id, data_len = struct.unpack_from(">QBII", data, 0)
        log_type = LogType(log_type_val)
        
        if len(data) < 17 + data_len:
            raise ValueError(f"Invalid log record: data length mismatch (expected {17 + data_len}, got {len(data)})")
        
        log_data = data[17:17 + data_len]
        
        return cls(
            lsn=lsn,
            log_type=log_type,
            transaction_id=transaction_id,
            data=log_data
        )
    
    @staticmethod
    def header_size() -> int:
        """ログレコードのヘッダーサイズを返す
        
        Returns:
            ヘッダーサイズ（バイト）
        """
        return 17  # 8 + 1 + 4 + 4


@dataclass
class InsertLogData:
    """INSERT操作のログデータ
    
    INSERT操作を記録するためのデータ構造です。
    """
    table_name: str
    page_id: int
    slot_id: int
    tuple_data: bytes
    
    def to_bytes(self) -> bytes:
        """INSERTログデータをバイト列に変換"""
        table_name_bytes = self.table_name.encode('utf-8')
        table_name_len = len(table_name_bytes)
        tuple_data_len = len(self.tuple_data)
        
        # Table name length (4 bytes) + Table name + Page ID (4 bytes) + Slot ID (4 bytes) + Tuple data length (4 bytes) + Tuple data
        header = struct.pack(">IIIII",
                           table_name_len,
                           self.page_id,
                           self.slot_id,
                           tuple_data_len,
                           0)  # 予約領域
        return header + table_name_bytes + self.tuple_data
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "InsertLogData":
        """バイト列からINSERTログデータを復元"""
        if len(data) < 20:
            raise ValueError("Invalid insert log data: too short")
        
        table_name_len, page_id, slot_id, tuple_data_len, _ = struct.unpack_from(">IIIII", data, 0)
        
        offset = 20
        table_name = data[offset:offset + table_name_len].decode('utf-8')
        offset += table_name_len
        
        tuple_data = data[offset:offset + tuple_data_len]
        
        return cls(
            table_name=table_name,
            page_id=page_id,
            slot_id=slot_id,
            tuple_data=tuple_data
        )

