"""流水线组装与任务入口。"""

from __future__ import annotations

import uuid

from backend.config import project_root
from backend.flow.nodes import (
    DataProcessorNode,
    DoneNode,
    HtmlReportNode,
    InputNode,
    MemoryRetrieveNode,
    MemoryStoreNode,
    MockDataNode,
    PdfReportNode,
    TextAgentBatchNode,
    ValuationNode,
)
from backend.observability.observable import ObservableFlow


def build_report_flow(job_id: str, event_bus=None) -> ObservableFlow:
    """组装 V1 流水线 DAG。"""
    input_node = InputNode(job_id=job_id, event_bus=event_bus)
    data_node = MockDataNode(job_id=job_id, event_bus=event_bus)
    process_node = DataProcessorNode(job_id=job_id, event_bus=event_bus)
    valuation_node = ValuationNode(job_id=job_id, event_bus=event_bus)
    memory_retrieve_node = MemoryRetrieveNode(job_id=job_id, event_bus=event_bus)
    agents_node = TextAgentBatchNode(job_id=job_id, event_bus=event_bus)
    report_node = HtmlReportNode(job_id=job_id, event_bus=event_bus)
    pdf_node = PdfReportNode(job_id=job_id, event_bus=event_bus)
    memory_store_node = MemoryStoreNode(job_id=job_id, event_bus=event_bus)
    done_node = DoneNode(job_id=job_id, event_bus=event_bus)

    input_node >> data_node
    data_node >> process_node
    process_node >> valuation_node
    valuation_node >> memory_retrieve_node
    memory_retrieve_node >> agents_node
    agents_node >> report_node
    report_node >> pdf_node
    pdf_node >> memory_store_node
    memory_store_node >> done_node

    return ObservableFlow(start=input_node, job_id=job_id, event_bus=event_bus)


async def run_job(job: dict, event_bus=None, job_id: str | None = None) -> dict:
    """执行一次分析任务，返回完整 shared 上下文。"""
    job_id = job_id or job.get("job_id") or uuid.uuid4().hex[:16]
    job["job_id"] = job_id
    shared = {"job": job}
    flow = build_report_flow(job_id, event_bus)
    await flow.run_async(shared)
    _write_result(shared, job, job_id)
    return shared


def _write_result(shared: dict, job: dict, job_id: str) -> None:
    """把结构化结果摘要落盘（CLI 与 API 共用，供多任务对比）。"""
    try:
        from backend.comparison.comparator import build_result_json

        result = build_result_json(shared, {**job, "job_id": job_id})
        out_dir = project_root() / "data" / "artifacts"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"job_{job_id}_result.json").write_text(
            __import__("json").dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
