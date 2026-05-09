import axios from 'axios'
import type {
  ModelTrendResponse,
  AppTrendResponse,
  Alert,
  AlertSummary,
  AppInfo,
  TrendSummary,
  ComparisonResponse,
  RankingsResponse,
  HeatmapResponse,
  ModelMetricsDetail,
  CategoryTrendsResponse,
  CategoryTimeSeriesResponse,
} from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 趋势 API
export const trendsApi = {
  // 获取模型趋势
  getModelTrend: async (
    modelSlug: string,
    startDate?: string,
    endDate?: string,
    metric: string = 'total_tokens'
  ): Promise<ModelTrendResponse> => {
    const params: any = { metric }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get(`/trends/models/${modelSlug}`, { params })
    return data
  },

  // 获取应用趋势
  getAppTrend: async (
    appName: string,
    startDate?: string,
    endDate?: string
  ): Promise<AppTrendResponse> => {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get(`/trends/apps/${appName}`, { params })
    return data
  },

  // 多模型对比
  compareModels: async (
    modelSlugs: string[],
    startDate?: string,
    endDate?: string
  ): Promise<any> => {
    const params: any = { model_slugs: modelSlugs }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get('/trends/compare', { params })
    return data
  },

  // 趋势摘要
  getSummary: async (startDate?: string, endDate?: string): Promise<TrendSummary> => {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get('/trends/summary', { params })
    return data
  },

  // 获取排名
  getRankings: async (
    metric: string = 'total_tokens',
    period: string = 'week',
    limit: number = 20,
    startDate?: string,
    endDate?: string
  ): Promise<RankingsResponse> => {
    const params: any = { metric, period, limit }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get('/trends/rankings', { params })
    return data
  },

  // 获取场景分类趋势
  getCategoryTrends: async (
    category?: string,
    startDate?: string,
    endDate?: string
  ): Promise<CategoryTrendsResponse | CategoryTimeSeriesResponse> => {
    const params: any = {}
    if (category) params.category = category
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get('/trends/category-trends', { params })
    return data
  },
}

// 应用 API
export const appsApi = {
  // 应用列表
  list: async (params?: {
    limit?: number
    category?: string
    search?: string
    sort_by?: string
  }): Promise<{ apps: AppInfo[]; count: number; total: number }> => {
    const { data } = await api.get('/apps', { params })
    return data
  },

  // 应用分类列表
  getCategories: async (): Promise<{ categories: { category: string; count: number }[] }> => {
    const { data } = await api.get('/apps/categories')
    return data
  },

  // 应用详情
  getDetail: async (appSlug: string): Promise<AppInfo> => {
    const { data } = await api.get(`/apps/by-slug/${appSlug}`)
    return data
  },

  // 应用分布
  getDistribution: async (date?: string, topN: number = 20): Promise<any> => {
    const params: any = { top_n: topN }
    if (date) params.date = date
    const { data } = await api.get('/apps/distribution', { params })
    return data
  },

  // 应用使用的模型
  getAppModels: async (
    appName: string,
    startDate?: string,
    endDate?: string
  ): Promise<any> => {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get(`/apps/by-slug/${appName}/models`, { params })
    return data
  },
}

// 告警 API
export const alertsApi = {
  // 告警列表
  list: async (params?: {
    severity?: string
    acknowledged?: boolean
    start_date?: string
    end_date?: string
    limit?: number
  }): Promise<{ alerts: Alert[]; count: number }> => {
    const { data } = await api.get('/alerts', { params })
    return data
  },

  // 确认告警
  acknowledge: async (alertId: number): Promise<{ success: boolean }> => {
    const { data } = await api.post(`/alerts/${alertId}/acknowledge`)
    return data
  },

  // 批量确认
  batchAcknowledge: async (alertIds: number[]): Promise<{ success: boolean }> => {
    const { data } = await api.post('/alerts/batch-acknowledge', alertIds)
    return data
  },

  // 告警摘要
  getSummary: async (startDate?: string, endDate?: string): Promise<AlertSummary> => {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get('/alerts/summary', { params })
    return data
  },
}

// 对比 API
export const comparisonApi = {
  // 多模型对比
  compareModels: async (
    modelSlugs: string[],
    startDate?: string,
    endDate?: string
  ): Promise<ComparisonResponse> => {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.post('/comparison/models', modelSlugs, { params })
    return data
  },

  // 获取热力图
  getHeatmap: async (
    startDate?: string,
    endDate?: string,
    topN: number = 20
  ): Promise<HeatmapResponse> => {
    const params: any = { top_n: topN }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get('/comparison/heatmap', { params })
    return data
  },

  // 获取模型指标
  getModelMetrics: async (
    modelSlug: string,
    startDate?: string,
    endDate?: string
  ): Promise<ModelMetricsDetail> => {
    const params: any = {}
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get(`/comparison/metrics/${modelSlug}`, { params })
    return data
  },

  // 获取模型 Top 应用
  getModelTopApps: async (
    modelSlug: string,
    limit: number = 10,
    startDate?: string,
    endDate?: string
  ): Promise<{ model_slug: string; top_apps: { app_name: string; total_tokens: number; total_requests: number }[] }> => {
    const params: any = { limit }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    const { data } = await api.get(`/comparison/top-apps/${modelSlug}`, { params })
    return data
  },
}

export default api
