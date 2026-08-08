# AssetOS v1.0

AssetOS는 주식·ETF·코인·현금·부동산을 계정별로 관리하고 대시보드와
포트폴리오 분석을 제공하는 Streamlit 자산관리 애플리케이션입니다.

## v1.0 기능

- 3-page UX: 총 자산 현황, 포트폴리오 분석, 종목 분석
- 4/2/1열 반응형 KPI, 계정 필터와 자산유형·국가·통화·섹터·계정 배분
- AssetOS 템플릿 및 일반 Excel Smart Import
- 자동 열 매핑, Asset Master/외부 Resolver, 현재가 조회, 편집 가능한 검증 미리보기
- 통합 보유자산 등록·수정·삭제·검색·일괄 삭제와 Excel/JSON 내보내기
- 브라우저 로컬 사용자, 투자계정과 사용자별 환경설정 기반
- user-scoped 자산·계정·스냅샷과 향후 identity 이전 계약
- 구조화된 Portfolio Advice와 교체 가능한 AI provider 계약
- 브라우저 UUID 기반 Local User Mode와 기존 `default_user` 자동 이전
- DB에 저장하지 않는 Excel Quick Analysis 및 PDF·PNG·JSON export
- Quick Analysis 결과의 선택적·확인 기반 AssetOS 계정 저장
- Dashboard 현재 필터 범위의 PDF·PNG·JSON 직접 다운로드
- KRW·USD·JPY·EUR·GBP·HKD 기준통화 표시
- System·Light·Dark 테마
- 검증된 SQLite 전체 백업 및 원자적 복구
- Repository Pattern과 자동 구버전 DB 마이그레이션

## 로컬 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Python 3.12를 권장합니다.

## 비밀정보

`.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사하고 필요한
키만 입력합니다. 실제 비밀 파일은 Git에서 제외됩니다.

```toml
DART_API_KEY = ""
KRX_ID = ""
KRX_PW = ""

[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "replace-with-a-random-secret"

[auth.google]
client_id = "your-google-client-id.apps.googleusercontent.com"
client_secret = "your-google-client-secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Streamlit Community Cloud에서는 앱 설정의 Secrets에 같은 키를 등록합니다.

## Streamlit Cloud

1. 저장소의 `app.py`를 entrypoint로 선택합니다.
2. `requirements.txt`와 `runtime.txt`가 자동 적용됩니다.
3. Secrets를 Cloud 설정에 등록합니다.

Google OAuth redirect, production secrets, environment variables, and post-deployment
checks are documented in [Deployment Guide](docs/DEPLOYMENT.md).

SQLite와 `data/backups`는 Community Cloud 재시작 시 영구 보존을 보장하지
않습니다. v1.0 로컬/단일 인스턴스에서는 설정의 백업 다운로드를 사용하고,
지속형 다중 인스턴스 배포는 향후 원격 Repository 구현을 사용해야 합니다.

## 데이터 마이그레이션

기존 `data/assets.db`는 시작 시 자동 마이그레이션됩니다. `default_user`,
`My Portfolio`, 환경설정과 `account_id`가 추가되고 기존 자산 값과 ID는
보존됩니다. 자세한 규칙은 [마이그레이션](docs/MIGRATION.md),
[제품 명세](docs/README.md)와 [아키텍처](ARCHITECTURE.md)를 참고하세요.
