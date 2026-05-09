#!/usr/bin/env python
"""
OpenRouter Apps 页面爬虫

爬取 https://openrouter.ai/apps 页面的全部应用信息

使用方式:
    python scraper.py
    python scraper.py --output ./output
    python scraper.py --save-db

数据存储：
    - JSON 原始数据: data/raw/json/openrouter/apps/
    - HTML 调试文件: data/raw/html/openrouter/apps/
    - Excel 文件: data/processed/excel/openrouter/apps/
    - SQLite 数据库: data/db/trend_tracker.db
"""

import os
import sys
import json
import time
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 尝试导入 scrapling
try:
    from scrapling.fetchers import StealthyFetcher, Fetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    StealthyFetcher = None
    Fetcher = None

# 尝试导入 pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# 导入统一数据存储
from data import DataStorage


# 默认请求头
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Referer': 'https://openrouter.ai/',
}


def fetch_apps_api() -> Dict[str, Any]:
    """
    尝试通过 API 端点获取 apps 数据

    返回:
        dict: {"success": bool, "data": list/None, "error": str/None}
    """
    if not SCRAPLING_AVAILABLE:
        return {"success": False, "data": None, "error": "Scrapling 未安装"}

    # 可能的 API 端点
    api_endpoints = [
        "https://openrouter.ai/api/frontend/apps",
        "https://openrouter.ai/api/v1/apps",
        "https://openrouter.ai/api/apps",
    ]

    for endpoint in api_endpoints:
        try:
            print(f"  尝试 API: {endpoint}")

            page = StealthyFetcher.fetch(
                endpoint,
                headers=DEFAULT_HEADERS,
                headless=True,
                network_idle=True
            )

            # 尝试解析 JSON
            if hasattr(page, 'json') and callable(page.json):
                try:
                    data = page.json()
                    if data and isinstance(data, (dict, list)):
                        print(f"  [OK] API 成功: {endpoint}")
                        return {"success": True, "data": data, "endpoint": endpoint, "error": None}
                except Exception:
                    pass

            # 尝试从 body 解析
            if hasattr(page, 'body'):
                body = page.body
                if body:
                    if isinstance(body, bytes):
                        body = body.decode('utf-8', errors='ignore')
                    try:
                        data = json.loads(body)
                        if data:
                            print(f"  [OK] API 成功: {endpoint}")
                            return {"success": True, "data": data, "endpoint": endpoint, "error": None}
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            print(f"  API {endpoint} 失败: {e}")
            continue

    return {"success": False, "data": None, "error": "所有 API 端点都失败"}


def fetch_apps_dom() -> Dict[str, Any]:
    """
    通过 DOM 爬取获取 apps 页面数据

    返回:
        dict: {"success": bool, "data": list/None, "html": str/None, "error": str/None}
    """
    if not SCRAPLING_AVAILABLE:
        return {"success": False, "data": None, "html": None, "error": "Scrapling 未安装"}

    url = "https://openrouter.ai/apps"

    try:
        print(f"  爬取页面: {url}")
        start_time = time.time()

        page = StealthyFetcher.fetch(
            url,
            headers=DEFAULT_HEADERS,
            headless=True,
            network_idle=True,
            wait_for='body'  # 等待 body 加载
        )

        elapsed = time.time() - start_time
        print(f"  页面加载完成，耗时: {elapsed:.2f}秒")

        # 获取 HTML
        html_content = None
        if hasattr(page, 'html'):
            html_content = page.html
        elif hasattr(page, 'body'):
            html_content = page.body
            if isinstance(html_content, bytes):
                html_content = html_content.decode('utf-8', errors='ignore')

        if not html_content:
            html_content = str(page)

        print(f"  HTML 大小: {len(html_content):,} 字符")

        # 提取 apps 数据
        apps_data = extract_apps_from_page(page)

        if apps_data:
            print(f"  [OK] 提取到 {len(apps_data)} 个应用")
            return {
                "success": True,
                "data": apps_data,
                "html": html_content,
                "error": None
            }
        else:
            return {
                "success": False,
                "data": None,
                "html": html_content,
                "error": "未能从页面提取到应用数据"
            }

    except Exception as e:
        return {"success": False, "data": None, "html": None, "error": str(e)}


def extract_apps_from_page(page) -> List[Dict[str, Any]]:
    """
    从页面中提取应用列表数据

    参数:
        page: Scrapling 页面对象

    返回:
        list: 应用数据列表
    """
    apps = []

    try:
        # 方法1: 查找 JSON 数据脚本
        print("  尝试从 script 标签提取 JSON 数据...")

        # 查找所有 script 标签
        scripts = page.css('script')
        for script in scripts:
            script_text = script.text_content() if hasattr(script, 'text_content') else str(script)

            # 查找包含 apps 数据的 JSON
            if 'apps' in script_text.lower() or 'application' in script_text.lower():
                try:
                    # 尝试提取 JSON
                    import re
                    # 查找 JSON 对象
                    json_matches = re.findall(r'\{[^{}]*"apps"[^{}]*\}', script_text)
                    for match in json_matches:
                        try:
                            data = json.loads(match)
                            if 'apps' in data:
                                apps.extend(data['apps'])
                        except:
                            pass
                except Exception:
                    pass

        if apps:
            return apps

        # 方法2: 从 DOM 元素提取
        print("  尝试从 DOM 元素提取数据...")

        # 查找应用卡片/列表项
        # OpenRouter 通常使用特定的 class 或 data 属性
        selectors = [
            'div[class*="app"]',
            'a[href^="/apps/"]',
            'tr[data-app]',
            'div[data-testid*="app"]',
            '.app-card',
            '.app-item',
            '.app-row',
        ]

        for selector in selectors:
            try:
                elements = page.css(selector)
                if elements:
                    print(f"    找到 {len(elements)} 个元素: {selector}")

                    for elem in elements:
                        app_data = extract_app_from_element(elem)
                        if app_data and app_data.get('slug'):
                            apps.append(app_data)

                    if apps:
                        return apps
            except Exception as e:
                continue

        # 方法3: 查找表格行
        print("  尝试从表格提取数据...")
        try:
            rows = page.css('tr')
            if rows:
                # 跳过表头
                for row in rows[1:]:
                    cells = row.css('td, th')
                    if len(cells) >= 2:
                        app_data = {}

                        # 尝试提取链接和名称
                        links = row.css('a')
                        for link in links:
                            href = link.attrib.get('href', '')
                            if '/apps/' in href:
                                app_data['slug'] = href.split('/apps/')[-1].strip('/')
                                app_data['name'] = link.text_content().strip() if hasattr(link, 'text_content') else str(link).strip()
                                app_data['url'] = f"https://openrouter.ai{href}"
                                break

                        # 提取其他单元格数据
                        cell_texts = []
                        for cell in cells:
                            text = cell.text_content().strip() if hasattr(cell, 'text_content') else str(cell).strip()
                            cell_texts.append(text)

                        if len(cell_texts) > 1:
                            app_data['raw_cells'] = cell_texts

                        if app_data.get('slug'):
                            apps.append(app_data)

                if apps:
                    return apps
        except Exception as e:
            print(f"    表格提取失败: {e}")

        # 方法4: 查找所有链接到 /apps/ 的元素
        print("  尝试从链接提取数据...")
        try:
            links = page.css('a[href*="/apps/"]')
            for link in links:
                href = link.attrib.get('href', '')
                if href.startswith('/apps/') and href != '/apps':
                    slug = href.replace('/apps/', '').strip('/')
                    if slug and not any(a.get('slug') == slug for a in apps):
                        name = link.text_content().strip() if hasattr(link, 'text_content') else slug
                        apps.append({
                            'slug': slug,
                            'name': name,
                            'url': f"https://openrouter.ai{href}"
                        })

            if apps:
                return apps
        except Exception as e:
            print(f"    链接提取失败: {e}")

    except Exception as e:
        print(f"  提取数据失败: {e}")

    return apps


def extract_app_from_element(elem) -> Dict[str, Any]:
    """
    从单个元素提取应用数据

    参数:
        elem: DOM 元素

    返回:
        dict: 应用数据
    """
    app_data = {}

    try:
        # 提取链接
        links = elem.css('a') if hasattr(elem, 'css') else []
        for link in links:
            href = link.attrib.get('href', '')
            if '/apps/' in href:
                app_data['slug'] = href.split('/apps/')[-1].strip('/')
                app_data['url'] = f"https://openrouter.ai{href}"
                if not app_data.get('name'):
                    app_data['name'] = link.text_content().strip() if hasattr(link, 'text_content') else ''
                break

        # 提取文本内容
        text = elem.text_content().strip() if hasattr(elem, 'text_content') else ''
        app_data['text'] = text

        # 提取 data 属性
        for attr in ['data-slug', 'data-name', 'data-id']:
            if attr in elem.attrib:
                key = attr.replace('data-', '')
                app_data[key] = elem.attrib[attr]

    except Exception:
        pass

    return app_data


def save_raw_data(data: Any, output_dir: str, filename: str) -> Optional[str]:
    """
    保存原始数据到文件

    参数:
        data: 数据内容
        output_dir: 输出目录 (已废弃，使用 DataStorage)
        filename: 文件名

    返回:
        str: 保存的文件路径
    """
    storage = DataStorage()

    # 根据文件扩展名判断保存类型
    if filename.endswith('.json'):
        # 提取文件名（不含扩展名）
        name = filename[:-5]
        filepath = storage.save_json(data, 'openrouter', name, subcategory='apps', timestamp=False)
    elif filename.endswith('.html'):
        name = filename[:-5]
        filepath = storage.save_html(str(data), 'openrouter', name, subcategory='apps', timestamp=False)
    else:
        # 其他格式直接保存
        filepath = storage.get_json_path('openrouter', filename, subcategory='apps')
        with open(filepath, 'w', encoding='utf-8') as f:
            if isinstance(data, (dict, list)):
                json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(data))
        print(f"  已保存: {filepath}")

    return str(filepath)


def export_to_excel(apps: List[Dict], output_dir: str) -> Optional[str]:
    """
    导出应用数据到 Excel

    参数:
        apps: 应用列表
        output_dir: 输出目录 (已废弃，使用 DataStorage)

    返回:
        str: Excel 文件路径
    """
    if not PANDAS_AVAILABLE:
        print("  无法导出 Excel: pandas 未安装")
        return None

    if not apps:
        print("  无数据可导出")
        return None

    storage = DataStorage()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"openrouter_apps"

    try:
        df = pd.DataFrame(apps)

        # 清理数据
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x)

        # 添加元数据
        metadata = {
            '抓取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '数据来源': 'OpenRouter Apps',
            '应用数量': len(df)
        }

        filepath = storage.save_excel(
            df,
            'openrouter',
            filename,
            subcategory='apps',
            timestamp=False,
            metadata=metadata
        )

        if filepath:
            # 重命名以包含时间戳
            new_filepath = filepath.parent / f"{filename}_{timestamp}.xlsx"
            filepath.rename(new_filepath)
            print(f"  [OK] Excel 已保存: {new_filepath}")
            print(f"       共 {len(df)} 行, {len(df.columns)} 列")
            return str(new_filepath)

        return None

    except Exception as e:
        print(f"  导出 Excel 失败: {e}")
        return None


async def save_apps_to_db(apps: List[Dict]) -> bool:
    """
    保存应用数据到数据库

    参数:
        apps: 应用列表

    返回:
        bool: 是否成功
    """
    if not apps:
        print("  无数据需要保存到数据库")
        return False

    try:
        # 动态导入数据库模块
        sys.path.insert(0, str(PROJECT_ROOT))
        from data import get_db_connection

        db = await get_db_connection()
        now = datetime.now().isoformat()

        saved_count = 0
        for app in apps:
            slug = app.get('slug', '')
            if not slug:
                continue

            # 准备数据
            raw_data_str = json.dumps(app.get('raw_data', {}), ensure_ascii=False) if app.get('raw_data') else None

            # 使用 UPSERT (INSERT OR REPLACE)
            await db.execute('''
                INSERT OR REPLACE INTO openrouter_apps
                (slug, name, description, url, icon_url, category, website, usage_count, created_at, updated_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                slug,
                app.get('name', ''),
                app.get('description', ''),
                app.get('url', f"https://openrouter.ai/apps/{slug}"),
                app.get('icon_url', ''),
                app.get('category', ''),
                app.get('website', ''),
                app.get('usage_count', 0),
                app.get('created_at'),
                now,
                raw_data_str
            ))
            saved_count += 1

        await db.commit()
        print(f"  [OK] 已保存 {saved_count} 个应用到数据库")
        return True

    except Exception as e:
        print(f"  保存到数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_apps_to_db_sync(apps: List[Dict]) -> bool:
    """同步版本：保存应用数据到数据库"""
    return asyncio.run(save_apps_to_db(apps))


def scrape_apps(output_dir: Optional[str] = None, save_to_db: bool = False) -> Dict[str, Any]:
    """
    主函数：爬取 OpenRouter Apps 页面

    参数:
        output_dir: 输出目录（已废弃，使用 DataStorage）
        save_to_db: 是否保存到数据库

    返回:
        dict: {
            "success": bool,
            "apps": list,
            "count": int,
            "source": str,
            "files": dict
        }
    """
    print("\n" + "=" * 60)
    print("OpenRouter Apps 爬虫")
    print("=" * 60)

    if not SCRAPLING_AVAILABLE:
        print("\n[ERROR] Scrapling 未安装")
        print("请安装: pip install scrapling[fetchers]")
        return {"success": False, "apps": [], "count": 0, "error": "Scrapling 未安装"}

    result = {
        "success": False,
        "apps": [],
        "count": 0,
        "source": None,
        "files": {"raw": None, "excel": None},
        "db_saved": False
    }

    fetch_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 方法1: 尝试 API
    print("\n[方法1] 尝试 API 端点...")
    api_result = fetch_apps_api()

    if api_result["success"]:
        print(f"  [OK] API 成功: {api_result.get('endpoint')}")

        # 保存原始数据
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_file = save_raw_data(
            api_result["data"],
            output_dir,
            f"apps_api_{timestamp}.json"
        )
        result["files"]["raw"] = raw_file

        # 解析数据
        from .parser import parse_apps_data
        apps = parse_apps_data(api_result["data"])

        if apps:
            result["success"] = True
            result["apps"] = apps
            result["count"] = len(apps)
            result["source"] = "API"

            # 导出 Excel
            excel_file = export_to_excel(apps, output_dir)
            result["files"]["excel"] = excel_file

            # 保存到数据库
            if save_to_db:
                result["db_saved"] = save_apps_to_db_sync(apps)

            return result

    # 方法2: DOM 爬取
    print("\n[方法2] DOM 爬取...")
    dom_result = fetch_apps_dom()

    if dom_result["success"]:
        print("  [OK] DOM 爬取成功")

        # 保存 HTML
        if dom_result.get("html"):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_file = save_raw_data(
                dom_result["html"],
                output_dir,
                f"apps_page_{timestamp}.html"
            )
            result["files"]["raw"] = html_file

        # 保存提取的数据
        apps = dom_result.get("data", [])

        if apps:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = save_raw_data(
                apps,
                output_dir,
                f"apps_data_{timestamp}.json"
            )

            result["success"] = True
            result["apps"] = apps
            result["count"] = len(apps)
            result["source"] = "DOM"

            # 导出 Excel
            excel_file = export_to_excel(apps, output_dir)
            result["files"]["excel"] = excel_file

            # 保存到数据库
            if save_to_db:
                result["db_saved"] = save_apps_to_db_sync(apps)

            return result

    # 失败
    print("\n[FAILED] 所有方法都失败")
    result["error"] = "无法获取应用数据"

    return result


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='OpenRouter Apps 爬虫'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='输出目录（已废弃，数据自动保存到 data 目录）'
    )
    parser.add_argument(
        '--save-db',
        action='store_true',
        help='保存数据到数据库'
    )

    args = parser.parse_args()

    # 执行爬取
    result = scrape_apps(output_dir=args.output, save_to_db=args.save_db)

    # 打印结果
    print("\n" + "=" * 60)
    print("执行结果")
    print("=" * 60)
    print(f"成功: {result['success']}")

    if result['success']:
        print(f"数据来源: {result['source']}")
        print(f"应用数量: {result['count']}")
        print(f"原始文件: {result['files'].get('raw')}")
        print(f"Excel 文件: {result['files'].get('excel')}")
        print(f"数据库保存: {result.get('db_saved', False)}")

        # 显示前几个应用
        if result['apps']:
            print("\n前 5 个应用:")
            for i, app in enumerate(result['apps'][:5], 1):
                print(f"  {i}. {app.get('name', app.get('slug', '未知'))}")
    else:
        print(f"错误: {result.get('error')}")

    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
