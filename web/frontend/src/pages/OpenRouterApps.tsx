import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Table, Input, Select, Space, Tag, Typography, Row, Col, Spin, Image, Tooltip } from 'antd'
import { SearchOutlined, GlobalOutlined } from '@ant-design/icons'
import { appsApi } from '@/api'

const { Title, Text } = Typography
const { Search } = Input

interface AppInfo {
  slug: string
  name: string
  description: string
  url: string
  icon_url: string
  category: string
  website: string
  usage_count: number
  created_at: string
  updated_at: string
}

export default function OpenRouterApps() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string | undefined>()
  const [sortBy, setSortBy] = useState('usage_count')
  const [pageSize, setPageSize] = useState(20)

  // 获取应用列表
  const { data: appsData, isLoading: appsLoading } = useQuery({
    queryKey: ['openrouterApps', search, category, sortBy, pageSize],
    queryFn: () => appsApi.list({
      limit: pageSize,
      search: search || undefined,
      category: category,
      sort_by: sortBy,
    }),
  })

  // 获取分类列表
  const { data: categoriesData } = useQuery({
    queryKey: ['appCategories'],
    queryFn: () => appsApi.getCategories(),
  })

  // 表格列定义
  const columns = [
    {
      title: '应用',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      render: (name: string, record: AppInfo) => (
        <Space>
          {record.icon_url ? (
            <Image
              src={record.icon_url}
              width={32}
              height={32}
              style={{ borderRadius: 4 }}
              fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
              preview={false}
            />
          ) : (
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 4,
              background: '#f0f0f0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 14,
              color: '#999'
            }}>
              {name?.charAt(0)?.toUpperCase() || '?'}
            </div>
          )}
          <div>
            <div style={{ fontWeight: 500 }}>
              <a href={record.url} target="_blank" rel="noopener noreferrer">
                {name || record.slug}
              </a>
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>{record.slug}</Text>
          </div>
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (desc: string) => (
        <Tooltip title={desc}>
          <span>{desc || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (cat: string) => cat ? <Tag color="blue">{cat}</Tag> : '-',
    },
    {
      title: '使用量 (B)',
      dataIndex: 'usage_count',
      key: 'usage_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => count ? `${(count / 1e9).toFixed(2)}B` : '-',
    },
    {
      title: '网站',
      dataIndex: 'website',
      key: 'website',
      width: 80,
      align: 'center' as const,
      render: (url: string) => url ? (
        <a href={url} target="_blank" rel="noopener noreferrer">
          <GlobalOutlined />
        </a>
      ) : '-',
    },
  ]

  return (
    <div>
      <Title level={4}>OpenRouter 应用市场</Title>
      <Text type="secondary">
        浏览 OpenRouter 平台上的所有应用
      </Text>

      {/* 筛选栏 */}
      <Card style={{ marginTop: 16, marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} md={8}>
            <Search
              placeholder="搜索应用名称或描述..."
              allowClear
              enterButton={<SearchOutlined />}
              onSearch={setSearch}
              onChange={(e) => !e.target.value && setSearch('')}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              placeholder="选择分类"
              allowClear
              style={{ width: '100%' }}
              onChange={setCategory}
              options={categoriesData?.categories?.map(c => ({
                label: `${c.category} (${c.count})`,
                value: c.category,
              })) || []}
            />
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Select
              value={sortBy}
              style={{ width: '100%' }}
              onChange={setSortBy}
              options={[
                { label: '按使用量排序', value: 'usage_count' },
                { label: '按名称排序', value: 'name' },
                { label: '按更新时间排序', value: 'updated_at' },
              ]}
            />
          </Col>
        </Row>
      </Card>

      {/* 统计信息 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Text type="secondary">总应用数</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>
              {appsData?.total || 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Text type="secondary">当前显示</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>
              {appsData?.count || 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Text type="secondary">分类数</Text>
            <div style={{ fontSize: 24, fontWeight: 'bold' }}>
              {categoriesData?.categories?.length || 0}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 应用列表 */}
      <Card>
        {appsLoading ? (
          <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />
        ) : (
          <Table
            dataSource={appsData?.apps}
            columns={columns}
            rowKey="slug"
            pagination={{
              pageSize: pageSize,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onShowSizeChange: (_, size) => setPageSize(size),
              showTotal: (total) => `共 ${total} 个应用`,
            }}
            size="middle"
          />
        )}
      </Card>
    </div>
  )
}
