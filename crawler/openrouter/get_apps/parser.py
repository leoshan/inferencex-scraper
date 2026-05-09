#!/usr/bin/env python
"""
OpenRouter Apps 数据解析模块

解析从 API 或 DOM 提取的应用数据
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AppsData:
    """应用数据结构"""
    slug: str = ""
    name: str = ""
    description: str = ""
    url: str = ""
    icon_url: str = ""
    category: str = ""
    website: str = ""
    created_at: str = ""
    usage_count: int = 0
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in asdict(self).items() if v or k in ['slug', 'name']}


def parse_apps_data(data: Any) -> List[Dict[str, Any]]:
    """
    解析应用数据

    参数:
        data: 原始数据（可能是 dict 或 list）

    返回:
        list: 标准化的应用数据列表
    """
    if not data:
        return []

    apps = []

    # 如果是字典，尝试提取 apps 列表
    if isinstance(data, dict):
        # 常见的数据结构
        if 'apps' in data:
            apps_list = data['apps']
        elif 'data' in data:
            apps_list = data['data']
        elif 'results' in data:
            apps_list = data['results']
        else:
            # 可能整个字典就是一个应用
            apps_list = [data]
    elif isinstance(data, list):
        apps_list = data
    else:
        return []

    # 解析每个应用
    for item in apps_list:
        if isinstance(item, dict):
            app = parse_single_app(item)
            if app:
                apps.append(app)

    return apps


def parse_single_app(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    解析单个应用数据

    参数:
        item: 原始应用数据

    返回:
        dict: 标准化的应用数据
    """
    if not isinstance(item, dict):
        return None

    # 提取 slug（应用唯一标识）
    slug = (
        item.get('slug') or
        item.get('id') or
        item.get('app_id') or
        item.get('name', '').lower().replace(' ', '-')
    )

    if not slug:
        return None

    # 提取名称
    name = (
        item.get('name') or
        item.get('displayName') or
        item.get('display_name') or
        item.get('title') or
        slug
    )

    # 提取描述
    description = (
        item.get('description') or
        item.get('desc') or
        item.get('about') or
        item.get('summary') or
        ""
    )

    # 提取 URL
    url = item.get('url') or item.get('link') or ""
    if url and not url.startswith('http'):
        url = f"https://openrouter.ai{url}"

    # 如果没有 URL，根据 slug 构建
    if not url:
        url = f"https://openrouter.ai/apps/{slug}"

    # 提取图标
    icon_url = (
        item.get('icon') or
        item.get('icon_url') or
        item.get('iconUrl') or
        item.get('image') or
        item.get('thumbnail') or
        ""
    )
    if isinstance(icon_url, dict):
        icon_url = icon_url.get('url', '')

    # 提取分类
    category = (
        item.get('category') or
        item.get('type') or
        item.get('app_type') or
        ""
    )

    # 提取网站
    website = (
        item.get('website') or
        item.get('homepage') or
        item.get('site') or
        ""
    )

    # 提取创建时间
    created_at = (
        item.get('created_at') or
        item.get('createdAt') or
        item.get('created') or
        ""
    )

    # 提取使用量
    usage_count = 0
    usage_fields = ['usage_count', 'usageCount', 'usage', 'requests', 'calls']
    for field in usage_fields:
        if field in item:
            try:
                usage_count = int(item[field])
                break
            except (ValueError, TypeError):
                pass

    # 构建标准化数据
    app_data = {
        'slug': slug,
        'name': name,
        'description': description,
        'url': url,
        'icon_url': icon_url,
        'category': category,
        'website': website,
        'created_at': created_at,
        'usage_count': usage_count,
        'raw_data': {k: v for k, v in item.items() if k not in ['slug', 'name', 'description', 'url', 'icon_url', 'category', 'website', 'created_at', 'usage_count']}
    }

    return app_data


def parse_apps_from_html(html_content: str) -> List[Dict[str, Any]]:
    """
    从 HTML 内容解析应用数据

    参数:
        html_content: HTML 字符串

    返回:
        list: 应用数据列表
    """
    import re

    apps = []

    # 方法1: 查找 Next.js 数据
    next_data_pattern = r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.+?)</script>'
    matches = re.findall(next_data_pattern, html_content, re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match)
            # 尝试从 Next.js 数据中提取 apps
            if 'props' in data:
                props = data['props']
                if 'pageProps' in props:
                    page_props = props['pageProps']
                    if 'apps' in page_props:
                        apps.extend(parse_apps_data(page_props['apps']))
                    elif 'data' in page_props:
                        apps.extend(parse_apps_data(page_props['data']))
        except json.JSONDecodeError:
            continue

    if apps:
        return apps

    # 方法2: 查找 JSON 数据片段
    json_pattern = r'\{[^{}]*"slug"[^{}]*\}'
    matches = re.findall(json_pattern, html_content)

    for match in matches:
        try:
            data = json.loads(match)
            if 'slug' in data:
                app = parse_single_app(data)
                if app:
                    apps.append(app)
        except json.JSONDecodeError:
            continue

    return apps


def deduplicate_apps(apps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    去重应用列表

    参数:
        apps: 应用列表

    返回:
        list: 去重后的列表
    """
    seen = set()
    unique_apps = []

    for app in apps:
        slug = app.get('slug', '')
        if slug and slug not in seen:
            seen.add(slug)
            unique_apps.append(app)

    return unique_apps


def sort_apps_by_usage(apps: List[Dict[str, Any]], descending: bool = True) -> List[Dict[str, Any]]:
    """
    按使用量排序应用

    参数:
        apps: 应用列表
        descending: 是否降序

    返回:
        list: 排序后的列表
    """
    return sorted(
        apps,
        key=lambda x: x.get('usage_count', 0),
        reverse=descending
    )


def get_apps_summary(apps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    获取应用列表摘要

    参数:
        apps: 应用列表

    返回:
        dict: 摘要信息
    """
    if not apps:
        return {
            'total': 0,
            'categories': {},
            'with_usage': 0,
            'with_description': 0
        }

    categories = {}
    with_usage = 0
    with_description = 0

    for app in apps:
        # 统计分类
        category = app.get('category', '未分类')
        categories[category] = categories.get(category, 0) + 1

        # 统计有使用量的
        if app.get('usage_count', 0) > 0:
            with_usage += 1

        # 统计有描述的
        if app.get('description'):
            with_description += 1

    return {
        'total': len(apps),
        'categories': categories,
        'with_usage': with_usage,
        'with_description': with_description
    }
