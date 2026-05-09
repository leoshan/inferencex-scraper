"""
解析 OpenRouter 模型详情 Excel 文件
根据 analysis.md 中的需求，提取价格和性能监控相关信息
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime

def parse_pricing_json(pricing_str):
    """解析 pricing_json 字符串"""
    if pd.isna(pricing_str) or pricing_str == '':
        return {}
    try:
        return json.loads(pricing_str)
    except:
        return {}

def extract_pricing_value(pricing, key_patterns):
    """从pricing字典中提取价格，支持多种键名格式"""
    for key, value in pricing.items():
        for pattern in key_patterns:
            if pattern in key.lower():
                try:
                    return float(value)
                except:
                    return 0
    return 0

def process_endpoint_stats(df):
    """处理 endpoint_stats 数据"""
    results = []

    for idx, row in df.iterrows():
        model_info = {
            'model_slug': row.get('model_slug', ''),
            'provider_name': row.get('provider_name', ''),
            'endpoint_variant': row.get('variant', ''),
            'model_name': row.get('name', ''),
            'context_length': row.get('context_length', 0),
            'is_free': row.get('is_free', False),
        }

        # 解析 pricing_json
        pricing_str = row.get('pricing_json', '')
        pricing = parse_pricing_json(pricing_str)

        # 提取价格信息 - 支持多种键名格式
        model_info['pricing_prompt'] = extract_pricing_value(pricing, ['prompt_tokens', 'prompt'])
        model_info['pricing_completion'] = extract_pricing_value(pricing, ['completion_tokens', 'completion'])
        model_info['pricing_cache_read'] = extract_pricing_value(pricing, ['cached_prompt', 'cache_read', 'input_cache'])
        model_info['pricing_image'] = extract_pricing_value(pricing, ['image'])
        model_info['pricing_request'] = extract_pricing_value(pricing, ['request'])

        # 提取性能统计信息
        model_info['stats_p50_latency'] = row.get('stats_p50_latency', 0)
        model_info['stats_p75_latency'] = row.get('stats_p75_latency', 0)
        model_info['stats_p90_latency'] = row.get('stats_p90_latency', 0)
        model_info['stats_p95_latency'] = row.get('stats_p95_latency', 0)
        model_info['stats_p99_latency'] = row.get('stats_p99_latency', 0)

        model_info['stats_p50_throughput'] = row.get('stats_p50_throughput', 0)
        model_info['stats_p75_throughput'] = row.get('stats_p75_throughput', 0)
        model_info['stats_p90_throughput'] = row.get('stats_p90_throughput', 0)
        model_info['stats_p95_throughput'] = row.get('stats_p95_throughput', 0)
        model_info['stats_p99_throughput'] = row.get('stats_p99_throughput', 0)

        # 提取其他关键信息
        model_info['supports_reasoning'] = row.get('supports_reasoning', False)
        model_info['num_requests'] = row.get('num_requests', 0)
        model_info['quantization'] = row.get('quantization', '')

        results.append(model_info)

    return pd.DataFrame(results)

def process_uptime_data(df):
    """处理 uptime 数据"""
    return df[['model_slug', 'uptime', 'date']].copy() if 'uptime' in df.columns else df

def process_artificial_analysis(df):
    """处理 artificial_analysis 基准测试数据"""
    # 提取关键基准测试指标
    result_cols = ['model_slug']
    for col in df.columns:
        if 'benchmark' in col.lower() or 'score' in col.lower() or 'index' in col.lower():
            result_cols.append(col)
    return df[result_cols].copy() if len(result_cols) > 1 else df

def process_design_arena(df):
    """处理 design_arena 数据"""
    return df.copy()

def analyze_file(file_path):
    """分析单个 Excel 文件"""
    print(f"\n{'='*60}")
    print(f"解析文件: {file_path.name}")
    print(f"{'='*60}")

    # 获取所有 sheet 名称
    xls = pd.ExcelFile(file_path)
    sheet_names = xls.sheet_names
    print(f"\nSheet 列表: {sheet_names}")

    results = {}

    # 读取 Summary sheet
    if 'Summary' in sheet_names:
        summary_df = pd.read_excel(file_path, sheet_name='Summary')
        print(f"\nSummary - 行数: {len(summary_df)}")
        results['summary'] = summary_df

    # 读取 endpoint_stats_all_models sheet (核心数据)
    if 'endpoint_stats_all_models' in sheet_names:
        endpoint_df = pd.read_excel(file_path, sheet_name='endpoint_stats_all_models')
        print(f"\nendpoint_stats_all_models - 行数: {len(endpoint_df)}, 列数: {len(endpoint_df.columns)}")
        print(f"列名: {list(endpoint_df.columns)[:20]}...")  # 只显示前20列

        # 处理 endpoint 数据
        processed_df = process_endpoint_stats(endpoint_df)
        results['endpoint_stats'] = processed_df

    # 读取 uptime_recent_all_models sheet
    if 'uptime_recent_all_models' in sheet_names:
        uptime_df = pd.read_excel(file_path, sheet_name='uptime_recent_all_models')
        print(f"\nuptime_recent_all_models - 行数: {len(uptime_df)}")
        results['uptime'] = process_uptime_data(uptime_df)

    # 读取 artificial_analysis_all_models sheet
    if 'artificial_analysis_all_models' in sheet_names:
        analysis_df = pd.read_excel(file_path, sheet_name='artificial_analysis_all_models')
        print(f"\nartificial_analysis_all_models - 行数: {len(analysis_df)}")
        results['artificial_analysis'] = process_artificial_analysis(analysis_df)

    # 读取 design_arena_all_models sheet
    if 'design_arena_all_models' in sheet_names:
        arena_df = pd.read_excel(file_path, sheet_name='design_arena_all_models')
        print(f"\ndesign_arena_all_models - 行数: {len(arena_df)}")
        results['design_arena'] = process_design_arena(arena_df)

    return results

def generate_analysis_report(all_data):
    """生成分析报告"""
    print(f"\n{'='*60}")
    print("生成分析报告")
    print(f"{'='*60}")

    # 合并所有 endpoint_stats 数据
    endpoint_dfs = [data['endpoint_stats'] for data in all_data if 'endpoint_stats' in data]
    if endpoint_dfs:
        combined_endpoint = pd.concat(endpoint_dfs, ignore_index=True)

        # 价格分析
        print("\n=== 价格分析 ===")
        print(f"总模型数: {len(combined_endpoint)}")

        free_models = combined_endpoint[combined_endpoint['is_free'] == True]
        print(f"免费模型数: {len(free_models)}")

        reasoning_models = combined_endpoint[combined_endpoint['supports_reasoning'] == True]
        print(f"推理模型数: {len(reasoning_models)}")

        # 价格统计
        price_cols = ['pricing_prompt', 'pricing_completion', 'pricing_cache_read']
        if all(col in combined_endpoint.columns for col in price_cols):
            print("\n价格统计 (每token价格):")
            # 过滤掉0值进行统计
            non_zero_prices = combined_endpoint[price_cols].replace(0, pd.NA).dropna()
            if len(non_zero_prices) > 0:
                print(non_zero_prices.describe())
            else:
                print("无有效价格数据")

        # 性能分析
        print("\n=== 性能分析 ===")
        latency_cols = ['stats_p50_latency', 'stats_p90_latency', 'stats_p99_latency']
        if all(col in combined_endpoint.columns for col in latency_cols):
            print("\n延迟统计 (ms):")
            print(combined_endpoint[latency_cols].describe())

        throughput_cols = ['stats_p50_throughput', 'stats_p90_throughput', 'stats_p99_throughput']
        if all(col in combined_endpoint.columns for col in throughput_cols):
            print("\n吞吐量统计 (tokens/s):")
            print(combined_endpoint[throughput_cols].describe())

        # 供应商对比
        print("\n=== 供应商对比 ===")
        model_providers = combined_endpoint.groupby('model_slug')['provider_name'].nunique()
        multi_provider = model_providers[model_providers > 1]
        print(f"多供应商模型数: {len(multi_provider)}")

        return combined_endpoint, free_models, reasoning_models

    return None, None, None

def main():
    # 文件路径
    base_path = Path("D:/ai/crawler/inferencex-scraper/openrouter/get_model_details")

    # 要解析的文件
    files = [
        "openrouter_batch_model_details_20260417_160253.xlsx",
        "openrouter_batch_model_details_20260418_142041_start101_end300.xlsx"
    ]

    all_data = []

    for file_name in files:
        file_path = base_path / file_name
        if not file_path.exists():
            print(f"文件不存在: {file_path}")
            continue

        data = analyze_file(file_path)
        data['source_file'] = file_name
        all_data.append(data)

    # 生成分析报告
    combined_endpoint, free_models, reasoning_models = generate_analysis_report(all_data)

    # 输出结果到 Excel
    if combined_endpoint is not None:
        output_path = Path("D:/ai/crawler/inferencex-scraper/analysis") / f"parsed_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 模型详情汇总
            combined_endpoint.to_excel(writer, sheet_name='模型详情汇总', index=False)

            # 价格分析
            price_analysis = combined_endpoint[['model_slug', 'provider_name', 'model_name',
                                                'pricing_prompt', 'pricing_completion', 'pricing_cache_read',
                                                'is_free', 'supports_reasoning', 'quantization']]
            price_analysis.to_excel(writer, sheet_name='价格分析', index=False)

            # 性能分析
            perf_analysis = combined_endpoint[['model_slug', 'provider_name',
                                               'stats_p50_latency', 'stats_p90_latency', 'stats_p99_latency',
                                               'stats_p50_throughput', 'stats_p90_throughput', 'stats_p99_throughput']]
            perf_analysis.to_excel(writer, sheet_name='性能分析', index=False)

            # 免费模型
            if len(free_models) > 0:
                free_models.to_excel(writer, sheet_name='免费模型', index=False)

            # 推理模型
            if len(reasoning_models) > 0:
                reasoning_models.to_excel(writer, sheet_name='推理模型', index=False)

            # 合并所有 Summary 数据
            summary_dfs = [data['summary'] for data in all_data if 'summary' in data]
            if summary_dfs:
                combined_summary = pd.concat(summary_dfs, ignore_index=True)
                combined_summary.to_excel(writer, sheet_name='Summary汇总', index=False)

            # 合并所有 uptime 数据
            uptime_dfs = [data['uptime'] for data in all_data if 'uptime' in data]
            if uptime_dfs:
                combined_uptime = pd.concat(uptime_dfs, ignore_index=True)
                combined_uptime.to_excel(writer, sheet_name='可用性数据', index=False)

            # 合并所有 artificial_analysis 数据
            analysis_dfs = [data['artificial_analysis'] for data in all_data if 'artificial_analysis' in data]
            if analysis_dfs:
                combined_analysis = pd.concat(analysis_dfs, ignore_index=True)
                combined_analysis.to_excel(writer, sheet_name='基准测试数据', index=False)

            # 合并所有 design_arena 数据
            arena_dfs = [data['design_arena'] for data in all_data if 'design_arena' in data]
            if arena_dfs:
                combined_arena = pd.concat(arena_dfs, ignore_index=True)
                combined_arena.to_excel(writer, sheet_name='设计竞技场数据', index=False)

        print(f"\n{'='*60}")
        print(f"解析完成！输出文件: {output_path}")
        print(f"{'='*60}")

if __name__ == "__main__":
    main()
