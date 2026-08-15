"""失败路径验证：不存在的 ticker → 节点失败事件 + 任务失败状态。"""

from __future__ import annotations

import asyncio
import json
import urllib.request

from websockets.asyncio.client import connect

BASE = "http://127.0.0.1:8000"


async def main() -> None:
    req = urllib.request.Request(
        BASE + "/api/jobs",
        data=json.dumps({"ticker": "UNKNOWN", "mode": "mock"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    job_id = json.loads(urllib.request.urlopen(req).read())["job_id"]
    print("job_id:", job_id)

    seen = []
    async with connect(f"ws://127.0.0.1:8000/ws/jobs/{job_id}") as ws:
        while True:
            msg = json.loads(await ws.recv())
            seen.append(msg["type"])
            if msg["type"] in ("job_finished", "job_failed"):
                print("final event payload:", msg["payload"])
                break

    print("event types:", seen)
    assert "node_failed" in seen, "expected node_failed event"
    assert "job_failed" in seen, "expected job_failed event"
    job = json.loads(urllib.request.urlopen(f"{BASE}/api/jobs/{job_id}").read())
    print("job status:", job["status"])
    assert job["status"] == "failed"
    print("PASS")


if __name__ == "__main__":
    asyncio.run(main())
