# OpenRouter 应用使用量爬虫

获取 OpenRouter 平台上特定应用（如 Claude Code）的使用量图表数据。

## 功能特性

- **双重策略**：优先尝试 API 端点，失败时自动回退到 DOM 爬取
- **自动发现**：尝试多个可能的 API 端点模式
- **数据解析**：自动解析时间序列数据并标准化列名
- **多格式输出**：保存原始响应（JSON/HTML）和结构化 Excel 文件

## 安装依赖

```bash
pip install scrapling pandas openpyxl
scrapling install
```

## 使用方法

### 方法 1：作为模块导入

```python
from openrouter.get_app_usage import fetch_app_usage

# 获取 Claude Code 的使用量数据
result = fetch_app_usage(app_name="claude-code", output_dir="./output")

if result["success"]:
    df = result["data"]  # pandas DataFrame
    print(f"获取到 {len(df)} 条记录")
    print(df.head())
```

### 方法 2：命令行运行

```bash
# 使用默认参数（claude-code）
python scraper.py

# 指定应用名称和输出目录
python scraper.py --app claude-code --output ./output
```

## 数据获取策略

### 策略 1：API 端点（优先）

尝试以下 API 端点模式：
1. `/api/frontend/stats/app-usage?app={app_name}`
2. `/api/frontend/stats/top-models-for-app?app={app_name}`
3. `/api/internal/v1/app-stats?app={app_name}`
4. `/api/frontend/app/{app_name}/usage`
5. `/api/frontend/app/{app_name}/stats`

### 策略 2：DOM 爬取（备用）

如果 API 端点不可用，使用 StealthyFetcher 加载页面并提取数据：
- 从 `<script>` 标签中查找 `chartData`、`usageData` 等变量
- 从 Recharts DOM 元素（`.recharts-bar-rectangle`）提取数据
- 从 tooltip 元素提取数据点

## 输出文件

### 1. 原始响应文件

- **API 模式**：`raw_response_api_{app_name}_{timestamp}.json`
- **DOM 模式**：
  - `raw_response_dom_{app_name}_{timestamp}.html`（完整 HTML）
  - `raw_response_dom_data_{app_name}_{timestamp}.json`（提取的数据）

### 2. Excel 文件

`{app_name}_usage_{timestamp}.xlsx`，包含两个工作表：

#### 工作表 1：usage_chart
时间序列数据，可能包含以下列：
- `date`：日期
- `tokens`：Token 总数
- `requests`：请求数
- `prompt_tokens`：提示 Token 数
- `completion_tokens`：完成 Token 数
- `cache_hits`：缓存命中数
- `tool_calls`：工具调用数

#### 工作表 2：metadata
元数据信息：
- 应用名称
- 获取时间
- 数据来源（API 或 DOM）
- API 端点或页面 URL
- 记录数

## 文件结构

```
get_app_usage/
├── __init__.py         # 模块入口
├── scraper.py          # 主入口，协调两种策略
├── api_fetcher.py      # API 端点检测和获取
├── dom_scraper.py      # DOM 爬取和数据提取
├── parser.py           # 数据解析和标准化
└── README.md           # 本文档
```

## 返回值结构

```python
{
    "success": bool,           # 是否成功
    "data": pd.DataFrame,      # 使用量数据（如果成功）
    "metadata": {              # 元数据
        "source": str,         # "API" 或 "DOM"
        "endpoint": str,       # API 端点或页面 URL
        "record_count": int    # 记录数
    },
    "files": {                 # 输出文件路径
        "raw": str,            # 原始响应文件
        "excel": str           # Excel 文件
    }
}
```

## 示例输出

```
============================================================
OpenRouter 应用使用量爬虫
应用名称: claude-code
============================================================

============================================================
方法1: 尝试查找 API 端点
============================================================

尝试查找 claude-code 的 API 端点...

[1/5] 测试端点...
[10:30:15] 尝试 候选 API 1: https://openrouter.ai/api/frontend/stats/app-usage?app=claude-code
  请求完成，耗时: 1.23秒
  成功使用 page.json() 解析
  ✓ 找到有效 API 端点！

✓ 成功从 API 获取数据
  原始数据已保存: raw_response_api_claude-code_20260421_103015.json
  usage_chart: 45 行, 7 列
  metadata: 1 行, 5 列

✓ Excel 文件已保存: claude-code_usage_20260421_103015.xlsx

============================================================
执行结果
============================================================
成功: True
数据来源: API
记录数: 45
原始文件: raw_response_api_claude-code_20260421_103015.json
Excel 文件: claude-code_usage_20260421_103015.xlsx
```

## 注意事项

1. **网络要求**：需要能够访问 openrouter.ai
2. **浏览器驱动**：DOM 爬取需要 Chromium 浏览器驱动（scrapling 自动管理）
3. **速率限制**：API 请求之间有 1 秒延迟，避免触发速率限制
4. **数据结构**：不同应用的数据结构可能不同，解析器会自动适配

## 故障排除

### 问题：Scrapling 库未安装
```bash
pip install scrapling[fetchers]
scrapling install
```

### 问题：pandas 未安装
```bash
pip install pandas openpyxl
```

### 问题：所有方法都失败
- 检查网络连接
- 确认应用名称正确（如 `claude-code`）
- 查看原始响应文件以诊断问题
- 检查 OpenRouter 网站是否更改了 API 或页面结构

## 相关项目

- `../get_model_details/`：获取 OpenRouter 模型详细信息的爬虫
- 使用相同的 Scrapling 库和请求模式
