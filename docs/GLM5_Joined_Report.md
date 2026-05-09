# GLM-5 数据联合分析报告 (OpenRouter + InferenceX)

## 1. 数据联查说明
本报告将 **OpenRouter** 的供应商价格数据与 **InferenceX** 的硬件性能数据进行了关联分析。
- **关联键**: `precision` (OpenRouter 的 quantization = InferenceX 的 precision)
- **数据量**: 联查后共生成 1072 条组合记录。

## 2. 价格 vs 性能 概览 (Top 10 组合)

| 供应商 | 硬件 | 精度 | 输入价格 ($/M) | 平均吞吐量 (tokens/s/GPU) |
| :--- | :--- | :--- | :--- | :--- |
| DeepInfra | b300 | fp4 | $0.60 | 1706.45 |
| BaseTen | b300 | fp4 | $0.95 | 1706.45 |
| BaseTen | b200 | fp4 | $0.95 | 1297.53 |
| DeepInfra | b200 | fp4 | $0.60 | 1297.53 |
| SiliconFlow | b300 | fp8 | $0.95 | 866.81 |
| Venice | b300 | fp8 | $1.00 | 866.81 |
| Parasail | b300 | fp8 | $1.00 | 866.81 |
| AtlasCloud | b300 | fp8 | $0.95 | 866.81 |
| Baidu | b300 | fp8 | $0.70 | 866.81 |
| GMICloud | b300 | fp8 | $0.60 | 866.81 |
| Chutes | b300 | fp8 | $0.95 | 866.81 |
| Novita | b300 | fp8 | $1.00 | 866.81 |
| Parasail | b200 | fp8 | $1.00 | 649.22 |
| Novita | b200 | fp8 | $1.00 | 649.22 |
| AtlasCloud | b200 | fp8 | $0.95 | 649.22 |

## 3. 结论
通过将价格与基准性能结合，可以更直观地评估不同服务商的技术方案优劣。
完整的联查结果已保存至: `/root/inferencex-scraper/json_data/glm5_joined_data.csv`
