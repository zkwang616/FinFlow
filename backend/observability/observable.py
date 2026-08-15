"""可观测节点/流程：不改 PocketFlow 源码，在生命周期外包装事件。"""

from __future__ import annotations

import time
import uuid
from typing import Any

import pandas as pd
from pocketflow import AsyncFlow, AsyncNode


def summarize(obj: Any, max_items: int = 8, max_len: int = 200) -> Any:
    """把任意对象转成可序列化的摘要（DataFrame 只留 shape/列名/前几行）。"""
    if isinstance(obj, pd.DataFrame):
        return {
            "kind": "DataFrame",
            "shape": list(obj.shape),
            "columns": list(obj.columns)[:max_items],
            "head": obj.head(2).to_dict(orient="records"),
        }
    if isinstance(obj, dict):
        return {k: summarize(v, max_items, max_len) for k, v in list(obj.items())[:max_items]}
    if isinstance(obj, (list, tuple)):
        return [summarize(v, max_items, max_len) for v in list(obj)[:max_items]]
    if isinstance(obj, str):
        return obj[:max_len]
    if obj is None or isinstance(obj, (int, float, bool)):
        return obj
    return repr(obj)[:max_len]


class ObservableNode(AsyncNode):
    """在 _run_async 外包装 prep/exec/post，广播生命周期事件。"""

    def __init__(
        self,
        job_id: str | None = None,
        event_bus=None,
        node_id: str | None = None,
        max_retries: int = 1,
        wait: int = 0,
    ) -> None:
        super().__init__(max_retries=max_retries, wait=wait)
        self.job_id = job_id
        self.event_bus = event_bus
        self.node_id = node_id or uuid.uuid4().hex[:12]
        self.node_name = type(self).__name__

    def _emit(self, event_type: str, payload: dict) -> None:
        if self.event_bus and self.job_id:
            self.event_bus.publish(
                self.job_id,
                event_type,
                {"node_id": self.node_id, "node_name": self.node_name, **payload},
            )

    async def _run_async(self, shared: dict):
        self._emit("node_started", {})
        t0 = time.perf_counter()
        try:
            prep_res = await self.prep_async(shared)
            self._emit("node_prepared", {"prep_summary": summarize(prep_res)})
            exec_res = await self._exec(prep_res)
            self._emit(
                "node_output",
                {"output_summary": summarize(exec_res), "elapsed_ms": (time.perf_counter() - t0) * 1000},
            )
            action = await self.post_async(shared, prep_res, exec_res)
            self._emit(
                "node_finished",
                {"action": action, "elapsed_ms": (time.perf_counter() - t0) * 1000},
            )
            return action
        except Exception as exc:
            self._emit(
                "node_failed",
                {"error": str(exc), "elapsed_ms": (time.perf_counter() - t0) * 1000},
            )
            raise


class ObservableFlow(AsyncFlow):
    """包装整个流程执行，广播 flow 级事件。"""

    def __init__(self, start=None, job_id: str | None = None, event_bus=None) -> None:
        super().__init__(start=start)
        self.job_id = job_id
        self.event_bus = event_bus
        self.flow_id = uuid.uuid4().hex[:12]

    def _emit(self, event_type: str, payload: dict) -> None:
        if self.event_bus and self.job_id:
            self.event_bus.publish(
                self.job_id,
                event_type,
                {"flow_id": self.flow_id, **payload},
            )

    async def _run_async(self, shared: dict):
        self._emit("flow_started", {})
        t0 = time.perf_counter()
        try:
            prep_res = await self.prep_async(shared)
            orch_res = await self._orch_async(shared)
            result = await self.post_async(shared, prep_res, orch_res)
            self._emit(
                "flow_finished",
                {"status": "succeeded", "elapsed_ms": (time.perf_counter() - t0) * 1000},
            )
            return result
        except Exception as exc:
            self._emit(
                "flow_failed",
                {"error": str(exc), "elapsed_ms": (time.perf_counter() - t0) * 1000},
            )
            raise
