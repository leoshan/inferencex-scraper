import urllib.request
import json
import pandas as pd
import os

URL = "https://openrouter.ai/api/v1/models/z-ai/glm-5/endpoints"
OUTPUT_DIR = "/root/inferencex-scraper/openrouter/glm5_output"
OLD_CSV = os.path.join(OUTPUT_DIR, "03_glm5_providers.csv")
NEW_CSV = os.path.join(OUTPUT_DIR, "03_glm5_providers_new.csv")
REPORT_FILE = "/root/inferencex-scraper/GLM5_Comparison_Report.md"

def main():
    print(f"Fetching endpoints from {URL} ...")
    req = urllib.request.Request(URL, headers={
        'User-Agent': 'Mozilla/5.0'
    })
    
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        
    endpoints = data.get('data', {}).get('endpoints', [])
    print(f"Found {len(endpoints)} endpoints")
    
    rows = []
    for ep in endpoints:
        pricing = ep.get('pricing', {})
        
        row = {
            'provider_name': ep.get('provider_name'),
            'provider_slug': ep.get('tag'),
            'context_length': ep.get('context_length'),
            'input_price_per_m': float(pricing.get('prompt', 0)) * 1_000_000 if pricing.get('prompt') else None,
            'output_price_per_m': float(pricing.get('completion', 0)) * 1_000_000 if pricing.get('completion') else None,
            'quantization': ep.get('quantization'),
            'status': ep.get('status')
        }
        rows.append(row)
        
    df_new = pd.DataFrame(rows)
    df_new.to_csv(NEW_CSV, index=False)
    print(f"Saved {NEW_CSV}")
    
    # Compare
    if not os.path.exists(OLD_CSV):
        print(f"Old CSV {OLD_CSV} not found.")
        return
        
    df_old = pd.read_csv(OLD_CSV)
    
    old_names = set(df_old['provider_name'].dropna().tolist())
    new_names = set(df_new['provider_name'].dropna().tolist())
    
    added = new_names - old_names
    removed = old_names - new_names
    
    report = f"""# GLM-5 采集数据比对与结构化报告

## 1. 结构化处理

最新从 OpenRouter API 抓取了 `z-ai/glm-5` 模型的 Provider 节点信息。
数据已结构化处理并保存为 CSV 表格：`openrouter/glm5_output/03_glm5_providers_new.csv`。

本次共提取到 **{len(df_new)}** 个 Provider 节点。

## 2. 数据比对结果 (最新 vs 历史)

与历史抓取数据（`03_glm5_providers.csv`）相比，平台的服务商发生如下变化：

- **历史节点数量**: {len(df_old)} 个
- **最新节点数量**: {len(df_new)} 个

### 2.1 提供商 (Providers) 动态变化

"""
    if added:
        report += "- **✅ 新增提供商**: " + ", ".join(added) + "\n"
    if removed:
        report += "- **❌ 下线/移除提供商**: " + ", ".join(removed) + "\n"
        
    if not added and not removed:
        report += "- **提供商名单未发生增减。**\n"
        
    report += "\n### 2.2 详细提供商列表与价格 (最新)\n\n"
    
    # Format prices as strings
    df_new['input_price_per_m'] = df_new['input_price_per_m'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    df_new['output_price_per_m'] = df_new['output_price_per_m'].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A")
    
    report += df_new[['provider_name', 'context_length', 'input_price_per_m', 'output_price_per_m', 'quantization']].to_markdown(index=False)
    
    with open(REPORT_FILE, "w", encoding='utf-8') as f:
        f.write(report)
        
    print(f"Saved report to {REPORT_FILE}")

if __name__ == "__main__":
    main()
