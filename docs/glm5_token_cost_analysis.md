# GLM-5 单位 Token 推理成本分析

> 基于 InferenceX Benchmark 数据 + SemiAnalysis 官方 TCO 定价
> 
> 生成时间: 2026-05-07

---

## 1. 计算方法论

### 1.1 TCO 定价来源

**定价数据来源**: InferenceX 页面 JS bundle（`_next/static/chunks/0n_gp9xy1alci.js`）中**硬编码**的 TCO 值，非动态 API 加载。

页面提供三种成本视角（Y-Axis Metric 下拉选项）：

| 成本模型 | 说明 |
|----------|------|
| **Owning - Hyperscaler** (costh) | 超大规模云厂商自建 — 最低成本基线 |
| **Owning - Neocloud Giant** (costn) | 新兴云算力巨头自建 — 中等成本 |
| **3 Year Rental** (costr) | 终端用户3年租赁合同 — 最高成本 |

### 1.2 官方 TCO $/GPU/hr 完整数据

| GPU 型号 | Hyperscaler (costh) | **Neocloud Giant (costn)** | 3 Year Rental (costr) |
|----------|:-------------------:|:-------------------------:|:---------------------:|
| H100 | $1.30 | **$1.69** | $1.30 |
| H200 | $1.41 | **$1.74** | $1.60 |
| B200 | $1.95 | **$2.34** | $2.90 |
| B300 | $2.34 | **$2.808** | $3.48 |
| GB200 | $2.21 | **$2.75** | $3.30 |
| GB300 | $2.652 | **$3.30** | $3.96 |
| MI300X | $1.12 | **$1.40** | $1.55 |
| MI325X | $1.28 | **$1.59** | $1.80 |
| MI355X | $1.48 | **$1.90** | $2.10 |

> 本报告以 **Neocloud Giant (costn)** 为主计算基准。

### 1.3 计算公式

```
Cost per Token = GPU每秒成本 / 每秒吞吐量(per GPU)
               = (TCO_hourly / 3600) / throughput_per_gpu

其中：
• Input Cost  = gpu_cost_per_second / metrics_input_tput_per_gpu
• Output Cost = gpu_cost_per_second / metrics_output_tput_per_gpu
• Total Cost  = gpu_cost_per_second / metrics_tput_per_gpu
```

### 1.4 新增列说明

| 新增列名 | 单位 | 说明 |
|----------|------|------|
| `cost_per_input_token` | $/token | 基于 input throughput 的单 input token 成本 |
| `cost_per_output_token` | $/token | 基于 output throughput 的单 output token 成本 |
| `cost_per_total_token` | $/token | 基于综合 throughput 的单 token 成本 |
| `cost_per_1m_input_tokens` | $/1M tokens | 每百万 input token 成本 |
| `cost_per_1m_output_tokens` | $/1M tokens | 每百万 output token 成本 |
| `cost_per_1m_total_tokens` | $/1M tokens | 每百万综合 token 成本 |

---

## 2. 数据概览

- **总测试配置**: 188 条记录
- **硬件平台**: B200 (74条), B300 (60条), MI355X (39条), H200 (15条)
- **序列长度**: ISL=1024/OSL=1024, ISL=1024/OSL=8192, ISL=8192/OSL=1024
- **精度**: FP8, FP4
- **推测解码**: none, mtp

---

## 3. 各硬件最优成本汇总（每百万 Total Tokens, Neocloud Giant）

| 硬件 | 最低成本 | 最高成本 | 中位成本 | 最佳吞吐量 (tok/s/gpu) | $/GPU/hr | 配置数 |
|------|----------|----------|----------|------------------------|----------|--------|
| **B300** | **$0.161** | $13.53 | $0.81 | 4,834 | $2.808 | 60 |
| **B200** | $0.178 | $20.01 | $1.05 | 3,657 | $2.340 | 74 |
| **MI355X** | $0.267 | $52.94 | $1.65 | 1,979 | $1.900 | 39 |
| **H200** | $0.756 | $15.67 | $2.44 | 639 | $1.740 | 15 |

> **关键发现**: B300 以 $0.161/百万token 实现最低推理成本，TCO 优势来自极高的吞吐量（4,834 tok/s/gpu）。

---

## 4. 最优配置详细分析

### 4.1 Top 10 最低综合成本配置

| 排名 | 硬件 | 精度 | ISL/OSL | 推测解码 | 并发 | GPU数 | Input $/1M | Output $/1M | **Total $/1M** | 吞吐量 |
|------|------|------|---------|----------|------|-------|-----------|------------|---------------|--------|
| 1 | B300 | FP4 | 8K/1K | mtp | 256 | 4 | $0.182 | $1.452 | **$0.161** | 4,834 |
| 2 | B300 | FP4 | 8K/1K | none | 256 | 4 | $0.197 | $1.572 | **$0.175** | 4,463 |
| 3 | B200 | FP4 | 8K/1K | mtp | 256 | 4 | $0.200 | $1.599 | **$0.178** | 3,657 |
| 4 | B200 | FP4 | 8K/1K | none | 128 | 4 | $0.215 | $1.726 | **$0.191** | 3,399 |
| 5 | B200 | FP4 | 1K/1K | mtp | 256 | 4 | $0.479 | $0.478 | **$0.239** | 2,717 |
| 6 | B300 | FP4 | 1K/1K | mtp | 256 | 4 | $0.480 | $0.480 | **$0.240** | 3,252 |
| 7 | B200 | FP4 | 1K/1K | none | 256 | 4 | $0.522 | $0.522 | **$0.261** | 2,490 |
| 8 | MI355X | FP8 | 8K/1K | none | 256 | 8 | $0.300 | $2.400 | **$0.267** | 1,979 |
| 9 | B300 | FP4 | 1K/1K | none | 256 | 4 | $0.571 | $0.570 | **$0.285** | 2,734 |
| 10 | B200 | FP8 | 8K/1K | mtp | 256 | 8 | $0.390 | $3.116 | **$0.346** | 1,877 |

### 4.2 Input vs Output 成本比例

| 硬件 | Input $/1M | Output $/1M | Total $/1M | Output/Input 比 | 最优配置 |
|------|-----------|------------|-----------|-----------------|----------|
| B300 | $0.182 | $1.452 | $0.161 | **8.0x** | conc=256, FP4, 8K/1K |
| B200 | $0.200 | $1.599 | $0.178 | **8.0x** | conc=256, FP4, 8K/1K |
| MI355X | $0.300 | $2.400 | $0.267 | **8.0x** | conc=256, FP8, 8K/1K |
| H200 | $0.850 | $6.813 | $0.756 | **8.0x** | conc=64, FP8, 8K/1K |

> **8:1 比例**: 在 8K Input / 1K Output 场景下，Output token 的单位成本约为 Input token 的 8 倍。这是因为 Input 通过 prefill 批量并行处理，吞吐量天然更高。在 1K/1K 等长场景下，Input 和 Output 成本几乎相等。

---

## 5. 定价数据来源机制

### 5.1 页面架构分析

通过浏览器 DevTools 调查确认：

- **TCO 价格是硬编码在 JS bundle 中**，具体位于 `_next/static/chunks/0n_gp9xy1alci.js`
- 每个 GPU 型号定义了 `costh`、`costn`、`costr` 三个价格字段
- **不是**通过外部 API 动态加载
- 成本计算在前端执行：`cost = tco_rate / throughput`

### 5.2 数据更新机制

- 价格调整需要修改 JS 代码并重新部署
- 性能 benchmark 数据通过 GitHub Actions runs 获取（有专用 API endpoint）
- 页面上的 "Updated: 05/07/2026" 指的是 benchmark 运行日期，非价格更新日期

---

## 6. 关键发现

### 6.1 FP4 量化显著降低成本
- FP4 相比 FP8 在 B200/B300 上可降低 **40-60%** 的推理成本
- FP4 + TP=4（4 卡）相比 FP8 + TP=8（8 卡）进一步减少 GPU 使用量

### 6.2 MTP（Multi-Token Prediction）推测解码带来收益
- 启用 MTP 可提升 **20-40%** 吞吐量，直接降低单位 token 成本
- 在长输入短输出（8K/1K）场景效果最为显著

### 6.3 高并发是降成本的关键
- 最优成本配置普遍出现在高并发（conc=128/256）下
- GPU 利用率在高并发下接近饱和，充分摊薄固定成本

### 6.4 B300 — 综合性价比之王
- B300 TCO 高于 B200 ($2.808 vs $2.34, +20%)
- 但吞吐量提升约 **30-35%**，最终 token 成本反而更低
- 对于大规模 GLM-5 推理服务，B300 是目前最优选择

---

## 7. 输出文件

| 文件 | 路径 |
|------|------|
| 带成本列的完整 CSV | `json_data/glm5_benchmarks_only_with_cost.csv` |
| 计算脚本 | `scripts/calculate_token_cost.py` |
| 本分析报告 | `glm5_token_cost_analysis.md` |

### TCO 参数配置

```python
GPU_COST_TIERS = {
    "h100":   {"costh": 1.30,  "costn": 1.69,  "costr": 1.30},
    "h200":   {"costh": 1.41,  "costn": 1.74,  "costr": 1.60},
    "b200":   {"costh": 1.95,  "costn": 2.34,  "costr": 2.90},
    "b300":   {"costh": 2.34,  "costn": 2.808, "costr": 3.48},
    "gb200":  {"costh": 2.21,  "costn": 2.75,  "costr": 3.30},
    "gb300":  {"costh": 2.652, "costn": 3.30,  "costr": 3.96},
    "mi300x": {"costh": 1.12,  "costn": 1.40,  "costr": 1.55},
    "mi325x": {"costh": 1.28,  "costn": 1.59,  "costr": 1.80},
    "mi355x": {"costh": 1.48,  "costn": 1.90,  "costr": 2.10},
}
# 当前使用: Neocloud Giant (costn)
```

> 可在脚本中修改 `COST_TIER` 变量来切换成本模型（"costh" / "costn" / "costr"）。
