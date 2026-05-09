import pandas as pd
import os

# Paths
openrouter_csv = '/root/inferencex-scraper/openrouter/glm5_output/03_glm5_providers_new.csv'
inferencex_csv = '/root/inferencex-scraper/json_data/glm5_performance.csv'
output_csv = '/root/inferencex-scraper/json_data/glm5_joined_data.csv'
report_md = '/root/inferencex-scraper/GLM5_Joined_Report.md'

def main():
    if not os.path.exists(openrouter_csv) or not os.path.exists(inferencex_csv):
        print("Missing input files.")
        return

    # Load data
    df_or = pd.read_csv(openrouter_csv)
    df_ix = pd.read_csv(inferencex_csv)

    # Clean and Prepare OpenRouter Data
    # Map 'unknown' to common precisions if possible, or just keep it.
    # We rename 'quantization' to 'precision' for joining
    df_or = df_or.rename(columns={'quantization': 'precision'})
    
    # Merge on 'precision'
    # This will create a cartesian product per precision level
    df_joined = pd.merge(df_or, df_ix, on='precision', how='inner')

    # Select and reorder columns for better readability in the final report
    # Key columns: provider, price, hardware, framework, throughput
    cols_to_keep = [
        'provider_name', 'input_price_per_m', 'output_price_per_m', 'precision',
        'hardware', 'framework', 'metrics_tput_per_gpu', 'metrics_mean_itl', 'conc', 'isl', 'osl'
    ]
    
    # Filter to only keep relevant columns if they exist
    cols_to_keep = [c for c in cols_to_keep if c in df_joined.columns]
    df_summary = df_joined[cols_to_keep].copy()

    # Save to CSV
    df_joined.to_csv(output_csv, index=False)
    print(f"Joined data saved to {output_csv}")

    # Generate Markdown Report
    summary_stats = df_summary.groupby(['provider_name', 'hardware', 'precision']).agg({
        'input_price_per_m': 'first',
        'metrics_tput_per_gpu': 'mean'
    }).reset_index()

    report = f"""# GLM-5 数据联合分析报告 (OpenRouter + InferenceX)

## 1. 数据联查说明
本报告将 **OpenRouter** 的供应商价格数据与 **InferenceX** 的硬件性能数据进行了关联分析。
- **关联键**: `precision` (OpenRouter 的 quantization = InferenceX 的 precision)
- **数据量**: 联查后共生成 {len(df_joined)} 条组合记录。

## 2. 价格 vs 性能 概览 (Top 10 组合)

| 供应商 | 硬件 | 精度 | 输入价格 ($/M) | 平均吞吐量 (tokens/s/GPU) |
| :--- | :--- | :--- | :--- | :--- |
"""
    for _, row in summary_stats.sort_values('metrics_tput_per_gpu', ascending=False).head(15).iterrows():
        report += f"| {row['provider_name']} | {row['hardware']} | {row['precision']} | ${row['input_price_per_m']:.2f} | {row['metrics_tput_per_gpu']:.2f} |\n"

    report += f"""
## 3. 结论
通过将价格与基准性能结合，可以更直观地评估不同服务商的技术方案优劣。
完整的联查结果已保存至: `{output_csv}`
"""

    with open(report_md, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Report saved to {report_md}")

if __name__ == "__main__":
    main()
