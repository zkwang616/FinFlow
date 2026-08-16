"""投资建议规则引擎：基于定量估值区间与当前股价推导（确定性、可复现）。"""

from __future__ import annotations


def compute_recommendation(processed: dict, valuation: dict | None) -> dict:
    """根据估值区间与当前价给出建议。

    规则：
    - 价格低于区间下沿 → buy，仓位随折价幅度上调（10-40%）
    - 价格在区间内 → hold，仓位 20%（下沿附近 30%，上沿附近 10%）
    - 价格高于区间上沿 → reduce，仓位 5%
    """
    price = processed.get("market", {}).get("price")
    rng = (valuation or {}).get("range") if valuation else None
    if price is None or not rng or rng.get("low") is None:
        return {"recommendation": "hold", "position_pct": 0, "confidence": 0.0,
                "rationale": "insufficient valuation data"}

    low, high = rng["low"], rng["high"]
    width = max(high - low, 1e-9)

    if price < low:
        discount = (low - price) / low
        position = min(40, round(10 + discount * 100 * 0.6))
        return {
            "recommendation": "buy",
            "position_pct": position,
            "confidence": 0.7,
            "rationale": (
                f"price ${price:.2f} is below fair value range ${low:.2f}-${high:.2f} "
                f"({discount * 100:.1f}% discount to lower bound)"
            ),
        }
    if price > high:
        premium = (price - high) / high
        return {
            "recommendation": "reduce",
            "position_pct": 5,
            "confidence": 0.6,
            "rationale": (
                f"price ${price:.2f} exceeds fair value range ${low:.2f}-${high:.2f} "
                f"({premium * 100:.1f}% premium to upper bound)"
            ),
        }

    # 区间内：按位置线性映射 30%（下沿）→ 10%（上沿）
    pos_in_range = (price - low) / width
    position = max(10, round(30 - pos_in_range * 20))
    return {
        "recommendation": "hold",
        "position_pct": position,
        "confidence": 0.5,
        "rationale": (
            f"price ${price:.2f} within fair value range ${low:.2f}-${high:.2f}; "
            f"position sized by distance to bounds"
        ),
    }
