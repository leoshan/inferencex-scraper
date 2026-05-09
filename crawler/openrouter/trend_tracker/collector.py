"""
数据收集器 - 复用现有爬虫模块 (SQLite 版本)
"""

import sys
import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from data import get_db_connection
from .config import Config

logger = logging.getLogger(__name__)


class DataCollector:
    """数据收集器"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.db = None

    async def init(self):
        """初始化数据库连接"""
        self.db = await get_db_connection()

    async def collect_model_usage(self, model_slug: Optional[str] = None) -> Dict[str, Any]:
        """采集模型使用量数据"""
        try:
            import subprocess

            url = f"{self.config.openrouter_base_url}/stats/top-apps-for-model"
            if model_slug:
                url += f"?model={model_slug}"

            logger.info(f"Collecting model usage from: {url}")

            result = subprocess.run(
                ['curl', '-sL', '--compressed', '--max-time', str(self.config.request_timeout),
                 '-H', 'User-Agent: Mozilla/5.0',
                 '-H', 'Accept: application/json',
                 url],
                capture_output=True, text=True, timeout=self.config.request_timeout + 10,
                encoding='utf-8', errors='ignore'
            )

            if result.returncode != 0:
                return {"success": False, "error": f"curl failed: {result.stderr}"}

            data = json.loads(result.stdout)
            await self._store_model_usage(data)

            return {"success": True, "data": data}

        except Exception as e:
            logger.error(f"Failed to collect model usage: {e}")
            return {"success": False, "error": str(e)}

    async def collect_app_distribution(self) -> Dict[str, Any]:
        """采集应用使用分布数据"""
        try:
            import subprocess

            url = f"{self.config.openrouter_base_url}/stats/app-usage"
            logger.info(f"Collecting app distribution from: {url}")

            result = subprocess.run(
                ['curl', '-sL', '--compressed', '--max-time', str(self.config.request_timeout),
                 '-H', 'User-Agent: Mozilla/5.0',
                 '-H', 'Accept: application/json',
                 url],
                capture_output=True, text=True, timeout=self.config.request_timeout + 10,
                encoding='utf-8', errors='ignore'
            )

            if result.returncode != 0:
                return {"success": False, "error": f"curl failed: {result.stderr}"}

            data = json.loads(result.stdout)
            await self._store_app_distribution(data)

            return {"success": True, "data": data}

        except Exception as e:
            logger.error(f"Failed to collect app distribution: {e}")
            return {"success": False, "error": str(e)}

    async def collect_model_list(self) -> Dict[str, Any]:
        """采集模型列表"""
        try:
            import subprocess

            url = f"{self.config.openrouter_base_url}/models"
            logger.info(f"Collecting model list from: {url}")

            result = subprocess.run(
                ['curl', '-sL', '--compressed', '--max-time', str(self.config.request_timeout),
                 '-H', 'User-Agent: Mozilla/5.0',
                 '-H', 'Accept: application/json',
                 url],
                capture_output=True, text=True, timeout=self.config.request_timeout + 10,
                encoding='utf-8', errors='ignore'
            )

            if result.returncode != 0:
                return {"success": False, "error": f"curl failed: {result.stderr}"}

            data = json.loads(result.stdout)
            await self._store_model_metadata(data)

            return {"success": True, "data": data}

        except Exception as e:
            logger.error(f"Failed to collect model list: {e}")
            return {"success": False, "error": str(e)}

    async def _store_model_usage(self, data: Dict):
        """存储模型使用量到数据库"""
        if not self.db:
            await self.init()

        now = datetime.utcnow().isoformat()
        records = data.get('data', []) if isinstance(data, dict) else data

        for record in records:
            model_slug = record.get('model_slug', record.get('model', ''))
            app_name = record.get('app_name', record.get('app', ''))

            await self.db.execute('''
                INSERT OR REPLACE INTO model_usage_daily
                (time, model_slug, app_name, prompt_tokens, completion_tokens, total_tokens, requests)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
                (
                    now,
                    model_slug,
                    app_name,
                    record.get('prompt_tokens', 0),
                    record.get('completion_tokens', 0),
                    record.get('total_tokens', 0),
                    record.get('requests', 0)
                )
            )

        await self.db.commit()
        logger.info(f"Stored {len(records)} model usage records")

    async def _store_app_distribution(self, data: Dict):
        """存储应用使用分布到数据库"""
        if not self.db:
            await self.init()

        now = datetime.utcnow().isoformat()
        records = data.get('data', []) if isinstance(data, dict) else data

        for record in records:
            app_name = record.get('app_name', record.get('app', ''))
            model_slug = record.get('model_slug', record.get('model', ''))
            token_share = record.get('token_share', record.get('share', 0))
            total_tokens = record.get('total_tokens', record.get('tokens', 0))

            await self.db.execute('''
                INSERT OR REPLACE INTO app_distribution
                (time, app_name, model_slug, token_share, total_tokens)
                VALUES (?, ?, ?, ?, ?)
            ''',
                (
                    now,
                    app_name,
                    model_slug,
                    token_share,
                    total_tokens
                )
            )

        await self.db.commit()
        logger.info(f"Stored {len(records)} app distribution records")

    async def _store_model_metadata(self, data: Dict):
        """存储模型元数据"""
        if not self.db:
            await self.init()

        models = data.get('data', []) if isinstance(data, dict) else data

        for model in models:
            model_slug = model.get('id', model.get('slug', ''))
            if not model_slug:
                continue

            pricing = model.get('pricing', {})
            prompt_price = pricing.get('prompt', 0) if isinstance(pricing, dict) else 0
            completion_price = pricing.get('completion', 0) if isinstance(pricing, dict) else 0

            await self.db.execute('''
                INSERT OR REPLACE INTO model_metadata
                (model_slug, display_name, provider, context_length, pricing_prompt, pricing_completion, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
                (
                    model_slug,
                    model.get('name', model.get('display_name', '')),
                    model.get('provider', ''),
                    model.get('context_length', 0),
                    float(prompt_price) if prompt_price else 0,
                    float(completion_price) if completion_price else 0,
                    datetime.utcnow().isoformat()
                )
            )

        await self.db.commit()
        logger.info(f"Stored {len(models)} model metadata records")
