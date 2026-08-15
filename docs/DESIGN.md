# FinFlow 设计方案

## 可观测的金融研究报告生成流水线（PocketFlow 重构版）

> 项目定位：参考 FinRobot（AI4Finance）的金融分析流程，使用 PocketFlow 重写为轻量、可观测、可审计的流水线，并配套一套实时可视化控制台（前后端全栈）。
>
> 一句话叙事（用于套磁/简历）：**"让 LLM 金融分析流水线可观测、可审计、可复现——每个结论都能追溯到数据、模型与中间产物。"**

---

## 1. 项目定位与目标

### 1.1 我们做什么

输入一个美股代码（ticker），系统自动完成：

1. 抓取财务数据、同业数据、市场数据、公司新闻
2. 数据清洗与指标计算（增长率、预测、估值、敏感性）
3. 8 个 LLM 分析 agent 并行产出结构化分析文本
4. 生成图表、渲染 HTML 报告、导出 PDF
5. **全程可视**：用户在前端实时看到每一个节点的执行状态、输入输出、耗时、重试与失败

### 1.2 与"照抄"的边界（为什么这是自己的项目）

| 部分 | 来源 | 说明 |
|---|---|---|
| 分析流程（7 步流水线）、agent 角色、报告章节 | 参考 FinRobot（Apache 2.0） | 只参考**流程设计**，代码全部自研；README/NOTICE 声明出处 |
| 执行架构 | 自研 | 用 PocketFlow 的 Node/Flow 表达流水线，不依赖 AutoGen / openai-agents |
| 运行时可视化与事件溯源 | **自研（核心增量）** | PocketFlow 核心 100 行无任何事件钩子；官方可视化是静态 D3/Mermaid，无运行时、无回放 |
| 全栈 Web 应用 | 自研 | FastAPI + WebSocket + React 控制台 |
| 可复现性设施 | 自研 | LLM 输出缓存、mock 数据模式、固定 seed、溯源文件导出 |

### 1.3 为什么这个增量有价值

LLM 金融分析的最大问题不是"能不能生成报告"，而是**结论不可信、不可追溯**。FinRobot 新版本质上是黑盒：8 个 agent 各自生成一段文字，然后拼进报告——你不知道哪段文字基于哪份数据、哪个 agent 失败了、报告是否过期。

FinFlow 把"执行过程"变成一等公民：每个结论都带着数据版本、生成节点、耗时与状态。这正好呼应我们在 TradingAgents 里修 look-ahead bias 的叙事——**评估与产出的可信度**。

### 1.4 版本规划（先做 V1 闭环，再做增量）

不追求一次抄全 FinRobot。**V1 的目标是：30 分钟内能演示的完整闭环**（输入 ticker → 看 DAG 实时执行 → 4 个 agent 生成报告 → HTML 报告），其余全部留到后续版本。

#### V1（MVP）——最小可演示闭环

**做：**

- 流程：`Input → MockData → DataProcessor → TextAgentBatch(4 agents) → HtmlReport`
- 数据源：仅 `MockProvider`（内置示例数据，离线开发、演示零成本）
- 4 个核心 agent（对应 FinRobot 角色，精简 prompt）：
  - `company_overview`（公司概览）
  - `valuation_analysis`（财务与估值分析）
  - `risks`（风险分析）
  - `takeaways`（投资要点总结）
- 报告：HTML 单页（数据表格 + 4 个章节文本，**无图表**）
- 可观测层核心：`ObservableNode` + EventBus + WebSocket + SQLite 事件落库
- 前端：任务创建页 + 实时看板（DAG + 节点详情 + 事件日志）+ 报告预览页
- 简单的文件级 LLM 缓存（按 prompt hash，省 DeepSeek 费用）

**明确不做（V2 再做）：**

- real 数据源（FMP / yfinance）
- 补齐 8 个 agent
- 图表、PDF
- 回放动画、trace.json 章节溯源导出

#### V2——补齐与增强

- 补齐 8 个 agent、2-3 类核心图表（股价走势、财务趋势）、PDF 导出
- FMP / yfinance 真实数据源（`mode=real`）
- 事件回放、trace.json 章节溯源
- 失败注入演示（模拟节点失败/重试，展示可视化对异常场景的处理）

#### V3——差异化增量（可选，视时间）

- 记忆层（结合 Mem0）：跨任务记忆，如"分析过的同类公司结论"注入新任务。
  **注意：FinRobot 全仓库无任何记忆层（已核实），这是纯增量而非替换**——FinRobot 的 agent
  每次任务都是失忆状态，无法保持跨任务一致性；这是我们的差异化能力。
- 多任务对比看板（同 ticker 不同模型/数据日期的结果对比）
- A 股数据源

---

## 2. 调研结论（写方案前读过的源码）

### 2.1 PocketFlow（执行框架）

核心文件：`pocketflow/__init__.py`（约 180 行，官方宣传 100 行核心）。

核心抽象：

| 类 | 作用 |
|---|---|
| `BaseNode` | 基类；`params`、`successors`、`next(action)` 建边 |
| `Node` | `prep(shared) → exec(prep_res) → post(shared, prep_res, exec_res)`，返回 action 字符串路由；支持 `max_retries` / `wait` / `exec_fallback` |
| `BatchNode` | 对 items 逐个执行 |
| `AsyncNode` / `AsyncBatchNode` / `AsyncParallelBatchNode` | 异步版；`AsyncParallelBatchNode._exec` 用 `asyncio.gather` 并行 |
| `Flow` / `AsyncFlow` | 持有 `start_node`，`_orch` 循环：执行当前节点 → 用返回的 action 查 `successors` 找下一节点 → 复制节点继续 |

关键事实：

- **节点间共享 `shared` dict**（整个 flow 的上下文，所有节点可读可写）
- **循环天然支持**：节点返回特定 action 即可指回前面的节点（如"重试"边）
- **`AsyncFlow` 混入了 `AsyncNode`**，所以 flow 本身也可以嵌套
- **没有任何事件钩子**：`_run` 内部直接调 `prep/_exec/post`，外部不可感知执行过程 → 这是本项目增量的立足点
- 官方可视化（`cookbook/pocketflow-visualization`）：`flow_to_json` 遍历图结构生成静态 D3 图 + Mermaid，**运行前**可视化；已知 loop 场景渲染报错（issue #107）

### 2.2 FinRobot（流程蓝本）

重点读的是**新版** `finrobot_equity/`（基于 openai-agents 的流水线版），原版 `finrobot/`（AutoGen 群聊版）只做背景参考。

新版流水线（`core/src/create_equity_report.py` + `modules/`）：

```
数据获取（FMP API）
  ├─ 三张报表 + ratios + key metrics        (market_data_api.get_comprehensive_financial_data)
  ├─ 同业 EBITDA / EV-EBITDA                (combine_peer_financial_data)
  ├─ 当前价、目标价、分析师评级、公司简介     (get_comprehensive_company_metrics)
  ├─ 技术指标                               (get_technical_indicators)
  └─ 公司新闻                               (get_company_news)
        ↓
数据处理
  ├─ 历史指标提取 + 增长率 + 预测            (financial_data_processor.calculate_growth_and_forecasts)
  ├─ 估值引擎 DCF/可比                       (valuation_engine)
  ├─ 敏感性分析                              (sensitivity_analyzer)
  ├─ 催化剂分析                              (catalyst_analyzer)
  └─ 新闻整合/零售情绪                        (news_integrator, retail_sentiment_client)
        ↓
8 个 LLM 分析 agent（各输出结构化字段，Pydantic BaseModel）
  tagline / company_overview / investment_overview / valuation_overview
  risks / competitor_analysis / major_takeaways / news_summary
        ↓
图表（chart_generator / enhanced_chart_generator，~15 类图）
        ↓
报告渲染（html_renderer / html_template_professional）+ PDF（pdf_generator / professional_pdf_report）
```

对我们有用的可复用点：

- agent 的职责划分与 prompt 思路（8 个角色）
- 报告章节结构与关键图表类型
- 失败兜底思路（`text_generator_agents._get_fallback_text`：agent 失败时用规则化 fallback 文本）
- FMP / yfinance 数据源封装思路

我们要**去掉**的东西：

- AutoGen / openai-agents / LangChain 依赖（PocketFlow 无任何依赖）
- 60KB 的巨型 `create_equity_report.py`（改为节点化、可读的模块）
- 模板硬编码的 HTML（改为结构化数据 + 渲染层分离）

许可证：FinRobot 为 **Apache 2.0**，重写时保留 NOTICE 声明。

---

## 3. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend（React + Vite + React Flow）                        │
│  ┌──────────┐  ┌────────────────────┐  ┌─────────────────┐  │
│  │ 任务创建页 │  │ 实时看板（DAG+日志） │  │ 报告预览/溯源页   │  │
│  └──────────┘  └────────────────────┘  └─────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────┴──────────────────────────────────────┐
│  Backend（FastAPI）                                           │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────────────────┐  │
│  │ JobManager   │ │ EventBus     │ │ SQLite                │  │
│  │ (任务状态机) │ │ (事件广播)    │ │ jobs/events/artifacts │  │
│  └─────────────┘ └──────────────┘ └───────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ 调用
┌──────────────────────┴──────────────────────────────────────┐
│  Execution Core（PocketFlow AsyncFlow + ObservableNode）     │
│                                                              │
│  Fetch → Process → Analyze(8 agents, parallel) → Chart →     │
│  Report → PDF                                                 │
│                                                              │
│  每个节点执行生命周期 → emit 事件 → EventBus → WebSocket/DB    │
└──────────────────────────────────────────────────────────────┘
```

**设计原则**：

1. **不动 PocketFlow 核心**：通过自定义基类 `ObservableNode` / `ObservableFlow` 实现可观测性，上游更新可平滑跟随
2. **执行与展示解耦**：节点只负责"做事 + 发事件"，不感知前端；展示层通过事件流重建画面
3. **数据分层**：`providers/`（数据源抽象）→ `flow/`（节点逻辑）→ `app/`（API）

---

## 4. 流程 → PocketFlow 节点映射（核心章节）

### 4.1 整体 DAG

```
InputNode
   │
   ▼
┌─────────── 阶段1: 数据获取（AsyncParallelBatchNode，可并行）───────────┐
│  MarketDataNode   NewsNode   PeerDataNode                              │
└───────────┬──────────────────┬─────────────────────────────────────────┘
            ▼                  ▼
┌─────────── 阶段2: 数据处理（部分并行）─────────────────────────────────┐
│  DataProcessorNode  ValuationNode  SensitivityNode  CatalystNode       │
└───────────┬────────────────────────────────────────────────────────────┘
            ▼
┌─────────── 阶段3: 文本分析（AsyncParallelBatchNode × 8 agent）────────┐
│  TextAgentBatchNode（每个 item = 一个 agent 任务）                      │
│  失败重试 → 循环回本节点（演示 loop 可视化）                             │
└───────────┬────────────────────────────────────────────────────────────┘
            ▼
┌─────────── 阶段4/5: 图表与报告 ───────────────────────────────────────┐
│  ChartNode → HtmlReportNode → PdfReportNode → DoneNode                 │
└────────────────────────────────────────────────────────────────────────┘
```

### 4.2 节点规格表

| 节点 | 类型 | 输入（从 shared 取） | 输出（写回 shared） | 失败策略 |
|---|---|---|---|---|
| `InputNode` | AsyncNode | HTTP 请求参数 | `job.params`（ticker、选项） | 参数校验失败 → `invalid` action |
| `MarketDataNode` | AsyncNode | ticker | `financial_data`、`market_metrics` | 重试 2 次；FMP 失败 → mock 降级 |
| `NewsNode` | AsyncNode | ticker | `news_list` | 重试 1 次；失败 → 空列表 + `warning` |
| `PeerDataNode` | AsyncNode | ticker | `peer_ebitda`、`peer_ev_ebitda` | 失败 → 空表 + `warning`（报告注明"无同业数据"） |
| `DataProcessorNode` | AsyncNode | 上述原始数据 | `analysis_df`（历史+增长率+预测） | 重试 2 次；无数据 → `abort` |
| `ValuationNode` | AsyncNode | `analysis_df`、peer | `valuation`（DCF/可比估值） | 重试 2 次 |
| `SensitivityNode` | AsyncNode | `analysis_df` | `sensitivity` | 失败 → 跳过（`warning`） |
| `CatalystNode` | AsyncNode | news、price | `catalysts` | 失败 → 跳过 |
| `TextAgentBatchNode` | AsyncParallelBatchNode | 数据 prompt + 8 个 agent 定义 | `text_sections`（dict） | 每个 item 重试 1 次；仍失败 → fallback 文本 + `warning` |
| `ChartNode` | AsyncNode | 各分析结果 | `charts`（base64 或文件路径） | 单图失败不影响整体（内部 try/except） |
| `HtmlReportNode` | AsyncNode | 全部结果 | `html_report`、`trace.json` | 重试 1 次 |
| `PdfReportNode` | AsyncNode | `html_report` | `pdf_path` | 失败 → 仅提供 HTML（`warning`） |
| `DoneNode` | AsyncNode | — | `job.status = succeeded` | — |

### 4.3 动作路由（PocketFlow 的 action 机制）

- `InputNode`：`valid` → MarketDataNode；`invalid` → End
- `DataProcessorNode`：`abort` → End（失败态）；默认 → 阶段 2 并行组
- `TextAgentBatchNode`：`retry` → 回到自身（存在失败 agent 且剩余重试次数 > 0）；`done` → ChartNode
- 任意节点 `error` → `ErrorHandlerNode`（记录错误、置失败状态）→ End

### 4.4 并行组怎么实现

阶段 1 与阶段 2 的并行有两种实现，方案选择 **A**：

- **A（推荐）**：`AsyncParallelBatchNode`，把"任务列表"放进 `shared`，每个 item 是 `{node_type, params}`，`exec` 内按 item 分发到对应处理函数。实现简单，且天然匹配 PocketFlow 的并行批处理。
- **B**：多个独立节点 + Flow 组合（每个子任务一个 Node，用 `AsyncFlow` 嵌套）。结构更"纯"，但建图繁琐。

阶段 3 的 8 个 agent 用 `AsyncParallelBatchNode`：items = 8 个 agent 任务，`asyncio.gather` 并行调用 LLM，**一个 agent 失败不影响其他 agent**（`BatchNode._exec` 逐 item 执行，我们在 item 内部捕获异常并标记）。

### 4.5 V1 的简化 DAG（实际第一版只实现这个）

```
InputNode
   │ valid
   ▼
MockDataNode（一次产出财务数据 + 市场指标 + 新闻，mock 模式合并数据获取）
   │
   ▼
DataProcessorNode（清洗 + 关键指标 + 简单预测）
   │
   ▼
TextAgentBatchNode（AsyncParallelBatchNode × 4 agents，并行调用 DeepSeek）
   │ done
   ▼
HtmlReportNode（4 个章节 + 数据表格 → 单页 HTML）
   │
   ▼
DoneNode
```

V1 只有 6 个节点、4 个 agent，但**完整的可观测链路（节点事件 → WebSocket → 前端 DAG）从第一天就有**——这是产品核心，不能放到后面。数据获取的 3 个节点合并成 1 个 `MockDataNode`，数据处理保留 1 个节点，图表/PDF 节点整个砍掉。

---

## 5. 可观测层设计（核心增量）

### 5.1 ObservableNode 基类

```python
class ObservableNode(AsyncNode):
    """在 PocketFlow 生命周期各阶段发事件，不修改框架源码。"""

    def __init__(self, event_bus=None, node_id=None, max_retries=1, wait=0):
        super().__init__(max_retries=max_retries, wait=wait)
        self.event_bus = event_bus        # 注入事件总线（默认 no-op）
        self.node_id = node_id or uuid4().hex
        self.name = type(self).__name__

    async def prep_async(self, shared):
        self._emit("node_started", {})
        return await super().prep_async(shared)

    async def exec_async(self, prep_res):
        self._emit("node_exec_started", {"prep_summary": summarize(prep_res)})
        t0 = time.perf_counter()
        try:
            result = await self._do_exec(prep_res)
        except Exception as e:
            self._emit("node_failed", {"error": str(e), "retry": self.cur_retry})
            raise
        self._emit("node_exec_finished", {
            "elapsed_ms": (time.perf_counter() - t0) * 1000,
            "output_summary": summarize(result),
        })
        return result

    async def post_async(self, shared, prep_res, exec_res):
        action = await super().post_async(shared, prep_res, exec_res)
        self._emit("node_finished", {"action": action, "elapsed_ms": ...})
        return action
```

`ObservableFlow(AsyncFlow)` 同样在 `_run_async` 前后发 `flow_started` / `flow_finished` / `flow_failed`。

### 5.2 事件类型与载荷

| 事件 | 触发时机 | 关键字段 |
|---|---|---|
| `job_created` | 任务入队 | job_id, params |
| `flow_started` / `flow_finished` | 整个流水线 | job_id, elapsed_ms, status |
| `node_started` | 节点 prep 前 | node_id, name |
| `node_exec_started` | exec 开始 | prep 摘要 |
| `node_output` | exec 结束 | 输出摘要 |
| `node_finished` | post 结束 | 路由 action, 耗时 |
| `node_failed` | exec 抛异常 | error, retry 次数 |
| `node_retrying` | 重试前 | retry, wait |
| `node_skipped` | 可选节点跳过 | 原因 |
| `job_finished` | 全部完成 | report 路径, 总耗时 |

### 5.3 摘要策略（避免把 DataFrame 塞进事件）

- `summarize(obj)`：DataFrame → `{shape, columns, head_n_rows(截断), key_metrics}`；dict/list → 截断到 N 项；文本 → 前 500 字符
- 完整中间产物按 `job_id/node_id` 写入 `artifacts/`（JSON/CSV），事件里只放摘要
- 前端想看完整输出时，调 `GET /api/jobs/{id}/nodes/{node_id}/artifact`

### 5.4 事件链路

```
ObservableNode._emit(event)
   → EventBus.publish(event)
      ├─ → WebSocketBroadcaster → 推送 /ws/jobs/{job_id}（实时）
      ├─ → SQLite events 表（持久化，供回放与审计）
      └─ → 内存环形缓冲（最近 N 条，供新订阅者补发）
```

### 5.5 回放与审计（差异化亮点）

- **回放**：`GET /api/jobs/{id}/events` 返回全量事件序列，前端按时间轴重放 DAG 状态流转（"看回放"功能）
- **审计/溯源**：`HtmlReportNode` 额外生成 `trace.json`——报告每个章节关联 `{数据源、数据日期、生成节点、agent 名、模型、耗时、状态}`；页面底部提供"查看溯源"入口
- 报告首页自动标注：**数据截止日期、数据源（FMP/mock）、模型版本、生成时间**——直接对应"可复现性"

---

## 6. 后端设计（FastAPI）

### 6.1 API 一览

| 方法 | 路径 | 作用 |
|---|---|---|
| POST | `/api/jobs` | 创建任务 `{ticker, mode: real/mock, model}` → 返回 job_id |
| GET | `/api/jobs/{id}` | 任务状态（queued/running/succeeded/failed） |
| GET | `/api/jobs/{id}/events` | 全量事件（回放） |
| WS | `/ws/jobs/{id}` | 实时事件流（入队后订阅；支持断线重连补发） |
| GET | `/api/jobs/{id}/nodes/{node_id}/artifact` | 某节点完整中间产物 |
| GET | `/api/jobs/{id}/report` | HTML 报告 |
| GET | `/api/jobs/{id}/report.pdf` | PDF |
| GET | `/api/jobs/{id}/trace` | trace.json |
| GET | `/api/meta/providers` | 可用数据源与状态（用于前端展示 mock/real） |

### 6.2 任务状态机

```
queued ──▶ running ──▶ succeeded
   │          │
   └──────────┴──▶ failed
```

- 后端 `JobManager` 维护 `asyncio.Task`，同一时刻最多运行 K 个任务（默认 2，避免 LLM 并发成本失控）
- WebSocket 连接先收到 `job_created`，断线重连时用 `events` 表补发错过的消息

### 6.3 SQLite Schema（简表）

```sql
jobs(id TEXT PK, ticker TEXT, mode TEXT, model TEXT, status TEXT,
     created_at TEXT, finished_at TEXT, report_path TEXT)
events(id INTEGER PK AUTOINCREMENT, job_id TEXT, seq INTEGER, ts TEXT,
       type TEXT, payload TEXT /* JSON */)
artifacts(job_id TEXT, node_id TEXT, kind TEXT, path TEXT)
```

---

## 7. 前端设计

### 7.1 技术选型

- React + Vite + Tailwind CSS
- **React Flow**（现成的 DAG 画布组件，MIT）：节点状态着色、边标签显示 action、拖动布局
- WebSocket 客户端（原生或 `useWebSocket` 轻封装）

### 7.2 页面与组件

**页面 1：任务创建**

- ticker 输入、模式选择（real/mock）、模型选择（DeepSeek 默认）
- 提交 → 跳转看板页

**页面 2：实时看板（核心页面）**

- 左侧：DAG 画布
  - 节点状态配色：等待（灰）/ 运行中（蓝/脉冲）/ 成功（绿）/ 失败（红）/ 重试中（橙）
  - 节点上显示耗时；边标签显示 action（`retry`、`done`…）
  - 点击节点 → 右侧抽屉：输入摘要、输出摘要、完整产物、错误信息
- 右侧：事件日志流（滚动）+ 运行统计（总耗时、LLM 调用次数、token 估算）
- 顶部：任务状态徽章 + "回放"按钮（按事件序列重放动画）

**页面 3：报告预览**

- iframe/HTML 渲染报告
- 底部"溯源"面板：章节 ↔ 数据来源映射表
- 下载 PDF / 导出 trace.json

### 7.3 前端状态模型

```ts
type FlowEvent =
  | { type: "node_started"; nodeId: string; name: string }
  | { type: "node_finished"; nodeId: string; action: string; elapsedMs: number }
  | { type: "node_failed"; nodeId: string; error: string; retry: number }
  | ...

// 前端用一个 reducer 维护：
// { jobId, status, nodeStates: Record<nodeId, NodeState>, events: FlowEvent[] }
```

---

## 8. 数据源与 LLM

### 8.1 DataProvider 抽象

```python
class DataProvider(ABC):
    def get_financial_statements(self, ticker) -> dict: ...
    def get_peer_data(self, ticker) -> dict: ...
    def get_market_metrics(self, ticker) -> dict: ...
    def get_news(self, ticker) -> list: ...

class FMPProvider(DataProvider): ...   # Financial Modeling Prep API（FinRobot 同款）
class MockProvider(DataProvider): ...  # 内置示例数据（CSV/JSON），离线可用
class YFinanceProvider(DataProvider): ...  # 可选，yfinance 包
```

- `mode=mock` 时用 MockProvider（开发、演示、测试都在 mock 下跑）
- 环境变量 `FMP_API_KEY` 存在才启用 FMPProvider
- 报告里永远标注实际使用的数据源与数据日期（可复现性的一部分）

### 8.2 LLM：DeepSeek

- 用 `openai` SDK（DeepSeek 兼容 OpenAI 协议），`base_url=https://api.deepseek.com`
- 结构化输出：每个 agent 的 response model 用 Pydantic 定义（继承 FinRobot 的字段思路，重新设计 prompt），通过 JSON schema 强制结构化
- 失败处理：单个 agent 重试 1 次 → fallback 文本 → 报告对应章节标注"生成失败（fallback）"

### 8.3 缓存（成本与可复现）

- 缓存键：`hash(ticker + agent + data_hash + model + prompt_version)`
- 命中缓存的事件里带 `cached: true`，前端可见
- 缓存目录：`data/cache/`，Git 忽略

---

## 9. 目录结构（目标态）

> V1 实际只使用其中 `flow/`、`observability/`、`providers/mock.py`、`report/html.py`、`app/` 与 `frontend/` 的核心子集；FMP、yfinance、PDF、charts、trace 目录先建占位或后建。

```
FinFlow/
├── docs/
│   └── DESIGN.md
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── api.py             # REST 路由
│   │   ├── ws.py              # WebSocket 路由
│   │   └── job_manager.py     # 任务状态机
│   ├── flow/
│   │   ├── nodes.py           # 各阶段节点（Input/Market/News/Peer/Process/...）
│   │   ├── agents.py          # 8 个 agent 的 prompt 与 response model
│   │   └── pipeline.py        # build_report_flow() 组装 DAG
│   ├── observability/
│   │   ├── event_bus.py
│   │   ├── observable.py      # ObservableNode / ObservableFlow
│   │   └── summarize.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── fmp.py
│   │   ├── mock.py
│   │   └── yfinance_provider.py
│   ├── storage/
│   │   ├── db.py
│   │   └── artifacts.py
│   ├── report/
│   │   ├── charts.py
│   │   ├── html.py
│   │   ├── pdf.py
│   │   └── trace.py
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/             # CreateJob / Dashboard / Report
│   │   ├── components/        # DagCanvas, NodeCard, EventLog, TracePanel...
│   │   ├── store/             # reducer + ws client
│   │   └── App.tsx
│   └── package.json
├── data/
│   ├── mock/                  # 内置示例数据
│   ├── cache/
│   └── artifacts/
└── README.md
```

---

## 10. 里程碑（分步实施）

### V1 里程碑

| 阶段 | 内容 | 验收标准 | 预计投入 |
|---|---|---|---|
| M0 | 项目骨架：目录、依赖、mock 示例数据、最小 FastAPI | `uvicorn` 启动，`/health` 可用 | 0.5-1 天 |
| M1 | 后端流程：PocketFlow 节点化流水线（6 节点 + 4 agent），DeepSeek 跑通，输出 HTML 报告 | 命令行/API 触发，生成完整报告 | 3-4 天 |
| M2 | 可观测层：ObservableNode + EventBus + SQLite + WebSocket | 事件落库；ws 客户端收到完整事件流 | 2 天 |
| M3 | 前端控制台：任务创建 + DAG 实时可视化 + 节点详情 + 事件日志 + 报告预览 | 浏览器实时看到节点状态流转与输出摘要 | 3-4 天 |
| M4 | LLM 缓存 + 失败/重试场景打磨 + README + 一键演示脚本 | mock 模式下浏览器完整演示；`python demo.py` 一条命令启动 | 1-2 天 |

**V1 总计约 1.5-2 周**，全部在 mock 模式下离线开发，DeepSeek 只需一个 key。

### V2/V3 里程碑（增量路线，V1 验收后再排期）

- V2a：补齐 8 个 agent + 图表 + PDF
- V2b：FMP/yfinance real 数据源 + 回放 + 溯源导出
- V3：Mem0 记忆层 / 多任务对比 / 扩展市场

---

## 11. 风险与取舍

1. **FMP API key**：免费版有额度限制 → mock 模式兜底；数据源抽象层让切换零成本
2. **LLM 成本**：8 个 agent 并行调用 → 缓存 + 默认只跑必要 agent 的选项（报告章节可裁剪）
3. **金融数据时效**：报告必须标注数据日期，避免"过期数据当新数据"（这本身就是审计卖点）
4. **范围控制**：只做美股 ticker（FinRobot 原有范围），不做 A 股/多市场，防止范围膨胀
5. **可视化性能**：事件量不大（每节点 5-6 条），React Flow 足够；若 agent 多，限制回放动画速率
6. **PocketFlow 升级**：只依赖其公开 API（Node/Flow/AsyncNode），Observable 基类不碰内部实现

---

## 12. 与 FinRobot 的合规边界

- 参考其**流程设计、agent 职责、报告章节**（Apache 2.0，允许借鉴，需保留署名）
- 本项目代码从零编写，不使用其源码文件（除：报告章节字段名、prompt 角色思路）
- `NOTICE` 文件声明："Financial analysis workflow design inspired by AI4Finance-Foundation/FinRobot (Apache-2.0)"
- README 中写明与 FinRobot / TradingAgents 的关系，作为套磁材料的一部分

---

## 13. 套磁/简历叙事（成稿后使用）

> **FinFlow：可观测的 LLM 金融分析流水线**。参考 FinRobot 的金融分析流程，用 100 行级轻量框架 PocketFlow 重构为可并行、可重试的 DAG 流水线，并自研运行时可视化层：每个分析节点的执行状态、输入输出、耗时与失败原因实时可见、可回放、可溯源。所有报告结论均带数据来源与数据日期标注，支持 mock 数据离线复现。

三个关键词供套磁信展开：

- **可观测**：执行过程实时可视化 + 事件回放（PocketFlow 生态空白）
- **可审计**：章节级溯源（数据 → 分析 → 结论的完整链路）
- **可复现**：缓存、固定 seed、mock 数据、数据版本标注

这与你修 look-ahead bias 的故事构成一条主线：**"让 LLM 系统可信"**。
