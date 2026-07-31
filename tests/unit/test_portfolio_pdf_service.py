from services.portfolio_pdf_service import build_portfolio_pdf


def test_build_portfolio_pdf_is_single_pdf_document() -> None:
    result = {
        "success": True,
        "exclude_real_estate": True,
        "summary": {
            "total_value_krw": 100_000_000,
            "profit_loss_krw": 5_000_000,
            "return_rate": 0.0526,
            "cash_weight": 0.10,
            "leveraged_weight": 0.12,
            "asset_count": 4,
        },
        "score": {"total": 78.0, "grade": "B", "label": "양호"},
        "concentration": {"top_1_weight": 0.40, "top_3_weight": 0.85, "hhi": 0.22},
        "allocations": {
            "asset_class": [
                {"label": "주식", "weight": 0.50},
                {"label": "ETF", "weight": 0.30},
                {"label": "현금", "weight": 0.20},
            ]
        },
        "assets": [
            {"name": "예시 주식", "weight": 0.40, "value_krw": 40_000_000},
            {"name": "예시 ETF", "weight": 0.30, "value_krw": 30_000_000},
        ],
        "insights": ["현금성 비중이 적정 범위에 있습니다."],
        "warnings": ["상위 자산 집중도를 정기적으로 점검하세요."],
    }

    pdf = build_portfolio_pdf(result)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 3_000
