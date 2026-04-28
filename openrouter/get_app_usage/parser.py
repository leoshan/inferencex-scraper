#!/usr/bin/env python
"""
数据解析模块 - 将原始数据转换为 pandas DataFrame
"""

import pandas as pd
from datetime import datetime


def parse_usage_data(raw_data, source_type="api"):
    """
    解析使用量数据为 DataFrame

    参数:
        raw_data: 原始数据（dict 或 list）
        source_type: 数据来源类型 ("api" 或 "dom")

    返回:
        pd.DataFrame: 包含日期和使用量的 DataFrame
    """
    try:
        if source_type == "api":
            return parse_api_data(raw_data)
        elif source_type == "dom":
            return parse_dom_data(raw_data)
        else:
            raise ValueError(f"未知的数据来源类型: {source_type}")
    except Exception as e:
        print(f"解析数据失败: {e}")
        return pd.DataFrame()


def parse_api_data(data):
    """
    解析 API 返回的数据

    参数:
        data: API 返回的 dict

    返回:
        pd.DataFrame
    """
    rows = []

    # 尝试不同的数据结构
    # 结构1: {"usage": [...]}
    if isinstance(data, dict) and 'usage' in data:
        usage_data = data['usage']
        if isinstance(usage_data, list):
            rows = usage_data

    # 结构2: {"data": [...]}
    elif isinstance(data, dict) and 'data' in data:
        usage_data = data['data']
        if isinstance(usage_data, list):
            rows = usage_data

    # 结构3: {"chart": [...]} 或 {"chartData": [...]}
    elif isinstance(data, dict):
        for key in ['chart', 'chartData', 'chart_data', 'usage_chart']:
            if key in data and isinstance(data[key], list):
                rows = data[key]
                break

    # 结构4: 直接是列表
    elif isinstance(data, list):
        rows = data

    if not rows:
        print("  警告: 未找到有效的数据数组")
        return pd.DataFrame()

    # 转换为 DataFrame
    df = pd.DataFrame(rows)

    # 标准化列名
    df = normalize_columns(df)

    # 清理数据
    df = clean_dataframe(df)

    return df


def parse_dom_data(data):
    """
    解析 DOM 提取的数据

    参数:
        data: DOM 提取的 list

    返回:
        pd.DataFrame
    """
    if not isinstance(data, list) or len(data) == 0:
        return pd.DataFrame()

    # 检查数据格式
    # 格式1: [{"x": "2026-03-23 00:00:00", "ys": {"model1": 123, "model2": 456}}]
    if isinstance(data[0], dict) and 'x' in data[0] and 'ys' in data[0]:
        print("  检测到格式: 时间序列数据 (x, ys)")
        rows = []
        for item in data:
            date = item.get('x', '')
            # 移除时间部分，只保留日期
            if ' ' in date:
                date = date.split(' ')[0]

            ys = item.get('ys', {})
            # 计算总使用量
            total = sum(ys.values())

            row = {
                'date': date,
                'total_tokens': total,
            }

            # 添加各个模型的使用量
            for model, tokens in ys.items():
                # 简化模型名称
                model_short = model.split('/')[-1] if '/' in model else model
                row[f'tokens_{model_short}'] = tokens

            rows.append(row)

        df = pd.DataFrame(rows)

    # 格式2: [{"date": "2026-04-22", "value": 123}]
    else:
        df = pd.DataFrame(data)

    # 标准化列名
    df = normalize_columns(df)

    # 清理数据
    df = clean_dataframe(df)

    return df


def normalize_columns(df):
    """
    标准化 DataFrame 列名

    参数:
        df: 原始 DataFrame

    返回:
        pd.DataFrame: 列名标准化后的 DataFrame
    """
    if df.empty:
        return df

    # 列名映射
    column_mapping = {
        # 日期相关
        'date': 'date',
        'Date': 'date',
        'day': 'date',
        'Day': 'date',
        'timestamp': 'date',
        'time': 'date',

        # 使用量相关
        'value': 'usage',
        'Value': 'usage',
        'usage': 'usage',
        'Usage': 'usage',
        'tokens': 'tokens',
        'Tokens': 'tokens',
        'total_tokens': 'tokens',
        'totalTokens': 'tokens',

        # 请求数相关
        'requests': 'requests',
        'Requests': 'requests',
        'request_count': 'requests',
        'requestCount': 'requests',
        'num_requests': 'requests',

        # 其他指标
        'prompt_tokens': 'prompt_tokens',
        'completion_tokens': 'completion_tokens',
        'cache_hits': 'cache_hits',
        'tool_calls': 'tool_calls',
    }

    # 重命名列
    df = df.rename(columns=column_mapping)

    return df


def clean_dataframe(df):
    """
    清理 DataFrame 数据

    参数:
        df: 原始 DataFrame

    返回:
        pd.DataFrame: 清理后的 DataFrame
    """
    if df.empty:
        return df

    # 处理日期列
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        except Exception as e:
            print(f"  警告: 日期转换失败: {e}")

    # 处理数值列
    numeric_columns = ['usage', 'tokens', 'requests', 'prompt_tokens',
                      'completion_tokens', 'cache_hits', 'tool_calls']

    for col in numeric_columns:
        if col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                print(f"  警告: 列 {col} 转换为数值失败: {e}")

    # 删除全为 NaN 的列
    df = df.dropna(axis=1, how='all')

    # 重置索引
    df = df.reset_index(drop=True)

    return df


def create_metadata_df(app_name, fetch_time, source_type, endpoint=None, record_count=0):
    """
    创建元数据 DataFrame

    参数:
        app_name: 应用名称
        fetch_time: 获取时间
        source_type: 数据来源类型
        endpoint: API 端点（如果有）
        record_count: 记录数

    返回:
        pd.DataFrame: 元数据 DataFrame
    """
    metadata = {
        '应用名称': [app_name],
        '获取时间': [fetch_time],
        '数据来源': [source_type],
        'API端点': [endpoint if endpoint else 'N/A'],
        '记录数': [record_count]
    }

    return pd.DataFrame(metadata)
