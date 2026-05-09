# GLM-5 采集数据比对与结构化报告

## 1. 结构化处理

最新从 OpenRouter API 抓取了 `z-ai/glm-5` 模型的 Provider 节点信息。
数据已结构化处理并保存为 CSV 表格：`openrouter/glm5_output/03_glm5_providers_new.csv`。

本次共提取到 **17** 个 Provider 节点。

## 2. 数据比对结果 (最新 vs 历史)

与历史抓取数据（`03_glm5_providers.csv`）相比，平台的服务商发生如下变化：

- **历史节点数量**: 18 个
- **最新节点数量**: 17 个

### 2.1 提供商 (Providers) 动态变化

- **提供商名单未发生增减。**

### 2.2 详细提供商列表与价格 (最新)

| provider_name   |   context_length | input_price_per_m   | output_price_per_m   | quantization   |
|:----------------|-----------------:|:--------------------|:---------------------|:---------------|
| GMICloud        |           202752 | $0.60               | $1.92                | fp8            |
| DeepInfra       |           202752 | $0.60               | $2.08                | fp4            |
| StreamLake      |           200000 | $0.65               | $2.08                | unknown        |
| Baidu           |           202752 | $0.70               | $2.24                | fp8            |
| SiliconFlow     |           204800 | $0.95               | $2.55                | fp8            |
| Chutes          |           202752 | $0.95               | $2.55                | fp8            |
| BaseTen         |           202800 | $0.95               | $3.15                | fp4            |
| AtlasCloud      |           202752 | $0.95               | $3.15                | fp8            |
| Amazon Bedrock  |           202752 | $1.00               | $3.20                | unknown        |
| Friendli        |           202752 | $1.00               | $3.20                | unknown        |
| Novita          |           202800 | $1.00               | $3.20                | fp8            |
| Z.AI            |           202752 | $1.00               | $3.20                | unknown        |
| Parasail        |           202752 | $1.00               | $3.20                | fp8            |
| Together        |           202752 | $1.00               | $3.20                | unknown        |
| Venice          |           198000 | $1.00               | $3.20                | fp8            |
| Fireworks       |           202752 | $1.00               | $3.20                | unknown        |
| Phala           |           202752 | $1.20               | $3.50                | unknown        |