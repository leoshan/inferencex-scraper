#!/usr/bin/env python
"""
OpenRouter批量模型详细数据获取脚本

基于 `openrouter_models_providers.xlsx` 文件的"所有模型"工作表的"slug"列，
使用 `get_1model_details.py` 中的方法，批量获取所有模型的详细数据。

功能特点：
1. 从Excel读取模型slug列表
2. 为每个模型生成7个API URL
3. 异步并发获取每个模型的7个API数据
4. 解析数据并保存到统一的Excel文件（方案B）
5. 支持测试版本（只处理前N个模型）
6. 支持指定起始索引和数量（从第M个模型开始，处理N个模型）
7. 不保存原始响应文件

方案B输出格式：
- 汇总表 (Summary): 模型列表和处理状态
- 按API类型分组的工作表（所有模型数据合并）：
  * top_apps_all_models
  * top_apps_chart_all_models
  * endpoint_stats_all_models
  * author_models_all_models
  * uptime_recent_all_models
  * provider_preferences_all_models
  * artificial_analysis_benchmarks_all_models
  * design_arena_benchmarks_all_models
"""

import sys
import os
import json
import time
import asyncio
import pandas as pd
import argparse
from datetime import datetime
from urllib.parse import urlparse, parse_qs, quote
import re
import traceback
import tempfile

# 导入Scrapling库
try:
    from scrapling.fetchers import AsyncFetcher
    SCRAPLING_AVAILABLE = True
    ASYNC_FETCHER_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    ASYNC_FETCHER_AVAILABLE = False
    print("错误: Scrapling库未安装或版本不支持异步")
    print("请安装支持异步的Scrapling版本")
    sys.exit(1)

# 从现有脚本导入解析函数
from get_1model_details import (
    parse_top_apps_json,
    parse_author_models,
    parse_endpoint_stats,
    parse_uptime_recent,
    parse_provider_preferences,
    parse_artificial_analysis_benchmark,
    parse_design_arena_benchmark
)

# ============================================================================
# 配置参数
# ============================================================================

class Config:
    """配置参数类"""
    # 输入文件
    INPUT_EXCEL = "openrouter_models_providers.xlsx"
    INPUT_SHEET = "所有模型"
    SLUG_COLUMN = "slug"

    # 输出设置
    OUTPUT_PREFIX = "openrouter_batch_model_details"

    # 处理设置
    TEST_MODE = True  # 测试模式：只处理前N个模型
    TEST_LIMIT = 100   # 测试模式处理模型数量
    START_INDEX = 0    # 起始模型索引（从0开始）
    MAX_RETRIES = 3   # API请求最大重试次数
    RETRY_DELAY = 2   # 重试延迟（秒）

    # 异步设置
    MAX_CONCURRENT_APIS = 7  # 每个模型最大并发API数
    REQUESTS_PER_SECOND = 2  # 每秒请求数限制
    REQUEST_TIMEOUT = 30     # 请求超时时间（秒）

    # 数据处理
    SAVE_RAW_RESPONSE = False  # 是否保存原始响应文件


# ============================================================================
# 异步API获取函数
# ============================================================================

class RateLimiter:
    """速率限制器"""
    def __init__(self, requests_per_second=2):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0

    async def wait_if_needed(self):
        """如果需要，等待以达到速率限制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)

        self.last_request_time = time.time()


class ModelDataFetcher:
    """模型数据获取器"""
    def __init__(self, config=Config()):
        self.config = config
        self.rate_limiter = RateLimiter(config.REQUESTS_PER_SECOND)

        # 默认请求头
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'https://openrouter.ai/',
            'Origin': 'https://openrouter.ai',
        }

    def generate_api_urls_for_model(self, model_slug):
        """
        为单个模型生成7个API URL

        参数:
            model_slug: 模型slug，格式如 "minimax/minimax-m2.7-20260318"

        返回:
            dict: API名称到URL的映射
        """
        # 解析作者和模型名称
        if '/' in model_slug:
            author = model_slug.split('/')[0]
            full_model = model_slug
        else:
            author = model_slug
            full_model = model_slug

        # URL编码
        encoded_slug = quote(full_model)
        encoded_author = quote(author)

        return {
            "top_apps": f"https://openrouter.ai/api/frontend/stats/top-apps-for-model?permaslug={encoded_slug}&variant=standard",
            "endpoint_stats": f"https://openrouter.ai/api/frontend/stats/endpoint?permaslug={encoded_slug}&variant=standard",
            "author_models": f"https://openrouter.ai/api/frontend/author-models?authorSlug={encoded_author}",
            "uptime_recent": f"https://openrouter.ai/api/frontend/stats/uptime-recent?permaslug={encoded_slug}",
            "provider_preferences": "https://openrouter.ai/api/internal/v1/provider-preferences",
            "artificial_analysis_benchmarks": f"https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks?slug={encoded_slug}",
            "design_arena_benchmarks": f"https://openrouter.ai/api/internal/v1/design-arena-benchmarks?slug={encoded_slug}"
        }

    async def fetch_single_api_async(self, url, api_name, model_slug="", attempt=1):
        """
        异步获取单个API数据

        参数:
            url: API URL
            api_name: API名称（用于日志）
            model_slug: 模型slug（用于日志）
            attempt: 当前尝试次数

        返回:
            dict: 包含success, data, error, api_name等信息
        """
        log_prefix = f"[{model_slug or 'unknown'}] {api_name}"

        try:
            # 应用速率限制
            await self.rate_limiter.wait_if_needed()

            print(f"{log_prefix}: 开始请求 (尝试 {attempt}/{self.config.MAX_RETRIES})")

            # 使用AsyncFetcher进行请求
            start_time = time.time()

            try:
                page = await AsyncFetcher.get(
                    url,
                    headers=self.default_headers,
                    timeout=self.config.REQUEST_TIMEOUT
                )
            except Exception as fetch_err:
                print(f"{log_prefix}: AsyncFetcher失败: {fetch_err}")
                raise

            elapsed_time = time.time() - start_time

            # 提取HTTP状态码
            http_status_code = None
            status_attrs = ['status_code', 'status', 'code']
            for attr in status_attrs:
                if hasattr(page, attr):
                    try:
                        attr_value = getattr(page, attr)
                        if attr_value is not None:
                            http_status_code = int(attr_value)
                            break
                    except (ValueError, TypeError):
                        pass

            print(f"{log_prefix}: 请求完成，耗时: {elapsed_time:.2f}秒")
            if http_status_code is not None:
                print(f"{log_prefix}: HTTP状态码: {http_status_code}")

                # 检查HTTP状态码（2xx表示成功）
                if http_status_code < 200 or http_status_code >= 300:
                    error_msg = f"HTTP错误: 状态码 {http_status_code}"
                    print(f"{log_prefix}: {error_msg}")
                    return {
                        "success": False,
                        "api_name": api_name,
                        "error": error_msg,
                        "elapsed_time": elapsed_time,
                        "http_status_code": http_status_code,
                        "error_type": "http_error",
                        "attempt": attempt,
                        "max_retries": self.config.MAX_RETRIES,
                        "url": url,
                        "model_slug": model_slug
                    }

            # 获取响应内容
            raw_text = None
            parsed_data = None

            # 方法1: 尝试使用json()方法
            if hasattr(page, 'json') and callable(page.json):
                try:
                    parsed_data = page.json()
                    raw_text = json.dumps(parsed_data, ensure_ascii=False, indent=2)
                except Exception as json_err:
                    print(f"{log_prefix}: json()方法失败: {json_err}")

            # 方法2: 尝试body属性
            if not raw_text and hasattr(page, 'body'):
                try:
                    body_value = page.body
                    if isinstance(body_value, bytes):
                        raw_text = body_value.decode('utf-8')
                    else:
                        raw_text = str(body_value)

                    # 尝试解析JSON
                    if parsed_data is None:
                        try:
                            parsed_data = json.loads(raw_text)
                        except json.JSONDecodeError:
                            pass
                except Exception as body_err:
                    print(f"{log_prefix}: 处理body时出错: {body_err}")

            # 方法3: 最后尝试
            if not raw_text:
                raw_text = str(page)

            if not raw_text:
                error_msg = "未能获取到响应内容"
                print(f"{log_prefix}: {error_msg}")
                return {
                    "success": False,
                    "api_name": api_name,
                    "error": error_msg,
                    "elapsed_time": elapsed_time,
                    "http_status_code": http_status_code,
                    "error_type": "no_response_content",
                    "attempt": attempt,
                    "max_retries": self.config.MAX_RETRIES,
                    "url": url,
                    "model_slug": model_slug
                }

            print(f"{log_prefix}: 响应大小: {len(raw_text):,} 字符")

            # 尝试解析JSON（如果尚未解析）
            if parsed_data is None:
                try:
                    parsed_data = json.loads(raw_text)
                except json.JSONDecodeError as json_err:
                    error_msg = f"无法解析JSON响应: {json_err}"
                    print(f"{log_prefix}: {error_msg}")
                    return {
                        "success": False,
                        "api_name": api_name,
                        "error": error_msg,
                        "raw_text": raw_text[:1000] if raw_text else "",
                        "elapsed_time": elapsed_time,
                        "http_status_code": http_status_code,
                        "error_type": "json_error",
                        "attempt": attempt,
                        "max_retries": self.config.MAX_RETRIES,
                        "url": url,
                        "model_slug": model_slug
                    }

            return {
                "success": True,
                "api_name": api_name,
                "data": parsed_data,
                "raw_text": raw_text,
                "elapsed_time": elapsed_time,
                "error": None,
                "http_status_code": http_status_code,
                "error_type": "success" if http_status_code and 200 <= http_status_code < 300 else "unknown",
                "attempt": attempt,
                "max_retries": self.config.MAX_RETRIES,
                "url": url,
                "model_slug": model_slug
            }

        except asyncio.TimeoutError:
            error_msg = f"请求超时 ({self.config.REQUEST_TIMEOUT}秒)"
            print(f"{log_prefix}: {error_msg}")
            return {
                "success": False,
                "api_name": api_name,
                "error": error_msg,
                "elapsed_time": self.config.REQUEST_TIMEOUT,
                "http_status_code": None,
                "error_type": "timeout",
                "attempt": attempt,
                "max_retries": self.config.MAX_RETRIES,
                "url": url,
                "model_slug": model_slug
            }
        except Exception as fetch_err:
            error_msg = f"请求异常: {fetch_err}"
            print(f"{log_prefix}: {error_msg}")
            return {
                "success": False,
                "api_name": api_name,
                "error": error_msg,
                "elapsed_time": 0,
                "http_status_code": None,
                "error_type": "network_error",
                "attempt": attempt,
                "max_retries": self.config.MAX_RETRIES,
                "url": url,
                "model_slug": model_slug
            }

    async def fetch_with_retry(self, url, api_name, model_slug=""):
        """
        带重试的异步获取

        参数:
            url: API URL
            api_name: API名称
            model_slug: 模型slug

        返回:
            dict: 请求结果
        """
        for attempt in range(1, self.config.MAX_RETRIES + 1):
            result = await self.fetch_single_api_async(url, api_name, model_slug, attempt)

            if result["success"]:
                return result

            # 如果失败且不是最后一次尝试，等待后重试
            if attempt < self.config.MAX_RETRIES:
                wait_time = self.config.RETRY_DELAY * (2 ** (attempt - 1))  # 指数退避
                print(f"[{model_slug}] {api_name}: 等待 {wait_time:.1f}秒后重试...")
                await asyncio.sleep(wait_time)

        # 所有重试都失败
        print(f"[{model_slug}] {api_name}: 所有重试失败")
        return result

    async def fetch_all_apis_for_model_async(self, model_slug):
        """
        并行获取单个模型的7个API数据

        参数:
            model_slug: 模型slug

        返回:
            dict: API名称到请求结果的映射
        """
        print(f"\n=== 开始处理模型: {model_slug} ===")
        start_time = time.time()

        # 生成API URL
        api_urls = self.generate_api_urls_for_model(model_slug)
        print(f"生成的API URL数量: {len(api_urls)}")

        # 创建所有API的异步任务
        tasks = []
        for api_name, api_url in api_urls.items():
            task = self.fetch_with_retry(api_url, api_name, model_slug)
            tasks.append(task)

        # 并行执行所有任务
        print(f"开始并行获取 {len(tasks)} 个API数据...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        api_results = {}
        success_count = 0
        fail_count = 0

        for i, result in enumerate(results):
            api_name = list(api_urls.keys())[i]

            if isinstance(result, Exception):
                print(f"[{model_slug}] {api_name}: 任务异常: {result}")
                api_results[api_name] = {
                    "success": False,
                    "api_name": api_name,
                    "error": f"任务异常: {result}",
                    "data": None,
                    "raw_text": ""
                }
                fail_count += 1
            else:
                api_results[api_name] = result
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1

        total_time = time.time() - start_time
        print(f"=== 模型处理完成: {model_slug} ===")
        print(f"  成功: {success_count}, 失败: {fail_count}")
        print(f"  总耗时: {total_time:.2f}秒")

        return api_results


# ============================================================================
# 数据处理函数
# ============================================================================

def read_model_slugs_from_excel(file_path, sheet_name="所有模型", column_name="slug", limit=None, start_index=0):
    """
    从Excel读取模型slug列表

    参数:
        file_path: Excel文件路径
        sheet_name: 工作表名称
        column_name: 列名
        limit: 限制读取数量（None表示全部）
        start_index: 起始索引（从0开始）

    返回:
        list: 模型slug列表
    """
    try:
        print(f"读取Excel文件: {file_path}")
        print(f"工作表: {sheet_name}, 列: {column_name}")

        # 读取Excel文件
        df = pd.read_excel(file_path, sheet_name=sheet_name)

        # 检查列是否存在
        if column_name not in df.columns:
            raise ValueError(f"列 '{column_name}' 不存在于工作表 '{sheet_name}' 中")

        # 提取slug列，去重并过滤空值
        slugs = df[column_name].dropna().unique().tolist()

        print(f"找到 {len(slugs)} 个唯一的模型slug")

        # 应用起始索引和限制
        total_slugs = len(slugs)

        # 检查起始索引是否有效
        if start_index < 0:
            start_index = 0
        elif start_index >= total_slugs:
            print(f"警告: 起始索引 {start_index} 超出范围，返回空列表")
            return []

        # 计算结束索引
        if limit is not None and limit > 0:
            end_index = start_index + limit
            if end_index > total_slugs:
                end_index = total_slugs
                print(f"警告: 限制数量 {limit} 超出范围，调整为 {end_index - start_index}")
        else:
            end_index = total_slugs

        # 切片
        slugs = slugs[start_index:end_index]

        # 打印信息
        if start_index > 0 or limit is not None:
            print(f"切片: 从索引 {start_index} 到 {end_index-1} (共 {len(slugs)} 个模型)")

        # 验证slug格式
        valid_slugs = []
        invalid_slugs = []

        for slug in slugs:
            if isinstance(slug, str) and slug.strip():
                valid_slugs.append(slug.strip())
            else:
                invalid_slugs.append(slug)

        if invalid_slugs:
            print(f"警告: 发现 {len(invalid_slugs)} 个无效的slug")

        print(f"有效模型slug数量: {len(valid_slugs)}")
        return valid_slugs

    except FileNotFoundError:
        print(f"错误: 文件不存在: {file_path}")
        raise
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        raise


def parse_model_data(api_results, model_slug):
    """
    解析模型数据

    参数:
        api_results: API获取结果字典
        model_slug: 模型slug

    返回:
        dict: 解析后的数据（DataFrame字典）
    """
    print(f"\n解析模型数据: {model_slug}")

    parsed_data = {}

    # API名称到解析函数的映射
    parse_functions = {
        "top_apps": parse_top_apps_json,
        "author_models": parse_author_models,
        "endpoint_stats": parse_endpoint_stats,
        "uptime_recent": parse_uptime_recent,
        "provider_preferences": parse_provider_preferences,
        "artificial_analysis_benchmarks": parse_artificial_analysis_benchmark,
        "design_arena_benchmarks": parse_design_arena_benchmark
    }

    for api_name, result in api_results.items():
        if not result["success"]:
            print(f"  {api_name}: 跳过（获取失败）")
            continue

        if api_name not in parse_functions:
            print(f"  {api_name}: 跳过（无解析函数）")
            continue

        temp_file_path = None
        try:
            # 保存原始数据到临时文件（用于解析）
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', encoding='utf-8', delete=False) as temp_file:
                json.dump(result["data"], temp_file, ensure_ascii=False, indent=2)
                temp_file_path = temp_file.name

            # 调用解析函数
            parse_func = parse_functions[api_name]

            if api_name == "top_apps":
                # top_apps API返回两个DataFrame
                df_apps, df_chart = parse_func(temp_file_path)
                parsed_data["top_apps"] = df_apps
                parsed_data["top_apps_chart"] = df_chart
                print(f"  {api_name}: 解析成功 -> top_apps ({len(df_apps)}行), top_apps_chart ({len(df_chart)}行)")
            else:
                # 其他API返回一个DataFrame
                df = parse_func(temp_file_path)
                parsed_data[api_name] = df
                print(f"  {api_name}: 解析成功 ({len(df)}行)")

        except Exception as parse_err:
            print(f"  {api_name}: 解析失败 - {parse_err}")
            # 返回空的DataFrame作为占位符
            if api_name == "top_apps":
                parsed_data["top_apps"] = pd.DataFrame()
                parsed_data["top_apps_chart"] = pd.DataFrame()
            else:
                parsed_data[api_name] = pd.DataFrame()
        finally:
            # 确保临时文件被删除
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    print(f"  警告: 无法删除临时文件 {temp_file_path}: {e}")

    return parsed_data


def add_model_slug_column(df, model_slug):
    """
    为DataFrame添加model_slug列

    参数:
        df: pandas DataFrame
        model_slug: 模型slug

    返回:
        DataFrame: 添加了model_slug列的新DataFrame
    """
    if df is None or df.empty:
        return df

    df_copy = df.copy()
    df_copy["model_slug"] = model_slug

    # 将model_slug列移到第一列
    cols = ["model_slug"] + [col for col in df_copy.columns if col != "model_slug"]
    df_copy = df_copy[cols]

    return df_copy


def clean_dataframe_for_excel(df):
    """
    清理DataFrame中的非法字符，使其兼容openpyxl/Excel

    参数:
        df: pandas DataFrame

    返回:
        清理后的DataFrame
    """
    if df is None or df.empty:
        return df

    import re
    import json as json_module

    # 定义要移除或替换的非法字符模式
    # 移除所有ASCII控制字符 (0x00-0x1F) 和 Unicode控制字符 (U+007F-U+009F)
    control_chars_regex = re.compile(r'[\x00-\x1f\x7f-\x9f]')

    # 创建副本，避免修改原始数据
    df_clean = df.copy()

    # 对每个列进行清理
    for col in df_clean.columns:
        # 只处理对象类型（字符串）的列
        if df_clean[col].dtype == 'object':
            # 对于对象类型列，可能包含字符串、混合类型或NaN
            # 使用apply逐个处理单元格
            def clean_cell(x):
                # 检查是否为NaN/None
                try:
                    if pd.isna(x):
                        return x  # 保持NaN不变
                except (ValueError, TypeError):
                    # 如果x是列表/数组，pandas.isna会报错，继续处理
                    pass

                # 处理列表、元组、字典等非标量类型
                if isinstance(x, (list, tuple)):
                    # 转换为JSON字符串
                    try:
                        s = json_module.dumps(x, ensure_ascii=False)
                    except (TypeError, ValueError):
                        # 如果JSON转换失败，使用字符串表示
                        s = str(x)
                elif isinstance(x, dict):
                    # 字典也转换为JSON字符串
                    try:
                        s = json_module.dumps(x, ensure_ascii=False)
                    except (TypeError, ValueError):
                        s = str(x)
                else:
                    # 其他类型转换为字符串
                    s = str(x)

                # 替换控制字符为空格
                s = control_chars_regex.sub(' ', s)
                return s

            df_clean[col] = df_clean[col].apply(clean_cell)

    return df_clean


def create_excel_with_all_models(all_model_data, all_results, output_path):
    """
    将所有模型数据保存到单个Excel文件（方案B）

    参数:
        all_model_data: 所有模型的数据字典
            {
                "model_slug_1": {
                    "top_apps": DataFrame,
                    "top_apps_chart": DataFrame,
                    ...
                },
                "model_slug_2": {...},
                ...
            }
        all_results: 所有模型的详细结果字典，包含每个API的详细错误信息
        output_path: 输出Excel文件路径

    返回:
        str: 生成的Excel文件路径，失败返回None
    """
    try:
        # 检查openpyxl是否可用
        try:
            import openpyxl
        except ImportError:
            print("错误: openpyxl未安装，无法创建Excel文件")
            print("请安装: pip install openpyxl")
            return None

        print(f"\n创建Excel文件: {output_path}")

        # 按API类型组织数据
        api_dataframes = {
            "top_apps": [],
            "top_apps_chart": [],
            "endpoint_stats": [],
            "author_models": [],
            "uptime_recent": [],
            "provider_preferences": [],
            "artificial_analysis_benchmarks": [],
            "design_arena_benchmarks": []
        }

        # 处理状态信息和错误日志
        model_status_rows = []
        error_log_rows = []

        # 收集所有模型的数据
        for model_slug, model_data in all_model_data.items():
            # 获取该模型的API结果
            model_result = all_results.get(model_slug, {})
            api_results = model_result.get("api_results", {})

            # 收集错误信息
            failed_apis = []
            success_apis = []
            error_messages = []
            status_codes = []
            error_types = []
            retry_counts = {}

            # 处理每个API的结果
            for api_name, api_result in api_results.items():
                if api_result.get("success", False):
                    success_apis.append(api_name)
                else:
                    failed_apis.append(api_name)
                    error_messages.append(api_result.get("error", "未知错误"))
                    status_code = api_result.get("http_status_code", "N/A")
                    status_codes.append(str(status_code))
                    error_types.append(api_result.get("error_type", "unknown"))

                    # 记录到错误日志
                    error_log_rows.append({
                        "model_slug": model_slug,
                        "api_name": api_name,
                        "error_type": api_result.get("error_type", "unknown"),
                        "error_message": api_result.get("error", "未知错误"),
                        "http_status_code": status_code,
                        "attempt": api_result.get("attempt", 1),
                        "url": api_result.get("url", ""),
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

            # 创建状态行（增强版）
            status_row = {
                "model_slug": model_slug,
                "total_apis": len(api_results),
                "success_apis": len(success_apis),
                "failed_apis": len(failed_apis),
                "has_data_apis": 0,  # 将在后面计算
                "failed_api_names": ", ".join(failed_apis) if failed_apis else "",
                "success_api_names": ", ".join(success_apis) if success_apis else "",
                "error_messages": "; ".join(error_messages[:3]) if error_messages else "",  # 只显示前3个错误
                "http_status_codes": ", ".join(status_codes) if status_codes else "",
                "error_types": ", ".join(error_types) if error_types else ""
            }

            # 计算has_data_apis（基于model_data中非空的DataFrame）
            # total_apis、success_apis、failed_apis已经基于api_results正确计算
            # 这里只计算实际有数据的API数量
            for api_type, df in model_data.items():
                if api_type in api_dataframes:  # 只处理预定义的API类型
                    if df is not None and not df.empty:
                        # 添加model_slug列并添加到对应列表中
                        df_with_slug = add_model_slug_column(df, model_slug)
                        api_dataframes[api_type].append(df_with_slug)
                        status_row["has_data_apis"] += 1

            model_status_rows.append(status_row)

        # 创建汇总DataFrame
        summary_df = pd.DataFrame(model_status_rows)

        # 创建错误日志DataFrame
        error_log_df = pd.DataFrame(error_log_rows) if error_log_rows else pd.DataFrame()
        if not error_log_df.empty:
            print(f"  错误日志: {len(error_log_df)}条错误记录")

        # 合并每个API类型的所有模型数据
        merged_dataframes = {}
        for api_type, df_list in api_dataframes.items():
            if df_list:
                # 合并所有DataFrame
                merged_df = pd.concat(df_list, ignore_index=True)
                merged_df = clean_dataframe_for_excel(merged_df)
                merged_dataframes[api_type] = merged_df
                print(f"  {api_type}: {len(df_list)}个模型，合并后{len(merged_df)}行")
            else:
                merged_dataframes[api_type] = pd.DataFrame()
                print(f"  {api_type}: 无数据")

        # 生成工作表名称映射（符合Excel工作表名称限制）
        sheet_name_mapping = {
            "top_apps": "top_apps_all_models",
            "top_apps_chart": "top_apps_chart_all_models",
            "endpoint_stats": "endpoint_stats_all_models",
            "author_models": "author_models_all_models",
            "uptime_recent": "uptime_recent_all_models",
            "provider_preferences": "provider_preferences_all_models",
            "artificial_analysis_benchmarks": "artificial_analysis_all_models",
            "design_arena_benchmarks": "design_arena_all_models"
        }

        # 使用ExcelWriter创建多工作表Excel文件
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            sheets_written = 0

            # 1. 写入汇总工作表
            if not summary_df.empty:
                summary_df_clean = clean_dataframe_for_excel(summary_df)
                summary_df_clean.to_excel(writer, sheet_name="Summary", index=False)
                sheets_written += 1
                print(f"  汇总工作表: {len(summary_df_clean)}行 x {len(summary_df_clean.columns)}列")

            # 2. 写入错误日志工作表
            if not error_log_df.empty:
                error_log_df_clean = clean_dataframe_for_excel(error_log_df)
                error_log_df_clean.to_excel(writer, sheet_name="Error_Log", index=False)
                sheets_written += 1
                print(f"  错误日志工作表: {len(error_log_df_clean)}条错误记录")

            # 3. 写入各个API类型的工作表
            for api_type, df in merged_dataframes.items():
                if df is not None and not df.empty:
                    sheet_name = sheet_name_mapping.get(api_type, api_type)
                    df_clean = clean_dataframe_for_excel(df)
                    df_clean.to_excel(writer, sheet_name=sheet_name, index=False)
                    sheets_written += 1
                    print(f"  工作表 '{sheet_name}': {len(df_clean)}行 x {len(df_clean.columns)}列")
                else:
                    sheet_name = sheet_name_mapping.get(api_type, api_type)
                    print(f"  工作表 '{sheet_name}': 无数据")

            # 检查是否至少写入了一个工作表
            if sheets_written == 0:
                raise ValueError("没有成功写入任何工作表，所有数据框都为空或无法写入")

        print(f"\n[成功] Excel文件已保存: {output_path}")

        # 显示文件信息
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"  文件大小: {file_size:.2f} KB")

        # 列出所有工作表
        wb = openpyxl.load_workbook(output_path, read_only=True)
        sheet_names = wb.sheetnames
        print(f"  包含工作表: {', '.join(sheet_names)}")

        return output_path

    except Exception as excel_err:
        print(f"[错误] 保存Excel文件时出错: {excel_err}")
        traceback.print_exc()
        return None


# ============================================================================
# 主处理函数
# ============================================================================

def process_single_model(model_slug, fetcher):
    """
    处理单个模型

    参数:
        model_slug: 模型slug
        fetcher: ModelDataFetcher实例

    返回:
        dict: 处理结果
    """
    try:
        # 异步获取所有API数据
        api_results = asyncio.run(fetcher.fetch_all_apis_for_model_async(model_slug))

        # 解析数据
        parsed_data = parse_model_data(api_results, model_slug)

        # 统计信息
        success_count = sum(1 for result in api_results.values() if result.get("success", False))
        total_count = len(api_results)

        return {
            "success": True,
            "model_slug": model_slug,
            "parsed_data": parsed_data,
            "api_results": api_results,
            "stats": {
                "total_apis": total_count,
                "success_apis": success_count,
                "failed_apis": total_count - success_count
            }
        }

    except Exception as e:
        print(f"[错误] 处理模型 {model_slug} 时出错: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "model_slug": model_slug,
            "error": str(e),
            "parsed_data": {},
            "stats": {"total_apis": 7, "success_apis": 0, "failed_apis": 7}
        }


def batch_process_models(model_slugs, config=Config(), start_index=0):
    """
    批量处理模型

    参数:
        model_slugs: 模型slug列表
        config: 配置参数
        start_index: 起始索引（用于文件名标识），默认: 0

    返回:
        dict: 批量处理结果
    """
    print("=" * 80)
    print("OpenRouter批量模型详细数据获取")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总模型数量: {len(model_slugs)}")
    if config.TEST_MODE:
        if start_index > 0:
            end_index = start_index + len(model_slugs) - 1
            print(f"测试模式: 处理模型 {start_index} 到 {end_index} (共 {len(model_slugs)} 个模型)")
        else:
            print(f"测试模式: 只处理前 {len(model_slugs)} 个模型")
    print()

    # 检查Scrapling库是否可用
    if not SCRAPLING_AVAILABLE:
        print("[错误] Scrapling库未安装或版本不支持异步，无法继续")
        return {"success": False, "error": "Scrapling库不可用"}

    # 创建数据获取器
    fetcher = ModelDataFetcher(config)

    # 处理所有模型
    all_results = {}
    all_model_data = {}

    start_time = time.time()

    for i, model_slug in enumerate(model_slugs, 1):
        print(f"\n{'='*60}")
        print(f"处理模型 {i}/{len(model_slugs)}: {model_slug}")
        print(f"{'='*60}")

        # 处理单个模型
        result = process_single_model(model_slug, fetcher)
        all_results[model_slug] = result

        if result["success"]:
            all_model_data[model_slug] = result["parsed_data"]

            # 显示统计信息
            stats = result["stats"]
            print(f"[OK] 处理成功: {stats['success_apis']}/{stats['total_apis']} 个API成功")
        else:
            print(f"[FAIL] 处理失败: {result.get('error', '未知错误')}")

        # 模型间延迟（避免请求过快）
        if i < len(model_slugs):
            print(f"等待1秒后处理下一个模型...")
            time.sleep(1)

    total_time = time.time() - start_time

    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 添加起始索引和范围信息到文件名（如果start_index > 0）
    if start_index > 0:
        end_index = start_index + len(model_slugs) - 1
        output_file = f"{config.OUTPUT_PREFIX}_{timestamp}_start{start_index}_end{end_index}.xlsx"
    else:
        output_file = f"{config.OUTPUT_PREFIX}_{timestamp}.xlsx"

    # 保存到Excel文件
    print(f"\n{'='*60}")
    print("保存所有模型数据到Excel文件...")
    excel_path = create_excel_with_all_models(all_model_data, all_results, output_file)

    # 统计信息
    total_models = len(model_slugs)
    success_models = sum(1 for r in all_results.values() if r["success"])
    failed_models = total_models - success_models

    print(f"\n{'='*60}")
    print("批量处理完成!")
    print(f"{'='*60}")
    print(f"处理统计:")
    print(f"  总模型数: {total_models}")
    print(f"  成功模型: {success_models}")
    print(f"  失败模型: {failed_models}")
    print(f"  总耗时: {total_time:.2f}秒")
    print(f"  平均每个模型: {total_time/max(total_models, 1):.2f}秒")

    if excel_path:
        print(f"\nExcel文件已生成: {excel_path}")

    return {
        "success": True,
        "total_models": total_models,
        "success_models": success_models,
        "failed_models": failed_models,
        "total_time": total_time,
        "excel_path": excel_path,
        "all_results": all_results
    }


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    try:
        # 先创建配置实例，用于命令行参数的默认值
        config = Config()

        # 解析命令行参数
        parser = argparse.ArgumentParser(description="OpenRouter批量模型详细数据获取脚本")
        parser.add_argument("--start-index", "-s", type=int, default=config.START_INDEX,
                          help=f"起始模型索引（从0开始），默认: {config.START_INDEX}")
        parser.add_argument("--limit", "-l", type=int, default=None,
                          help=f"处理模型数量限制，默认: None（使用配置文件中的TEST_LIMIT: {config.TEST_LIMIT}）")
        parser.add_argument("--test-mode", action="store_true", default=None,
                          help=f"启用测试模式（覆盖配置，当前: {config.TEST_MODE}）")
        parser.add_argument("--no-test-mode", action="store_false", dest="test_mode",
                          help="禁用测试模式（覆盖配置）")

        args = parser.parse_args()

        # 覆盖配置参数
        if args.test_mode is not None:
            config.TEST_MODE = args.test_mode

        # 确定limit值
        if args.limit is not None:
            limit = args.limit
            # 如果指定了limit，则启用测试模式
            config.TEST_MODE = True
        elif config.TEST_MODE:
            limit = config.TEST_LIMIT
        else:
            limit = None

        # 打印参数信息
        print("命令行参数:")
        print(f"  起始索引: {args.start_index}")
        print(f"  限制数量: {limit}")
        print(f"  测试模式: {config.TEST_MODE}")

        # 读取模型slug列表
        print("\n读取模型列表...")
        model_slugs = read_model_slugs_from_excel(
            file_path=config.INPUT_EXCEL,
            sheet_name=config.INPUT_SHEET,
            column_name=config.SLUG_COLUMN,
            limit=limit,
            start_index=args.start_index
        )

        if not model_slugs:
            print("错误: 未找到有效的模型slug")
            return

        # 批量处理模型
        result = batch_process_models(model_slugs, config, start_index=args.start_index)

        if result["success"]:
            print(f"\n[完成] 批量处理成功!")
        else:
            print(f"\n[错误] 批量处理失败: {result.get('error', '未知错误')}")

    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as err:
        print(f"\n[错误] 主函数异常: {err}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()