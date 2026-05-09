# OpenRouter Trend Tracker Frontend

React + TypeScript + ECharts + Ant Design 前端应用。

## 技术栈

- **React 18** - 前端框架
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Ant Design** - UI 组件库
- **ECharts** - 图表库
- **TanStack Query** - 数据请求和缓存
- **Zustand** - 状态管理
- **React Router** - 路由

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建
npm run build

# 预览构建结果
npm run preview
```

## 页面

| 路由 | 页面 | 描述 |
|-----|------|------|
| `/` | Overview | 总览页，关键指标卡片 |
| `/trends` | ModelTrends | 模型趋势分析，折线图 |
| `/apps` | AppDistribution | 应用分布分析，饼图 |
| `/alerts` | Alerts | 异常告警列表 |
| `/reports` | Reports | 数据报表导出 |

## 目录结构

```
src/
├── api/              # API 客户端
├── components/       # 组件
│   └── charts/       # 图表组件
├── pages/            # 页面组件
├── stores/           # Zustand stores
├── types/            # TypeScript 类型定义
└── utils/            # 工具函数
```

## API 代理

开发服务器配置了代理，将 `/api` 请求转发到 `http://localhost:8000`。

## 构建 Docker 镜像

```bash
docker build -t trend-tracker-frontend .
```
