# FinFlow

**可观测的 LLM 金融分析流水线**：输入一个股票代码，系统自动完成数据准备、多角色分析、报告生成，全程执行过程实时可视、可审计、可复现。

FinFlow 是一个原创项目：基于极简 LLM 框架 PocketFlow 从零构建，不依赖任何重量级 agent 框架。它把"执行过程"变成一等公民——每个节点的状态、输入输出、耗时与失败都被记录、可回放，使 LLM 分析结论可溯源。

## 核心特点

- **轻量**：执行内核基于 PocketFlow（百行级框架），依赖极少（fastapi + openai + pandas）
- **可观测**：自研可观测层——每个节点执行生命周期实时广播事件（WebSocket），落库 SQLite
- **可审计**：报告章节关联数据来源与生成节点，执行过程可回放（V2 完善章节级溯源）
- **可复现**：mock 数据模式 + LLM 结果缓存 + CLI 批量重复实验，离线可完整演示
- **全栈**：FastAPI + WebSocket 后端，React + React Flow 前端控制台

## 研究

FinFlow 不只是工程 demo，它还用作 LLM 金融分析可靠性研究的实验平台：

- [结论一致性研究报告](docs/research/consistency_report.md)：相同输入下重复 10 次，事实性信息相对稳定，但风险、估值区间、投资结论方向存在显著随机性；且 `temperature=0` 贪心解码下结论方向依然 50/50 摇摆
- 实验数据与脚本：`backend/experiments/` + `data/experiments/`（可复现）

## 快速开始

### 一键演示

```powershell
cd C:\Users\LENOVO\Documents\量化\FinFlow
.venv\Scripts\python.exe demo.py
```

然后浏览器打开 http://localhost:5173 ，输入 `AAPL` 或 `MSFT` 生成分析报告。

### 手动启动

```powershell
# 1. 后端 API（127.0.0.1:8000）
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000

# 2. 前端控制台（localhost:5173）
cd frontend
npm run dev
```

### 命令行生成报告

```powershell
.venv\Scripts\python.exe -m backend.cli --ticker AAPL
# 同一 ticker 重复跑 N 次（结论一致性实验，绕过缓存取独立样本）
.venv\Scripts\python.exe -m backend.cli --ticker AAPL --repeat 5 --no-cache
```

## 环境要求

- Python 3.12（项目内 `.venv` 虚拟环境，已配置）
- Node.js 20+ / npm（前端）
- DeepSeek API key：复制 `.env.example` 为 `.env` 并填入 `DEEPSEEK_API_KEY`

## 架构

```
React 前端控制台（DAG 实时可视化）
        │ REST + WebSocket
FastAPI（JobManager 任务状态机 + EventBus）
        │
PocketFlow AsyncFlow（ObservableNode 包装）
  Input → MockData → DataProcessor → TextAgents(×4 并行) → HtmlReport → Done
```

## 目录结构

```
backend/
  app/            FastAPI 路由、JobManager
  flow/           节点、agent、流水线组装（PocketFlow）
  observability/  事件总线、可观测节点、WebSocket 广播
  providers/      数据源抽象（mock）
  report/         HTML 报告渲染
  storage/        SQLite（jobs / events）
  tests/          端到端测试
frontend/         React + Vite + React Flow 控制台
data/
  mock/           内置示例数据（AAPL / MSFT）
  cache/          LLM 结果缓存
  artifacts/      生成的报告
```

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/jobs` | 创建分析任务 `{ticker, mode}` |
| GET | `/api/jobs/{id}` | 任务状态 |
| GET | `/api/jobs/{id}/events` | 全量事件（回放/审计） |
| WS | `/ws/jobs/{id}` | 实时事件流 |
| GET | `/api/jobs/{id}/report` | HTML 报告 |

## 里程碑

- [x] M0 项目骨架
- [x] M1 后端流水线（PocketFlow 节点化 + 4 个分析 agent + DeepSeek）
- [x] M2 可观测层（事件总线 + SQLite + WebSocket）
- [x] M3 前端可视化控制台
- [x] M4 缓存、失败路径、一键演示、README
- [ ] V2：补齐 agent、图表、PDF、真实数据源、回放、章节溯源
- [ ] V3：记忆层（Mem0）、多任务对比、扩展市场

## 文档

- [设计方案](docs/DESIGN.md)
- [结论一致性研究报告](docs/research/consistency_report.md)

## 合规说明

FinFlow 为原创项目。多角色金融分析流程设计受 AI4Finance-Foundation/FinRobot（Apache-2.0）启发，未复制其源码，详见 [NOTICE](NOTICE)。
