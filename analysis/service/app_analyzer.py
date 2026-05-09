"""
应用场景分析器 - 自动分类应用并分析各场景趋势
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CategoryResult:
    """场景分类结果"""
    category: str
    total_tokens: int
    total_requests: int
    apps: List[str]
    top_models: List[str]


class AppAnalyzer:
    """应用场景分析器"""

    # 预定义应用分类规则 (基于应用名称关键词匹配)
    CATEGORY_RULES = {
        'coding': [
            'cursor', 'claude-code', 'copilot', 'codeium', 'zed',
            'vscode', 'vim', 'neovim', 'jetbrains', 'intellij',
            'code', 'dev', 'programming', 'debugger', 'linter'
        ],
        'chat': [
            'chatgpt', 'perplexity', 'poe', 'character.ai',
            'chat', 'talk', 'conversation', 'assistant', 'bot'
        ],
        'creative': [
            'midjourney', 'dalle', 'suno', 'runway', 'stable',
            'creative', 'art', 'design', 'image', 'video', 'audio',
            'music', 'generate'
        ],
        'analysis': [
            'notion', 'mem', 'raycast', 'linear', 'obsidian',
            'analysis', 'research', 'data', 'analytics', 'insight',
            'dashboard', 'report'
        ],
        'agent': [
            'autogpt', 'crewai', 'langchain', 'agent', 'agents',
            'workflow', 'automation', 'task', 'pipeline'
        ],
        'api': [
            'api', 'sdk', 'integration', 'backend', 'service',
            'endpoint', 'proxy', 'gateway'
        ],
        'education': [
            'learn', 'education', 'teach', 'course', 'tutorial',
            'student', 'academic', 'school', 'university'
        ],
        'enterprise': [
            'enterprise', 'business', 'corporate', 'company',
            'crm', 'erp', 'salesforce', 'slack', 'teams'
        ],
        'other': []
    }

    def __init__(self):
        self._app_category_cache: Dict[str, str] = {}

    def categorize_app(self, app_name: str) -> str:
        """根据应用名称自动分类

        Args:
            app_name: 应用名称

        Returns:
            分类名称: 'coding', 'chat', 'creative', 'analysis', 'agent', 'api', 'education', 'enterprise', 'other'
        """
        if app_name in self._app_category_cache:
            return self._app_category_cache[app_name]

        app_name_lower = app_name.lower()

        # 按优先级顺序匹配关键词
        for category, keywords in self.CATEGORY_RULES.items():
            if category == 'other':
                continue
            for keyword in keywords:
                if keyword in app_name_lower:
                    self._app_category_cache[app_name] = category
                    return category

        # 未匹配则归入 'other'
        self._app_category_cache[app_name] = 'other'
        return 'other'

    def categorize_apps_batch(self, app_names: List[str]) -> Dict[str, str]:
        """批量分类应用

        Args:
            app_names: 应用名称列表

        Returns:
            应用名称到分类的映射字典
        """
        return {app: self.categorize_app(app) for app in app_names}

    def analyze_category_trends(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """分析各类场景的趋势变化

        Args:
            df: 包含 app_name, model_slug, total_tokens, requests, time 的 DataFrame
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            各类场景的趋势分析结果
        """
        if df.empty:
            return {'categories': [], 'distribution': []}

        # 添加场景分类列
        df['category'] = df['app_name'].apply(self.categorize_app)

        # 按场景聚合
        category_stats = df.groupby('category').agg({
            'total_tokens': 'sum',
            'requests': 'sum'
        }).reset_index()

        # 获取每个场景的应用列表
        category_apps = df.groupby('category')['app_name'].unique().to_dict()

        # 获取每个场景的 Top 模型
        category_models = {}
        for category in category_stats['category']:
            cat_df = df[df['category'] == category]
            top_models = cat_df.groupby('model_slug')['total_tokens'].sum()
            top_models = top_models.sort_values(ascending=False).head(5).index.tolist()
            category_models[category] = top_models

        # 计算增长率
        if start_date and end_date and 'time' in df.columns:
            df_sorted = df.sort_values('time')
            mid_point = len(df_sorted) // 2

            growth_rates = {}
            for category in category_stats['category']:
                cat_df = df_sorted[df_sorted['category'] == category]
                if len(cat_df) > 1:
                    recent = cat_df.iloc[mid_point:]['total_tokens'].sum()
                    previous = cat_df.iloc[:mid_point]['total_tokens'].sum()
                    if previous > 0:
                        growth_rates[category] = (recent - previous) / previous * 100
                    else:
                        growth_rates[category] = 0
                else:
                    growth_rates[category] = 0
        else:
            growth_rates = {cat: 0 for cat in category_stats['category']}

        # 构建结果
        categories = []
        for _, row in category_stats.iterrows():
            category = row['category']
            categories.append({
                'name': category,
                'total_tokens': int(row['total_tokens']),
                'total_requests': int(row['requests']),
                'apps': list(category_apps.get(category, [])),
                'top_models': category_models.get(category, []),
                'growth_rate': growth_rates.get(category, 0)
            })

        # 按总 tokens 排序
        categories.sort(key=lambda x: x['total_tokens'], reverse=True)

        # 生成饼图分布数据
        distribution = [
            {'name': cat['name'], 'value': cat['total_tokens']}
            for cat in categories
        ]

        return {
            'categories': categories,
            'distribution': distribution,
            'total_tokens': sum(cat['total_tokens'] for cat in categories),
            'total_requests': sum(cat['total_requests'] for cat in categories)
        }

    def get_category_distribution(self, df: pd.DataFrame) -> Dict:
        """获取场景分布数据 (饼图格式)

        Args:
            df: DataFrame

        Returns:
            饼图数据格式
        """
        result = self.analyze_category_trends(df)

        # 添加占比计算
        total = result['total_tokens'] or 1
        for item in result['distribution']:
            item['percentage'] = round(item['value'] / total * 100, 2)

        return result['distribution']

    def get_top_apps_by_category(
        self,
        df: pd.DataFrame,
        category: str,
        top_n: int = 10
    ) -> List[Dict]:
        """获取指定场景下的 Top 应用

        Args:
            df: DataFrame
            category: 场景分类
            top_n: 返回数量

        Returns:
            Top 应用列表
        """
        df['category'] = df['app_name'].apply(self.categorize_app)

        cat_df = df[df['category'] == category]
        if cat_df.empty:
            return []

        app_stats = cat_df.groupby('app_name').agg({
            'total_tokens': 'sum',
            'requests': 'sum'
        }).reset_index()

        app_stats = app_stats.sort_values('total_tokens', ascending=False)

        result = []
        for _, row in app_stats.head(top_n).iterrows():
            result.append({
                'app_name': row['app_name'],
                'total_tokens': int(row['total_tokens']),
                'total_requests': int(row['requests'])
            })

        return result

    def get_category_time_series(
        self,
        df: pd.DataFrame,
        category: Optional[str] = None
    ) -> Dict:
        """获取场景的时间序列数据

        Args:
            df: DataFrame (需要包含 time 列)
            category: 指定场景，为 None 时返回所有场景

        Returns:
            时间序列数据，用于趋势图
        """
        if df.empty or 'time' not in df.columns:
            return {'times': [], 'series': []}

        df['category'] = df['app_name'].apply(self.categorize_app)
        df['time'] = pd.to_datetime(df['time'])

        # 按时间和场景聚合
        time_cat_stats = df.groupby([pd.Grouper(key='time', freq='D'), 'category']).agg({
            'total_tokens': 'sum'
        }).reset_index()

        times = time_cat_stats['time'].unique()
        times = sorted(times)

        if category:
            # 返回指定场景的时间序列
            cat_data = time_cat_stats[time_cat_stats['category'] == category]
            series = {
                'name': category,
                'data': [cat_data[cat_data['time'] == t]['total_tokens'].sum()
                        if t in cat_data['time'].values else 0 for t in times]
            }
            return {
                'times': [t.strftime('%Y-%m-%d') for t in times],
                'series': [series]
            }
        else:
            # 返回所有场景的时间序列
            categories = time_cat_stats['category'].unique()
            series = []
            for cat in categories:
                cat_data = time_cat_stats[time_cat_stats['category'] == cat]
                series.append({
                    'name': cat,
                    'data': [cat_data[cat_data['time'] == t]['total_tokens'].sum()
                            if t in cat_data['time'].values else 0 for t in times]
                })

            return {
                'times': [t.strftime('%Y-%m-%d') for t in times],
                'series': series
            }