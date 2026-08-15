"""WebSocket 实时事件流。"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.observability.ws_manager import ws_manager

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def ws_job(websocket: WebSocket, job_id: str) -> None:
    await websocket.accept()
    manager = websocket.app.state.manager
    # 断线重连：先补发该任务已产生的事件
    for event in manager.db.list_events(job_id):
        await websocket.send_json(event)
    queue = await ws_manager.connect(job_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        ws_manager.disconnect(job_id, queue)
