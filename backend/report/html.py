"""HTML 报告渲染（V1：数据表格 + 4 个分析章节，无图表）。"""

from __future__ import annotations

from html import escape


def _metric_row(label: str, value) -> str:
    return f"<tr><td>{escape(label)}</td><td>{escape(str(value))}</td></tr>"


def render_html(
    processed: dict, sections: dict, failures: list[str], valuation: dict | None = None
) -> str:
    p = processed
    market = p["market"]
    ratios = p.get("ratios", {})

    # 财务历史表
    rows = ""
    for i, year in enumerate(p["years"]):
        rows += (
            f"<tr><td>{year}</td><td>{p['revenue'][i]:,.0f}</td>"
            f"<td>{p['ebitda'][i]:,.0f}</td><td>{p['net_income'][i]:,.0f}</td>"
            f"<td>{p['eps'][i]:.2f}</td></tr>"
        )

    def section(title: str, body: str, content: dict) -> str:
        lists = ""
        for field in ("key_strengths", "key_challenges", "risks", "key_catalysts", "watch_indicators"):
            items = content.get(field)
            if items:
                lis = "".join(f"<li>{escape(str(i))}</li>" for i in items)
                lists += f"<h4>{field.replace('_', ' ').title()}</h4><ul>{lis}</ul>"
        return f"<section><h2>{escape(title)}</h2><p>{escape(body)}</p>{lists}</section>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Financial Analysis Report - {escape(p['ticker'])}</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px auto; max-width: 900px; color: #222; }}
h1 {{ border-bottom: 3px solid #1f6feb; padding-bottom: 8px; }}
h2 {{ color: #1f6feb; margin-top: 32px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: right; }}
th {{ background: #f5f7fa; }}
.meta {{ color: #666; font-size: 0.9em; }}
.warn {{ background: #fff7e6; border-left: 4px solid #fa8c16; padding: 8px 12px; margin: 12px 0; }}
.disclaimer {{ margin-top: 40px; font-size: 0.8em; color: #999; border-top: 1px solid #eee; padding-top: 12px; }}
</style>
</head>
<body>
<h1>{escape(p['company_name'])} ({escape(p['ticker'])})</h1>
<p class="meta">Data as of {escape(p['as_of'])} · Latest fiscal year {p['latest_year']} · Source: {escape(p.get('as_of', '')) and 'mock'}</p>
"""

    if failures:
        html += '<div class="warn">Warning: ' + escape("; ".join(failures)) + "</div>"

    ratio_rows = ""
    ratio_items = [
        ("Gross Margin", f"{ratios['gross_margin_pct']:.1f}%" if ratios.get("gross_margin_pct") is not None else "n/a"),
        ("Net Margin", f"{ratios['net_margin_pct']:.1f}%" if ratios.get("net_margin_pct") is not None else "n/a"),
        ("ROE", f"{ratios['roe_pct']:.1f}%" if ratios.get("roe_pct") is not None else "n/a"),
        ("ROIC", f"{ratios['roic_pct']:.1f}%" if ratios.get("roic_pct") is not None else "n/a"),
        ("Debt/Equity", ratios.get("debt_to_equity") if ratios.get("debt_to_equity") is not None else "n/a"),
        ("Debt/Assets", f"{ratios['debt_to_assets_pct']:.1f}%" if ratios.get("debt_to_assets_pct") is not None else "n/a"),
        ("Current Ratio", ratios.get("current_ratio") if ratios.get("current_ratio") is not None else "n/a"),
        ("Interest Coverage", ratios.get("interest_coverage") if ratios.get("interest_coverage") is not None else "n/a"),
        ("FCF Margin", f"{ratios['fcf_margin_pct']:.1f}%" if ratios.get("fcf_margin_pct") is not None else "n/a"),
        ("Net Debt ($M)", ratios.get("net_debt") if ratios.get("net_debt") is not None else "n/a"),
    ]
    for label, value in ratio_items:
        ratio_rows += _metric_row(label, value)

    html += f"""
<h2>Financial Ratios</h2>
<table>
<tr><th>Ratio</th><th>Value</th></tr>
{ratio_rows}
</table>

<h2>Key Metrics</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{_metric_row("Current Price", market.get("price"))}
{_metric_row("Market Cap ($B)", market.get("market_cap_bn"))}
{_metric_row("Analyst Rating", market.get("analyst_rating"))}
{_metric_row("Target Price", market.get("target_price"))}
{_metric_row("P/E", market.get("pe_ratio"))}
{_metric_row("EV/EBITDA", market.get("ev_ebitda"))}
{_metric_row("Revenue Growth (YoY, %)", f"{p['revenue_growth_pct']:.1f}" if p['revenue_growth_pct'] is not None else "n/a")}
{_metric_row("Net Margin (%)", f"{p['net_margin_pct']:.1f}" if p['net_margin_pct'] is not None else "n/a")}
{_metric_row("1Y Revenue Forecast", f"{p['forecast_revenue_1y']:,.0f}" if p['forecast_revenue_1y'] else "n/a")}
</table>

<h2>Financial History</h2>
<table>
<tr><th>Year</th><th>Revenue</th><th>EBITDA</th><th>Net Income</th><th>EPS</th></tr>
{rows}
</table>
"""

    if valuation:
        dcf = valuation.get("dcf") or {}
        comp = valuation.get("comparable") or {}
        rng = valuation.get("range") or {}
        sens = valuation.get("sensitivity") or []

        valuation_rows = ""
        if dcf.get("value_per_share") is not None:
            valuation_rows += _metric_row(
                "DCF (WACC "
                f"{dcf.get('wacc', 0.09) * 100:.0f}%, terminal g {dcf.get('terminal_growth', 0.025) * 100:.1f}%)",
                f"${dcf['value_per_share']:.2f}",
            )
        if comp.get("value_per_share") is not None:
            valuation_rows += _metric_row(
                f"Comparable EV/EBITDA (median {comp.get('median_multiple', 0):.1f}x)",
                f"${comp['value_per_share']:.2f}",
            )
        if rng.get("low") is not None:
            valuation_rows += _metric_row(
                "Combined fair value range",
                f"${rng['low']:.2f} - ${rng['high']:.2f} (mid ${rng['mid']:.2f})",
            )

        sens_html = ""
        if sens:
            header = "".join(f"<th>{escape(k.replace('g=', 'g '))}</th>" for k in sens[0] if k != "wacc")
            rows_html = ""
            for row in sens:
                cells = "".join(
                    f"<td>${v:.2f}</td>" if v is not None else "<td>n/a</td>"
                    for k, v in row.items()
                    if k != "wacc"
                )
                rows_html += f"<tr><td>{escape(row['wacc'])}</td>{cells}</tr>"
            sens_html = (
                "<h4>DCF Sensitivity (WACC × terminal growth)</h4>"
                f"<table><tr><th>WACC \\ g</th>{header}</tr>{rows_html}</table>"
            )

        html += f"""
<h2>Quantitative Valuation</h2>
<table>
<tr><th>Method</th><th>Value per Share</th></tr>
{valuation_rows}
</table>
{sens_html}
"""

    section_titles = {
        "company_overview": "Company Overview",
        "valuation_analysis": "Valuation Analysis",
        "risks": "Risk Analysis",
        "takeaways": "Investment Takeaways",
    }
    for key, title in section_titles.items():
        if key in sections:
            content = sections[key]
            if key == "company_overview":
                body = content.get("overview", "")
            elif key == "valuation_analysis":
                body = content.get("valuation_assessment", "")
            elif key == "risks":
                body = f"Risk rating: {content.get('risk_rating', 'n/a')}. {content.get('risk_mitigation', '')}"
            elif key == "takeaways":
                thesis = content.get("investment_thesis", "")
                conclusion = content.get("conclusion", "")
                body = f"{thesis}\n\nConclusion: {conclusion}"
            else:
                body = ""
            html += section(title, body, content)

    html += '<p class="disclaimer">This report is generated for demonstration purposes using mock data. Not investment advice.</p>'
    html += "</body></html>"
    return html
