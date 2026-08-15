"""实验 A：LLM 金融分析结论一致性研究。

研究问题：相同输入、相同流程下，重复生成的金融分析结论有多稳定？
方法：固定 mock 数据 + 关闭缓存 + 重复运行 N 次，采集 4 个 agent 的结构化输出，
      计算文本一致性、列表一致性、离散字段稳定性与方向一致性。

用法：
    .venv\\Scripts\\python.exe -m backend.experiments.consistency --ticker AAPL --runs 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import time
from collections import Counter
from datetime import datetime
from itertools import combinations
from pathlib import Path

from backend.config import project_root
from backend.flow.pipeline import run_job


# ---------- 文本相似度工具（无外部依赖） ----------

def _char_ngrams(text: str, n: int = 3) -> set[str]:
    text = re.sub(r"\s+", " ", text or "").strip().lower()
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard(a: str, b: str) -> float:
    sa, sb = _char_ngrams(a), _char_ngrams(b)
    if not sa and not sb:
        return 1.0
    union = sa | sb
    if not union:
        return 1.0
    return len(sa & sb) / len(union)


def mean_pairwise(values: list[str]) -> float:
    if len(values) < 2:
        return 1.0
    pairs = list(combinations(values, 2))
    return sum(jaccard(a, b) for a, b in pairs) / len(pairs)


def list_overlap(list_a: list[str], list_b: list[str]) -> float:
    """两个字符串列表的语义重叠率（贪心 n-gram 匹配）。"""
    if not list_a and not list_b:
        return 1.0
    if not list_a or not list_b:
        return 0.0
    unmatched = list(list_b)
    matches = 0
    for item in list_a:
        best, best_idx = 0.0, -1
        for j, other in enumerate(unmatched):
            s = jaccard(item, other)
            if s > best:
                best, best_idx = s, j
        if best >= 0.35 and best_idx >= 0:
            matches += 1
            unmatched.pop(best_idx)
    return matches / max(len(list_a), len(list_b))


def mean_list_overlap(values: list[list[str]]) -> float:
    if len(values) < 2:
        return 1.0
    pairs = list(combinations(values, 2))
    return sum(list_overlap(a, b) for a, b in pairs) / len(pairs)


# ---------- 方向与区间 ----------

POSITIVE = ("strong", "attractive", "upside", "overweight", "buy", "outperform", "favorable", "recommend")
NEGATIVE = ("weak", "risky", "downside", "underweight", "sell", "underperform", "caution", "unfavorable", "avoid")
NEUTRAL = ("mixed", "neutral", "stable", "in-line", "balanced", "moderate")


def direction(text: str) -> str:
    t = (text or "").lower()
    pos = sum(1 for w in POSITIVE if w in t)
    neg = sum(1 for w in NEGATIVE if w in t)
    neu = sum(1 for w in NEUTRAL if w in t)
    if pos > neg and pos > neu:
        return "positive"
    if neg > pos and neg > neu:
        return "negative"
    return "neutral"


def parse_range(text: str) -> tuple[float, float] | None:
    """从 fair_value_range 文本提取数值区间，如 '120-140' / '$125 to $150'。"""
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text or "")]
    if len(nums) >= 2:
        return (min(nums[:2]), max(nums[:2]))
    return None


def range_iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    inter = max(0.0, hi - lo)
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


# ---------- 字段映射 ----------

TEXT_FIELDS = {
    "company_overview": "overview",
    "valuation_analysis": "valuation_assessment",
    "risks": "risk_mitigation",
    "takeaways": "investment_thesis",
}

LIST_FIELDS = {
    "company_overview": ["key_strengths", "key_challenges"],
    "valuation_analysis": [],
    "risks": ["risks"],
    "takeaways": ["key_catalysts", "watch_indicators"],
}


# ---------- 实验主流程 ----------

def _avg(xs: list[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


async def run_experiment(
    ticker: str, runs: int, out_dir: Path, temperature: float = 0.3
) -> dict:
    results: list[dict] = []
    failures_total = 0
    t0 = time.perf_counter()
    for i in range(runs):
        job = {
            "ticker": ticker,
            "mode": "mock",
            "no_cache": True,
            "temperature": temperature,
        }
        shared = await run_job(job)
        sections = shared.get("text_sections", {})
        failures = shared.get("agent_failures", [])
        failures_total += len(failures)
        results.append(
            {
                "run": i + 1,
                "ts": datetime.now().isoformat(timespec="seconds"),
                "sections": sections,
                "failures": failures,
            }
        )
        print(f"  run {i + 1}/{runs} done ({time.perf_counter() - t0:.1f}s elapsed)")

    raw_path = out_dir / "runs.jsonl"
    with raw_path.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    metrics = compute_metrics(results)
    metrics["meta"] = {
        "ticker": ticker,
        "runs": runs,
        "temperature": temperature,
        "model": "deepseek-chat",
        "no_cache": True,
        "total_failures": failures_total,
        "raw_data": str(raw_path),
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"summary saved: {summary_path}")
    return metrics


def compute_metrics(results: list[dict]) -> dict:
    agents = list(results[0]["sections"].keys())
    per_agent: dict[str, dict] = {}

    for agent in agents:
        texts = [r["sections"][agent].get(TEXT_FIELDS[agent], "") for r in results]
        lists: dict[str, list[list[str]]] = {}
        for field in LIST_FIELDS[agent]:
            lists[field] = [r["sections"][agent].get(field, []) for r in results]

        entry: dict = {
            "text_similarity": round(mean_pairwise(texts), 4),
        }
        for field, values in lists.items():
            entry[f"{field}_overlap"] = round(mean_list_overlap(values), 4)

        if agent == "risks":
            ratings = [r["sections"][agent].get("risk_rating", "") for r in results]
            entry["risk_rating_distribution"] = dict(Counter(ratings))
            entry["risk_rating_entropy"] = round(_entropy(ratings), 4)

        if agent == "valuation_analysis":
            ranges = [
                parse_range(r["sections"][agent].get("fair_value_range", ""))
                for r in results
            ]
            parsed = [x for x in ranges if x is not None]
            if len(parsed) >= 2:
                entry["fair_value_range_iou"] = round(
                    _avg(range_iou(a, b) for a, b in combinations(parsed, 2)), 4
                )
                entry["fair_value_range_parsed"] = len(parsed)

        if agent == "takeaways":
            dirs = [
                direction(r["sections"][agent].get("conclusion", ""))
                for r in results
            ]
            entry["conclusion_direction_distribution"] = dict(Counter(dirs))
            entry["conclusion_direction_entropy"] = round(_entropy(dirs), 4)

        per_agent[agent] = entry

    overall_text = _avg(
        [per_agent[a]["text_similarity"] for a in agents if not math.isnan(per_agent[a]["text_similarity"])]
    )
    return {
        "per_agent": per_agent,
        "overall": {
            "mean_text_similarity": round(overall_text, 4),
        },
    }


def _entropy(values: list[str]) -> float:
    counts = Counter(values)
    total = len(values)
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="FinFlow consistency experiment (A)")
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument(
        "--from-jsonl",
        metavar="PATH",
        help="recompute metrics from an existing runs.jsonl (no LLM calls)",
    )
    args = parser.parse_args()

    if args.from_jsonl:
        jsonl = Path(args.from_jsonl)
        results = [
            json.loads(line)
            for line in jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        metrics = compute_metrics(results)
        metrics["meta"] = {"raw_data": str(jsonl), "runs": len(results), "recomputed": True}
        summary_path = jsonl.parent / "summary.json"
        summary_path.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"summary saved: {summary_path}")
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = project_root() / "data" / "experiments" / f"{args.ticker}_{stamp}"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(
            f"consistency experiment: ticker={args.ticker} runs={args.runs} "
            f"temperature={args.temperature}"
        )
        metrics = asyncio.run(
            run_experiment(args.ticker, args.runs, out_dir, args.temperature)
        )
    print("\n=== per-agent metrics ===")
    print(json.dumps(metrics["per_agent"], ensure_ascii=False, indent=2))
    print("overall:", metrics["overall"])


if __name__ == "__main__":
    main()
