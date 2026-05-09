"""
竞品对比分析器 - 多模型对比、排名、热力图数据生成
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ModelMetrics:
    """模型指标数据"""
    model_slug: str
    total_tokens: int
    requests: int
    avg_tokens_per_request: float
    growth_rate: float
    market_share: float


@dataclass
class RankingItem:
    """排名项"""
    rank: int
    model_slug: str
    value: int
    change: float


class ComparisonAnalyzer:
    """竞品对比分析器"""

    def __init__(self):
        self._model_metadata_cache: Dict[str, Dict] = {}

    def compare_models(
        self,
        model_slugs: List[str],
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """多模型对比分析

        Args:
            model_slugs: 要对比的模型列表
            df: DataFrame (包含 model_slug, total_tokens, requests, time)
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            对比分析结果
        """
        if df.empty or not model_slugs:
            return self._empty_comparison(model_slugs)

        # 过滤指定模型
        df_filtered = df[df['model_slug'].isin(model_slugs)]
        if df_filtered.empty:
            return self._empty_comparison(model_slugs)

        # 计算各模型指标
        metrics = {}
        for model_slug in model_slugs:
            model_df = df_filtered[df_filtered['model_slug'] == model_slug]
            if model_df.empty:
                metrics[model_slug] = {
                    'total_tokens': 0,
                    'requests': 0,
                    'avg_tokens_per_request': 0,
                    'growth_rate': 0,
                    'market_share': 0
                }
            else:
                total_tokens = model_df['total_tokens'].sum()
                requests = model_df['requests'].sum()
                total_all = df_filtered['total_tokens'].sum()

                # 计算增长率
                if 'time' in model_df.columns and len(model_df) > 1:
                    model_df_sorted = model_df.sort_values('time')
                    mid = len(model_df_sorted) // 2
                    recent = model_df_sorted.iloc[mid:]['total_tokens'].sum()
                    previous = model_df_sorted.iloc[:mid]['total_tokens'].sum()
                    growth_rate = (recent - previous) / previous * 100 if previous > 0 else 0
                else:
                    growth_rate = 0

                metrics[model_slug] = {
                    'total_tokens': int(total_tokens),
                    'requests': int(requests),
                    'avg_tokens_per_request': round(total_tokens / requests, 2) if requests > 0 else 0,
                    'growth_rate': round(growth_rate, 2),
                    'market_share': round(total_tokens / total_all * 100, 2) if total_all > 0 else 0
                }

        # 生成趋势对比数据
        trend_comparison = self._generate_trend_comparison(df_filtered, model_slugs)

        # 生成排名
        ranking = self.rank_models(df_filtered, 'total_tokens', 'week')

        return {
            'models': model_slugs,
            'metrics': metrics,
            'trend_comparison': trend_comparison,
            'ranking': ranking[:len(model_slugs)]
        }

    def _empty_comparison(self, model_slugs: List[str]) -> Dict:
        """生成空的对比结果"""
        metrics = {
            slug: {
                'total_tokens': 0,
                'requests': 0,
                'avg_tokens_per_request': 0,
                'growth_rate': 0,
                'market_share': 0
            }
            for slug in model_slugs
        }
        return {
            'models': model_slugs,
            'metrics': metrics,
            'trend_comparison': {'times': [], 'series': []},
            'ranking': []
        }

    def _generate_trend_comparison(
        self,
        df: pd.DataFrame,
        model_slugs: List[str]
    ) -> Dict:
        """生成趋势对比数据

        Args:
            df: DataFrame
            model_slugs: 模型列表

        Returns:
            ECharts 多线图格式数据
        """
        if 'time' not in df.columns:
            return {'times': [], 'series': []}

        df['time'] = pd.to_datetime(df['time'])
        daily_stats = df.groupby([pd.Grouper(key='time', freq='D'), 'model_slug']).agg({
            'total_tokens': 'sum'
        }).reset_index()

        times = sorted(daily_stats['time'].unique())
        times_str = [t.strftime('%Y-%m-%d') for t in times]

        series = []
        for model_slug in model_slugs:
            model_data = daily_stats[daily_stats['model_slug'] == model_slug]
            data = []
            for t in times:
                val = model_data[model_data['time'] == t]['total_tokens'].sum()
                data.append(int(val))
            series.append({
                'name': model_slug,
                'data': data
            })

        return {
            'times': times_str,
            'series': series
        }

    def rank_models(
        self,
        df: pd.DataFrame,
        metric: str = 'total_tokens',
        period: str = 'week',
        limit: int = 20
    ) -> List[Dict]:
        """模型排名

        Args:
            df: DataFrame
            metric: 排名指标 ('total_tokens', 'requests', 'growth_rate')
            period: 统计周期 ('day', 'week', 'month')
            limit: 返回数量

        Returns:
            排名列表
        """
        if df.empty:
            return []

        # 按模型聚合
        model_stats = df.groupby('model_slug').agg({
            'total_tokens': 'sum',
            'requests': 'sum'
        }).reset_index()

        # 计算 metrics
        total_all = model_stats['total_tokens'].sum()
        model_stats['market_share'] = model_stats['total_tokens'] / total_all * 100 if total_all > 0 else 0

        # 计算增长率 (简化版)
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df_sorted = df.sort_values('time')
            mid = len(df_sorted) // 2

            growth_rates = {}
            for model_slug in model_stats['model_slug']:
                model_df = df_sorted[df_sorted['model_slug'] == model_slug]
                if len(model_df) > 1:
                    recent = model_df.iloc[mid:]['total_tokens'].sum()
                    previous = model_df.iloc[:mid]['total_tokens'].sum()
                    growth_rates[model_slug] = (recent - previous) / previous * 100 if previous > 0 else 0
                else:
                    growth_rates[model_slug] = 0

            model_stats['growth_rate'] = model_stats['model_slug'].map(growth_rates)
        else:
            model_stats['growth_rate'] = 0

        # 选择排序指标
        if metric == 'total_tokens':
            model_stats = model_stats.sort_values('total_tokens', ascending=False)
        elif metric == 'requests':
            model_stats = model_stats.sort_values('requests', ascending=False)
        elif metric == 'growth_rate':
            model_stats = model_stats.sort_values('growth_rate', ascending=False)

        # 生成排名结果
        result = []
        for i, (_, row) in enumerate(model_stats.head(limit).iterrows(), 1):
            result.append({
                'rank': i,
                'model_slug': row['model_slug'],
                'value': int(row.get('total_tokens', 0)) if metric == 'total_tokens' else int(row.get('requests', 0)),
                'growth_rate': round(row.get('growth_rate', 0), 2),
                'market_share': round(row.get('market_share', 0), 2)
            })

        return result

    def get_usage_heatmap(
        self,
        df: pd.DataFrame,
        top_n: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """生成调用量热力图数据

        Args:
            df: DataFrame (需要包含 time, model_slug, total_tokens)
            top_n: Top N 模型数量
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            ECharts heatmap 格式数据
        """
        if df.empty or 'time' not in df.columns:
            return {'times': [], 'models': [], 'data': []}

        df['time'] = pd.to_datetime(df['time'])

        # 获取 Top N 模型
        top_models = df.groupby('model_slug')['total_tokens'].sum()
        top_models = top_models.sort_values(ascending=False).head(top_n).index.tolist()

        df_filtered = df[df['model_slug'].isin(top_models)]

        # 按日期和模型聚合
        daily_stats = df_filtered.groupby([
            pd.Grouper(key='time', freq='D'),
            'model_slug'
        ]).agg({'total_tokens': 'sum'}).reset_index()

        # 生成时间轴
        times = sorted(daily_stats['time'].unique())
        times_str = [t.strftime('%Y-%m-%d') for t in times]

        # 生成模型轴 (按总调用量排序)
        models = top_models

        # 生成热力图数据 [x_index, y_index, value]
        heatmap_data = []
        for i, t in enumerate(times):
            for j, model in enumerate(models):
                val = daily_stats[
                    (daily_stats['time'] == t) &
                    (daily_stats['model_slug'] == model)
                ]['total_tokens'].sum()
                heatmap_data.append([i, j, int(val)])

        return {
            'times': times_str,
            'models': models,
            'data': heatmap_data
        }

    def get_model_metrics_detail(
        self,
        model_slug: str,
        df: pd.DataFrame
    ) -> Dict:
        """获取模型详细指标

        Args:
            model_slug: 模型标识
            df: DataFrame

        Returns:
            模型详细指标数据
        """
        model_df = df[df['model_slug'] == model_slug]
        if model_df.empty:
            return {'model_slug': model_slug, 'error': 'No data found'}

        total_tokens = model_df['total_tokens'].sum()
        requests = model_df['requests'].sum()
        total_all = df['total_tokens'].sum()

        # 应用分布
        app_dist = model_df.groupby('app_name')['total_tokens'].sum()
        app_dist = app_dist.sort_values(ascending=False).head(10)
        app_distribution = [
            {'app_name': app, 'tokens': int(tokens)}
            for app, tokens in app_dist.items()
        ]

        # 计算时间范围
        if 'time' in model_df.columns:
            time_range = {
                'start': model_df['time'].min(),
                'end': model_df['time'].max()
            }
        else:
            time_range = None

        return {
            'model_slug': model_slug,
            'total_tokens': int(total_tokens),
            'total_requests': int(requests),
            'avg_tokens_per_request': round(total_tokens / requests, 2) if requests > 0 else 0,
            'market_share': round(total_tokens / total_all * 100, 2) if total_all > 0 else 0,
            'app_distribution': app_distribution,
            'time_range': time_range
        }