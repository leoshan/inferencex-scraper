#!/usr/bin/env python3
"""
CSV 合并脚本 v3 - 合并多个 benchmark CSV 文件或直接处理单一 CSV

新版 API 已经在 benchmarks 端点返回了综合数据（包含所有 metrics），
所以不再需要合并 e2e 和 interactivity 两个文件。

本脚本的功能:
  1. 如果只有一个 CSV 文件，直接复制为最终输出
  2. 如果有多个 CSV 文件，按 composite key 合并
  3. 支持向后兼容旧版的 e2e + interactivity 合并模式

数据存储：
    - 输入 CSV: data/processed/csv/inferencex/
    - 输出 CSV: data/processed/csv/inferencex/inference_max_merged.csv
"""

import csv
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入统一数据存储
from data import DataStorage


def merge_or_copy_csv(input_dir: str, output_file: str) -> dict:
    """
    合并或复制 CSV 文件

    Args:
        input_dir: 输入目录
        output_file: 输出文件路径

    Returns:
        统计信息字典
    """
    # 查找 CSV 文件
    csv_files = []
    for f in os.listdir(input_dir):
        if f.endswith('.csv') and not f.startswith('inference_max_merged'):
            csv_files.append(os.path.join(input_dir, f))

    if not csv_files:
        print("❌ No CSV files found in input directory")
        return None

    print(f"📊 Found {len(csv_files)} CSV file(s)")

    # 检查是否有旧版的 e2e + interactivity 文件
    e2e_file = os.path.join(input_dir, 'inference_max_e2e.csv')
    inter_file = os.path.join(input_dir, 'inference_max_interactivity.csv')
    benchmarks_file = os.path.join(input_dir, 'inference_max_benchmarks.csv')

    if os.path.exists(benchmarks_file):
        # 新版: 单一 benchmarks CSV，直接复制
        print(f"📄 Using new unified benchmarks CSV: {benchmarks_file}")
        return copy_csv(benchmarks_file, output_file)
    elif os.path.exists(e2e_file) and os.path.exists(inter_file):
        # 旧版: 合并 e2e + interactivity
        print(f"📄 Using legacy e2e + interactivity CSVs")
        return merge_legacy_csvs(e2e_file, inter_file, output_file)
    elif len(csv_files) == 1:
        # 只有一个 CSV 文件
        print(f"📄 Single CSV file found: {csv_files[0]}")
        return copy_csv(csv_files[0], output_file)
    else:
        # 多个 CSV 文件，简单合并
        print(f"📄 Merging {len(csv_files)} CSV files...")
        return merge_multiple_csvs(csv_files, output_file)


def copy_csv(src_file: str, dst_file: str) -> dict:
    """复制 CSV 文件"""
    os.makedirs(os.path.dirname(dst_file) if os.path.dirname(dst_file) else '.', exist_ok=True)

    rows = []
    fieldnames = []
    with open(src_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    with open(dst_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Output saved: {dst_file} ({len(rows)} records)")
    return {
        'total_records': len(rows),
        'columns': len(fieldnames),
        'source': 'copy',
    }


def merge_multiple_csvs(csv_files: list, output_file: str) -> dict:
    """合并多个 CSV 文件"""
    all_rows = []
    all_fieldnames = []

    for csv_file in csv_files:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not all_fieldnames:
                all_fieldnames = list(reader.fieldnames)
            else:
                for fn in reader.fieldnames:
                    if fn not in all_fieldnames:
                        all_fieldnames.append(fn)
            for row in reader:
                all_rows.append(row)

    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"✅ Merged output saved: {output_file} ({len(all_rows)} records)")
    return {
        'total_records': len(all_rows),
        'columns': len(all_fieldnames),
        'source': 'merge',
    }


def merge_legacy_csvs(e2e_file: str, inter_file: str, output_file: str) -> dict:
    """合并旧版 e2e + interactivity CSV 文件（向后兼容）"""
    # 定义合并键
    key_fields = ['model_name', 'sequence_length', 'conc', 'hwKey', 'precision', 'tp']

    # 读取 e2e 数据
    e2e_rows = {}
    e2e_fieldnames = []
    with open(e2e_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        e2e_fieldnames = list(reader.fieldnames)
        for row in reader:
            key = tuple(row.get(k, '') for k in key_fields)
            e2e_rows[key] = row

    # 读取 interactivity 数据
    inter_rows = {}
    inter_fieldnames = []
    with open(inter_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        inter_fieldnames = list(reader.fieldnames)
        for row in reader:
            key = tuple(row.get(k, '') for k in key_fields)
            inter_rows[key] = row

    # 确定输出列
    e2e_data_cols = [c for c in e2e_fieldnames if c not in key_fields and c not in ['model_name', 'sequence_length']]
    inter_data_cols = [c for c in inter_fieldnames if c not in key_fields and c not in ['model_name', 'sequence_length']]

    output_columns = key_fields[:]
    for col in e2e_data_cols:
        output_columns.append(f"e2e_{col}")
    for col in inter_data_cols:
        output_columns.append(f"inter_{col}")

    # 合并
    all_keys = set(e2e_rows.keys()) | set(inter_rows.keys())
    merged_rows = []

    for key in sorted(all_keys):
        merged_row = {}
        e2e_row = e2e_rows.get(key, {})
        inter_row = inter_rows.get(key, {})

        for i, k in enumerate(key_fields):
            merged_row[k] = key[i]

        for col in e2e_data_cols:
            merged_row[f"e2e_{col}"] = e2e_row.get(col, '')
        for col in inter_data_cols:
            merged_row[f"inter_{col}"] = inter_row.get(col, '')

        merged_rows.append(merged_row)

    # 保存
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(merged_rows)

    print(f"✅ Merged output saved: {output_file} ({len(merged_rows)} records)")
    return {
        'total_records': len(merged_rows),
        'columns': len(output_columns),
        'source': 'legacy_merge',
    }


def main():
    parser = argparse.ArgumentParser(
        description='合并 InferenceX CSV 数据文件'
    )
    parser.add_argument(
        '--input-dir', '-i',
        default=None,
        help='输入 CSV 文件目录 (默认: data/processed/csv/inferencex)'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='输出合并后的 CSV 文件路径 (默认: data/processed/csv/inferencex/inference_max_merged.csv)'
    )

    args = parser.parse_args()

    storage = DataStorage()

    # 设置输入目录
    if args.input_dir is None:
        input_directory = str(storage.processed_dir / 'csv' / 'inferencex')
    else:
        input_directory = args.input_dir

    # 设置输出文件
    if args.output is None:
        output_file = str(storage.processed_dir / 'csv' / 'inferencex' / 'inference_max_merged.csv')
    else:
        output_file = args.output

    if not os.path.exists(input_directory):
        print(f"❌ Input directory {input_directory} does not exist")
        return

    print("🚀 Starting CSV merge...")
    result = merge_or_copy_csv(input_directory, output_file)

    if result:
        file_size = os.path.getsize(output_file)
        print(f"\n🎉 Merge completed!")
        print(f"📄 Output: {output_file}")
        print(f"📊 Size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
        print(f"📈 Records: {result['total_records']:,}")
        print(f"📋 Columns: {result['columns']}")
    else:
        print("❌ Merge failed!")


if __name__ == "__main__":
    main()
