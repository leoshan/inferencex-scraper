# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

这是 OpenRouter 模型调用量和应用场景趋势跟踪系统，包含数据采集、分析和可视化功能。

## 快速启动

### 后端 API (端口 8005)

```bash
cd web/api
uvicorn main:app --reload --port 8005
```

### 前端 (端口 5175)

```bash
cd web/frontend
npm install
npm run dev
```

访问 http://localhost:5175 查看前端界面。

## 端口配置

| 服务 | 端口 |
|------|------|
| 后端 API | 8005 |
| 前端 Dev | 5175 |

## 项目结构

```
inferencex-scraper/
├── crawler/                    # 数据采集模块
│   ├── openrouter/             # OpenRouter 爬虫
│   │   ├── get_app_usage/      # 应用使用量采集
│   │   ├── get_model_details/  # 模型详情采集
│   │   └── trend_tracker/      # 趋势跟踪调度器
│   ├── artificialanalysis/     # Artificial Analysis 爬虫
│   └── inferencex/             # InferenceX 爬虫
│
├── analysis/                   # 数据分析模块
│   └── service/                # 分析服务
│       ├── trend_analyzer.py   # 趋势分析
│       ├── anomaly_detector.py # 异常检测
│       ├── cluster_analyzer.py # 聚类分析
│       ├── app_analyzer.py     # 应用场景分析
│       └── comparison_analyzer.py # 竞品对比分析
│
├── data/                       # 数据模块
│   ├── models.py               # ORM 模型
│   └── db/                     # SQLite 数据库
│
└── web/                        # Web 模块
    ├── api/                    # FastAPI 后端
    └── frontend/               # React 前端
```

## 主要功能

1. **模型对比** - `/comparison` 多模型趋势对比、指标对比表、热力图
2. **场景分析** - `/categories` 应用场景自动分类、分布饼图、趋势图
3. **模型趋势** - `/trends` 单模型趋势分析、移动平均、异常检测
4. **应用分布** - `/apps` 应用使用分布、饼图
5. **异常告警** - `/alerts` 异常检测告警列表

## API 端点

- `GET /api/v1/trends/models/{model_slug}` - 获取模型趋势
- `GET /api/v1/trends/rankings` - 模型排名
- `GET /api/v1/trends/category-trends` - 场景分类趋势
- `POST /api/v1/comparison/models` - 多模型对比
- `GET /api/v1/comparison/heatmap` - 调用量热力图

## 开发说明

- 后端使用 FastAPI + SQLite
- 前端使用 React + TypeScript + Ant Design + ECharts
- 数据采集使用 APScheduler 定时调度
- 中文注释，面向中文开发者