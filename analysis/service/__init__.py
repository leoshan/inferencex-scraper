"""
数据分析服务 - 整合趋势分析、异常检测、聚类分析、应用场景分析、竞品对比分析
"""

import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

from .trend_analyzer import TrendAnalyzer, TrendResult
from .anomaly_detector import AnomalyDetector, AnomalyResult
from .cluster_analyzer import AppClusterAnalyzer
from .app_analyzer import AppAnalyzer
from .comparison_analyzer import ComparisonAnalyzer


class AnalysisService:
    """分析服务整合"""

    def __init__(self):
        self.trend_analyzer = TrendAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.cluster_analyzer = AppClusterAnalyzer()
        self.app_analyzer = AppAnalyzer()
        self.comparison_analyzer = ComparisonAnalyzer()

    async def analyze_model_trend(
        self,
        df: pd.DataFrame,
        model_slug: str
    ) -> Dict:
        """分析单个模型的趋势"""
        model_df = df[df['model_slug'] == model_slug].copy()

        if len(model_df) == 0:
            return {'error': f'No data found for model: {model_slug}'}

        trend_result = self.trend_analyzer.analyze_trend(model_df)
        anomalies = self.anomaly_detector.detect_all_anomalies(model_df)

        return {
            'model_slug': model_slug,
            'trend': trend_result,
            'anomalies': [a.__dict__ for a in anomalies]
        }

    async def analyze_app_distribution(
        self,
        df: pd.DataFrame
    ) -> Dict:
        """分析应用分布"""
        app_totals = df.groupby('app_name')['total_tokens'].sum().sort_values(ascending=False)

        total = app_totals.sum()
        app_shares = (app_totals / total * 100).round(2)

        clustering = self.cluster_analyzer.cluster_by_usage_pattern(df)

        # 转换 numpy 类型为 Python 原生类型
        app_totals_dict = {k: int(v) for k, v in app_totals.to_dict().items()}
        app_shares_dict = {k: float(v) for k, v in app_shares.to_dict().items()}

        return {
            'app_totals': app_totals_dict,
            'app_shares': app_shares_dict,
            'clustering': clustering
        }

    async def get_trend_summary(
        self,
        df: pd.DataFrame
    ) -> Dict:
        """获取趋势摘要"""
        if len(df) == 0:
            return {
                'total_models': 0,
                'total_apps': 0,
                'total_tokens': 0,
                'total_requests': 0,
                'date_range': {'start': None, 'end': None}
            }

        # 处理 time 字段
        time_min = df['time'].min() if 'time' in df.columns and len(df) > 0 else None
        time_max = df['time'].max() if 'time' in df.columns and len(df) > 0 else None

        # 转换为字符串格式
        if time_min is not None:
            time_min = str(time_min)
        if time_max is not None:
            time_max = str(time_max)

        summary = {
            'total_models': df['model_slug'].nunique() if 'model_slug' in df.columns else 0,
            'total_apps': df['app_name'].nunique() if 'app_name' in df.columns else 0,
            'total_tokens': int(df['total_tokens'].sum()) if 'total_tokens' in df.columns else 0,
            'total_requests': int(df['requests'].sum()) if 'requests' in df.columns else 0,
            'date_range': {
                'start': time_min,
                'end': time_max
            }
        }

        return summary

    async def get_category_analysis(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """获取应用场景分类分析"""
        return self.app_analyzer.analyze_category_trends(df, start_date, end_date)

    async def get_category_distribution(
        self,
        df: pd.DataFrame
    ) -> List[Dict]:
        """获取场景分布数据 (饼图格式)"""
        return self.app_analyzer.get_category_distribution(df)

    async def get_category_time_series(
        self,
        df: pd.DataFrame,
        category: Optional[str] = None
    ) -> Dict:
        """获取场景时间序列数据"""
        return self.app_analyzer.get_category_time_series(df, category)

    async def get_top_apps_by_category(
        self,
        df: pd.DataFrame,
        category: str,
        top_n: int = 10
    ) -> List[Dict]:
        """获取指定场景下的 Top 应用"""
        return self.app_analyzer.get_top_apps_by_category(df, category, top_n)

    async def compare_models(
        self,
        model_slugs: List[str],
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """多模型对比分析"""
        return self.comparison_analyzer.compare_models(model_slugs, df, start_date, end_date)

    async def get_model_rankings(
        self,
        df: pd.DataFrame,
        metric: str = 'total_tokens',
        period: str = 'week',
        limit: int = 20
    ) -> List[Dict]:
        """获取模型排名"""
        return self.comparison_analyzer.rank_models(df, metric, period, limit)

    async def get_usage_heatmap(
        self,
        df: pd.DataFrame,
        top_n: int = 20,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """获取调用量热力图数据"""
        return self.comparison_analyzer.get_usage_heatmap(df, top_n, start_date, end_date)

    async def get_model_metrics(
        self,
        model_slug: str,
        df: pd.DataFrame
    ) -> Dict:
        """获取模型详细指标"""
        return self.comparison_analyzer.get_model_metrics_detail(model_slug, df)


__all__ = [
    'AnalysisService',
    'TrendAnalyzer',
    'TrendResult',
    'AnomalyDetector',
    'AnomalyResult',
    'AppClusterAnalyzer',
    'AppAnalyzer',
    'ComparisonAnalyzer',
]
