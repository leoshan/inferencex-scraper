# InferenceX Scraper & OpenRouter Trend Tracker

从多个数据源采集 LLM 推理性能数据，并跟踪 OpenRouter 模型调用量和应用场景趋势变化。

## 功能特性

### 数据采集
- **InferenceX** - 从 SemiAnalysis InferenceX 平台采集 LLM 推理性能基准数据
- **OpenRouter** - 采集模型调用量、应用使用分布、模型详情
- **Artificial Analysis** - 采集 AI 模型评测数据（Intelligence Index、Speed、Price）

### 数据单位说明
- 所有使用量数据（Token 数、请求数）均以 **B（十亿）** 为单位显示
- Excel 导出文件中的 Token 数据已转换为 Billion 单位

### 趋势分析
- 移动平均趋势分析（7日/30日均线）
- 异常检测（Z-Score、零使用、模式变化）
- 应用场景聚类分析

### 可视化展示
- React + ECharts + Ant Design 前端
- 趋势图表、分布图、热力图
- 异常告警列表

## 目录结构

```
inferencex-scraper/
├── crawler/                        # 数据采集模块
│   ├── openrouter/                 # OpenRouter 爬虫
│   │   ├── get_app_usage/          # 应用使用量采集
│   │   ├── get_apps/               # 应用列表采集
│   │   ├── get_model_details/      # 模型详情采集
│   │   └── trend_tracker/          # 趋势跟踪调度器
│   ├── artificialanalysis/         # Artificial Analysis 爬虫
│   └── inferencex/                 # InferenceX 爬虫
│
├── analysis/                       # 数据分析模块
│   ├── service/                    # 分析服务
│   │   ├── trend_analyzer.py       # 趋势分析
│   │   ├── anomaly_detector.py     # 异常检测
│   │   └── cluster_analyzer.py     # 聚类分析
│   └── processor/                  # 数据处理器
│
├── data/                           # 数据模块（统一存储）
│   ├── __init__.py                 # 数据库连接管理
│   ├── models.py                   # ORM 数据模型
│   ├── storage.py                  # 统一数据存储管理器
│   │
│   ├── raw/                        # 原始数据
│   │   ├── json/                   # JSON 格式原始数据
│   │   │   ├── openrouter/         # OpenRouter 数据
│   │   │   ├── artificialanalysis/ # Artificial Analysis 数据
│   │   │   └── inferencex/         # InferenceX 数据
│   │   └── html/                   # HTML 调试文件
│   │
│   ├── processed/                  # 处理后数据
│   │   ├── excel/                  # Excel 文件
│   │   └── csv/                    # CSV 文件
│   │
│   └── db/                         # SQLite 数据库
│       └── trend_tracker.db        # 主数据库
│
├── web/                            # Web 模块
│   ├── api/                        # 后端 API (FastAPI)
│   ├── frontend/                   # 前端 (React)
│   └── venv/                       # Python 虚拟环境
│
├── scripts/                        # 工具脚本
│   └── import_all_data.py          # 数据导入脚本
├── run.py                          # 启动脚本
└── requirements.txt                # Python 依赖
```

## 数据库表结构

| 表名 | 说明 | 记录数 |
|------|------|--------|
| model_usage_daily | 模型每日调用量 | 17,634 |
| app_distribution | 应用使用分布 | 2,090 |
| model_metadata | 模型元数据 | 713 |
| openrouter_apps | OpenRouter 应用信息 | 28 |
| openrouter_model_details | OpenRouter 模型详情 | 12,945 |
| artificial_analysis_data | Artificial Analysis 性能数据 | 1,995 |
| inferencex_benchmarks | InferenceX 基准数据 | 3,292 |

**总计: 38,697+ 条记录**

## 快速开始

### 1. 创建虚拟环境

```bash
python -m venv web/venv
source web/venv/Scripts/activate  # Windows
# source web/venv/bin/activate   # Linux/Mac
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 导入数据到数据库

```bash
python scripts/import_all_data.py
```

### 4. 运行一次数据采集

```bash
python run.py once
```

### 5. 启动 API 服务

```bash
python run.py api --port 8005
```

访问 http://localhost:8005/docs 查看 API 文档。

### 6. 启动前端

```bash
cd web/frontend
npm install
npm run dev
```

访问 http://localhost:5175 查看前端界面。

### 7. 启动数据采集服务（后台运行）

```bash
python run.py collector
```

## 数据采集使用

### OpenRouter Apps 采集

```bash
# 采集应用列表
python -m crawler.openrouter.get_apps.scraper

# 采集应用使用量
python -m crawler.openrouter.get_app_usage.scraper --app claude-code
```

### Artificial Analysis 采集

```bash
python -m crawler.artificialanalysis.scraper
```

### InferenceX 采集

```bash
# 一键执行
python -m crawler.inferencex.run_pipeline

# 分步执行
python -m crawler.inferencex.scrape          # 采集 JSON
python -m crawler.inferencex.convert_to_csv  # 转换 CSV
python -m crawler.inferencex.merge_csv       # 合并 CSV
```

### 支持的 InferenceX 模型

| 模型 ID | 对应模型名称 |
|---------|-------------|
| `llama70b` | Llama-3.3-70B-Instruct-FP8 |
| `dsr1` | DeepSeek-R1-0528 |
| `kimik2.5` | Kimi-K2.5 |
| `minimaxm2.5` | MiniMax-M2.5 |
| `qwen3.5` | Qwen-3.5-397B-A17B |
| `glm5` | GLM-5 |

## API 端点

### 趋势数据

| 端点 | 说明 |
|-----|------|
| `GET /api/v1/trends/models/{model_slug}` | 获取模型趋势 |
| `GET /api/v1/trends/apps/{app_name}` | 获取应用趋势 |
| `GET /api/v1/trends/compare` | 多模型对比 |
| `GET /api/v1/trends/summary` | 趋势摘要 |
| `GET /api/v1/trends/rankings` | 模型排名 |
| `GET /api/v1/trends/category-trends` | 场景分类趋势 |

### 对比分析

| 端点 | 说明 |
|-----|------|
| `POST /api/v1/comparison/models` | 多模型对比分析 |
| `GET /api/v1/comparison/heatmap` | 调用量热力图 |
| `GET /api/v1/comparison/metrics/{model_slug}` | 模型详细指标 |
| `GET /api/v1/comparison/top-apps/{model_slug}` | 模型 Top 应用 |

### 应用数据

| 端点 | 说明 |
|-----|------|
| `GET /api/v1/apps` | 应用列表 |
| `GET /api/v1/apps/distribution` | 应用分布 |
| `GET /api/v1/apps/{app_name}/models` | 应用使用的模型 |

### 异常告警

| 端点 | 说明 |
|-----|------|
| `GET /api/v1/alerts` | 告警列表 |
| `POST /api/v1/alerts/{id}/acknowledge` | 确认告警 |
| `GET /api/v1/alerts/summary` | 告警摘要 |

## 前端页面

| 路由 | 页面 | 描述 |
|-----|------|------|
| `/` | Overview | 总览页，关键指标卡片 |
| `/comparison` | ModelComparison | 模型对比分析，多线图、热力图 |
| `/apps` | AppDistribution | 应用分布分析，饼图 |
| `/openrouter-apps` | OpenRouterApps | OpenRouter 应用市场 |

## 统一数据存储

所有爬虫使用统一的 `DataStorage` 类保存数据：

```python
from data import DataStorage

storage = DataStorage()

# 保存 JSON 数据
storage.save_json(data, 'openrouter', 'apps_data')

# 保存 Excel 数据
storage.save_excel(df, 'openrouter', 'model_details')

# 保存 CSV 数据
storage.save_csv(df, 'inferencex', 'benchmarks')
```

数据存储路径规则：
- JSON 原始数据: `data/raw/json/{category}/`
- HTML 调试文件: `data/raw/html/{category}/`
- Excel 处理数据: `data/processed/excel/{category}/`
- CSV 处理数据: `data/processed/csv/{category}/`

## 配置

环境变量:

| 变量 | 说明 | 默认值 |
|-----|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | SQLite 本地数据库 |

## License

MIT
