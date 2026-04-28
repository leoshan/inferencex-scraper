#!/usr/bin/env python
"""
Artificial Analysis 页面爬虫 - 抓取 https://artificialanalysis.ai/ 数据

该网站提供 AI 模型性能分析和比较数据

数据来源:
1. JSON-LD 格式嵌入在页面中 - 主要榜单数据
2. Next.js __next_f.push 数据 - 详细模型信息

包含数据:
- Intelligence Index (智能评测分数)
- Speed & Latency (性能速度)
- Price (定价信息)
- Omniscience (知识可靠性)
- Openness (开放程度)
- Provider Performance (提供商性能)
"""

import json
import re
import os
import time
import sys
from datetime import datetime

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

try:
    from scrapling.fetchers import DynamicFetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    print("错误: Scrapling库未安装")
    DynamicFetcher = None


def fetch_artificialanalysis_page(url="https://artificialanalysis.ai/"):
    """
    抓取 Artificial Analysis 页面

    参数:
        url: 页面 URL

    返回:
        dict: {"success": bool, "html": str, "data": dict, "error": str/None}
    """
    if not SCRAPLING_AVAILABLE:
        return {"success": False, "html": None, "data": None, "error": "Scrapling库未安装"}

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    try:
        start_time = time.time()
        page = DynamicFetcher.fetch(
            url,
            headers=headers,
            headless=True,
            network_idle=True
        )
        elapsed = time.time() - start_time
        print(f"  页面加载完成，耗时: {elapsed:.2f}秒")

        # 获取 HTML 内容
        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        if not html_content:
            return {"success": False, "html": None, "data": None, "error": "无法获取页面内容"}

        print(f"  HTML 大小: {len(html_content):,} 字符")

        # 保存 HTML 用于调试
        output_dir = os.path.dirname(__file__)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = os.path.join(output_dir, f"artificialanalysis_debug_{timestamp}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  HTML 已保存: {html_file}")

        # 提取数据
        data = extract_data_from_html(html_content)

        if data:
            print(f"  成功提取数据")
            return {"success": True, "html": html_content, "data": data, "error": None, "html_file": html_file}
        else:
            return {"success": False, "html": html_content, "data": None, "error": "未能提取到数据", "html_file": html_file}

    except Exception as e:
        print(f"  抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "html": None, "data": None, "error": str(e)}


def extract_json_ld_data(html_content):
    """
    从 HTML 中提取所有 JSON-LD 数据

    返回:
        list: JSON-LD 数据列表
    """
    json_ld_list = []

    # 匹配 <script type="application/ld+json">...</script>
    pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html_content, re.DOTALL)

    for i, match in enumerate(matches):
        try:
            data = json.loads(match)
            json_ld_list.append(data)
            dataset_name = data.get('name', f'Dataset {i+1}')
            data_count = len(data.get('data', []))
            print(f"    找到 JSON-LD: {dataset_name} ({data_count} 条记录)")
        except json.JSONDecodeError as e:
            print(f"    JSON-LD 解析失败: {e}")

    return json_ld_list


def extract_nextjs_data(html_content):
    """
    从 HTML 中提取 Next.js __next_f.push 数据

    返回:
        dict: 提取的模型详细数据
    """
    result = {
        "models_detail": [],
        "providers_detail": []
    }

    # 提取 __next_f.push 内容
    push_pattern = r'self\.__next_f\.push\(\[1,"(.*?)"\]\)'
    push_matches = re.findall(push_pattern, html_content)

    if not push_matches:
        return result

    # 合并所有内容
    combined = ''.join(push_matches)

    # 提取模型详细数据
    # 注意: 数据中使用转义字符 \"

    # 1. 提取 hosts_url, context_window_tokens
    pattern1 = r'context_window_tokens\\":(\d+).*?hosts_url\\":\\"/models/([^/]+)/providers'
    matches1 = re.findall(pattern1, combined)

    # 2. 提取 hosts_url, 价格
    pattern2 = r'hosts_url\\":\\"/models/([^/]+)/providers\\".*?price_1m_input_tokens\\":(\d+).*?price_1m_output_tokens\\":(\d+)'
    matches2 = re.findall(pattern2, combined)

    # 3. 提取 median_output_speed
    pattern3 = r'hosts_url\\":\\"/models/([^/]+)/providers\\".*?median_output_speed\\":([\d.]+)'
    matches3 = re.findall(pattern3, combined)

    # 4. 提取 intelligence_index
    pattern4 = r'hosts_url\\":\\"/models/([^/]+)/providers\\".*?\\"intelligence_index\\":(\d+\.?\d*)'
    matches4 = re.findall(pattern4, combined)

    # 合并数据
    models_dict = {}

    # 添加 context_window
    for context, slug in matches1:
        if slug not in models_dict:
            models_dict[slug] = {"model_slug": slug}
        models_dict[slug]["context_window_tokens"] = int(context)

    # 添加价格
    for slug, input_price, output_price in matches2:
        if slug not in models_dict:
            models_dict[slug] = {"model_slug": slug}
        models_dict[slug]["input_price"] = float(input_price)
        models_dict[slug]["output_price"] = float(output_price)

    # 添加速度
    for slug, speed in matches3:
        if slug not in models_dict:
            models_dict[slug] = {"model_slug": slug}
        models_dict[slug]["median_output_speed"] = float(speed)

    # 添加 intelligence_index
    for slug, index in matches4:
        if slug not in models_dict:
            models_dict[slug] = {"model_slug": slug}
        models_dict[slug]["intelligence_index"] = float(index)

    result["models_detail"] = list(models_dict.values())

    if result["models_detail"]:
        print(f"    提取到 {len(result['models_detail'])} 个模型的详细数据")

    return result


def extract_data_from_html(html_content):
    """
    从 HTML 内容中提取数据

    返回:
        dict: 包含提取的数据
    """
    result = {
        # 1. Intelligence Index - 智能评测分数
        "intelligence_index": [],
        # 2. Intelligence Breakdown - 智能评测细分 (推理、编程、智能体)
        "intelligence_breakdown": [],
        # 3. Omniscience - 知识可靠性指数
        "omniscience": [],
        # 4. Speed - 输出速度
        "speed": [],
        # 5. Price - 定价
        "price": [],
        # 6. Output Speed by Provider - 提供商输出速度
        "output_speed_by_provider": [],
        # 7. Pricing by Provider - 提供商定价
        "pricing_by_provider": [],
        # 8. Models Detail - 模型详细信息 (context window 等)
        "models_detail": [],
        # 9. 原始数据集
        "raw_datasets": [],
        # 10. 模型列表
        "models": [],
        # 11. 提供商列表
        "providers": []
    }

    # 1. 提取 JSON-LD 数据（主要数据源）
    print("\n  提取 JSON-LD 数据...")
    json_ld_list = extract_json_ld_data(html_content)

    for dataset in json_ld_list:
        dataset_name = dataset.get('name', '')
        dataset_data = dataset.get('data', [])

        result["raw_datasets"].append({
            "name": dataset_name,
            "data": dataset_data
        })

        # 根据数据集名称分类
        if 'Intelligence Index' in dataset_name and 'Open Weights' not in dataset_name:
            result["intelligence_index"] = dataset_data
        elif 'Intelligence Index by Open Weights' in dataset_name:
            result["intelligence_breakdown"] = dataset_data
        elif 'Omniscience' in dataset_name:
            result["omniscience"] = dataset_data
        elif dataset_name == 'Speed':
            result["speed"] = dataset_data
        elif dataset_name == 'Price':
            result["price"] = dataset_data
        elif 'Output Speed' in dataset_name and 'Provider' in dataset_name:
            result["output_speed_by_provider"] = dataset_data
        elif 'Pricing' in dataset_name and 'Provider' in dataset_name:
            result["pricing_by_provider"] = dataset_data

    # 2. 提取 Next.js 详细数据
    print("\n  提取 Next.js 详细数据...")
    nextjs_data = extract_nextjs_data(html_content)
    result["models_detail"] = nextjs_data.get("models_detail", [])

    # 3. 提取模型名称
    print("\n  提取模型名称...")
    model_patterns = [
        r'claude-[a-z0-9.-]+',
        r'gpt-[a-z0-9.-]+',
        r'llama-[a-z0-9.-]+',
        r'mistral-[a-z0-9.-]+',
        r'gemini-[a-z0-9.-]+',
        r'deepseek-[a-z0-9.-]+',
    ]

    found_models = set()
    for pattern in model_patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        found_models.update(matches)

    if found_models:
        result["models"] = sorted(list(found_models))
        print(f"    找到 {len(result['models'])} 个模型名称")

    # 4. 提取提供商名称
    print("\n  提取提供商名称...")
    provider_keywords = ['openai', 'anthropic', 'google', 'meta', 'mistral', 'cohere', 'deepseek']
    found_providers = set()
    for keyword in provider_keywords:
        if keyword in html_content.lower():
            found_providers.add(keyword.capitalize())

    if found_providers:
        result["providers"] = sorted(list(found_providers))
        print(f"    找到 {len(result['providers'])} 个提供商")

    # 检查是否有数据
    total_items = (len(result["intelligence_index"]) +
                   len(result["speed"]) +
                   len(result["price"]) +
                   len(result["output_speed_by_provider"]) +
                   len(result["pricing_by_provider"]) +
                   len(result["omniscience"]) +
                   len(result["models_detail"]))

    if total_items == 0:
        return None

    return result


def save_to_excel(data, output_dir=None):
    """
    将数据保存到 Excel 文件

    参数:
        data: 提取的数据字典
        output_dir: 输出目录

    返回:
        str: Excel 文件路径
    """
    if not PANDAS_AVAILABLE:
        print("错误: pandas 未安装")
        return None

    if not OPENPYXL_AVAILABLE:
        print("错误: openpyxl 未安装")
        return None

    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = os.path.join(output_dir, f"artificialanalysis_{timestamp}.xlsx")

    try:
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # 写入汇总信息
            summary_data = {
                "抓取时间": [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                "数据来源": ["https://artificialanalysis.ai/"],
                "Intelligence Index 记录数": [len(data.get("intelligence_index", []))],
                "Speed 记录数": [len(data.get("speed", []))],
                "Price 记录数": [len(data.get("price", []))],
                "Output Speed by Provider 记录数": [len(data.get("output_speed_by_provider", []))],
                "Pricing by Provider 记录数": [len(data.get("pricing_by_provider", []))],
                "Omniscience 记录数": [len(data.get("omniscience", []))],
                "Models Detail 记录数": [len(data.get("models_detail", []))],
                "模型数量": [len(data.get("models", []))],
                "提供商数量": [len(data.get("providers", []))],
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name="汇总", index=False)
            print(f"  写入汇总表")

            # 写入 Intelligence Index (智能评测分数)
            if data.get("intelligence_index"):
                df = pd.DataFrame(data["intelligence_index"])
                df.to_excel(writer, sheet_name="Intelligence_Index", index=False)
                print(f"  写入 Intelligence_Index: {len(df)} 行")

            # 写入 Speed (输出速度)
            if data.get("speed"):
                df = pd.DataFrame(data["speed"])
                df.to_excel(writer, sheet_name="Speed", index=False)
                print(f"  写入 Speed: {len(df)} 行")

            # 写入 Price (定价)
            if data.get("price"):
                df = pd.DataFrame(data["price"])
                df.to_excel(writer, sheet_name="Price", index=False)
                print(f"  写入 Price: {len(df)} 行")

            # 写入 Output Speed by Provider (提供商输出速度)
            if data.get("output_speed_by_provider"):
                df = pd.DataFrame(data["output_speed_by_provider"])
                df.to_excel(writer, sheet_name="Output_Speed_Provider", index=False)
                print(f"  写入 Output_Speed_Provider: {len(df)} 行")

            # 写入 Pricing by Provider (提供商定价)
            if data.get("pricing_by_provider"):
                df = pd.DataFrame(data["pricing_by_provider"])
                df.to_excel(writer, sheet_name="Pricing_Provider", index=False)
                print(f"  写入 Pricing_Provider: {len(df)} 行")

            # 写入 Omniscience (知识可靠性)
            if data.get("omniscience"):
                df = pd.DataFrame(data["omniscience"])
                df.to_excel(writer, sheet_name="Omniscience", index=False)
                print(f"  写入 Omniscience: {len(df)} 行")

            # 写入 Intelligence Breakdown
            if data.get("intelligence_breakdown"):
                df = pd.DataFrame(data["intelligence_breakdown"])
                df.to_excel(writer, sheet_name="Intelligence_Breakdown", index=False)
                print(f"  写入 Intelligence_Breakdown: {len(df)} 行")

            # 写入 Models Detail
            if data.get("models_detail"):
                df = pd.DataFrame(data["models_detail"])
                df.to_excel(writer, sheet_name="Models_Detail", index=False)
                print(f"  写入 Models_Detail: {len(df)} 行")

            # 写入模型列表
            if data.get("models"):
                models_df = pd.DataFrame({"model": data["models"]})
                models_df.to_excel(writer, sheet_name="Models", index=False)

            # 写入提供商列表
            if data.get("providers"):
                providers_df = pd.DataFrame({"provider": data["providers"]})
                providers_df.to_excel(writer, sheet_name="Providers", index=False)

        print(f"\nExcel 文件已保存: {excel_file}")
        return excel_file

    except Exception as e:
        print(f"\n保存 Excel 失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_raw_data(data, output_dir=None):
    """
    保存原始数据到 JSON 文件

    参数:
        data: 提取的数据字典
        output_dir: 输出目录

    返回:
        str: JSON 文件路径
    """
    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_file = os.path.join(output_dir, f"artificialanalysis_data_{timestamp}.json")

    try:
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"JSON 数据已保存: {json_file}")
        return json_file
    except Exception as e:
        print(f"保存 JSON 失败: {e}")
        return None


def fetch_and_save(url="https://artificialanalysis.ai/", save_excel=True):
    """
    抓取页面并保存数据

    参数:
        url: 页面 URL
        save_excel: 是否保存 Excel 文件

    返回:
        dict: {"success": bool, "data": dict, "files": dict, "error": str}
    """
    result = fetch_artificialanalysis_page(url)

    if not result["success"]:
        return result

    data = result["data"]
    output_dir = os.path.dirname(__file__)

    files = {
        "html": result.get("html_file"),
        "json": None,
        "excel": None
    }

    # 保存 JSON
    files["json"] = save_raw_data(data, output_dir)

    # 保存 Excel
    if save_excel:
        files["excel"] = save_to_excel(data, output_dir)

    return {
        "success": True,
        "data": data,
        "files": files,
        "error": None
    }


def main():
    """主函数"""
    url = sys.argv[1] if len(sys.argv) > 1 else "https://artificialanalysis.ai/"

    print("=" * 80)
    print("Artificial Analysis 页面爬虫")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL: {url}")
    print()

    result = fetch_and_save(url, save_excel=True)

    if result["success"]:
        print("\n" + "=" * 80)
        print("抓取成功!")
        print("=" * 80)

        data = result["data"]

        # 显示 Intelligence Index
        if data.get("intelligence_index"):
            print(f"\n【Intelligence Index 智能评测分数】: {len(data['intelligence_index'])} 条记录")
            print("Top 5:")
            for item in data["intelligence_index"][:5]:
                score = item.get('intelligenceIndex', 'N/A')
                name = item.get('modelName', 'Unknown')
                print(f"  {name}: {score}")

        # 显示 Speed
        if data.get("speed"):
            print(f"\n【Speed 输出速度】: {len(data['speed'])} 条记录")
            print("Top 5 (tokens/秒):")
            for item in data["speed"][:5]:
                speed = item.get('medianOutputSpeed', 'N/A')
                name = item.get('modelName', 'Unknown')
                print(f"  {name}: {speed:.1f}" if isinstance(speed, float) else f"  {name}: {speed}")

        # 显示 Price
        if data.get("price"):
            print(f"\n【Price 定价】: {len(data['price'])} 条记录")
            print("按价格排序 (USD/百万tokens):")
            for item in data["price"][:5]:
                price = item.get('pricePerMillionTokens', 'N/A')
                name = item.get('modelName', 'Unknown')
                print(f"  {name}: ${price}")

        # 显示 Omniscience
        if data.get("omniscience"):
            print(f"\n【Omniscience 知识可靠性】: {len(data['omniscience'])} 条记录")
            print("Top 5:")
            for item in data["omniscience"][:5]:
                score = item.get('omniscienceIndex', 'N/A')
                name = item.get('modelName', 'Unknown')
                print(f"  {name}: {score}")

        # 显示 Provider Performance
        if data.get("output_speed_by_provider"):
            print(f"\n【Provider Performance 提供商性能】: {len(data['output_speed_by_provider'])} 条记录")

        # 显示文件路径
        print("\n输出文件:")
        for file_type, file_path in result.get("files", {}).items():
            if file_path:
                print(f"  {file_type}: {file_path}")

    else:
        print("\n" + "=" * 80)
        print("抓取失败!")
        print("=" * 80)
        print(f"错误: {result['error']}")


if __name__ == "__main__":
    main()
