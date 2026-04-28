#!/usr/bin/env python
"""
OpenRouter 应用使用量爬虫 - 主入口

支持两种数据获取方式：
1. API 端点（优先）
2. DOM 爬取（备用）

使用示例：
    python scraper.py
    python scraper.py --app claude-code --output ./output
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# 导入子模块
try:
    from .api_fetcher import try_find_api_endpoint
    from .dom_scraper import fetch_from_dom
    from .parser import parse_usage_data, create_metadata_df
except ImportError:
    # 直接运行时使用绝对导入
    from api_fetcher import try_find_api_endpoint
    from dom_scraper import fetch_from_dom
    from parser import parse_usage_data, create_metadata_df

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("警告: pandas 未安装，无法导出 Excel")


def save_raw_response(data, output_dir, app_name, source_type, extension="json"):
    """
    保存原始响应数据

    参数:
        data: 原始数据
        output_dir: 输出目录
        app_name: 应用名称
        source_type: 数据来源类型
        extension: 文件扩展名

    返回:
        str: 保存的文件路径
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"raw_response_{source_type}_{app_name}_{timestamp}.{extension}"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            if extension == "json":
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))

        print(f"  原始数据已保存: {filepath}")
        return filepath
    except Exception as e:
        print(f"  保存原始数据失败: {e}")
        return None


def export_to_excel(df_usage, df_metadata, output_dir, app_name):
    """
    导出数据到 Excel 文件

    参数:
        df_usage: 使用量数据 DataFrame
        df_metadata: 元数据 DataFrame
        output_dir: 输出目录
        app_name: 应用名称

    返回:
        str: Excel 文件路径
    """
    if not PANDAS_AVAILABLE:
        print("  无法导出 Excel: pandas 未安装")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{app_name}_usage_{timestamp}.xlsx"
    filepath = os.path.join(output_dir, filename)

    try:
        # 转换 token 数量为 Billion 单位
        df_export = df_usage.copy()

        # 找出所有 token 相关的列
        token_columns = [col for col in df_export.columns if 'token' in col.lower()]

        for col in token_columns:
            if pd.api.types.is_numeric_dtype(df_export[col]):
                # 转换为 Billion (除以 10^9)
                df_export[col] = df_export[col] / 1_000_000_000
                # 重命名列，添加单位说明
                new_col_name = col.replace('tokens', 'tokens_B').replace('token', 'token_B')
                df_export.rename(columns={col: new_col_name}, inplace=True)

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 写入使用量数据
            if not df_export.empty:
                df_export.to_excel(writer, sheet_name='usage_chart', index=False)
                print(f"  usage_chart: {len(df_export)} 行, {len(df_export.columns)} 列")
                print(f"  Token 数量已转换为 Billion 单位")

            # 写入元数据
            if not df_metadata.empty:
                df_metadata.to_excel(writer, sheet_name='metadata', index=False)
                print(f"  metadata: {len(df_metadata)} 行, {len(df_metadata.columns)} 列")

        print(f"\n[OK] Excel 文件已保存: {filepath}")
        return filepath
    except Exception as e:
        print(f"\n[ERROR] 导出 Excel 失败: {e}")
        return None


def fetch_app_usage(app_name="claude-code", output_dir=None):
    """
    获取应用使用量数据（主函数）

    参数:
        app_name: 应用名称（默认 "claude-code"）
        output_dir: 输出目录（默认为当前目录）

    返回:
        dict: {
            "success": bool,
            "data": pd.DataFrame/None,
            "metadata": dict,
            "files": {"raw": str, "excel": str}
        }
    """
    print(f"\n{'='*60}")
    print(f"OpenRouter 应用使用量爬虫")
    print(f"应用名称: {app_name}")
    print(f"{'='*60}\n")

    # 设置输出目录
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)

    fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = {
        "success": False,
        "data": None,
        "metadata": {},
        "files": {"raw": None, "excel": None}
    }

    # 方法1: 尝试 API 端点
    print("=" * 60)
    print("方法1: 尝试查找 API 端点")
    print("=" * 60)

    api_result = try_find_api_endpoint(app_name)

    if api_result["success"]:
        print(f"\n[OK] 成功从 API 获取数据")

        # 保存原始响应
        raw_file = save_raw_response(
            api_result["data"],
            output_dir,
            app_name,
            "api",
            "json"
        )
        result["files"]["raw"] = raw_file

        # 解析数据
        df_usage = parse_usage_data(api_result["data"], source_type="api")

        if not df_usage.empty:
            # 创建元数据
            df_metadata = create_metadata_df(
                app_name=app_name,
                fetch_time=fetch_time,
                source_type="API",
                endpoint=api_result.get("endpoint"),
                record_count=len(df_usage)
            )

            # 导出 Excel
            excel_file = export_to_excel(df_usage, df_metadata, output_dir, app_name)
            result["files"]["excel"] = excel_file

            result["success"] = True
            result["data"] = df_usage
            result["metadata"] = {
                "source": "API",
                "endpoint": api_result.get("endpoint"),
                "record_count": len(df_usage)
            }

            return result

    # 方法2: DOM 爬取
    print("\n" + "=" * 60)
    print("方法2: 使用 DOM 爬取")
    print("=" * 60)

    app_url = f"https://openrouter.ai/apps/{app_name}"
    dom_result = fetch_from_dom(app_name, app_url)

    if dom_result["success"]:
        print(f"\n[OK] 成功从 DOM 提取数据")

        # 保存原始响应
        if dom_result.get("html"):
            raw_file = save_raw_response(
                dom_result["html"],
                output_dir,
                app_name,
                "dom",
                "html"
            )
            result["files"]["raw"] = raw_file

        # 保存提取的数据
        if dom_result.get("data"):
            json_file = save_raw_response(
                dom_result["data"],
                output_dir,
                app_name,
                "dom_data",
                "json"
            )

        # 解析数据
        df_usage = parse_usage_data(dom_result["data"], source_type="dom")

        if not df_usage.empty:
            # 创建元数据
            df_metadata = create_metadata_df(
                app_name=app_name,
                fetch_time=fetch_time,
                source_type="DOM",
                endpoint=app_url,
                record_count=len(df_usage)
            )

            # 导出 Excel
            excel_file = export_to_excel(df_usage, df_metadata, output_dir, app_name)
            result["files"]["excel"] = excel_file

            result["success"] = True
            result["data"] = df_usage
            result["metadata"] = {
                "source": "DOM",
                "url": app_url,
                "record_count": len(df_usage)
            }

            return result

    # 两种方法都失败
    print("\n" + "=" * 60)
    print("[X] 所有方法都失败")
    print("=" * 60)
    result["metadata"] = {
        "error": "无法从 API 或 DOM 获取数据"
    }

    return result


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='OpenRouter 应用使用量爬虫'
    )
    parser.add_argument(
        '--app',
        default='claude-code',
        help='应用名称（默认: claude-code）'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='输出目录（默认: 当前目录）'
    )

    args = parser.parse_args()

    # 执行爬取
    result = fetch_app_usage(
        app_name=args.app,
        output_dir=args.output
    )

    # 打印结果摘要
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"成功: {result['success']}")
    if result['success']:
        print(f"数据来源: {result['metadata'].get('source')}")
        print(f"记录数: {result['metadata'].get('record_count')}")
        print(f"原始文件: {result['files'].get('raw')}")
        print(f"Excel 文件: {result['files'].get('excel')}")
    else:
        print(f"错误: {result['metadata'].get('error')}")

    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
