# AssetOS Product Specification

이 폴더는 AssetOS의 제품 명세다. 문서 간 내용이 다를 때는 다음 순서로
해석한다.

1. `Product_Vision.md` — 제품 원칙과 장기 방향
2. `UX_RULES.md` — 모든 화면에 적용되는 UX 규칙
3. `SMART_IMPORT_SPEC.md` — Smart Import와 Asset Resolver 계약
4. `AI_ADVISOR.md` — AI Advisor 출력과 provider·개인정보 계약
5. `SPRINT*.md` — 특정 시점에 구현된 범위를 기록한 역사 문서

운영 데이터의 자동 변경 규칙은 `MIGRATION.md`에 기록한다.

상위 문서는 제품이 지향해야 할 현재 상태를 설명한다. Sprint 문서는 당시
구현을 설명하며, 상위 명세와 충돌할 경우 상위 명세를 따른다. 제품 명세와
현재 애플리케이션이 다를 수 있으며, 그 차이는 후속 구현 작업에서 명시적으로
해소한다.

## 용어

- **자산관리**: 자산 추가·수정·삭제, Excel 템플릿, 내보내기와 가져오기
- **Smart Import**: 최소 입력을 검증·해석·보강한 뒤 사용자 확인을 거쳐 반영하는 흐름
- **Asset Resolver**: 이름·별칭·티커를 표준 자산 후보로 변환하는 제공자 독립 서비스
- **Asset Master**: Resolver와 분석이 공유하는 로컬 표준 메타데이터 원천
- **투자계정**: 한 사용자의 자산을 Brokerage·ISA·Pension 등 목적별로 분리하는 소유 단위
- **분석 가능**: 계산에 필요한 원천값이 모두 존재해 결과를 왜곡 없이 표시할 수 있는 상태
- **로컬 사용자 컨텍스트**: 브라우저 `localStorage` UUID를 모든 Repository 호출의 `user_id` 범위로 전달하는 요청 단위 상태
- **Quick Analysis**: 업로드부터 export까지 Repository를 사용하지 않는 세션 전용 분석 흐름
- **스냅샷**: 한 사용자의 구조화된 포트폴리오 상태를 시점별로 보존한 불변 레코드

## Specification decisions

- 사용자 탐색은 세 페이지로 제한하고 통합 자산관리는 대시보드 dialog와 포트폴리오에서 같은 기능을 공유한다.
- Smart Import와 Asset Resolver의 모든 결정은 `SMART_IMPORT_SPEC.md`에 집중한다.
- Local User Mode는 `local:<uuid>`를 사용하며 모든 계정·자산·스냅샷 조회를 사용자 컨텍스트의 `user_id`로 제한한다.
- 설정, 백업과 복구는 세 페이지 탐색을 늘리지 않고 공통 사이드바에서 제공한다.

## Documentation review checklist

제품 동작을 추가하거나 변경할 때 다음을 함께 확인한다.

- 제품 원칙과 분석 무결성을 지키는가?
- Desktop, Tablet, Mobile 흐름이 정의되어 있는가?
- 빈 상태, 로딩, 실패, 부분 데이터와 재시도 상태가 정의되어 있는가?
- 자동조회 출처, 기준 시점과 fallback이 정의되어 있는가?
- 기존 DB와 Excel 호환성에 미치는 영향이 기록되어 있는가?
- destructive action의 미리보기, 백업, 롤백이 정의되어 있는가?
