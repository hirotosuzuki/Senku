"""
データベースエントリーポイント

データベース全体を管理するメインクラスです。
SQL文を受け取り、パース、実行、結果返却を行います。

このクラスがデータベースの「顔」となり、
ユーザーはこのクラスを通じてデータベースと対話します。
"""

from pathlib import Path
from typing import Optional, List, Any

from .parser import SqlParser, ParsedStatement, StatementType
from .catalog import Catalog, Schema
from .storage import HeapFile, HeapTuple, BufferManager
from .executor import (
    ScanOperator,
    FilterOperator,
    ProjectOperator,
    Tuple as ExecTuple,
)


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
        
        # パーサを初期化
        self.parser = SqlParser()
        
        # テーブルファイルのマッピング（メモリ内キャッシュ）
        self.heap_files: dict[str, HeapFile] = {}
    
    def _get_heap_file(self, table_name: str) -> Optional[HeapFile]:
        """テーブルのヒープファイルを取得
        
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
        if stmt.kind == StatementType.CREATE:
            return self._execute_create(stmt)
        elif stmt.kind == StatementType.INSERT:
            return self._execute_insert(stmt)
        elif stmt.kind == StatementType.SELECT:
            return self._execute_select(stmt)
        else:
            raise ValueError(f"未対応のステートメント: {stmt.kind}")
    
    def _execute_create(self, stmt: ParsedStatement) -> None:
        """CREATE TABLE文を実行
        
        Args:
            stmt: パースされたCREATEステートメント
        """
        if not stmt.table_name or not stmt.columns:
            raise ValueError("CREATE TABLE文にテーブル名またはカラム定義がありません")
        
        if self.catalog.table_exists(stmt.table_name):
            raise ValueError(f"テーブル '{stmt.table_name}' は既に存在します")
        
        # スキーマを作成
        from .catalog.schema import ColumnDefinition as ColDef
        columns = [
            ColDef(name=col.name, data_type=col.data_type)
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
    
    def _execute_insert(self, stmt: ParsedStatement) -> None:
        """INSERT文を実行
        
        Args:
            stmt: パースされたINSERTステートメント
        """
        if not stmt.insert_table or not stmt.insert_values:
            raise ValueError("INSERT文にテーブル名または値がありません")
        
        # スキーマを取得
        schema = self.catalog.get_schema(stmt.insert_table)
        if not schema:
            raise ValueError(f"テーブル '{stmt.insert_table}' が存在しません")
        
        # 値の検証
        if not schema.validate_values(stmt.insert_values):
            raise ValueError("値がスキーマに適合しません")
        
        # ヒープファイルを取得
        heap_file = self._get_heap_file(stmt.insert_table)
        if not heap_file:
            raise ValueError(f"テーブル '{stmt.insert_table}' のヒープファイルが見つかりません")
        
        # タプルを作成
        heap_tuple = HeapTuple(values=stmt.insert_values)
        tuple_data = heap_tuple.to_bytes()
        
        # タプルを挿入
        heap_file.insert_tuple(tuple_data)
        
        # 行数を更新（簡易版: 実際は正確にカウントする必要がある）
        # self.catalog.update_row_count(stmt.insert_table, ...)
    
    def _execute_select(self, stmt: ParsedStatement) -> List[List[Any]]:
        """SELECT文を実行
        
        Args:
            stmt: パースされたSELECTステートメント
            
        Returns:
            結果のリスト（各行は値のリスト）
        """
        if not stmt.select_table:
            raise ValueError("SELECT文にテーブル名がありません")
        
        # スキーマを取得
        schema = self.catalog.get_schema(stmt.select_table)
        if not schema:
            raise ValueError(f"テーブル '{stmt.select_table}' が存在しません")
        
        # ヒープファイルを取得
        heap_file = self._get_heap_file(stmt.select_table)
        if not heap_file:
            raise ValueError(f"テーブル '{stmt.select_table}' のヒープファイルが見つかりません")
        
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
        if stmt.select_columns and stmt.select_columns != ["*"]:
            # 指定されたカラムのみを選択
            column_indices = []
            for col_name in stmt.select_columns:
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

