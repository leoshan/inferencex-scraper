#!/usr/bin/env python
"""
DOM 爬取模块 - 从渲染的页面提取 Recharts 图表数据

当没有可用的 API 端点时，使用此模块从页面 DOM 中提取数据。
"""

import json
import time
import re
from datetime import datetime

try:
    from scrapling.fetchers import StealthyFetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    print("错误: Scrapling库未安装")
    StealthyFetcher = None


def get_default_headers(referer_url):
    """获取默认请求头"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': referer_url,
    }


def extract_chart_data_from_scripts(page):
    """
    从页面的 script 标签中提取图表数据

    参数:
        page: Scrapling page 对象

    返回:
        list: 图表数据点列表，每个元素为 {"date": str, "value": int}
    """
    try:
        # 获取页面 HTML
        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        if not html_content:
            return []

        # 查找所有日期
        all_dates = re.findall(r'202[456]-\d{2}-\d{2}', html_content)
        unique_dates = set(all_dates)
        print(f"  页面包含 {len(unique_dates)} 个不同日期")

        # 查找包含多个日期的数组（时间序列数据）
        array_pattern = r'\[\s*\{[^]]{50,15000}\}\s*(?:,\s*\{[^]]{50,15000}\}\s*)*\]'
        arrays = re.findall(array_pattern, html_content)
        print(f"  找到 {len(arrays)} 个可能的数组")

        for i, arr in enumerate(arrays):
            # 统计这个数组中的日期
            dates_in_array = re.findall(r'202[456]-\d{2}-\d{2}', arr)
            unique_dates_in_array = set(dates_in_array)

            # 查找包含多个不同日期的数组（至少 5 个）
            if len(unique_dates_in_array) >= 5:
                print(f"  数组 {i+1} 包含 {len(unique_dates_in_array)} 个不同日期")

                # 修复转义的引号
                fixed_arr = arr.replace('\\"', '"')
                if fixed_arr.startswith('[{\\"'):
                    fixed_arr = fixed_arr.replace('\\', '')

                try:
                    parsed = json.loads(fixed_arr)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        print(f"  从数组 {i+1} 提取到 {len(parsed)} 个数据点")
                        return parsed
                except Exception as e:
                    print(f"  数组 {i+1} 解析失败: {e}")

        return []
    except Exception as e:
        print(f"  从 scripts 提取数据失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_chart_data_from_dom(page):
    """
    从页面的 DOM 元素中提取 Recharts 图表数据

    参数:
        page: Scrapling page 对象

    返回:
        list: 图表数据点列表
    """
    try:
        data_points = []

        # 尝试从 Recharts 的 bar 元素提取
        bars = page.css('.recharts-bar-rectangle, .recharts-rectangle')
        if bars:
            print(f"  找到 {len(bars)} 个 bar 元素")

            # 尝试提取每个 bar 的属性
            for i, bar in enumerate(bars):
                try:
                    # 获取元素的所有属性
                    if hasattr(bar, 'attribs'):
                        attribs = bar.attribs

                        # 尝试多种属性组合
                        data_point = {}

                        # 检查常见的数据属性
                        for key in attribs:
                            if 'date' in key.lower() or 'time' in key.lower():
                                data_point['date'] = attribs[key]
                            elif 'value' in key.lower() or 'count' in key.lower():
                                data_point['value'] = attribs[key]
                            elif key in ['x', 'y', 'width', 'height']:
                                data_point[key] = attribs[key]

                        if data_point:
                            data_points.append(data_point)

                    # 尝试从元素文本提取
                    if hasattr(bar, 'text'):
                        text = str(bar.text).strip()
                        if text:
                            print(f"    Bar {i} text: {text[:50]}")

                    # 只打印前几个元素的详细信息
                    if i < 3:
                        print(f"    Bar {i} 属性: {dict(bar.attribs) if hasattr(bar, 'attribs') else 'N/A'}")

                except Exception as e:
                    if i < 3:
                        print(f"    Bar {i} 提取失败: {e}")

        # 尝试从 tooltip 元素提取
        if not data_points:
            tooltips = page.css('.recharts-tooltip-wrapper, .recharts-tooltip')
            if tooltips:
                print(f"  找到 {len(tooltips)} 个 tooltip 元素")
                for i, tooltip in enumerate(tooltips[:3]):
                    if hasattr(tooltip, 'text'):
                        print(f"    Tooltip {i}: {str(tooltip.text)[:100]}")

        # 尝试从 text 元素提取（可能包含数值）
        if not data_points:
            texts = page.css('.recharts-text, .recharts-label')
            if texts:
                print(f"  找到 {len(texts)} 个 text 元素")
                for i, text in enumerate(texts[:10]):
                    if hasattr(text, 'text'):
                        text_content = str(text.text).strip()
                        if text_content:
                            print(f"    Text {i}: {text_content}")

        return data_points
    except Exception as e:
        print(f"  从 DOM 提取数据失败: {e}")
        return []


def fetch_from_dom(app_name, app_url):
    """
    从渲染的页面提取应用使用量数据

    参数:
        app_name: 应用名称
        app_url: 应用页面 URL

    返回:
        dict: {"success": bool, "data": list/None, "error": str/None, "html": str/None}
    """
    if not SCRAPLING_AVAILABLE:
        return {"success": False, "data": None, "error": "Scrapling库未安装", "html": None}

    try:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始 DOM 爬取: {app_url}")
        headers = get_default_headers('https://openrouter.ai/apps')

        start_time = time.time()

        # 使用 StealthyFetcher 加载页面并等待渲染
        print(f"  使用 StealthyFetcher 加载页面...")
        page = StealthyFetcher.fetch(
            app_url,
            headers=headers,
            headless=True,
            network_idle=True  # 等待网络空闲，确保图表已加载
        )

        elapsed = time.time() - start_time
        print(f"  页面加载完成，耗时: {elapsed:.2f}秒")

        # 获取页面 HTML
        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        # 保存 HTML 用于调试
        if html_content:
            import os
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_file = os.path.join(os.path.dirname(__file__), f'debug_page_{timestamp}.html')
            try:
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"  调试: HTML 已保存到 {html_file}")
            except Exception as e:
                print(f"  调试: 保存 HTML 失败: {e}")

        # 方法1: 从 script 标签提取数据
        print(f"\n  方法1: 从 script 标签提取数据...")
        data = extract_chart_data_from_scripts(page)

        # 方法2: 从 DOM 元素提取数据
        if not data:
            print(f"\n  方法2: 从 DOM 元素提取数据...")
            data = extract_chart_data_from_dom(page)

        if data and len(data) > 0:
            print(f"\n  [OK] 成功提取 {len(data)} 个数据点")
            return {
                "success": True,
                "data": data,
                "error": None,
                "html": html_content
            }
        else:
            print(f"\n  [X] 未能提取到数据")
            return {
                "success": False,
                "data": None,
                "error": "未能从页面提取到图表数据",
                "html": html_content
            }

    except Exception as e:
        print(f"\n  DOM 爬取失败: {e}")
        return {
            "success": False,
            "data": None,
            "error": str(e),
            "html": None
        }
