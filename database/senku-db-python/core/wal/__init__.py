"""
WAL（Write-Ahead Logging）層

トランザクションログを管理し、障害復旧を実現します。
Write-Ahead Loggingは、データを変更する前にログを書き込む方式です。
これにより、システムクラッシュ時でもデータを復元できます。
"""

from .record import LogRecord, LogType, InsertLogData
from .writer import WALWriter
from .reader import WALReader
from .checkpoint import CheckpointManager
from .recovery import RecoveryManager

__all__ = [
    "LogRecord",
    "LogType",
    "InsertLogData",
    "WALWriter",
    "WALReader",
    "CheckpointManager",
    "RecoveryManager",
]

