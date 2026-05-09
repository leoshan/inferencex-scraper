"""
统一数据存储管理器

提供统一的数据存储接口，所有爬虫数据按以下结构存储：

data/
├── raw/                          # 原始数据
│   ├── json/                     # JSON 格式原始数据
│   │   ├── openrouter/           # OpenRouter 爬虫数据
│   │   ├── artificialanalysis/   # Artificial Analysis 数据
│   │   └── inferencex/           # InferenceX 数据
│   └── html/                     # HTML 调试文件
├── processed/                    # 处理后数据
│   ├── excel/                    # Excel 文件
│   └── csv/                      # CSV 文件
└── db/                           # SQLite 数据库
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'


class DataStorage:
    """统一数据存储管理器"""

    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化数据存储管理器

        参数:
            base_dir: 数据存储根目录，默认为项目的 data 目录
        """
        self.base_dir = Path(base_dir) if base_dir else DATA_DIR
        self.raw_dir = self.base_dir / 'raw'
        self.processed_dir = self.base_dir / 'processed'

        # 确保目录存在
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保所有必要的目录都存在"""
        dirs = [
            self.raw_dir / 'json' / 'openrouter',
            self.raw_dir / 'json' / 'artificialanalysis',
            self.raw_dir / 'json' / 'inferencex',
            self.raw_dir / 'html' / 'openrouter',
            self.raw_dir / 'html' / 'artificialanalysis',
            self.processed_dir / 'excel' / 'openrouter',
            self.processed_dir / 'excel' / 'artificialanalysis',
            self.processed_dir / 'excel' / 'inferencex',
            self.processed_dir / 'csv' / 'openrouter',
            self.processed_dir / 'csv' / 'artificialanalysis',
            self.processed_dir / 'csv' / 'inferencex',
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _get_category_dir(self, data_type: str, category: str, subcategory: str = '') -> Path:
        """
        获取分类目录路径

        参数:
            data_type: 数据类型 ('json', 'html', 'excel', 'csv')
            category: 数据分类 ('openrouter', 'artificialanalysis', 'inferencex')
            subcategory: 子分类 (可选)

        返回:
            Path: 目录路径
        """
        if data_type in ('json', 'html'):
            base = self.raw_dir / data_type / category
        else:
            base = self.processed_dir / data_type / category

        if subcategory:
            base = base / subcategory

        base.mkdir(parents=True, exist_ok=True)
        return base

    def save_json(
        self,
        data: Any,
        category: str,
        filename: str,
        subcategory: str = '',
        timestamp: bool = True
    ) -> Path:
        """
        保存 JSON 数据

        参数:
            data: 要保存的数据
            category: 数据分类 ('openrouter', 'artificialanalysis', 'inferencex')
            filename: 文件名 (不含扩展名)
            subcategory: 子分类目录 (可选)
            timestamp: 是否在文件名中添加时间戳

        返回:
            Path: 保存的文件路径
        """
        dir_path = self._get_category_dir('json', category, subcategory)

        if timestamp:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{ts}"

        filepath = dir_path / f"{filename}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  JSON 已保存: {filepath}")
        return filepath

    def save_html(
        self,
        html: str,
        category: str,
        filename: str,
        subcategory: str = '',
        timestamp: bool = True
    ) -> Path:
        """
        保存 HTML 数据

        参数:
            html: HTML 内容
            category: 数据分类
            filename: 文件名 (不含扩展名)
            subcategory: 子分类目录 (可选)
            timestamp: 是否在文件名中添加时间戳

        返回:
            Path: 保存的文件路径
        """
        dir_path = self._get_category_dir('html', category, subcategory)

        if timestamp:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{ts}"

        filepath = dir_path / f"{filename}.html"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"  HTML 已保存: {filepath}")
        return filepath

    def save_excel(
        self,
        df_or_data: Any,
        category: str,
        filename: str,
        subcategory: str = '',
        timestamp: bool = True,
        sheet_name: str = 'data',
        metadata: Optional[Dict] = None
    ) -> Optional[Path]:
        """
        保存 Excel 数据

        参数:
            df_or_data: DataFrame 或数据字典
            category: 数据分类
            filename: 文件名 (不含扩展名)
            subcategory: 子分类目录 (可选)
            timestamp: 是否在文件名中添加时间戳
            sheet_name: 工作表名称
            metadata: 元数据 (可选，会添加到 metadata 工作表)

        返回:
            Path: 保存的文件路径
        """
        try:
            import pandas as pd
        except ImportError:
            print("  无法保存 Excel: pandas 未安装")
            return None

        try:
            import openpyxl
        except ImportError:
            print("  无法保存 Excel: openpyxl 未安装")
            return None

        dir_path = self._get_category_dir('excel', category, subcategory)

        if timestamp:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{ts}"

        filepath = dir_path / f"{filename}.xlsx"

        try:
            # 处理不同类型的数据
            if isinstance(df_or_data, pd.DataFrame):
                df = df_or_data
            elif isinstance(df_or_data, dict):
                df = pd.DataFrame(df_or_data)
            elif isinstance(df_or_data, list):
                df = pd.DataFrame(df_or_data)
            else:
                print(f"  不支持的数据类型: {type(df_or_data)}")
                return None

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # 添加元数据工作表
                if metadata:
                    meta_df = pd.DataFrame([metadata])
                    meta_df.to_excel(writer, sheet_name='metadata', index=False)

            print(f"  Excel 已保存: {filepath} ({len(df)} 行)")
            return filepath

        except Exception as e:
            print(f"  保存 Excel 失败: {e}")
            return None

    def save_excel_multi_sheets(
        self,
        data_dict: Dict[str, Any],
        category: str,
        filename: str,
        subcategory: str = '',
        timestamp: bool = True
    ) -> Optional[Path]:
        """
        保存多工作表 Excel 数据

        参数:
            data_dict: {工作表名: DataFrame} 字典
            category: 数据分类
            filename: 文件名 (不含扩展名)
            subcategory: 子分类目录 (可选)
            timestamp: 是否在文件名中添加时间戳

        返回:
            Path: 保存的文件路径
        """
        try:
            import pandas as pd
        except ImportError:
            print("  无法保存 Excel: pandas 未安装")
            return None

        try:
            import openpyxl
        except ImportError:
            print("  无法保存 Excel: openpyxl 未安装")
            return None

        dir_path = self._get_category_dir('excel', category, subcategory)

        if timestamp:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{ts}"

        filepath = dir_path / f"{filename}.xlsx"

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                for sheet_name, data in data_dict.items():
                    if isinstance(data, pd.DataFrame):
                        df = data
                    elif isinstance(data, (dict, list)):
                        df = pd.DataFrame(data)
                    else:
                        continue

                    # Excel 工作表名最多 31 字符
                    sheet_name_short = sheet_name[:31]
                    df.to_excel(writer, sheet_name=sheet_name_short, index=False)
                    print(f"    写入 {sheet_name_short}: {len(df)} 行")

            print(f"  Excel 已保存: {filepath}")
            return filepath

        except Exception as e:
            print(f"  保存 Excel 失败: {e}")
            return None

    def save_csv(
        self,
        df_or_data: Any,
        category: str,
        filename: str,
        subcategory: str = '',
        timestamp: bool = True
    ) -> Optional[Path]:
        """
        保存 CSV 数据

        参数:
            df_or_data: DataFrame 或数据列表
            category: 数据分类
            filename: 文件名 (不含扩展名)
            subcategory: 子分类目录 (可选)
            timestamp: 是否在文件名中添加时间戳

        返回:
            Path: 保存的文件路径
        """
        try:
            import pandas as pd
        except ImportError:
            print("  无法保存 CSV: pandas 未安装")
            return None

        dir_path = self._get_category_dir('csv', category, subcategory)

        if timestamp:
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{filename}_{ts}"

        filepath = dir_path / f"{filename}.csv"

        try:
            if isinstance(df_or_data, pd.DataFrame):
                df = df_or_data
            elif isinstance(df_or_data, (dict, list)):
                df = pd.DataFrame(df_or_data)
            else:
                print(f"  不支持的数据类型: {type(df_or_data)}")
                return None

            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            print(f"  CSV 已保存: {filepath} ({len(df)} 行)")
            return filepath

        except Exception as e:
            print(f"  保存 CSV 失败: {e}")
            return None

    def get_json_path(
        self,
        category: str,
        filename: str,
        subcategory: str = ''
    ) -> Path:
        """获取 JSON 文件路径"""
        return self._get_category_dir('json', category, subcategory) / f"{filename}.json"

    def get_excel_path(
        self,
        category: str,
        filename: str,
        subcategory: str = ''
    ) -> Path:
        """获取 Excel 文件路径"""
        return self._get_category_dir('excel', category, subcategory) / f"{filename}.xlsx"

    def get_csv_path(
        self,
        category: str,
        filename: str,
        subcategory: str = ''
    ) -> Path:
        """获取 CSV 文件路径"""
        return self._get_category_dir('csv', category, subcategory) / f"{filename}.csv"

    def list_json_files(
        self,
        category: str,
        subcategory: str = ''
    ) -> List[Path]:
        """列出指定分类下的所有 JSON 文件"""
        dir_path = self._get_category_dir('json', category, subcategory)
        return sorted(dir_path.glob('*.json'))

    def list_excel_files(
        self,
        category: str,
        subcategory: str = ''
    ) -> List[Path]:
        """列出指定分类下的所有 Excel 文件"""
        dir_path = self._get_category_dir('excel', category, subcategory)
        return sorted(dir_path.glob('*.xlsx'))


# 全局实例
_storage: Optional[DataStorage] = None


def get_storage(base_dir: Optional[Path] = None) -> DataStorage:
    """获取全局 DataStorage 实例"""
    global _storage
    if _storage is None or (base_dir and _storage.base_dir != Path(base_dir)):
        _storage = DataStorage(base_dir)
    return _storage
