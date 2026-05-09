"""
启动脚本
"""

import asyncio
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_api_server(host: str = "127.0.0.1", port: int = 8005):
    """启动 API 服务器"""
    import uvicorn
    from web.api.main import app

    logger.info(f"Starting API server on {host}:{port}")
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def run_collector():
    """启动数据采集服务"""
    from data import init_database
    from crawler.openrouter.trend_tracker.scheduler import start_scheduler, stop_scheduler

    logger.info("Initializing database...")
    await init_database()

    logger.info("Starting scheduler...")
    start_scheduler()

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_scheduler()


async def run_once():
    """运行一次采集 (测试用)"""
    from data import init_database
    from crawler.openrouter.trend_tracker.collector import DataCollector

    logger.info("Initializing database...")
    await init_database()

    logger.info("Running one-time collection...")
    collector = DataCollector()
    await collector.init()

    await collector.collect_model_list()
    await collector.collect_model_usage()
    await collector.collect_app_distribution()

    logger.info("Collection completed")


def main():
    parser = argparse.ArgumentParser(description="OpenRouter Trend Tracker")
    parser.add_argument('command', choices=['api', 'collector', 'once'],
                        help='Command to run: api (start API server), collector (start data collector), once (run once)')
    parser.add_argument('--host', default='127.0.0.1', help='API server host')
    parser.add_argument('--port', type=int, default=8005, help='API server port')

    args = parser.parse_args()

    if args.command == 'api':
        asyncio.run(run_api_server(args.host, args.port))
    elif args.command == 'collector':
        asyncio.run(run_collector())
    elif args.command == 'once':
        asyncio.run(run_once())


if __name__ == '__main__':
    main()