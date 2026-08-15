"""从 runs.jsonl 中打印关键字段的跨 run 示例（研究报告中用）。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--n", type=int, default=4, help="show first N runs")
    args = parser.parse_args()

    runs = [
        json.loads(line)
        for line in args.jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    n = min(args.n, len(runs))

    print(f"=== risk_rating & risks (runs 1-{n}) ===")
    for r in runs[:n]:
        s = r["sections"]["risks"]
        print(f"run {r['run']}: rating={s['risk_rating']!r}")
        print(f"   risks={s['risks']}")

    print(f"\n=== fair_value_range (runs 1-{n}) ===")
    for r in runs[:n]:
        print(f"run {r['run']}: {r['sections']['valuation_analysis']['fair_value_range']!r}")

    print(f"\n=== conclusion (runs 1-{n}) ===")
    for r in runs[:n]:
        print(f"run {r['run']}: {r['sections']['takeaways']['conclusion'][:150]!r}")

    print(f"\n=== key_strengths (runs 1-{n}) ===")
    for r in runs[:n]:
        print(f"run {r['run']}: {r['sections']['company_overview']['key_strengths']}")


if __name__ == "__main__":
    main()
