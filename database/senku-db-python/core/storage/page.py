"""
ページ管理

データベースの基本単位である「ページ」を管理します。
PostgreSQLでは8KBの固定長ページを使用していますが、ここでも同様の設計を採用します。

歴史的背景:
- ページサイズは通常OSのページサイズ（4KB）の倍数に設定されます
- 8KBは多くのデータベースシステムで採用されている標準的なサイズです
- 大きすぎるとメモリ効率が悪く、小さすぎるとI/O回数が増えます
"""

import struct
from typing import Optional, List
from dataclasses import dataclass

# ページサイズ: 8KB (8192 bytes)
# これはPostgreSQLの標準ページサイズと同じです
PAGE_SIZE = 8192

# ページヘッダーサイズ: 24 bytes
# 将来の拡張を考慮して余裕を持たせています
PAGE_HEADER_SIZE = 24

# スロット配列のオーバーヘッド（各スロットは8 bytes: offset + length）
SLOT_SIZE = 8


@dataclass
class PageHeader:
    """ページヘッダー
    
    ページのメタデータを保持します。
    - checksum: ページの整合性チェック用（将来実装）
    - free_space: 利用可能なスペース
    - slot_count: スロット配列のエントリ数
    - lsn: Log Sequence Number（WAL実装時に使用）
    """
    checksum: int = 0
    free_space: int = PAGE_SIZE - PAGE_HEADER_SIZE
    slot_count: int = 0
    lsn: int = 0  # Log Sequence Number (WAL用)
    
    def to_bytes(self) -> bytes:
        """ページヘッダーをバイト列に変換"""
        return struct.pack(">IIII", 
                          self.checksum,
                          self.free_space,
                          self.slot_count,
                          self.lsn)
    
    @classmethod
    def from_bytes(cls, data: bytes) -> "PageHeader":
        """バイト列からページヘッダーを復元"""
        checksum, free_space, slot_count, lsn = struct.unpack(">IIII", data[:16])
        return cls(
            checksum=checksum,
            free_space=free_space,
            slot_count=slot_count,
            lsn=lsn
        )


class Page:
    """データベースページ
    
    固定長のページを表現します。可変長のタプル（行）を効率的に格納するため、
    スロット配列方式を採用しています。
    
    スロット配列方式:
    - ページの末尾からスロット配列を配置
    - 各スロットは(offset, length)のペア
    - データはページの先頭（ヘッダーの後）から順に配置
    - これにより可変長データを効率的に管理できます
    
    例:
    [Header][Data...][...Free Space...][Slot Array]
    """
    
    def __init__(self, page_id: int = 0):
        """ページを初期化
        
        Args:
            page_id: ページID（ファイル内でのページ番号）
        """
        self.page_id = page_id
        self.header = PageHeader()
        self.data = bytearray(PAGE_SIZE)
        self.slots: List[tuple[int, int]] = []  # (offset, length) のリスト
        
        # ヘッダーをページの先頭に書き込む
        header_bytes = self.header.to_bytes()
        self.data[:PAGE_HEADER_SIZE] = header_bytes
    
    def insert_tuple(self, tuple_data: bytes) -> Optional[int]:
        """タプルをページに挿入
        
        Args:
            tuple_data: タプルのバイト列
            
        Returns:
            スロット番号（失敗時はNone）
        """
        tuple_size = len(tuple_data)
        required_space = tuple_size + SLOT_SIZE  # タプル + スロットエントリ
        
        # 空きスペースをチェック
        if self.header.free_space < required_space:
            return None  # ページに空きがない
        
        # データを挿入する位置を決定（ヘッダーの後から順に）
        data_start = PAGE_HEADER_SIZE
        current_offset = data_start
        
        # 既存のタプルの最大オフセットを計算
        for offset, length in self.slots:
            current_offset = max(current_offset, offset + length)
        
        # タプルを書き込む
        offset = current_offset
        self.data[offset:offset + tuple_size] = tuple_data
        
        # スロットを追加（ページの末尾から逆順に配置）
        slot_offset = PAGE_SIZE - (len(self.slots) + 1) * SLOT_SIZE
        struct.pack_into(">II", self.data, slot_offset, offset, tuple_size)
        self.slots.append((offset, tuple_size))
        
        # ヘッダーを更新
        self.header.slot_count = len(self.slots)
        self.header.free_space = PAGE_SIZE - current_offset - tuple_size - len(self.slots) * SLOT_SIZE
        
        # ヘッダーを再書き込み
        header_bytes = self.header.to_bytes()
        self.data[:PAGE_HEADER_SIZE] = header_bytes
        
        return len(self.slots) - 1
    
    def get_tuple(self, slot_id: int) -> Optional[bytes]:
        """スロットIDからタプルを取得
        
        Args:
            slot_id: スロット番号
            
        Returns:
            タプルのバイト列（存在しない場合はNone）
        """
        if slot_id < 0 or slot_id >= len(self.slots):
            return None
        
        offset, length = self.slots[slot_id]
        return bytes(self.data[offset:offset + length])
    
    def to_bytes(self) -> bytes:
        """ページ全体をバイト列に変換（ディスクへの書き込み用）"""
        # スロット配列をページの末尾に書き込む
        slot_start = PAGE_SIZE - len(self.slots) * SLOT_SIZE
        for i, (offset, length) in enumerate(self.slots):
            slot_offset = slot_start + i * SLOT_SIZE
            struct.pack_into(">II", self.data, slot_offset, offset, length)
        
        return bytes(self.data)
    
    @classmethod
    def from_bytes(cls, data: bytes, page_id: int = 0) -> "Page":
        """バイト列からページを復元（ディスクからの読み込み用）
        
        Args:
            data: ページのバイト列（PAGE_SIZE長）
            page_id: ページID
            
        Returns:
            復元されたPageオブジェクト
        """
        page = cls(page_id)
        page.data = bytearray(data)
        
        # ヘッダーを読み込む
        page.header = PageHeader.from_bytes(data[:PAGE_HEADER_SIZE])
        
        # スロット配列を読み込む
        slot_count = page.header.slot_count
        slot_start = PAGE_SIZE - slot_count * SLOT_SIZE
        page.slots = []
        
        for i in range(slot_count):
            slot_offset = slot_start + i * SLOT_SIZE
            offset, length = struct.unpack_from(">II", data, slot_offset)
            page.slots.append((offset, length))
        
        return page
    
    def get_free_space(self) -> int:
        """利用可能な空きスペースを取得"""
        return self.header.free_space

