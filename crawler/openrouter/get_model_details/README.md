# OpenRouter API 爬虫 - Minimax 模型数据收集

基于 Scrapling 框架的 OpenRouter API 数据爬虫，用于获取 Minimax 模型在 OpenRouter 平台上的完整数据。

## 项目简介

本项目是一个专业的 API 数据采集工具，专门用于获取 OpenRouter 平台上 Minimax 模型的相关数据。通过 Scrapling 框架实现高效、稳定的数据采集，支持多个 API 端点的批量获取和结构化数据导出。

## 主要特性

- **全面 API 覆盖**：支持 OpenRouter 平台上 9 个核心 API 端点的数据采集
- **智能数据解析**：使用 extract.py 中的专业解析函数处理复杂的嵌套 JSON 数据结构
- **多工作表 Excel 导出**：将所有数据整理到 Excel 的不同工作表，便于分析
- **原始数据保存**：自动保存所有 API 的原始响应，便于回溯和调试
- **错误处理完善**：单个 API 失败不影响其他数据的采集
- **Scrapling 框架**：使用先进的 Scrapling 库绕过反爬虫机制，确保数据采集成功率

## 系统要求

- Python 3.10 或更高版本
- Windows/Linux/macOS 系统

## 安装指南

### 1. 安装依赖包

```bash
pip install pandas openpyxl
```

### 2. 安装 Scrapling 框架

```bash
pip install "scrapling[fetchers]"
```

### 3. 安装浏览器依赖

```bash
scrapling install
```

如果遇到问题，可以强制重新安装：

```bash
scrapling install --force
```

## 使用方法

### 1. 运行主爬虫脚本

```bash
cd D:\ai\crawler\byrequest
python minimax_api_crawler.py
```

### 2. 运行过程说明

脚本会依次执行以下步骤：

1. **检查依赖**：验证 Scrapling 库和解析函数是否可用
2. **获取所有 API 数据**：依次调用 9 个 API 端点
3. **保存原始响应**：将每个 API 的原始 JSON 响应保存到文本文件
4. **解析数据**：使用 extract.py 中的解析函数处理每个 API 的响应
5. **生成 Excel 文件**：将所有解析结果保存到 Excel 的不同工作表
6. **显示数据摘要**：在控制台显示每个工作表的数据统计信息

### 3. 输出文件

运行成功后，会生成以下文件：

1. **Excel 数据文件**：`openrouter_api_data_YYYYMMDD_HHMMSS.xlsx`
2. **原始响应文件**：`raw_response_*_YYYYMMDD_HHMMSS.txt`（每个 API 一个）

## API 端点列表

脚本会自动获取以下 9 个 API 端点的数据：

### 1. top-apps-for-model（核心 API）
- **URL**: https://openrouter.ai/api/frontend/stats/top-apps-for-model?permaslug=minimax%2Fminimax-m2.7-20260318&variant=standard
- **功能**: 获取使用 MiniMax M2.7 模型的 Top 应用列表（总 token 排名）以及模型每日聚合用量
- **解析结果**:
  - `top_apps`：应用排名数据
  - `top_apps_chart`：每日聚合用量数据

### 2. endpoint-stats（核心 API）
- **URL**: https://openrouter.ai/api/frontend/stats/endpoint?permaslug=minimax%2Fminimax-m2.7-20260318&variant=standard
- **功能**: 获取模型端点的实时性能统计（吞吐量、延迟、请求数、状态）
- **解析结果**: `endpoint_stats`：端点性能统计数据

### 3. author-models（核心 API）
- **URL**: https://openrouter.ai/api/frontend/author-models?authorSlug=minimax
- **功能**: 获取指定作者（MiniMax）的所有模型元数据（名称、描述、端点、定价等）
- **解析结果**: `author_models`：作者模型列表

### 4. 所有模型列表
- **URL**: https://openrouter.ai/api/frontend/models
- **功能**: 获取平台所有可用模型的列表
- **解析结果**: `all_models`：所有模型列表

### 5. 所有提供商
- **URL**: https://openrouter.ai/api/frontend/all-providers
- **功能**: 获取所有模型提供商的元数据
- **解析结果**: `all_providers`：所有提供商列表

### 6. uptime 统计
- **URL**: https://openrouter.ai/api/frontend/stats/uptime-recent?permaslug=minimax%2Fminimax-m2.7-20260318
- **功能**: 获取模型最近一段时间的 uptime 统计数据
- **解析结果**: `uptime_recent`：uptime 统计数据

### 7. 提供商偏好
- **URL**: https://openrouter.ai/api/internal/v1/provider-preferences
- **功能**: 获取用户或默认的提供商偏好设置
- **解析结果**: `provider_preferences`：提供商偏好设置

### 8. Artificial Analysis 基准
- **URL**: https://openrouter.ai/api/internal/v1/artificial-analysis-benchmarks?slug=minimax%2Fminimax-m2.7-20260318
- **功能**: 获取模型在 Artificial Analysis 上的基准评分
- **解析结果**: `artificial_analysis_benchmarks`：Artificial Analysis 基准评分

### 9. Design Arena 基准
- **URL**: https://openrouter.ai/api/internal/v1/design-arena-benchmarks?slug=minimax%2Fminimax-m2.7-20260318
- **功能**: 获取模型在 Design Arena 上的基准评分
- **解析结果**: `design_arena_benchmarks`：Design Arena 基准评分

## Excel 输出结构

生成的 Excel 文件包含多个工作表，每个工作表对应一个 API 的解析结果：

| 工作表名称 | 数据内容 | 行数示例 | 列数示例 |
|-----------|----------|----------|----------|
| `top_apps` | Top 应用排名数据 | 5 行 | 15 列 |
| `top_apps_chart` | 每日聚合用量数据 | 23 行 | 14 列 |
| `author_models` | 作者模型元数据 | 8 行 | 76 列 |
| `endpoint_stats` | 端点性能统计 | 2 行 | 65 列 |
| `all_models` | 所有模型列表 | 取决于 API 返回 | 取决于解析 |
| `all_providers` | 所有提供商列表 | 取决于 API 返回 | 取决于解析 |
| `uptime_recent` | uptime 统计数据 | 取决于 API 返回 | 取决于解析 |
| `provider_preferences` | 提供商偏好设置 | 取决于 API 返回 | 取决于解析 |
| `artificial_analysis_benchmarks` | Artificial Analysis 基准 | 取决于 API 返回 | 取决于解析 |
| `design_arena_benchmarks` | Design Arena 基准 | 取决于 API 返回 | 取决于解析 |

## 文件说明

### 1. `minimax_api_crawler.py`（主脚本）
- **功能**: 主爬虫脚本，负责获取所有 API 数据并生成 Excel 文件
- **主要函数**:
  - `fetch_api_data()`: 使用 Scrapling 获取 API 数据
  - `save_raw_response()`: 保存原始 API 响应
  - `find_latest_files()`: 查找最新保存的原始响应文件
  - `create_excel_with_sheets()`: 创建包含多个工作表的 Excel 文件
  - `main()`: 主函数，协调整个数据采集流程

### 2. `extract.py`（解析函数库）
- **功能**: 包含所有 API 的解析函数，将复杂的 JSON 数据结构转换为扁平化的 DataFrame
- **主要函数**:
  - `parse_top_apps_json()`: 解析 top-apps-for-model API（返回两个 DataFrame）
  - `parse_author_models()`: 解析 author-models API
  - `parse_endpoint_stats()`: 解析 endpoint-stats API
  - `parse_models_to_df()`: 解析所有模型列表 API
  - `parse_frontend_all_providers()`: 解析所有提供商 API
  - `parse_uptime_recent()`: 解析 uptime 统计数据
  - `parse_provider_preferences()`: 解析提供商偏好设置
  - `parse_artificial_analysis_benchmark()`: 解析 Artificial Analysis 基准
  - `parse_design_arena_benchmark()`: 解析 Design Arena 基准

### 3. 原始响应文件
- **命名格式**: `raw_response_{api_path}_{timestamp}.txt`
- **示例**: `raw_response_api_frontend_stats_top-apps-for-model_permaslug_minimax%2Fminimax-m2.7-20260318_variant__20260410_102713.txt`
- **用途**: 保存 API 的原始 JSON 响应，便于调试和回溯

## 常见问题

### Q1: Scrapling 安装失败
**解决方案**:
```bash
# 尝试使用管理员权限安装
sudo pip install "scrapling[fetchers]"

# 或者使用清华镜像源
pip install "scrapling[fetchers]" -i https://pypi.tuna.tsinghua.edu.cn/simple

# 如果浏览器安装失败，尝试强制重新安装
scrapling install --force
```

### Q2: API 请求失败
**可能原因**:
1. 网络连接问题
2. OpenRouter API 限流
3. 请求头不匹配

**解决方案**:
1. 检查网络连接
2. 等待一段时间后重试
3. 检查 `minimax_api_crawler.py` 中的请求头配置

### Q3: 解析函数导入失败
**解决方案**:
确保 `extract.py` 文件与 `minimax_api_crawler.py` 在同一目录下，并且包含所有必需的解析函数。

### Q4: Excel 文件生成失败
**解决方案**:
1. 确保已安装 `openpyxl` 库：`pip install openpyxl`
2. 检查文件写入权限
3. 确保没有其他程序正在使用目标 Excel 文件

## 技术实现细节

### 1. Scrapling 框架优势
- **StealthyFetcher**: 使用无头浏览器模拟真实用户行为，绕过反爬虫机制
- **智能重试**: 当 StealthyFetcher 失败时自动回退到普通 Fetcher
- **网络空闲检测**: 等待页面完全加载后再获取数据

### 2. 数据解析策略
- **扁平化处理**: 将嵌套的 JSON 结构转换为扁平的表格结构
- **类型转换**: 自动识别并转换数值类型字段
- **字段前缀**: 为嵌套字段添加前缀避免冲突

### 3. 错误处理机制
- **独立处理**: 每个 API 的失败不影响其他 API 的处理
- **详细日志**: 提供详细的运行日志便于问题排查
- **原始数据保存**: 即使解析失败，原始数据也会被保存

## 性能优化建议

1. **并发请求**: 如果需要提高采集速度，可以考虑使用 Scrapling 的 AsyncFetcher 实现并发请求
2. **代理轮换**: 如果遇到 IP 限制，可以配置 Scrapling 的 ProxyRotator
3. **数据缓存**: 对于不经常变化的数据，可以实现本地缓存机制

## 法律声明

本项目仅用于教育和研究目的。使用本项目时，请遵守：
1. OpenRouter 平台的服务条款
2. 当地的数据采集法律法规
3. robots.txt 文件规定

请合理使用本项目，避免对目标服务器造成过大压力。

## 更新日志

### v1.0.0 (2026-04-10)
- 初始版本发布
- 支持 9 个 OpenRouter API 端点
- 集成 Scrapling 框架
- 实现多工作表 Excel 导出

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目仓库：`D:\ai\crawler\byrequest\`
- 创建 Issue：项目目录下的问题反馈

---

**免责声明**: 本工具仅供学习和研究使用，请勿用于非法用途。使用者需自行承担因使用本工具而产生的所有法律责任。