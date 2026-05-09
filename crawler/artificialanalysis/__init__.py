"""
Artificial Analysis 爬虫模块

使用方法:
    from artificialanalysis.scraper import fetch_and_save, fetch_artificialanalysis_page

    # 抓取并保存数据
    result = fetch_and_save()

    # 只抓取页面
    result = fetch_artificialanalysis_page()
"""

from .scraper import (
    fetch_artificialanalysis_page,
    fetch_and_save,
    extract_data_from_html,
    save_to_excel,
    save_raw_data,
)

__all__ = [
    'fetch_artificialanalysis_page',
    'fetch_and_save',
    'extract_data_from_html',
    'save_to_excel',
    'save_raw_data',
]
