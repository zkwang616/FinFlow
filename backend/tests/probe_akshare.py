"""探测 akshare 接口结构（V3c 开发用）。"""

from __future__ import annotations

import akshare as ak


def main() -> None:
    import os

    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"
    print("akshare version:", ak.__version__)

    print("\n=== financial abstract (600519) ===")
    try:
        df = ak.stock_financial_abstract(symbol="600519")
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.head(8).to_string())
    except Exception as exc:
        print("ERROR:", exc)

    print("\n=== individual info ===")
    try:
        df = ak.stock_individual_info_em(symbol="600519")
        print(df.to_string())
    except Exception as exc:
        print("ERROR:", exc)

    print("\n=== bid ask ===")
    try:
        df = ak.stock_bid_ask_em(symbol="600519")
        print(df.to_string())
    except Exception as exc:
        print("ERROR:", exc)

    print("\n=== sina daily ===")
    try:
        df = ak.stock_zh_a_daily(symbol="sh600519")
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.tail(3).to_string())
    except Exception as exc:
        print("ERROR:", exc)

    print("\n=== financial abstract 指标名 ===")
    try:
        df = ak.stock_financial_abstract(symbol="600519")
        names = df["指标"].tolist()
        for i, n in enumerate(names):
            print(i, repr(n))
    except Exception as exc:
        print("ERROR:", exc)

    print("\n=== daily hist ===")
    try:
        df = ak.stock_zh_a_hist(
            symbol="600519", period="daily", start_date="20260601", end_date="20260815", adjust="qfq"
        )
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.head(3).to_string())
    except Exception as exc:
        print("ERROR:", exc)

    print("\n=== news ===")
    try:
        df = ak.stock_news_em(symbol="600519")
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.head(3).to_string())
    except Exception as exc:
        print("ERROR:", exc)


if __name__ == "__main__":
    main()
