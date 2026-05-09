"""
ORM 数据模型
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal


@dataclass
class ModelUsageDaily:
    """模型每日调用量"""
    time: datetime
    model_slug: str
    app_name: Optional[str]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    cache_hits: int = 0
    provider_name: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'time': self.time.isoformat() if self.time else None,
            'model_slug': self.model_slug,
            'app_name': self.app_name,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'requests': self.requests,
            'cache_hits': self.cache_hits,
            'provider_name': self.provider_name
        }

    @classmethod
    def from_row(cls, row: dict) -> 'ModelUsageDaily':
        return cls(
            time=row['time'],
            model_slug=row['model_slug'],
            app_name=row['app_name'],
            prompt_tokens=row['prompt_tokens'] or 0,
            completion_tokens=row['completion_tokens'] or 0,
            total_tokens=row['total_tokens'] or 0,
            requests=row['requests'] or 0,
            cache_hits=row['cache_hits'] or 0,
            provider_name=row['provider_name']
        )


@dataclass
class AppDistribution:
    """应用使用分布"""
    time: datetime
    app_name: str
    model_slug: str
    token_share: Optional[Decimal] = None
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return {
            'time': self.time.isoformat() if self.time else None,
            'app_name': self.app_name,
            'model_slug': self.model_slug,
            'token_share': float(self.token_share) if self.token_share else None,
            'total_tokens': self.total_tokens
        }

    @classmethod
    def from_row(cls, row: dict) -> 'AppDistribution':
        return cls(
            time=row['time'],
            app_name=row['app_name'],
            model_slug=row['model_slug'],
            token_share=row['token_share'],
            total_tokens=row['total_tokens'] or 0
        )


@dataclass
class ModelMetadata:
    """模型元数据"""
    model_slug: str
    display_name: Optional[str] = None
    provider: Optional[str] = None
    context_length: Optional[int] = None
    pricing_prompt: Optional[Decimal] = None
    pricing_completion: Optional[Decimal] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            'model_slug': self.model_slug,
            'display_name': self.display_name,
            'provider': self.provider,
            'context_length': self.context_length,
            'pricing_prompt': float(self.pricing_prompt) if self.pricing_prompt else None,
            'pricing_completion': float(self.pricing_completion) if self.pricing_completion else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_row(cls, row: dict) -> 'ModelMetadata':
        return cls(
            model_slug=row['model_slug'],
            display_name=row['display_name'],
            provider=row['provider'],
            context_length=row['context_length'],
            pricing_prompt=row['pricing_prompt'],
            pricing_completion=row['pricing_completion'],
            updated_at=row['updated_at']
        )


@dataclass
class AnomalyAlert:
    """异常告警"""
    id: Optional[int] = None
    time: Optional[datetime] = None
    model_slug: Optional[str] = None
    app_name: Optional[str] = None
    anomaly_type: Optional[str] = None  # 'spike', 'drop', 'zero', 'pattern_change'
    severity: Optional[str] = None  # 'low', 'medium', 'high'
    details: Optional[dict] = None
    acknowledged: bool = False

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'time': self.time.isoformat() if self.time else None,
            'model_slug': self.model_slug,
            'app_name': self.app_name,
            'anomaly_type': self.anomaly_type,
            'severity': self.severity,
            'details': self.details,
            'acknowledged': self.acknowledged
        }

    @classmethod
    def from_row(cls, row: dict) -> 'AnomalyAlert':
        return cls(
            id=row['id'],
            time=row['time'],
            model_slug=row['model_slug'],
            app_name=row['app_name'],
            anomaly_type=row['anomaly_type'],
            severity=row['severity'],
            details=row['details'],
            acknowledged=row['acknowledged']
        )


@dataclass
class OpenRouterApp:
    """OpenRouter 应用信息"""
    slug: str
    name: str = ""
    description: str = ""
    url: str = ""
    icon_url: str = ""
    category: str = ""
    website: str = ""
    usage_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'url': self.url,
            'icon_url': self.icon_url,
            'category': self.category,
            'website': self.website,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_row(cls, row: dict) -> 'OpenRouterApp':
        import json
        raw_data = None
        if row.get('raw_data'):
            try:
                raw_data = json.loads(row['raw_data']) if isinstance(row['raw_data'], str) else row['raw_data']
            except:
                pass

        return cls(
            slug=row['slug'],
            name=row.get('name', ''),
            description=row.get('description', ''),
            url=row.get('url', ''),
            icon_url=row.get('icon_url', ''),
            category=row.get('category', ''),
            website=row.get('website', ''),
            usage_count=row.get('usage_count', 0),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None,
            raw_data=raw_data
        )
