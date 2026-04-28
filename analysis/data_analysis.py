"""
数据解析模块 - 基于 analysis.md 实现
实现价格监控、性能监控、交叉分析等功能
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from datetime import datetime

# ============================================================
# 一、数据准备
# ============================================================

def load_data(file_path):
    """加载解析后的 Excel 数据"""
    xls = pd.ExcelFile(file_path)
    print(f"加载文件: {file_path}")
    print(f"Sheet列表: {xls.sheet_names}")

    data = {}
    sheets = [
        ('模型详情汇总', 'model_details'),
        ('价格分析', 'price_analysis'),
        ('性能分析', 'performance_analysis'),
        ('推理模型', 'reasoning_models'),
        ('可用性数据', 'availability'),
        ('基准测试数据', 'benchmark'),
        ('设计竞技场数据', 'design_arena'),
        ('Summary汇总', 'summary')
    ]

    for sheet_name, key in sheets:
        if sheet_name in xls.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            data[key] = df
            print(f"  {sheet_name}: {len(df)} 行")
        else:
            data[key] = pd.DataFrame()
            print(f"  {sheet_name}: 不存在")

    return data

def preprocess_data(data):
    """数据预处理"""
    # 处理可用性数据的日期
    if 'availability' in data and not data['availability'].empty:
        if 'date' in data['availability'].columns:
            data['availability']['date'] = pd.to_datetime(data['availability']['date'], errors='coerce')

    # 处理基准测试数据 - 解析 benchmark_data JSON
    if 'benchmark' in data and not data['benchmark'].empty:
        df = data['benchmark']
        if 'benchmark_data' in df.columns:
            df['AA_index'] = df['benchmark_data'].apply(
                lambda x: extract_benchmark_value(x, 'artificial_analysis_intelligence_index')
            )
            df['AA_coding_index'] = df['benchmark_data'].apply(
                lambda x: extract_benchmark_value(x, 'artificial_analysis_coding_index')
            )
            df['AA_agentic_index'] = df['benchmark_data'].apply(
                lambda x: extract_benchmark_value(x, 'artificial_analysis_agentic_index')
            )

    return data

def extract_benchmark_value(json_str, key):
    """从 benchmark_data JSON 中提取指定键值"""
    if pd.isna(json_str) or json_str == '':
        return None
    try:
        data = json.loads(json_str)
        return data.get(key)
    except:
        return None

# ============================================================
# 二、交叉筛选法
# ============================================================

def filter_models(df, free_only=False, reasoning_only=None,
                  max_prompt_price=None, max_completion_price=None,
                  max_p50_latency=None):
    """
    多条件筛选模型
    - free_only: 仅免费模型
    - reasoning_only: True=仅推理模型, False=仅非推理模型, None=全部
    - max_prompt_price: 最大 prompt 价格
    - max_completion_price: 最大 completion 价格
    - max_p50_latency: 最大 P50 延迟
    """
    result = df.copy()

    if free_only and 'is_free' in result.columns:
        result = result[result['is_free'] == True]

    if reasoning_only is not None and 'supports_reasoning' in result.columns:
        result = result[result['supports_reasoning'] == reasoning_only]

    if max_prompt_price is not None and 'pricing_prompt' in result.columns:
        result = result[result['pricing_prompt'] <= max_prompt_price]

    if max_completion_price is not None and 'pricing_completion' in result.columns:
        result = result[result['pricing_completion'] <= max_completion_price]

    if max_p50_latency is not None and 'stats_p50_latency' in result.columns:
        result = result[result['stats_p50_latency'] <= max_p50_latency]

    return result

# ============================================================
# 三、排序对比法
# ============================================================

def get_cheapest_models(df, n=10):
    """获取最便宜的模型（按 completion 价格）"""
    if 'pricing_completion' not in df.columns:
        return pd.DataFrame()
    result = df[df['pricing_completion'] > 0].nsmallest(n, 'pricing_completion')
    return result[['model_slug', 'provider_name', 'pricing_prompt', 'pricing_completion']]

def get_fastest_models(df, n=10):
    """获取延迟最低的模型"""
    if 'stats_p50_latency' not in df.columns:
        return pd.DataFrame()
    result = df[df['stats_p50_latency'].notna()].nsmallest(n, 'stats_p50_latency')
    return result[['model_slug', 'provider_name', 'stats_p50_latency', 'stats_p99_latency']]

def get_highest_throughput_models(df, n=10):
    """获取吞吐量最高的模型"""
    if 'stats_p50_throughput' not in df.columns:
        return pd.DataFrame()
    result = df[df['stats_p50_throughput'].notna()].nlargest(n, 'stats_p50_throughput')
    return result[['model_slug', 'provider_name', 'stats_p50_throughput', 'stats_p99_throughput']]

def compare_providers(df, model_name_pattern):
    """对比同一模型不同供应商的性能和价格"""
    result = df[df['model_slug'].str.contains(model_name_pattern, case=False, na=False)]
    cols = ['model_slug', 'provider_name', 'pricing_prompt', 'pricing_completion',
            'stats_p50_latency', 'stats_p50_throughput']
    available_cols = [c for c in cols if c in result.columns]
    return result[available_cols].sort_values('pricing_completion')

# ============================================================
# 四、阈值告警法
# ============================================================

def check_uptime_alerts(availability_df, threshold=95.0):
    """检查可用性低于阈值的模型"""
    if availability_df.empty or 'uptime' not in availability_df.columns:
        return pd.DataFrame()

    alerts = availability_df[availability_df['uptime'] < threshold].copy()
    alerts = alerts.sort_values('uptime')
    return alerts[['model_slug', 'uptime', 'date']] if 'date' in alerts.columns else alerts[['model_slug', 'uptime']]

def check_latency_alerts(perf_df, p99_threshold=5000):
    """检查 P99 延迟超过阈值的模型"""
    if perf_df.empty or 'stats_p99_latency' not in perf_df.columns:
        return pd.DataFrame()

    alerts = perf_df[perf_df['stats_p99_latency'] > p99_threshold].copy()
    alerts = alerts.sort_values('stats_p99_latency', ascending=False)
    return alerts[['model_slug', 'provider_name', 'stats_p50_latency', 'stats_p99_latency']]

# ============================================================
# 五、性价比排名计算
# ============================================================

def calculate_value_score(price_df, benchmark_df):
    """计算性价比分数"""
    if price_df.empty or benchmark_df.empty:
        return pd.DataFrame()

    # 合并价格和基准测试数据
    if 'AA_index' not in benchmark_df.columns:
        return pd.DataFrame()

    # 获取每个模型的最高 AA_index
    benchmark_scores = benchmark_df.groupby('model_slug')['AA_index'].max().reset_index()

    # 合并
    merged = price_df.merge(benchmark_scores, on='model_slug', how='inner')

    if merged.empty:
        return pd.DataFrame()

    # 过滤有效数据
    merged = merged[(merged['pricing_completion'] > 0) & (merged['AA_index'].notna())]

    if merged.empty:
        return pd.DataFrame()

    # 计算总价格（每百万 token）
    merged['total_price_per_million'] = (merged['pricing_prompt'] + merged['pricing_completion']) * 1e6

    # 计算性价比分数
    merged['value_score'] = merged['AA_index'] / merged['total_price_per_million']

    # 排序
    result = merged.sort_values('value_score', ascending=False)

    cols = ['model_slug', 'provider_name', 'AA_index', 'pricing_prompt', 'pricing_completion',
            'total_price_per_million', 'value_score']
    available_cols = [c for c in cols if c in result.columns]

    return result[available_cols]

# ============================================================
# 六、推理模型专项分析
# ============================================================

def analyze_reasoning_models(reasoning_df):
    """推理模型专项分析"""
    if reasoning_df.empty:
        return {}

    results = {}

    # 最低延迟
    if 'stats_p50_latency' in reasoning_df.columns:
        valid = reasoning_df[reasoning_df['stats_p50_latency'].notna()]
        if not valid.empty:
            results['lowest_latency'] = valid.nsmallest(5, 'stats_p50_latency')[
                ['model_slug', 'provider_name', 'stats_p50_latency', 'pricing_completion']
            ]

    # 最高吞吐
    if 'stats_p50_throughput' in reasoning_df.columns:
        valid = reasoning_df[reasoning_df['stats_p50_throughput'].notna()]
        if not valid.empty:
            results['highest_throughput'] = valid.nlargest(5, 'stats_p50_throughput')[
                ['model_slug', 'provider_name', 'stats_p50_throughput', 'pricing_completion']
            ]

    # 最低价格
    if 'pricing_completion' in reasoning_df.columns:
        valid = reasoning_df[reasoning_df['pricing_completion'] > 0]
        if not valid.empty:
            results['cheapest'] = valid.nsmallest(5, 'pricing_completion')[
                ['model_slug', 'provider_name', 'pricing_prompt', 'pricing_completion']
            ]

    return results

# ============================================================
# 七、可用性风险识别
# ============================================================

def identify_availability_risks(availability_df, days=3, threshold=95.0):
    """识别可用性风险"""
    if availability_df.empty or 'uptime' not in availability_df.columns:
        return pd.DataFrame()

    # 获取最近 N 天数据
    if 'date' in availability_df.columns:
        max_date = availability_df['date'].max()
        recent = availability_df[availability_df['date'] >= (max_date - pd.Timedelta(days=days))]
    else:
        recent = availability_df

    # 计算平均可用性
    if 'model_slug' in recent.columns:
        avg_uptime = recent.groupby('model_slug').agg({
            'uptime': ['mean', 'min', 'count']
        }).reset_index()
        avg_uptime.columns = ['model_slug', 'avg_uptime', 'min_uptime', 'sample_count']

        # 筛选高风险
        risks = avg_uptime[avg_uptime['avg_uptime'] < threshold].sort_values('avg_uptime')
        return risks

    return pd.DataFrame()

# ============================================================
# 八、质量验证逻辑
# ============================================================

def analyze_quality_benchmark(benchmark_df, design_arena_df):
    """分析基准测试和设计竞技场数据"""
    results = {}

    # 基准测试分析
    if not benchmark_df.empty and 'AA_index' in benchmark_df.columns:
        valid = benchmark_df[benchmark_df['AA_index'].notna()]
        if not valid.empty:
            results['top_intelligence'] = valid.nlargest(10, 'AA_index')[
                ['model_slug', 'AA_index', 'AA_coding_index', 'AA_agentic_index']
            ]

    if not benchmark_df.empty and 'AA_coding_index' in benchmark_df.columns:
        valid = benchmark_df[benchmark_df['AA_coding_index'].notna()]
        if not valid.empty:
            results['top_coding'] = valid.nlargest(10, 'AA_coding_index')[
                ['model_slug', 'AA_index', 'AA_coding_index', 'AA_agentic_index']
            ]

    return results

# ============================================================
# 九、供应商健康度分析
# ============================================================

def analyze_provider_health(model_details_df, availability_df):
    """分析供应商健康度"""
    results = {}

    # 按供应商统计模型数量
    if 'provider_name' in model_details_df.columns:
        provider_models = model_details_df.groupby('provider_name').size().reset_index(name='model_count')
        results['provider_model_count'] = provider_models.sort_values('model_count', ascending=False).head(20)

    # 按供应商统计平均可用性
    if not availability_df.empty and 'uptime' in availability_df.columns:
        # 需要关联 provider_name
        if 'model_slug' in availability_df.columns and 'provider_name' in model_details_df.columns:
            merged = availability_df.merge(
                model_details_df[['model_slug', 'provider_name']].drop_duplicates(),
                on='model_slug', how='left'
            )
            if 'provider_name' in merged.columns:
                provider_uptime = merged.groupby('provider_name').agg({
                    'uptime': 'mean'
                }).reset_index()
                provider_uptime.columns = ['provider_name', 'avg_uptime']
                results['provider_uptime'] = provider_uptime.sort_values('avg_uptime', ascending=False)

    return results

# ============================================================
# 主程序
# ============================================================

def main():
    # 文件路径
    base_path = Path("D:/ai/crawler/inferencex-scraper/analysis")
    input_file = base_path / "parsed_analysis_20260424_160331.xlsx"

    # 查找最新的解析文件
    if not input_file.exists():
        files = list(base_path.glob("parsed_analysis_*.xlsx"))
        if files:
            input_file = max(files, key=lambda x: x.stat().st_mtime)
            print(f"使用最新文件: {input_file}")
        else:
            print("未找到解析文件，请先运行 parse_model_details.py")
            return

    # 加载数据
    print("\n" + "="*60)
    print("一、数据加载")
    print("="*60)
    data = load_data(input_file)
    data = preprocess_data(data)

    # 生成结论
    conclusions = []
    conclusions.append(f"# AI 模型性能与价格监控分析报告")
    conclusions.append(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    conclusions.append(f"\n数据来源: {input_file.name}")

    # ===== 二、价格分析 =====
    print("\n" + "="*60)
    print("二、价格分析")
    print("="*60)
    conclusions.append("\n\n---\n\n## 一、价格分析\n")

    price_df = data.get('price_analysis', pd.DataFrame())
    if not price_df.empty:
        # 最便宜模型
        cheapest = get_cheapest_models(price_df, 10)
        if not cheapest.empty:
            conclusions.append("\n### 1. 最便宜的模型（按 completion 价格排序）\n")
            conclusions.append(cheapest.to_markdown(index=False))

        # 价格统计
        conclusions.append("\n\n### 2. 价格统计摘要\n")
        price_stats = price_df[['pricing_prompt', 'pricing_completion']].describe()
        conclusions.append("```\n")
        conclusions.append(price_stats.to_string())
        conclusions.append("\n```")

    # ===== 三、性能分析 =====
    print("\n" + "="*60)
    print("三、性能分析")
    print("="*60)
    conclusions.append("\n\n---\n\n## 二、性能分析\n")

    perf_df = data.get('performance_analysis', pd.DataFrame())
    if not perf_df.empty:
        # 最快模型
        fastest = get_fastest_models(perf_df, 10)
        if not fastest.empty:
            conclusions.append("\n### 1. 延迟最低的模型（P50 Latency）\n")
            conclusions.append(fastest.to_markdown(index=False))

        # 最高吞吐
        highest_tp = get_highest_throughput_models(perf_df, 10)
        if not highest_tp.empty:
            conclusions.append("\n\n### 2. 吞吐量最高的模型（P50 Throughput）\n")
            conclusions.append(highest_tp.to_markdown(index=False))

        # 延迟告警
        latency_alerts = check_latency_alerts(perf_df, 5000)
        if not latency_alerts.empty:
            conclusions.append("\n\n### 3. 延迟告警（P99 > 5000ms）\n")
            conclusions.append(f"共 {len(latency_alerts)} 个模型 P99 延迟超过 5000ms\n")
            conclusions.append(latency_alerts.head(10).to_markdown(index=False))

    # ===== 四、推理模型分析 =====
    print("\n" + "="*60)
    print("四、推理模型分析")
    print("="*60)
    conclusions.append("\n\n---\n\n## 三、推理模型专项分析\n")

    reasoning_df = data.get('reasoning_models', pd.DataFrame())
    if not reasoning_df.empty:
        reasoning_results = analyze_reasoning_models(reasoning_df)

        conclusions.append(f"\n推理模型总数: {len(reasoning_df)}\n")

        if 'lowest_latency' in reasoning_results:
            conclusions.append("\n### 1. 延迟最低的推理模型\n")
            conclusions.append(reasoning_results['lowest_latency'].to_markdown(index=False))

        if 'highest_throughput' in reasoning_results:
            conclusions.append("\n\n### 2. 吞吐量最高的推理模型\n")
            conclusions.append(reasoning_results['highest_throughput'].to_markdown(index=False))

        if 'cheapest' in reasoning_results:
            conclusions.append("\n\n### 3. 最便宜的推理模型\n")
            conclusions.append(reasoning_results['cheapest'].to_markdown(index=False))

    # ===== 五、性价比分析 =====
    print("\n" + "="*60)
    print("五、性价比分析")
    print("="*60)
    conclusions.append("\n\n---\n\n## 四、性价比分析\n")

    value_df = calculate_value_score(price_df, data.get('benchmark', pd.DataFrame()))
    if not value_df.empty:
        conclusions.append("\n### 性价比 Top 10（AA_index / 每百万token价格）\n")
        conclusions.append(value_df.head(10).to_markdown(index=False))

    # ===== 六、可用性分析 =====
    print("\n" + "="*60)
    print("六、可用性分析")
    print("="*60)
    conclusions.append("\n\n---\n\n## 五、可用性分析\n")

    availability_df = data.get('availability', pd.DataFrame())
    if not availability_df.empty:
        # 可用性告警
        uptime_alerts = check_uptime_alerts(availability_df, 95.0)
        if not uptime_alerts.empty:
            conclusions.append("\n### 1. 可用性告警（Uptime < 95%）\n")
            conclusions.append(f"共 {len(uptime_alerts)} 条记录可用性低于 95%\n")
            conclusions.append(uptime_alerts.head(20).to_markdown(index=False))

        # 可用性风险
        risks = identify_availability_risks(availability_df, days=3, threshold=95.0)
        if not risks.empty:
            conclusions.append("\n\n### 2. 高风险模型（近3天平均可用性 < 95%）\n")
            conclusions.append(risks.to_markdown(index=False))

    # ===== 七、供应商对比 =====
    print("\n" + "="*60)
    print("七、供应商对比")
    print("="*60)
    conclusions.append("\n\n---\n\n## 六、供应商对比分析\n")

    model_details_df = data.get('model_details', pd.DataFrame())
    if not model_details_df.empty:
        # 多供应商模型
        if 'model_slug' in model_details_df.columns and 'provider_name' in model_details_df.columns:
            model_providers = model_details_df.groupby('model_slug')['provider_name'].nunique()
            multi_provider = model_providers[model_providers > 1].sort_values(ascending=False)

            conclusions.append(f"\n### 多供应商模型数量: {len(multi_provider)}\n")

            # 示例：对比具体模型
            if len(multi_provider) > 0:
                sample_model = multi_provider.index[0]
                comparison = compare_providers(model_details_df, sample_model.split('/')[-1] if '/' in sample_model else sample_model)
                if not comparison.empty:
                    conclusions.append(f"\n### 示例：{sample_model} 不同供应商对比\n")
                    conclusions.append(comparison.to_markdown(index=False))

    # ===== 八、基准测试分析 =====
    print("\n" + "="*60)
    print("八、基准测试分析")
    print("="*60)
    conclusions.append("\n\n---\n\n## 七、基准测试排名\n")

    benchmark_df = data.get('benchmark', pd.DataFrame())
    quality_results = analyze_quality_benchmark(benchmark_df, data.get('design_arena', pd.DataFrame()))

    if 'top_intelligence' in quality_results:
        conclusions.append("\n### 1. 智能指数 Top 10\n")
        conclusions.append(quality_results['top_intelligence'].to_markdown(index=False))

    if 'top_coding' in quality_results:
        conclusions.append("\n\n### 2. 编码指数 Top 10\n")
        conclusions.append(quality_results['top_coding'].to_markdown(index=False))

    # ===== 九、供应商健康度 =====
    print("\n" + "="*60)
    print("九、供应商健康度")
    print("="*60)
    conclusions.append("\n\n---\n\n## 八、供应商健康度\n")

    health_results = analyze_provider_health(model_details_df, availability_df)

    if 'provider_model_count' in health_results:
        conclusions.append("\n### 1. 供应商模型数量 Top 20\n")
        conclusions.append(health_results['provider_model_count'].to_markdown(index=False))

    if 'provider_uptime' in health_results:
        conclusions.append("\n\n### 2. 供应商平均可用性\n")
        conclusions.append(health_results['provider_uptime'].head(20).to_markdown(index=False))

    # ===== 十、总结与建议（基于实际数据动态生成）=====
    print("\n" + "="*60)
    print("十、总结与建议")
    print("="*60)
    conclusions.append("\n\n---\n\n## 九、总结与建议（基于数据分析）\n")

    # 1. 价格优化建议
    conclusions.append("\n### 1. 价格优化建议\n")
    if not price_df.empty:
        cheapest_model = price_df[price_df['pricing_completion'] > 0].nsmallest(1, 'pricing_completion')
        if not cheapest_model.empty:
            model = cheapest_model.iloc[0]['model_slug']
            price = cheapest_model.iloc[0]['pricing_completion']
            conclusions.append(f"- **最便宜模型**: `{model}`，completion 价格为 {price:.2e} per token\n")

        # 多供应商模型建议
        if not model_details_df.empty and 'model_slug' in model_details_df.columns:
            model_providers = model_details_df.groupby('model_slug')['provider_name'].nunique()
            multi_provider_count = (model_providers > 1).sum()
            conclusions.append(f"- **多供应商模型**: 共 {multi_provider_count} 个模型有多个供应商，可对比选择最优价格\n")

    # 2. 性能优化建议
    conclusions.append("\n### 2. 性能优化建议\n")
    if not perf_df.empty:
        # 低延迟模型数量
        low_latency_count = (perf_df['stats_p50_latency'] < 1000).sum() if 'stats_p50_latency' in perf_df.columns else 0
        conclusions.append(f"- **低延迟模型**: 共 {low_latency_count} 个模型 P50 延迟 < 1000ms，适合延迟敏感场景\n")

        # 高吞吐模型数量
        high_tp_count = (perf_df['stats_p50_throughput'] > 100).sum() if 'stats_p50_throughput' in perf_df.columns else 0
        conclusions.append(f"- **高吞吐模型**: 共 {high_tp_count} 个模型 P50 吞吐量 > 100 tokens/s\n")

        # 延迟告警数量
        latency_alert_count = (perf_df['stats_p99_latency'] > 5000).sum() if 'stats_p99_latency' in perf_df.columns else 0
        conclusions.append(f"- **延迟告警**: {latency_alert_count} 个模型 P99 延迟 > 5000ms，需关注\n")

    # 3. 可用性建议
    conclusions.append("\n### 3. 可用性建议\n")
    if not availability_df.empty and 'uptime' in availability_df.columns:
        # 高可用供应商
        high_uptime_count = (availability_df['uptime'] >= 99).sum()
        conclusions.append(f"- **高可用记录**: {high_uptime_count} 条记录可用性 >= 99%\n")

        # 低可用告警
        low_uptime_count = (availability_df['uptime'] < 95).sum()
        conclusions.append(f"- **可用性告警**: {low_uptime_count} 条记录可用性 < 95%，需设置备用方案\n")

        # 高风险模型
        risks = identify_availability_risks(availability_df, days=3, threshold=95.0)
        if not risks.empty:
            conclusions.append(f"- **高风险模型**: {len(risks)} 个模型近3天平均可用性 < 95%\n")
            for _, row in risks.head(3).iterrows():
                conclusions.append(f"  - `{row['model_slug']}`: 平均可用性 {row['avg_uptime']:.1f}%\n")

    # 4. 推理模型建议
    conclusions.append("\n### 4. 推理模型建议\n")
    if not reasoning_df.empty:
        conclusions.append(f"- **推理模型总数**: {len(reasoning_df)} 个\n")

        if 'stats_p50_latency' in reasoning_df.columns:
            valid = reasoning_df[reasoning_df['stats_p50_latency'].notna()]
            if not valid.empty:
                avg_latency = valid['stats_p50_latency'].mean()
                conclusions.append(f"- **推理模型平均延迟**: {avg_latency:.0f}ms（普遍高于非推理模型）\n")

        # 推荐的推理模型
        if 'stats_p50_latency' in reasoning_df.columns and 'pricing_completion' in reasoning_df.columns:
            valid = reasoning_df[(reasoning_df['stats_p50_latency'].notna()) & (reasoning_df['pricing_completion'] > 0)]
            if not valid.empty:
                # 综合评分：延迟低 + 价格低
                valid = valid.copy()
                valid['score'] = 1 / (valid['stats_p50_latency'] + 1) / (valid['pricing_completion'] + 1e-10)
                best = valid.nlargest(1, 'score')
                if not best.empty:
                    conclusions.append(f"- **推荐推理模型**: `{best.iloc[0]['model_slug']}`（延迟 {best.iloc[0]['stats_p50_latency']:.0f}ms，价格 {best.iloc[0]['pricing_completion']:.2e}）\n")

    # 5. 供应商建议
    conclusions.append("\n### 5. 供应商建议\n")
    if 'provider_uptime' in health_results and not health_results['provider_uptime'].empty:
        top_providers = health_results['provider_uptime'].head(5)
        conclusions.append("- **推荐供应商**（按平均可用性排序）:\n")
        for _, row in top_providers.iterrows():
            conclusions.append(f"  - {row['provider_name']}: {row['avg_uptime']:.1f}%\n")

    # 6. 后续监控建议
    conclusions.append("\n### 6. 后续监控建议\n")
    conclusions.append("- 建立价格变动追踪机制，定期对比历史价格\n")
    conclusions.append("- 设置延迟告警阈值（建议 P99 > 5000ms）\n")
    conclusions.append("- 设置可用性告警阈值（建议 < 95%）\n")
    conclusions.append("- 定期更新性价比排名\n")

    # 保存结论
    output_path = base_path / f"conclusion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(conclusions))

    print(f"\n{'='*60}")
    print(f"分析完成！结论已保存到: {output_path}")
    print(f"{'='*60}")

    return output_path

if __name__ == "__main__":
    main()
