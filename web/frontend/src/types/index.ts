// API 类型定义

export interface ModelUsage {
  time: string
  model_slug: string
  app_name: string | null
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  requests: number
  cache_hits: number
  provider_name: string | null
}

export interface TrendResult {
  growth_rate: number
  trend: 'increasing' | 'decreasing' | 'stable'
  ma_7: number | null
  ma_30: number | null
  has_seasonality: boolean
  weekly_autocorr: number | null
  data: ModelUsage[]
}

export interface Anomaly {
  time: string
  value: number
  anomaly_type: 'spike' | 'drop' | 'zero' | 'pattern_change'
  severity: 'low' | 'medium' | 'high'
  z_score: number | null
  details: Record<string, any> | null
}

export interface ModelTrendResponse {
  model_slug: string
  trend: TrendResult
  anomalies: Anomaly[]
}

export interface AppTrendResponse {
  app_name: string
  trend: TrendResult
  model_breakdown: Record<string, number>
}

export interface Alert {
  id: number
  time: string
  model_slug: string | null
  app_name: string | null
  anomaly_type: string
  severity: string
  details: Record<string, any> | null
  acknowledged: boolean
}

export interface AlertSummary {
  by_severity: Record<string, number>
  by_type: Record<string, number>
  unacknowledged_count: number
  date_range: { start: string; end: string }
}

export interface AppInfo {
  app_name: string
  total_tokens: number
}

export interface TrendSummary {
  total_models: number
  total_apps: number
  total_tokens: number
  total_requests: number
  date_range: { start: string | null; end: string | null }
}

// 对比分析类型
export interface ModelMetrics {
  total_tokens: number
  requests: number
  avg_tokens_per_request: number
  growth_rate: number
  market_share: number
}

export interface ComparisonResponse {
  models: string[]
  metrics: Record<string, ModelMetrics>
  trend_comparison: {
    times: string[]
    series: { name: string; data: number[] }[]
  }
  ranking: RankingItem[]
}

export interface RankingItem {
  rank: number
  model_slug: string
  value: number
  growth_rate: number
  market_share: number
}

export interface RankingsResponse {
  rankings: RankingItem[]
  metric: string
  period: string
}

export interface HeatmapResponse {
  times: string[]
  models: string[]
  data: [number, number, number][]  // [x_index, y_index, value]
}

export interface ModelMetricsDetail {
  model_slug: string
  total_tokens: number
  total_requests: number
  avg_tokens_per_request: number
  market_share: number
  app_distribution: { app_name: string; tokens: number }[]
  time_range: { start: string; end: string } | null
}

// 场景分析类型
export interface CategoryResult {
  name: string
  total_tokens: number
  total_requests: number
  apps: string[]
  top_models: string[]
  growth_rate: number
}

export interface CategoryTrendsResponse {
  categories: CategoryResult[]
  distribution: { name: string; value: number; percentage?: number }[]
  total_tokens: number
  total_requests: number
}

export interface CategoryTimeSeriesResponse {
  times: string[]
  series: { name: string; data: number[] }[]
}
