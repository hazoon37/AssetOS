from __future__ import annotations

from services.asset_resolver import AssetResolution, ResolvedAsset
from services.smart_import_service import (
    SmartImportResolution,
    apply_preview_edits,
    apply_resolution_candidate,
    build_import_error_report,
    build_resolution_table,
    candidate_label,
    detect_account_keyword,
    display_asset_name,
    enrich_import_row,
    finalize_import_rows,
    resolution_summary,
)


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "asset_name": "Apple",
        "quantity": 2.0,
        "asset_type": "미국주식",
        "symbol": "",
        "average_price": 0.0,
        "current_price": 0.0,
        "currency": "",
        "country": "",
        "exchange": "",
        "sector": "",
        "tags": "",
        "data_source": "",
        "_average_price_missing": True,
    }
    row.update(overrides)
    return row


def test_resolves_name_fetches_price_and_calculates_value() -> None:
    result = enrich_import_row(
        _base_row(),
        price_lookup=lambda asset_type, ticker, currency: 210.0,
    )
    assert result.status == "resolved"
    assert result.row["symbol"] == "AAPL"
    assert result.row["current_price"] == 210.0
    assert result.current_value == 420.0
    assert result.profit_available is False
    assert result.row["average_price"] == 0.0
    assert "COST_BASIS_UNKNOWN" in result.row["tags"]
    assert result.row["data_source"] == "Smart Import"


def test_price_failure_keeps_resolver_success_as_auto() -> None:
    result = enrich_import_row(
        _base_row(),
        price_lookup=lambda asset_type, ticker, currency: None,
    )
    assert result.status == "resolved"
    assert result.row["asset_name"] == "Apple"
    assert result.row["symbol"] == "AAPL"
    assert result.row["current_price"] == 0.0
    assert "UNRESOLVED" not in result.row["tags"]
    assert result.row["data_source"] == "Smart Import"
    assert "Price unavailable" in result.warnings
    assert result.current_value == 0.0


def test_manual_values_override_resolver_and_price_lookup() -> None:
    calls: list[tuple[str, str, str]] = []
    result = enrich_import_row(
        _base_row(
            symbol="MANUAL",
            asset_type="기타",
            currency="KRW",
            country="KR",
            exchange="직접입력",
            current_price=123.0,
            average_price=100.0,
            _average_price_missing=False,
        ),
        resolver=lambda query: AssetResolution(query=query, status="unknown"),
        price_lookup=lambda *args: calls.append(args) or 999.0,
    )
    assert result.row["symbol"] == "MANUAL"
    assert result.row["current_price"] == 123.0
    assert result.current_value == 246.0
    assert result.profit_available is True
    assert calls == []


def test_supplied_ticker_is_resolved_before_asset_name() -> None:
    queries: list[str] = []
    apple = ResolvedAsset(
        "AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple"
    )
    result = enrich_import_row(
        _base_row(asset_name="Wrong Name", symbol="aapl"),
        resolver=lambda query: queries.append(query) or AssetResolution(
            query=query, status="exact", asset=apple
        ),
        price_lookup=lambda *_args: 210.0,
    )
    assert queries == ["aapl"]
    assert result.row["symbol"] == "AAPL"
    assert result.status == "resolved"


def test_changed_ticker_always_refreshes_source_price() -> None:
    calls: list[tuple[str, str, str]] = []
    apple = ResolvedAsset(
        "AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple"
    )
    result = enrich_import_row(
        _base_row(symbol="INVALID", current_price=99_999.0, currency="KRW"),
        resolver=lambda query: AssetResolution(query, "exact", asset=apple),
        price_lookup=lambda *args: calls.append(args) or 210.0,
    )
    assert result.row["symbol"] == "AAPL"
    assert result.row["currency"] == "USD"
    assert result.row["current_price"] == 210.0
    assert calls == [("미국주식", "AAPL", "USD")]


def test_crypto_keeps_requested_quote_currency() -> None:
    bitcoin = ResolvedAsset(
        "BTC", "CoinGecko", "USD", "GLOBAL", "코인", "Cryptocurrency", "Bitcoin"
    )
    calls: list[tuple[str, str, str]] = []
    result = enrich_import_row(
        _base_row(asset_name="비트코인", asset_type="코인", currency="KRW"),
        resolver=lambda query: AssetResolution(query, "exact", asset=bitcoin),
        price_lookup=lambda *args: calls.append(args) or 100_000_000.0,
    )
    assert result.row["currency"] == "KRW"
    assert result.row["current_price"] == 100_000_000.0
    assert calls == [("코인", "BTC", "KRW")]


def test_invalid_supplied_ticker_is_failed_for_market_asset() -> None:
    result = enrich_import_row(
        _base_row(symbol="NOT-A-TICKER", asset_type="미국주식", current_price=100),
        resolver=lambda query: AssetResolution(query=query, status="unknown"),
    )
    assert result.status == "unresolved"
    assert any("입력한 티커" in warning for warning in result.warnings)


def test_invalid_supplied_ticker_retries_asset_name() -> None:
    queries: list[str] = []
    apple = ResolvedAsset(
        "AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple"
    )

    def resolver(query: str) -> AssetResolution:
        queries.append(query)
        return (
            AssetResolution(query, "exact", asset=apple)
            if query == "Apple"
            else AssetResolution(query, "unknown")
        )

    result = enrich_import_row(
        _base_row(symbol="INVALID", asset_type="미국주식"),
        resolver=resolver,
        price_lookup=lambda *_args: 200.0,
    )
    assert queries == ["INVALID", "Apple"]
    assert result.status == "resolved"
    assert result.row["symbol"] == "AAPL"


def test_single_fuzzy_match_above_resolver_threshold_is_auto_filled() -> None:
    candidate = ResolvedAsset(
        "AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple"
    )
    result = enrich_import_row(
        _base_row(asset_name="Aple"),
        resolver=lambda query: AssetResolution(query=query, status="fuzzy", asset=candidate),
        price_lookup=lambda *_args: 210.0,
    )
    assert result.status == "resolved"
    assert result.row["symbol"] == "AAPL"
    assert result.candidates == ()
    assert result.matched_asset == candidate


def test_common_krx_names_stay_auto_when_price_is_unavailable() -> None:
    expected = {
        "삼성전자": "005930.KS",
        "삼성전기": "009150.KS",
        "셀트리온": "068270.KS",
        "NAVER": "035420.KS",
        "카카오": "035720.KS",
        "카카오뱅크": "323410.KS",
        "현대글로비스": "086280.KS",
        "한화오션": "042660.KS",
        "HMM": "011200.KS",
    }
    for name, ticker in expected.items():
        result = enrich_import_row(
            _base_row(asset_name=name),
            price_lookup=lambda *_args: None,
        )
        assert result.status == "resolved"
        assert result.row["symbol"] == ticker
        assert "Price unavailable" in result.warnings


def test_non_searchable_asset_is_skipped_without_resolver_or_warnings() -> None:
    calls: list[str] = []
    result = enrich_import_row(
        _base_row(asset_type="예금", asset_name="예금*농협*매직트리"),
        resolver=lambda query: calls.append(query) or AssetResolution(query, "unknown"),
    )
    assert result.status == "skipped"
    assert result.warnings == []
    assert calls == []
    assert result.row["asset_name"] == "예금*농협*매직트리"
    assert display_asset_name(result.row["asset_name"]) == "농협 매직트리"


def test_account_keywords_skip_before_resolver() -> None:
    for keyword in (
        "계좌", "예수금", "위탁", "종합매매", "CMA", "입출금",
        "외화예수금", "외화계좌", "RP", "MMF", "증거금",
    ):
        calls: list[str] = []
        result = enrich_import_row(
            _base_row(asset_name=f"테스트 {keyword} 자산", asset_type="미국주식"),
            resolver=lambda query, calls=calls: calls.append(query)
            or AssetResolution(query, "unknown"),
        )
        assert calls == []
        assert result.status == "skipped"
        assert result.row["asset_type"] == "Account"
        assert result.detected_keyword == keyword
        assert result.classification == "Account"
        assert keyword in result.reason


def test_specific_account_keyword_precedes_contained_generic_keyword() -> None:
    assert detect_account_keyword("USD 외화예수금 계좌") == "외화예수금"


def test_account_name_containing_stock_alias_never_resolves_ticker() -> None:
    calls: list[str] = []
    result = enrich_import_row(
        _base_row(
            asset_name="카카오페이*종합계좌*주식",
            asset_type="Account",
        ),
        resolver=lambda query: calls.append(query) or AssetResolution(query, "unknown"),
    )
    assert calls == []
    assert result.status == "skipped"
    assert result.row["asset_type"] == "Account"
    assert not result.row.get("symbol")


def test_unknown_name_is_retained_with_persistence_fallbacks() -> None:
    result = enrich_import_row(
        _base_row(asset_name="Unknown Asset"),
        resolver=lambda query: AssetResolution(query=query, status="unknown"),
        price_lookup=lambda asset_type, ticker, currency: None,
    )
    assert result.status == "unresolved"
    assert result.row["asset_name"] == "Unknown Asset"
    assert result.row["asset_type"] == "미국주식"
    assert result.row["currency"] == "KRW"
    assert result.row["country"] == "OTHER"


def test_ambiguous_asset_is_not_auto_selected() -> None:
    candidates = [
        ResolvedAsset("AAA", "NASDAQ", "USD", "US", "미국주식", "Technology", "Alpha A"),
        ResolvedAsset("AAB", "NYSE", "USD", "US", "미국주식", "Technology", "Alpha B"),
    ]
    result = enrich_import_row(
        _base_row(asset_name="Alpha"),
        resolver=lambda query: AssetResolution(
            query=query,
            status="ambiguous",
            candidates=candidates,
        ),
        price_lookup=lambda asset_type, ticker, currency: 100.0,
    )
    assert result.status == "unresolved"
    assert result.row["symbol"] == ""
    assert "UNRESOLVED" in result.row["tags"]
    assert tuple(candidates) == result.candidates


def test_explicit_candidate_selection_fills_metadata_and_price() -> None:
    candidate = ResolvedAsset(
        "AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple"
    )
    result = apply_resolution_candidate(
        _base_row(), candidate, price_lookup=lambda *_args: 215.0
    )
    assert result.status == "resolved"
    assert result.row["symbol"] == "AAPL"
    assert result.row["exchange"] == "NASDAQ"
    assert result.row["currency"] == "USD"
    assert result.row["country"] == "US"
    assert result.row["current_price"] == 215.0


def test_preview_edits_are_validated_and_preserve_metadata() -> None:
    resolved = _base_row(exchange="NASDAQ", sector="Technology")
    preview = {
        "Asset": "Apple Inc.", "Ticker": "AAPL", "Asset Type": "미국주식",
        "Quantity": 3, "Average Price": 190, "Current Price": 220,
        "Currency": "USD", "Exchange": "NASDAQ", "Country": "US",
        "Status": "Resolved",
    }
    result = apply_preview_edits([resolved], [preview])
    assert result.errors == []
    assert result.rows[0]["asset_name"] == "Apple Inc."
    assert result.rows[0]["quantity"] == 3.0
    assert result.rows[0]["sector"] == "Technology"


def test_preview_edits_reject_invalid_required_and_numeric_values() -> None:
    preview = {
        "Asset": "", "Ticker": "", "Asset Type": "기타",
        "Quantity": -1, "Average Price": 0, "Current Price": 0,
        "Currency": "", "Exchange": "", "Country": "",
        "Status": "Needs Review",
    }
    result = apply_preview_edits([_base_row()], [preview])
    assert len(result.errors) == 3


def test_preview_uses_original_row_number_and_status_labels() -> None:
    from services.smart_import_service import build_import_preview

    preview = build_import_preview([
        {**_base_row(_excel_row_number=7), "resolution_status": "resolved"},
        {**_base_row(_excel_row_number=9), "resolution_status": "needs_selection"},
        {**_base_row(_excel_row_number=12), "resolution_status": "unresolved"},
    ])
    assert preview["Row Number"].tolist() == [7, 9, 12]
    assert preview["Status"].tolist() == [
        "✅ Resolved", "⚠ Needs Selection", "❌ Failed"
    ]


def test_preview_errors_reference_original_excel_row() -> None:
    preview = {
        "Row Number": 11, "Asset": "", "Ticker": "", "Asset Type": "기타",
        "Quantity": -1, "Average Price": 0, "Current Price": 0,
        "Currency": "", "Exchange": "", "Country": "", "Status": "❌ Failed",
    }
    result = apply_preview_edits([_base_row(_excel_row_number=11)], [preview])
    assert result.errors
    assert all(error.startswith("11행") for error in result.errors)


def test_resolution_table_and_summary_cover_every_status() -> None:
    candidate = ResolvedAsset(
        "GOOGL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Alphabet"
    )
    sources = [
        _base_row(_excel_row_number=2, asset_name="Apple"),
        _base_row(_excel_row_number=3, asset_name="예금*농협*매직트리", asset_type="예금"),
        _base_row(_excel_row_number=4, asset_name="Alphabet"),
        _base_row(_excel_row_number=5, asset_name="Unknown"),
    ]
    results = [
        SmartImportResolution(sources[0], "resolved", 1, True, []),
        SmartImportResolution(sources[1], "skipped", 1, True, []),
        SmartImportResolution(sources[2], "unresolved", 0, True, ["후보 확인"], (candidate,)),
        SmartImportResolution(sources[3], "unresolved", 0, True, ["조회 실패"]),
    ]
    table = build_resolution_table(sources, results)
    assert len(table) == 4
    assert table.columns.tolist() == ["Row", "Type", "Asset", "Ticker", "Status"]
    assert table.loc[1, "Asset"] == "농협 매직트리"
    assert table["Status"].tolist() == [
        "🟢 Auto", "⚪ Skip", "🟡 Select", "🔴 Fail"
    ]
    assert resolution_summary(results) == {
        "Total": 4, "Auto": 1, "Select": 1, "Skip": 1, "Fail": 1,
    }


def test_error_report_keeps_original_columns_and_appends_resolution_fields() -> None:
    from io import BytesIO

    import pandas as pd

    source_dataframe = pd.DataFrame([{
        "자산명": "Alphabet", "수량": 2, "사용자열": "keep"
    }])
    source = _base_row(_excel_row_number=2, asset_name="Alphabet")
    candidate = ResolvedAsset(
        "GOOGL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Alphabet"
    )
    result = SmartImportResolution(
        source, "unresolved", 0, True, ["후보 확인"], (candidate,)
    )
    report = pd.read_excel(BytesIO(build_import_error_report(
        source_dataframe, [source], [result]
    )))
    assert report.columns.tolist() == [
        "자산명", "수량", "사용자열", "Status", "Suggested Action"
    ]
    assert report.loc[0, "사용자열"] == "keep"
    assert "GOOGL | Alphabet" in report.loc[0, "Suggested Action"]


def test_candidate_label_adds_exchange_only_for_duplicate_names() -> None:
    nyse = ResolvedAsset("BHP", "NYSE", "USD", "US", "미국주식", "Materials", "BHP Group")
    asx = ResolvedAsset("BHP.AX", "ASX", "AUD", "AU", "미국주식", "Materials", "BHP Group")
    apple = ResolvedAsset("AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple")
    assert candidate_label(apple, (apple,)) == "AAPL | Apple"
    assert candidate_label(nyse, (nyse, asx)) == "BHP | BHP Group | NYSE"
    assert candidate_label(asx, (nyse, asx)) == "BHP.AX | BHP Group | ASX"
    naver = ResolvedAsset("035420.KS", "KOSPI", "KRW", "KR", "국내주식", "Communication", "NAVER")
    assert candidate_label(naver, (naver,)) == "035420 | NAVER"


def test_single_table_results_are_finalized_for_existing_import_service() -> None:
    source = _base_row(_excel_row_number=8, symbol="AAPL")
    result = SmartImportResolution(source, "resolved", 100, True, [])
    rows = finalize_import_rows([result])
    assert rows[0]["symbol"] == "AAPL"
    assert "_excel_row_number" not in rows[0]


def test_ticker_edits_use_session_state_without_forced_navigation_rerun() -> None:
    import inspect

    from components.asset_management.import_candidate_picker import (
        render_candidate_pickers,
    )

    source = inspect.getsource(render_candidate_pickers)
    assert "st.session_state[selection_key]" in source
    assert "st.session_state[manual_key]" in source


def test_picker_keeps_manual_input_as_last_dropdown_option() -> None:
    import inspect

    from components.asset_management.import_candidate_picker import (
        render_candidate_pickers,
    )

    source = inspect.getsource(render_candidate_pickers)
    assert "Ticker candidates" in source
    assert "options=build_ticker_dropdown_options(candidates)" in source
    assert "Manual input" in source
    assert source.index("Ticker candidates") < source.index("Manual input")
    assert "st.rerun(" not in source


def test_candidate_dropdown_keeps_every_candidate_before_manual_option() -> None:
    import pickle

    from components.asset_management.import_candidate_picker import (
        build_ticker_dropdown_options,
    )

    candidates = (
        ResolvedAsset("005930.KS", "KOSPI", "KRW", "KR", "국내주식", "Technology", "삼성전자"),
        ResolvedAsset("005935.KS", "KOSPI", "KRW", "KR", "국내주식", "Technology", "삼성전자우"),
        ResolvedAsset("009150.KS", "KOSPI", "KRW", "KR", "국내주식", "Technology", "삼성전기"),
    )
    source = _base_row(asset_name="Samsung")
    resolution = enrich_import_row(
        source,
        resolver=lambda query: AssetResolution(query, "ambiguous", candidates=list(candidates)),
        price_lookup=lambda *_args: None,
    )
    restored = pickle.loads(pickle.dumps(resolution))
    options = build_ticker_dropdown_options(restored.candidates)
    assert options[-1] == "✏ 직접 입력..."
    assert options[1:-1] == list(candidates)
