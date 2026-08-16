"""多任务结果对比：汇总同一 ticker 的多次运行，评估结论一致性。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from backend.config import project_root

POSITIVE = ("strong", "attractive", "upside", "overweight", "buy", "outperform", "favorable", "recommend")
NEGATIVE = ("weak", "risky", "downside", "underweight", "sell", "underperform", "caution", "unfavorable", "avoid")
NEUTRAL = ("mixed", "neutral", "stable", "in-line", "balanced", "moderate")


def direction(text: str) -> str:
    """从结论文本判断方向（关键词规则）。"""
    t = (text or "").lower()
    pos = sum(1 for w in POSITIVE if w in t)
    neg = sum(1 for w in NEGATIVE if w in t)
    neu = sum(1 for w in NEUTRAL if w in t)
    if pos > neg and pos > neu:
        return "positive"
    if neg > pos and neg > neu:
        return "negative"
    return "neutral"


def build_result_json(shared: dict, params: dict) -> dict:
    """从一次任务的 shared 上下文提取结构化结果摘要。"""
    processed = shared.get("processed", {})
    valuation = shared.get("valuation") or {}
    sections = shared.get("text_sections", {})
    market = processed.get("market", {})

    rng = valuation.get("range") or {}
    takeaways = sections.get("takeaways") or {}
    news = sections.get("news_summary") or {}
    risks = sections.get("risks") or {}

    return {
        "job_id": params.get("job_id"),
        "ticker": processed.get("ticker", params.get("ticker", "")),
        "mode": params.get("mode", "mock"),
        "data_source": processed.get("data_source", "mock"),
        "as_of": processed.get("as_of", ""),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "report": (shared.get("report") or {}).get("path"),
        "pdf": (shared.get("pdf") or {}).get("pdf_path"),
        "valuation": {
            "dcf": (valuation.get("dcf") or {}).get("value_per_share"),
            "comparable": (valuation.get("comparable") or {}).get("value_per_share"),
            "range_low": rng.get("low"),
            "range_high": rng.get("high"),
            "range_mid": rng.get("mid"),
        },
        "conclusion": {
            "direction": direction(takeaways.get("conclusion", "")),
            "text": (takeaways.get("conclusion") or "")[:300],
        },
        "sentiment": {
            "label": news.get("sentiment"),
            "score": news.get("sentiment_score"),
        },
        "recommendation": shared.get("recommendation") or {},
        "risk_rating": risks.get("risk_rating"),
        "key_metrics": {
            "price": market.get("price"),
            "rating": market.get("analyst_rating"),
            "pe_ratio": market.get("pe_ratio"),
            "ev_ebitda": market.get("ev_ebitda"),
        },
    }


def _result_paths(ticker: str) -> list[Path]:
    artifacts = project_root() / "data" / "artifacts"
    paths = sorted(artifacts.glob("job_*_result.json"))
    return [p for p in paths if ticker in _read_ticker(p)]


def _read_ticker(path: Path) -> str:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("ticker", "")
    except Exception:
        return ""


def load_results(ticker: str) -> list[dict]:
    """读取某 ticker 的全部历史任务结果（按时间排序）。"""
    results = []
    for p in _result_paths(ticker.upper()):
        try:
            results.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    results.sort(key=lambda r: r.get("created_at", ""))
    return results


def compare(ticker: str) -> dict:
    """汇总对比：估值区间序列、结论方向分布、情绪分布。"""
    results = load_results(ticker)
    if not results:
        return {"ticker": ticker, "runs": [], "summary": {"error": "no results yet"}}

    directions = [r["conclusion"]["direction"] for r in results]
    sentiments = [r["sentiment"].get("label") for r in results if r["sentiment"].get("label")]
    ranges = [r["valuation"] for r in results if r["valuation"].get("range_mid") is not None]

    return {
        "ticker": ticker,
        "run_count": len(results),
        "runs": results,
        "summary": {
            "conclusion_direction_distribution": {
                d: directions.count(d) for d in sorted(set(directions))
            },
            "sentiment_distribution": {
                s: sentiments.count(s) for s in sorted(set(sentiments))
            },
            "valuation": {
                "range_lows": [r["range_low"] for r in ranges],
                "range_highs": [r["range_high"] for r in ranges],
                "range_mids": [r["range_mid"] for r in ranges],
            },
        },
    }
