"""图表生成：matplotlib → base64 PNG，嵌入 HTML 报告。"""

from __future__ import annotations

import base64
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def financial_trend_chart(processed: dict) -> str | None:
    """收入 / EBITDA / 净利的历史趋势折线图。"""
    years = processed.get("years", [])
    if len(years) < 2:
        return None
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(years, processed["revenue"], marker="o", label="Revenue")
    ax.plot(years, processed["ebitda"], marker="s", label="EBITDA")
    ax.plot(years, processed["net_income"], marker="^", label="Net Income")
    ax.set_title(f"{processed['ticker']} Financial Trend ($M)")
    ax.set_xlabel("Fiscal Year")
    ax.legend()
    ax.grid(alpha=0.3)
    return _fig_to_base64(fig)


def peer_ev_ebitda_chart(processed: dict) -> str | None:
    """本公司 vs 同业 EV/EBITDA 横向条形图。"""
    peers = processed.get("peer_ev_ebitda", [])
    own = processed.get("market", {}).get("ev_ebitda")
    if not peers or own is None:
        return None
    names = [f"{processed['ticker']} (us)"] + [p["ticker"] for p in peers]
    values = [own] + [p["ev_ebitda"] for p in peers]
    colors = ["#1d4ed8"] + ["#94a3b8"] * len(peers)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.barh(names, values, color=colors)
    for i, v in enumerate(values):
        ax.text(v + 0.2, i, f"{v:.1f}x", va="center", fontsize=9)
    ax.set_title(f"EV/EBITDA: {processed['ticker']} vs Peers")
    ax.set_xlabel("EV/EBITDA (x)")
    ax.grid(axis="x", alpha=0.3)
    return _fig_to_base64(fig)


def price_history_chart(snapshot: dict) -> str | None:
    """股价历史走势图。"""
    history = snapshot.get("price_history", [])
    if len(history) < 2:
        return None
    dates = [h["date"] for h in history]
    closes = [h["close"] for h in history]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(dates, closes, color="#16a34a", linewidth=1.8)
    ax.fill_between(range(len(dates)), closes, alpha=0.1, color="#16a34a")
    ax.set_title(f"{snapshot.get('ticker', '')} Price History")
    ax.set_ylabel("Close Price (USD)")
    ax.set_xticks(range(0, len(dates), max(1, len(dates) // 6)))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), max(1, len(dates) // 6))], rotation=30, fontsize=8)
    ax.grid(alpha=0.3)
    return _fig_to_base64(fig)


def generate_all(processed: dict, snapshot: dict) -> dict:
    """生成全部图表，返回 {chart_key: base64}。"""
    return {
        "financial_trend": financial_trend_chart(processed),
        "peer_ev_ebitda": peer_ev_ebitda_chart(processed),
        "price_history": price_history_chart(snapshot),
    }
