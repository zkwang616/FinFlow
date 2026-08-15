"""事件总线：节点事件 → 订阅者（DB 落库 / WebSocket 广播）。"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Callable

Subscriber = Callable[[dict], None]


class EventBus:
    """同步发布事件；订阅者收到完整事件 dict。"""

    def __init__(self, max_recent: int = 500) -> None:
        self._subscribers: list[Subscriber] = []
        self._recent: deque[dict] = deque(maxlen=max_recent)
        self._seq = 0

    def subscribe(self, fn: Subscriber) -> None:
        self._subscribers.append(fn)

    def publish(self, job_id: str, event_type: str, payload: dict) -> dict:
        event = {
            "job_id": job_id,
            "seq": self._seq,
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "type": event_type,
            "payload": payload,
        }
        self._seq += 1
        self._recent.append(event)
        for fn in self._subscribers:
            fn(event)
        return event

    def recent_events(self, job_id: str) -> list[dict]:
        return [e for e in self._recent if e["job_id"] == job_id]
