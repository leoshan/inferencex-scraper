基于“监控性能与价格”这一需求，从你提供的文件中可以梳理出以下信息类型：
# 数据整理

### 一、价格监控类

| 信息类型 | 可分析内容 | 相关数据字段/文件 |
|---------|------------|-------------------|
| **各模型定价对比** | 同一模型不同供应商定价差异；输入/输出/缓存读取单价比较；免费模型识别 | `endpoint_stats.pricing_json`, `pricing_prompt/completion/input_cache_read`；`endpoint_variant=free` |
| **Claude Code 应用每日成本估算** | 结合每日 token 用量与对应模型单价，计算各模型每日、累计消费金额；跟踪成本变化趋势 | `usage_chart.token_Bs_B` × `endpoint_stats.pricing` |
| **性价比趋势** | 将 benchmark/设计竞技场得分与单位 token 价格相除，得出“每美元性能”指标，跟踪随时间变化 | `artificial_analysis_all_models`、`design_arena_all_models` + `pricing` |
| **免费模型用量监控** | 免费模型(如 GLM 4.5 Air free)的实际消耗占比及变化，评估用户对免费层依赖度 | `endpoint_variant=free` + `usage_chart` |
| **推理 vs 非推理模型成本差异** | 推理模型通常输出含 thinking tokens，同等输出总 token 更多，实际有效产出成本对比 | `supports_reasoning` + `pricing` + `usage_chart` |
| **价格变动预警基线** | 以当前定价为基线，持续记录，便于未来识别降价/涨价趋势 | `pricing_json` 时间序列快照 |

### 二、性能监控类

| 信息类型 | 可分析内容 | 相关数据字段/文件 |
|---------|------------|-------------------|
| **延迟监控 (Latency)** | 各模型/供应商的 P50/P75/P90/P95/P99 延迟，识别性能退化或异常尖峰 | `endpoint_stats.stats_p*_latency` |
| **吞吐量监控 (Throughput)** | 各模型/供应商的 P50/P75/P90/P95/P99 吞吐量，评估服务容量和突发支撑能力 | `endpoint_stats.stats_p*_throughput` |
| **可用性监控 (Uptime)** | 各 endpoint 每日 uptime 百分比，快速发现宕机或降级时段 | `uptime_recent_all_models.uptime` + `date` |
| **供应商性能对比** | 同一模型不同 provider（如 Trinity Large Thinking 有 Parasail/Arcee/Venice）的延迟、吞吐、可用性横向对比，选择最优供应商 | `endpoint_stats` 按 `model_slug` + `provider_name` 分组 |
| **基准测试成绩跟踪** | AI 智能指数、编码指数、Agent 指数等 benchmark 分数变化，判断模型能力演进 | `artificial_analysis_all_models.benchmark_data` |
| **设计竞技场 Elo 跟踪** | Web/Code/Game/UI 等具体设计任务的 Elo 分变化，直观反映前端生成质量 | `design_arena_all_models.records.elo` |
| **新模型性能评估** | 新上市模型（如 kimi-k2.6、glm-5.1）的延迟、吞吐初始表现，判断是否值得切换 | `endpoint_stats` + 模型首发日期对比 |
| **推理性能专用监控** | 支持推理的模型的 thinking token 生成效率、是否出现推理超时等 | `endpoint_stats.supports_reasoning` + 相应模型的 latency/throughput |

### 三、交叉分析类（性能与价格综合）

| 信息类型 | 可分析内容 | 相关数据 |
|---------|------------|----------|
| **性能/价格比排名** | 按“每美元可获得性能”对模型排序，找出最佳性价比模型 | benchmark/elo ÷ 每 token 成本 |
| **延迟与用量的关联** | 高延迟是否导致用户抛弃该模型（用量骤降），用于设定性能告警阈值 | `latency` ↔ `usage_chart` |
| **供应商价格-性能博弈** | 同一模型不同供应商可能价格相同但性能不同，或价格不同性能接近，分析最优 trade-off | `provider_pricing` + `provider_latency/throughput` |
| **免费模型性能底线** | 免费模型（如 GLM 4.5 Air）的延迟/吞吐/基准分数，作为付费模型的最低性能基线 | 免费模型的 benchmark/elo/latency |
| **成本优化建议来源** | 识别高成本低用量模型（可以用更便宜或更免费的替代），或发现高性价比模型缺乏关注 | `cost` vs `usage` vs `benchmark` |

以上类型都可从当前文件中直接或通过简单计算得出，能支撑构建一个完整的“AI 模型性能与价格监控看板”。

# 数据解析
基于你提供的解析文件结构，以下是将之前分析结论转化为可用 Python 实现的逻辑描述（伪代码/步骤说明），使用 pandas 作为主要数据处理库。

---

## 一、数据准备

**逻辑步骤：**
1. 读取 `parsed_analysis_20260424_160331.xlsx` 文件，获取所有 sheet 名称。
2. 将以下 sheet 分别加载为 DataFrame：
   - `模型详情汇总`
   - `价格分析`
   - `性能分析`
   - `推理模型`
   - `可用性数据`
   - `基准测试数据`
   - `设计竞技场数据`
3. 对于价格和性能 DataFrame，统一处理定价列（将科学记数法字符串转换为 float）。
4. 对于 `可用性数据`，将 `date` 列转换为 datetime 类型。
5. 对于 `基准测试数据`，从 `benchmark_data` JSON 字符串中提取关键指标（如 `artificial_analysis_intelligence_index`、`artificial_analysis_coding_index`）。
6. 为每个 DataFrame 建立一致的索引，通常以 `model_slug` 和 `provider_name` 作为组合键。

---

## 二、交叉筛选法逻辑

**目标：** 支持按多个条件（免费/付费、是否推理模型、价格区间、延迟区间）筛选模型。

**实现逻辑：**
1. 以 `模型详情汇总` 为基准表。
2. 定义筛选函数 `filter_models(df, free_only=False, reasoning_only=None, max_prompt_price=None, max_completion_price=None, max_p50_latency=None)`：
   - 如果 `free_only=True`，仅保留 `is_free == True` 的行。
   - 如果 `reasoning_only=True`，仅保留 `supports_reasoning == True` 的行；`False` 则相反。
   - 如果 `max_prompt_price` 不为空，保留 `pricing_prompt <= max_prompt_price` 的行。
   - 类似处理 `max_completion_price` 和 `max_p50_latency`。
3. 返回筛选后的 DataFrame。

**可回答的问题示例：** “免费且支持推理的模型中，P50延迟最低的5个是哪些？”
- 调用 `filter_models(free_only=True, reasoning_only=True)` 后按 `stats_p50_latency` 升序排序取前5。

---

## 三、排序对比法逻辑

**目标：** 找出价格最低、延迟最低、吞吐最高的模型，以及各 provider 横向对比。

**实现逻辑：**
1. **最便宜模型：** 对 `价格分析` DataFrame 按 `pricing_completion` 升序排列，取前 N 行。
2. **最快模型：** 对 `性能分析` DataFrame 按 `stats_p50_latency` 升序排列，取前 N 行。
3. **长尾延迟最小：** 对 `性能分析` 按 `stats_p99_latency` 升序排列，取前 N 行。
4. **同一模型不同 provider 对比：**
   - 对 `模型详情汇总` 按 `model_slug` 分组（即模型名去重保留普通名称，不按完整 slug），比较同一 model_name 下各 provider 的延迟和价格。
   - 示例：筛选 `model_name` 包含 “gemini-2.5-flash” 的行，输出 provider、价格、延迟字段，直观对比。

---

## 四、阈值告警法逻辑

**目标：** 基于可用性数据识别高风险供应商。

**实现逻辑：**
1. 设定阈值：`UPTIME_THRESHOLD = 95.0`。
2. 过滤 `可用性数据` DataFrame 中 `uptime < UPTIME_THRESHOLD` 的行。
3. 将结果按 `model_slug`, `provider_name`（如果需要）和日期排序，输出为告警列表。
4. 可选：若三天内平均 uptime 低于阈值，则提升告警级别。

---

## 五、性价比排名计算逻辑

**目标：** 综合价格和基准测试分数，计算“每美元性能”。

**实现逻辑：**
1. 从 `基准测试数据` DataFrame 中，对每条记录解析 `benchmark_data` JSON，提取 `artificial_analysis_intelligence_index`（简称 `AA_index`）。
   - 注意：同一 `model_slug` 可能有推理模式和非推理模式的不同记录，需要按情况取最大值或平均值。这里可先取 max。
2. 合并 `价格分析` 和 `基准测试数据` 的 AA_index，通过 `model_slug` 关联。
3. 计算总价格：`total_price_per_million = pricing_prompt + pricing_completion`。
4. 计算性价比分数：`value_score = AA_index / total_price_per_million`。
5. 按 `value_score` 降序排列，得到性价比排名。
6. 输出时附带关键延迟指标，避免性价比高但延迟不可用的情况。

**注意：** 如果 AA_index 缺失，可跳过该模型。

---

## 六、推理模型专项分析逻辑

**目标：** 在支持推理的模型中，对比延迟、吞吐、价格。

**实现逻辑：**
1. 使用 `推理模型` sheet（或从 `模型详情汇总` 中筛选 `supports_reasoning == True`）。
2. 分别找出：
   - 最低 P50 延迟：`df.nsmallest(1, 'stats_p50_latency')`
   - 最高 P50 吞吐：`df.nlargest(1, 'stats_p50_throughput')`
   - 最佳综合平衡：可自定义加权评分，例如 `score = 0.7 * (1/延迟归一化) + 0.3 * 吞吐归一化`。
3. 输出结果。

---

## 七、可用性风险识别逻辑

**目标：** 计算各供应商近3天平均可用性，标记高风险。

**实现逻辑：**
1. 从 `可用性数据` 中筛选最近3天（基于数据最大日期）的记录。
2. 按 `model_slug` 和 provider 分组（需注意可用性数据中可能包含多个 endpoint ID，但这里可以忽略，先按 model_slug 和 date 聚合取平均），计算 `avg_uptime`。
3. 过滤 `avg_uptime < 95` 的组，按平均 uptime 升序排列。
4. 输出风险列表，包含模型、平均可用性、最低单日值。

---

## 八、质量验证逻辑（基准测试 + 设计竞技场）

**目标：** 将 benchmark 分数与设计竞技场 Elo 结合，评估模型能力，并关联用量（如有）验证是否与实际使用正相关。

**实现逻辑：**
1. **基准测试提取：** 从 `基准测试数据` 提取 `AA_index`, `AA_coding_index`, `AA_agentic_index`。
2. **设计竞技场提取：** `设计竞技场数据` 的 `records` 列包含多个类别的 elo 值，可计算 overall_elo（取所有类别 Elo 中位数或平均值）。若无记录，则缺失。
3. 合并两个质量指标形成一个综合质量分，例如：`quality = 0.5 * AA_index_normalized + 0.5 * overall_elo_normalized`。
4. 如果存在用量数据（例如从另一个文件合并），计算 quality 与 token 用量的相关系数，验证“高质量模型是否被更多地使用”。

---

## 九、几个具体结论的推导逻辑

### 结论1：编码场景性价比最优模型
**逻辑：**
- 筛选价格较低的模型（例如 `pricing_completion <= 1e-06`）。
- 筛选 `AA_coding_index` 较高的模型（需从基准测试数据提取）。
- 过滤延迟可接受的模型（P50 latency < 3000 ms）。
- 输出满足条件的模型列表。

### 结论2：高风险供应商
**逻辑：**
- 直接调用“可用性风险识别”模块，输出 uptime < 95% 的记录。
- 特别关注 uptime 为 0 或极低的记录。

### 结论3：价格与质量正相关
**逻辑：**
- 计算每个模型的平均总价格（log10 处理）和其综合质量分（如 AA_index）。
- 计算 Spearman 秩相关系数，或绘制散点图观察趋势。

### 结论4：量化方式对性能的影响
**逻辑：**
- 筛选同一 `model_name` 但不同 `quantization` 的行。
- 对比它们的 `stats_p50_latency`、`stats_p50_throughput`。
- 例如：`model_name == 'openai/gpt-oss-120b'`，按 `quantization` 分组输出性能指标。

---

## 十、持续监控看板逻辑

**目标：** 构建几个定期刷新的简易报告。

**实现逻辑：**

### 1. 价格变动追踪
- 需要历史价格快照（当前数据只有一个时间点，需假设未来会追加数据）。
- 逻辑：比较同一 `model_slug` + `provider` 在不同日期的 `pricing_prompt` 和 `pricing_completion`，计算变动百分比。

### 2. 延迟异常告警
- 输入：当前日期的 `性能分析`。
- 设定 P99 latency 阈值为 5000 ms。
- 筛选 `stats_p99_latency > 5000` 的行，生成告警。

### 3. 可用性红绿灯
- 获取最新可用性数据。
- 计算每个模型+provider 的最近平均 uptime。
- 分级：`>= 99` 绿色，`95-99` 黄色，`<95` 红色。

### 4. 性价比 Top10
- 直接运行“性价比排名”逻辑，取前10名。

### 5. 供应商健康度
- 对每个 `provider_name`，计算其所有模型的平均 uptime（加权或简单平均）。
- 按平均 uptime 降序排列，得到供应商健康度排名。

---

## 总结：程序模块结构建议

- `data_loader.py`：读取 Excel，返回各 DataFrame。
- `preprocessing.py`：数据类型转换、缺失值处理、JSON 解析。
- `filter.py`：实现交叉筛选函数。
- `price_performance.py`：性价比计算、排序、推理模型对比。
- `availability.py`：可用性告警、供应商健康度计算。
- `quality.py`：基准测试与设计竞技场数据处理，质量评分。
- `monitor.py`：看板输出函数，整合上述分析并生成报告（如 CSV、Excel 或可视化）。
- `main.py`：串联所有流程，输出结论。

以上逻辑可直接指导 Python 代码实现，无需额外设计。

---

# 趋势跟踪系统架构

## 一、系统目标

基于现有爬虫能力，构建 OpenRouter 模型调用量与应用场景趋势跟踪系统：

1. **模型调用量趋势** - 各模型的 token 使用量、请求数随时间变化
2. **应用场景分布** - 不同应用（claude-code、cursor 等）对各模型的使用情况
3. **异常检测与告警** - 自动识别调用量异常波动
4. **可视化展示** - 前端界面展示趋势图表和分析报告

## 二、技术选型

| 层面 | 技术选型 | 理由 |
|-----|---------|------|
| **时序数据库** | TimescaleDB | PostgreSQL 扩展，支持高效时间范围查询、自动分区、压缩 |
| **缓存** | Redis | 缓存热门查询、实时数据 |
| **后端框架** | FastAPI | 异步支持好，自动生成 API 文档 |
| **前端框架** | React 18 + TypeScript | 生态成熟，组件丰富 |
| **图表库** | ECharts | 支持复杂交互，中文友好 |
| **UI 组件** | Ant Design | 企业级组件库 |
| **数据请求** | TanStack Query | 自动缓存，后台刷新 |

## 三、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端展示层 (React)                         │
│  趋势图表 │ 应用分布图 │ 异常告警 │ 数据报表 │ 交互筛选           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      后端服务层 (FastAPI)                         │
│  REST API │ 趋势分析服务 │ 异常检测服务 │ 数据聚合服务            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据存储层                                 │
│  TimescaleDB (时序数据) │ Redis (缓存) │ SQLite (元数据)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                数据采集层 (扩展现有爬虫)                           │
│  APScheduler 调度器 │ 复用 get_app_usage/get_model_details      │
└─────────────────────────────────────────────────────────────────┘
```

## 四、数据采集层设计

### 4.1 采集数据类型

| 数据类型 | API 端点 | 采集频率 | 数据内容 |
|---------|---------|---------|---------|
| 模型日调用量 | `/api/frontend/stats/top-apps-for-model` | 每小时 | 每日聚合 token 数、请求数 |
| 应用使用分布 | `/api/frontend/stats/app-usage` | 每6小时 | 各应用的模型使用分布 |
| 模型列表 | `/api/frontend/models` | 每日 | 模型元数据、价格、性能 |
| 模型详情 | `/{model}/benchmarks` | 每周 | 基准测试分数 |

### 4.2 新增目录结构

```
openrouter/trend_tracker/
├── __init__.py
├── scheduler.py      # APScheduler 定时调度
├── collector.py      # 数据收集器（复用现有爬虫）
├── models.py         # 数据模型定义
└── config.py         # 采集配置
```

### 4.3 调度策略

```python
# 每小时采集模型调用量
scheduler.add_job(collect_model_usage, trigger=IntervalTrigger(hours=1))

# 每6小时采集应用分布
scheduler.add_job(collect_app_distribution, trigger=IntervalTrigger(hours=6))

# 每日更新模型列表
scheduler.add_job(collect_model_list, trigger=CronTrigger(hour=2, minute=0))

# 每周采集基准测试
scheduler.add_job(collect_benchmarks, trigger=CronTrigger(day_of_week='mon', hour=3))
```

## 五、数据存储层设计

### 5.1 TimescaleDB 数据模型

```sql
-- 模型每日调用量 (时序超级表)
CREATE TABLE model_usage_daily (
    time            TIMESTAMPTZ NOT NULL,
    model_slug      VARCHAR(255) NOT NULL,
    app_name        VARCHAR(255),
    prompt_tokens   BIGINT DEFAULT 0,
    completion_tokens BIGINT DEFAULT 0,
    total_tokens    BIGINT DEFAULT 0,
    requests        BIGINT DEFAULT 0,
    cache_hits      BIGINT DEFAULT 0,
    provider_name   VARCHAR(100),
    PRIMARY KEY (time, model_slug, app_name)
);

SELECT create_hypertable('model_usage_daily', 'time', chunk_time_interval => INTERVAL '1 day');

-- 应用使用分布表
CREATE TABLE app_distribution (
    time            TIMESTAMPTZ NOT NULL,
    app_name        VARCHAR(255) NOT NULL,
    model_slug      VARCHAR(255) NOT NULL,
    token_share     DECIMAL(10, 4),
    total_tokens    BIGINT,
    PRIMARY KEY (time, app_name, model_slug)
);

SELECT create_hypertable('app_distribution', 'time', chunk_time_interval => INTERVAL '1 day');

-- 模型元数据表
CREATE TABLE model_metadata (
    model_slug      VARCHAR(255) PRIMARY KEY,
    display_name    VARCHAR(255),
    provider        VARCHAR(100),
    context_length  INTEGER,
    pricing_prompt  DECIMAL(15, 10),
    pricing_completion DECIMAL(15, 10),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 异常告警表
CREATE TABLE anomaly_alerts (
    id              SERIAL PRIMARY KEY,
    time            TIMESTAMPTZ NOT NULL,
    model_slug      VARCHAR(255),
    app_name        VARCHAR(255),
    anomaly_type    VARCHAR(50),  -- 'spike', 'drop', 'zero'
    severity        VARCHAR(20),  -- 'low', 'medium', 'high'
    details         JSONB,
    acknowledged    BOOLEAN DEFAULT FALSE
);

-- 索引
CREATE INDEX idx_usage_model ON model_usage_daily (model_slug, time DESC);
CREATE INDEX idx_usage_app ON model_usage_daily (app_name, time DESC);
CREATE INDEX idx_distribution_app ON app_distribution (app_name, time DESC);
```

### 5.2 数据保留策略

```sql
-- 原始数据保留 90 天
SELECT add_retention_policy('model_usage_daily', INTERVAL '90 days');

-- 7 天前数据自动压缩
ALTER TABLE model_usage_daily SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'model_slug'
);
SELECT add_compression_policy('model_usage_daily', INTERVAL '7 days');

-- 周聚合视图
CREATE MATERIALIZED VIEW model_usage_weekly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('7 days', time) AS week,
    model_slug,
    app_name,
    SUM(prompt_tokens) AS prompt_tokens,
    SUM(completion_tokens) AS completion_tokens,
    SUM(total_tokens) AS total_tokens,
    SUM(requests) AS requests
FROM model_usage_daily
GROUP BY week, model_slug, app_name;
```

## 六、数据分析层设计

### 6.1 趋势分析算法

```python
class TrendAnalyzer:
    def calculate_moving_average(self, df, window=7, column='total_tokens'):
        """计算移动平均"""
        df['ma_7'] = df[column].rolling(window=window).mean()
        df['ma_30'] = df[column].rolling(window=30).mean()
        return df

    def calculate_growth_rate(self, df, column='total_tokens'):
        """计算增长率"""
        recent = df.tail(7)[column].sum()
        previous = df.tail(14).head(7)[column].sum()
        growth_rate = (recent - previous) / previous * 100 if previous > 0 else 0
        return {
            'growth_rate': growth_rate,
            'trend': 'increasing' if growth_rate > 5 else 'decreasing' if growth_rate < -5 else 'stable'
        }

    def detect_seasonality(self, df, column='total_tokens'):
        """检测周期性"""
        values = df[column].values
        autocorr_weekly = pd.Series(values).autocorr(lag=7)
        return {'has_seasonality': autocorr_weekly > 0.5, 'weekly_autocorr': autocorr_weekly}
```

### 6.2 异常检测算法

```python
class AnomalyDetector:
    def detect_spikes(self, df, column='total_tokens', threshold=3.0):
        """检测突发增长 (Z-Score)"""
        mean = df[column].mean()
        std = df[column].std()
        anomalies = []
        for _, row in df.iterrows():
            z_score = (row[column] - mean) / std if std > 0 else 0
            if abs(z_score) > threshold:
                anomalies.append({
                    'time': row['time'],
                    'value': row[column],
                    'z_score': z_score,
                    'type': 'spike' if z_score > 0 else 'drop',
                    'severity': 'high' if abs(z_score) > 5 else 'medium'
                })
        return anomalies

    def detect_zero_usage(self, df, column='total_tokens', consecutive_days=3):
        """检测零使用"""
        anomalies = []
        zero_count = 0
        start_time = None
        for _, row in df.iterrows():
            if row[column] == 0:
                if zero_count == 0:
                    start_time = row['time']
                zero_count += 1
            else:
                if zero_count >= consecutive_days:
                    anomalies.append({
                        'start_time': start_time,
                        'duration_days': zero_count,
                        'type': 'zero_usage',
                        'severity': 'high'
                    })
                zero_count = 0
        return anomalies

    def detect_pattern_change(self, df, column='total_tokens', window=7):
        """检测模式变化"""
        if len(df) < window * 4:
            return []
        anomalies = []
        df['rolling_mean'] = df[column].rolling(window).mean()
        for i in range(window * 2, len(df)):
            prev_mean = df.iloc[i-window*2:i-window]['rolling_mean'].mean()
            curr_mean = df.iloc[i-window:i]['rolling_mean'].mean()
            if prev_mean > 0:
                change_ratio = abs(curr_mean - prev_mean) / prev_mean
                if change_ratio > 0.5:
                    anomalies.append({
                        'time': df.iloc[i]['time'],
                        'type': 'pattern_change',
                        'change_ratio': change_ratio,
                        'severity': 'medium'
                    })
        return anomalies
```

### 6.3 应用场景聚类分析

```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class AppClusterAnalyzer:
    def cluster_by_usage_pattern(self, app_data):
        """基于使用模式聚类应用"""
        # 特征: 各模型使用占比
        features = []
        app_names = []
        for app_name in app_data['app_name'].unique():
            app_df = app_data[app_data['app_name'] == app_name]
            total = app_df['total_tokens'].sum()
            if total == 0:
                continue
            feature_vector = app_df.groupby('model_slug')['total_tokens'].sum() / total
            features.append(feature_vector.fillna(0))
            app_names.append(app_name)

        if len(features) < 3:
            return {'clusters': {}}

        # K-Means 聚类
        scaler = StandardScaler()
        X = scaler.fit_transform(pd.DataFrame(features).fillna(0))
        n_clusters = min(5, len(features) // 2)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(X)

        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(app_names[i])

        return {'clusters': clusters}
```

## 七、后端 API 设计

```python
# FastAPI 端点

# --- 趋势数据 API ---
GET  /api/v1/trends/models/{model_slug}    # 获取单个模型的调用量趋势
GET  /api/v1/trends/apps/{app_name}        # 获取单个应用的使用趋势
GET  /api/v1/trends/compare                # 多模型对比

# --- 分布数据 API ---
GET  /api/v1/distribution/apps             # 获取应用使用分布
GET  /api/v1/distribution/models           # 获取模型使用分布

# --- 异常告警 API ---
GET  /api/v1/alerts                        # 获取异常告警列表
POST /api/v1/alerts/{id}/acknowledge       # 确认告警

# --- 元数据 API ---
GET  /api/v1/models                        # 获取模型列表
GET  /api/v1/apps                          # 获取应用列表
```

## 八、前端展示层设计

### 8.1 核心页面

1. **总览页** - 关键指标卡片 + 趋势概览
2. **模型趋势页** - 折线图 + 移动均线 + 异常标记
3. **应用分布页** - 堆叠面积图 + 饼图
4. **异常告警页** - 告警列表 + 确认操作
5. **报表页** - 数据导出 + 自定义报表

### 8.2 核心图表类型

- **折线图**: 模型调用量趋势 + 移动均线
- **堆叠面积图**: 多应用使用量对比
- **热力图**: 模型-应用使用矩阵
- **饼图**: 应用场景分布占比

### 8.3 交互功能

- 日期范围选择 (快捷 + 自定义)
- 模型/应用多选筛选
- 指标切换 (tokens/requests)
- 图表缩放拖拽
- 数据导出 (CSV/Excel/图片)

## 九、实施路线图

### Phase 1: 数据采集层扩展 (1-2周)
- 创建 `trend_tracker` 目录结构
- 实现调度器基础框架
- 集成现有爬虫模块

### Phase 2: 数据存储层 (1周)
- 安装配置 TimescaleDB
- 创建数据表和索引
- 设置保留和压缩策略

### Phase 3: 数据分析层 (1-2周)
- 实现趋势分析算法
- 实现异常检测算法
- 实现聚类分析

### Phase 4: 后端 API 开发 (1-2周)
- 实现核心 API 端点
- 实现分析服务

### Phase 5: 前端开发 (2-3周)
- React 项目初始化
- 核心页面开发
- 图表组件实现

### Phase 6: 部署与测试 (1周)
- Docker Compose 配置
- 生产环境部署
- 测试与优化

**总计**: 7-12 周
