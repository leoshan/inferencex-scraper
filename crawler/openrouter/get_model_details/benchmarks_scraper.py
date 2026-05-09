#!/usr/bin/env python
"""
Benchmarks 页面抓取 - 使用 DynamicFetcher 抓取 Design Arena benchmark 数据

关键发现: 必须使用 DynamicFetcher 而不是 StealthyFetcher 才能获取完整数据
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


def fetch_benchmarks_page(model_slug="anthropic/claude-opus-4.7"):
    """
    抓取 benchmarks 页面并提取数据

    参数:
        model_slug: 模型标识，如 "anthropic/claude-opus-4.7"

    返回:
        dict: {"success": bool, "data": dict, "error": str/None}
    """
    if not SCRAPLING_AVAILABLE:
        return {"success": False, "data": None, "error": "Scrapling库未安装"}

    url = f"https://openrouter.ai/{model_slug}/benchmarks"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    try:
        start_time = time.time()
        # 关键: 使用 DynamicFetcher 而不是 StealthyFetcher
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
            return {"success": False, "data": None, "error": "无法获取页面内容"}

        print(f"  HTML 大小: {len(html_content):,} 字符")

        # 保存 HTML 用于调试
        output_dir = os.path.dirname(__file__)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = os.path.join(output_dir, f"benchmarks_debug_{timestamp}.html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"  HTML 已保存: {html_file}")

        # 提取 benchmark 数据
        data = extract_benchmarks_from_html(html_content)

        if data:
            print(f"  成功提取 benchmark 数据")
            return {"success": True, "data": data, "error": None}
        else:
            return {"success": False, "data": None, "error": "未能提取到 benchmark 数据"}

    except Exception as e:
        print(f"  抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "data": None, "error": str(e)}


def extract_benchmarks_from_html(html_content):
    """
    从 HTML 内容中提取 Design Arena benchmark 数据
    """
    result = {
        "ranking_distribution": [],
        "models_arena": [],
        "agents_arena": [],
        "category_performance": []
    }

    # 1. 提取 Category Performance (雷达图数据)
    # 格式: fill-foreground text-xs font-medium">3D</text>
    #       fill-muted-foreground text-2xs">Elo: 1320</text>
    print("\n  提取 Category Performance...")
    category_pattern = r'fill-foreground text-xs font-medium">([^<]+)</text>.*?fill-muted-foreground text-2xs">Elo:\s*(\d+)</text>'
    category_matches = re.findall(category_pattern, html_content, re.DOTALL)

    for match in category_matches:
        category = match[0].strip()
        elo = int(match[1])
        result["category_performance"].append({
            "category": category,
            "elo": elo
        })

    print(f"    Category Performance: {len(result['category_performance'])} 条")

    # 2. 提取 Models Arena 数据
    # 查找 "Models Arena" 标题后的数据卡片
    print("\n  提取 Models Arena...")

    # 提取所有 Elo 大数字 (text-3xl font-bold tabular-nums)
    elo_pattern = r'text-3xl font-bold tabular-nums">(\d+)</span>'
    all_elo_scores = re.findall(elo_pattern, html_content)

    # 提取类别名称和对应的卡片数据
    # 格式: text-sm font-medium">3D</span> ... whitespace-nowrap ... Top 11% ... text-3xl font-bold tabular-nums">1320</span>
    card_pattern = r'''<span class="text-sm font-medium">([^<]+)</span>.*?
        <span[^>]*class="[^"]*whitespace-nowrap[^"]*"[^>]*>([^<]+)</span>.*?
        text-3xl font-bold tabular-nums">(\d+)</span>.*?
        style="width:\s*([\d.]+)%.*?
        <span>([\d.]+)%\s*Win</span>'''

    # 查找 Models Arena 部分
    models_section_match = re.search(
        r'<h3[^>]*>Models Arena</h3>(.*?)(?:<h3[^>]*>Agents Arena</h3>|<div class="pt-4")',
        html_content,
        re.DOTALL
    )

    if models_section_match:
        models_html = models_section_match.group(1)

        # 更精确的模式匹配卡片
        card_pattern = r'<span class="text-sm font-medium">([^<]+)</span>.*?<span[^>]*class="[^"]*whitespace-nowrap[^"]*"[^>]*>([^<]+)</span>.*?<span class="text-3xl font-bold tabular-nums">(\d+)</span>.*?style="width:\s*([\d.]+)%.*?<span>([\d.]+)%\s*Win</span>.*?<span[^>]*>·</span>.*?<span>([\d.]+)s\s*Avg</span>.*?<span[^>]*>·</span>.*?<span>Top\s*([\d.]+)%</span>'

        card_matches = re.findall(card_pattern, models_html, re.DOTALL)

        for match in card_matches:
            result["models_arena"].append({
                "category": match[0].strip(),
                "rank_badge": match[1].strip(),
                "elo": int(match[2]),
                "progress_percent": float(match[3]),
                "win_rate": float(match[4]),
                "avg_time_seconds": float(match[5]) if match[5] else None,
                "top_percent": match[6].strip()
            })

    print(f"    Models Arena: {len(result['models_arena'])} 条")

    # 3. 提取 Agents Arena 数据
    print("\n  提取 Agents Arena...")
    agents_section_match = re.search(
        r'<h3[^>]*>Agents Arena</h3>(.*?)(?:<div class="pt-4"|</div>\s*</div>\s*<div)',
        html_content,
        re.DOTALL
    )

    if agents_section_match:
        agents_html = agents_section_match.group(1)

        # Agents Arena 没有 avg_time
        card_pattern = r'<span class="text-sm font-medium">([^<]+)</span>.*?<span[^>]*class="[^"]*whitespace-nowrap[^"]*"[^>]*>([^<]+)</span>.*?<span class="text-3xl font-bold tabular-nums">(\d+)</span>.*?style="width:\s*([\d.]+)%.*?<span>([\d.]+)%\s*Win</span>.*?<span[^>]*>·</span>.*?<span>Top\s*([\d.]+)%</span>'

        card_matches = re.findall(card_pattern, agents_html, re.DOTALL)

        for match in card_matches:
            result["agents_arena"].append({
                "category": match[0].strip(),
                "rank_badge": match[1].strip(),
                "elo": int(match[2]),
                "progress_percent": float(match[3]),
                "win_rate": float(match[4]),
                "top_percent": match[5].strip()
            })

    print(f"    Agents Arena: {len(result['agents_arena'])} 条")

    # 4. 提取 Ranking Distribution
    print("\n  提取 Ranking Distribution...")
    # 查找 "Ranking Distribution" 标题后的数据
    ranking_section = re.search(
        r'<span class="text-sm font-medium">Ranking Distribution</span>(.*?)(?:<div class="flex flex-col gap-3 rounded-lg border|<div class="grid)',
        html_content,
        re.DOTALL
    )

    if ranking_section:
        ranking_html = ranking_section.group(1)
        # 提取排名数字
        # 格式: <tspan x="96.5" dy="0.71em">1442</tspan>
        tspan_pattern = r'<tspan[^>]*>(\d+)</tspan>'
        values = re.findall(tspan_pattern, ranking_html)

        # 查找排名标签
        labels = ['First', 'Second', 'Third', 'Fourth']
        for i, label in enumerate(labels):
            if i < len(values):
                result["ranking_distribution"].append({
                    "rank": label,
                    "count": int(values[i])
                })

    # 如果上面方法没找到，尝试从 bar 图表提取
    if not result["ranking_distribution"]:
        # 查找 bar 图表中的数字
        bar_values = re.findall(r'<tspan[^>]*>(\d+)</tspan></text>\s*</g>\s*</g>\s*</g>', html_content)
        labels = ['First', 'Second', 'Third', 'Fourth']
        for i, label in enumerate(labels):
            if i < len(bar_values):
                result["ranking_distribution"].append({
                    "rank": label,
                    "count": int(bar_values[i])
                })

    print(f"    Ranking Distribution: {len(result['ranking_distribution'])} 条")

    # 检查是否有数据
    total_items = (len(result["ranking_distribution"]) +
                   len(result["models_arena"]) +
                   len(result["agents_arena"]) +
                   len(result["category_performance"]))

    if total_items == 0:
        return None

    return result


def parse_benchmarks_to_dataframes(data):
    """
    将 benchmark 数据转换为 DataFrame
    """
    if not PANDAS_AVAILABLE:
        print("警告: pandas 未安装，无法创建 DataFrame")
        return {}

    dataframes = {}

    if data.get("ranking_distribution"):
        dataframes["ranking_distribution"] = pd.DataFrame(data["ranking_distribution"])

    if data.get("models_arena"):
        dataframes["models_arena"] = pd.DataFrame(data["models_arena"])

    if data.get("agents_arena"):
        dataframes["agents_arena"] = pd.DataFrame(data["agents_arena"])

    if data.get("category_performance"):
        dataframes["category_performance"] = pd.DataFrame(data["category_performance"])

    return dataframes


def save_to_excel(dataframes, model_slug, output_dir=None):
    """
    将 benchmark 数据保存到 Excel 文件

    参数:
        dataframes: DataFrame 字典
        model_slug: 模型标识
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

    # 生成文件名
    model_name = model_slug.replace("/", "_")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = os.path.join(output_dir, f"benchmarks_{model_name}_{timestamp}.xlsx")

    # 创建 Excel 文件
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # 写入汇总信息
        summary_data = {
            "模型": [model_slug],
            "抓取时间": [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            "数据来源": ["Design Arena"],
            "Category Performance 数量": [len(dataframes.get("category_performance", []))],
            "Models Arena 数量": [len(dataframes.get("models_arena", []))],
            "Agents Arena 数量": [len(dataframes.get("agents_arena", []))],
            "Ranking Distribution 数量": [len(dataframes.get("ranking_distribution", []))],
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name="汇总", index=False)

        # 写入各个数据表
        for sheet_name, df in dataframes.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"\nExcel 文件已保存: {excel_file}")
    return excel_file


def fetch_and_save_benchmarks(model_slug="anthropic/claude-opus-4.7", save_excel=True):
    """
    抓取 benchmarks 页面并保存为 Excel

    参数:
        model_slug: 模型标识
        save_excel: 是否保存 Excel 文件

    返回:
        dict: {"success": bool, "data": dict, "excel_file": str, "error": str}
    """
    result = fetch_benchmarks_page(model_slug)

    if not result["success"]:
        return result

    data = result["data"]

    # 转换为 DataFrame
    dataframes = parse_benchmarks_to_dataframes(data)

    # 保存 Excel
    excel_file = None
    if save_excel and dataframes:
        excel_file = save_to_excel(dataframes, model_slug)

    return {
        "success": True,
        "data": data,
        "dataframes": dataframes,
        "excel_file": excel_file,
        "error": None
    }


def main():
    """主函数"""
    # 支持命令行参数指定模型
    model_slug = sys.argv[1] if len(sys.argv) > 1 else "anthropic/claude-opus-4.7"

    print("=" * 80)
    print("Benchmarks 页面抓取 (DynamicFetcher)")
    print("=" * 80)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"模型: {model_slug}")
    print()

    result = fetch_and_save_benchmarks(model_slug, save_excel=True)

    if result["success"]:
        print("\n" + "=" * 80)
        print("抓取成功!")
        print("=" * 80)

        data = result["data"]

        # 显示 Category Performance
        if data.get("category_performance"):
            print("\nCategory Performance:")
            for item in data["category_performance"]:
                print(f"  {item['category']}: Elo {item['elo']}")

        # 显示 Models Arena
        if data.get("models_arena"):
            print("\nModels Arena:")
            for item in data["models_arena"]:
                print(f"  {item['category']}: Elo {item['elo']}, Win {item['win_rate']}%, Top {item['top_percent']}%")

        # 显示 Agents Arena
        if data.get("agents_arena"):
            print("\nAgents Arena:")
            for item in data["agents_arena"]:
                print(f"  {item['category']}: Elo {item['elo']}, Win {item['win_rate']}%, Top {item['top_percent']}%")

        # 显示 Ranking Distribution
        if data.get("ranking_distribution"):
            print("\nRanking Distribution:")
            for item in data["ranking_distribution"]:
                print(f"  {item['rank']}: {item['count']}")

        # 显示 Excel 文件
        if result.get("excel_file"):
            print(f"\nExcel 文件: {result['excel_file']}")

    else:
        print("\n" + "=" * 80)
        print("抓取失败!")
        print("=" * 80)
        print(f"错误: {result['error']}")


if __name__ == "__main__":
    main()
