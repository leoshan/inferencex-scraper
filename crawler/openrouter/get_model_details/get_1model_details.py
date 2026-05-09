#!/usr/bin/env python
"""
OpenRouter Minimax Apps API爬虫 - 使用Scrapling库获取API数据并保存为Excel

整合了merge_api_data.py功能，使用extract.py中的解析函数处理数据

所有API端点（共7个API）：
1. top-apps-for-model (核心API)
   URL: https://openrouter.ai/api/frontend/stats/top-apps-for-model?permaslug=minimax%2Fminimax-m2.7-20260318&variant=standard
   返回：使用MiniMax M2.7模型的Top应用列表（总token排名）以及模型每日聚合用量
   解析结果：top_apps (应用排名数据), top_apps_chart (每日聚合用量数据)

2. endpoint-stats (核心API)
   URL: https://openrouter.ai/api/frontend/stats/endpoint?permaslug=minimax%2Fminimax-m2.7-20260318&variant=standard
   返回：模型端点的实时性能统计（吞吐量、延迟、请求数、状态）
   解析结果：endpoint_stats (端点性能统计数据)

3. author-models (核心API)
   URL: https://openrouter.ai/api/frontend/author-models?authorSlug=minimax
   返回：指定作者（MiniMax）的所有模型元数据（名称、描述、端点、定价等）
   解析结果：author_models (作者模型列表)


4. uptime统计
   URL: https://openrouter.ai/api/frontend/stats/uptime-recent?permaslug=minimax%2Fminimax-m2.7-20260318
   返回：模型最近一段时间的uptime统计数据
   解析结果：uptime_recent (uptime统计数据)

5. 提供商偏好
   URL: https://openrouter.ai/api/internal/v1/provider-preferences
   返回：用户或默认的提供商偏好设置
   解析结果：provider_preferences (提供商偏好设置)

6. Artificial Analysis基准
   URL: https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks?slug=minimax%2Fminimax-m2.7-20260318
   返回：模型在Artificial Analysis上的基准评分
   解析结果：artificial_analysis_benchmarks (Artificial Analysis基准评分)

7. Design Arena基准
   URL: https://openrouter.ai/api/internal/v1/design-arena-benchmarks?slug=minimax%2Fminimax-m2.7-20260318
   返回：模型在Design Arena上的基准评分
   解析结果：design_arena_benchmarks (Design Arena基准评分)

8. Benchmarks页面 (DOM抓取)
   URL: https://openrouter.ai/{model_slug}/benchmarks
   返回：Design Arena详细benchmark数据（Category Performance, Models Arena, Agents Arena, Ranking Distribution）
   解析结果：benchmarks_category_performance, benchmarks_models_arena, benchmarks_agents_arena, benchmarks_ranking_distribution

本脚本自动获取上述所有API数据，使用extract.py中的解析函数处理后，
生成包含多个工作表的Excel文件。
"""

import sys
import os
import json
import time
import glob
import tempfile
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse

# 导入Scrapling库
try:
    from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    print("错误: Scrapling库未安装")
    print("请安装: pip install scrapling[fetchers]")
    print("然后运行: scrapling install")
    # 在except块中定义变量以避免NameError
    Fetcher = None
    StealthyFetcher = None
    DynamicFetcher = None
    sys.exit(1)

# 解析函数将直接定义在本文件中
EXTRACT_AVAILABLE = True

# 配置参数
SAVE_RAW_RESPONSE = False  # 是否保存原始API响应文件
SAVE_BENCHMARKS_HTML = False  # 是否保存benchmarks页面的HTML（用于调试）


def fetch_api_data(url, description="API数据"):
    """
    使用Scrapling获取API数据

    参数:
        url: API端点URL
        description: 描述信息

    返回:
        dict: 包含success, data, error等信息
    """
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始获取{description}: {url}")

        # 默认请求头
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Accept-Encoding': 'gzip, deflate',  # 移除br避免Brotli压缩问题
            'Referer': 'https://openrouter.ai/minimax/minimax-m2.7/apps',
            'Origin': 'https://openrouter.ai',
        }

        print(f"  请求头: {default_headers}")
        start_time = time.time()

        # 直接使用StealthyFetcher - 更可靠
        print(f"  使用StealthyFetcher进行API请求...")
        try:
            page = StealthyFetcher.fetch(url, headers=default_headers, headless=True, network_idle=True)
            print(f"  使用StealthyFetcher成功")
        except Exception as fetcher_err:
            print(f"  StealthyFetcher失败: {fetcher_err}")
            print(f"  回退到Fetcher...")
            # 使用Fetcher
            page = Fetcher.get(url, headers=default_headers)
            print(f"  使用Fetcher成功")

        elapsed_time = time.time() - start_time

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Scrapling请求完成，耗时: {elapsed_time:.2f}秒")

        # 调试信息：打印page对象类型和属性
        print(f"  page对象类型: {type(page)}")

        # 打印一些重要属性
        important_attrs = ['body', 'text', 'json', 'content', 'response', 'status_code', 'status', 'code']
        for attr in important_attrs:
            if hasattr(page, attr):
                attr_value = getattr(page, attr)
                print(f"  {attr}: {type(attr_value)}")
                if not callable(attr_value):
                    if attr_value:
                        if isinstance(attr_value, bytes):
                            print(f"    bytes长度: {len(attr_value):,}")
                        else:
                            print(f"    值预览: {str(attr_value)[:100]}...")
                    else:
                        print(f"    值: {attr_value}")

        # 获取响应内容
        raw_text = None
        parsed_data = None

        # 方法1: 尝试直接使用json()方法
        if hasattr(page, 'json') and callable(page.json):
            try:
                parsed_data = page.json()
                print(f"  [方法1] 使用page.json()成功解析JSON数据")
                raw_text = json.dumps(parsed_data, ensure_ascii=False, indent=2)
                print(f"    JSON转换为字符串，大小: {len(raw_text):,} 字符")
            except Exception as json_err:
                print(f"  [方法1] page.json()失败: {json_err}")

        # 方法2: 如果json()失败，尝试body属性
        if not raw_text and hasattr(page, 'body'):
            body_value = page.body
            if body_value:
                print(f"  [方法2] 使用page.body，类型: {type(body_value)}，大小: {len(body_value):,} 字节")
                try:
                    # 如果是bytes，尝试解码
                    if isinstance(body_value, bytes):
                        try:
                            raw_text = body_value.decode('utf-8')
                            print(f"    成功解码为UTF-8字符串")
                        except UnicodeDecodeError:
                            try:
                                raw_text = body_value.decode('latin-1')
                                print(f"    使用latin-1解码")
                            except UnicodeDecodeError:
                                raw_text = str(body_value)
                                print(f"    无法解码，转换为字符串")
                    else:
                        raw_text = str(body_value)

                    # 尝试解析JSON
                    if parsed_data is None:
                        try:
                            parsed_data = json.loads(raw_text)
                            print(f"    成功解析JSON数据")
                        except json.JSONDecodeError as json_err:
                            print(f"    无法解析JSON: {json_err}")
                except Exception as body_err:
                    print(f"  [方法2] 处理page.body时出错: {body_err}")

        # 方法3: 如果上述方法都失败，尝试text属性（可能是TextHandler）
        if not raw_text and hasattr(page, 'text'):
            text_value = page.text
            print(f"  [方法3] 使用page.text，类型: {type(text_value)}")

            # 检查是否是TextHandler对象
            if hasattr(text_value, '__class__') and 'TextHandler' in text_value.__class__.__name__:
                print(f"    text是TextHandler对象")
                # 尝试get()方法
                if hasattr(text_value, 'get') and callable(text_value.get):
                    try:
                        text_result = text_value.get()
                        print(f"    使用get()获取文本，类型: {type(text_result)}")
                        if text_result:
                            raw_text = str(text_result)
                            print(f"      获取到文本，大小: {len(raw_text):,} 字符")
                    except Exception as get_err:
                        print(f"    get()方法失败: {get_err}")

                # 如果get()失败，尝试getall()
                if not raw_text and hasattr(text_value, 'getall') and callable(text_value.getall):
                    try:
                        text_result = text_value.getall()
                        print(f"    使用getall()获取文本，类型: {type(text_result)}")
                        if text_result:
                            raw_text = str(text_result)
                            print(f"      获取到文本，大小: {len(raw_text):,} 字符")
                    except Exception as getall_err:
                        print(f"    getall()方法失败: {getall_err}")
            else:
                # 不是TextHandler，直接使用
                if text_value:
                    raw_text = str(text_value)
                    print(f"    直接使用text值，大小: {len(raw_text):,} 字符")

        # 方法4: 最后尝试，使用str(page)
        if not raw_text:
            raw_text = str(page)
            print(f"  [方法4] 使用str(page)获取内容")

        if not raw_text:
            raw_text = ""
            print("  [警告] 未能获取到响应内容")
        else:
            print(f"  [最终] 响应大小: {len(raw_text):,} 字符")
            if len(raw_text) < 500:
                print(f"  响应内容预览: {raw_text[:500]}")

        # 根据配置保存原始响应
        if SAVE_RAW_RESPONSE:
            save_raw_response(raw_text, url)

        # 返回结果
        if parsed_data is not None:
            return {
                "success": True,
                "data": parsed_data,
                "raw_text": raw_text,
                "elapsed_time": elapsed_time,
                "error": None
            }
        elif raw_text:
            # 有原始文本但没有解析的数据
            # 尝试最后解析JSON（可能在之前的步骤中未尝试）
            try:
                parsed_data = json.loads(raw_text)
                print(f"  成功解析JSON数据")
                return {
                    "success": True,
                    "data": parsed_data,
                    "raw_text": raw_text,
                    "elapsed_time": elapsed_time,
                    "error": None
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "data": raw_text,
                    "raw_text": raw_text,
                    "elapsed_time": elapsed_time,
                    "error": "响应不是JSON格式或无法解析"
                }
        else:
            return {
                "success": False,
                "data": None,
                "raw_text": "",
                "elapsed_time": elapsed_time,
                "error": "未能获取到响应内容"
            }

    except Exception as fetch_err:
        error_msg = f"Scrapling API请求错误: {fetch_err}"
        print(f"[ERROR] {error_msg}")
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "data": None,
            "error": error_msg
        }


def extract_model_name_from_url(url):
    """
    从URL中提取模型名称

    参数:
        url: API端点URL

    返回:
        str: 提取的模型名称，如果无法提取则返回"unknown_model"
    """
    from urllib.parse import urlparse, parse_qs

    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # 尝试从permaslug参数提取
    if 'permaslug' in query_params:
        permaslug = query_params['permaslug'][0]
        # 解码URL编码
        import urllib.parse
        permaslug = urllib.parse.unquote(permaslug)
        # 提取模型名称部分（可能包含作者/模型）
        # 例如: "minimax/minimax-m2.7-20260318" -> 取"minimax-m2.7"
        # 或者直接使用整个permaslug但移除日期后缀
        model_name = permaslug.split('/')[-1]  # 获取最后一部分
        # 移除可能的日期后缀，如"-20260318"
        import re
        model_name = re.sub(r'-\d{8}$', '', model_name)
        return model_name

    # 尝试从slug参数提取
    if 'slug' in query_params:
        slug = query_params['slug'][0]
        # 解码URL编码
        import urllib.parse
        slug = urllib.parse.unquote(slug)
        # 提取模型名称部分
        model_name = slug.split('/')[-1]  # 获取最后一部分
        # 移除可能的日期后缀
        import re
        model_name = re.sub(r'-\d{8}$', '', model_name)
        return model_name

    # 尝试从authorSlug参数提取
    if 'authorSlug' in query_params:
        author_slug = query_params['authorSlug'][0]
        return author_slug

    # 无法提取模型名称
    return "unknown_model"


def save_raw_response(raw_text, url, filename=None):
    """
    保存原始API响应到文件

    参数:
        raw_text: 原始响应文本
        url: 请求的URL（用于生成文件名）
        filename: 保存的文件名，如果为None则自动生成
    """
    if filename is None:
        # 从URL生成安全文件名
        import re
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/').replace('/', '_')
        query = parsed_url.query
        if query:
            # 简化查询参数
            query_simple = re.sub(r'[&=]', '_', query)[:50]
            path = f"{path}_{query_simple}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 去除"raw_response_api_frontend_"前缀，只保留path部分
        filename = f"{path}_{timestamp}.txt"

    # 创建模型名称文件夹
    model_name = extract_model_name_from_url(url)
    model_dir = model_name

    # 确保模型目录存在
    os.makedirs(model_dir, exist_ok=True)

    # 将文件保存到模型目录下
    filename = os.path.join(model_dir, os.path.basename(filename))

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(raw_text)

        print(f"[OK] 已保存原始响应到: {filename}")
        print(f"     文件大小: {len(raw_text):,} 字符")
        return filename
    except Exception as save_err:
        print(f"[ERROR] 保存原始响应时出错: {save_err}")
        return None


def find_latest_files(model_name=None):
    """
    查找最新的原始API响应文件

    参数:
        model_name: 模型名称（文件夹名），如果为None则自动检测

    返回:
        dict: 包含所有API文件路径的字典
    """
    # 如果未提供模型名称，尝试从当前目录的子目录中自动检测
    if model_name is None:
        # 查找所有子目录
        import glob
        subdirs = [d for d in glob.glob("*") if os.path.isdir(d) and not d.startswith(".")]
        if subdirs:
            # 假设第一个子目录是模型目录
            model_name = subdirs[0]
            print(f"[INFO] 自动检测到模型目录: {model_name}")
        else:
            model_name = "unknown_model"
            print(f"[WARN] 未找到模型目录，使用默认: {model_name}")

    # 文件模式 - 对应所有API端点（已去除raw_response_前缀）
    patterns = {
        "top_apps": "api_frontend_stats_top-apps-for-model_*.txt",
        "endpoint_stats": "api_frontend_stats_endpoint_*.txt",
        "author_models": "api_frontend_author-models_*.txt",
        "uptime_recent": "api_frontend_stats_uptime-recent_*.txt",
        "provider_preferences": "api_internal_v1_provider-preferences_*.txt",
        "artificial_analysis_benchmarks": "api_internal_v1_artificial-analysis-benchmarks_*.txt",
        "design_arena_benchmarks": "api_internal_v1_design-arena-benchmarks_*.txt"
    }

    files = {}

    for key, pattern in patterns.items():
        # 在模型目录下查找匹配的文件
        search_pattern = os.path.join(model_name, pattern)
        import glob
        matches = glob.glob(search_pattern)

        if not matches:
            # 如果未找到，尝试在当前目录查找（向后兼容）
            matches = glob.glob(pattern)
            if not matches:
                print(f"[WARN] 未找到{key}的原始响应文件")
                print(f"  搜索模式: {search_pattern}")
                continue

        # 按修改时间排序，获取最新的文件
        matches.sort(key=os.path.getmtime, reverse=True)
        latest_file = matches[0]
        files[key] = latest_file

        print(f"[INFO] 找到{key}文件: {os.path.basename(latest_file)}")
        print(f"  路径: {latest_file}")

    return files


def clean_dataframe_for_excel(df):
    """
    清理DataFrame中的非法字符，使其兼容openpyxl/Excel

    参数:
        df: pandas DataFrame

    返回:
        清理后的DataFrame
    """
    import re
    import json
    import pandas

    # 创建副本，避免修改原始数据
    df_clean = df.copy()

    # 定义要移除或替换的非法字符模式
    # 移除所有ASCII控制字符 (0x00-0x1F) 和 Unicode控制字符 (U+007F-U+009F)
    # 包括换行符(\n, 0x0A)、回车符(\r, 0x0D)、制表符(\t, 0x09)等
    # openpyxl 不允许这些字符出现在单元格中
    control_chars_regex = re.compile(r'[\x00-\x1f\x7f-\x9f]')

    # 对每个列进行清理
    for col in df_clean.columns:
        # 只处理对象类型（字符串）的列
        if df_clean[col].dtype == 'object':
            # 对于对象类型列，可能包含字符串、混合类型或NaN
            # 使用apply逐个处理单元格
            def clean_cell(x):
                # 检查是否为NaN/None
                try:
                    if pandas.isna(x):
                        return x  # 保持NaN不变
                except (ValueError, TypeError):
                    # 如果x是列表/数组，pandas.isna会报错，继续处理
                    pass

                # 处理列表、元组、字典等非标量类型
                if isinstance(x, (list, tuple)):
                    # 转换为JSON字符串
                    try:
                        s = json.dumps(x, ensure_ascii=False)
                    except (TypeError, ValueError):
                        # 如果JSON转换失败，使用字符串表示
                        s = str(x)
                elif isinstance(x, dict):
                    # 字典也转换为JSON字符串
                    try:
                        s = json.dumps(x, ensure_ascii=False)
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


def create_excel_with_sheets(dataframes_dict, output_path, api_info_df=None):
    """
    将多个DataFrame保存到Excel文件的不同工作表，可选的API信息工作表作为首页

    Parameters
    ----------
    dataframes_dict : dict
        字典，键为工作表名，值为DataFrame
    output_path : str
        输出的Excel文件路径
    api_info_df : pandas.DataFrame, optional
        API信息DataFrame，包含调用的API接口信息，将作为第一个工作表
    """
    # 检查openpyxl是否可用
    try:
        import openpyxl
        # 检查openpyxl版本，确保兼容性
        openpyxl_version = openpyxl.__version__
        print(f"[INFO] 使用openpyxl版本: {openpyxl_version}")
    except ImportError:
        print("[ERROR] openpyxl未安装，无法创建Excel文件")
        print("请安装: pip install openpyxl")
        return None

    try:
        # 使用ExcelWriter创建多工作表Excel文件
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            sheets_written = 0

            # 1. 首先写入API信息工作表（如果提供）
            if api_info_df is not None and not api_info_df.empty:
                try:
                    # 清理API信息DataFrame中的非法字符
                    api_info_df_clean = clean_dataframe_for_excel(api_info_df)
                    # 将API信息DataFrame写入工作表，作为第一个工作表
                    api_info_df_clean.to_excel(writer, sheet_name="API接口", index=False)
                    sheets_written += 1
                    print(f"  API信息工作表: {len(api_info_df_clean)} 行 x {len(api_info_df_clean.columns)} 列")
                    print(f"  包含API接口信息: {', '.join(api_info_df_clean.columns.tolist())}")
                except Exception as api_err:
                    print(f"  警告: 写入API信息工作表时出错: {api_err}")
                    print(f"  尝试使用原始API信息DataFrame")
                    try:
                        api_info_df.to_excel(writer, sheet_name="API接口", index=False)
                        sheets_written += 1
                        print(f"  API信息工作表: {len(api_info_df)} 行 x {len(api_info_df.columns)} 列")
                    except Exception as api_write_err:
                        print(f"  错误: 无法写入API信息工作表: {api_write_err}")
                        # 继续处理其他工作表
                print()

            # 2. 写入其他数据工作表
            for sheet_name, df in dataframes_dict.items():
                if df is not None and not df.empty:
                    try:
                        # 清理DataFrame中的非法字符
                        df_clean = clean_dataframe_for_excel(df)
                        # 将DataFrame写入工作表
                        df_clean.to_excel(writer, sheet_name=sheet_name, index=False)
                        sheets_written += 1
                        print(f"  工作表 '{sheet_name}': {len(df_clean)} 行 x {len(df_clean.columns)} 列")
                    except Exception as clean_err:
                        print(f"  警告: 清理工作表 '{sheet_name}' 时出错: {clean_err}")
                        print(f"  尝试使用原始DataFrame（可能包含非法字符）")
                        try:
                            # 尝试直接写入，可能失败
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            sheets_written += 1
                            print(f"  工作表 '{sheet_name}': {len(df)} 行 x {len(df.columns)} 列")
                        except Exception as write_err:
                            print(f"  错误: 无法写入工作表 '{sheet_name}': {write_err}")
                            # 跳过此工作表
                else:
                    print(f"  工作表 '{sheet_name}': 无数据")

            # 检查是否至少写入了一个工作表
            if sheets_written == 0:
                raise ValueError("没有成功写入任何工作表，所有数据框都为空或无法写入")

        print(f"\n[SUCCESS] Excel文件已保存: {output_path}")

        # 显示文件信息
        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"  文件大小: {file_size:.2f} KB")

        # 列出所有工作表
        wb = openpyxl.load_workbook(output_path, read_only=True)
        sheet_names = wb.sheetnames
        print(f"  包含工作表: {', '.join(sheet_names)}")

    except Exception as excel_err:
        print(f"[ERROR] 保存Excel文件时出错: {excel_err}")
        import traceback
        traceback.print_exc()
        return None

    return output_path


def main():
    print("=" * 80)
    print("OpenRouter Minimax Apps API爬虫 - 使用Scrapling获取数据并生成Excel文件")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 检查Scrapling库是否可用
    if not SCRAPLING_AVAILABLE:
        print("[ERROR] Scrapling库未安装，无法继续")
        sys.exit(1)

    # 检查extract.py解析函数是否可用
    if not EXTRACT_AVAILABLE:
        print("[ERROR] extract.py中的解析函数不可用，无法继续")
        sys.exit(1)

    # 1. 定义要获取的所有API端点（共7个API）
    api_endpoints = {
        "top_apps": "https://openrouter.ai/api/frontend/stats/top-apps-for-model?permaslug=minimax%2Fminimax-m2.7-20260318&variant=standard",
        "endpoint_stats": "https://openrouter.ai/api/frontend/stats/endpoint?permaslug=minimax%2Fminimax-m2.7-20260318&variant=standard",
        "author_models": "https://openrouter.ai/api/frontend/author-models?authorSlug=minimax",
        "uptime_recent": "https://openrouter.ai/api/frontend/stats/uptime-recent?permaslug=minimax%2Fminimax-m2.7-20260318",
        "provider_preferences": "https://openrouter.ai/api/internal/v1/provider-preferences",
        "artificial_analysis_benchmarks": "https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks?slug=minimax%2Fminimax-m2.7-20260318",
        "design_arena_benchmarks": "https://openrouter.ai/api/internal/v1/design-arena-benchmarks?slug=minimax%2Fminimax-m2.7-20260318"
    }

    # 从第一个API端点提取模型名称
    model_name = None
    for api_url in api_endpoints.values():
        model_name = extract_model_name_from_url(api_url)
        if model_name != "unknown_model":
            break

    if model_name == "unknown_model":
        model_name = "minimax-m2.7"  # 默认值

    print(f"[INFO] 目标模型: {model_name}")
    print()

    print("步骤1: 获取所有API数据并保存原始响应文件")
    print("-" * 40)

    # 获取所有API数据
    api_results = {}
    for api_name, api_url in api_endpoints.items():
        description = f"{api_name} API"
        print(f"\n获取{description}...")
        result = fetch_api_data(api_url, description)

        if result["success"]:
            print(f"  [OK] {description}获取成功")
            api_results[api_name] = result
        else:
            print(f"  [FAIL] {description}获取失败: {result.get('error', '未知错误')}")
            # 如果核心API失败，继续执行但会跳过后续解析

    print(f"\nAPI数据获取完成: {len([r for r in api_results.values() if r['success']])}个成功, {len([r for r in api_results.values() if not r['success']])}个失败")
    print()

    # 2. 查找或创建原始响应数据
    print("步骤2: 处理原始响应数据")
    print("-" * 40)

    files = {}
    temp_files_to_cleanup = []

    if SAVE_RAW_RESPONSE:
        # 模式1: 从保存的文件中查找
        files = find_latest_files(model_name)
        if not files:
            print("错误: 未找到任何原始响应文件")
            sys.exit(1)
    else:
        # 模式2: 从api_results创建临时文件
        print("使用API结果创建临时文件...")
        for api_name, result in api_results.items():
            if result["success"]:
                try:
                    # 创建临时文件
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', encoding='utf-8', delete=False) as temp_file:
                        json.dump(result["data"], temp_file, ensure_ascii=False, indent=2)
                        temp_file_path = temp_file.name
                        files[api_name] = temp_file_path
                        temp_files_to_cleanup.append(temp_file_path)
                        print(f"  创建临时文件: {api_name}")
                except Exception as e:
                    print(f"  警告: 无法为{api_name}创建临时文件: {e}")
            else:
                print(f"  跳过失败的API: {api_name}")

    if not files:
        print("错误: 没有可用的响应数据")
        sys.exit(1)

    # 检查是否找到所有必需的文件（核心API）
    required_files = ["top_apps", "endpoint_stats", "author_models"]
    missing_files = [f for f in required_files if f not in files]

    if missing_files:
        print(f"警告: 缺少核心API文件: {missing_files}")
        print(f"找到的文件: {list(files.keys())}")
        # 如果缺少核心API文件，继续尝试解析可用的文件

    print(f"处理 {len(files)} 个响应数据文件")
    print()

    # 3. 使用extract.py中的解析函数解析所有文件
    print("步骤3: 解析所有原始响应文件")
    print("-" * 40)

    dataframes = {}

    # 定义API名称到解析函数的映射
    parse_functions = {
        "top_apps": lambda f: parse_top_apps_json(f),  # 返回两个DataFrame
        "author_models": parse_author_models,
        "endpoint_stats": parse_endpoint_stats,
        "uptime_recent": parse_uptime_recent,
        "provider_preferences": parse_provider_preferences,
        "artificial_analysis_benchmarks": parse_artificial_analysis_benchmark,
        "design_arena_benchmarks": parse_design_arena_benchmark
    }

    # 解析所有文件
    for api_name, file_path in files.items():
        if api_name in parse_functions:
            try:
                print(f"\n解析文件: {os.path.basename(file_path)}")

                if api_name == "top_apps":
                    # top_apps API返回两个DataFrame
                    df_apps, df_chart = parse_functions[api_name](file_path)
                    dataframes['top_apps'] = df_apps
                    dataframes['top_apps_chart'] = df_chart
                    print(f"  top_apps: {len(df_apps)} 行, {len(df_apps.columns)} 列")
                    print(f"  top_apps_chart: {len(df_chart)} 行, {len(df_chart.columns)} 列")
                else:
                    # 其他API返回一个DataFrame
                    df = parse_functions[api_name](file_path)
                    dataframes[api_name] = df
                    print(f"  {api_name}: {len(df)} 行, {len(df.columns)} 列")

            except Exception as parse_err:
                print(f"  解析{api_name}文件时出错: {parse_err}")
                import traceback
                traceback.print_exc()
        else:
            print(f"警告: 未找到{api_name}的解析函数，跳过解析")

    # 清理临时文件（如果使用临时文件模式）
    if not SAVE_RAW_RESPONSE and temp_files_to_cleanup:
        print("\n清理临时文件...")
        for temp_file_path in temp_files_to_cleanup:
            if os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    print(f"  已删除: {os.path.basename(temp_file_path)}")
                except Exception as e:
                    print(f"  警告: 无法删除临时文件 {temp_file_path}: {e}")

    # 检查是否有可用的数据
    if not dataframes:
        print("\n[ERROR] 没有成功解析任何数据")
        sys.exit(1)

    print()

    # 4. 创建Excel文件
    print("\n步骤4: 创建包含多个工作表的Excel文件")
    print("-" * 40)

    # 4.1 先抓取 Benchmarks 页面（在创建 Excel 之前）
    print("\n步骤4.1: 抓取 Benchmarks 页面 (DOM)")
    print("-" * 40)

    # 从 API 端点提取 model_slug
    model_slug = None
    for api_url in api_endpoints.values():
        if 'permaslug=' in api_url or 'slug=' in api_url:
            # 提取 slug 参数
            import urllib.parse
            parsed = urllib.parse.urlparse(api_url)
            params = urllib.parse.parse_qs(parsed.query)
            if 'permaslug' in params:
                model_slug = params['permaslug'][0]
            elif 'slug' in params:
                model_slug = params['slug'][0]
            if model_slug:
                break

    if model_slug:
        print(f"目标模型: {model_slug}")
        benchmarks_result = fetch_benchmarks_page(model_slug)

        if benchmarks_result["success"]:
            benchmarks_data = benchmarks_result["data"]
            benchmarks_dfs = parse_benchmarks_to_dataframes(benchmarks_data)

            # 添加到 dataframes
            dataframes.update(benchmarks_dfs)
            print(f"  Benchmarks 数据获取成功，共 {len(benchmarks_dfs)} 个工作表")
        else:
            print(f"  Benchmarks 数据获取失败: {benchmarks_result.get('error', '未知错误')}")
    else:
        print("  警告: 无法从API端点提取模型标识，跳过 Benchmarks 页面抓取")

    # 4.2 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_excel = f"openrouter_api_data_{timestamp}.xlsx"

    print(f"\n输出文件: {output_excel}")
    print("工作表:")

    # 创建API信息DataFrame（作为Excel文件的首页）
    print("\n创建API接口信息工作表...")

    # API描述映射（从文档注释中提取）
    api_descriptions = {
        "top_apps": "返回使用该模型的Top应用列表（总token排名）以及模型每日聚合用量",
        "endpoint_stats": "返回模型端点的实时性能统计（吞吐量、延迟、请求数、状态）",
        "author_models": "返回指定作者（MiniMax）的所有模型元数据（名称、描述、端点、定价等）",
        "uptime_recent": "返回模型最近一段时间的uptime统计数据",
        "provider_preferences": "返回用户或默认的提供商偏好设置",
        "artificial_analysis_benchmarks": "返回模型在Artificial Analysis上的基准评分",
        "design_arena_benchmarks": "返回模型在Design Arena上的基准评分"
    }

    # 解析函数映射
    parse_function_names = {
        "top_apps": "parse_top_apps_json",
        "endpoint_stats": "parse_endpoint_stats",
        "author_models": "parse_author_models",
        "uptime_recent": "parse_uptime_recent",
        "provider_preferences": "parse_provider_preferences",
        "artificial_analysis_benchmarks": "parse_artificial_analysis_benchmark",
        "design_arena_benchmarks": "parse_design_arena_benchmark"
    }

    # 构建API信息列表
    api_info_rows = []

    for api_name, api_url in api_endpoints.items():
        # 获取API获取状态
        api_fetch_success = api_results.get(api_name, {}).get("success", False) if api_name in api_results else False
        fetch_status = "成功" if api_fetch_success else "失败"

        # 获取解析结果
        parse_status = "未解析"
        rows_count = 0
        cols_count = 0
        sheet_names = []

        # 检查是否有对应的DataFrame
        if api_name in dataframes:
            df = dataframes[api_name]
            if df is not None and not df.empty:
                parse_status = "成功"
                rows_count = len(df)
                cols_count = len(df.columns)
                sheet_names = [api_name]
            else:
                parse_status = "无数据"
        elif api_name == "top_apps" and "top_apps" in dataframes and "top_apps_chart" in dataframes:
            # top_apps特殊处理：生成两个工作表
            df_apps = dataframes.get("top_apps")
            df_chart = dataframes.get("top_apps_chart")
            parse_status = "成功"
            rows_count = (len(df_apps) if df_apps is not None else 0) + (len(df_chart) if df_chart is not None else 0)
            cols_count = max(len(df_apps.columns) if df_apps is not None else 0,
                            len(df_chart.columns) if df_chart is not None else 0)
            sheet_names = ["top_apps", "top_apps_chart"]

        # 获取描述
        description = api_descriptions.get(api_name, "无描述")

        # 获取解析函数名
        parse_function = parse_function_names.get(api_name, "未知")

        api_info_rows.append({
            "API名称": api_name,
            "API URL": api_url,
            "描述": description,
            "获取状态": fetch_status,
            "解析状态": parse_status,
            "解析函数": parse_function,
            "数据行数": rows_count,
            "数据列数": cols_count,
            "生成的工作表": ", ".join(sheet_names) if sheet_names else "无"
        })

    # 创建API信息DataFrame
    api_info_df = pd.DataFrame(api_info_rows)

    print(f"API接口信息: {len(api_info_df)} 个API")
    for _, row in api_info_df.iterrows():
        print(f"  {row['API名称']}: 获取{row['获取状态']}, 解析{row['解析状态']}, 工作表: {row['生成的工作表']}")

    # 添加 Benchmarks 数据到 API 信息
    for sheet_name in dataframes.keys():
        if sheet_name.startswith("benchmarks_"):
            df = dataframes[sheet_name]
            api_info_rows.append({
                "API名称": sheet_name,
                "API URL": f"https://openrouter.ai/{model_slug}/benchmarks" if model_slug else "",
                "描述": f"Design Arena {sheet_name.replace('benchmarks_', '').replace('_', ' ').title()}",
                "获取状态": "成功",
                "解析状态": "成功",
                "解析函数": "DOM抓取",
                "数据行数": len(df),
                "数据列数": len(df.columns),
                "生成的工作表": sheet_name
            })

    # 更新 API 信息 DataFrame
    api_info_df = pd.DataFrame(api_info_rows)

    # 创建Excel文件（包含API信息工作表）
    excel_path = create_excel_with_sheets(dataframes, output_excel, api_info_df)

    if not excel_path:
        print("[ERROR] 创建Excel文件失败")
        sys.exit(1)

    # 5. 显示数据摘要
    print("\n步骤5: 数据摘要")
    print("-" * 40)

    for sheet_name, df in dataframes.items():
        if df is not None and not df.empty:
            print(f"工作表 '{sheet_name}':")
            print(f"  行数: {len(df):,}")
            print(f"  列数: {len(df.columns)}")

            # 显示前几列名称
            col_preview = list(df.columns)[:5]
            if len(df.columns) > 5:
                col_preview.append("...")
            print(f"  列名预览: {col_preview}")

            # 显示数据预览
            if len(df) > 0:
                print(f"  第一行预览:")
                first_row = df.iloc[0]
                for i, (col, val) in enumerate(zip(df.columns[:3], first_row[:3])):
                    val_preview = str(val)[:50] + "..." if len(str(val)) > 50 else str(val)
                    print(f"    {col}: {val_preview}")
            print()

    print("=" * 80)
    print(f"完成! Excel文件已保存: {excel_path}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


# ============================================================================
# API解析函数（从extract.py移动过来）
# ============================================================================

# 返回使用该模型的 Top 应用列表（总 token 排名）以及模型每日聚合用量
def parse_top_apps_json(file_path: str):
    """
    解析 OpenRouter API 返回的 top-apps-for-model JSON 文件

    Parameters
    ----------
    file_path : str
        JSON 文件路径

    Returns
    -------
    df_apps : pd.DataFrame
        top_apps 表，包含 App 排名、总用量、请求数、标题、描述等信息
    df_chart : pd.DataFrame
        top_apps_chart 表，包含模型每日聚合用量（总 token、请求数、缓存命中、工具调用等）
    """

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    data = raw.get('data', {})

    # ---------- 1. 处理 top_apps ----------
    apps_raw = data.get('top_apps', [])
    apps_rows = []
    for item in apps_raw:
        # 提取 app 嵌套对象
        app_info = item.pop('app', {})
        # 将 app 内部字段平铺，加前缀 'app_' 避免与顶层字段冲突
        flat_item = {
            **item,
            'app_id': app_info.get('id'),
            'app_title': app_info.get('title'),
            'app_description': app_info.get('description'),
            'app_slug': app_info.get('slug'),
            'app_origin_url': app_info.get('origin_url'),
            'app_categories': app_info.get('categories'),
            'app_favicon_url': app_info.get('favicon_url'),
            'app_main_url': app_info.get('main_url'),
            'app_source_code_url': app_info.get('source_code_url'),
            'app_icon_class_name': app_info.get('icon_class_name'),
            'app_created_at': app_info.get('created_at'),
            'app_related_apps': app_info.get('related_apps')
        }
        # 数值转换
        if 'total_tokens' in flat_item:
            try:
                flat_item['total_tokens'] = int(flat_item['total_tokens'])
            except (ValueError, TypeError):
                pass
        if 'total_requests' in flat_item:
            try:
                flat_item['total_requests'] = int(flat_item['total_requests'])
            except (ValueError, TypeError):
                pass
        apps_rows.append(flat_item)

    df_apps = pd.DataFrame(apps_rows)

    # ---------- 2. 处理 top_apps_chart ----------
    chart_raw = data.get('top_apps_chart', [])
    df_chart = pd.DataFrame(chart_raw)

    # 转换数值列
    numeric_cols = [
        'total_completion_tokens', 'total_prompt_tokens', 'total_native_tokens_reasoning',
        'count', 'num_media_prompt', 'num_media_completion', 'num_audio_prompt',
        'total_native_tokens_cached', 'total_tool_calls', 'requests_with_tool_call_errors'
    ]
    for col in numeric_cols:
        if col in df_chart.columns:
            try:
                df_chart[col] = pd.to_numeric(df_chart[col], errors='coerce')
            except Exception:
                pass

    return df_apps, df_chart


# 返回指定作者（MiniMax）的所有模型元数据（名称、描述、端点、定价等）
def parse_author_models(file_path: str):
    """
    解析 OpenRouter API 返回的 author-models JSON 文件

    返回一个扁平化的模型列表 DataFrame，包含模型基本信息、端点配置、定价等。
    """

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    models = raw.get('data', {}).get('models', [])
    rows = []

    for model in models:
        # 提取 endpoint 嵌套对象（每个 model 下有一个 endpoint）
        endpoint = model.pop('endpoint', {})

        # 将 endpoint 内部的定价、provider_info 等进一步展开
        pricing = endpoint.pop('pricing', {})
        display_pricing = endpoint.pop('display_pricing', [])
        pricing_json = endpoint.pop('pricing_json', {})
        provider_info = endpoint.pop('provider_info', {})
        data_policy = endpoint.pop('data_policy', {})
        features = endpoint.pop('features', {})

        # 扁平化 model 主表字段（加上前缀避免冲突，可选）
        flat_model = {
            **model,
            'endpoint_id': endpoint.get('id'),
            'endpoint_name': endpoint.get('name'),
            'endpoint_context_length': endpoint.get('context_length'),
            'endpoint_adapter_name': endpoint.get('adapter_name'),
            'endpoint_provider_name': endpoint.get('provider_name'),
            'endpoint_provider_display_name': endpoint.get('provider_display_name'),
            'endpoint_provider_slug': endpoint.get('provider_slug'),
            'endpoint_provider_model_id': endpoint.get('provider_model_id'),
            'endpoint_quantization': endpoint.get('quantization'),
            'endpoint_variant': endpoint.get('variant'),
            'endpoint_is_free': endpoint.get('is_free'),
            'endpoint_can_abort': endpoint.get('can_abort'),
            'endpoint_max_completion_tokens': endpoint.get('max_completion_tokens'),
            'endpoint_supported_parameters': endpoint.get('supported_parameters'),
            'endpoint_is_byok': endpoint.get('is_byok'),
            'endpoint_moderation_required': endpoint.get('moderation_required'),
            'endpoint_limit_rpm': endpoint.get('limit_rpm'),
            'endpoint_limit_rpd': endpoint.get('limit_rpd'),
            'endpoint_has_completions': endpoint.get('has_completions'),
            'endpoint_has_chat_completions': endpoint.get('has_chat_completions'),
            'endpoint_supports_tool_parameters': endpoint.get('supports_tool_parameters'),
            'endpoint_supports_reasoning': endpoint.get('supports_reasoning'),
            'endpoint_supports_multipart': endpoint.get('supports_multipart'),
            'endpoint_deprecation_date': endpoint.get('deprecation_date'),
            # 定价相关
            'pricing_prompt': pricing.get('prompt'),
            'pricing_completion': pricing.get('completion'),
            'pricing_input_cache_read': pricing.get('input_cache_read'),
            'pricing_discount': pricing.get('discount'),
            'pricing_json': pricing_json,
            'display_pricing': display_pricing,
            # provider_info 关键字段
            'provider_display_name': provider_info.get('displayName'),
            'provider_slug': provider_info.get('slug'),
            'provider_base_url': provider_info.get('baseUrl'),
            'provider_headquarters': provider_info.get('headquarters'),
            'provider_datacenters': provider_info.get('datacenters'),
            'provider_icon_url': provider_info.get('icon', {}).get('url'),
            # data_policy
            'data_policy_training': data_policy.get('training'),
            'data_policy_training_openrouter': data_policy.get('trainingOpenRouter'),
            'data_policy_retains_prompts': data_policy.get('retainsPrompts'),
            'data_policy_can_publish': data_policy.get('canPublish'),
            # features
            'features_supports_tool_choice': features.get('supports_tool_choice'),
            'features_reasoning_return_mechanism': features.get('reasoning_return_mechanism'),
        }
        rows.append(flat_model)

    df = pd.DataFrame(rows)
    return df


# 返回模型端点的实时性能统计（吞吐量、延迟、请求数、状态）
def parse_endpoint_stats(file_path: str):
    """
    解析 OpenRouter API 返回的 endpoint stats JSON 文件

    返回每个端点的性能统计数据（吞吐量、延迟、请求数等），扁平化 stats 子对象。
    """
    import json
    import pandas as pd

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    endpoints = raw.get('data', [])
    rows = []

    for ep in endpoints:
        # 提取 stats 对象
        stats = ep.pop('stats', {})
        # 提取 model 嵌套对象（可选，可保留或省略）
        model_info = ep.pop('model', {})

        flat_ep = {
            **ep,
            'model_slug': model_info.get('slug'),
            'model_name': model_info.get('name'),
            'model_short_name': model_info.get('short_name'),
            'model_author': model_info.get('author'),
            'model_description': model_info.get('description'),
            'model_context_length': model_info.get('context_length'),
            'model_supports_reasoning': model_info.get('supports_reasoning'),
            'model_reasoning_start_token': model_info.get('reasoning_config', {}).get('start_token'),
            'model_reasoning_end_token': model_info.get('reasoning_config', {}).get('end_token'),
            # stats 字段
            'stats_p50_throughput': stats.get('p50_throughput'),
            'stats_p75_throughput': stats.get('p75_throughput'),
            'stats_p90_throughput': stats.get('p90_throughput'),
            'stats_p95_throughput': stats.get('p95_throughput'),
            'stats_p99_throughput': stats.get('p99_throughput'),
            'stats_p50_latency': stats.get('p50_latency'),
            'stats_p75_latency': stats.get('p75_latency'),
            'stats_p90_latency': stats.get('p90_latency'),
            'stats_p95_latency': stats.get('p95_latency'),
            'stats_p99_latency': stats.get('p99_latency'),
            'stats_request_count': stats.get('request_count'),
            'stats_window_minutes': stats.get('window_minutes'),
            # 状态
            'status': ep.get('status')
        }
        rows.append(flat_ep)

    df = pd.DataFrame(rows)
    return df




# 获取模型最近一段时间的 uptime 统计数据
def parse_uptime_recent(file_path: str):
    """
    解析 /api/frontend/stats/uptime-recent 接口，返回扁平化的 DataFrame
    """
    import json
    import pandas as pd

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    data = raw.get('data', {})
    rows = []
    for endpoint_id, records in data.items():
        for rec in records:
            rows.append({
                'endpoint_id': endpoint_id,
                'date': rec.get('date'),
                'uptime': rec.get('uptime')
            })
    return pd.DataFrame(rows)


# 获取用户或默认的提供商偏好（如排序、过滤）
def parse_provider_preferences(file_path: str):
    """
    解析 /api/internal/v1/provider-preferences 接口，处理未授权情况
    """
    import json
    import pandas as pd

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    if 'error' in raw:
        # 可打印警告或返回空 DataFrame
        print(f"API 返回错误: {raw['error'].get('message')}")
        return pd.DataFrame()
    data = raw.get('data', raw)
    if isinstance(data, dict):
        return pd.DataFrame([data])
    elif isinstance(data, list):
        return pd.DataFrame(data)
    else:
        return pd.DataFrame()


# 获取模型在 Artificial Analysis 上的基准评分
def parse_artificial_analysis_benchmark(file_path: str):
    """
    解析 /api/internal/v1/artificial-analysis-benchmarks 接口
    """
    import json
    import pandas as pd

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    data = raw.get('data', [])
    if isinstance(data, list):
        return pd.DataFrame(data)
    else:
        return pd.DataFrame([data])


# 获取模型在 Design Arena 上的基准评分
def parse_design_arena_benchmark(file_path: str):
    """
    解析 /api/internal/v1/design-arena-benchmarks 接口
    """
    import json
    import pandas as pd

    with open(file_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    data = raw.get('data', [])
    if isinstance(data, list):
        return pd.DataFrame(data)
    else:
        return pd.DataFrame([data])


# ============================================================================
# Benchmarks 页面 DOM 抓取函数
# ============================================================================

def fetch_benchmarks_page(model_slug):
    """
    使用 DynamicFetcher 抓取 benchmarks 页面

    参数:
        model_slug: 模型标识，如 "minimax/minimax-m2.7-20260318"

    返回:
        dict: {"success": bool, "data": dict, "html": str, "error": str}
    """
    url = f"https://openrouter.ai/{model_slug}/benchmarks"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取 Benchmarks 页面: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    try:
        start_time = time.time()
        # 关键: 使用 DynamicFetcher 才能获取完整数据
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
            return {"success": False, "data": None, "html": None, "error": "无法获取页面内容"}

        print(f"  HTML 大小: {len(html_content):,} 字符")

        # 保存 HTML 用于调试
        if SAVE_BENCHMARKS_HTML:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_file = f"benchmarks_debug_{model_slug.replace('/', '_')}_{timestamp}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"  HTML 已保存: {html_file}")

        # 提取 benchmark 数据
        data = extract_benchmarks_from_html(html_content)

        if data:
            print(f"  成功提取 benchmark 数据")
            return {"success": True, "data": data, "html": html_content, "error": None}
        else:
            return {"success": False, "data": None, "html": html_content, "error": "未能提取到 benchmark 数据"}

    except Exception as e:
        print(f"  抓取失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "data": None, "html": None, "error": str(e)}


def extract_benchmarks_from_html(html_content):
    """
    从 HTML 内容中提取 Design Arena benchmark 数据
    """
    result = {
        "category_performance": [],
        "models_arena": [],
        "agents_arena": [],
        "ranking_distribution": []
    }

    # 1. 提取 Category Performance (雷达图数据)
    category_pattern = r'fill-foreground text-xs font-medium">([^<]+)</text>.*?fill-muted-foreground text-2xs">Elo:\s*(\d+)</text>'
    category_matches = re.findall(category_pattern, html_content, re.DOTALL)

    for match in category_matches:
        result["category_performance"].append({
            "category": match[0].strip(),
            "elo": int(match[1])
        })

    # 2. 提取 Models Arena 数据
    models_section_match = re.search(
        r'<h3[^>]*>Models Arena</h3>(.*?)(?:<h3[^>]*>Agents Arena</h3>|<div class="pt-4")',
        html_content,
        re.DOTALL
    )

    if models_section_match:
        models_html = models_section_match.group(1)
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

    # 3. 提取 Agents Arena 数据
    agents_section_match = re.search(
        r'<h3[^>]*>Agents Arena</h3>(.*?)(?:<div class="pt-4"|</div>\s*</div>\s*<div)',
        html_content,
        re.DOTALL
    )

    if agents_section_match:
        agents_html = agents_section_match.group(1)
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

    # 4. 提取 Ranking Distribution
    ranking_section = re.search(
        r'<span class="text-sm font-medium">Ranking Distribution</span>(.*?)(?:<div class="flex flex-col gap-3 rounded-lg border|<div class="grid)',
        html_content,
        re.DOTALL
    )

    if ranking_section:
        ranking_html = ranking_section.group(1)
        tspan_pattern = r'<tspan[^>]*>(\d+)</tspan>'
        values = re.findall(tspan_pattern, ranking_html)

        labels = ['First', 'Second', 'Third', 'Fourth']
        for i, label in enumerate(labels):
            if i < len(values):
                result["ranking_distribution"].append({
                    "rank": label,
                    "count": int(values[i])
                })

    # 检查是否有数据
    total_items = sum(len(result[k]) for k in result)

    if total_items == 0:
        return None

    return result


def parse_benchmarks_to_dataframes(benchmarks_data):
    """
    将 benchmark 数据转换为 DataFrame
    """
    dataframes = {}

    if benchmarks_data.get("category_performance"):
        dataframes["benchmarks_category_performance"] = pd.DataFrame(benchmarks_data["category_performance"])

    if benchmarks_data.get("models_arena"):
        dataframes["benchmarks_models_arena"] = pd.DataFrame(benchmarks_data["models_arena"])

    if benchmarks_data.get("agents_arena"):
        dataframes["benchmarks_agents_arena"] = pd.DataFrame(benchmarks_data["agents_arena"])

    if benchmarks_data.get("ranking_distribution"):
        dataframes["benchmarks_ranking_distribution"] = pd.DataFrame(benchmarks_data["ranking_distribution"])

    return dataframes


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as err:
        print(f"\n错误: {err}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
