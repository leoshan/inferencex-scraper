# 目录整理方案 (Directory Reorganization Plan)

## 当前问题
1. 根目录下散落了一些 Python 脚本和 HTML 报告。
2. 数据文件、脚本、报告的分类不够清晰。
3. `json_data` 目录文件过多，建议归档到 `data/` 下。

## 调整建议

### 1. 结构化目录
创建以下新目录以更好地分类文件：
- `data/`: 存储所有原始和处理后的数据。
    - `data/raw/`: 原始 JSON/HTML 抓取数据（如 `json_data` 目录）。
    - `data/processed/`: 处理后的 CSV/Excel 数据。
- `reports/`: 存储生成的 HTML 报告和分析结果。
    - `reports/archive/`: 存储旧的 HTML 页面抓取。
- `scripts/`: 现有的脚本目录，建议进一步细分。
    - `scripts/glm5/`: 专门存放 GLM5 相关的处理脚本。

### 2. 预定移动文件清单
| 原路径 | 新路径 | 说明 |
| :--- | :--- | :--- |
| `extract_glm5.py` | `scripts/glm5/extract_glm5.py` | 归类 GLM5 脚本 |
| `join_glm_data.py` | `scripts/glm5/join_glm_data.py` | 归类 GLM5 脚本 |
| `inference_data_report.html` | `reports/inference_data_report.html` | 报告归类 |
| `inference_page.html` | `reports/archive/inference_page.html` | 归档原始页面 |
| `page.html` | `reports/archive/page.html` | 归档原始页面 |
| `json_data/` | `data/raw/` | 移动整个数据目录 |

### 3. 其他建议
- **保持现状**: `InferenceX` (子模块) 和 `artificialanalysis` (代码包) 保持不动。
- **文档更新**: 在清理完成后，更新根目录下的 `README.md`。

---
**待执行操作**: 如果您同意上述方案，我将开始执行移动操作并创建相应目录。
