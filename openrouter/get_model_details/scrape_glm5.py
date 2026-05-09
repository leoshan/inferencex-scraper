#!/usr/bin/env python3
"""
OpenRouter GLM-5 模型数据抓取脚本 (轻量版)
纯 JSON API 抓取，无需 Scrapling/浏览器
"""

import sys
import os
import json
import time
import re
import urllib.request
import urllib.parse
from datetime import datetime

# 检查 requests
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("提示: requests 未安装，尝试使用 urllib")

import pandas as pd

# === 配置 ===
MODEL_PERMASLUG = "z-ai/glm-5"
MODEL_NAME = "GLM-5"
AUTHOR_SLUG = "z-ai"
OUTPUT_DIR = "/root/inferencex-scraper/openrouter/glm5_output"
SAVE_RAW_RESPONSE = True

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def fetch_api(url, description="API", timeout=30):
    """使用 requests 或 urllib 获取 JSON API"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取 {description}")
        print(f"  URL: {url}")
        start = time.time()

        if HAS_REQUESTS:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        else:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode('utf-8')
                data = json.loads(raw)

        elapsed = time.time() - start
        raw_text = json.dumps(data, ensure_ascii=False, indent=2)
        print(f"  成功: {len(raw_text):,} 字符, 耗时 {elapsed:.1f}s")
        return {"success": True, "data": data, "raw_text": raw_text, "elapsed": elapsed, "error": None}
    except Exception as e:
        print(f"  [FAIL] {description}: {e}")
        return {"success": False, "data": None, "error": str(e)}


def save_raw(raw_text, label):
    """保存原始响应"""
    safe_label = re.sub(r'[^\w\-]', '_', label)[:60]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"{safe_label}_{ts}.json")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(raw_text)
    print(f"  [保存] {path}")


# ========== 解析函数 ==========

def parse_top_apps(data):
    d = data.get('data', {})
    apps_raw = d.get('top_apps', [])
    apps_rows = []
    for item in apps_raw:
        app = item.pop('app', {})
        row = {**item, 'app_title': app.get('title'), 'app_description': app.get('description'), 'app_slug': app.get('slug')}
        for k in ['total_tokens', 'total_requests']:
            if k in row:
                try: row[k] = int(row[k])
                except: pass
        apps_rows.append(row)
    df_apps = pd.DataFrame(apps_rows)
    df_chart = pd.DataFrame(d.get('top_apps_chart', []))
    return df_apps, df_chart


def parse_author_models(data):
    models = data.get('data', {}).get('models', [])
    rows = []
    for m in models:
        ep = m.pop('endpoint', {})
        pricing = ep.pop('pricing', {})
        provider = ep.pop('provider_info', {})
        features = ep.pop('features', {})
        row = {
            **m,
            'endpoint_id': ep.get('id'), 'endpoint_name': ep.get('name'),
            'endpoint_context_length': ep.get('context_length'),
            'endpoint_provider_name': ep.get('provider_name'),
            'endpoint_variant': ep.get('variant'),
            'endpoint_is_free': ep.get('is_free'),
            'pricing_prompt': pricing.get('prompt'),
            'pricing_completion': pricing.get('completion'),
            'provider_display_name': provider.get('displayName'),
            'provider_slug': provider.get('slug'),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def parse_endpoint_stats(data):
    endpoints = data.get('data', [])
    rows = []
    for ep in endpoints:
        stats = ep.pop('stats', {})
        model_info = ep.pop('model', {})
        row = {
            **ep,
            'model_slug': model_info.get('slug'), 'model_name': model_info.get('name'),
            'p50_throughput': stats.get('p50_throughput'),
            'p90_throughput': stats.get('p90_throughput'),
            'p95_throughput': stats.get('p95_throughput'),
            'p50_latency': stats.get('p50_latency'),
            'p90_latency': stats.get('p90_latency'),
            'request_count': stats.get('request_count'),
            'status': ep.get('status'),
        }
        rows.append(row)
    return pd.DataFrame(rows)

def parse_model_endpoints(data):
    endpoints = data.get('data', [])
    if isinstance(endpoints, dict) and 'endpoints' in endpoints:
        endpoints = endpoints['endpoints']
    rows = []
    for ep in endpoints:
        pricing = ep.pop('pricing', {})
        provider = ep.pop('provider_info', {})
        row = {
            **ep,
            'pricing_prompt': pricing.get('prompt'),
            'pricing_completion': pricing.get('completion'),
            'provider_name': provider.get('displayName'),
            'provider_slug': provider.get('slug'),
        }
        rows.append(row)
    return pd.DataFrame(rows)



def parse_uptime(data):
    d = data.get('data', {})
    rows = []
    for eid, records in d.items():
        for rec in records:
            rows.append({'endpoint_id': eid, 'date': rec.get('date'), 'uptime': rec.get('uptime')})
    return pd.DataFrame(rows)


def parse_benchmark(data):
    d = data.get('data', [])
    if isinstance(d, list):
        return pd.DataFrame(d)
    return pd.DataFrame([d])


def clean_df(df):
    """清理 DataFrame 中的非法字符，兼容 Excel"""
    import re as _re
    import pandas as pd
    import numpy as np
    control = _re.compile(r'[\x00-\x1f\x7f-\x9f]')
    
    def safe_clean(x):
        if x is None:
            return x
        if isinstance(x, (float, np.floating)) and pd.isna(x):
            return x
        return control.sub(' ', str(x))

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)
        elif df[col].dtype == 'object':
            df[col] = df[col].apply(safe_clean)
    return df


# ========== 主流程 ==========

def main():
    print("=" * 70)
    print(f"OpenRouter {MODEL_NAME} 模型数据抓取 (轻量版)")
    print(f"模型: {MODEL_PERMASLUG}")
    print(f"输出: {OUTPUT_DIR}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    apis = {
        "top_apps": f"https://openrouter.ai/api/frontend/stats/top-apps-for-model?permaslug={MODEL_PERMASLUG}&variant=standard",
        "endpoint_stats": f"https://openrouter.ai/api/frontend/stats/endpoint?model_slug={MODEL_PERMASLUG}&variant=standard",
        "model_endpoints": f"https://openrouter.ai/api/frontend/models/{MODEL_PERMASLUG}/endpoints",
        "author_models": f"https://openrouter.ai/api/frontend/author-models?authorSlug={AUTHOR_SLUG}",
        "uptime_recent": f"https://openrouter.ai/api/frontend/stats/uptime-recent?permaslug={MODEL_PERMASLUG}",
        "artificial_analysis": f"https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks?slug={MODEL_PERMASLUG}",
        "design_arena": f"https://openrouter.ai/api/internal/v1/design-arena-benchmarks?slug={MODEL_PERMASLUG}",
    }

    # 1. 获取数据
    print("\n[步骤1] 获取 API 数据")
    print("-" * 40)
    results = {}
    for name, url in apis.items():
        r = fetch_api(url, name)
        results[name] = r
        if SAVE_RAW_RESPONSE and r["success"] and r.get("raw_text"):
            save_raw(r["raw_text"], name)
        time.sleep(0.8)

    ok = sum(1 for r in results.values() if r["success"])
    print(f"\n结果: {ok}/{len(apis)} 成功")

    # 2. 解析
    print("\n[步骤2] 解析数据")
    print("-" * 40)
    dfs = {}
    for name, r in results.items():
        if not r["success"] or r["data"] is None:
            continue
        data = r["data"] if isinstance(r["data"], dict) else {}
        try:
            if name == "top_apps":
                df_a, df_c = parse_top_apps(data)
                dfs['top_apps'] = df_a
                dfs['top_apps_chart'] = df_c
                print(f"  top_apps: {len(df_a)} 行 | chart: {len(df_c)} 行")
            elif name == "endpoint_stats":
                df = parse_endpoint_stats(data)
                dfs[name] = df
                print(f"  {name}: {len(df)} 行")
            elif name == "model_endpoints":
                df = parse_model_endpoints(data)
                dfs[name] = df
                print(f"  {name}: {len(df)} 行")
            elif name == "author_models":
                df = parse_author_models(data)
                dfs[name] = df
                print(f"  {name}: {len(df)} 行")
            elif name == "uptime_recent":
                df = parse_uptime(data)
                dfs[name] = df
                print(f"  {name}: {len(df)} 行")
            elif name in ("artificial_analysis", "design_arena"):
                df = parse_benchmark(data)
                dfs[name] = df
                print(f"  {name}: {len(df)} 行")
        except Exception as e:
            print(f"  解析 {name} 失败: {e}")

    # 3. 生成 Excel
    print("\n[步骤3] 生成 Excel")
    print("-" * 40)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    xls_path = os.path.join(OUTPUT_DIR, f"glm5_data_{ts}.xlsx")
    try:
        with pd.ExcelWriter(xls_path, engine='openpyxl') as writer:
            # Create a dummy sheet to prevent 'At least one sheet must be visible' on error
            pd.DataFrame(['dummy']).to_excel(writer, sheet_name='_dummy')
            
            for sname, df in dfs.items():
                if df is not None and not df.empty:
                    # Always save CSV directly (it doesn't need strict cleaning)
                    csv_path = os.path.join(OUTPUT_DIR, f"{sname}_{ts}.csv")
                    try:
                        df.to_csv(csv_path, index=False)
                        print(f"  {sname}: {len(df)} 行 x {len(df.columns)} 列 (已存CSV)")
                    except Exception as e_csv:
                        print(f"  [ERROR] 保存 CSV {sname} 失败: {repr(e_csv)}")

                    # Try Excel saving
                    try:
                        df_clean = clean_df(df.copy())
                        df_clean.to_excel(writer, sheet_name=sname[:31], index=False)
                    except Exception as e_inner:
                        print(f"  [WARN] 处理 Excel {sname} 失败: {repr(e_inner)}")
        print(f"\n[OK] Excel: {xls_path}")
    except Exception as e:
        print(f"[ERROR] Excel 失败: {e}")

    # 4. 生成汇总 JSON
    print("\n[步骤4] 汇总")
    summary = {
        "model": MODEL_PERMASLUG, "name": MODEL_NAME,
        "time": datetime.now().isoformat(),
        "results": {n: {"success": r["success"], "error": r.get("error")} for n, r in results.items()}
    }
    js_path = os.path.join(OUTPUT_DIR, f"glm5_summary_{ts}.json")
    with open(js_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  汇总: {js_path}")

    # 5. 打印关键信息
    print("\n" + "=" * 70)
    print("关键信息摘要:")
    print("-" * 40)
    if 'author_models' in dfs and not dfs['author_models'].empty:
        glm5_rows = dfs['author_models'][dfs['author_models'].get('slug', pd.Series()) == MODEL_PERMASLUG]
        if not glm5_rows.empty:
            row = glm5_rows.iloc[0]
            print(f"  模型名称: {row.get('name', 'N/A')}")
            print(f"  描述: {str(row.get('description', ''))[:120]}...")
            print(f"  上下文长度: {row.get('endpoint_context_length', 'N/A')}")
            print(f"  输入价格: {row.get('pricing_prompt', 'N/A')}")
            print(f"  输出价格: {row.get('pricing_completion', 'N/A')}")
            print(f"  提供商: {row.get('provider_display_name', 'N/A')}")
            print(f"  免费: {row.get('endpoint_is_free', 'N/A')}")
    if 'endpoint_stats' in dfs and not dfs['endpoint_stats'].empty:
        row = dfs['endpoint_stats'].iloc[0]
        print(f"\n  性能统计:")
        print(f"    P50 吞吐量: {row.get('p50_throughput', 'N/A')}")
        print(f"    P90 吞吐量: {row.get('p90_throughput', 'N/A')}")
        print(f"    P50 延迟: {row.get('p50_latency', 'N/A')}")
        print(f"    P90 延迟: {row.get('p90_latency', 'N/A')}")
        print(f"    请求数: {row.get('request_count', 'N/A')}")
    if 'top_apps' in dfs and not dfs['top_apps'].empty:
        print(f"\n  Top 应用 (前5):")
        for i, (_, row) in enumerate(dfs['top_apps'].head(5).iterrows()):
            print(f"    {i+1}. {row.get('app_title', 'N/A')} - {row.get('total_tokens', 0):,} tokens")
    if 'artificial_analysis' in dfs and not dfs['artificial_analysis'].empty:
        print(f"\n  Artificial Analysis 基准评分:")
        for _, row in dfs['artificial_analysis'].head(5).iterrows():
            name = row.get('name', row.get('category', 'N/A'))
            score = row.get('score', row.get('value', 'N/A'))
            print(f"    {name}: {score}")
    if 'design_arena' in dfs and not dfs['design_arena'].empty:
        print(f"\n  Design Arena 基准:")
        for _, row in dfs['design_arena'].head(5).iterrows():
            name = row.get('name', row.get('category', 'N/A'))
            score = row.get('score', row.get('value', 'N/A'))
            print(f"    {name}: {score}")

    print("\n" + "=" * 70)
    print("完成!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
