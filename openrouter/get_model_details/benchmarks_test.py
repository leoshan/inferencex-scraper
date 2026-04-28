#!/usr/bin/env python
"""
Benchmarks 页面抓取 - 系统性测试多种方法

记录所有尝试到 get_benchmark.md 文件
"""

import json
import re
import os
import time
from datetime import datetime

try:
    from scrapling.fetchers import StealthyFetcher, DynamicFetcher, Fetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    print("错误: Scrapling库未安装")
    exit(1)

# 测试记录文件
LOG_FILE = os.path.join(os.path.dirname(__file__), "get_benchmark.md")

def log(message):
    """记录日志到文件和打印"""
    print(message)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(message + "\n")

def log_section(title):
    """记录章节标题"""
    log(f"\n## {title}\n")

def log_code(code):
    """记录代码块"""
    log(f"```\n{code}\n```\n")

def save_html(html_content, filename):
    """保存 HTML 文件"""
    output_dir = os.path.dirname(__file__)
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return filepath


def attempt_1_basic_fetch(url):
    """尝试1: 基础 StealthyFetcher"""
    log_section("尝试1: 基础 StealthyFetcher")
    log(f"URL: {url}")
    log("参数: headless=True, network_idle=True")

    try:
        start_time = time.time()
        page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
        elapsed = time.time() - start_time
        log(f"耗时: {elapsed:.2f}秒")

        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        if html_content:
            log(f"HTML 大小: {len(html_content):,} 字符")
            filepath = save_html(html_content, "attempt_1_basic.html")
            log(f"HTML 已保存: {filepath}")

            # 检查关键内容
            check_benchmark_content(html_content)
            return html_content
        else:
            log("错误: 无法获取 HTML 内容")
            return None

    except Exception as e:
        log(f"错误: {e}")
        return None


def attempt_2_dynamic_fetcher(url):
    """尝试2: DynamicFetcher (可能支持更多 JS 渲染)"""
    log_section("尝试2: DynamicFetcher")

    try:
        start_time = time.time()
        page = DynamicFetcher.fetch(url, headless=True, network_idle=True, wait=5000)
        elapsed = time.time() - start_time
        log(f"耗时: {elapsed:.2f}秒")

        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        if html_content:
            log(f"HTML 大小: {len(html_content):,} 字符")
            filepath = save_html(html_content, "attempt_2_dynamic.html")
            log(f"HTML 已保存: {filepath}")

            check_benchmark_content(html_content)
            return html_content
        else:
            log("错误: 无法获取 HTML 内容")
            return None

    except Exception as e:
        log(f"错误: {e}")
        return None


def attempt_3_with_wait(url):
    """尝试3: 增加等待时间"""
    log_section("尝试3: 增加等待时间 (wait=10000)")

    try:
        start_time = time.time()
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            wait=10000  # 等待 10 秒
        )
        elapsed = time.time() - start_time
        log(f"耗时: {elapsed:.2f}秒")

        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        if html_content:
            log(f"HTML 大小: {len(html_content):,} 字符")
            filepath = save_html(html_content, "attempt_3_wait.html")
            log(f"HTML 已保存: {filepath}")

            check_benchmark_content(html_content)
            return html_content
        else:
            log("错误: 无法获取 HTML 内容")
            return None

    except Exception as e:
        log(f"错误: {e}")
        return None


def attempt_4_scroll_page(url):
    """尝试4: 滚动页面触发加载"""
    log_section("尝试4: 滚动页面触发加载")

    try:
        start_time = time.time()
        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            wait=3000
        )

        # 尝试滚动
        if hasattr(page, 'evaluate'):
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                log("已执行页面滚动")
            except Exception as scroll_err:
                log(f"滚动失败: {scroll_err}")

        elapsed = time.time() - start_time
        log(f"耗时: {elapsed:.2f}秒")

        html_content = None
        if hasattr(page, 'body'):
            body = page.body
            if isinstance(body, bytes):
                html_content = body.decode('utf-8', errors='ignore')
            else:
                html_content = str(body)

        if html_content:
            log(f"HTML 大小: {len(html_content):,} 字符")
            filepath = save_html(html_content, "attempt_4_scroll.html")
            log(f"HTML 已保存: {filepath}")

            check_benchmark_content(html_content)
            return html_content
        else:
            log("错误: 无法获取 HTML 内容")
            return None

    except Exception as e:
        log(f"错误: {e}")
        return None


def attempt_5_check_api_endpoints(html_content):
    """尝试5: 从 HTML 中提取 API 端点"""
    log_section("尝试5: 从 HTML 中提取 API 端点")

    if not html_content:
        log("跳过: 没有 HTML 内容")
        return

    # 查找所有 API URL
    api_patterns = [
        r'["\'](/api/[^"\']+)["\']',
        r'["\'](https://openrouter\.ai/api/[^"\']+)["\']',
        r'fetch\(["\']([^"\']+)["\']',
    ]

    all_apis = set()
    for pattern in api_patterns:
        matches = re.findall(pattern, html_content)
        all_apis.update(matches)

    log(f"找到 {len(all_apis)} 个 API 端点:")

    # 筛选 benchmark 相关的 API
    benchmark_apis = []
    for api in sorted(all_apis):
        if 'benchmark' in api.lower() or 'score' in api.lower() or 'arena' in api.lower():
            benchmark_apis.append(api)
            log(f"  [BENCHMARK] {api}")
        elif 'design' in api.lower() or 'artificial' in api.lower():
            benchmark_apis.append(api)
            log(f"  [DESIGN/ARTIFICIAL] {api}")

    if not benchmark_apis:
        log("未找到 benchmark 相关 API")
        # 列出所有 API
        log("\n所有 API 端点:")
        for api in sorted(all_apis)[:30]:
            log(f"  {api}")


def attempt_6_extract_json_data(html_content):
    """尝试6: 提取嵌入的 JSON 数据"""
    log_section("尝试6: 提取嵌入的 JSON 数据")

    if not html_content:
        log("跳过: 没有 HTML 内容")
        return

    # 查找 __NEXT_DATA__
    next_data_match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>',
        html_content,
        re.DOTALL
    )

    if next_data_match:
        log("找到 __NEXT_DATA__")
        try:
            next_data = json.loads(next_data_match.group(1))
            log(f"顶层键: {list(next_data.keys())}")

            # 保存 JSON
            filepath = save_html(json.dumps(next_data, ensure_ascii=False, indent=2), "attempt_6_next_data.json")
            log(f"JSON 已保存: {filepath}")

            # 递归搜索 benchmark 数据
            found = find_benchmark_in_json(next_data, "")
            if found:
                log(f"\n找到 {len(found)} 个 benchmark 相关数据:")
                for path, value in found[:10]:
                    log(f"  {path}: {str(value)[:100]}")
        except json.JSONDecodeError as e:
            log(f"JSON 解析失败: {e}")
    else:
        log("未找到 __NEXT_DATA__")

    # 查找其他 JSON 数据
    json_pattern = r'<script[^>]*type="application/json"[^>]*>(.+?)</script>'
    json_matches = re.findall(json_pattern, html_content, re.DOTALL)
    log(f"\n找到 {len(json_matches)} 个 JSON script 标签")


def attempt_7_extract_text_content(html_content):
    """尝试7: 提取纯文本内容"""
    log_section("尝试7: 提取纯文本内容")

    if not html_content:
        log("跳过: 没有 HTML 内容")
        return

    # 移除 HTML 标签
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    log(f"纯文本大小: {len(text):,} 字符")

    # 搜索关键词
    keywords = ['Elo', 'benchmark', 'tournament', 'Design Arena', 'Artificial Analysis',
                'Models Arena', 'Agents Arena', 'Ranking Distribution', 'Category Performance']

    log("\n关键词搜索:")
    for kw in keywords:
        count = text.lower().count(kw.lower())
        log(f"  '{kw}': {count} 次")

    # 提取数字模式 (可能是 Elo 分数)
    elo_pattern = r'\b(1[0-9]{3}|2000)\b'  # 1000-2000 的数字
    elo_matches = re.findall(elo_pattern, text)
    if elo_matches:
        log(f"\n可能的 Elo 分数 (1000-2000): {elo_matches[:20]}")


def find_benchmark_in_json(obj, path, depth=0, max_depth=8):
    """递归搜索 JSON 中的 benchmark 数据"""
    if depth > max_depth:
        return []

    results = []

    if isinstance(obj, dict):
        keys_lower = [k.lower() for k in obj.keys()]
        benchmark_keywords = ['benchmark', 'elo', 'score', 'arena', 'tournament', 'ranking']

        for kw in benchmark_keywords:
            if any(kw in k for k in keys_lower):
                results.append((path, obj))
                break

        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            results.extend(find_benchmark_in_json(value, new_path, depth + 1, max_depth))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(find_benchmark_in_json(item, f"{path}[{i}]", depth + 1, max_depth))

    return results


def check_benchmark_content(html_content):
    """检查 HTML 中是否包含 benchmark 数据"""
    log("\n检查 benchmark 内容:")

    # 检查关键字符串
    checks = [
        ("Elo", r'\bElo\b'),
        ("Design Arena", r'Design Arena'),
        ("Models Arena", r'Models Arena'),
        ("Agents Arena", r'Agents Arena'),
        ("Ranking Distribution", r'Ranking Distribution'),
        ("Category Performance", r'Category Performance'),
        ("tournament", r'tournament'),
        ("1320", r'1320'),  # 示例 Elo 分数
        ("1342", r'1342'),
    ]

    for name, pattern in checks:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        log(f"  {name}: {len(matches)} 次")


def main():
    """主测试函数"""
    # 初始化日志文件
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Benchmarks 页面抓取测试记录\n\n")
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"目标 URL: https://openrouter.ai/anthropic/claude-opus-4.7/benchmarks\n\n")
        f.write("---\n")

    url = "https://openrouter.ai/anthropic/claude-opus-4.7/benchmarks"

    log("=" * 80)
    log("开始系统性测试 Benchmarks 页面抓取")
    log("=" * 80)

    # 尝试各种方法
    html_content = attempt_1_basic_fetch(url)

    if not html_content or "Elo" not in html_content:
        html_content = attempt_2_dynamic_fetcher(url)

    if not html_content or "Elo" not in html_content:
        html_content = attempt_3_with_wait(url)

    if not html_content or "Elo" not in html_content:
        html_content = attempt_4_scroll_page(url)

    # 分析 HTML 内容
    if html_content:
        attempt_5_check_api_endpoints(html_content)
        attempt_6_extract_json_data(html_content)
        attempt_7_extract_text_content(html_content)

    log("\n" + "=" * 80)
    log("测试完成!")
    log("=" * 80)
    log(f"\n详细记录已保存到: {LOG_FILE}")


if __name__ == "__main__":
    main()
