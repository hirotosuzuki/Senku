"""
データベースエントリーポイント

データベース全体を管理するメインクラスです。
SQL文を受け取り、パース、実行、結果返却を行います。

このクラスがデータベースの「顔」となり、
ユーザーはこのクラスを通じてデータベースと対話します。
"""

from pathlib import Path
from typing import Optional, List, Any

from .parser import (
    SqlParser,
    CreateStatement,
    InsertStatement,
    SelectStatement,
)
from .catalog import Catalog, Schema
from .storage import HeapFile, HeapTuple, BufferManager
from .executor import (
    ScanOperator,
    FilterOperator,
    ProjectOperator,
    Tuple as ExecTuple,
)
from .wal import WALWriter, CheckpointManager, RecoveryManager


class Database:
    """データベースクラス
    
    データベースのメインエントリーポイントです。
    SQL文の実行、テーブル管理、トランザクション管理などを担当します。
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """データベースを初期化
        
        Args:
            db_path: データベースファイルの保存先ディレクトリ
                    デフォルトはカレントディレクトリの`.senkudb`ディレクトリ
        """
        if db_path is None:
            db_path = Path(".senkudb")
        
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # カタログを初期化
        catalog_file = self.db_path / "catalog.json"
        self.catalog = Catalog(catalog_file)
        
        # バッファマネージャを初期化
        self.buffer_manager = BufferManager()
        
        # WALを初期化
        wal_path = self.db_path / "wal.log"
        self.wal_writer = WALWriter(wal_path)
        self.checkpoint_manager = CheckpointManager(self.wal_writer, self.db_path)
        
        # パーサを初期化
        self.parser = SqlParser()
        
        # テーブルファイルのマッピング（メモリ内キャッシュ）
        self.heap_files: dict[str, HeapFile] = {}
        
        # 起動時にリカバリを実行
        self._recover()
    
    def _recover(self):
        """起動時にリカバリを実行
        
        WALファイルを読み込んで、チェックポイント以降の操作を再実行します。
        """
        recovery_manager = RecoveryManager(self.db_path, self.catalog)
        recovered_count = recovery_manager.recover()
        if recovered_count > 0:
            print(f"Recovered {recovered_count} log records from WAL")
    
    def checkpoint(self) -> int:
        """チェックポイントを実行
        
        1. BufferManagerのダーティページをすべてディスクに書き込む
        2. WALにチェックポイントログを記録する
        
        Returns:
            チェックポイントのLSN
        """
        # 1. すべてのダーティページをディスクに書き込む
        for table_name, heap_file in self.heap_files.items():
            self.buffer_manager.flush_all(heap_file)
        
        # 2. WALにチェックポイントログを記録
        return self.checkpoint_manager.checkpoint()
    
    def _get_heap_file(self, table_name: str) -> Optional[HeapFile]:
        """テーブルのヒープファイルを取得
        
        BufferManagerを使ってページをキャッシュするため、
        ページの取得はBufferManagerを通じて行います。
        
        Args:
            table_name: テーブル名
            
        Returns:
            HeapFileオブジェクト（存在しない場合はNone）
        """
        if table_name in self.heap_files:
            return self.heap_files[table_name]
        
        metadata = self.catalog.get_table_metadata(table_name)
        if not metadata:
            return None
        
        file_path = self.db_path / metadata.file_path
        heap_file = HeapFile(file_path)
        self.heap_files[table_name] = heap_file
        return heap_file
    
    def execute(self, sql: str) -> Optional[Any]:
        """SQL文を実行
        
        Args:
            sql: SQL文
            
        Returns:
            実行結果（SELECTの場合は結果リスト、その他はNone）
        """
        # SQL文をパース
        stmt = self.parser.parse(sql)
        
        # ステートメントの種類に応じて処理
        if isinstance(stmt, CreateStatement):
            return self._execute_create(stmt)
        elif isinstance(stmt, InsertStatement):
            return self._execute_insert(stmt)
        elif isinstance(stmt, SelectStatement):
            return self._execute_select(stmt)
        else:
            raise ValueError(f"未対応のステートメント: {stmt.kind}")
    
    def _execute_create(self, stmt: CreateStatement) -> None:
        """CREATE TABLE文を実行
        
        Args:
            stmt: パースされたCREATEステートメント
        """
        if self.catalog.table_exists(stmt.table_name):
            raise ValueError(f"テーブル '{stmt.table_name}' は既に存在します")
        
        # スキーマを作成
        from .catalog.schema import ColumnDefinition as ColDef
        from .types import DataType
        columns = [
            ColDef(name=col.name, data_type=DataType.from_string(col.data_type))
            for col in stmt.columns
        ]
        schema = Schema(stmt.table_name, columns)
        
        # ヒープファイルを作成
        file_path = self.db_path / f"{stmt.table_name}.heap"
        heap_file = HeapFile(file_path)
        heap_file.create()
        
        # カタログに登録
        self.catalog.create_table(stmt.table_name, schema, file_path)
        
        # メモリキャッシュに追加
        self.heap_files[stmt.table_name] = heap_file
    
    def _execute_insert(self, stmt: InsertStatement) -> None:
        """INSERT文を実行
        
        Args:
            stmt: パースされたINSERTステートメント
        """
        # スキーマを取得
        schema = self.catalog.get_schema(stmt.table_name)
        if not schema:
            raise ValueError(f"テーブル '{stmt.table_name}' が存在しません")
        
        # 値の検証
        if not schema.validate_values(stmt.values):
            raise ValueError("値がスキーマに適合しません")
        
        # ヒープファイルを取得
        heap_file = self._get_heap_file(stmt.table_name)
        if not heap_file:
            raise ValueError(f"テーブル '{stmt.table_name}' のヒープファイルが見つかりません")
        
        # タプルを作成
        heap_tuple = HeapTuple(values=stmt.values)
        tuple_data = heap_tuple.to_bytes(schema.to_tuple_list())
        
        # Write-Ahead Loggingの原則に従い、先に挿入先を決定
        # （実際にはまだメモリ上のページを変更しない）
        page_id, slot_id = heap_file.find_insert_location(tuple_data)
        
        # WALにログを書き込む（Write-Ahead: データを変更する前に、必ずログを書き込む）
        # LSNは将来の拡張（トランザクション管理など）で使用する可能性がある
        _lsn = self.wal_writer.write_insert_log(
            table_name=stmt.table_name,
            page_id=page_id,
            slot_id=slot_id,
            tuple_data=tuple_data
        )
        
        # WALへの書き込みが完了したら、メモリ上のページを更新
        # BufferManagerを使ってページを管理（ダーティページとしてマーク）
        page, actual_slot_id = heap_file.insert_tuple(tuple_data, page_id=page_id)
        
        # BufferManagerにページをキャッシュし、ダーティとしてマーク
        self.buffer_manager.buffer_pool.put(heap_file.file_path, page_id, page)
        self.buffer_manager.mark_dirty(heap_file, page)
        
        # スロットIDの検証（デバッグ用）
        if actual_slot_id != slot_id:
            # これは通常発生しないはずだが、念のため警告を出す
            # 実際には、find_insert_location()で正確なスロットIDを予測しているため、
            # この条件は満たされないはず
            pass  # フェーズ2では警告を出さない（将来的にログに記録）
        
        # 行数を更新（簡易版: 実際は正確にカウントする必要がある）
        # self.catalog.update_row_count(stmt.table_name, ...)
    
    def _execute_select(self, stmt: SelectStatement) -> List[List[Any]]:
        """SELECT文を実行
        
        Args:
            stmt: パースされたSELECTステートメント
            
        Returns:
            結果のリスト（各行は値のリスト）
        """
        # スキーマを取得
        schema = self.catalog.get_schema(stmt.table_name)
        if not schema:
            raise ValueError(f"テーブル '{stmt.table_name}' が存在しません")
        
        # ヒープファイルを取得
        heap_file = self._get_heap_file(stmt.table_name)
        if not heap_file:
            raise ValueError(f"テーブル '{stmt.table_name}' のヒープファイルが見つかりません")
        
        # スキャン演算子を作成
        scan = ScanOperator(heap_file, schema)
        
        # WHERE句がある場合はフィルタ演算子を追加
        iterator = scan
        if stmt.where_clause:
            def predicate(tuple_obj: ExecTuple) -> bool:
                col_index = schema.get_column_index(stmt.where_clause.column)
                if col_index is None:
                    return False
                
                value = tuple_obj.get_value(col_index)
                operator = stmt.where_clause.operator
                target_value = stmt.where_clause.value
                
                if operator == "=":
                    return value == target_value
                elif operator == ">":
                    return value > target_value
                elif operator == "<":
                    return value < target_value
                elif operator == ">=":
                    return value >= target_value
                elif operator == "<=":
                    return value <= target_value
                elif operator == "!=" or operator == "<>":
                    return value != target_value
                else:
                    raise ValueError(f"未対応の演算子: {operator}")
            
            filter_op = FilterOperator(scan, predicate)
            iterator = filter_op
        
        # SELECT句の処理（射影）
        if stmt.columns and stmt.columns != ["*"]:
            # 指定されたカラムのみを選択
            column_indices = []
            for col_name in stmt.columns:
                index = schema.get_column_index(col_name)
                if index is None:
                    raise ValueError(f"カラム '{col_name}' が存在しません")
                column_indices.append(index)
            
            project_op = ProjectOperator(iterator, column_indices, schema)
            iterator = project_op
        else:
            # SELECT * の場合は全カラム
            column_indices = list(range(len(schema.columns)))
        
        # クエリを実行
        results = []
        iterator.open()
        try:
            while True:
                tuple_obj = iterator.next()
                if tuple_obj is None:
                    break
                results.append(tuple_obj.values)
        finally:
            iterator.close()
        
        return results

