"""4 个分析 agent：response model、prompt 与结构化 LLM 调用。"""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.config import get_settings, project_root


def _cache_dir() -> Path:
    path = project_root() / "data" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(agent_key: str, data_brief: str, model: str) -> str:
    raw = f"{agent_key}|{model}|{data_brief}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest() + ".json"


class CompanyOverviewResponse(BaseModel):
    overview: str
    key_strengths: list[str]
    key_challenges: list[str]


class ValuationAnalysisResponse(BaseModel):
    valuation_assessment: str
    key_metrics_analysis: str
    fair_value_range: str


class RiskAnalysisResponse(BaseModel):
    risks: list[str]
    risk_rating: str
    risk_mitigation: str


class TakeawaysResponse(BaseModel):
    investment_thesis: str
    key_catalysts: list[str]
    watch_indicators: list[str]
    conclusion: str


class NewsSummaryResponse(BaseModel):
    summary: str
    sentiment: str  # positive / negative / neutral
    sentiment_score: float  # -1.0 ~ 1.0
    key_headlines: list[str]


class CompetitorAnalysisResponse(BaseModel):
    competitive_position: str
    main_competitors: list[str]
    moat_assessment: str


class CatalystAnalysisResponse(BaseModel):
    near_term_catalysts: list[str]
    risks_to_catalysts: list[str]
    outlook: str


class FinancialHealthResponse(BaseModel):
    health_assessment: str
    strengths: list[str]
    concerns: list[str]


AGENTS: list[dict] = [
    {
        "key": "company_overview",
        "name": "Company Overview Analyst",
        "response_model": CompanyOverviewResponse,
        "system_prompt": (
            "You are a professional equity research analyst specializing in company overviews. "
            "Analyze the provided financial data and news. "
            "Return ONLY a valid JSON object matching the schema: "
            '{"overview": string, "key_strengths": [string], "key_challenges": [string]}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "valuation_analysis",
        "name": "Valuation Analyst",
        "response_model": ValuationAnalysisResponse,
        "system_prompt": (
            "You are a professional equity valuation analyst. "
            "Assess valuation using revenue growth, EBITDA, net margin, P/E, EV/EBITDA and peer comparisons. "
            "Return ONLY a valid JSON object matching the schema: "
            '{"valuation_assessment": string, "key_metrics_analysis": string, "fair_value_range": string}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "risks",
        "name": "Risk Analyst",
        "response_model": RiskAnalysisResponse,
        "system_prompt": (
            "You are a professional risk analyst. "
            "Identify the most material risks for the company based on the data and news provided. "
            "Return ONLY a valid JSON object matching the schema: "
            '{"risks": [string], "risk_rating": string, "risk_mitigation": string}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "takeaways",
        "name": "Investment Takeaways Analyst",
        "response_model": TakeawaysResponse,
        "system_prompt": (
            "You are a senior portfolio strategist writing investment takeaways. "
            "Summarize the thesis, catalysts, and watch indicators. "
            "Return ONLY a valid JSON object matching the schema: "
            '{"investment_thesis": string, "key_catalysts": [string], "watch_indicators": [string], "conclusion": string}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "news_summary",
        "name": "News & Sentiment Analyst",
        "response_model": NewsSummaryResponse,
        "system_prompt": (
            "You are a financial news analyst. Summarize the recent news, judge the overall "
            "market sentiment (positive/negative/neutral), and give a sentiment score from -1.0 "
            "(very negative) to 1.0 (very positive). "
            "Return ONLY a valid JSON object matching the schema: "
            '{"summary": string, "sentiment": string, "sentiment_score": number, '
            '"key_headlines": [string]}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "competitor_analysis",
        "name": "Competitor Analyst",
        "response_model": CompetitorAnalysisResponse,
        "system_prompt": (
            "You are a competitive strategy analyst. Assess the company's competitive position "
            "against its peers using the peer valuation data and financial metrics provided. "
            "Return ONLY a valid JSON object matching the schema: "
            '{"competitive_position": string, "main_competitors": [string], '
            '"moat_assessment": string}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "catalyst_analysis",
        "name": "Catalyst Analyst",
        "response_model": CatalystAnalysisResponse,
        "system_prompt": (
            "You are a catalysts analyst. Identify near-term catalysts for the stock based on "
            "the recent news and revenue forecast, and the risks that could derail them. "
            "Return ONLY a valid JSON object matching the schema: "
            '{"near_term_catalysts": [string], "risks_to_catalysts": [string], '
            '"outlook": string}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
    {
        "key": "financial_health",
        "name": "Financial Health Analyst",
        "response_model": FinancialHealthResponse,
        "system_prompt": (
            "You are a financial health analyst. Assess the company's financial strength using "
            "the calculated ratios provided (ROE, ROIC, margins, leverage, liquidity, interest "
            "coverage, FCF margin). "
            "Return ONLY a valid JSON object matching the schema: "
            '{"health_assessment": string, "strengths": [string], "concerns": [string]}. '
            "Do not include markdown fences or any text outside the JSON."
        ),
    },
]


def build_data_brief(
    processed: dict,
    valuation: dict | None = None,
    memory_context: list[dict] | None = None,
    recommendation: dict | None = None,
) -> str:
    """把处理后的指标、定量估值与历史记忆转成所有 agent 共享的数据简报。"""
    def _fmt(value, spec: str = ".2f") -> str:
        return f"{value:{spec}}" if value is not None else "n/a"

    market = processed["market"]
    lines = [
        f"Company: {processed['company_name']} ({processed['ticker']})",
        f"Data as of: {processed['as_of']}",
        f"Latest fiscal year: {_fmt(processed.get('latest_year'), 'd')}",
        (
            f"Revenue: {_fmt(processed.get('latest_revenue'), '.0f')} "
            f"(growth {_fmt(processed.get('revenue_growth_pct'), '.1f')}% YoY)"
            if processed["revenue_growth_pct"] is not None
            else f"Revenue: {_fmt(processed.get('latest_revenue'), '.0f')}"
        ),
        f"EBITDA: {_fmt(processed.get('latest_ebitda'), '.0f')}",
        f"Net income: {_fmt(processed.get('latest_net_income'), '.0f')} "
        f"(margin {_fmt(processed.get('net_margin_pct'), '.1f')}%)",
        f"EPS: {_fmt(processed.get('latest_eps'), '.2f')}",
        f"Current price: {_fmt(market.get('price'), '.2f')} | "
        f"Market cap: {_fmt(market.get('market_cap_bn'), '.1f')}B",
        f"Analyst rating: {market.get('analyst_rating') or 'n/a'} | "
        f"Target: {_fmt(market.get('target_price'), '.2f')}",
        f"P/E: {_fmt(market.get('pe_ratio'), '.1f')} | "
        f"EV/EBITDA: {_fmt(market.get('ev_ebitda'), '.1f')}",
    ]
    if processed["forecast_revenue_1y"]:
        lines.append(f"1y revenue forecast: {processed['forecast_revenue_1y']:.0f}")
    if processed["peer_ev_ebitda"]:
        peer_str = ", ".join(
            f"{p['ticker']}={p['ev_ebitda']}" for p in processed["peer_ev_ebitda"]
        )
        lines.append(f"Peer EV/EBITDA: {peer_str}")
    if processed["news"]:
        lines.append("Recent news:")
        for i, n in enumerate(processed["news"][:5], 1):
            lines.append(f"  {i}. [{n['date']}] {n['title']}: {n['summary']}")
    if valuation:
        lines.append("Quantitative valuation (calculated from data, not LLM-estimated):")
        dcf = valuation.get("dcf") or {}
        if dcf.get("value_per_share") is not None:
            lines.append(
                f"  DCF fair value per share: ${dcf['value_per_share']:.2f} "
                f"(WACC {dcf.get('wacc', 0.09) * 100:.0f}%, terminal g {dcf.get('terminal_growth', 0.025) * 100:.1f}%)"
            )
        comp = valuation.get("comparable") or {}
        if comp.get("value_per_share") is not None:
            lines.append(
                f"  Comparable EV/EBITDA valuation: ${comp['value_per_share']:.2f} "
                f"(median peer multiple {comp.get('median_multiple', 0):.1f}x)"
            )
        rng = valuation.get("range") or {}
        if rng.get("low") is not None:
            lines.append(
                f"  Combined fair value range: ${rng['low']:.2f} - ${rng['high']:.2f} "
                f"(mid ${rng['mid']:.2f})"
            )
        sens = valuation.get("sensitivity") or []
        if sens:
            vals = [
                v
                for row in sens
                for k, v in row.items()
                if k != "wacc" and v is not None
            ]
            if vals:
                lines.append(
                    f"  DCF sensitivity (WACC 8-10% × terminal g 2-3%): "
                    f"${min(vals):.2f} - ${max(vals):.2f}"
                )
    if memory_context:
        lines.append(
            "Historical analysis memory (from previous runs, for reference). "
            "If relevant, briefly note consistency or divergence with these prior conclusions:"
        )
        for m in memory_context[:3]:
            lines.append(f"  - {m.get('text', '')[:400]}")
    if recommendation:
        lines.append(
            "Quantitative recommendation (rule-based, from valuation vs price): "
            f"{recommendation.get('recommendation', 'hold')} at "
            f"{recommendation.get('position_pct', 0)}% position "
            f"(confidence {recommendation.get('confidence', 0):.1f}). "
            f"{recommendation.get('rationale', '')}"
        )
    return "\n".join(lines)


def _extract_json(text: str) -> str:
    """容错解析：优先整体解析，失败则提取第一个 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    return text


async def call_structured(
    agent: dict,
    data_brief: str,
    settings: dict | None = None,
    no_cache: bool = False,
    temperature: float = 0.3,
) -> dict:
    """调用 DeepSeek 并解析为结构化 JSON；默认启用磁盘缓存。"""
    settings = settings or get_settings()
    if not settings["deepseek_api_key"]:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )
    model = settings["deepseek_model"]

    cache_path = _cache_dir() / _cache_key(
        agent["key"], f"t={temperature}|{data_brief}", model
    )
    if not no_cache and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    client = AsyncOpenAI(
        api_key=settings["deepseek_api_key"],
        base_url=settings["deepseek_base_url"],
    )
    response_model = agent["response_model"]

    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": data_brief},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    raw = resp.choices[0].message.content or ""
    content = response_model.model_validate_json(_extract_json(raw)).model_dump()
    cache_path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return content
