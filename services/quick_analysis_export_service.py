from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from io import BytesIO
import json
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from services.portfolio_ai_service import PortfolioAIDiagnosis
from services.portfolio_pdf_service import build_portfolio_pdf


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(f"지원하지 않는 JSON 값입니다: {type(value).__name__}")


def export_quick_analysis_pdf(
    analysis: dict[str, Any],
    diagnosis: PortfolioAIDiagnosis | None = None,
) -> bytes:
    """Build the existing one-page report, enriched with advisor findings."""
    if diagnosis is None:
        return build_portfolio_pdf(analysis)
    report = dict(analysis)
    report["insights"] = list(dict.fromkeys(
        [*analysis.get("insights", []), *diagnosis.top_strengths,
         *diagnosis.recommended_actions, f"다음 행동: {diagnosis.next_action}"]
    ))
    report["warnings"] = list(dict.fromkeys(
        [*analysis.get("warnings", []), *diagnosis.top_risks]
    ))
    return build_portfolio_pdf(report)


def export_quick_analysis_json(
    analysis: dict[str, Any],
    diagnosis: PortfolioAIDiagnosis,
) -> bytes:
    payload = {
        "format": "AssetOS Quick Analysis",
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "analysis": analysis,
        "advisor": asdict(diagnosis),
    }
    return json.dumps(
        payload, ensure_ascii=False, indent=2, default=_json_default
    ).encode("utf-8")


def export_quick_analysis_png(
    analysis: dict[str, Any],
    diagnosis: PortfolioAIDiagnosis,
) -> bytes:
    """Render a portable summary image without browser screenshot dependencies."""
    width, height = 1400, 900
    image = Image.new("RGB", (width, height), "#F4F7FB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=24)
    title_font = ImageFont.load_default(size=38)
    value_font = ImageFont.load_default(size=32)
    draw.text((70, 55), "AssetOS Quick Portfolio Analysis", fill="#0F172A", font=title_font)
    draw.text(
        (70, 110), datetime.now().strftime("Generated %Y-%m-%d %H:%M"),
        fill="#64748B", font=font,
    )
    metrics = diagnosis.metrics
    cards = [
        ("Overall Score", f"{diagnosis.overall_score:.1f}"),
        ("Diversification", f"{metrics.diversification_score:.1f}"),
        ("Risk Management", f"{metrics.risk_score:.1f}"),
        ("Cash", f"{metrics.cash_ratio:.1%}"),
        ("US", f"{metrics.us_ratio:.1%}"),
        ("KR", f"{metrics.kr_ratio:.1%}"),
        ("ETF", f"{metrics.etf_ratio:.1%}"),
        ("Stock", f"{metrics.stock_ratio:.1%}"),
        ("Crypto", f"{metrics.crypto_ratio:.1%}"),
        ("Real Estate", f"{metrics.real_estate_ratio:.1%}"),
    ]
    card_width, card_height, gap = 238, 125, 18
    for index, (label, value) in enumerate(cards):
        row, column = divmod(index, 5)
        x = 70 + column * (card_width + gap)
        y = 175 + row * (card_height + gap)
        draw.rounded_rectangle(
            (x, y, x + card_width, y + card_height), radius=18,
            fill="#FFFFFF", outline="#E2E8F0", width=2,
        )
        draw.text((x + 18, y + 18), label, fill="#64748B", font=font)
        draw.text((x + 18, y + 58), value, fill="#0F172A", font=value_font)
    summary = analysis.get("summary", {})
    draw.text((70, 500), "Portfolio Snapshot", fill="#0F172A", font=title_font)
    snapshot_lines = [
        f"Assets: {int(summary.get('asset_count') or 0)}",
        f"Value (KRW): {float(summary.get('total_value_krw') or 0):,.0f}",
        f"Profit/Loss (KRW): {float(summary.get('profit_loss_krw') or 0):+,.0f}",
        f"Risk: {diagnosis.risk_level} | Flags: {len(diagnosis.top_risks)} | Actions: {len(diagnosis.recommended_actions)}",
    ]
    for index, line in enumerate(snapshot_lines):
        draw.text((70, 565 + index * 55), line, fill="#334155", font=font)
    recommendation = diagnosis.recommended_actions[0] if diagnosis.recommended_actions else "-"
    draw.text(
        (560, 565), f"Recommendation: {recommendation[:48]}",
        fill="#334155", font=font,
    )
    draw.text(
        (560, 625), f"Next Action: {diagnosis.next_action[:48]}",
        fill="#334155", font=font,
    )
    draw.text(
        (70, 835), "Rule-based decision support. Not investment advice.",
        fill="#64748B", font=font,
    )
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
