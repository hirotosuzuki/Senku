from pathlib import Path
from typing import Dict

class TableMetadata:
    pass

class Catalog:
    def __init__(self, catalog_path: Path):
        self.catalog_path = catalog_path
        self.tables: Dict[str, TableMetadata] = {}
        self._load()
    
    def _load(self):
        """カタログをディスクから読み込む"""
        pass

    def _save(self):
        """カタログをディスクに保存"""
        pass

    def create_table(self, table_name: str, schema: any, file_path: Path):
        pass