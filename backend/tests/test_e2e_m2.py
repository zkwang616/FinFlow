"""M2 端到端验证：创建任务 → WS 收事件流 → 事件落库。

前置条件：uvicorn 已在 127.0.0.1:8000 启动。
运行：.venv\Scripts\python.exe -m backend.tests.test_e2e_m2
"""

from __future__ import annotations

import asyncio
import json
import urllib.request

from websockets.asyncio.client import connect

BASE = "http://127.0.0.1:8000"


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read())


def _get(path: str):
    return json.loads(urllib.request.urlopen(BASE + path).read())


async def main() -> None:
    resp = _post("/api/jobs", {"ticker": "AAPL", "mode": "mock"})
    job_id = resp["job_id"]
    print("job_id:", job_id)

    types: list[str] = []
    async with connect(f"ws://127.0.0.1:8000/ws/jobs/{job_id}") as ws:
        while True:
            msg = json.loads(await ws.recv())
            types.append(msg["type"])
            node = msg.get("payload", {}).get("node_name", "")
            print(f"  [{msg['type']}] {node}")
            if msg["type"] in ("job_finished", "job_failed"):
                print("  payload:", msg["payload"])
                break

    print("\nreal-time event types:", types)
    print("db events:", len(_get(f"/api/jobs/{job_id}/events")))
    job = _get(f"/api/jobs/{job_id}")
    print("job status:", job["status"], "| report:", job.get("report_path"))


if __name__ == "__main__":
    asyncio.run(main())
