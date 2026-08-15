# FinFlow

An observable LLM-powered financial analysis pipeline. Enter a ticker and watch the full pipeline execute in real time — data fetching, multi-role LLM analysis, and report generation — with every node's state, inputs, outputs, and failures tracked and replayable.

FinFlow is built on [PocketFlow](https://github.com/The-Pocket/PocketFlow), a 100-line minimalist LLM framework, and adds a self-built observability layer so that every conclusion in a generated report can be traced back to its data and the analysis step that produced it.

## Features

- **Lightweight core** — built on PocketFlow (a ~100-line LLM framework), with minimal dependencies (`fastapi`, `openai`, `pandas`)
- **Observable execution** — a custom observability layer broadcasts every node lifecycle event (start / ready / output / finish / fail) over WebSocket and persists it to SQLite
- **Full-stack console** — FastAPI + WebSocket backend, React + React Flow frontend with a live DAG view, event log, and per-node I/O inspection
- **Reproducible** — mock data mode, LLM result caching, and CLI experiments with repeatable sampling
- **Research-ready** — the pipeline doubles as an experiment platform for studying LLM output reliability (see [Research](#research))

## Research

FinFlow is also an experiment platform for studying the reliability of LLM-generated financial analysis.

[**Consistency of LLM Financial Analysis: Facts Are Stable, Judgments Are Random**](docs/research/consistency_report.md)

Key findings from 10 repeated runs with identical input (DeepSeek, `temperature=0.3`):

- Overall text similarity between runs: **0.45** (n-gram Jaccard) — wording varies substantially
- Judgment outputs are highly unstable: risk list overlap **0.37**, fair-value-range IoU **0.30**
- Investment conclusion direction flips between *positive* and *neutral* **50/50** (entropy 1.0)
- With `temperature=0` (greedy decoding), conclusion direction remains **50/50** — the instability is not sampling noise but the model itself

Raw experiment data and scripts: `backend/experiments/` and `data/experiments/`.

## Getting Started

### Prerequisites

- Python 3.12
- Node.js 20+ / npm
- A [DeepSeek](https://platform.deepseek.com/) API key (OpenAI-compatible)

### Quick Start (one command)

```powershell
cd FinFlow
.venv\Scripts\python.exe demo.py
```

Then open http://localhost:5173 and submit `AAPL` or `MSFT` (mock data included).

### Manual Setup

```powershell
# Backend (127.0.0.1:8000)
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000

# Frontend (localhost:5173)
cd frontend
npm run dev
```

Copy `.env.example` to `.env` and set `DEEPSEEK_API_KEY`.

### CLI

```powershell
# Generate a report for a ticker
.venv\Scripts\python.exe -m backend.cli --ticker AAPL

# Repeat N times without cache (consistency experiments)
.venv\Scripts\python.exe -m backend.cli --ticker AAPL --repeat 5 --no-cache
```

## Architecture

```
React console (live DAG visualization)
        │ REST + WebSocket
FastAPI (JobManager + EventBus)
        │
PocketFlow AsyncFlow (ObservableNode wrapping)
  Input → MockData → DataProcessor → TextAgents (×4 parallel) → HtmlReport → Done
```

## Project Structure

```
backend/
  app/            FastAPI routes, JobManager
  flow/           nodes, agents, pipeline assembly (PocketFlow)
  observability/  event bus, observable nodes, WebSocket broadcast
  providers/      data source abstraction (mock)
  report/         HTML report rendering
  storage/        SQLite (jobs / events)
  experiments/    research experiments (consistency study)
  tests/          end-to-end tests
frontend/         React + Vite + React Flow console
data/
  mock/           built-in sample data (AAPL / MSFT)
  cache/          LLM result cache
  artifacts/      generated reports
  experiments/    experiment raw data
```

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/jobs` | Create an analysis job `{ticker, mode}` |
| GET | `/api/jobs/{id}` | Job status |
| GET | `/api/jobs/{id}/events` | Full event history (replay / audit) |
| WS | `/ws/jobs/{id}` | Real-time event stream |
| GET | `/api/jobs/{id}/report` | Generated HTML report |

## Roadmap

- [x] V1: pipeline, observability layer, console, caching, failure paths, consistency study
- [ ] V2: full agent suite, charts, PDF export, real data sources, replay, section-level tracing
- [ ] V3: memory layer (Mem0), multi-job comparison, more markets

## Acknowledgements

The multi-role financial analysis workflow design was inspired by [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) (Apache-2.0). See [NOTICE](NOTICE).

## License

[MIT](LICENSE)
