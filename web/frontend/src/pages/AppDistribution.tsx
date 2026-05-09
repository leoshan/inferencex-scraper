import { useQuery } from '@tanstack/react-query'
import { Card, Row, Col, Spin, Typography, Table } from 'antd'
import dayjs from 'dayjs'
import { appsApi } from '@/api'
import { DistributionPie } from '@/components/charts'

const { Title } = Typography

export default function AppDistribution() {
  // 获取应用列表
  const { data: appsData, isLoading: appsLoading } = useQuery({
    queryKey: ['appsList'],
    queryFn: () => appsApi.list(50),
  })

  // 获取应用分布
  const { data: distributionData, isLoading: distLoading } = useQuery({
    queryKey: ['appDistribution'],
    queryFn: () => appsApi.getDistribution(dayjs().toISOString(), 20),
  })

  if (appsLoading || distLoading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  // 应用表格列
  const appColumns = [
    { title: '应用名称', dataIndex: 'name', key: 'name' },
    { title: '总 Token 数 (B)', dataIndex: 'usage_count', key: 'usage_count', render: (v: number) => v ? `${(v / 1e9).toFixed(2)}B` : '-' },
  ]

  return (
    <div>
      <Title level={4}>应用分布分析</Title>

      <Row gutter={[16, 16]}>
        {/* 应用使用分布饼图 */}
        <Col xs={24} lg={12}>
          <Card className="chart-container">
            <DistributionPie
              data={distributionData?.app_totals || {}}
              title="应用 Token 使用分布"
              height={400}
            />
          </Card>
        </Col>

        {/* 应用份额 */}
        <Col xs={24} lg={12}>
          <Card title="应用份额占比">
            <Table
              dataSource={Object.entries(distributionData?.app_shares || {}).map(([name, share]) => ({
                app_name: name,
                share: share,
              }))}
              columns={[
                { title: '应用名称', dataIndex: 'app_name', key: 'name' },
                { title: '份额 (%)', dataIndex: 'share', key: 'share', render: (v: number) => v.toFixed(2) + '%' },
              ]}
              rowKey="app_name"
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* 应用列表 */}
      <Card title="应用列表" style={{ marginTop: 16 }}>
        <Table
          dataSource={appsData?.apps}
          columns={appColumns}
          rowKey="slug"
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Card>
    </div>
  )
}