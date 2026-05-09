import pandas as pd
import json

df = pd.read_csv('/root/inferencex-scraper/json_data/inference_max_benchmarks.csv')

# Look at the columns to see how model is identified
print(df.columns)

# Usually it's 'model' or 'model_name'
model_col = 'model' if 'model' in df.columns else 'model_name'

glm5_df = df[df[model_col] == 'glm5']
out_path = '/root/inferencex-scraper/json_data/glm5_performance.csv'
glm5_df.to_csv(out_path, index=False)

print(f'Extracted {len(glm5_df)} rows for glm5 into {out_path}')

# Create markdown report
report_content = f"""# GLM-5 性能数据提取报告

已成功从 `inference_max_benchmarks.csv` 中提取了 **GLM-5** 的性能基准数据。

- **总提取行数**: {len(glm5_df)} 条记录
- **存储路径**: `{out_path}`

您可以直接查看该 CSV 文件以获取详细的 GLM-5 各硬件、框架和并发级别的吞吐量与延迟数据。
"""

with open('/root/inferencex-scraper/GLM-5_Performance_Report.md', 'w') as f:
    f.write(report_content)

print("Report saved.")
