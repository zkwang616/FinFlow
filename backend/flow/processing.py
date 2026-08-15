"""数据处理：把原始数据快照转换为分析指标。"""

from __future__ import annotations


def _growth_rate(values: list[float]) -> float | None:
    """最近两期增长率（百分比）。"""
    if len(values) < 2 or not values[-2]:
        return None
    return (values[-1] / values[-2] - 1) * 100


def process_snapshot(snapshot: dict) -> dict:
    """从 mock 快照计算历史指标、增长率与简易预测。"""
    income = snapshot["financial_data"]["income_statement"]
    years = [r["year"] for r in income]
    revenue = [r["revenue"] for r in income]
    ebitda = [r["ebitda"] for r in income]
    net_income = [r["net_income"] for r in income]
    eps = [r["eps"] for r in income]

    latest = income[-1]
    net_margin = latest["net_income"] / latest["revenue"] * 100 if latest["revenue"] else None

    revenue_growth = _growth_rate(revenue)
    forecast_revenue_1y = (
        latest["revenue"] * (1 + revenue_growth / 100) if revenue_growth is not None else None
    )

    market = snapshot.get("market_metrics", {})
    peers = snapshot.get("peer_data", {})

    return {
        "company_name": snapshot.get("company_name", ""),
        "ticker": snapshot.get("ticker", ""),
        "as_of": snapshot.get("as_of", ""),
        "years": years,
        "revenue": revenue,
        "ebitda": ebitda,
        "net_income": net_income,
        "eps": eps,
        "latest_year": latest["year"],
        "latest_revenue": latest["revenue"],
        "latest_ebitda": latest["ebitda"],
        "latest_net_income": latest["net_income"],
        "latest_eps": latest["eps"],
        "net_margin_pct": net_margin,
        "revenue_growth_pct": revenue_growth,
        "forecast_revenue_1y": forecast_revenue_1y,
        "market": market,
        "peer_tickers": peers.get("peers", []),
        "peer_ev_ebitda": peers.get("peer_ev_ebitda", []),
        "news": snapshot.get("news", []),
    }
