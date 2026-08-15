"""真实数据源：yfinance（Yahoo Finance），输出与 mock 相同的快照 schema。"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


def _to_millions(value) -> float | None:
    """金额转百万美元（yfinance 原始值可能是美元，EPS 等小值原样返回）。"""
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return round(value / 1e6, 2) if abs(value) > 1e9 else round(value, 2)


def _cell(df: pd.DataFrame | None, row: str, col) -> float | None:
    if df is None or df.empty or row not in df.index:
        return None
    value = df.loc[row, col]
    return float(value) if not pd.isna(value) else None


def _statement(df: pd.DataFrame | None, mapping: dict[str, str], milli: bool = True) -> list[dict]:
    """把 yfinance 财务报表转成 {year: 字段} 列表（最近 4 期）。"""
    if df is None or df.empty:
        return []
    rows = []
    for col in sorted(df.columns, reverse=True)[:4]:  # 最近 4 期
        entry: dict = {"year": getattr(col, "year", datetime.now().year)}
        for out_key, row_label in mapping.items():
            val = _cell(df, row_label, col)
            entry[out_key] = _to_millions(val) if milli and val is not None else val
        rows.append(entry)
    return rows


class YFinanceProvider:
    """从 Yahoo Finance 拉取某美股的真实数据快照。"""

    def get_snapshot(self, ticker: str) -> dict:
        t = yf.Ticker(ticker)
        info = t.info or {}

        income = _statement(
            t.financials,
            {
                "revenue": "Total Revenue",
                "cogs": "Cost Of Revenue",
                "ebitda": "EBITDA",
                "net_income": "Net Income",
                "eps": "Diluted EPS",
                "interest_expense": "Interest Expense",
            },
        )
        balance = _statement(
            t.balance_sheet,
            {
                "total_assets": "Total Assets",
                "total_liabilities": "Total Liabilities Net Minority Interest",
                "total_equity": "Stockholders Equity",
                "cash_and_equivalents": "Cash Cash Equivalents And Short Term Investments",
                "current_assets": "Total Current Assets",
                "current_liabilities": "Total Current Liabilities",
                "long_term_debt": "Long Term Debt",
                "short_term_debt": "Short Term Debt",
            },
        )
        cashflow = _statement(
            t.cashflow,
            {
                "operating_cash_flow": "Operating Cash Flow",
                "capex": "Capital Expenditure",
                "free_cash_flow": "Free Cash Flow",
            },
        )

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")
        ev = info.get("enterpriseValue")
        ebitda = info.get("ebitda")
        market_metrics = {
            "price": round(price, 2) if price else None,
            "market_cap_bn": round(market_cap / 1e9, 1) if market_cap else None,
            "target_price": info.get("targetMeanPrice"),
            "analyst_rating": (info.get("recommendationKey") or "n/a").title(),
            "pe_ratio": round(info["trailingPE"], 1) if info.get("trailingPE") else None,
            "ev_ebitda": round(ev / ebitda, 1) if ev and ebitda else None,
        }

        news = []
        for n in (t.news or [])[:8]:
            ts = n.get("providerPublishTime")
            date = (
                datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                if ts
                else ""
            )
            news.append(
                {
                    "title": n.get("title", ""),
                    "date": date,
                    "summary": n.get("summary") or "",
                }
            )

        price_history = []
        hist = t.history(period="3mo")
        if hist is not None and not hist.empty:
            for idx, row in hist.iterrows():
                price_history.append(
                    {"date": str(idx.date()), "close": round(float(row["Close"]), 2)}
                )
            price_history = price_history[-40:]

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("longName") or ticker.upper(),
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "currency": info.get("financialCurrency") or "USD",
            "data_source": "yfinance",
            "financial_data": {
                "income_statement": income,
                "balance_sheet": balance,
                "cash_flow": cashflow,
            },
            "market_metrics": market_metrics,
            "price_history": price_history,
            "peer_data": {"peers": [], "peer_ev_ebitda": []},
            "news": news,
        }
