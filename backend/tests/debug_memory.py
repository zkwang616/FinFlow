"""调试 Mem0 记忆检索（诊断用）。"""

from __future__ import annotations

from backend.memory.memory_service import get_memory, search_memories


def main() -> None:
    m = get_memory()
    print("=== get_all ===")
    all_items = m.get_all(filters={"user_id": "finflow"})
    memories = all_items.get("results", all_items) if isinstance(all_items, dict) else all_items
    print(f"count: {len(memories)}")
    for item in memories[:5]:
        print(" -", str(item.get("memory", item))[:200])

    print("\n=== search variants ===")
    q = "Apple Inc. (AAPL) investment analysis conclusion"
    variants = {
        "no filter": lambda: m.search(q, top_k=5),
        "user_id kwarg": lambda: m.search(q, top_k=5, user_id="finflow"),
        "filters user_id": lambda: m.search(q, top_k=5, filters={"user_id": "finflow"}),
        "threshold 0": lambda: m.search(q, top_k=5, user_id="finflow", threshold=0.0),
    }
    for name, fn in variants.items():
        try:
            res = fn()
            print(f"{name}: {len(res.get('results', res))} results")
            for r in res.get("results", res)[:2]:
                print("   score:", r.get("score"), "|", str(r.get("memory", ""))[:100])
        except Exception as exc:
            print(f"{name}: ERROR {exc}")


if __name__ == "__main__":
    main()
