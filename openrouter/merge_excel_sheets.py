#!/usr/bin/env python3
"""
合并两个多工作表Excel文件的每个对应工作表。

用法：python merge_excel_sheets.py [输出文件路径]

该脚本会：
1. 读取两个Excel文件的所有工作表
2. 检查它们是否有相同的工作表结构
3. 对于每个工作表，合并两个文件的数据
4. 对于不同的工作表类型采用不同的去重策略：
   - Summary工作表：基于model_slug去重
   - Error_Log工作表：基于所有列去重
   - 其他数据工作表：基于所有列去重
5. 生成新的Excel文件，包含所有合并后的工作表
"""

import sys
import os
import pandas as pd
from datetime import datetime

def get_sheet_info(file_path):
    """获取Excel文件的工作表信息"""
    try:
        xls = pd.ExcelFile(file_path)
        return {
            'path': file_path,
            'sheet_names': xls.sheet_names,
            'engine': xls.engine
        }
    except Exception as e:
        print(f"错误：无法读取文件 {file_path}: {e}")
        sys.exit(1)

def read_sheet(file_path, sheet_name):
    """读取指定工作表的DataFrame"""
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print(f"  读取工作表 '{sheet_name}': {len(df)}行 × {len(df.columns)}列")
        return df
    except Exception as e:
        print(f"  错误：无法读取工作表 '{sheet_name}': {e}")
        return pd.DataFrame()

def merge_summary_sheets(df1, df2, sheet_name):
    """
    合并Summary工作表
    基于model_slug去重，保留最后一个出现的记录
    """
    print(f"  合并{sheet_name}工作表...")

    # 检查必需的列
    required_columns = ['model_slug']
    for col in required_columns:
        if col not in df1.columns:
            print(f"  警告：文件1的{sheet_name}工作表缺少列 '{col}'")
            df1[col] = None
        if col not in df2.columns:
            print(f"  警告：文件2的{sheet_name}工作表缺少列 '{col}'")
            df2[col] = None

    # 合并两个DataFrame
    combined = pd.concat([df1, df2], ignore_index=True)
    print(f"    合并后总行数: {len(combined)}")

    # 基于model_slug去重，保留最后一个出现的记录
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset='model_slug', keep='last')
    after_dedup = len(combined)

    if before_dedup != after_dedup:
        print(f"    移除重复记录: {before_dedup - after_dedup}条")

    print(f"    最终行数: {after_dedup}")
    return combined

def merge_error_log_sheets(df1, df2, sheet_name):
    """
    合并Error_Log工作表
    基于所有列去重
    """
    print(f"  合并{sheet_name}工作表...")

    # 合并两个DataFrame
    combined = pd.concat([df1, df2], ignore_index=True)
    print(f"    合并后总行数: {len(combined)}")

    # 基于所有列去重
    before_dedup = len(combined)
    combined = combined.drop_duplicates()
    after_dedup = len(combined)

    if before_dedup != after_dedup:
        print(f"    移除重复记录: {before_dedup - after_dedup}条")

    print(f"    最终行数: {after_dedup}")
    return combined

def merge_data_sheets(df1, df2, sheet_name):
    """
    合并数据工作表（非Summary/Error_Log）
    基于所有列去重
    """
    print(f"  合并{sheet_name}工作表...")

    # 合并两个DataFrame
    combined = pd.concat([df1, df2], ignore_index=True)
    print(f"    合并后总行数: {len(combined)}")

    # 基于所有列去重
    before_dedup = len(combined)
    combined = combined.drop_duplicates()
    after_dedup = len(combined)

    if before_dedup != after_dedup:
        print(f"    移除重复记录: {before_dedup - after_dedup}条")

    print(f"    最终行数: {after_dedup}")
    return combined

def merge_excel_files(file1, file2, output_path):
    """
    合并两个Excel文件的所有工作表
    """
    print("=" * 80)
    print("开始合并Excel文件")
    print("=" * 80)

    # 获取文件信息
    print(f"文件1: {file1}")
    info1 = get_sheet_info(file1)
    print(f"  工作表数量: {len(info1['sheet_names'])}")
    print(f"  工作表列表: {info1['sheet_names']}")

    print(f"\n文件2: {file2}")
    info2 = get_sheet_info(file2)
    print(f"  工作表数量: {len(info2['sheet_names'])}")
    print(f"  工作表列表: {info2['sheet_names']}")

    # 检查工作表结构是否一致
    if set(info1['sheet_names']) != set(info2['sheet_names']):
        print("\n警告：两个文件的工作表结构不一致！")
        print(f"文件1有但文件2没有的工作表: {set(info1['sheet_names']) - set(info2['sheet_names'])}")
        print(f"文件2有但文件1没有的工作表: {set(info2['sheet_names']) - set(info1['sheet_names'])}")

        # 使用两个文件的并集作为要处理的工作表
        all_sheets = sorted(set(info1['sheet_names']).union(set(info2['sheet_names'])))
        print(f"\n将处理的工作表: {all_sheets}")
    else:
        all_sheets = sorted(info1['sheet_names'])
        print(f"\n工作表结构一致，将处理 {len(all_sheets)} 个工作表")

    # 创建Excel写入器
    print(f"\n开始合并工作表...")
    merged_data = {}

    for sheet_name in all_sheets:
        print(f"\n处理工作表: '{sheet_name}'")

        # 读取两个文件的工作表
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()

        if sheet_name in info1['sheet_names']:
            df1 = read_sheet(file1, sheet_name)

        if sheet_name in info2['sheet_names']:
            df2 = read_sheet(file2, sheet_name)

        # 如果两个DataFrame都为空，跳过
        if df1.empty and df2.empty:
            print(f"  警告：两个文件的工作表 '{sheet_name}' 都为空，跳过")
            merged_data[sheet_name] = pd.DataFrame()
            continue

        # 根据工作表类型选择合并策略
        if sheet_name.lower() == 'summary':
            merged_df = merge_summary_sheets(df1, df2, sheet_name)
        elif 'error' in sheet_name.lower():
            merged_df = merge_error_log_sheets(df1, df2, sheet_name)
        else:
            merged_df = merge_data_sheets(df1, df2, sheet_name)

        merged_data[sheet_name] = merged_df

    # 写入新的Excel文件
    print(f"\n{'='*80}")
    print(f"写入合并后的Excel文件: {output_path}")

    try:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            sheets_written = 0

            for sheet_name, df in merged_data.items():
                if df.empty:
                    print(f"  工作表 '{sheet_name}': 空，跳过")
                    continue

                df.to_excel(writer, sheet_name=sheet_name, index=False)
                sheets_written += 1
                print(f"  工作表 '{sheet_name}': {len(df)}行 × {len(df.columns)}列")

            if sheets_written == 0:
                raise ValueError("没有成功写入任何工作表，所有数据框都为空")

        print(f"\n[成功] Excel文件已保存: {output_path}")

        # 显示文件信息
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"  文件大小: {file_size:.2f} KB")
        print(f"  包含工作表: {', '.join([name for name, df in merged_data.items() if not df.empty])}")

        return output_path

    except Exception as e:
        print(f"\n[错误] 保存Excel文件时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数"""
    # 文件路径
    file1 = r"D:\ai\crawler\merged_openrouter_all_sheets_20260420_152513.xlsx"
    file2 = r"D:\ai\crawler\byrequest\openrouter_batch_model_details_20260420_154815.xlsx"

    # 输出文件路径
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"merged_openrouter_all_sheets_{timestamp}.xlsx"

    # 检查输入文件是否存在
    if not os.path.exists(file1):
        print(f"错误：文件不存在 - {file1}")
        sys.exit(1)
    if not os.path.exists(file2):
        print(f"错误：文件不存在 - {file2}")
        sys.exit(1)

    # 执行合并
    result = merge_excel_files(file1, file2, output_path)

    if result:
        print(f"\n{'='*80}")
        print("合并完成！")
        print(f"输出文件: {output_path}")
        sys.exit(0)
    else:
        print(f"\n{'='*80}")
        print("合并失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()