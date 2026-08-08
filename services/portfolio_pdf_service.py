from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas

PAGE_WIDTH, PAGE_HEIGHT = A4
FONT_REGULAR = "HYGothic-Medium"
FONT_BOLD = "HYGothic-Medium"

PALETTE = [
    "#2563EB",
    "#16A34A",
    "#F59E0B",
    "#7C3AED",
    "#0EA5E9",
    "#94A3B8",
    "#DC2626",
]


def _register_fonts() -> None:
    try:
        pdfmetrics.getFont(FONT_REGULAR)
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_REGULAR))


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _format_krw(value: Any) -> str:
    amount = _number(value)
    sign = "-" if amount < 0 else ""
    return f"{sign}{abs(amount):,.0f}원"


def _format_rate(value: Any) -> str:
    if value is None:
        return "정보 없음"
    return f"{_number(value) * 100:+.1f}%"


def _truncate(text: Any, limit: int) -> str:
    value = str(text or "-")
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _fit_text(text: str, font_name: str, max_size: float, max_width: float) -> float:
    size = max_size
    while size > 6.5 and pdfmetrics.stringWidth(text, font_name, size) > max_width:
        size -= 0.5
    return size


def _wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return []
    lines: list[str] = []
    current = ""
    for char in normalized:
        candidate = current + char
        if current and pdfmetrics.stringWidth(candidate, font_name, font_size) > max_width:
            lines.append(current.strip())
            current = char
        else:
            current = candidate
    if current.strip():
        lines.append(current.strip())
    return lines


def _draw_card(c: canvas.Canvas, x: float, y: float, width: float, height: float) -> None:
    c.setFillColor(HexColor("#FFFFFF"))
    c.setStrokeColor(HexColor("#DCE4EF"))
    c.setLineWidth(0.75)
    c.roundRect(x, y, width, height, 9, stroke=1, fill=1)


def _draw_kpi(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    value: str,
    note: str = "",
    value_color: str = "#0F172A",
) -> None:
    _draw_card(c, x, y, width, height)
    c.setFillColor(HexColor("#64748B"))
    c.setFont(FONT_REGULAR, 7.2)
    c.drawString(x + 10, y + height - 15, label)
    value_size = _fit_text(value, FONT_BOLD, 12.5, width - 20)
    c.setFillColor(HexColor(value_color))
    c.setFont(FONT_BOLD, value_size)
    c.drawString(x + 10, y + 18, value)
    if note:
        c.setFillColor(HexColor("#64748B"))
        c.setFont(FONT_REGULAR, 6.4)
        c.drawRightString(x + width - 10, y + 8, note)


def _draw_donut(
    c: canvas.Canvas,
    center_x: float,
    center_y: float,
    radius: float,
    rows: list[dict[str, Any]],
    total_value: float,
) -> None:
    top_rows = rows[:5]
    other_weight = max(0.0, 1.0 - sum(_number(row.get("weight")) for row in top_rows))
    if other_weight > 0.005:
        top_rows = top_rows + [{"label": "기타", "weight": other_weight}]

    start_angle = 90.0
    for index, row in enumerate(top_rows):
        weight = max(0.0, _number(row.get("weight")))
        extent = -360.0 * weight
        c.setFillColor(HexColor(PALETTE[index % len(PALETTE)]))
        c.setStrokeColor(HexColor("#FFFFFF"))
        c.wedge(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            start_angle,
            extent,
            stroke=1,
            fill=1,
        )
        start_angle += extent

    c.setFillColor(HexColor("#FFFFFF"))
    inner = radius * 0.58
    c.circle(center_x, center_y, inner, stroke=0, fill=1)
    c.setFillColor(HexColor("#64748B"))
    c.setFont(FONT_REGULAR, 6.8)
    c.drawCentredString(center_x, center_y + 5, "총 평가금액")
    center_value = _format_krw(total_value)
    size = _fit_text(center_value, FONT_BOLD, 9.5, inner * 1.65)
    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, size)
    c.drawCentredString(center_x, center_y - 8, center_value)

    legend_x = center_x + radius + 12
    legend_y = center_y + radius - 6
    for index, row in enumerate(top_rows):
        label = _truncate(row.get("label") or row.get("code") or "미분류", 12)
        weight = _number(row.get("weight"))
        c.setFillColor(HexColor(PALETTE[index % len(PALETTE)]))
        c.roundRect(legend_x, legend_y - 5, 7, 7, 2, stroke=0, fill=1)
        c.setFillColor(HexColor("#334155"))
        c.setFont(FONT_REGULAR, 7.0)
        c.drawString(legend_x + 11, legend_y - 4, f"{label}  {weight * 100:.1f}%")
        legend_y -= 16


def _draw_top_holdings(
    c: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    assets: list[dict[str, Any]],
) -> None:
    rows = assets[:5]
    if not rows:
        c.setFillColor(HexColor("#64748B"))
        c.setFont(FONT_REGULAR, 7.5)
        c.drawString(x, y + height - 15, "표시할 보유자산이 없습니다.")
        return

    max_weight = max((_number(row.get("weight")) for row in rows), default=1.0)
    row_height = height / max(len(rows), 1)
    for index, row in enumerate(rows):
        row_y = y + height - (index + 1) * row_height
        name = _truncate(row.get("name") or row.get("symbol") or "-", 22)
        weight = _number(row.get("weight"))
        value = _number(row.get("value_krw"))
        c.setFillColor(HexColor("#334155"))
        c.setFont(FONT_REGULAR, 7.4)
        c.drawString(x, row_y + row_height - 9, f"{index + 1}. {name}")
        c.setFillColor(HexColor("#64748B"))
        c.setFont(FONT_REGULAR, 6.5)
        c.drawRightString(x + width, row_y + row_height - 9, f"{weight * 100:.1f}% · {_format_krw(value)}")
        bar_y = row_y + 6
        c.setFillColor(HexColor("#E8EEF7"))
        c.roundRect(x, bar_y, width, 5, 2.5, stroke=0, fill=1)
        c.setFillColor(HexColor(PALETTE[index % len(PALETTE)]))
        bar_width = width * (weight / max_weight if max_weight > 0 else 0)
        c.roundRect(x, bar_y, max(bar_width, 2), 5, 2.5, stroke=0, fill=1)


def _draw_bullets(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    width: float,
    items: list[str],
    max_items: int,
    bullet_color: str,
) -> float:
    cursor_y = y_top
    for item in items[:max_items]:
        lines = _wrap_text(str(item), FONT_REGULAR, 7.2, width - 14)
        if not lines:
            continue
        c.setFillColor(HexColor(bullet_color))
        c.circle(x + 3, cursor_y - 3, 1.8, stroke=0, fill=1)
        c.setFillColor(HexColor("#334155"))
        c.setFont(FONT_REGULAR, 7.2)
        for line_index, line in enumerate(lines[:2]):
            c.drawString(x + 10, cursor_y - line_index * 9, line)
        cursor_y -= 11 + max(0, len(lines[:2]) - 1) * 9
    return cursor_y


def build_portfolio_pdf(result: dict[str, Any]) -> bytes:
    """Build a compact one-page A4 portrait portfolio PDF."""

    if not result.get("success"):
        raise ValueError(result.get("message") or "포트폴리오 분석 결과가 없습니다.")

    _register_fonts()
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=A4, pageCompression=1)
    c.setTitle("AssetOS Portfolio Report")
    c.setAuthor("AssetOS")

    summary = result.get("summary", {})
    allocations = result.get("allocations", {})
    concentration = result.get("concentration", {})
    score = result.get("score", {})
    assets = result.get("assets", [])
    insights = [str(item) for item in result.get("insights", [])]
    warnings = [str(item) for item in result.get("warnings", [])]

    total_value = _number(summary.get("total_value_krw"))
    profit_loss = _number(summary.get("profit_loss_krw"))
    return_rate = summary.get("return_rate")
    cash_weight = _number(summary.get("cash_weight"))
    leverage_weight = _number(summary.get("leveraged_weight"))

    c.setFillColor(HexColor("#F4F7FB"))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

    margin = 24
    content_width = PAGE_WIDTH - margin * 2

    c.setFillColor(HexColor("#2563EB"))
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(margin, PAGE_HEIGHT - 25, "ASSETOS · PORTFOLIO REPORT")
    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, 18)
    c.drawString(margin, PAGE_HEIGHT - 48, "포트폴리오 한눈 요약")

    mode = "부동산 제외" if result.get("exclude_real_estate") else "전체 자산"
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    c.setFillColor(HexColor("#64748B"))
    c.setFont(FONT_REGULAR, 7.2)
    c.drawRightString(PAGE_WIDTH - margin, PAGE_HEIGHT - 25, f"분석 기준: {mode}")
    c.drawRightString(PAGE_WIDTH - margin, PAGE_HEIGHT - 39, f"생성: {generated}")

    # KPI 2 x 2
    gap = 9
    kpi_width = (content_width - gap) / 2
    kpi_height = 48
    kpi_top_y = PAGE_HEIGHT - 111
    profit_color = "#15803D" if profit_loss >= 0 else "#DC2626"
    kpis = [
        ("총 평가금액", _format_krw(total_value), f"{int(summary.get('asset_count') or 0)}개 자산", "#0F172A"),
        ("총 평가손익", _format_krw(profit_loss), _format_rate(return_rate), profit_color),
        ("현금성 비중", f"{cash_weight * 100:.1f}%", "유동성 여력", "#0F172A"),
        ("진단 점수", f"{_number(score.get('total')):.1f}점", f"{score.get('grade') or '-'}등급 · {score.get('label') or '-'}", "#2563EB"),
    ]
    for index, (label, value, note, color_value) in enumerate(kpis):
        row = index // 2
        col = index % 2
        _draw_kpi(
            c,
            margin + col * (kpi_width + gap),
            kpi_top_y - row * (kpi_height + gap),
            kpi_width,
            kpi_height,
            label,
            value,
            note,
            color_value,
        )

    # Composition and top holdings
    card_y = 356
    card_height = 255
    left_width = 265
    right_width = content_width - left_width - gap
    _draw_card(c, margin, card_y, left_width, card_height)
    _draw_card(c, margin + left_width + gap, card_y, right_width, card_height)

    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, 9.5)
    c.drawString(margin + 13, card_y + card_height - 19, "자산군 구성")
    _draw_donut(
        c,
        margin + 77,
        card_y + 121,
        57,
        allocations.get("asset_class", []),
        total_value,
    )

    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, 9.5)
    right_x = margin + left_width + gap
    c.drawString(right_x + 13, card_y + card_height - 19, "상위 보유자산")
    _draw_top_holdings(c, right_x + 13, card_y + 14, right_width - 26, card_height - 44, assets)

    # Summary / warnings
    summary_y = 94
    summary_height = 250
    left_summary_width = (content_width - gap) * 0.56
    right_summary_width = content_width - left_summary_width - gap
    _draw_card(c, margin, summary_y, left_summary_width, summary_height)
    _draw_card(c, margin + left_summary_width + gap, summary_y, right_summary_width, summary_height)

    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, 9.5)
    c.drawString(margin + 13, summary_y + summary_height - 19, "핵심 요점")
    _draw_bullets(
        c,
        margin + 13,
        summary_y + summary_height - 39,
        left_summary_width - 26,
        insights or ["현재 기본 진단 규칙에서 표시할 핵심 요점이 없습니다."],
        5,
        "#2563EB",
    )

    warning_x = margin + left_summary_width + gap
    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, 9.5)
    c.drawString(warning_x + 13, summary_y + summary_height - 19, "주요 점검사항")
    _draw_bullets(
        c,
        warning_x + 13,
        summary_y + summary_height - 39,
        right_summary_width - 26,
        warnings or ["현재 기본 진단 규칙에서 특별한 경고가 없습니다."],
        4,
        "#DC2626" if warnings else "#16A34A",
    )

    top1 = _number(concentration.get("top_1_weight"))
    top3 = _number(concentration.get("top_3_weight"))
    c.setFillColor(HexColor("#F8FAFC"))
    c.setStrokeColor(HexColor("#E2E8F0"))
    c.roundRect(warning_x + 13, summary_y + 13, right_summary_width - 26, 47, 7, stroke=1, fill=1)
    c.setFillColor(HexColor("#64748B"))
    c.setFont(FONT_REGULAR, 6.8)
    c.drawString(warning_x + 23, summary_y + 43, "구조 요약")
    c.setFillColor(HexColor("#0F172A"))
    c.setFont(FONT_BOLD, 7.3)
    structure_text = (
        f"최대 자산 {top1 * 100:.1f}% · 상위 3개 {top3 * 100:.1f}%\n"
        f"레버리지 {leverage_weight * 100:.1f}% · HHI {_number(concentration.get('hhi')):.3f}"
    )
    for line_index, line in enumerate(structure_text.splitlines()):
        c.drawString(warning_x + 23, summary_y + 28 - line_index * 11, line)

    c.setFillColor(HexColor("#64748B"))
    c.setFont(FONT_REGULAR, 6.2)
    c.drawString(
        margin,
        18,
        "본 보고서는 등록 자산과 규칙 기반 분석을 요약한 참고자료이며, 투자성과를 보장하거나 매매를 권유하지 않습니다.",
    )
    c.drawRightString(PAGE_WIDTH - margin, 18, "AssetOS")

    c.showPage()
    c.save()
    output.seek(0)
    return output.getvalue()


def build_portfolio_pdf_filename(result: dict[str, Any]) -> str:
    mode = "financial" if result.get("exclude_real_estate") else "all_assets"
    generated = datetime.now().astimezone().strftime("%Y%m%d")
    return f"AssetOS_Portfolio_{mode}_{generated}.pdf"
