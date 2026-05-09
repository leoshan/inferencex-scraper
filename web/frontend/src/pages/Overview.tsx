import { useQuery } from '@tanstack/react-query'
import { Card, Row, Col, Statistic, Spin, Alert, Typography, Table, Tag } from 'antd'
import {
  RiseOutlined,
  FallOutlined,
  MinusOutlined,
  AlertOutlined,
  BarChartOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import { trendsApi, alertsApi, appsApi } from '@/api'
import dayjs from 'dayjs'

const { Title } = Typography

export default function Overview() {
  // 获取趋势摘要
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['trendSummary'],
    queryFn: () => trendsApi.getSummary(
      dayjs().subtract(30, 'day').toISOString(),
      dayjs().toISOString()
    ),
  })

  // 获取告警摘要
  const { data: alertSummary, isLoading: alertLoading } = useQuery({
    queryKey: ['alertSummary'],
    queryFn: () => alertsApi.getSummary(
      dayjs().subtract(7, 'day').toISOString(),
      dayjs().toISOString()
    ),
  })

  // 获取应用统计
  const { data: appsData, isLoading: appsLoading } = useQuery({
    queryKey: ['appsOverview'],
    queryFn: () => appsApi.list({ limit: 10, sort_by: 'usage_count' }),
  })

  // 获取应用分类
  const { data: categoriesData } = useQuery({
    queryKey: ['appCategories'],
    queryFn: () => appsApi.getCategories(),
  })

  if (summaryLoading || alertLoading || appsLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  // 应用表格列
  const appColumns = [
    {
      title: '应用名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <a href={record.url} target="_blank" rel="noopener noreferrer">
          {name || record.slug}
        </a>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (cat: string) => cat ? <Tag color="blue">{cat}</Tag> : '-',
    },
    {
      title: '使用量 (B)',
      dataIndex: 'usage_count',
      key: 'usage_count',
      align: 'right' as const,
      render: (v: number) => v ? `${(v / 1e9).toFixed(2)}B` : '-',
    },
  ]

  return (
    <div>
      <Title level={4}>总览</Title>

      {/* 关键指标卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="模型总数"
              value={summary?.total_models || 0}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="应用总数"
              value={appsData?.total || 0}
              prefix={<AppstoreOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总 Token 数"
              value={summary?.total_tokens || 0}
              formatter={(v) => `${(Number(v) / 1e9).toFixed(2)}B`}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="总请求数"
              value={summary?.total_requests || 0}
              formatter={(v) => `${(Number(v) / 1e9).toFixed(2)}B`}
            />
          </Card>
        </Col>
      </Row>

      {/* 应用统计模块 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="热门应用" extra={<a href="/openrouter-apps">查看全部</a>}>
            <Table
              dataSource={appsData?.apps || []}
              columns={appColumns}
              rowKey="slug"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="应用分类">
            <Row gutter={[8, 8]}>
              {(categoriesData?.categories || []).map((cat: any) => (
                <Col key={cat.category} span={8}>
                  <Card size="small" hoverable>
                    <Statistic
                      title={cat.category || '未分类'}
                      value={cat.count}
                      suffix="个"
                    />
                  </Card>
                </Col>
              ))}
              {(!categoriesData?.categories || categoriesData.categories.length === 0) && (
                <Col span={24}>
                  <div style={{ textAlign: 'center', color: '#999', padding: 20 }}>
                    暂无分类数据
                  </div>
                </Col>
              )}
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 告警统计 */}
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="未确认告警"
              value={alertSummary?.unacknowledged_count || 0}
              valueStyle={{ color: (alertSummary?.unacknowledged_count || 0) > 0 ? '#cf1322' : '#3f8600' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card title="按严重程度">
            <Row gutter={8}>
              <Col span={8}>
                <Statistic title="高" value={alertSummary?.by_severity?.high || 0} valueStyle={{ color: '#cf1322' }} />
              </Col>
              <Col span={8}>
                <Statistic title="中" value={alertSummary?.by_severity?.medium || 0} valueStyle={{ color: '#faad14' }} />
              </Col>
              <Col span={8}>
                <Statistic title="低" value={alertSummary?.by_severity?.low || 0} valueStyle={{ color: '#52c41a' }} />
              </Col>
            </Row>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card title="按类型">
            <Row gutter={8}>
              <Col span={6}>
                <Statistic title="突发" value={alertSummary?.by_type?.spike || 0} />
              </Col>
              <Col span={6}>
                <Statistic title="下降" value={alertSummary?.by_type?.drop || 0} />
              </Col>
              <Col span={6}>
                <Statistic title="零使用" value={alertSummary?.by_type?.zero_usage || 0} />
              </Col>
              <Col span={6}>
                <Statistic title="模式变化" value={alertSummary?.by_type?.pattern_change || 0} />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 数据范围 */}
      {summary?.date_range && (
        <Card style={{ marginTop: 16 }}>
          <Statistic
            title="数据时间范围"
            value={`${dayjs(summary.date_range.start).format('YYYY-MM-DD')} ~ ${dayjs(summary.date_range.end).format('YYYY-MM-DD')}`}
          />
        </Card>
      )}
    </div>
  )
}