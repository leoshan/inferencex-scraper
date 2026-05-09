import pandas as pd
import os

# 硬件成本模型 (估算值，基于 SemiAnalysis 常见假设)
# CapEx: 采购成本 (USD)
# TDP_kW: 热设计功耗 (千瓦)
HW_COST_MODEL = {
    'h100': {'capex': 30000, 'tdp_kw': 0.7},
    'h200': {'capex': 40000, 'tdp_kw': 0.7},
    'b200': {'capex': 50000, 'tdp_kw': 1.0},
    'b300': {'capex': 60000, 'tdp_kw': 1.0},
    'gb200': {'capex': 70000, 'tdp_kw': 1.2},
    'mi300x': {'capex': 20000, 'tdp_kw': 0.75},
    'mi325x': {'capex': 25000, 'tdp_kw': 0.75},
    'mi355x': {'capex': 35000, 'tdp_kw': 1.0},
    'default': {'capex': 30000, 'tdp_kw': 0.7}
}

# 运营假设
AMORTIZATION_YEARS = 3
ELEC_RATE_KWH = 0.12  # $0.12 每度电

def calculate_hourly_cost(hw_key):
    hw_key = str(hw_key).lower()
    hw = HW_COST_MODEL.get(hw_key, HW_COST_MODEL['default'])
    # 每小时硬件折旧 = 总价 / (年限 * 365天 * 24小时)
    hourly_capex = hw['capex'] / (AMORTIZATION_YEARS * 365 * 24)
    # 每小时电费 = 功耗 * 电价
    hourly_opex = hw['tdp_kw'] * ELEC_RATE_KWH
    return hourly_capex + hourly_opex

def enrich_data():
    input_file = 'json_data/inference_max_merged.csv'
    output_file = 'json_data/inference_max_enhanced.csv'
    
    if not os.path.exists(input_file):
        print(f"错误: 找不到输入文件 {input_file}")
        return

    print(f"正在读取数据: {input_file}...")
    df = pd.read_csv(input_file)
    
    print("正在计算成本指标...")
    
    # 1. 计算每小时单卡成本
    df['hourly_gpu_cost'] = df['hardware'].apply(calculate_hourly_cost)
    
    # 2. 计算每百万 Token 成本
    # 公式: (每小时单卡成本 / (每秒单卡吞吐量 * 3600)) * 1,000,000
    # 注意: metrics_tput_per_gpu 已经是 per GPU 的总吞吐量
    
    # 防止除零错误
    tput = df['metrics_tput_per_gpu'].replace(0, float('nan'))
    
    if 'metrics_input_tput_per_gpu' in df.columns:
        input_tput = df['metrics_input_tput_per_gpu'].replace(0, float('nan'))
        df['cost_per_million_input_tokens'] = (df['hourly_gpu_cost'] / (input_tput * 3600)) * 1e6
        
    if 'metrics_output_tput_per_gpu' in df.columns:
        output_tput = df['metrics_output_tput_per_gpu'].replace(0, float('nan'))
        df['cost_per_million_output_tokens'] = (df['hourly_gpu_cost'] / (output_tput * 3600)) * 1e6
    
    df['cost_per_million_total_tokens'] = (df['hourly_gpu_cost'] / (tput * 3600)) * 1e6
    
    # 保留四位小数
    cost_cols = ['cost_per_million_total_tokens']
    if 'cost_per_million_input_tokens' in df.columns: cost_cols.append('cost_per_million_input_tokens')
    if 'cost_per_million_output_tokens' in df.columns: cost_cols.append('cost_per_million_output_tokens')
    
    df[cost_cols] = df[cost_cols].round(4)
    
    print(f"正在保存增强后的数据到: {output_file}")
    df.to_csv(output_file, index=False)
    print("处理完成！")

if __name__ == "__main__":
    enrich_data()
