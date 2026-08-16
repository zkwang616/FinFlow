# FinFlow

An LLM-powered stock analysis platform. Enter a ticker and FinFlow prepares the data, runs multi-role LLM analysis (company overview, valuation, risks, investment takeaways), and generates a structured analysis report. Every analysis run also produces an execution trace document, so each conclusion can be audited and reproduced.

FinFlow is built on [PocketFlow](https://github.com/The-Pocket/PocketFlow), a 100-line minimalist LLM framework, and adds a lightweight observability layer that records how each analysis conclusion was produced.

## Features

- **Multi-role stock analysis** — 8 parallel analysis agents (overview, financial health, valuation, competitors, news/sentiment, catalysts, risks, takeaways) produce a structured report from one ticker
- **Quantitative engine** — financial ratios, DCF & comparable valuation, and sensitivity analysis are computed from data (not LLM-generated), then fed to the analysis agents as ground truth
- **Charts & PDF** — trend / peer / price charts embedded in the report, plus a PDF export
- **Lightweight core** — built on PocketFlow (a ~100-line LLM framework), with minimal dependencies (`fastapi`, `openai`, `pandas`)
- **Auditable execution** — every run produces a `trace.json` alongside the report, recording each step's inputs, outputs, timing, actions, and errors
- **Full-stack console** — FastAPI + WebSocket backend, React frontend with a live pipeline status view and report preview
- **Reproducible** — mock data mode, LLM result caching, and CLI experiments with repeatable sampling
- **Research-ready** — the pipeline doubles as an experiment platform for studying LLM output reliability (see [Research](#research))
- **Cross-task memory** — analysis conclusions are stored via Mem0 (local embeddings) and retrieved in later runs for consistency
- **Multi-market** — US stocks via yfinance, A-shares via akshare (e.g. `600519`), or offline mock data

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
# Generate a report for a ticker (mock data, offline)
.venv\Scripts\python.exe -m backend.cli --ticker AAPL

# Real market data via yfinance (network / proxy may be required)
.venv\Scripts\python.exe -m backend.cli --ticker AAPL --mode real

# A-share via akshare (e.g. Kweichow Moutai)
.venv\Scripts\python.exe -m backend.cli --ticker 600519 --mode real

# Compare previous runs of a ticker
.venv\Scripts\python.exe -m backend.cli --compare AAPL

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
                  and trace audit document generation
  providers/      data source abstraction (mock)
  report/         HTML/PDF report rendering, charts
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

- [x] V1: multi-role analysis pipeline, audit trace, caching, failure paths, consistency study
- [x] V2: analysis depth — valuation engine (DCF / comparable), financial ratios, sensitivity analysis, core charts, full 8-agent suite, news/sentiment, PDF export, yfinance real data source
- [x] V3: memory layer (Mem0), multi-run comparison, A-share data source (akshare)

## Acknowledgements

The multi-role financial analysis workflow design was inspired by [AI4Finance-Foundation/FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) (Apache-2.0). See [NOTICE](NOTICE).

## License

[MIT](LICENSE)
