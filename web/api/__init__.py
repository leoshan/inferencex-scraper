"""
API Server - FastAPI 后端服务
"""

from .main import app
from .routers import trends, apps, alerts

__all__ = ['app']
