"""
APScheduler 调度器
"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Optional

from .collector import DataCollector
from .config import Config

logger = logging.getLogger(__name__)

scheduler: Optional[AsyncIOScheduler] = None
collector: Optional[DataCollector] = None


async def collect_model_usage_job():
    """定时采集模型使用量"""
    global collector
    if collector is None:
        collector = DataCollector()
        await collector.init()

    logger.info("Starting model usage collection...")
    result = await collector.collect_model_usage()
    if result['success']:
        logger.info("Model usage collection completed successfully")
    else:
        logger.error(f"Model usage collection failed: {result.get('error')}")


async def collect_app_distribution_job():
    """定时采集应用分布"""
    global collector
    if collector is None:
        collector = DataCollector()
        await collector.init()

    logger.info("Starting app distribution collection...")
    result = await collector.collect_app_distribution()
    if result['success']:
        logger.info("App distribution collection completed successfully")
    else:
        logger.error(f"App distribution collection failed: {result.get('error')}")


async def collect_model_list_job():
    """定时采集模型列表"""
    global collector
    if collector is None:
        collector = DataCollector()
        await collector.init()

    logger.info("Starting model list collection...")
    result = await collector.collect_model_list()
    if result['success']:
        logger.info("Model list collection completed successfully")
    else:
        logger.error(f"Model list collection failed: {result.get('error')}")


def start_scheduler(config: Optional[Config] = None):
    """启动调度器"""
    global scheduler, collector

    config = config or Config()
    scheduler = AsyncIOScheduler()
    collector = DataCollector(config)

    # 每小时采集模型调用量
    scheduler.add_job(
        collect_model_usage_job,
        trigger=IntervalTrigger(hours=config.model_usage_interval),
        id='model_usage_hourly',
        name='Collect Model Usage',
        replace_existing=True
    )

    # 每6小时采集应用分布
    scheduler.add_job(
        collect_app_distribution_job,
        trigger=IntervalTrigger(hours=config.app_distribution_interval),
        id='app_distribution',
        name='Collect App Distribution',
        replace_existing=True
    )

    # 每日更新模型列表 (凌晨2点)
    scheduler.add_job(
        collect_model_list_job,
        trigger=CronTrigger(hour=2, minute=0),
        id='model_list_daily',
        name='Collect Model List',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started with jobs: model_usage_hourly, app_distribution, model_list_daily")


def stop_scheduler():
    """停止调度器"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def run_once():
    """运行一次采集 (用于测试)"""
    await collect_model_usage_job()
    await collect_app_distribution_job()
    await collect_model_list_job()


if __name__ == '__main__':
    # 直接运行调度器
    logging.basicConfig(level=logging.INFO)

    async def main():
        # 初始化数据库
        from data import init_database
        await init_database()

        # 启动调度器
        start_scheduler()

        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            stop_scheduler()

    asyncio.run(main())
