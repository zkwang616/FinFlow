"""PDF 报告生成（reportlab）。"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _table(data: list[list], col_widths: list[float] | None = None) -> Table:
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def build_pdf(
    processed: dict,
    sections: dict,
    valuation: dict | None,
    output_path: Path | str,
) -> str:
    """生成 PDF 分析报告，返回输出路径。"""
    output_path = Path(output_path)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Financial Analysis - {processed['ticker']}",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, textColor=colors.grey)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=4)

    story = []
    story.append(Paragraph(
        f"{processed['company_name']} ({processed['ticker']})", styles["Title"]
    ))
    story.append(Paragraph(
        f"Data as of {processed['as_of']} · Latest fiscal year {processed['latest_year']} · "
        f"Source: {processed.get('data_source', 'mock')}",
        small,
    ))
    story.append(Spacer(1, 8))

    market = processed["market"]
    ratios = processed.get("ratios", {})

    def metric_rows(pairs: list[tuple[str, object]]) -> list[list]:
        return [["Metric", "Value"]] + [[str(k), str(v)] for k, v in pairs]

    story.append(Paragraph("Financial Ratios", styles["Heading2"]))
    ratio_pairs = [
        ("Gross Margin", f"{ratios.get('gross_margin_pct', 'n/a')}%"),
        ("Net Margin", f"{ratios.get('net_margin_pct', 'n/a')}%"),
        ("ROE", f"{ratios.get('roe_pct', 'n/a')}%"),
        ("ROIC", f"{ratios.get('roic_pct', 'n/a')}%"),
        ("Debt/Equity", ratios.get("debt_to_equity", "n/a")),
        ("Current Ratio", ratios.get("current_ratio", "n/a")),
        ("Interest Coverage", ratios.get("interest_coverage", "n/a")),
        ("FCF Margin", f"{ratios.get('fcf_margin_pct', 'n/a')}%"),
    ]
    story.append(_table(metric_rows(ratio_pairs), col_widths=[2.6 * inch, 1.6 * inch]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Key Metrics", styles["Heading2"]))
    key_pairs = [
        ("Current Price", market.get("price", "n/a")),
        ("Market Cap ($B)", market.get("market_cap_bn", "n/a")),
        ("Analyst Rating", market.get("analyst_rating", "n/a")),
        ("Target Price", market.get("target_price", "n/a")),
        ("P/E", market.get("pe_ratio", "n/a")),
        ("EV/EBITDA", market.get("ev_ebitda", "n/a")),
    ]
    story.append(_table(metric_rows(key_pairs), col_widths=[2.6 * inch, 1.6 * inch]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Financial History ($M)", styles["Heading2"]))
    hist = [["Year", "Revenue", "EBITDA", "Net Income", "EPS"]]
    for i, year in enumerate(processed["years"]):
        def cell(v, spec: str = ",.0f") -> str:
            return f"{v:{spec}}" if v is not None else "n/a"
        hist.append(
            [
                str(year),
                cell(processed["revenue"][i]),
                cell(processed["ebitda"][i]),
                cell(processed["net_income"][i]),
                cell(processed["eps"][i], ".2f"),
            ]
        )
    story.append(_table(hist, col_widths=[0.9 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 0.8 * inch]))
    story.append(Spacer(1, 10))

    if valuation:
        story.append(Paragraph("Quantitative Valuation", styles["Heading2"]))
        dcf = valuation.get("dcf") or {}
        comp = valuation.get("comparable") or {}
        rng = valuation.get("range") or {}
        val_rows = [["Method", "Value per Share"]]
        if dcf.get("value_per_share") is not None:
            val_rows.append([f"DCF (WACC {dcf.get('wacc', 0.09) * 100:.0f}%, g {dcf.get('terminal_growth', 0.025) * 100:.1f}%)", f"${dcf['value_per_share']:.2f}"])
        if comp.get("value_per_share") is not None:
            val_rows.append([f"Comparable EV/EBITDA (median {comp.get('median_multiple', 0):.1f}x)", f"${comp['value_per_share']:.2f}"])
        if rng.get("low") is not None:
            val_rows.append(["Combined range", f"${rng['low']:.2f} - ${rng['high']:.2f}"])
        story.append(_table(val_rows, col_widths=[2.8 * inch, 1.4 * inch]))
        story.append(Spacer(1, 10))

    section_titles = {
        "company_overview": "Company Overview",
        "financial_health": "Financial Health",
        "valuation_analysis": "Valuation Analysis",
        "competitor_analysis": "Competitor Analysis",
        "news_summary": "News & Sentiment",
        "catalyst_analysis": "Catalyst Analysis",
        "risks": "Risk Analysis",
        "takeaways": "Investment Takeaways",
    }
    for key, title in section_titles.items():
        content = sections.get(key)
        if not content:
            continue
        story.append(Paragraph(title, styles["Heading2"]))
        for field, value in content.items():
            if isinstance(value, list) and value:
                story.append(Paragraph(field.replace("_", " ").title(), styles["Heading3"]))
                for item in value:
                    story.append(Paragraph(f"• {item}", bullet))
            elif isinstance(value, str) and value:
                story.append(Paragraph(value, body))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "This report is generated for demonstration purposes. Not investment advice.",
        small,
    ))
    doc.build(story)
    return str(output_path)
