"""V1 流水线节点：Input → MockData → DataProcessor → TextAgents → HtmlReport → Done。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pocketflow import AsyncParallelBatchNode

from backend.config import project_root
from backend.flow.agents import AGENTS, build_data_brief, call_structured
from backend.flow.processing import process_snapshot
from backend.observability.observable import ObservableNode
from backend.providers.mock import MockProvider
from backend.report.html import render_html


class InputNode(ObservableNode):
    """校验任务参数，写 ticker/mode 到 shared。"""

    async def prep_async(self, shared):
        return shared["job"]

    async def exec_async(self, job):
        ticker = str(job.get("ticker", "")).strip().upper()
        mode = str(job.get("mode", "mock")).strip().lower()
        if not ticker:
            raise ValueError("ticker is required")
        if mode not in ("mock", "real"):
            raise ValueError(f"unsupported mode: {mode}")
        return {"ticker": ticker, "mode": mode}

    async def post_async(self, shared, prep_res, exec_res):
        shared["ticker"] = exec_res["ticker"]
        shared["mode"] = exec_res["mode"]
        return "default"


class MockDataNode(ObservableNode):
    """从内置示例数据读取分析快照。"""

    async def prep_async(self, shared):
        return shared["ticker"]

    async def exec_async(self, ticker):
        return MockProvider().get_snapshot(ticker)

    async def post_async(self, shared, prep_res, exec_res):
        shared["snapshot"] = exec_res
        return "default"


class DataProcessorNode(ObservableNode):
    """计算历史指标、增长率与预测。"""

    async def prep_async(self, shared):
        return shared["snapshot"]

    async def exec_async(self, snapshot):
        return process_snapshot(snapshot)

    async def post_async(self, shared, prep_res, exec_res):
        shared["processed"] = exec_res
        return "default"


class TextAgentBatchNode(ObservableNode, AsyncParallelBatchNode):
    """4 个分析 agent 并行执行；单个失败不影响整体，标记 fallback。"""

    async def prep_async(self, shared):
        data_brief = build_data_brief(shared["processed"])
        return [
            {
                "agent": agent,
                "data_brief": data_brief,
                "no_cache": bool(shared.get("job", {}).get("no_cache", False)),
                "temperature": float(shared.get("job", {}).get("temperature", 0.3)),
            }
            for agent in AGENTS
        ]

    async def exec_async(self, item):
        agent = item["agent"]
        try:
            content = await call_structured(
                agent,
                item["data_brief"],
                no_cache=item.get("no_cache", False),
                temperature=item.get("temperature", 0.3),
            )
            return {"agent_key": agent["key"], "ok": True, "content": content}
        except Exception as exc:  # 单个 agent 失败 → fallback，不中断流水线
            return {
                "agent_key": agent["key"],
                "ok": False,
                "error": str(exc),
                "content": {
                    "overview": f"[Fallback] Analysis unavailable for {agent['name']}: {exc}",
                },
            }

    async def post_async(self, shared, prep_res, exec_res):
        sections: dict = {}
        failed: list[str] = []
        for result in exec_res:
            key = result["agent_key"]
            if result["ok"]:
                sections[key] = result["content"]
            else:
                failed.append(f"{key} ({result['error'][:120]})")
                sections[key] = result["content"]
        shared["text_sections"] = sections
        shared["agent_failures"] = failed
        return "default"


class HtmlReportNode(ObservableNode):
    """渲染 HTML 报告并落盘。"""

    async def prep_async(self, shared):
        return {
            "processed": shared["processed"],
            "sections": shared["text_sections"],
            "failures": shared.get("agent_failures", []),
        }

    async def exec_async(self, payload):
        html = render_html(payload["processed"], payload["sections"], payload["failures"])
        artifacts = project_root() / "data" / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        ticker = payload["processed"]["ticker"]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = artifacts / f"{ticker}_{ts}.html"
        path.write_text(html, encoding="utf-8")
        return {"path": str(path), "html": html}

    async def post_async(self, shared, prep_res, exec_res):
        shared["report"] = exec_res
        return "default"


class DoneNode(ObservableNode):
    """流水线收尾。"""

    async def prep_async(self, shared):
        return shared.get("report")

    async def exec_async(self, report):
        return {"status": "succeeded", "report_path": report["path"]}

    async def post_async(self, shared, prep_res, exec_res):
        shared["job_status"] = "succeeded"
        shared["result"] = exec_res
        return "default"
