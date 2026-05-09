import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Select, DatePicker, Button, Space, Spin, Typography, Row, Col, Table, Tag, message } from 'antd'
import { ReloadOutlined, DownloadOutlined, PlusOutlined, CloseOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import dayjs from 'dayjs'
import { comparisonApi } from '@/api'
import type { RankingItem } from '@/types'

const { Title } = Typography
const { RangePicker } = DatePicker

// 常用模型列表
const popularModels = [
  'anthropic/claude-3.5-sonnet',
  'anthropic/claude-3-opus',
  'openai/gpt-4o',
  'openai/gpt-4-turbo',
  'google/gemini-pro-1.5',
  'meta-llama/llama-3.1-70b-instruct',
  'deepseek/deepseek-chat',
  'qwen/qwen-2.5-72b-instruct',
  'mistralai/mistral-large',
  'cohere/command-r-plus',
]

export default function ModelComparison() {
  const [selectedModels, setSelectedModels] = useState<string[]>([
    'anthropic/claude-3.5-sonnet',
    'openai/gpt-4o',
  ])
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs]>([
    dayjs().subtract(30, 'day'),
    dayjs(),
  ])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['modelComparison', selectedModels, dateRange[0].toISOString(), dateRange[1].toISOString()],
    queryFn: () => comparisonApi.compareModels(
      selectedModels,
      dateRange[0].toISOString(),
      dateRange[1].toISOString()
    ),
    enabled: selectedModels.length > 0,
  })

  const { data: heatmapData, isLoading: heatmapLoading } = useQuery({
    queryKey: ['heatmap', dateRange[0].toISOString(), dateRange[1].toISOString()],
    queryFn: () => comparisonApi.getHeatmap(
      dateRange[0].toISOString(),
      dateRange[1].toISOString(),
      15
    ),
  })

  const handleExport = () => {
    if (!data) return
    const csv = selectedModels.map(m => {
      const metrics = data.metrics[m]
      return `${m},${metrics.total_tokens},${metrics.requests},${metrics.growth_rate}%`
    }).join('\n')
    const blob = new Blob([`model,total_tokens,requests,growth_rate\n${csv}`], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'model_comparison.csv'
    a.click()
    message.success('导出成功')
  }

  // 指标对比表列
  const metricColumns = [
    { title: '模型', dataIndex: 'model', key: 'model', width: 250 },
    { title: '总 Tokens (B)', dataIndex: 'total_tokens', key: 'total_tokens', render: (v: number) => v ? `${(v / 1e9).toFixed(2)}B` : '-' },
    { title: '总请求数 (B)', dataIndex: 'requests', key: 'requests', render: (v: number) => v ? `${(v / 1e9).toFixed(2)}B` : '-' },
    { title: '平均 Tokens/请求', dataIndex: 'avg_tokens_per_request', key: 'avg' },
    { title: '增长率', dataIndex: 'growth_rate', key: 'growth_rate', render: (v: number) => (
      <Tag color={v > 0 ? 'green' : v < 0 ? 'red' : 'blue'}>{v > 0 ? '+' : ''}{v?.toFixed(2)}%</Tag>
    )},
    { title: '市场份额', dataIndex: 'market_share', key: 'market_share', render: (v: number) => `${v?.toFixed(2)}%` },
  ]

  // 指标表数据
  const metricData = selectedModels.map((model, idx) => ({
    key: idx,
    model: model.split('/').pop(),
    ...data?.metrics[model],
  }))

  // 趋势对比图配置
  const trendOption = data?.trend_comparison ? {
    tooltip: { trigger: 'axis' },
    legend: { data: data.trend_comparison.series.map((s: any) => s.name.split('/').pop()), top: 30 },
    grid: { left: '3%', right: '4%', bottom: '3%', top: 80, containLabel: true },
    xAxis: { type: 'category', data: data.trend_comparison.times, boundaryGap: false },
    yAxis: { type: 'value', name: 'Tokens (B)', axisLabel: { formatter: (v: number) => `${(v / 1e9).toFixed(2)}B` } },
    series: data.trend_comparison.series.map((s: any) => ({
      name: s.name.split('/').pop(),
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
    })),
  } : {}

  // 热力图配置
  const heatmapOption = heatmapData?.models ? {
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        return `${heatmapData.models[params.data[1]]}<br/>${heatmapData.times[params.data[0]]}<br/>${(params.data[2] / 1e9).toFixed(2)}B tokens`
      }
    },
    grid: { left: '25%', right: '10%', bottom: '15%', top: '5%' },
    xAxis: { type: 'category', data: heatmapData.times, splitArea: { show: true } },
    yAxis: { type: 'category', data: heatmapData.models.map((m: string) => m.split('/').pop()), splitArea: { show: true } },
    visualMap: {
      min: 0,
      max: Math.max(...(heatmapData.data?.map((d: any) => d[2]) || [0])),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: { color: ['#f7fbff', '#08306b'] }
    },
    series: [{
      type: 'heatmap',
      data: heatmapData.data,
      label: { show: false },
    }]
  } : {}

  return (
    <div>
      <Title level={4}>模型对比分析</Title>

      {/* 筛选器 */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <RangePicker
            value={dateRange}
            onChange={(dates) => dates && setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs])}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
          <Button icon={<DownloadOutlined />} onClick={handleExport} disabled={!data}>导出 CSV</Button>
        </Space>

        {/* 模型选择 */}
        <div style={{ marginTop: 16 }}>
          <Space wrap>
            {selectedModels.map((model) => (
              <Tag
                key={model}
                closable
                onClose={() => setSelectedModels(selectedModels.filter(m => m !== model))}
              >
                {model.split('/').pop()}
              </Tag>
            ))}
            <Select
              style={{ width: 200 }}
              placeholder="添加模型"
              onChange={(value) => {
                if (!selectedModels.includes(value)) {
                  setSelectedModels([...selectedModels, value])
                }
              }}
              options={popularModels.filter(m => !selectedModels.includes(m)).map(m => ({ value: m, label: m.split('/').pop() }))}
              value={undefined}
            />
          </Space>
        </div>
      </Card>

      {isLoading && <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />}

      {data && (
        <>
          {/* 指标对比表 */}
          <Card title="指标对比" style={{ marginBottom: 16 }}>
            <Table
              dataSource={metricData}
              columns={metricColumns}
              pagination={false}
              size="small"
            />
          </Card>

          {/* 趋势对比图 */}
          <Card title="调用量趋势对比" style={{ marginBottom: 16 }}>
            <ReactECharts option={trendOption} style={{ height: 400 }} />
          </Card>

          {/* 排名 */}
          {data.ranking && data.ranking.length > 0 && (
            <Card title="模型排名" style={{ marginBottom: 16 }}>
              <Row gutter={[16, 16]}>
                {data.ranking.map((item: RankingItem, idx: number) => (
                  <Col xs={24} sm={12} md={8} lg={6} key={idx}>
                    <Card size="small">
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 24, fontWeight: 'bold', color: idx < 3 ? '#1890ff' : '#666' }}>
                          #{item.rank}
                        </span>
                        <div>
                          <div style={{ fontWeight: 500 }}>{item.model_slug.split('/').pop()}</div>
                          <div style={{ color: '#888', fontSize: 12 }}>
                            {(item.value / 1e9).toFixed(2)}B tokens
                          </div>
                        </div>
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Card>
          )}
        </>
      )}

      {/* 热力图 */}
      <Card title="调用量热力图 (Top 15 模型)">
        {heatmapLoading ? <Spin /> : <ReactECharts option={heatmapOption} style={{ height: 500 }} />}
      </Card>
    </div>
  )
}