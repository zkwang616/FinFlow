"""命令行入口：python -m backend.cli --ticker AAPL"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

from backend.flow.pipeline import run_job


async def _main(args) -> int:
    if args.compare:
        from backend.comparison.comparator import compare

        data = compare(args.compare.upper())
        print(f"=== compare {args.compare.upper()} ({data['run_count']} runs) ===")
        print(json.dumps(data["summary"], ensure_ascii=False, indent=2))
        return 0

    if not args.ticker:
        print("error: --ticker is required (or use --compare)")
        return 2

    job = {
        "ticker": args.ticker,
        "mode": args.mode,
        "no_cache": args.no_cache,
    }
    t0 = time.perf_counter()
    ok_counts: dict[str, int] = {}
    fail_counts: dict[str, int] = {}
    for i in range(args.repeat):
        shared = await run_job(job)
        print(f"run {i + 1}/{args.repeat} status: {shared.get('job_status')}")
        for key, section in shared.get("text_sections", {}).items():
            if shared.get("agent_failures") and any(key in f for f in shared["agent_failures"]):
                fail_counts[key] = fail_counts.get(key, 0) + 1
            elif section:
                ok_counts[key] = ok_counts.get(key, 0) + 1
        print("  report:", shared["result"]["report_path"])
        if args.verbose:
            print(
                "  agent failures:",
                json.dumps(shared.get("agent_failures", []), ensure_ascii=False),
            )
    elapsed = time.perf_counter() - t0
    print(f"\n{args.repeat} run(s) finished in {elapsed:.1f}s")
    if args.repeat > 1:
        print("per-agent success counts:", json.dumps(ok_counts, ensure_ascii=False))
        if fail_counts:
            print("per-agent failure counts:", json.dumps(fail_counts, ensure_ascii=False))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="FinFlow report generation")
    parser.add_argument("--ticker", default="", help="stock ticker (e.g. AAPL)")
    parser.add_argument("--mode", default="mock", choices=["mock", "real"])
    parser.add_argument("--repeat", type=int, default=1, help="run N times (consistency experiments)")
    parser.add_argument("--no-cache", action="store_true", help="bypass LLM cache")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--compare", metavar="TICKER", help="compare previous runs of a ticker")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()
