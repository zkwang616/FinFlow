"""数据处理：把原始数据快照转换为分析指标。"""

from __future__ import annotations

TAX_RATE = 0.21


def _growth_rate(values: list[float]) -> float | None:
    """最近两期增长率（百分比）。"""
    if len(values) < 2 or not values[-2]:
        return None
    return (values[-1] / values[-2] - 1) * 100


def compute_ratios(income: list[dict], balance: list[dict], cashflow: list[dict]) -> dict:
    """计算核心财务比率（基于最新财年）。"""
    latest = income[-1]
    bs = balance[-1] if balance else {}
    cf = cashflow[-1] if cashflow else {}

    revenue = latest.get("revenue")
    cogs = latest.get("cogs")
    ebitda = latest.get("ebitda")
    net_income = latest.get("net_income")
    interest = latest.get("interest_expense", 0)

    equity = bs.get("total_equity")
    total_assets = bs.get("total_assets")
    cash = bs.get("cash_and_equivalents", 0)
    current_assets = bs.get("current_assets")
    current_liabilities = bs.get("current_liabilities")
    total_debt = (bs.get("long_term_debt", 0) or 0) + (bs.get("short_term_debt", 0) or 0)

    fcf = cf.get("free_cash_flow")

    def pct(a, b):
        return round(a / b * 100, 2) if a is not None and b else None

    roic = None
    if net_income is not None and interest is not None and total_debt + (equity or 0) > 0:
        nopat = net_income + interest * (1 - TAX_RATE)
        roic = pct(nopat, total_debt + equity)

    return {
        "gross_margin_pct": pct(revenue - cogs, revenue) if cogs is not None else None,
        "net_margin_pct": pct(net_income, revenue),
        "roe_pct": pct(net_income, equity),
        "roic_pct": roic,
        "debt_to_equity": round(total_debt / equity, 2) if equity else None,
        "debt_to_assets_pct": pct(total_debt, total_assets),
        "current_ratio": (
            round(current_assets / current_liabilities, 2)
            if current_assets and current_liabilities
            else None
        ),
        "interest_coverage": (
            round(ebitda / interest, 2)
            if ebitda is not None and interest
            else None
        ),
        "fcf_margin_pct": pct(fcf, revenue),
        "net_debt": (
            round(total_debt - cash, 2) if total_debt or cash else None
        ),
    }


def process_snapshot(snapshot: dict) -> dict:
    """从 mock 快照计算历史指标、增长率与简易预测。"""
    income = snapshot["financial_data"]["income_statement"]
    balance = snapshot["financial_data"].get("balance_sheet", [])
    cashflow = snapshot["financial_data"].get("cash_flow", [])
    years = [r["year"] for r in income]
    revenue = [r["revenue"] for r in income]
    ebitda = [r["ebitda"] for r in income]
    net_income = [r["net_income"] for r in income]
    eps = [r["eps"] for r in income]
    fcf = [r.get("free_cash_flow") for r in cashflow]

    latest = income[-1]
    net_margin = latest["net_income"] / latest["revenue"] * 100 if latest["revenue"] else None

    revenue_growth = _growth_rate(revenue)
    forecast_revenue_1y = (
        latest["revenue"] * (1 + revenue_growth / 100) if revenue_growth is not None else None
    )

    market = snapshot.get("market_metrics", {})
    peers = snapshot.get("peer_data", {})
    ratios = compute_ratios(income, balance, cashflow)

    price = market.get("price")
    market_cap_bn = market.get("market_cap_bn")
    shares_outstanding = (
        round(market_cap_bn * 1e9 / price, 1) if price and market_cap_bn else None
    )

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
        "fcf": fcf,
        "net_margin_pct": net_margin,
        "revenue_growth_pct": revenue_growth,
        "forecast_revenue_1y": forecast_revenue_1y,
        "ratios": ratios,
        "shares_outstanding": shares_outstanding,
        "market": market,
        "peer_tickers": peers.get("peers", []),
        "peer_ev_ebitda": peers.get("peer_ev_ebitda", []),
        "news": snapshot.get("news", []),
    }
