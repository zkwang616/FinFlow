"""任务管理器：提交任务、并发控制、事件发布、状态流转。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.config import project_root
from backend.flow.pipeline import build_report_flow
from backend.observability.event_bus import EventBus
from backend.observability.ws_manager import ws_manager
from backend.storage.db import Database


class JobManager:
    def __init__(self, max_concurrent: int = 2, db_path: Path | str | None = None) -> None:
        self.db = Database(db_path or project_root() / "data" / "finflow.db")
        self.bus = EventBus()
        self.bus.subscribe(self.db.append_event)
        self.bus.subscribe(lambda event: ws_manager.push(event["job_id"], event))
        self._sem = asyncio.Semaphore(max_concurrent)
        self._tasks: dict[str, asyncio.Task] = {}

    def submit(self, params: dict) -> str:
        job_id = self.db.create_job(params)
        task = asyncio.get_running_loop().create_task(self._run_job(job_id, params))
        self._tasks[job_id] = task
        return job_id

    async def _run_job(self, job_id: str, params: dict) -> None:
        self.bus.publish(job_id, "job_created", {"params": params})
        try:
            async with self._sem:
                self.db.update_job_status(job_id, "running")
                self.bus.publish(job_id, "job_started", {})
                shared = {"job": {**params, "job_id": job_id}}
                flow = build_report_flow(job_id, self.bus)
                await flow.run_async(shared)
                report_path = shared["result"]["report_path"]
                self.db.update_job_status(job_id, "succeeded", report_path=report_path)
                self.bus.publish(
                    job_id,
                    "job_finished",
                    {"status": "succeeded", "report_path": report_path},
                )
        except Exception as exc:
            self.db.update_job_status(job_id, "failed")
            self.bus.publish(job_id, "job_failed", {"error": str(exc)})
