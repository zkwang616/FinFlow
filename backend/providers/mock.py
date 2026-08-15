"""内置示例数据源（V1 唯一数据源，离线可用）。"""

from __future__ import annotations

import json
from pathlib import Path

_MOCK_DIR = Path(__file__).resolve().parents[2] / "data" / "mock"


class MockProvider:
    """从 data/mock/{TICKER}.json 读取一份"分析快照"。"""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or _MOCK_DIR

    def get_snapshot(self, ticker: str) -> dict:
        """返回某 ticker 的完整数据快照（财务、市场、新闻）。"""
        path = self.data_dir / f"{ticker.upper()}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"No mock data for {ticker.upper()} (expected {path}). "
                f"Available: {self.available_tickers()}"
            )
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def available_tickers(self) -> list[str]:
        return sorted(p.stem for p in self.data_dir.glob("*.json"))
