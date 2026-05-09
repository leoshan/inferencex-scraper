# Benchmarks 页面抓取测试记录

## 最终方案

**关键发现**: 必须使用 `DynamicFetcher` 而不是 `StealthyFetcher` 才能获取完整的 benchmark 数据。

### 成功方法

```python
from scrapling.fetchers import DynamicFetcher

page = DynamicFetcher.fetch(
    url,
    headers=headers,
    headless=True,
    network_idle=True
)
```

### 测试结果对比

| 方法 | HTML 大小 | Elo 出现次数 | 数据完整性 |
|------|-----------|--------------|------------|
| StealthyFetcher | 267,541 | 0 | ❌ 不完整 |
| **DynamicFetcher** | 274,714 | 22 | ✅ 完整 |

### 提取的数据

1. **Category Performance** - 雷达图数据 (8个类别)
2. **Models Arena** - 模型竞技场数据 (8个类别)
3. **Agents Arena** - Agent 竞技场数据 (5个类别)
4. **Ranking Distribution** - 排名分布 (4个排名)

---

## 测试记录

测试时间: 2026-04-23 10:28:25

目标 URL: https://openrouter.ai/anthropic/claude-opus-4.7/benchmarks

---

### 尝试1: 基础 StealthyFetcher

URL: https://openrouter.ai/anthropic/claude-opus-4.7/benchmarks
参数: headless=True, network_idle=True
耗时: 37.58秒
HTML 大小: 267,541 字符

检查 benchmark 内容:
  Elo: 0 次
  Design Arena: 1 次
  Models Arena: 0 次
  Agents Arena: 0 次
  Ranking Distribution: 0 次
  Category Performance: 0 次
  tournament: 0 次

**结论**: ❌ 数据不完整，benchmark 内容未加载

### 尝试2: DynamicFetcher

耗时: 36.34秒
HTML 大小: 274,714 字符

检查 benchmark 内容:
  Elo: 22 次
  Design Arena: 3 次
  Models Arena: 1 次
  Agents Arena: 1 次
  Ranking Distribution: 1 次
  Category Performance: 1 次
  tournament: 2 次
  1320: 2 次
  1342: 2 次

**结论**: ✅ 数据完整，benchmark 内容已加载

### 尝试5: 从 HTML 中提取 API 端点

找到 0 个 API 端点:
未找到 benchmark 相关 API

### 尝试6: 提取嵌入的 JSON 数据

未找到 __NEXT_DATA__

找到 0 个 JSON script 标签

### 尝试7: 提取纯文本内容

纯文本大小: 14,140 字符

关键词搜索:
  'Elo': 31 次
  'benchmark': 12 次
  'tournament': 2 次
  'Design Arena': 3 次
  'Artificial Analysis': 1 次
  'Models Arena': 1 次
  'Agents Arena': 1 次
  'Ranking Distribution': 1 次
  'Category Performance': 1 次

可能的 Elo 分数 (1000-2000): ['1200', '1600', '1442', '1062', '1320', '1342', '1263', '1361', '1200', '1242', '1361', '1343', '1320', '1342', '1263', '1361', '1200', '1242', '1361', '1343']

---

## 使用方法

```bash
# 默认抓取 claude-opus-4.7
py benchmarks_scraper.py

# 指定模型
py benchmarks_scraper.py minimax/minimax-m2.7-20260318
```

输出:
- Excel 文件: `benchmarks_{model}_{timestamp}.xlsx`
- 包含工作表: 汇总, category_performance, models_arena, agents_arena, ranking_distribution
