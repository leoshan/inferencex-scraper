# InferenceX TCO 定价监控方案

> 2026-05-07

---

## 1. 定价数据来源机制

### 1.1 数据存储方式

TCO 定价数据 **硬编码在 Next.js 的 JS bundle 中**，不是通过 API 动态加载。

```
当前 bundle: /_next/static/chunks/0n_gp9xy1alci.js
```

> ⚠️ chunk 文件名中的 hash (`0n_gp9xy1alci`) 会随代码/数据变更而改变，脚本每次自动扫描定位。

### 1.2 值会"偷摸变化"吗？

**会的**。以下场景会触发变化（不会有公告）：

| 场景 | 频率 |
|------|------|
| SemiAnalysis 更新 GPU 定价假设 | 不定期（数周/数月） |
| 新增 GPU 型号 | 新硬件发布时 |
| 调整 power factor / TDP | 电费/PUE 假设变化时 |
| 前端代码重构/部署 | 任何时候 |

---

## 2. 自动监控脚本

### 2.1 核心功能

| 功能 | 说明 |
|------|------|
| **自动发现 bundle** | 不依赖固定文件名，扫描所有 JS chunks |
| **数据提取** | 解析 minified JS，提取 9 种 GPU 的 specs + 3 种定价 |
| **变更检测** | 对比上次数据，自动检测价格/GPU 变化 |
| **每日快照** | 每天保存独立的 JSON 快照文件 |
| **日志记录** | 完整日志写入本地文件（按日期轮转） |
| **历史追踪** | CSV 追加模式，支持趋势分析 |

### 2.2 用法

```bash
# 单次运行
python3 scripts/scrape_tco_pricing.py

# 强制保存（即使无变化也写入当天记录）
python3 scripts/scrape_tco_pricing.py --force

# 安装 cron 定时任务（每天 08:00）
python3 scripts/scrape_tco_pricing.py --install-cron
```

### 2.3 Cron 定时任务（已安装）

```
0 8 * * * cd /root/inferencex-scraper && /usr/bin/python3 scripts/scrape_tco_pricing.py --force 2>&1
```

---

## 3. 输出文件结构

```
inferencex-scraper/
├── json_data/tco_history/
│   ├── tco_latest.json          ← 最新快照（覆盖更新）
│   ├── tco_history.csv          ← 完整历史（每行一个GPU，追加模式）
│   ├── tco_daily_summary.csv    ← 每日价格汇总（一天一行，含所有GPU的3种价格）
│   ├── tco_changelog.md         ← 价格变更日志
│   └── daily/
│       ├── tco_2026-05-07.json  ← 当日完整快照
│       ├── tco_2026-05-08.json
│       └── ...
└── logs/tco_scraper/
    ├── tco_scraper_2026-05-07.log  ← 当日详细运行日志
    ├── tco_scraper_2026-05-08.log
    └── ...
```

### 3.1 每日价格汇总 CSV 格式

每天一行，记录所有 GPU 的三种成本模型价格：

```csv
date,bundle_hash,b200_costh,b200_costn,b200_costr,b300_costh,b300_costn,...
2026-05-07,0n_gp9xy1alci,1.95,2.34,2.9,2.34,2.808,3.48,...
2026-05-08,xxxxx,1.95,2.34,2.9,2.34,2.808,3.48,...
```

### 3.2 日志文件示例

```
2026-05-07 21:55:38 [INFO]  🔍 InferenceX TCO Pricing Scraper
2026-05-07 21:55:38 [DEBUG] Fetching: https://inferencex.semianalysis.com/inference
2026-05-07 21:55:38 [DEBUG]   → 70449 bytes
2026-05-07 21:55:38 [INFO]    HTML size: 70449 bytes
2026-05-07 21:55:46 [INFO]    ✅ Found TCO bundle: /_next/static/chunks/0n_gp9xy1alci.js
2026-05-07 21:55:46 [INFO]    Extracted 9 GPUs: b200, b300, gb200, ...
2026-05-07 21:55:46 [INFO]    📅 Daily snapshot: .../daily/tco_2026-05-07.json
```

---

## 4. 当前价格数据

| GPU | Hyperscaler (costh) | **Neocloud (costn)** | 3Y Rental (costr) |
|-----|:-------------------:|:--------------------:|:-----------------:|
| GB300 NVL72 | $2.652 | **$3.300** | $3.960 |
| GB200 NVL72 | $2.210 | **$2.750** | $3.300 |
| B300 | $2.340 | **$2.808** | $3.480 |
| B200 | $1.950 | **$2.340** | $2.900 |
| MI355X | $1.480 | **$1.900** | $2.100 |
| H200 | $1.410 | **$1.740** | $1.600 |
| MI325X | $1.280 | **$1.590** | $1.800 |
| H100 | $1.300 | **$1.690** | $1.300 |
| MI300X | $1.120 | **$1.400** | $1.550 |

> 数据来源: InferenceX JS bundle, 抓取时间: 2026-05-07
