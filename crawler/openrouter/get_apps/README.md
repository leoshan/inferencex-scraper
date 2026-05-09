# OpenRouter Apps 爬虫

爬取 https://openrouter.ai/apps 页面的全部应用信息。

## 功能

- 获取 OpenRouter 平台上的所有应用列表
- 支持多种数据获取方式（API 优先，DOM 备用）
- 自动解析和标准化应用数据
- 存储到 SQLite 数据库
- 导出为 JSON 和 Excel 格式
- 与前端页面集成展示

## 使用方法

### 命令行

```bash
# 进入项目目录
cd D:\ai\crawler\inferencex-scraper

# 直接运行（仅保存文件）
python -m crawler.openrouter.get_apps.scraper

# 保存到数据库
python -m crawler.openrouter.get_apps.scraper --save-db

# 指定输出目录
python -m crawler.openrouter.get_apps.scraper --output ./output --save-db
```

### Python 导入

```python
from crawler.openrouter.get_apps import scrape_apps

# 执行爬取并保存到数据库
result = scrape_apps(save_to_db=True)

if result['success']:
    print(f"获取到 {result['count']} 个应用")
    print(f"数据库保存: {result['db_saved']}")
    for app in result['apps']:
        print(f"  - {app['name']}: {app['url']}")
```

## 数据存储

### 文件存储

- `data/raw/apps_api_YYYYMMDD_HHMMSS.json` - API 原始响应
- `data/raw/apps_page_YYYYMMDD_HHMMSS.html` - 页面 HTML（DOM 方式）
- `data/raw/apps_data_YYYYMMDD_HHMMSS.json` - 提取的应用数据
- `data/raw/openrouter_apps_YYYYMMDD_HHMMSS.xlsx` - Excel 格式输出

### 数据库存储

数据存储在 `data/db/trend_tracker.db` 的 `openrouter_apps` 表中：

| 字段 | 类型 | 说明 |
|------|------|------|
| slug | TEXT | 应用唯一标识（主键） |
| name | TEXT | 应用名称 |
| description | TEXT | 应用描述 |
| url | TEXT | 应用详情页 URL |
| icon_url | TEXT | 应用图标 URL |
| category | TEXT | 应用分类 |
| website | TEXT | 应用官网 |
| usage_count | INTEGER | 使用量 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| raw_data | TEXT | 原始 JSON 数据 |

## API 接口

### 获取应用列表

```
GET /api/v1/apps?limit=20&category=&search=&sort_by=usage_count
```

### 获取分类列表

```
GET /api/v1/apps/categories
```

### 获取应用详情

```
GET /api/v1/apps/{app_slug}
```

## 前端页面

访问 http://localhost:5175/openrouter-apps 查看应用市场页面。

功能：
- 应用列表展示
- 搜索过滤
- 分类筛选
- 多种排序方式
- 分页浏览

## 依赖

- `scrapling[fetchers]` - 网页抓取库
- `pandas` - 数据处理和 Excel 导出
- `openpyxl` - Excel 文件写入
- `aiosqlite` - 异步 SQLite 操作

## 安装依赖

```bash
pip install scrapling[fetchers] pandas openpyxl aiosqlite
scrapling install
```
