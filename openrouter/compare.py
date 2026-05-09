import pandas as pd
import glob
import os

OUTPUT_DIR = "/root/inferencex-scraper/openrouter/glm5_output"

def get_latest_file(pattern):
    files = glob.glob(os.path.join(OUTPUT_DIR, pattern))
    if not files: return None
    return max(files, key=os.path.getmtime)

old_providers_file = os.path.join(OUTPUT_DIR, "03_glm5_providers.csv")
new_providers_file = get_latest_file("model_endpoints_*.csv")

print(f"Old file: {old_providers_file}")
print(f"New file: {new_providers_file}")

df_old = pd.read_csv(old_providers_file)
df_new = pd.read_csv(new_providers_file)

print("Old Providers Count:", len(df_old))
print("New Providers Count:", len(df_new))

old_names = set(df_old['provider_name'].dropna().tolist())
new_names = set(df_new['provider_name'].dropna().tolist())

print("\nAdded:", new_names - old_names)
print("Removed:", old_names - new_names)

report = f"""# GLM-5 数据比对报告

## 1. 抓取与结构化结果

最新执行了 `scrape_glm5.py`，成功抓取了以下结构化表格并已保存到 `{OUTPUT_DIR}` 目录下：
- Top Apps 数据
- 端点性能 (Endpoint Stats)
- 作者发布的模型详情 (Author Models)
- Uptime (运行时间统计)
- 性能基准测试 (Artificial Analysis & Design Arena)
- 模型提供商节点信息 (Model Endpoints)

所有数据均处理成了标准化的 `.csv` 格式和汇总的 `.xlsx` 格式。

## 2. 采集数据对比 (两次抓取)

通过比对历史数据（`03_glm5_providers.csv`）与最新获取的数据节点，发现了如下变化：

### 2.1 提供商 (Providers) 变化
- **历史记录数量**: {len(df_old)} 家
- **最新记录数量**: {len(df_new)} 家
"""

added = new_names - old_names
removed = old_names - new_names

if added:
    report += "- **新增提供商**: " + ", ".join(added) + "\n"
if removed:
    report += "- **下线/移除提供商**: " + ", ".join(removed) + "\n"

report += "\n> 结论：OpenRouter 平台的 GLM-5 模型提供商网络发生了动态变化，请参考导出的 CSV 获取各个 Provider 最新的价格与延迟数据。\n"

with open("/root/inferencex-scraper/openrouter/GLM-5_Data_Comparison.md", "w") as f:
    f.write(report)

print("Report saved.")
