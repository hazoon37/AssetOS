# v1.1.1 — 부동산 제외 보기

- 대시보드에 `전체 자산 / 부동산 제외` 선택 옵션 추가
- 포트폴리오 페이지에도 동일한 분석 기준 선택 옵션 추가
- 부동산 제외 선택 시 요약, 배분, 위험 분석, 보고서만 재계산
- 보유자산 목록과 SQLite DB 원본은 변경하지 않음

# Changelog

## AssetOS Feature Pack #1

- 세션 전용 Excel Quick Analysis와 PDF·PNG·JSON export 추가
- 브라우저 localStorage UUID 기반 Local User Mode 추가
- `default_user` 자산·계정·스냅샷·환경설정의 원자적 사용자 이전 추가
- Portfolio AI provider 출력 계약과 Rule Engine 확장
- Dashboard 최상단 AI Summary 배치
- Dashboard PDF·PNG·JSON 직접 export 추가
- Quick Analysis에 `Analyze Only`와 확인 기반 `Save into AssetOS` 분기 추가

## Sprint 5 — AI Portfolio Advisor MVP

- 총자산 상단에 `🤖 AI 포트폴리오 진단` 실행 버튼 추가
- Portfolio·분산·위험 점수와 7개 자산 배분 비율 계산
- 구조화 데이터 기반 장점·리스크·추천사항 Rule Engine 추가
- 기존 반응형 AssetOS 카드 스타일을 재사용한 진단 컴포넌트 추가

## AssetOS v1.0 RC — SaaS Foundation

- `assets.user_id` 무손실 마이그레이션과 사용자·계정 일치 trigger 추가
- 사용자별 Portfolio Snapshot Repository 추가
- local/default_user 인증 provider와 Google·Apple·GitHub 확장 계약 추가
- 사용자 ID를 포함하는 포트폴리오 캐시 및 계정별 분석 추가
- 구조화 데이터 기반 AI Advisor provider와 Dashboard AI Portfolio Summary 추가

## AssetOS v1.0 MVP

- Smart Import: 템플릿·일반 Excel 감지, 열 매핑, Resolver, 계정 선택, 편집·재검증 미리보기
- Asset Master 기반 로컬 우선 메타데이터 및 외부 provider fallback
- Repository Pattern, `default_user`, 투자계정과 자동 구버전 DB 마이그레이션
- 통합 자산관리의 등록·수정·삭제·검색·일괄 삭제와 Excel/JSON 내보내기
- 계정별 대시보드 필터, 다차원 배분과 4/2/1 반응형 KPI
- 사용자 기준통화 및 System·Light·Dark 테마 저장
- SQLite 무결성 검증 기반 전체 백업·원자적 복구
- 업로드 제한, Resolver 캐시, 일회성 Repository 초기화 성능 개선
- Streamlit Cloud 설정, 비밀정보 예제와 배포 문서 정리
- AI placeholder를 실제 규칙 기반 Summary/Insight로 교체

## v0.9 Portfolio Foundation

- SQLite 자동 마이그레이션과 자산 메타데이터 컬럼 추가
- 자산 자동입력 메타데이터 저장
- 포트폴리오 손익·자산군·국가·통화·섹터 분석 추가
- 현금·레버리지·인버스 및 명목 노출 분석 추가
- HHI와 집중도 진단 고도화
- 국내주식 기본정보와 가치평가 탭의 핵심 지표 기준 통일
- 포트폴리오 페이지를 테스트 화면에서 정식 기능으로 변경
- 단위 테스트 추가

## v1.0 Portfolio Intelligence
- Portfolio Score 규칙 기반 진단 추가
- 분산·현금·레버리지·국가·통화 세부 점수 추가
- 글로벌 급락·기술주 조정·금리 급등·달러 약세 스트레스 테스트 추가
- 자산 태그와 섹터 기반 Investment DNA 추가
- 자동 핵심 해석 문장 추가
- 포트폴리오 인텔리전스 단위 테스트 추가

## v1.1 Unified Portfolio Workspace

- 사용자 메뉴를 대시보드·포트폴리오·종목분석 3개로 축소했습니다.
- 기존 자산관리와 포트폴리오분석을 하나의 포트폴리오 페이지로 통합했습니다.
- 포트폴리오 페이지를 보유자산·구성 분석·위험 분석·보고서 탭으로 구분했습니다.
- 자산 등록·수정·삭제 후 포트폴리오 분석 캐시가 즉시 초기화되도록 개선했습니다.
- 현재 구조화 데이터를 이용한 포트폴리오 요약 보고서를 추가했습니다.

## Excel Asset DB Import

- 포트폴리오 보유자산 탭에 Excel 업로드 기능 추가
- `Assets` 시트 필수 열 및 숫자·통화 검증
- 반영 전 SQLite DB 자동 백업
- Excel 마스터 데이터로 자산 테이블 전체 원자적 교체
- 가져오기 완료 후 포트폴리오 분석 캐시 자동 초기화

## v1.2 UI Pack 1.0

- 대시보드 공통 디자인 토큰과 경량 CSS 테마 적용
- 외부 UI 라이브러리 없이 카드형 핵심 지표 컴포넌트 추가
- 자산군별 고정 색상과 전문형 도넛 차트 스타일 적용
- 표·차트·버튼·필터의 테두리, 여백, 배경을 일관되게 정리
- 기능·DB 구조·Excel 가져오기 방식은 변경하지 않음

## v1.2.1 Dashboard Ranking Fix
- 대시보드 기본 표시 기준을 `부동산 제외`로 변경했습니다.
- 평가이익 상위 표에 수익률 열이 항상 보이도록 열 너비를 명시했습니다.
- 평가손실 상위는 평가손실 금액이 큰 순서로 안정 정렬하도록 명확히 수정했습니다.

## v1.2.2 - One-page portfolio PDF

- 포트폴리오 보고서 탭에 A4 가로 1페이지 PDF 다운로드 기능을 추가했습니다.
- 현재 선택한 전체 자산/부동산 제외 기준을 PDF에 반영합니다.
- 핵심 지표, 자산군 도넛 그래프, 상위 보유자산, 핵심 요점과 위험을 한 페이지에 배치합니다.
- 별도 폰트 파일을 포함하지 않고 ReportLab 한국어 CID 폰트를 사용합니다.

## v1.2.3 - Portrait PDF Preview Fix
- 포트폴리오 상단 표시 기준과 PDF 분석 기준을 강제로 동기화
- 부동산 제외 선택 시 PDF에서도 부동산 제외 결과 사용
- 다운로드 전 PDF 미리보기 추가
- PDF를 A4 가로형에서 A4 세로형 1페이지로 변경
- 미리보기와 PDF가 동일한 분석 결과 객체를 사용하도록 개선

--------------------------------

## v0.3.1

### Changed

- Guest sidebar always exposes Google login when OAuth is configured
- Missing OAuth configuration shows a concise setup notice instead of a disabled button
- Successful Google login migrates Guest portfolio data before ending the Guest session

### Fixed

- Automatic Guest fallback no longer makes the Google upgrade path inaccessible

--------------------------------

## v0.3.0

### Added

- Google email SHA-256 user identity generation
- Per-user `portfolio.db`, `feedback.db`, and `logs.db` storage directories
- Automatic Guest fallback for missing secrets, invalid claims, auth errors, and logout

### Changed

- Repository selection now follows the request-scoped User Context without global
  cross-session switching
- Sidebar identity display consistently distinguishes Google and Guest users
- Existing shared SQLite user rows are copied into isolated storage on first activation

### Fixed

- Guest and Google portfolios, feedback, and error records can no longer share files

### Known Issues

- Per-user SQLite files remain ephemeral on Streamlit Community Cloud
- Live two-account OAuth verification requires the deployed URL and two Google pilot users

--------------------------------

## v0.2.9

### Added

- Streamlit Community Cloud deployment guide
- Production Google OAuth redirect and secrets checklist
- Documented non-secret build environment variables

### Changed

- Added the Authlib runtime dependency required by Streamlit Google login
- Removed fixed localhost server address and port from production configuration
- Enabled headless deployment defaults

### Fixed

- Google login can now load its required OAuth runtime on a clean cloud deployment

### Known Issues

- SQLite, feedback, and error logs remain instance-local on Streamlit Community Cloud

--------------------------------

## v0.2.8

### Added

- About dialog with Version, Build, and Git Tag
- User-scoped Bug, Suggestion, and Comment feedback capture
- Size-bounded local logging for unexpected page exceptions

### Changed

- Pilot sidebar now provides compact About and Feedback actions

### Fixed

- Uncaught application failures now retain diagnostic details locally

### Known Issues

- Feedback and error logs remain instance-local on Streamlit Community Cloud

--------------------------------

## v0.2.7

### Added

- Pilot-ready Google OIDC login through Streamlit authentication
- Persistent Google identity mapping using the provider subject ID
- Automatic empty portfolio and default account creation on first login

### Changed

- Returning users automatically restore their existing SQLite portfolio scope
- Google, Guest, and Developer modes share the same repository isolation boundary

### Fixed

- Added regression coverage preventing portfolio visibility across Google users

### Known Issues

- Streamlit Community Cloud SQLite files are not durable across instance replacement
- Production deployment still requires Google OAuth secrets and redirect registration

--------------------------------

## v0.2.6

### Added

- Google Login
- Guest Mode
- User Session
- Developer Login
- Complete User Context profile (`id`, `name`, `email`, `photo`, `plan`, guest and authentication state)
- Stable per-session Guest User ID
- Automatic SQLite ownership migration for legacy assets
- Google, Guest, and Developer login entry points

### Changed

- Repository supports user_id
- Authentication uses a single User Context
- Repository default scopes are obtained from the shared User Context
- Asset and account operations are isolated by `user_id`

### Fixed

- No breaking changes
- Restored original Excel row numbers after empty-row filtering
- Cleared all Ruff and Pylance/Pyright diagnostics without changing calculations
- Corrected malformed add-asset session warning lookup

### Known Issues

- Firestore not enabled yet

--------------------------------
