"""
应用数据 API 路由 (SQLite 版本)
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd

from data import get_db_connection
from analysis import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()


@router.get("")
async def list_apps(
    limit: int = Query(default=20, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    sort_by: str = Query(default="usage_count", pattern="^(usage_count|name|updated_at)$")
):
    """获取应用列表（从 openrouter_apps 表）"""
    db = await get_db_connection()

    # 构建查询
    query = '''
        SELECT slug, name, description, url, icon_url, category, website, usage_count, created_at, updated_at
        FROM openrouter_apps
        WHERE 1=1
    '''
    params = []

    # 分类过滤
    if category:
        query += ' AND category = ?'
        params.append(category)

    # 搜索过滤
    if search:
        query += ' AND (name LIKE ? OR description LIKE ? OR slug LIKE ?)'
        search_pattern = f'%{search}%'
        params.extend([search_pattern, search_pattern, search_pattern])

    # 排序
    if sort_by == 'usage_count':
        query += ' ORDER BY usage_count DESC'
    elif sort_by == 'name':
        query += ' ORDER BY name ASC'
    elif sort_by == 'updated_at':
        query += ' ORDER BY updated_at DESC'

    # 限制数量
    query += ' LIMIT ?'
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    # 获取总数
    count_query = 'SELECT COUNT(*) FROM openrouter_apps'
    count_cursor = await db.execute(count_query)
    total = (await count_cursor.fetchone())[0]

    return {
        'apps': [dict(r) for r in rows],
        'count': len(rows),
        'total': total
    }


@router.get("/categories")
async def get_categories():
    """获取所有应用分类"""
    db = await get_db_connection()

    cursor = await db.execute('''
        SELECT category, COUNT(*) as count
        FROM openrouter_apps
        WHERE category IS NOT NULL AND category != ''
        GROUP BY category
        ORDER BY count DESC
    ''')
    rows = await cursor.fetchall()

    return {
        'categories': [dict(r) for r in rows]
    }


@router.get("/distribution")
async def get_app_distribution(
    date: Optional[datetime] = Query(default=None),
    top_n: int = Query(default=20, ge=1, le=100)
):
    """获取应用使用分布"""
    db = await get_db_connection()

    # 如果没有指定日期，获取最新的数据日期
    if date is None:
        cursor = await db.execute('SELECT MAX(time) FROM app_distribution')
        row = await cursor.fetchone()
        if row and row[0]:
            date = datetime.fromisoformat(row[0])
        else:
            return {'distribution': {}, 'message': 'No data available'}

    cursor = await db.execute('''
        SELECT app_name, model_slug, total_tokens, token_share
        FROM app_distribution
        WHERE date(time) = date(?)
        ORDER BY total_tokens DESC
        LIMIT ?
    ''', (date.isoformat(), top_n))
    rows = await cursor.fetchall()

    df = pd.DataFrame([dict(r) for r in rows])

    if len(df) == 0:
        # 如果指定日期没数据，尝试获取所有数据
        cursor = await db.execute('''
            SELECT app_name, model_slug, total_tokens, token_share
            FROM app_distribution
            ORDER BY total_tokens DESC
            LIMIT ?
        ''', (top_n,))
        rows = await cursor.fetchall()
        df = pd.DataFrame([dict(r) for r in rows])

    if len(df) == 0:
        return {'distribution': {}, 'message': 'No data for specified date'}

    result = await analysis_service.analyze_app_distribution(df)

    return result


@router.get("/detail/{app_slug}")
async def get_app_detail(app_slug: str):
    """获取应用详情"""
    db = await get_db_connection()

    cursor = await db.execute('''
        SELECT slug, name, description, url, icon_url, category, website, usage_count, created_at, updated_at
        FROM openrouter_apps
        WHERE slug = ?
    ''', (app_slug,))
    row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"App '{app_slug}' not found")

    return dict(row)


@router.get("/detail/{app_name}/models")
async def get_app_models(
    app_name: str,
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """获取应用使用的模型分布"""
    db = await get_db_connection()

    # 从 app_distribution 表查询
    cursor = await db.execute('''
        SELECT model_slug, SUM(total_tokens) as total_tokens,
               token_share
        FROM app_distribution
        WHERE app_name = ? AND model_slug != '_summary_'
        GROUP BY model_slug
        ORDER BY total_tokens DESC
    ''', (app_name,))
    rows = await cursor.fetchall()

    return {
        'app_name': app_name,
        'models': [dict(r) for r in rows],
        'date_range': {'start': start_date.isoformat() if start_date else None, 'end': end_date.isoformat() if end_date else None}
    }
