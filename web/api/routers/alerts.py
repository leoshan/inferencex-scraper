"""
异常告警 API 路由 (SQLite 版本)
"""

from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, List
import json

from data import get_db_connection
from data import AnomalyAlert

router = APIRouter()


@router.get("")
async def get_alerts(
    severity: Optional[str] = Query(default=None, regex="^(low|medium|high)$"),
    acknowledged: Optional[bool] = Query(default=None),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200)
):
    """获取异常告警列表"""
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=7)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()

    query = 'SELECT id, time, model_slug, app_name, anomaly_type, severity, details, acknowledged FROM anomaly_alerts WHERE time >= ? AND time <= ?'
    params = [start_date.isoformat(), end_date.isoformat()]

    if severity:
        query += ' AND severity = ?'
        params.append(severity)

    if acknowledged is not None:
        query += ' AND acknowledged = ?'
        params.append(1 if acknowledged else 0)

    query += ' ORDER BY time DESC LIMIT ?'
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    alerts = []
    for r in rows:
        alert = dict(r)
        alert['acknowledged'] = bool(alert['acknowledged'])
        if alert['details']:
            alert['details'] = json.loads(alert['details'])
        alerts.append(alert)

    return {
        'alerts': alerts,
        'count': len(alerts),
        'filters': {
            'severity': severity,
            'acknowledged': acknowledged,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
    }


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """确认告警"""
    db = await get_db_connection()
    cursor = await db.execute('''
        UPDATE anomaly_alerts SET acknowledged = 1 WHERE id = ?
    ''', (alert_id,))

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Alert not found: {alert_id}")

    await db.commit()
    return {'success': True, 'alert_id': alert_id, 'acknowledged': True}


@router.post("/batch-acknowledge")
async def batch_acknowledge_alerts(alert_ids: List[int]):
    """批量确认告警"""
    db = await get_db_connection()
    placeholders = ','.join(['?' for _ in alert_ids])
    cursor = await db.execute(f'''
        UPDATE anomaly_alerts SET acknowledged = 1 WHERE id IN ({placeholders})
    ''', alert_ids)

    await db.commit()
    return {'success': True, 'updated_count': cursor.rowcount}


@router.get("/summary")
async def get_alert_summary(
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None)
):
    """获取告警摘要统计"""
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=7)
    if end_date is None:
        end_date = datetime.utcnow()

    db = await get_db_connection()

    # 按严重程度统计
    cursor = await db.execute('''
        SELECT severity, COUNT(*) as count
        FROM anomaly_alerts
        WHERE time >= ? AND time <= ?
        GROUP BY severity
    ''', (start_date.isoformat(), end_date.isoformat()))
    severity_rows = await cursor.fetchall()
    severity_stats = {r['severity']: r['count'] for r in severity_rows}

    # 按类型统计
    cursor = await db.execute('''
        SELECT anomaly_type, COUNT(*) as count
        FROM anomaly_alerts
        WHERE time >= ? AND time <= ?
        GROUP BY anomaly_type
    ''', (start_date.isoformat(), end_date.isoformat()))
    type_rows = await cursor.fetchall()
    type_stats = {r['anomaly_type']: r['count'] for r in type_rows}

    # 未确认数量
    cursor = await db.execute('''
        SELECT COUNT(*) as count
        FROM anomaly_alerts
        WHERE time >= ? AND time <= ? AND acknowledged = 0
    ''', (start_date.isoformat(), end_date.isoformat()))
    unacknowledged = (await cursor.fetchone())['count']

    return {
        'by_severity': severity_stats,
        'by_type': type_stats,
        'unacknowledged_count': unacknowledged,
        'date_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()}
    }
