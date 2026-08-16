"""Mem0 记忆服务：分析结论写入与检索（本地向量库 + DeepSeek LLM）。"""

from __future__ import annotations

import os

from backend.config import get_settings, project_root

_memory = None

os.environ.setdefault("MEM0_TELEMETRY", "False")


def memory_enabled() -> bool:
    return os.getenv("FINFLOW_MEMORY", "1").lower() not in ("0", "false", "off")


def get_memory():
    """初始化 Mem0（懒加载单例）。embedding 用本地 fastembed，向量库用本地 chroma。"""
    global _memory
    if _memory is not None:
        return _memory
    settings = get_settings()
    mem_dir = project_root() / "data" / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": settings["deepseek_model"],
                "api_key": settings["deepseek_api_key"],
                "openai_base_url": settings["deepseek_base_url"],
                "temperature": 0.1,
            },
        },
        "embedder": {
            "provider": "fastembed",
            "config": {"model": "BAAI/bge-small-en-v1.5"},
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "finflow_memories",
                "path": str(mem_dir / "chroma"),
            },
        },
        "history_db_path": str(mem_dir / "history.db"),
    }
    from mem0 import Memory

    _memory = Memory.from_config(config)
    return _memory


def build_memory_text(processed: dict, sections: dict, valuation: dict | None) -> str:
    """把一次分析的关键结论压缩成一条记忆文本。"""
    lines = [
        f"Investment analysis of {processed.get('company_name', '')} "
        f"({processed.get('ticker', '')}) as of {processed.get('as_of', '')}."
    ]
    takeaways = sections.get("takeaways") or {}
    if takeaways.get("investment_thesis"):
        lines.append(f"Thesis: {takeaways['investment_thesis']}")
    if takeaways.get("conclusion"):
        lines.append(f"Conclusion: {takeaways['conclusion']}")
    rng = (valuation or {}).get("range")
    if rng:
        lines.append(
            f"Fair value range: ${rng['low']:.2f} - ${rng['high']:.2f} "
            f"(mid ${rng['mid']:.2f})"
        )
    risks = (sections.get("risks") or {}).get("risks") or []
    if risks:
        lines.append("Key risks: " + "; ".join(str(r) for r in risks[:3]))
    return " ".join(lines)


def store_analysis_memory(
    processed: dict, sections: dict, valuation: dict | None
) -> dict:
    """把本次分析结论写入 Mem0。"""
    if not memory_enabled():
        return {"stored": False, "reason": "memory disabled"}
    text = build_memory_text(processed, sections, valuation)
    metadata = {
        "ticker": processed.get("ticker", ""),
        "company_name": processed.get("company_name", ""),
        "as_of": processed.get("as_of", ""),
    }
    get_memory().add(text, user_id="finflow", agent_id="analyst", metadata=metadata)
    return {"stored": True}


def search_memories(query: str, limit: int = 3) -> list[dict]:
    """检索与 query 相关的历史分析记忆。失败时返回空（不影响主流程）。"""
    if not memory_enabled():
        return []
    try:
        resp = get_memory().search(
            query, top_k=limit, filters={"user_id": "finflow"}
        )
        results = resp.get("results", []) if isinstance(resp, dict) else resp
        return [
            {
                "text": r.get("memory", ""),
                "score": r.get("score"),
                "metadata": r.get("metadata") or {},
            }
            for r in results
        ]
    except Exception:
        return []
