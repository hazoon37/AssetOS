# AssetOS Product Specification

이 폴더는 AssetOS의 제품 명세다. 문서 간 내용이 다를 때는 다음 순서로
해석한다.

1. `Product_Vision.md` — 제품 원칙과 장기 방향
2. `UX_RULES.md` — 모든 화면에 적용되는 UX 규칙
3. `SMART_IMPORT_SPEC.md` — Smart Import와 Asset Resolver 계약
4. `SPRINT*.md` — 특정 시점에 구현된 범위를 기록한 역사 문서

상위 문서는 제품이 지향해야 할 현재 상태를 설명한다. Sprint 문서는 당시
구현을 설명하며, 상위 명세와 충돌할 경우 상위 명세를 따른다. 제품 명세와
현재 애플리케이션이 다를 수 있으며, 그 차이는 후속 구현 작업에서 명시적으로
해소한다.

## 용어

- **자산관리**: 자산 추가·수정·삭제, Excel 템플릿, 내보내기와 가져오기
- **Smart Import**: 최소 입력을 검증·해석·보강한 뒤 사용자 확인을 거쳐 반영하는 흐름
- **Asset Resolver**: 이름·별칭·티커를 표준 자산 후보로 변환하는 제공자 독립 서비스
- **분석 가능**: 계산에 필요한 원천값이 모두 존재해 결과를 왜곡 없이 표시할 수 있는 상태

## Specification decisions

- 사용자 탐색은 세 페이지로 제한하고 자산관리는 대시보드와 포트폴리오에서 같은 기능을 공유한다.
- Smart Import와 Asset Resolver의 모든 결정은 `SMART_IMPORT_SPEC.md`에 집중한다.

## Documentation review checklist

제품 동작을 추가하거나 변경할 때 다음을 함께 확인한다.

- 제품 원칙과 분석 무결성을 지키는가?
- Desktop, Tablet, Mobile 흐름이 정의되어 있는가?
- 빈 상태, 로딩, 실패, 부분 데이터와 재시도 상태가 정의되어 있는가?
- 자동조회 출처, 기준 시점과 fallback이 정의되어 있는가?
- 기존 DB와 Excel 호환성에 미치는 영향이 기록되어 있는가?
- destructive action의 미리보기, 백업, 롤백이 정의되어 있는가?
