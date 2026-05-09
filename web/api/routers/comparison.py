"""
模型对比分析 API 路由
"""

from fastapi import APIRouter, Query, HTTPException, Body
from datetime import datetime, timedelta
from typing import Optional, List

from data import get_db_connection
from analysis import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()


@router.post("/models")
async def compare_models(
    model_slugs: List[str] = Body(...),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """多模型对比分析

    Args:
        model_slugs: 要对比的模型列表
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        对比分析结果，包含指标对比、趋势对比、排名
    """
    if not model_slugs:
        raise HTTPException(status_code=400, detail="model_slugs is required")

    if len(model_slugs) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 models can be compared at once")

    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()
    placeholders = ','.join(['?' for _ in model_slugs])
    cursor = await db.execute(f'''
        SELECT time, model_slug, app_name, total_tokens, requests
        FROM model_usage_daily
        WHERE model_slug IN ({placeholders}) AND time >= ? AND time <= ?
        ORDER BY time ASC
    ''', (*model_slugs, start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    import pandas as pd
    df = pd.DataFrame([dict(r) for r in rows])

    result = await analysis_service.compare_models(model_slugs, df, start_date, end_date)

    return result


@router.get("/heatmap")
async def get_usage_heatmap(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    top_n: int = Query(default=20, ge=5, le=50)
):
    """调用量热力图 (时间 x 模型)

    Args:
        start_date: 开始日期
        end_date: 结束日期
        top_n: Top N 模型数量

    Returns:
        ECharts heatmap 格式数据
    """
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()
    cursor = await db.execute('''
        SELECT time, model_slug, app_name, total_tokens, requests
        FROM model_usage_daily
        WHERE time >= ? AND time <= ?
        ORDER BY time ASC
    ''', (start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    import pandas as pd
    df = pd.DataFrame([dict(r) for r in rows])

    result = await analysis_service.get_usage_heatmap(df, top_n, start_date, end_date)

    return result


@router.get("/metrics/{model_slug}")
async def get_model_metrics(
    model_slug: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """获取模型详细指标

    Args:
        model_slug: 模型标识
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        模型详细指标数据
    """
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()
    cursor = await db.execute('''
        SELECT time, model_slug, app_name, total_tokens, requests
        FROM model_usage_daily
        WHERE model_slug = ? AND time >= ? AND time <= ?
        ORDER BY time ASC
    ''', (model_slug, start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    import pandas as pd
    df = pd.DataFrame([dict(r) for r in rows])

    result = await analysis_service.get_model_metrics(model_slug, df)

    return result


@router.get("/top-apps/{model_slug}")
async def get_model_top_apps(
    model_slug: str,
    limit: int = Query(default=10, ge=1, le=50),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """获取模型的 Top 应用

    Args:
        model_slug: 模型标识
        limit: 返回数量
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        Top 应用列表
    """
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()
    cursor = await db.execute('''
        SELECT app_name, SUM(total_tokens) as total_tokens, SUM(requests) as requests
        FROM model_usage_daily
        WHERE model_slug = ? AND time >= ? AND time <= ?
        GROUP BY app_name
        ORDER BY total_tokens DESC
        LIMIT ?
    ''', (model_slug, start_date.isoformat(), end_date.isoformat(), limit))
    rows = await cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            'app_name': row['app_name'],
            'total_tokens': row['total_tokens'],
            'total_requests': row['requests']
        })

    return {'model_slug': model_slug, 'top_apps': result}