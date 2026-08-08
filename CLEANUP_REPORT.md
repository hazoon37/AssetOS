# AssetOS v1.0 Cleanup Report

## Completed

- SQL 접근을 SQLite Repository 한 곳으로 통합
- 대시보드 중복 포트폴리오 계산 제거
- 미사용 대시보드 상수 제거
- AI placeholder를 실제 데이터 기반 요약으로 교체
- 폐기 예정 Streamlit width API를 현재 API로 교체
- `data/` ignore 범위를 DB와 백업으로 제한해 Asset Master CSV 배포 보장
- 실제 secrets는 ignore하고 빈 예제만 저장
- Python 캐시, 로컬 DB, 백업과 `.venv`를 배포 대상에서 제외

## Verification

- 자동 마이그레이션 및 사용자/계정 격리 테스트
- Smart Import 템플릿·일반 Excel·매핑·Resolver 테스트
- Asset Master와 외부 fallback 테스트
- 환경설정 및 백업/복구 테스트
- Streamlit 전체 앱 smoke test
- Python compile 및 dependency consistency 검사
- `.venv`와 `.git` 제외 프로젝트 크기 검사
