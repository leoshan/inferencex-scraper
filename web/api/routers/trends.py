"""
趋势数据 API 路由 (SQLite 版本)
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, List
import pandas as pd
import json

from data import get_db_connection
from analysis import AnalysisService

router = APIRouter()
analysis_service = AnalysisService()


@router.get("/models/{model_slug}")
async def get_model_trend(
    model_slug: str,
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    metric: str = Query(default="total_tokens", regex="^(total_tokens|requests|prompt_tokens|completion_tokens)$")
):
    """获取单个模型的调用量趋势"""
    db = await get_db_connection()

    # 如果没有指定日期范围，自动检测数据范围
    if start_date is None or end_date is None:
        cursor = await db.execute('SELECT MIN(time), MAX(time) FROM model_usage_daily')
        row = await cursor.fetchone()
        if row and row[0] and row[1]:
            max_time = datetime.fromisoformat(row[1])
            if start_date is None:
                start_date = max_time - timedelta(days=30)
            if end_date is None:
                end_date = max_time

    cursor = await db.execute('''
        SELECT time, model_slug, app_name, prompt_tokens, completion_tokens,
               total_tokens, requests, cache_hits, provider_name
        FROM model_usage_daily
        WHERE model_slug = ? AND time >= ? AND time <= ?
        ORDER BY time ASC
    ''', (model_slug, start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for model: {model_slug}")

    df = pd.DataFrame([dict(r) for r in rows])
    result = await analysis_service.analyze_model_trend(df, model_slug)

    return result


@router.get("/apps/{app_name}")
async def get_app_trend(
    app_name: str,
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """获取单个应用的使用趋势"""
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()
    cursor = await db.execute('''
        SELECT time, model_slug, app_name, total_tokens
        FROM model_usage_daily
        WHERE app_name = ? AND time >= ? AND time <= ?
        ORDER BY time ASC
    ''', (app_name, start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for app: {app_name}")

    df = pd.DataFrame([dict(r) for r in rows])

    # 按时间聚合
    daily = df.groupby('time')['total_tokens'].sum().reset_index()
    trend_result = analysis_service.trend_analyzer.analyze_trend(daily)

    return {
        'app_name': app_name,
        'trend': trend_result,
        'model_breakdown': df.groupby('model_slug')['total_tokens'].sum().to_dict()
    }


@router.get("/compare")
async def compare_models(
    model_slugs: List[str] = Query(...),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """多模型对比"""
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()
    placeholders = ','.join(['?' for _ in model_slugs])
    cursor = await db.execute(f'''
        SELECT time, model_slug, total_tokens, requests
        FROM model_usage_daily
        WHERE model_slug IN ({placeholders}) AND time >= ? AND time <= ?
        ORDER BY time ASC
    ''', (*model_slugs, start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No data found for specified models")

    df = pd.DataFrame([dict(r) for r in rows])

    # 按模型分组
    comparison = {}
    for model_slug in model_slugs:
        model_df = df[df['model_slug'] == model_slug]
        if len(model_df) > 0:
            daily = model_df.groupby('time')['total_tokens'].sum().reset_index()
            trend = analysis_service.trend_analyzer.analyze_trend(daily)
            comparison[model_slug] = trend

    return {
        'comparison': comparison,
        'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()}
    }


@router.get("/summary")
async def get_trend_summary(
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """获取趋势摘要"""
    db = await get_db_connection()

    # 如果没有指定日期范围，自动检测数据范围
    if start_date is None or end_date is None:
        cursor = await db.execute('SELECT MIN(time), MAX(time) FROM model_usage_daily')
        row = await cursor.fetchone()
        if row and row[0] and row[1]:
            max_time = datetime.fromisoformat(row[1])
            if start_date is None:
                start_date = max_time - timedelta(days=30)
            if end_date is None:
                end_date = max_time

    cursor = await db.execute('''
        SELECT time, model_slug, app_name, total_tokens, requests
        FROM model_usage_daily
        WHERE time >= ? AND time <= ?
    ''', (start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    df = pd.DataFrame([dict(r) for r in rows])
    summary = await analysis_service.get_trend_summary(df)

    return summary


@router.get("/rankings")
async def get_rankings(
    metric: str = Query(default="total_tokens", regex="^(total_tokens|requests|growth_rate)$"),
    period: str = Query(default="week", regex="^(day|week|month)$"),
    limit: int = Query(default=20, ge=1, le=100),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """获取模型排名"""
    db = await get_db_connection()

    # 如果没有指定日期范围，自动检测数据范围
    if start_date is None or end_date is None:
        cursor = await db.execute('SELECT MIN(time), MAX(time) FROM model_usage_daily')
        row = await cursor.fetchone()
        if row and row[0] and row[1]:
            min_time = datetime.fromisoformat(row[0])
            max_time = datetime.fromisoformat(row[1])
            if start_date is None:
                # 根据period计算开始日期
                if period == 'day':
                    start_date = max_time - timedelta(days=1)
                elif period == 'week':
                    start_date = max_time - timedelta(days=7)
                else:  # month
                    start_date = max_time - timedelta(days=30)
            if end_date is None:
                end_date = max_time

    cursor = await db.execute('''
        SELECT time, model_slug, app_name, total_tokens, requests
        FROM model_usage_daily
        WHERE time >= ? AND time <= ?
    ''', (start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    df = pd.DataFrame([dict(r) for r in rows])
    rankings = await analysis_service.get_model_rankings(df, metric, period, limit)

    return {'rankings': rankings, 'metric': metric, 'period': period}


@router.get("/category-trends")
async def get_category_trends(
    category: Optional[str] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """获取场景分类趋势"""
    db = await get_db_connection()

    # 如果没有指定日期范围，自动检测数据范围
    if start_date is None or end_date is None:
        cursor = await db.execute('SELECT MIN(time), MAX(time) FROM model_usage_daily')
        row = await cursor.fetchone()
        if row and row[0] and row[1]:
            max_time = datetime.fromisoformat(row[1])
            if start_date is None:
                start_date = max_time - timedelta(days=30)
            if end_date is None:
                end_date = max_time

    cursor = await db.execute('''
        SELECT time, model_slug, app_name, total_tokens, requests
        FROM model_usage_daily
        WHERE time >= ? AND time <= ?
    ''', (start_date.isoformat(), end_date.isoformat()))
    rows = await cursor.fetchall()

    df = pd.DataFrame([dict(r) for r in rows])

    if category:
        # 返回指定场景的时间序列
        result = await analysis_service.get_category_time_series(df, category)
    else:
        # 返回所有场景的分析
        result = await analysis_service.get_category_analysis(df, start_date, end_date)

    return result
