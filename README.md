# AssetOS v0.9

주식·ETF·코인·현금·부동산을 관리하고 개별 종목과 전체 포트폴리오를 분석하는 Streamlit 기반 자산관리 앱입니다.

## 주요 기능

- 자산 등록·수정·삭제와 티커 자동입력
- 국내·미국 주식, ETF, 코인 종목분석
- OpenDART 기반 국내주식 가치평가
- 외화자산 원화 환산
- 포트폴리오 평가손익과 수익률
- 자산군·국가·통화·섹터 배분
- 현금·레버리지·인버스 노출
- HHI와 상위 보유자산 집중도

## 설치 및 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## API 키

`.streamlit/secrets.toml`에 본인의 OpenDART API 키를 입력합니다.

```toml
DART_API_KEY = "본인_API_KEY"
KRX_ID = ""
KRX_PW = ""
```

## DB 마이그레이션

기존 `data/assets.db`는 그대로 사용할 수 있습니다. 자산관리 또는 포트폴리오 페이지를 열면 신규 메타데이터 컬럼이 자동 추가되고 기존 자산은 기본 규칙으로 분류됩니다.

상세 변경 내용은 `CHANGELOG.md`, `docs/SPRINT1_PORTFOLIO.md`, `CLEANUP_REPORT.md`를 참고하세요.


## v1.1 메뉴 구조

- 대시보드: 한눈에 보는 전체 자산
- 포트폴리오: 보유자산 관리와 구성·위험·보고서 통합
- 종목분석: 개별 종목의 투자 가치 분석

## Excel 자산 DB 업데이트

1. `포트폴리오` → `보유자산` 탭으로 이동합니다.
2. `📥 Excel 자산 DB 업데이트`를 엽니다.
3. AssetOS 표준 양식의 `.xlsx` 파일을 선택합니다.
4. 미리보기와 검증 결과를 확인합니다.
5. 전체 교체 동의 항목을 체크하고 업데이트 버튼을 누릅니다.

가져오기 직전에 기존 `data/assets.db`는 `data/backups/`에 자동 백업됩니다.
Excel 파일에는 `Assets` 시트와 다음 필수 열이 있어야 합니다.

`자산종류, 자산명, 수량, 평균단가, 현재가, 통화`
