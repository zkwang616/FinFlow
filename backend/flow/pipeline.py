"""流水线组装与任务入口。"""

from __future__ import annotations

import uuid

from backend.flow.nodes import (
    DataProcessorNode,
    DoneNode,
    HtmlReportNode,
    InputNode,
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
    agents_node = TextAgentBatchNode(job_id=job_id, event_bus=event_bus)
    report_node = HtmlReportNode(job_id=job_id, event_bus=event_bus)
    pdf_node = PdfReportNode(job_id=job_id, event_bus=event_bus)
    done_node = DoneNode(job_id=job_id, event_bus=event_bus)

    input_node >> data_node
    data_node >> process_node
    process_node >> valuation_node
    valuation_node >> agents_node
    agents_node >> report_node
    report_node >> pdf_node
    pdf_node >> done_node

    return ObservableFlow(start=input_node, job_id=job_id, event_bus=event_bus)


async def run_job(job: dict, event_bus=None, job_id: str | None = None) -> dict:
    """执行一次分析任务，返回完整 shared 上下文。"""
    job_id = job_id or job.get("job_id") or uuid.uuid4().hex[:16]
    job["job_id"] = job_id
    shared = {"job": job}
    flow = build_report_flow(job_id, event_bus)
    await flow.run_async(shared)
    return shared
