#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据导入脚本 - 将 data 目录下所有数据文件导入数据库

支持的文件类型：
- JSON: 导入到对应的表
- CSV: 导入到对应的表
- Excel: 导入到对应的表
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("[ERROR] pandas 未安装，无法处理 Excel/CSV 文件")
    sys.exit(1)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
DB_PATH = DATA_DIR / 'db' / 'trend_tracker.db'


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database(conn):
    """初始化/更新数据库表结构"""
    # 模型每日调用量表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS model_usage_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            model_slug TEXT NOT NULL,
            app_name TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            requests INTEGER DEFAULT 0,
            cache_hits INTEGER DEFAULT 0,
            provider_name TEXT,
            UNIQUE(time, model_slug, app_name)
        )
    ''')

    # 应用使用分布表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS app_distribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            app_name TEXT NOT NULL,
            model_slug TEXT NOT NULL,
            token_share REAL,
            total_tokens INTEGER,
            UNIQUE(time, app_name, model_slug)
        )
    ''')

    # 模型元数据表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS model_metadata (
            model_slug TEXT PRIMARY KEY,
            display_name TEXT,
            provider TEXT,
            context_length INTEGER,
            pricing_prompt REAL,
            pricing_completion REAL,
            context_window INTEGER,
            median_output_speed REAL,
            intelligence_index REAL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # OpenRouter 应用表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS openrouter_apps (
            slug TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            url TEXT,
            icon_url TEXT,
            category TEXT,
            website TEXT,
            usage_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT
        )
    ''')

    # Artificial Analysis 数据表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS artificial_analysis_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_time TEXT NOT NULL,
            model_name TEXT,
            model_slug TEXT,
            intelligence_index REAL,
            median_output_speed REAL,
            price_per_million_tokens REAL,
            context_window_tokens INTEGER,
            input_price REAL,
            output_price REAL,
            omniscience_index REAL,
            provider TEXT,
            data_type TEXT,
            raw_data TEXT,
            UNIQUE(fetch_time, model_name, data_type)
        )
    ''')

    # InferenceX benchmarks 数据表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inferencex_benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_time TEXT NOT NULL,
            model_id TEXT,
            model_display_name TEXT,
            hardware TEXT,
            framework TEXT,
            precision TEXT,
            isl INTEGER,
            osl INTEGER,
            conc INTEGER,
            date TEXT,
            spec_method TEXT,
            disagg TEXT,
            is_multinode INTEGER,
            p99_itl REAL,
            mean_itl REAL,
            p99_e2el REAL,
            tput_per_gpu REAL,
            p99_ttft REAL,
            mean_tpot REAL,
            median_ttft REAL,
            median_tpot REAL,
            median_itl REAL,
            median_e2el REAL,
            throughput REAL,
            metrics_json TEXT,
            UNIQUE(fetch_time, model_id, hardware, framework, precision, isl, osl, conc)
        )
    ''')

    # OpenRouter 模型详情表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS openrouter_model_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fetch_time TEXT NOT NULL,
            model_slug TEXT,
            model_name TEXT,
            provider TEXT,
            context_length INTEGER,
            pricing_prompt REAL,
            pricing_completion REAL,
            top_app TEXT,
            endpoint TEXT,
            raw_data TEXT,
            UNIQUE(fetch_time, model_slug)
        )
    ''')

    # 创建索引
    conn.execute('CREATE INDEX IF NOT EXISTS idx_usage_model ON model_usage_daily (model_slug, time)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_usage_app ON model_usage_daily (app_name, time)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_aa_model ON artificial_analysis_data (model_name)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_inferencex_model ON inferencex_benchmarks (model_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_model_details ON openrouter_model_details (model_slug)')

    conn.commit()


def import_artificialanalysis_json(conn):
    """导入 Artificial Analysis JSON 数据"""
    json_dir = DATA_DIR / 'raw' / 'json' / 'artificialanalysis'
    if not json_dir.exists():
        return 0

    imported = 0
    cursor = conn.cursor()

    for json_file in json_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Intelligence Index
            for item in data.get('intelligence_index', []):
                model_name = item.get('modelName', item.get('model_name', ''))
                if not model_name:
                    continue
                cursor.execute('''
                    INSERT OR REPLACE INTO artificial_analysis_data
                    (fetch_time, model_name, intelligence_index, median_output_speed,
                     price_per_million_tokens, data_type, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (fetch_time, model_name,
                      item.get('intelligenceIndex', item.get('intelligence_index')),
                      item.get('medianOutputSpeed', item.get('median_output_speed')),
                      item.get('pricePerMillionTokens', item.get('price_per_million_tokens')),
                      'intelligence_index', json.dumps(item, ensure_ascii=False)))
                imported += 1

            # Speed 数据
            for item in data.get('speed', []):
                model_name = item.get('modelName', item.get('model_name', ''))
                if not model_name:
                    continue
                cursor.execute('''
                    INSERT OR REPLACE INTO artificial_analysis_data
                    (fetch_time, model_name, median_output_speed, data_type, raw_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (fetch_time, model_name,
                      item.get('medianOutputSpeed', item.get('median_output_speed')),
                      'speed', json.dumps(item, ensure_ascii=False)))
                imported += 1

            # Price 数据
            for item in data.get('price', []):
                model_name = item.get('modelName', item.get('model_name', ''))
                if not model_name:
                    continue
                cursor.execute('''
                    INSERT OR REPLACE INTO artificial_analysis_data
                    (fetch_time, model_name, price_per_million_tokens, data_type, raw_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (fetch_time, model_name,
                      item.get('pricePerMillionTokens', item.get('price_per_million_tokens')),
                      'price', json.dumps(item, ensure_ascii=False)))
                imported += 1

            # Omniscience 数据
            for item in data.get('omniscience', []):
                model_name = item.get('modelName', item.get('model_name', ''))
                if not model_name:
                    continue
                cursor.execute('''
                    INSERT OR REPLACE INTO artificial_analysis_data
                    (fetch_time, model_name, omniscience_index, data_type, raw_data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (fetch_time, model_name,
                      item.get('omniscienceIndex', item.get('omniscience_index')),
                      'omniscience', json.dumps(item, ensure_ascii=False)))
                imported += 1

            # Models Detail 数据
            for item in data.get('models_detail', []):
                model_slug = item.get('model_slug', '')
                if not model_slug:
                    continue
                cursor.execute('''
                    INSERT OR REPLACE INTO artificial_analysis_data
                    (fetch_time, model_name, model_slug, context_window_tokens, input_price,
                     output_price, median_output_speed, intelligence_index, data_type, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (fetch_time, model_slug, model_slug,
                      item.get('context_window_tokens'),
                      item.get('input_price'), item.get('output_price'),
                      item.get('median_output_speed'), item.get('intelligence_index'),
                      'models_detail', json.dumps(item, ensure_ascii=False)))
                imported += 1

            print(f"  [JSON] {json_file.name}")

        except Exception as e:
            print(f"  [ERROR] {json_file.name}: {e}")

    conn.commit()
    return imported


def import_inferencex_json(conn):
    """导入 InferenceX JSON 数据"""
    json_dir = DATA_DIR / 'raw' / 'json' / 'raw_json_files'
    if not json_dir.exists():
        json_dir = DATA_DIR / 'raw' / 'json' / 'inferencex'
    if not json_dir.exists():
        return 0

    imported = 0
    cursor = conn.cursor()

    for json_file in json_dir.glob('*_benchmarks.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            metadata = data.get('metadata', {})
            model_id = metadata.get('model_id', '')
            model_display_name = metadata.get('model_display_name', '')
            fetch_time = metadata.get('timestamp', datetime.now().isoformat())

            for record in data.get('data', []):
                metrics = record.get('metrics', {})
                cursor.execute('''
                    INSERT OR REPLACE INTO inferencex_benchmarks
                    (fetch_time, model_id, model_display_name, hardware, framework,
                     precision, isl, osl, conc, date, spec_method, disagg, is_multinode,
                     p99_itl, mean_itl, p99_e2el, tput_per_gpu, p99_ttft, mean_tpot,
                     median_ttft, median_tpot, median_itl, median_e2el, throughput, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    fetch_time, model_id, model_display_name,
                    record.get('hardware', ''), record.get('framework', ''),
                    record.get('precision', ''), record.get('isl', 0), record.get('osl', 0),
                    record.get('conc', 0), record.get('date', ''),
                    record.get('spec_method', ''), record.get('disagg', ''),
                    1 if record.get('is_multinode') else 0,
                    metrics.get('p99_itl'), metrics.get('mean_itl'),
                    metrics.get('p99_e2el'), metrics.get('tput_per_gpu'),
                    metrics.get('p99_ttft'), metrics.get('mean_tpot'),
                    metrics.get('median_ttft'), metrics.get('median_tpot'),
                    metrics.get('median_itl'), metrics.get('median_e2el'),
                    metrics.get('throughput'),
                    json.dumps(metrics, ensure_ascii=False)
                ))
                imported += 1

            print(f"  [JSON] {json_file.name} ({len(data.get('data', []))} 条)")

        except Exception as e:
            print(f"  [ERROR] {json_file.name}: {e}")

    conn.commit()
    return imported


def import_openrouter_apps_json(conn):
    """导入 OpenRouter Apps JSON 数据"""
    json_dir = DATA_DIR / 'raw' / 'json' / 'openrouter' / 'apps'
    if not json_dir.exists():
        return 0

    imported = 0
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    for json_file in json_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            apps = data if isinstance(data, list) else data.get('apps', data.get('data', []))

            for app in apps:
                slug = app.get('slug', '')
                if not slug:
                    continue
                cursor.execute('''
                    INSERT OR REPLACE INTO openrouter_apps
                    (slug, name, description, url, icon_url, category, website,
                     usage_count, updated_at, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (slug, app.get('name', ''), app.get('description', ''),
                      app.get('url', f"https://openrouter.ai/apps/{slug}"),
                      app.get('icon_url', ''), app.get('category', ''),
                      app.get('website', ''), app.get('usage_count', 0),
                      now, json.dumps(app, ensure_ascii=False)))
                imported += 1

            print(f"  [JSON] {json_file.name} ({len(apps)} 条)")

        except Exception as e:
            print(f"  [ERROR] {json_file.name}: {e}")

    conn.commit()
    return imported


def import_excel_file(conn, filepath, table_name, mapping=None):
    """导入单个 Excel 文件到指定表"""
    try:
        xlsx = pd.ExcelFile(filepath)
        imported = 0
        cursor = conn.cursor()
        fetch_time = datetime.now().isoformat()

        for sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            if df.empty:
                continue

            # 根据表名和文件名决定导入逻辑
            if table_name == 'artificial_analysis_data':
                imported += import_aa_excel_sheet(cursor, df, fetch_time, filepath.name, sheet_name)
            elif table_name == 'openrouter_model_details':
                imported += import_or_model_excel_sheet(cursor, df, fetch_time, filepath.name, sheet_name)
            elif table_name == 'model_metadata':
                imported += import_model_metadata(cursor, df, fetch_time, filepath.name, sheet_name)
            else:
                # 通用导入
                imported += import_generic_excel(cursor, df, table_name, fetch_time, filepath.name, sheet_name)

        conn.commit()
        return imported

    except Exception as e:
        print(f"  [ERROR] {filepath.name}: {e}")
        return 0


def import_aa_excel_sheet(cursor, df, fetch_time, filename, sheet_name):
    """导入 Artificial Analysis Excel 数据"""
    imported = 0

    # 映射常见列名
    col_mapping = {
        'modelName': 'model_name', 'model_name': 'model_name',
        'intelligenceIndex': 'intelligence_index', 'intelligence_index': 'intelligence_index',
        'medianOutputSpeed': 'median_output_speed', 'median_output_speed': 'median_output_speed',
        'pricePerMillionTokens': 'price_per_million_tokens', 'price_per_million_tokens': 'price_per_million_tokens',
        'omniscienceIndex': 'omniscience_index', 'omniscience_index': 'omniscience_index',
    }

    for _, row in df.iterrows():
        model_name = None
        for col in ['modelName', 'model_name', 'Model', 'model']:
            if col in row.index and pd.notna(row[col]):
                model_name = str(row[col])
                break

        if not model_name:
            continue

        values = {
            'fetch_time': fetch_time,
            'model_name': model_name,
            'data_type': sheet_name,
        }

        # 提取数值字段
        for col in df.columns:
            if pd.notna(row[col]):
                val = row[col]
                if col in ['intelligenceIndex', 'intelligence_index', 'Intelligence Index']:
                    values['intelligence_index'] = float(val) if pd.notna(val) else None
                elif col in ['medianOutputSpeed', 'median_output_speed', 'Output Speed']:
                    values['median_output_speed'] = float(val) if pd.notna(val) else None
                elif col in ['pricePerMillionTokens', 'price_per_million_tokens', 'Price']:
                    values['price_per_million_tokens'] = float(val) if pd.notna(val) else None

        values['raw_data'] = row.to_json()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO artificial_analysis_data
                (fetch_time, model_name, intelligence_index, median_output_speed,
                 price_per_million_tokens, omniscience_index, data_type, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (values.get('fetch_time'), values.get('model_name'),
                  values.get('intelligence_index'), values.get('median_output_speed'),
                  values.get('price_per_million_tokens'), values.get('omniscience_index'),
                  values.get('data_type'), values.get('raw_data')))
            imported += 1
        except:
            pass

    return imported


def import_or_model_excel_sheet(cursor, df, fetch_time, filename, sheet_name):
    """导入 OpenRouter 模型详情 Excel 数据"""
    imported = 0

    for _, row in df.iterrows():
        model_slug = None
        for col in ['slug', 'model_slug', 'id', 'model_id', 'Model', 'model']:
            if col in row.index and pd.notna(row[col]):
                model_slug = str(row[col])
                break

        if not model_slug:
            continue

        model_name = None
        for col in ['name', 'model_name', 'display_name', 'Model Name']:
            if col in row.index and pd.notna(row[col]):
                model_name = str(row[col])
                break

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO openrouter_model_details
                (fetch_time, model_slug, model_name, provider, context_length,
                 pricing_prompt, pricing_completion, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fetch_time, model_slug, model_name,
                  str(row.get('provider', '')) if pd.notna(row.get('provider')) else None,
                  int(row.get('context_length', 0)) if pd.notna(row.get('context_length')) else None,
                  float(row.get('pricing_prompt', 0)) if pd.notna(row.get('pricing_prompt')) else None,
                  float(row.get('pricing_completion', 0)) if pd.notna(row.get('pricing_completion')) else None,
                  row.to_json()))
            imported += 1
        except:
            pass

    return imported


def import_model_metadata(cursor, df, fetch_time, filename, sheet_name):
    """导入模型元数据"""
    imported = 0

    for _, row in df.iterrows():
        model_slug = None
        for col in ['slug', 'model_slug', 'id', 'model_id', 'Model', 'model']:
            if col in row.index and pd.notna(row[col]):
                model_slug = str(row[col])
                break

        if not model_slug:
            continue

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO model_metadata
                (model_slug, display_name, provider, context_length, context_window,
                 pricing_prompt, pricing_completion, median_output_speed, intelligence_index, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model_slug,
                  str(row.get('name', row.get('display_name', ''))) if pd.notna(row.get('name', row.get('display_name'))) else None,
                  str(row.get('provider', '')) if pd.notna(row.get('provider')) else None,
                  int(row.get('context_length', 0)) if pd.notna(row.get('context_length')) else None,
                  int(row.get('context_window', 0)) if pd.notna(row.get('context_window')) else None,
                  float(row.get('pricing_prompt', row.get('input_price', 0))) if pd.notna(row.get('pricing_prompt', row.get('input_price'))) else None,
                  float(row.get('pricing_completion', row.get('output_price', 0))) if pd.notna(row.get('pricing_completion', row.get('output_price'))) else None,
                  float(row.get('median_output_speed', 0)) if pd.notna(row.get('median_output_speed')) else None,
                  float(row.get('intelligence_index', 0)) if pd.notna(row.get('intelligence_index')) else None,
                  fetch_time))
            imported += 1
        except:
            pass

    return imported


def import_generic_excel(cursor, df, table_name, fetch_time, filename, sheet_name):
    """通用 Excel 导入"""
    # 获取表结构
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]

    imported = 0
    for _, row in df.iterrows():
        values = {}
        for col in df.columns:
            if col in columns and pd.notna(row[col]):
                values[col] = row[col]

        if not values:
            continue

        # 构建插入语句
        cols = ', '.join(values.keys())
        placeholders = ', '.join(['?' for _ in values])
        try:
            cursor.execute(f'''
                INSERT OR REPLACE INTO {table_name} ({cols})
                VALUES ({placeholders})
            ''', list(values.values()))
            imported += 1
        except:
            pass

    return imported


def import_all_excel_files(conn):
    """导入所有 Excel 文件"""
    excel_dirs = [
        (DATA_DIR / 'processed' / 'excel' / 'artificialanalysis', 'artificial_analysis_data'),
        (DATA_DIR / 'processed' / 'excel' / 'openrouter' / 'model_details', 'openrouter_model_details'),
        (DATA_DIR / 'processed' / 'excel' / 'openrouter' / 'app_usage', 'model_usage_daily'),
        (DATA_DIR / 'processed' / 'excel' / 'openrouter' / 'apps', 'openrouter_apps'),
        (DATA_DIR / 'processed' / 'excel' / 'openrouter', 'openrouter_model_details'),
        (DATA_DIR / 'processed' / 'excel' / 'analysis', 'openrouter_model_details'),
    ]

    total_imported = 0

    for dir_path, table_name in excel_dirs:
        if not dir_path.exists():
            continue

        print(f"\n[{dir_path.relative_to(DATA_DIR)}]")

        for xlsx_file in sorted(dir_path.glob('*.xlsx')):
            if xlsx_file.name.startswith('~$'):
                continue
            count = import_excel_file(conn, xlsx_file, table_name)
            print(f"  [Excel] {xlsx_file.name} ({count} 条)")
            total_imported += count

    return total_imported


def import_csv_files(conn):
    """导入所有 CSV 文件"""
    csv_files = list(DATA_DIR.rglob('*.csv'))
    if not csv_files:
        return 0

    total_imported = 0
    cursor = conn.cursor()
    fetch_time = datetime.now().isoformat()

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if df.empty:
                continue

            # 根据文件名判断表
            filename = csv_file.name.lower()
            if 'inferencex' in filename or 'benchmark' in filename:
                table_name = 'inferencex_benchmarks'
            elif 'artificial' in filename:
                table_name = 'artificial_analysis_data'
            else:
                table_name = 'model_metadata'

            # 导入数据
            count = 0
            for _, row in df.iterrows():
                try:
                    if table_name == 'inferencex_benchmarks':
                        model_id = str(row.get('model_id', row.get('model_display_name', '')))
                        cursor.execute('''
                            INSERT OR REPLACE INTO inferencex_benchmarks
                            (fetch_time, model_id, model_display_name, hardware, framework,
                             precision, isl, osl, conc, date, p99_itl, mean_itl, p99_e2el,
                             tput_per_gpu, p99_ttft, mean_tpot, median_ttft, median_tpot,
                             median_itl, median_e2el, throughput, metrics_json)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (fetch_time, model_id,
                              str(row.get('model_display_name', '')),
                              str(row.get('hardware', '')) if pd.notna(row.get('hardware')) else None,
                              str(row.get('framework', '')) if pd.notna(row.get('framework')) else None,
                              str(row.get('precision', '')) if pd.notna(row.get('precision')) else None,
                              int(row.get('isl', 0)) if pd.notna(row.get('isl')) else None,
                              int(row.get('osl', 0)) if pd.notna(row.get('osl')) else None,
                              int(row.get('conc', 0)) if pd.notna(row.get('conc')) else None,
                              str(row.get('date', '')) if pd.notna(row.get('date')) else None,
                              float(row.get('p99_itl', 0)) if pd.notna(row.get('p99_itl')) else None,
                              float(row.get('mean_itl', 0)) if pd.notna(row.get('mean_itl')) else None,
                              float(row.get('p99_e2el', 0)) if pd.notna(row.get('p99_e2el')) else None,
                              float(row.get('tput_per_gpu', 0)) if pd.notna(row.get('tput_per_gpu')) else None,
                              float(row.get('p99_ttft', 0)) if pd.notna(row.get('p99_ttft')) else None,
                              float(row.get('mean_tpot', 0)) if pd.notna(row.get('mean_tpot')) else None,
                              float(row.get('median_ttft', 0)) if pd.notna(row.get('median_ttft')) else None,
                              float(row.get('median_tpot', 0)) if pd.notna(row.get('median_tpot')) else None,
                              float(row.get('median_itl', 0)) if pd.notna(row.get('median_itl')) else None,
                              float(row.get('median_e2el', 0)) if pd.notna(row.get('median_e2el')) else None,
                              float(row.get('throughput', 0)) if pd.notna(row.get('throughput')) else None,
                              row.to_json()))
                        count += 1
                except:
                    pass

            conn.commit()
            print(f"  [CSV] {csv_file.name} ({count} 条)")
            total_imported += count

        except Exception as e:
            print(f"  [ERROR] {csv_file.name}: {e}")

    return total_imported


def show_database_stats(conn):
    """显示数据库统计信息"""
    cursor = conn.cursor()

    print("\n" + "=" * 60)
    print("数据库统计")
    print("=" * 60)

    tables = [
        ('model_usage_daily', '模型使用量'),
        ('app_distribution', '应用分布'),
        ('model_metadata', '模型元数据'),
        ('openrouter_apps', 'OpenRouter 应用'),
        ('openrouter_model_details', 'OpenRouter 模型详情'),
        ('artificial_analysis_data', 'Artificial Analysis'),
        ('inferencex_benchmarks', 'InferenceX 基准'),
    ]

    total = 0
    for table, name in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {name}: {count:,} 条记录")
            total += count
        except:
            print(f"  {name}: 表不存在")

    print(f"\n  总计: {total:,} 条记录")


def main():
    print("=" * 60)
    print("数据导入脚本")
    print("=" * 60)
    print(f"数据目录: {DATA_DIR}")
    print(f"数据库: {DB_PATH}")

    # 初始化数据库
    print("\n[1/6] 初始化数据库...")
    conn = get_db_connection()
    init_database(conn)
    print("  [OK] 数据库表结构已初始化")

    # 导入 JSON 文件
    print("\n[2/6] 导入 Artificial Analysis JSON...")
    aa_count = import_artificialanalysis_json(conn)
    print(f"  [OK] 导入 {aa_count} 条记录")

    print("\n[3/6] 导入 InferenceX JSON...")
    ix_count = import_inferencex_json(conn)
    print(f"  [OK] 导入 {ix_count} 条记录")

    print("\n[4/6] 导入 OpenRouter Apps JSON...")
    or_count = import_openrouter_apps_json(conn)
    print(f"  [OK] 导入 {or_count} 条记录")

    # 导入 Excel 文件
    print("\n[5/6] 导入 Excel 文件...")
    excel_count = import_all_excel_files(conn)
    print(f"  [OK] 导入 {excel_count} 条记录")

    # 导入 CSV 文件
    print("\n[6/6] 导入 CSV 文件...")
    csv_count = import_csv_files(conn)
    print(f"  [OK] 导入 {csv_count} 条记录")

    # 显示统计
    show_database_stats(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("[OK] 数据导入完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
