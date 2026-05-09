"""
配置文件
"""

from dataclasses import dataclass
from typing import List
import os


@dataclass
class Config:
    """采集配置"""

    # 数据库配置
    database_url: str = os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/trend_tracker'
    )

    # Redis 配置
    redis_url: str = os.getenv('REDIS_URL', 'redis://localhost:6379')

    # OpenRouter API 基础 URL
    openrouter_base_url: str = 'https://openrouter.ai/api/frontend'

    # 采集间隔配置 (小时)
    model_usage_interval: int = 1
    app_distribution_interval: int = 6
    model_list_interval: int = 24
    benchmarks_interval: int = 168  # 每周

    # 目标模型列表 (为空则采集所有)
    target_models: List[str] = None

    # 目标应用列表 (为空则采集所有)
    target_apps: List[str] = None

    # 请求超时 (秒)
    request_timeout: int = 60

    # 重试次数
    max_retries: int = 3

    def __post_init__(self):
        if self.target_models is None:
            self.target_models = []
        if self.target_apps is None:
            self.target_apps = []
