# AssetOS v1.0 Architecture

## Runtime flow

```text
Streamlit pages/components
        │
        ├── browser localStorage UUID → local user context
        │
        ├── domain services (import, resolver, portfolio, settings)
        │         │
        │         ├── Asset Master CSV / external market providers
        │         └── AssetRepository interface
        │                    │
        └── database.db compatibility facade
                             │
                    SQLiteAssetRepository
```

SQL은 `repositories/sqlite_asset_repository.py`에만 존재합니다. 서비스는
Repository 인터페이스를 주입받거나 애플리케이션 기본 Repository를 사용합니다.
`database.db`는 기존 UI 호출을 유지하기 위한 얇은 호환 facade입니다.

## Data ownership

```text
User
 ├── UserPreferences
 ├── Account
 │    └── Asset
 └── PortfolioSnapshot
```

- 현재 사용자는 브라우저별 `local:<uuid>`이며 `default_user`는 기존 데이터 이전에만 사용됩니다.
- 모든 사용자는 `My Portfolio` 기본 계정을 가집니다.
- 모든 자산은 일치하는 `user_id`와 `account_id`를 가집니다.
- 모든 자산·계정·환경설정·스냅샷 쿼리는 로컬 사용자 컨텍스트의 `user_id`로 제한됩니다.
- DB trigger가 자산의 사용자와 계정 소유자 불일치를 차단합니다.

## Local user mode

Streamlit v2 양방향 컴포넌트가 브라우저 `localStorage`에서 UUID를 읽거나 최초
생성합니다. 서버는 검증된 `local:<uuid>`만 요청 단위 user context로 설정합니다.
로그인과 인증 UI는 없으며 모든 Repository query가 이 범위를 상속합니다.
`migrate_user_scope`는 기존 `default_user` 이전과 향후 로그인 identity 연결에
공통으로 사용할 원자적 소유권 이전 경계입니다.

## Quick Analysis

```text
Excel bytes (session_state)
 → shared detection / mapping / validation
 → shared resolver / price enrichment
 → editable preview
 → in-memory Portfolio Analyzer
 → PortfolioAIProvider
 → PDF / PNG / JSON bytes (session_state)
```

분석과 export 흐름은 `AssetRepository`를 호출하지 않습니다. 파일이 바뀌면 모든 임시 결과와
export bytes를 폐기하며 `Analyze Only`는 영구 DB와 snapshot에 어떤 행도 기록하지
않습니다. 사용자가 `Save into AssetOS`와 대상 계정 전체 교체를 확인한 경우에만
기존 백업·원자적 `import_asset_rows` 경로로 분기합니다.

## AI Advisor

`AIAdvisorProvider`는 구조화된 포트폴리오 분석을 `PortfolioAdvice`로 변환합니다.
현재 provider는 실제 배분·집중도 수치에서 결정적 설명을 생성합니다. 향후 OpenAI
provider도 같은 입력·출력 계약을 사용하며 Dashboard는 provider 구현을 알지 않습니다.

## Smart Import

```text
Account selection
 → file detection
 → column mapping
 → validation
 → shared Asset Master / alias / local search
 → external resolution only on local miss
 → market-price enrichment
 → editable preview and validation
 → confirmation
 → backup
 → atomic account replacement
```

업로드와 미리보기 편집은 DB를 변경하지 않습니다. 동일 행의 Resolver 결과는 짧게
캐시하며 unknown/ambiguous 자산은 자동 선택하지 않고 `Needs Review`로 남깁니다.

자산 단건·일괄 변경은 Repository의 사용자 범위 검증을 거칩니다. Excel/JSON
내보내기는 읽기 전용 서비스이며 SQLite 전체 백업·복구와 분리됩니다.

## Recovery

SQLite backup API로 일관된 전체 백업을 생성합니다. 복구 파일은 크기,
`PRAGMA integrity_check`, `assets` 테이블을 검증한 뒤 현재 DB를 안전 백업하고
같은 파일시스템에서 원자적으로 교체합니다. 구형 AssetOS DB도 복구 후 자동
마이그레이션됩니다.

## Performance

- Repository 스키마 초기화는 프로세스당 한 번 수행합니다.
- 정적 Asset Master와 학습 overlay는 하나의 메모리 캐시로 병합됩니다.
- 검증된 사용자 선택과 신뢰도 높은 온라인 결과는 학습 overlay에 원자적으로
  기록되어 다음 조회부터 로컬 resolver가 처리합니다.
- fuzzy 검색은 신뢰 임계값을 통과한 관련 후보만 반환합니다.
- 환율·시장정보·Smart Import Resolver 결과에는 TTL 캐시가 적용됩니다.
- Excel/PDF 생성과 외부 조회는 사용자 행동 이후 실행합니다.
- 업로드는 10MB/10,000행으로 제한합니다.

## Deployment boundary

Streamlit Community Cloud에서 실행 가능하지만 로컬 SQLite는 단일 인스턴스
저장소입니다. 향후 인증과 영구 다중 인스턴스 운영은 동일 `AssetRepository` 계약의
원격 구현으로 확장합니다.
