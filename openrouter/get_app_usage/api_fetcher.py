#!/usr/bin/env python
"""
API 获取模块 - 尝试从 OpenRouter API 端点获取应用使用量数据

尝试的 API 端点模式：
1. /api/frontend/stats/app-usage?app={app_name}
2. /api/frontend/stats/top-models-for-app?app={app_name}
3. /api/internal/v1/app-stats?app={app_name}
"""

import json
import time
from datetime import datetime
from urllib.parse import quote

try:
    from scrapling.fetchers import Fetcher, StealthyFetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    print("错误: Scrapling库未安装")
    Fetcher = None
    StealthyFetcher = None


def get_default_headers(referer_url):
    """获取默认请求头"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Referer': referer_url,
        'Origin': 'https://openrouter.ai',
    }


def try_fetch_api(url, description="API"):
    """
    尝试从 API 端点获取数据

    参数:
        url: API 端点 URL
        description: 描述信息

    返回:
        dict: {"success": bool, "data": dict/None, "error": str/None}
    """
    if not SCRAPLING_AVAILABLE:
        return {"success": False, "data": None, "error": "Scrapling库未安装"}

    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 尝试 {description}: {url}")
        headers = get_default_headers('https://openrouter.ai/apps')

        start_time = time.time()

        # 尝试 StealthyFetcher
        try:
            page = StealthyFetcher.fetch(url, headers=headers, headless=True, network_idle=True)
        except Exception as e:
            print(f"  StealthyFetcher 失败: {e}")
            print(f"  回退到 Fetcher...")
            page = Fetcher.get(url, headers=headers)

        elapsed = time.time() - start_time
        print(f"  请求完成，耗时: {elapsed:.2f}秒")

        # 解析响应
        parsed_data = None

        # 方法1: 尝试 page.json()
        if hasattr(page, 'json') and callable(page.json):
            try:
                parsed_data = page.json()
                print(f"  成功使用 page.json() 解析")
            except Exception as json_err:
                print(f"  page.json() 失败: {json_err}")

        # 方法2: 尝试 page.body
        if not parsed_data and hasattr(page, 'body'):
            body = page.body
            if body:
                try:
                    if isinstance(body, bytes):
                        body = body.decode('utf-8')
                    parsed_data = json.loads(body)
                    print(f"  成功从 page.body 解析")
                except Exception as body_err:
                    print(f"  page.body 解析失败: {body_err}")

        # 方法3: 尝试 page.text
        if not parsed_data and hasattr(page, 'text'):
            text = page.text
            if text:
                try:
                    if hasattr(text, 'get') and callable(text.get):
                        text = text.get()
                    parsed_data = json.loads(str(text))
                    print(f"  成功从 page.text 解析")
                except Exception as text_err:
                    print(f"  page.text 解析失败: {text_err}")

        if parsed_data:
            return {"success": True, "data": parsed_data, "error": None}
        else:
            return {"success": False, "data": None, "error": "无法解析响应数据"}

    except Exception as e:
        print(f"  请求失败: {e}")
        return {"success": False, "data": None, "error": str(e)}


def try_find_api_endpoint(app_name):
    """
    尝试查找应用使用量的 API 端点

    参数:
        app_name: 应用名称（如 "claude-code"）

    返回:
        dict: {"success": bool, "data": dict/None, "error": str/None, "endpoint": str/None}
    """
    encoded_app = quote(app_name)

    # 可能的 API 端点列表
    api_candidates = [
        f"https://openrouter.ai/api/frontend/stats/app-usage?app={encoded_app}",
        f"https://openrouter.ai/api/frontend/stats/top-models-for-app?app={encoded_app}",
        f"https://openrouter.ai/api/internal/v1/app-stats?app={encoded_app}",
        f"https://openrouter.ai/api/frontend/app/{encoded_app}/usage",
        f"https://openrouter.ai/api/frontend/app/{encoded_app}/stats",
    ]

    print(f"\n尝试查找 {app_name} 的 API 端点...")

    for i, url in enumerate(api_candidates, 1):
        print(f"\n[{i}/{len(api_candidates)}] 测试端点...")
        result = try_fetch_api(url, f"候选 API {i}")

        if result["success"] and result["data"]:
            # 检查返回的数据是否有效
            data = result["data"]
            if isinstance(data, dict) and len(data) > 0:
                print(f"  [OK] 找到有效 API 端点！")
                return {
                    "success": True,
                    "data": data,
                    "error": None,
                    "endpoint": url
                }

        # 避免请求过快
        time.sleep(1)

    print(f"\n[X] 未找到有效的 API 端点")
    return {
        "success": False,
        "data": None,
        "error": "未找到有效的 API 端点",
        "endpoint": None
    }
