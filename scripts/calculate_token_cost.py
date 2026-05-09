#!/usr/bin/env python3
"""
GLM-5 Token Cost Calculator
============================
根据 InferenceX benchmark 数据中的硬件信息和吞吐量指标，
计算每个 token 的推理成本（按 3 年租赁 TCO 模型）。

计算公式：
    Cost per Token = GPU 每小时成本 / (吞吐量 tok/s × 3600)

新增三列：
    1. cost_per_input_token   — 基于 input throughput 的单 token 成本 ($/token)
    2. cost_per_output_token  — 基于 output throughput 的单 token 成本 ($/token)  
    3. cost_per_total_token    — 基于 total throughput 的综合单 token 成本 ($/token)

同时额外增加以百万 token 为单位的成本列，方便阅读：
    4. cost_per_1m_input_tokens
    5. cost_per_1m_output_tokens
    6. cost_per_1m_total_tokens
"""

import pandas as pd
import sys
import os

# ============================================================
# GPU 每小时 TCO 成本 — 来源: InferenceX (SemiAnalysis)
# 数据写死在 JS bundle: _next/static/chunks/0n_gp9xy1alci.js
# 包含三种成本模型:
#   costh = Hyperscaler (超大规模云厂商自建)
#   costn = Neocloud Giant (新兴云算力巨头自建)
#   costr = 3 Year Rental (3年租赁)
# 单位：美元/GPU/小时
# ============================================================

# 三种成本模型完整数据
GPU_COST_TIERS = {
    "h100":   {"costh": 1.30,  "costn": 1.69,  "costr": 1.30},
    "h200":   {"costh": 1.41,  "costn": 1.74,  "costr": 1.60},
    "b200":   {"costh": 1.95,  "costn": 2.34,  "costr": 2.90},
    "b300":   {"costh": 2.34,  "costn": 2.808, "costr": 3.48},
    "gb200":  {"costh": 2.21,  "costn": 2.75,  "costr": 3.30},
    "gb300":  {"costh": 2.652, "costn": 3.30,  "costr": 3.96},
    "mi300x": {"costh": 1.12,  "costn": 1.40,  "costr": 1.55},
    "mi325x": {"costh": 1.28,  "costn": 1.59,  "costr": 1.80},
    "mi355x": {"costh": 1.48,  "costn": 1.90,  "costr": 2.10},
}

# 默认使用 Neocloud Giant (costn) 作为主计算基准
COST_TIER = "costn"
GPU_HOURLY_COST = {k: v[COST_TIER] for k, v in GPU_COST_TIERS.items()}

def main():
    csv_path = os.path.join(os.path.dirname(__file__), "..", "json_data", "glm5_benchmarks_only.csv")
    csv_path = os.path.abspath(csv_path)
    
    print(f"📂 Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"   Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # 显示硬件分布
    print(f"\n📊 Hardware distribution:")
    print(df['hardware'].value_counts().to_string())
    
    # 映射 GPU 每小时成本
    df['gpu_hourly_cost'] = df['hardware'].map(GPU_HOURLY_COST)
    
    # 获取每行使用的 GPU 数量（取 decode 和 prefill 中较大的）
    df['total_gpus'] = df[['num_decode_gpu', 'num_prefill_gpu']].max(axis=1)
    
    # ============================================================
    # 关键指标说明：
    # metrics_input_tput_per_gpu  — 每块 GPU 的 input token 吞吐量 (tok/s/gpu)
    # metrics_output_tput_per_gpu — 每块 GPU 的 output token 吞吐量 (tok/s/gpu)
    # metrics_tput_per_gpu        — 每块 GPU 的总 token 吞吐量 (tok/s/gpu)
    #
    # 这些是 "per GPU" 指标，所以直接用单卡成本除以单卡吞吐量
    # ============================================================
    
    # 每秒每 GPU 成本 = 每小时成本 / 3600
    df['gpu_cost_per_second'] = df['gpu_hourly_cost'] / 3600.0
    
    # 计算单 token 成本 ($/token)
    # Input: cost_per_second / input_throughput_per_gpu
    df['cost_per_input_token'] = df['gpu_cost_per_second'] / df['metrics_input_tput_per_gpu']
    
    # Output: cost_per_second / output_throughput_per_gpu
    df['cost_per_output_token'] = df['gpu_cost_per_second'] / df['metrics_output_tput_per_gpu']
    
    # Total (综合): cost_per_second / total_throughput_per_gpu
    df['cost_per_total_token'] = df['gpu_cost_per_second'] / df['metrics_tput_per_gpu']

    # 转换为每百万 token 的成本（方便阅读）
    df['cost_per_1m_input_tokens'] = df['cost_per_input_token'] * 1_000_000
    df['cost_per_1m_output_tokens'] = df['cost_per_output_token'] * 1_000_000
    df['cost_per_1m_total_tokens'] = df['cost_per_total_token'] * 1_000_000
    
    # 保存结果
    output_path = csv_path.replace('.csv', '_with_cost.csv')
    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved to: {output_path}")
    
    # ============================================================
    # 输出分析摘要
    # ============================================================
    print("\n" + "="*100)
    print("💰 GLM-5 Token Cost Analysis Summary (per Million Tokens, USD)")
    print("="*100)
    
    # 按硬件+精度+isl/osl+spec_method 分组汇总
    summary_cols = ['hardware', 'framework', 'precision', 'isl', 'osl', 'spec_method', 'conc',
                    'total_gpus', 'gpu_hourly_cost',
                    'metrics_input_tput_per_gpu', 'metrics_output_tput_per_gpu', 'metrics_tput_per_gpu',
                    'cost_per_1m_input_tokens', 'cost_per_1m_output_tokens', 'cost_per_1m_total_tokens']
    
    # 展示每种配置下最优（最低成本）的结果
    print("\n📋 Per-config optimal cost (lowest total cost per million tokens):\n")
    
    group_keys = ['hardware', 'precision', 'isl', 'osl', 'spec_method', 'framework']
    best = df.loc[df.groupby(group_keys)['cost_per_1m_total_tokens'].idxmin()]
    
    display_cols = ['hardware', 'precision', 'isl', 'osl', 'spec_method', 'framework',
                    'conc', 'total_gpus',
                    'cost_per_1m_input_tokens', 'cost_per_1m_output_tokens', 'cost_per_1m_total_tokens',
                    'metrics_tput_per_gpu']
    
    best_display = best[display_cols].sort_values('cost_per_1m_total_tokens')
    
    # 格式化输出
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    pd.set_option('display.float_format', lambda x: f'{x:.4f}')
    
    print(best_display.to_string(index=False))
    
    # 按硬件汇总
    print("\n\n📊 Cost range by hardware (per Million Total Tokens):\n")
    hw_summary = df.groupby('hardware').agg(
        min_cost=('cost_per_1m_total_tokens', 'min'),
        max_cost=('cost_per_1m_total_tokens', 'max'),
        median_cost=('cost_per_1m_total_tokens', 'median'),
        best_tput=('metrics_tput_per_gpu', 'max'),
        hourly_cost=('gpu_hourly_cost', 'first'),
        config_count=('cost_per_1m_total_tokens', 'count'),
    ).round(4)
    print(hw_summary.to_string())
    
    # Input vs Output 成本对比
    print("\n\n📊 Input vs Output Cost Ratio (per Million Tokens, best config per hardware):\n")
    best_hw = df.loc[df.groupby('hardware')['cost_per_1m_total_tokens'].idxmin()]
    for _, row in best_hw.iterrows():
        ratio = row['cost_per_1m_output_tokens'] / row['cost_per_1m_input_tokens'] if row['cost_per_1m_input_tokens'] > 0 else float('inf')
        print(f"  {row['hardware']:8s} | Input: ${row['cost_per_1m_input_tokens']:.4f}  "
              f"Output: ${row['cost_per_1m_output_tokens']:.4f}  "
              f"Total: ${row['cost_per_1m_total_tokens']:.4f}  "
              f"Output/Input ratio: {ratio:.2f}x  "
              f"(conc={int(row['conc'])}, {row['precision']}, isl={int(row['isl'])}/osl={int(row['osl'])})")

    print("\n" + "="*100)
    print(f"📁 Full results saved to: {output_path}")
    print(f"   New columns: cost_per_input_token, cost_per_output_token, cost_per_total_token")
    print(f"   Also added:  cost_per_1m_input_tokens, cost_per_1m_output_tokens, cost_per_1m_total_tokens")
    print("="*100)

if __name__ == "__main__":
    main()
