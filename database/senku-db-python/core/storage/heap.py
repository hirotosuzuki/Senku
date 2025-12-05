"""
ヒープファイル管理

テーブルのデータを物理的に保存する「ヒープファイル」を管理します。
ヒープファイルは複数のページから構成され、タプル（行）を順次追加していく方式です。

「ヒープ」という名前の由来:
- データが任意の順序で格納されるため、ヒープ（積み重ね）と呼ばれます
- インデックスがない場合、全ページをスキャンする必要があります
- これが「フルテーブルスキャン」の基礎となります
"""

import os
from typing import Optional, List, Iterator
from dataclasses import dataclass
from pathlib import Path

from .page import Page, PAGE_SIZE
from ..types import DataType, INT, TEXT, FLOAT


@dataclass
class HeapTuple:
    """ヒープタプル（行）の表現
    
    データベースの1行を表現します。
    将来的にはNULL値の処理や可変長カラムのサポートを追加します。
    """
    values: List[any]  # カラム値のリスト
    tuple_id: Optional[tuple[int, int]] = None  # (page_id, slot_id)
    
    def to_bytes(self, schema: Optional[List[tuple[str, str]]] = None) -> bytes:
        """タプルをバイト列にシリアライズ
        
        簡易的な実装: 各値を型に応じてシリアライズ
        将来的にはより効率的なフォーマット（列指向など）を検討
        
        Args:
            schema: スキーマ情報 [(column_name, data_type), ...]
                   指定されない場合は、値の型から推論
        """
        parts = []
        
        if schema:
            # スキーマが指定されている場合は、それを使用
            for (col_name, col_type_str), value in zip(schema, self.values):
                col_type = DataType.from_string(col_type_str)
                parts.append(col_type.serialize(value))
        else:
            # スキーマが指定されていない場合は、値の型から推論（後方互換性）
            for value in self.values:
                if isinstance(value, int):
                    parts.append(INT.serialize(value))
                elif isinstance(value, str):
                    parts.append(TEXT.serialize(value))
                elif isinstance(value, float):
                    parts.append(FLOAT.serialize(value))
                else:
                    # その他の型は文字列として扱う
                    parts.append(TEXT.serialize(str(value)))
        
        return b''.join(parts)
    
    @classmethod
    def from_bytes(cls, data: bytes, schema: List[tuple[str, str]]) -> "HeapTuple":
        """バイト列からタプルを復元
        
        Args:
            data: タプルのバイト列
            schema: スキーマ情報 [(column_name, data_type), ...]
            
        Returns:
            復元されたHeapTuple
        """
        values = []
        offset = 0
        
        for col_name, col_type_str in schema:
            try:
                col_type = DataType.from_string(col_type_str)
                value, offset = col_type.deserialize(data, offset)
                values.append(value)
            except ValueError:
                # 未知の型はTEXTとして扱う（後方互換性）
                value, offset = TEXT.deserialize(data, offset)
                values.append(value)
        
        return cls(values=values)


class HeapFile:
    """ヒープファイル
    
    テーブルのデータを物理的に保存するファイルを管理します。
    各テーブルは1つのヒープファイルに対応します。
    
    ファイル構造:
    - ファイルは複数の固定長ページ（8KB）から構成
    - ページは順次追加され、既存ページが満杯になったら新しいページを追加
    - 削除されたタプルのスペースは再利用可能（将来のVACUUM機能で整理）
    """
    
    def __init__(self, file_path: Path):
        """ヒープファイルを初期化
        
        Args:
            file_path: ヒープファイルのパス
        """
        self.file_path = Path(file_path)
        self.page_count = 0
        
        # ファイルが存在する場合はページ数を計算
        if self.file_path.exists():
            file_size = self.file_path.stat().st_size
            self.page_count = file_size // PAGE_SIZE
    
    def create(self):
        """新しいヒープファイルを作成"""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.touch()
        self.page_count = 0
    
    def get_page(self, page_id: int) -> Optional[Page]:
        """ページを読み込む
        
        Args:
            page_id: ページID（0始まり）
            
        Returns:
            Pageオブジェクト（存在しない場合はNone）
        """
        if page_id >= self.page_count:
            return None
        
        with open(self.file_path, 'rb') as f:
            f.seek(page_id * PAGE_SIZE)
            page_data = f.read(PAGE_SIZE)
        
        if len(page_data) < PAGE_SIZE:
            return None
        
        return Page.from_bytes(page_data, page_id)
    
    def write_page(self, page: Page):
        """ページを書き込む
        
        Args:
            page: 書き込むPageオブジェクト
        """
        with open(self.file_path, 'r+b') as f:
            f.seek(page.page_id * PAGE_SIZE)
            f.write(page.to_bytes())
            f.flush()
            os.fsync(f.fileno())  # ディスクへの確実な書き込み
    
    def allocate_page(self) -> Page:
        """新しいページを割り当て
        
        Returns:
            新しく作成されたPageオブジェクト
        """
        page = Page(page_id=self.page_count)
        self.page_count += 1
        self.write_page(page)
        return page
    
    def find_insert_location(self, tuple_data: bytes) -> tuple[int, int]:
        """挿入先のページとスロットを決定（実際にはまだ挿入しない）
        
        Write-Ahead Loggingの原則に従い、WALに書き込む前に挿入先を決定するために使用します。
        
        Args:
            tuple_data: タプルのバイト列
            
        Returns:
            (page_id, slot_id) のタプル
            slot_idは、挿入時に割り当てられるスロットID（現在のslot_count）
        """
        required_space = len(tuple_data) + 8  # タプル + スロット
        
        # 既存のページに空きがあるか確認
        for page_id in range(self.page_count):
            page = self.get_page(page_id)
            if page and page.get_free_space() >= required_space:
                # このページに挿入可能
                # スロットIDは現在のslot_count（次の挿入でこの値になる）
                slot_id = page.header.slot_count
                return (page_id, slot_id)
        
        # 既存ページに空きがない場合は新しいページが必要
        # 新しいページIDは現在のpage_count、スロットIDは0（新しいページの最初のスロット）
        return (self.page_count, 0)
    
    def insert_tuple(self, tuple_data: bytes, page_id: int) -> tuple[Page, int]:
        """タプルを挿入
        
        Write-Ahead Loggingの原則に従い、指定されたページにタプルを挿入します。
        このメソッドはページをディスクに書き込まず、更新されたページオブジェクトを返します。
        ディスクへの書き込みはBufferManagerを通じて、チェックポイント時に行います。
        
        Args:
            tuple_data: タプルのバイト列
            page_id: 挿入先のページID
        
        Returns:
            (更新されたPageオブジェクト, スロットID) のタプル
        """
        # ページが存在するか確認
        if page_id >= self.page_count:
            # 新しいページを割り当て（メモリ上のみ、まだディスクには書き込まない）
            if page_id == self.page_count:
                page = Page(page_id=page_id)
                self.page_count += 1
            else:
                raise ValueError(f"ページID {page_id} は無効です（現在のページ数: {self.page_count}）")
        else:
            page = self.get_page(page_id)
            if not page:
                raise ValueError(f"ページ {page_id} が見つかりません")
        
        # タプルを挿入
        slot_id = page.insert_tuple(tuple_data)
        if slot_id is None:
            raise RuntimeError(f"ページ {page_id} にタプルを挿入できませんでした（空きスペース不足）")
        
        # ページを返す（ディスクには書き込まない）
        # ディスクへの書き込みはBufferManagerを通じて、チェックポイント時に行う
        return (page, slot_id)
    
    def scan_tuples(self, schema: List[tuple[str, str]]) -> Iterator[HeapTuple]:
        """全タプルをスキャン（フルテーブルスキャン）
        
        Args:
            schema: スキーマ情報
            
        Yields:
            HeapTupleオブジェクト
        """
        for page_id in range(self.page_count):
            page = self.get_page(page_id)
            if page:
                for slot_id in range(page.header.slot_count):
                    tuple_data = page.get_tuple(slot_id)
                    if tuple_data:
                        tuple_obj = HeapTuple.from_bytes(tuple_data, schema)
                        tuple_obj.tuple_id = (page_id, slot_id)
                        yield tuple_obj
    
    def get_tuple(self, page_id: int, slot_id: int, schema: List[tuple[str, str]]) -> Optional[HeapTuple]:
        """特定のタプルを取得
        
        Args:
            page_id: ページID
            slot_id: スロットID
            schema: スキーマ情報
            
        Returns:
            HeapTupleオブジェクト（存在しない場合はNone）
        """
        page = self.get_page(page_id)
        if not page:
            return None
        
        tuple_data = page.get_tuple(slot_id)
        if not tuple_data:
            return None
        
        tuple_obj = HeapTuple.from_bytes(tuple_data, schema)
        tuple_obj.tuple_id = (page_id, slot_id)
        return tuple_obj

