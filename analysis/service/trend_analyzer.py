"""
趋势分析器
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class TrendResult:
    """趋势分析结果"""
    growth_rate: float
    trend: str  # 'increasing', 'decreasing', 'stable'
    ma_7: Optional[float] = None
    ma_30: Optional[float] = None
    has_seasonality: bool = False
    weekly_autocorr: Optional[float] = None


class TrendAnalyzer:
    """趋势分析器"""

    def calculate_moving_average(
        self,
        df: pd.DataFrame,
        window: int = 7,
        column: str = 'total_tokens'
    ) -> pd.DataFrame:
        """计算移动平均"""
        df = df.sort_values('time').copy()
        df['ma_7'] = df[column].rolling(window=7, min_periods=1).mean()
        df['ma_30'] = df[column].rolling(window=30, min_periods=1).mean()
        return df

    def calculate_growth_rate(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens'
    ) -> TrendResult:
        """计算增长率"""
        if len(df) < 2:
            return TrendResult(growth_rate=0, trend='stable')

        df = df.sort_values('time')
        recent = df.tail(7)[column].sum()
        previous = df.tail(14).head(7)[column].sum() if len(df) >= 14 else df.head(7)[column].sum()

        if previous == 0:
            growth_rate = 0
        else:
            growth_rate = (recent - previous) / previous * 100

        if growth_rate > 5:
            trend = 'increasing'
        elif growth_rate < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return TrendResult(
            growth_rate=growth_rate,
            trend=trend,
            ma_7=df['ma_7'].iloc[-1] if 'ma_7' in df.columns else None,
            ma_30=df['ma_30'].iloc[-1] if 'ma_30' in df.columns else None
        )

    def detect_seasonality(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens'
    ) -> Dict:
        """检测周期性"""
        values = df[column].values
        if len(values) < 14:
            return {'has_seasonality': False}

        try:
            autocorr_weekly = pd.Series(values).autocorr(lag=7)
        except:
            autocorr_weekly = 0

        return {
            'has_seasonality': autocorr_weekly > 0.5 if not np.isnan(autocorr_weekly) else False,
            'weekly_autocorr': autocorr_weekly
        }

    def analyze_trend(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens'
    ) -> Dict:
        """综合趋势分析"""
        df = self.calculate_moving_average(df, column=column)
        growth = self.calculate_growth_rate(df, column=column)
        seasonality = self.detect_seasonality(df, column=column)

        return {
            'growth_rate': growth.growth_rate,
            'trend': growth.trend,
            'ma_7': growth.ma_7,
            'ma_30': growth.ma_30,
            'has_seasonality': seasonality['has_seasonality'],
            'weekly_autocorr': seasonality['weekly_autocorr'],
            'data': df.to_dict('records')
        }
