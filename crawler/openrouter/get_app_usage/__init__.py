"""
OpenRouter 应用使用量爬虫模块

用于爬取 OpenRouter 平台上特定应用（如 Claude Code）的使用量图表数据。
支持 API 端点和 DOM 爬取两种方式。
"""

from .scraper import fetch_app_usage

__all__ = ['fetch_app_usage']
