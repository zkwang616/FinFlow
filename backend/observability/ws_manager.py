"""WebSocket 连接管理：按 job 分发事件到各连接队列。"""

from __future__ import annotations

import asyncio
from collections import defaultdict


class WebSocketManager:
    def __init__(self, queue_size: int = 1000) -> None:
        self._queues: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._queue_size = queue_size

    async def connect(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        self._queues[job_id].add(q)
        return q

    def disconnect(self, job_id: str, q: asyncio.Queue) -> None:
        self._queues[job_id].discard(q)

    def push(self, job_id: str, event: dict) -> None:
        for q in list(self._queues.get(job_id, ())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # 队列满时丢弃，前端可从 DB 补拉


ws_manager = WebSocketManager()
