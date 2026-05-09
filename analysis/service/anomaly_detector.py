"""
异常检测器
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class AnomalyResult:
    """异常检测结果"""
    time: datetime
    value: float
    anomaly_type: str  # 'spike', 'drop', 'zero', 'pattern_change'
    severity: str  # 'low', 'medium', 'high'
    z_score: Optional[float] = None
    details: Optional[Dict] = None


class AnomalyDetector:
    """异常检测器"""

    def __init__(self, spike_threshold: float = 3.0, pattern_change_threshold: float = 0.5):
        self.spike_threshold = spike_threshold
        self.pattern_change_threshold = pattern_change_threshold

    def detect_spikes(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens'
    ) -> List[AnomalyResult]:
        """检测突发增长 (Z-Score)"""
        mean = df[column].mean()
        std = df[column].std()

        if std == 0:
            return []

        anomalies = []
        for _, row in df.iterrows():
            z_score = (row[column] - mean) / std

            if abs(z_score) > self.spike_threshold:
                anomaly_type = 'spike' if z_score > 0 else 'drop'
                severity = 'high' if abs(z_score) > 5 else 'medium'

                anomalies.append(AnomalyResult(
                    time=row['time'],
                    value=row[column],
                    anomaly_type=anomaly_type,
                    severity=severity,
                    z_score=z_score
                ))

        return anomalies

    def detect_zero_usage(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens',
        consecutive_days: int = 3
    ) -> List[AnomalyResult]:
        """检测零使用"""
        anomalies = []
        zero_count = 0
        start_time = None

        for _, row in df.iterrows():
            if row[column] == 0:
                if zero_count == 0:
                    start_time = row['time']
                zero_count += 1
            else:
                if zero_count >= consecutive_days:
                    anomalies.append(AnomalyResult(
                        time=start_time,
                        value=0,
                        anomaly_type='zero_usage',
                        severity='high',
                        details={'duration_days': zero_count}
                    ))
                zero_count = 0

        return anomalies

    def detect_pattern_change(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens',
        window: int = 7
    ) -> List[AnomalyResult]:
        """检测模式变化"""
        if len(df) < window * 4:
            return []

        anomalies = []
        df = df.copy()
        df['rolling_mean'] = df[column].rolling(window).mean()

        for i in range(window * 2, len(df)):
            prev_mean = df.iloc[i - window * 2:i - window]['rolling_mean'].mean()
            curr_mean = df.iloc[i - window:i]['rolling_mean'].mean()

            if prev_mean > 0 and not np.isnan(prev_mean) and not np.isnan(curr_mean):
                change_ratio = abs(curr_mean - prev_mean) / prev_mean

                if change_ratio > self.pattern_change_threshold:
                    anomalies.append(AnomalyResult(
                        time=df.iloc[i]['time'],
                        value=df.iloc[i][column],
                        anomaly_type='pattern_change',
                        severity='medium',
                        details={
                            'prev_mean': prev_mean,
                            'curr_mean': curr_mean,
                            'change_ratio': change_ratio
                        }
                    ))

        return anomalies

    def detect_all_anomalies(
        self,
        df: pd.DataFrame,
        column: str = 'total_tokens'
    ) -> List[AnomalyResult]:
        """检测所有类型的异常"""
        all_anomalies = []

        all_anomalies.extend(self.detect_spikes(df, column))
        all_anomalies.extend(self.detect_zero_usage(df, column))
        all_anomalies.extend(self.detect_pattern_change(df, column))

        all_anomalies.sort(key=lambda x: x.time, reverse=True)

        return all_anomalies
