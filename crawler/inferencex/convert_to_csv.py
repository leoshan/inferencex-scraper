#!/usr/bin/env python3
"""
JSON → CSV 转换脚本 v3 - 将 benchmarks API 采集到的 JSON 数据转换为 CSV 文件

新版 API 数据格式:
  每条记录包含 hardware, framework, model, precision, isl, osl, conc, metrics{...} 等字段
  metrics 包含: p99_itl, mean_itl, p99_e2el, tput_per_gpu, p99_ttft, mean_tpot, ...

核心功能:
  1. 自动识别新格式 JSON 文件
  2. 扫描所有记录和 metrics 子字段，自动展平
  3. 输出单个综合 CSV 文件（不再分 e2e/interactivity）

数据存储：
    - 输入 JSON: data/raw/json/inferencex/
    - 输出 CSV: data/processed/csv/inferencex/
"""

import json
import os
import sys
import csv
import glob
import argparse
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入统一数据存储
from data import DataStorage


def flatten_record(record):
    """将 benchmarks 记录展平（特别是 metrics 子字典）"""
    flattened = {}

    for key, value in record.items():
        if key == 'metrics' and isinstance(value, dict):
            # 展平 metrics 字典
            for metric_key, metric_value in value.items():
                flattened[f"metrics_{metric_key}"] = metric_value
        elif isinstance(value, dict):
            # 其他嵌套字典也展平
            for nested_key, nested_value in value.items():
                flattened[f"{key}_{nested_key}"] = nested_value
        elif isinstance(value, (list, tuple)):
            flattened[key] = json.dumps(value)
        else:
            flattened[key] = value

    return flattened


def extract_all_fields(json_files):
    """提取所有 JSON 文件中出现过的所有字段名"""
    all_fields = set()

    for filepath in json_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            records = data.get('data', [])
            for record in records:
                if isinstance(record, dict):
                    flattened = flatten_record(record)
                    all_fields.update(flattened.keys())
        except Exception as e:
            print(f"Error extracting fields from {filepath}: {e}")

    return sorted(list(all_fields))


def convert_files_to_csv(files, output_file):
    """将所有 JSON 文件转换为单个 CSV"""
    if not files:
        print("❌ No files to process")
        return None

    print(f"\n🔄 Processing {len(files)} benchmark files...")

    # 提取所有可能的字段
    print("🔍 Analyzing data structure...")
    all_fields = extract_all_fields(files)
    print(f"📋 Found {len(all_fields)} unique data fields")

    # 定义 CSV 列
    # 优先列 + 剩余列
    priority_columns = [
        'model', 'hardware', 'framework', 'precision',
        'isl', 'osl', 'conc', 'date',
        'spec_method', 'disagg', 'is_multinode',
    ]
    # 按 metrics_ 前缀整理
    metric_columns = sorted([f for f in all_fields if f.startswith('metrics_')])
    other_columns = sorted([f for f in all_fields
                            if f not in priority_columns and f not in metric_columns])

    # 最终列顺序: 添加 model_display_name 列
    csv_columns = ['model_display_name'] + \
                  [c for c in priority_columns if c in all_fields] + \
                  other_columns + metric_columns

    # 准备 CSV 数据
    csv_data = []
    total_records = 0

    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        print(f"  📄 Processing {i+1}/{len(files)}: {filename}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            metadata = json_data.get('metadata', {})
            model_display_name = metadata.get('model_display_name', metadata.get('model_id', 'Unknown'))

            records = json_data.get('data', [])
            file_records = 0

            for record in records:
                if isinstance(record, dict):
                    flattened = flatten_record(record)

                    csv_row = {'model_display_name': model_display_name}
                    for col in csv_columns:
                        if col == 'model_display_name':
                            continue
                        csv_row[col] = flattened.get(col, '')

                    csv_data.append(csv_row)
                    file_records += 1

            total_records += file_records
            print(f"    ✅ Extracted {file_records} data points")

        except Exception as e:
            print(f"    ❌ Error processing {filename}: {e}")

    print(f"📊 Total records extracted: {total_records}")

    # 保存 CSV
    if csv_data:
        try:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                writer.writerows(csv_data)

            print(f"✅ CSV file saved: {output_file}")
            return {
                'columns': csv_columns,
                'total_records': total_records,
                'file_count': len(files),
            }
        except Exception as e:
            print(f"❌ Error saving CSV file: {e}")
            return None
    else:
        print("❌ No data to save")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='将 InferenceX benchmarks JSON 数据转换为 CSV 文件'
    )
    parser.add_argument(
        '--input-dir', '-i',
        default=None,
        help='输入 JSON 文件目录 (默认: data/raw/json/inferencex)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default=None,
        help='输出 CSV 文件目录 (默认: data/processed/csv/inferencex)'
    )

    args = parser.parse_args()

    storage = DataStorage()

    # 设置输入目录
    if args.input_dir is None:
        input_directory = str(storage.raw_dir / 'json' / 'inferencex')
    else:
        input_directory = args.input_dir

    # 设置输出目录
    if args.output_dir is None:
        output_directory = str(storage.processed_dir / 'csv' / 'inferencex')
    else:
        output_directory = args.output_dir

    output_file = os.path.join(output_directory, 'inference_max_benchmarks.csv')

    if not os.path.exists(input_directory):
        print(f"❌ Input directory {input_directory} does not exist")
        return

    # 查找所有 JSON 文件（排除报告文件）
    import glob
    json_files = glob.glob(os.path.join(input_directory, '*.json'))
    json_files = [f for f in json_files if not any(x in os.path.basename(f).lower()
                                                for x in ['readme', 'summary', 'cleanup', 'report'])]

    print(f"🚀 Starting JSON to CSV conversion...")
    print(f"📊 Found {len(json_files)} JSON files to process")

    if not json_files:
        print("❌ No JSON files found!")
        return

    result = convert_files_to_csv(json_files, output_file)

    if result:
        file_size = os.path.getsize(output_file)
        print(f"\n🎉 Conversion completed successfully!")
        print(f"📄 Output CSV: {output_file}")
        print(f"📊 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"📈 Total records: {result['total_records']:,}")
        print(f"📋 Total columns: {len(result['columns'])}")
    else:
        print("❌ Conversion failed")


if __name__ == "__main__":
    main()
