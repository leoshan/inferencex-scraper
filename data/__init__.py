"""
数据模块 - 数据库连接和数据模型

包含:
- 数据库连接管理
- ORM 数据模型
- 数据文件目录结构
"""

import os
import sqlite3
import aiosqlite
from pathlib import Path
from typing import Optional

# 数据库路径
DB_DIR = Path(__file__).parent / 'db'
DATABASE_PATH = os.getenv('DATABASE_PATH', str(DB_DIR / 'trend_tracker.db'))

_db: Optional[aiosqlite.Connection] = None


async def get_db_connection() -> aiosqlite.Connection:
    """获取数据库连接"""
    global _db
    if _db is None:
        # 确保 db 目录存在
        DB_DIR.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(DATABASE_PATH)
        _db.row_factory = sqlite3.Row
    return _db


async def init_database():
    """初始化数据库表结构"""
    db = await get_db_connection()

    # 模型每日调用量表
    await db.execute('''
        CREATE TABLE IF NOT EXISTS model_usage_daily (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            model_slug TEXT NOT NULL,
            app_name TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            requests INTEGER DEFAULT 0,
            cache_hits INTEGER DEFAULT 0,
            provider_name TEXT,
            UNIQUE(time, model_slug, app_name)
        )
    ''')

    # 应用使用分布表
    await db.execute('''
        CREATE TABLE IF NOT EXISTS app_distribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            app_name TEXT NOT NULL,
            model_slug TEXT NOT NULL,
            token_share REAL,
            total_tokens INTEGER,
            UNIQUE(time, app_name, model_slug)
        )
    ''')

    # 模型元数据表
    await db.execute('''
        CREATE TABLE IF NOT EXISTS model_metadata (
            model_slug TEXT PRIMARY KEY,
            display_name TEXT,
            provider TEXT,
            context_length INTEGER,
            pricing_prompt REAL,
            pricing_completion REAL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 异常告警表
    await db.execute('''
        CREATE TABLE IF NOT EXISTS anomaly_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT NOT NULL,
            model_slug TEXT,
            app_name TEXT,
            anomaly_type TEXT,
            severity TEXT,
            details TEXT,
            acknowledged INTEGER DEFAULT 0
        )
    ''')

    # OpenRouter 应用表
    await db.execute('''
        CREATE TABLE IF NOT EXISTS openrouter_apps (
            slug TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            url TEXT,
            icon_url TEXT,
            category TEXT,
            website TEXT,
            usage_count INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            raw_data TEXT
        )
    ''')

    # 创建索引
    await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_model ON model_usage_daily (model_slug, time)')
    await db.execute('CREATE INDEX IF NOT EXISTS idx_usage_app ON model_usage_daily (app_name, time)')
    await db.execute('CREATE INDEX IF NOT EXISTS idx_alerts_time ON anomaly_alerts (time)')
    await db.execute('CREATE INDEX IF NOT EXISTS idx_apps_category ON openrouter_apps (category)')
    await db.execute('CREATE INDEX IF NOT EXISTS idx_apps_usage ON openrouter_apps (usage_count)')

    await db.commit()
    print("SQLite database initialized successfully")


async def close_db_connection():
    """关闭数据库连接"""
    global _db
    if _db:
        await _db.close()
        _db = None


# 导入数据模型
from .models import ModelUsageDaily, AppDistribution, ModelMetadata, AnomalyAlert, OpenRouterApp

# 导入数据存储管理器
from .storage import DataStorage, get_storage

__all__ = [
    'get_db_connection',
    'init_database',
    'close_db_connection',
    'ModelUsageDaily',
    'AppDistribution',
    'ModelMetadata',
    'AnomalyAlert',
    'OpenRouterApp',
    'DATABASE_PATH',
    'DataStorage',
    'get_storage',
]