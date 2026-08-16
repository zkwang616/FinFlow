"""A 股数据源：akshare（东财/新浪，国内直连，绕过系统代理）。"""

from __future__ import annotations

import os
import time
from datetime import datetime


def is_a_share(ticker: str) -> bool:
    """判断 ticker 是否为 A 股格式（6 位数字，或带 .SH/.SS/.SZ 后缀）。"""
    t = ticker.upper()
    if t.endswith((".SH", ".SS", ".SZ")):
        return True
    return len(t) == 6 and t.isdigit()


def _no_proxy() -> None:
    """akshare 访问国内数据源，绕过系统代理（Clash）。"""
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


class AkshareProvider:
    """从 akshare 拉取 A 股数据快照（输出与 mock 相同的 schema）。"""

    def get_snapshot(self, ticker: str) -> dict:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self._get_snapshot_once(ticker)
            except Exception as exc:
                last_error = exc
                time.sleep(2 * (attempt + 1))
        raise last_error  # type: ignore[misc]

    def _get_snapshot_once(self, ticker: str) -> dict:
        _no_proxy()
        import akshare as ak

        code = ticker.split(".")[0]
        fa = ak.stock_financial_abstract(symbol=code)
        prefix = "sh" if code.startswith(("6", "9")) else "sz"
        hist = ak.stock_zh_a_daily(symbol=f"{prefix}{code}")
        news = ak.stock_news_em(symbol=code)

        income, balance, cashflow = self._financial_rows(fa)
        price_history, price = self._price(hist)

        eps = income[-1].get("eps") if income else None
        market_metrics = {
            "price": price,
            "market_cap_bn": None,
            "target_price": None,
            "analyst_rating": None,
            "pe_ratio": round(price / eps, 1) if price and eps else None,
            "ev_ebitda": None,
        }

        news_list = []
        if news is not None and not news.empty:
            for _, n in news.head(8).iterrows():
                news_list.append(
                    {
                        "title": str(n.get("新闻标题", ""))[:200],
                        "date": str(n.get("发布时间", ""))[:10],
                        "summary": str(n.get("新闻内容", ""))[:500],
                    }
                )

        return {
            "ticker": code,
            "company_name": code,
            "as_of": datetime.now().date().isoformat(),
            "currency": "CNY",
            "data_source": "akshare",
            "financial_data": {
                "income_statement": income,
                "balance_sheet": balance,
                "cash_flow": cashflow,
            },
            "market_metrics": market_metrics,
            "price_history": price_history,
            "peer_data": {"peers": [], "peer_ev_ebitda": []},
            "news": news_list,
        }

    def _financial_rows(self, fa):
        """从财务摘要提取最近 4 个年报期的三表简化数据（金额转百万）。"""
        annual_cols = sorted(
            [c for c in fa.columns[2:] if str(c).endswith("1231")],
            reverse=True,
        )[:4]
        annual_cols.reverse()  # 升序（旧 → 新）

        def val(name, col):
            try:
                v = fa.loc[fa["指标"] == name, col].iloc[0]
                if v is None or (isinstance(v, float) and v != v):
                    return None
                return round(float(v) / 1e6, 2) if abs(float(v)) > 1e6 else round(float(v), 4)
            except Exception:
                return None

        income, balance, cashflow = [], [], []
        for col in annual_cols:
            year = int(str(col)[:4])
            revenue = val("营业总收入", col)
            ocf = val("经营活动现金流净额", col)
            income.append(
                {
                    "year": year,
                    "revenue": revenue,
                    "cogs": val("营业成本", col),
                    "ebitda": None,
                    "net_income": val("归母净利润", col),
                    "eps": val("基本每股收益", col),
                    "interest_expense": None,
                }
            )
            balance.append(
                {
                    "year": year,
                    "total_assets": val("总资产", col),
                    "total_liabilities": None,
                    "total_equity": val("股东权益合计(净资产)", col),
                    "cash_and_equivalents": None,
                    "current_assets": None,
                    "current_liabilities": None,
                    "long_term_debt": None,
                    "short_term_debt": None,
                }
            )
            cashflow.append(
                {
                    "year": year,
                    "operating_cash_flow": ocf,
                    "capex": None,
                    "free_cash_flow": ocf,  # 简化：以经营现金流近似
                }
            )
        return income, balance, cashflow

    def _price(self, hist):
        history = []
        price = None
        if hist is not None and not hist.empty:
            date_col = "date" if "date" in hist.columns else "日期"
            close_col = "close" if "close" in hist.columns else "收盘"
            for _, row in hist.tail(40).iterrows():
                history.append(
                    {
                        "date": str(row.get(date_col, ""))[:10],
                        "close": round(float(row[close_col]), 2),
                    }
                )
            price = round(float(hist.iloc[-1][close_col]), 2)
        return history, price
