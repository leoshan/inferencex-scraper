# 目录整理完成报告 (Directory Cleanup Report)

## 整理内容总结

为了解决目录混乱的问题，我执行了以下整理操作：

### 1. 结构化目录调整
- **创建新目录**:
    - `data/raw/`: 用于存储原始抓取的数据。
    - `reports/archive/`: 用于归档旧的 HTML 页面和报告。
    - `scripts/glm5/`: 归类 GLM5 专项脚本。
- **符号链接**:
    - 创建了 `json_data` -> `data/raw/json_data` 的符号链接，以确保现有脚本的硬编码路径不会失效。

### 2. 文件移动清单
| 类别 | 文件 | 新位置 |
| :--- | :--- | :--- |
| **脚本** | `extract_glm5.py`, `join_glm_data.py` | `scripts/glm5/` |
| **报告** | `inference_data_report.html` | `reports/` |
| **归档** | `inference_page.html`, `page.html` | `reports/archive/` |
| **数据** | 整个 `json_data/` 目录 | `data/raw/json_data/` |

### 3. 文档更新
- 更新了根目录下的 `README.md`，反映了最新的目录结构。

## 整理后的目录预览
```text
inferencex-scraper/
├── data/           # 结构化数据
├── reports/        # 可视化报告
├── scripts/        # 核心脚本 (含子目录)
├── openrouter/     # 独立模块
├── InferenceX/     # 子模块
└── json_data       # (Symlink) 兼容性链接
```

---
**提示**: 如果您发现任何脚本执行异常，请优先检查路径引用。目前的符号链接方案应能解决大部分路径问题。
