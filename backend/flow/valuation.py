"""定量估值引擎：DCF、可比公司估值与敏感性分析（纯计算，不依赖 LLM）。"""

from __future__ import annotations

import statistics

DEFAULT_WACC = 0.09
DEFAULT_TERMINAL_G = 0.025


def _dcf_per_share(
    fcf_series: list[float],
    net_debt: float,
    shares_m: float,
    wacc: float,
    g_term: float,
    years: int = 5,
) -> float | None:
    """简化两阶段 DCF：FCF 以最近一期增长率增长 years 年，然后永续增长 g_term。"""
    if not fcf_series or shares_m <= 0:
        return None
    base = fcf_series[-1]
    growth = fcf_series[-1] / fcf_series[-2] - 1 if len(fcf_series) >= 2 and fcf_series[-2] else 0.05
    growth = max(0.0, min(growth, 0.15))  # 增长假设上限 15%

    pv = 0.0
    fcf_t = base
    for t in range(1, years + 1):
        fcf_t *= 1 + growth
        pv += fcf_t / (1 + wacc) ** t
    tv = fcf_t * (1 + g_term) / (wacc - g_term) if wacc > g_term else 0.0
    ev = pv + tv / (1 + wacc) ** years
    equity_value = ev - net_debt
    return round(equity_value / shares_m, 2)


def _comparable_per_share(
    ebitda: float,
    peer_multiple: float,
    net_debt: float,
    shares_m: float,
) -> float | None:
    if not ebitda or not peer_multiple or shares_m <= 0:
        return None
    ev = peer_multiple * ebitda
    return round((ev - net_debt) / shares_m, 2)


def sensitivity_matrix(
    fcf_series: list[float],
    net_debt: float,
    shares_m: float,
    waccs: list[float] | None = None,
    g_terms: list[float] | None = None,
) -> list[dict]:
    """DCF 每股价值对 WACC × 永续增长率的敏感性矩阵。"""
    waccs = waccs or [0.08, 0.09, 0.10]
    g_terms = g_terms or [0.02, 0.025, 0.03]
    rows = []
    for wacc in waccs:
        row = {"wacc": f"{wacc * 100:.1f}%"}
        for g in g_terms:
            row[f"g={g * 100:.1f}%"] = _dcf_per_share(fcf_series, net_debt, shares_m, wacc, g)
        rows.append(row)
    return rows


def valuation_engine(processed: dict) -> dict:
    """汇总 DCF、可比估值、敏感性，产出综合估值区间。"""
    fcf_series = [x for x in processed.get("fcf", []) if x is not None]
    net_debt = processed.get("ratios", {}).get("net_debt")
    shares_m = (
        processed.get("shares_outstanding", 0) / 1e6
        if processed.get("shares_outstanding")
        else None
    )
    ebitda = processed.get("latest_ebitda")
    peer_multiples = [p.get("ev_ebitda") for p in processed.get("peer_ev_ebitda", []) if p.get("ev_ebitda")]

    result: dict = {"dcf": None, "comparable": None, "sensitivity": [], "range": None}

    if fcf_series and net_debt is not None and shares_m:
        result["dcf"] = {
            "value_per_share": _dcf_per_share(
                fcf_series, net_debt, shares_m, DEFAULT_WACC, DEFAULT_TERMINAL_G
            ),
            "wacc": DEFAULT_WACC,
            "terminal_growth": DEFAULT_TERMINAL_G,
        }
        result["sensitivity"] = sensitivity_matrix(fcf_series, net_debt, shares_m)

    if ebitda and peer_multiples and net_debt is not None and shares_m:
        median_multiple = statistics.median(peer_multiples)
        result["comparable"] = {
            "value_per_share": _comparable_per_share(ebitda, median_multiple, net_debt, shares_m),
            "median_multiple": median_multiple,
            "peer_count": len(peer_multiples),
        }

    values = [
        v["value_per_share"]
        for v in (result["dcf"], result["comparable"])
        if v and v.get("value_per_share") is not None
    ]
    if values:
        result["range"] = {
            "low": round(min(values), 2),
            "high": round(max(values), 2),
            "mid": round(sum(values) / len(values), 2),
        }
    return result
