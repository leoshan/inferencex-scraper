import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import {
  DashboardOutlined,
  BarChartOutlined,
  PieChartOutlined,
  AppstoreOutlined,
} from '@ant-design/icons'
import Overview from './pages/Overview'
import ModelComparison from './pages/ModelComparison'
import AppDistribution from './pages/AppDistribution'
import OpenRouterApps from './pages/OpenRouterApps'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '总览' },
  { key: '/comparison', icon: <BarChartOutlined />, label: '模型对比' },
  { key: '/apps', icon: <PieChartOutlined />, label: '应用分布' },
  { key: '/openrouter-apps', icon: <AppstoreOutlined />, label: '应用市场' },
]

function AppContent() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={200} theme="light">
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', fontSize: 16 }}>
          Trend Tracker
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px' }}>
          <h2 style={{ margin: 0, lineHeight: '64px' }}>OpenRouter 趋势跟踪系统</h2>
        </Header>
        <Content style={{ margin: 24, background: '#f5f5f5' }}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/comparison" element={<ModelComparison />} />
            <Route path="/apps" element={<AppDistribution />} />
            <Route path="/openrouter-apps" element={<OpenRouterApps />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}

export default App
