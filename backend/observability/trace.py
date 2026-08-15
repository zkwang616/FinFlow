"""执行 trace 副产物：把事件流聚合为审计文档，随分析报告一起输出。"""

from __future__ import annotations

from datetime import datetime


def build_trace(
    job_id: str,
    ticker: str,
    mode: str,
    status: str,
    report_path: str | None,
    events: list[dict],
) -> dict:
    """从全量事件构建结构化 trace：节点级 I/O 摘要、耗时、action、错误。"""
    nodes: list[dict] = []
    current: dict | None = None

    for event in events:
        p = event.get("payload", {})
        etype = event["type"]
        if etype == "node_started":
            current = {"node": p.get("node_name"), "status": "running"}
        elif etype == "node_prepared" and current is not None:
            current["prep_summary"] = p.get("prep_summary")
        elif etype == "node_output" and current is not None:
            current["output_summary"] = p.get("output_summary")
            current["elapsed_ms"] = p.get("elapsed_ms")
        elif etype == "node_finished" and current is not None:
            current["status"] = "success"
            current["action"] = p.get("action")
            current["elapsed_ms"] = p.get("elapsed_ms")
            nodes.append(current)
            current = None
        elif etype == "node_failed" and current is not None:
            current["status"] = "error"
            current["error"] = p.get("error")
            nodes.append(current)
            current = None

    return {
        "job_id": job_id,
        "ticker": ticker,
        "mode": mode,
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "report": report_path,
        "nodes": nodes,
        "event_count": len(events),
        "events": events,
    }
