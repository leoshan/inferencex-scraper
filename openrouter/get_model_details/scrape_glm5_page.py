import urllib.request
import json
import re
import pandas as pd
import os
import time

URL = "https://openrouter.ai/z-ai/glm-5"
OUTPUT_DIR = "/root/inferencex-scraper/openrouter/glm5_output"
OLD_CSV = os.path.join(OUTPUT_DIR, "03_glm5_providers.csv")
NEW_CSV = os.path.join(OUTPUT_DIR, "03_glm5_providers_new.csv")
REPORT_FILE = os.path.join(OUTPUT_DIR, "GLM5_Comparison_Report.md")

def main():
    print(f"Fetching {URL} ...")
    req = urllib.request.Request(URL, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8')
    
    print(f"Fetched HTML, length: {len(html)}")
    
    # Extract NEXT_DATA
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not match:
        print("Failed to find __NEXT_DATA__")
        return
        
    next_data = json.loads(match.group(1))
    
    # Find variantGroups
    queries = next_data.get('props', {}).get('pageProps', {}).get('trpcState', {}).get('json', {}).get('queries', [])
    variant_groups = []
    
    for q in queries:
        data = q.get('state', {}).get('data', {})
        if isinstance(data, dict) and 'variantGroups' in data:
            variant_groups = data['variantGroups']
            break
            
    if not variant_groups:
        print("Failed to find variantGroups in __NEXT_DATA__")
        return
        
    print(f"Found {len(variant_groups)} variant groups")
    
    endpoints = []
    for group in variant_groups:
        for ep in group.get('endpoints', []):
            endpoints.append(ep)
            
    print(f"Found {len(endpoints)} endpoints")
    
    rows = []
    for ep in endpoints:
        provider = ep.get('provider_info', {})
        pricing = ep.get('pricing', {})
        
        row = {
            'provider_name': provider.get('displayName'),
            'provider_slug': provider.get('slug'),
            'context_length': ep.get('context_length'),
            'input_price_per_m': pricing.get('prompt') * 1_000_000 if pricing.get('prompt') else None,
            'output_price_per_m': pricing.get('completion') * 1_000_000 if pricing.get('completion') else None,
            'quantization': ep.get('quantization'),
            'status': ep.get('status')
        }
        rows.append(row)
        
    df_new = pd.DataFrame(rows)
    df_new.to_csv(NEW_CSV, index=False)
    print(f"Saved {NEW_CSV}")
    
    # Compare
    if not os.path.exists(OLD_CSV):
        print(f"Old CSV {OLD_CSV} not found, skipping comparison.")
        return
        
    df_old = pd.read_csv(OLD_CSV)
    
    old_names = set(df_old['provider_name'].dropna().tolist())
    new_names = set(df_new['provider_name'].dropna().tolist())
    
    added = new_names - old_names
    removed = old_names - new_names
    
    report = f"""# GLM-5 页面数据抓取与比对报告

## 1. 抓取与结构化处理

最新从页面 `{URL}` 抓取了 `__NEXT_DATA__` 数据，并提取了各个 Provider 的详细节点信息（Endpoints）。
数据已结构化处理并保存为 CSV 表格：`{NEW_CSV}`。

本次共提取到 **{len(df_new)}** 个 Provider 节点。

## 2. 数据比对结果 (最新采集 vs 历史采集)

与历史数据（`{OLD_CSV}`）相比，提供商发生了如下变化：

- **历史节点数量**: {len(df_old)} 个
- **最新节点数量**: {len(df_new)} 个

### 2.1 提供商 (Providers) 变化

"""
    if added:
        report += "- **✅ 新增提供商**: " + ", ".join(added) + "\n"
    if removed:
        report += "- **❌ 下线/移除提供商**: " + ", ".join(removed) + "\n"
        
    if not added and not removed:
        report += "- **提供商名单未发生增减。**\n"
        
    report += "\n### 2.2 详细提供商列表 (最新)\n\n"
    report += df_new[['provider_name', 'context_length', 'input_price_per_m', 'output_price_per_m']].to_markdown(index=False)
    
    with open(REPORT_FILE, "w", encoding='utf-8') as f:
        f.write(report)
        
    print(f"Saved report to {REPORT_FILE}")

if __name__ == "__main__":
    main()
