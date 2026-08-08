from __future__ import annotations

import io
import zipfile
from datetime import datetime
from typing import Any
from xml.etree import ElementTree

import pandas as pd
import requests
import streamlit as st

DART_API_BASE_URL = "https://opendart.fss.or.kr/api"

REPORT_CODES = {
    "사업보고서": "11011",
    "반기보고서": "11012",
    "1분기보고서": "11013",
    "3분기보고서": "11014",
}

FINANCIAL_ACCOUNT_NAMES = {
    "매출액": [
        "매출액",
        "수익(매출액)",
        "영업수익",
        "매출",
    ],
    "영업이익": [
        "영업이익",
        "영업이익(손실)",
        "영업손익",
    ],
    "당기순이익": [
        "당기순이익",
        "당기순이익(손실)",
        "연결당기순이익",
        "분기순이익",
        "반기순이익",
    ],
    "자산총계": [
        "자산총계",
    ],
    "부채총계": [
        "부채총계",
    ],
    "자본총계": [
        "자본총계",
    ],
}


def get_dart_api_key() -> str:
    """Streamlit secrets에서 OpenDART 인증키를 읽습니다."""

    try:
        api_key = str(
            st.secrets["DART_API_KEY"]
        ).strip()

    except (KeyError, FileNotFoundError):
        return ""

    return api_key


def make_failure_result(
    message: str,
) -> dict[str, Any]:
    """공통 실패 결과입니다."""

    return {
        "success": False,
        "message": message,
        "data": None,
    }


def parse_amount(
    value: Any,
) -> float | None:
    """DART 금액 문자열을 숫자로 변환합니다."""

    if value is None:
        return None

    text = str(value).strip()

    if not text or text == "-":
        return None

    text = text.replace(",", "")

    # 괄호 형식 음수 처리: (1,000) → -1000
    if (
        text.startswith("(")
        and text.endswith(")")
    ):
        text = f"-{text[1:-1]}"

    try:
        return float(text)

    except ValueError:
        return None


@st.cache_data(
    ttl=24 * 60 * 60,
    show_spinner=False,
)
def download_corporation_codes(
    api_key: str,
) -> pd.DataFrame:
    """
    OpenDART 고유번호 ZIP/XML을 내려받아
    종목코드와 corp_code 목록을 생성합니다.
    """

    response = requests.get(
        f"{DART_API_BASE_URL}/corpCode.xml",
        params={
            "crtfc_key": api_key,
        },
        timeout=30,
    )

    response.raise_for_status()

    with zipfile.ZipFile(
        io.BytesIO(response.content)
    ) as zip_file:

        xml_filename = zip_file.namelist()[0]

        xml_content = zip_file.read(
            xml_filename
        )

    root = ElementTree.fromstring(
        xml_content
    )

    rows: list[dict[str, str]] = []

    for item in root.findall("list"):

        corp_code = (
            item.findtext("corp_code")
            or ""
        ).strip()

        corp_name = (
            item.findtext("corp_name")
            or ""
        ).strip()

        stock_code = (
            item.findtext("stock_code")
            or ""
        ).strip()

        modify_date = (
            item.findtext("modify_date")
            or ""
        ).strip()

        if not corp_code:
            continue

        rows.append(
            {
                "corp_code": corp_code,
                "corp_name": corp_name,
                "stock_code": stock_code,
                "modify_date": modify_date,
            }
        )

    return pd.DataFrame(rows)


def find_corporation_by_stock_code(
    stock_code: str,
) -> dict[str, Any]:
    """6자리 종목코드로 DART 고유번호를 찾습니다."""

    api_key = get_dart_api_key()

    if not api_key:

        return make_failure_result(
            "DART_API_KEY가 설정되지 않았습니다."
        )

    normalized_code = (
        stock_code.strip()
        .replace(".KS", "")
        .replace(".KQ", "")
    )

    if not (
        normalized_code.isdigit()
        and len(normalized_code) == 6
    ):

        return make_failure_result(
            "국내주식 종목코드는 6자리 숫자로 입력해 주세요."
        )

    try:
        corporations_df = (
            download_corporation_codes(
                api_key
            )
        )

    except (
        requests.RequestException,
        zipfile.BadZipFile,
        ElementTree.ParseError,
        IndexError,
    ) as error:

        return make_failure_result(
            "DART 고유번호 목록을 불러오지 못했습니다. "
            f"오류: {error}"
        )

    matched_df = corporations_df[
        corporations_df["stock_code"]
        == normalized_code
    ]

    if matched_df.empty:

        return make_failure_result(
            "해당 종목코드와 일치하는 DART 기업을 찾지 못했습니다."
        )

    row = matched_df.iloc[0]

    return {
        "success": True,
        "message": "",
        "data": {
            "corp_code": str(
                row["corp_code"]
            ),
            "corp_name": str(
                row["corp_name"]
            ),
            "stock_code": str(
                row["stock_code"]
            ),
            "modify_date": str(
                row["modify_date"]
            ),
        },
    }


@st.cache_data(
    ttl=60 * 60,
    show_spinner=False,
)
def get_company_overview(
    corp_code: str,
) -> dict[str, Any]:
    """OpenDART 기업개황을 조회합니다."""

    api_key = get_dart_api_key()

    if not api_key:

        return make_failure_result(
            "DART_API_KEY가 설정되지 않았습니다."
        )

    try:
        response = requests.get(
            f"{DART_API_BASE_URL}/company.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
            },
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as error:

        return make_failure_result(
            "DART 기업개황 조회에 실패했습니다. "
            f"오류: {error}"
        )

    if data.get("status") != "000":

        return make_failure_result(
            "DART 기업개황 조회 실패: "
            f"{data.get('message', '알 수 없는 오류')}"
        )

    return {
        "success": True,
        "message": "",
        "data": data,
    }


@st.cache_data(
    ttl=60 * 60,
    show_spinner=False,
)
def get_major_financial_accounts(
    corp_code: str,
    business_year: int,
    report_code: str = "11011",
) -> dict[str, Any]:
    """단일회사 주요 재무계정을 조회합니다."""

    api_key = get_dart_api_key()

    if not api_key:

        return make_failure_result(
            "DART_API_KEY가 설정되지 않았습니다."
        )

    try:
        response = requests.get(
            f"{DART_API_BASE_URL}/fnlttSinglAcnt.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": str(
                    business_year
                ),
                "reprt_code": report_code,
            },
            timeout=20,
        )

        response.raise_for_status()
        data = response.json()

    except (
        requests.RequestException,
        ValueError,
    ) as error:

        return make_failure_result(
            "DART 재무정보 조회에 실패했습니다. "
            f"오류: {error}"
        )

    if data.get("status") != "000":

        return make_failure_result(
            "DART 재무정보 조회 실패: "
            f"{data.get('message', '알 수 없는 오류')}"
        )

    accounts = data.get(
        "list",
        [],
    )

    if not isinstance(accounts, list):

        accounts = []

    return {
        "success": True,
        "message": "",
        "data": accounts,
    }


def choose_preferred_statement(
    accounts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    연결재무제표(CFS)가 있으면 우선 사용하고,
    없으면 별도재무제표(OFS)를 사용합니다.
    """

    cfs_accounts = [
        account
        for account in accounts
        if account.get("fs_div") == "CFS"
    ]

    if cfs_accounts:
        return cfs_accounts

    return [
        account
        for account in accounts
        if account.get("fs_div") == "OFS"
    ]


def find_account_value(
    accounts: list[dict[str, Any]],
    candidate_names: list[str],
) -> dict[str, Any] | None:
    """후보 계정명과 일치하는 재무계정을 찾습니다."""

    for candidate_name in candidate_names:

        for account in accounts:

            account_name = str(
                account.get(
                    "account_nm",
                    "",
                )
            ).strip()

            if account_name == candidate_name:

                return {
                    "account_name": account_name,
                    "current_amount": parse_amount(
                        account.get(
                            "thstrm_amount"
                        )
                    ),
                    "previous_amount": parse_amount(
                        account.get(
                            "frmtrm_amount"
                        )
                    ),
                    "current_name": account.get(
                        "thstrm_nm"
                    ),
                    "previous_name": account.get(
                        "frmtrm_nm"
                    ),
                    "statement_type": account.get(
                        "fs_nm"
                    ),
                }

    # 정확히 일치하지 않을 때 부분 포함 검색
    for candidate_name in candidate_names:

        for account in accounts:

            account_name = str(
                account.get(
                    "account_nm",
                    "",
                )
            ).strip()

            if candidate_name in account_name:

                return {
                    "account_name": account_name,
                    "current_amount": parse_amount(
                        account.get(
                            "thstrm_amount"
                        )
                    ),
                    "previous_amount": parse_amount(
                        account.get(
                            "frmtrm_amount"
                        )
                    ),
                    "current_name": account.get(
                        "thstrm_nm"
                    ),
                    "previous_name": account.get(
                        "frmtrm_nm"
                    ),
                    "statement_type": account.get(
                        "fs_nm"
                    ),
                }

    return None


def summarize_financial_accounts(
    accounts: list[dict[str, Any]],
) -> dict[str, Any]:
    """주요 계정을 AssetOS 공통 형식으로 정리합니다."""

    preferred_accounts = (
        choose_preferred_statement(
            accounts
        )
    )

    summary: dict[str, Any] = {}

    for label, candidate_names in (
        FINANCIAL_ACCOUNT_NAMES.items()
    ):

        summary[label] = find_account_value(
            accounts=preferred_accounts,
            candidate_names=candidate_names,
        )

    return summary


def get_latest_annual_financials(
    corp_code: str,
    start_year: int | None = None,
) -> dict[str, Any]:
    """
    최근 사업보고서가 존재하는 연도를 찾아
    주요 재무계정을 반환합니다.
    """

    if start_year is None:
        start_year = (
            datetime.now().astimezone().year - 1
        )

    attempted_years: list[int] = []

    for business_year in range(
        start_year,
        start_year - 5,
        -1,
    ):

        attempted_years.append(
            business_year
        )

        result = get_major_financial_accounts(
            corp_code=corp_code,
            business_year=business_year,
            report_code="11011",
        )

        if result.get("success"):

            accounts = result.get(
                "data",
                [],
            )

            return {
                "success": True,
                "message": "",
                "business_year": business_year,
                "report_code": "11011",
                "report_name": "사업보고서",
                "accounts": accounts,
                "summary": (
                    summarize_financial_accounts(
                        accounts
                    )
                ),
            }

    return {
        "success": False,
        "message": (
            "최근 5개 사업연도에서 사업보고서 "
            "재무정보를 찾지 못했습니다."
        ),
        "attempted_years": attempted_years,
        "business_year": None,
        "accounts": [],
        "summary": {},
    }


def get_dart_company_data(
    stock_code: str,
) -> dict[str, Any]:
    """종목코드 기준 DART 기업·재무정보 통합 조회입니다."""

    corporation_result = (
        find_corporation_by_stock_code(
            stock_code
        )
    )

    if not corporation_result.get(
        "success"
    ):

        return {
            "success": False,
            "message": corporation_result[
                "message"
            ],
        }

    corporation = corporation_result[
        "data"
    ]

    corp_code = corporation[
        "corp_code"
    ]

    overview_result = get_company_overview(
        corp_code
    )

    financial_result = (
        get_latest_annual_financials(
            corp_code
        )
    )

    return {
        "success": True,
        "message": "",
        "corporation": corporation,
        "overview": (
            overview_result.get("data")
            if overview_result.get("success")
            else None
        ),
        "overview_error": (
            None
            if overview_result.get("success")
            else overview_result.get(
                "message"
            )
        ),
        "financials": financial_result,
    }
