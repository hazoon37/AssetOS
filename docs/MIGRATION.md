# AssetOS v1.0 Migration

## Automatic migration

애플리케이션 시작 시 SQLite Repository가 기존 `assets` 테이블을 검사한다.
없는 메타데이터, `account_id`와 `user_id` 열만 추가하며 기존 자산의 ID, 가격, 수량,
메모와 생성일은 보존한다.

`default_user`와 `My Portfolio`가 없으면 생성하고, 계정이 없는 과거 자산을
기본 계정에 연결하고 `assets.user_id`를 계정 소유자로 채운다. `snapshots` 테이블과
사용자별 인덱스를 자동 생성한다. 모든 신규 자산은 사용자 소유 계정에만 저장되며 DB
트리거가 사용자·계정 불일치 행을 차단한다. 사용자 환경설정은 최초 조회 시 기본값
`KRW`와 `System`으로 생성된다.

브라우저 Local User Mode가 처음 활성화되면 `local:<uuid>` 사용자와 기본 계정을
생성한다. 해당 사용자의 자산이 비어 있고 `default_user`에 기존 자산이 있을 때만
계정 이름을 기준으로 매핑하여 자산·스냅샷·환경설정을 한 트랜잭션으로 이전한다.
두 번째 브라우저가 같은 데이터를 중복 인계받지 않으며 기존 ID와 자산 값은 보존한다.

## Import and recovery

Smart Import는 선택 계정만 백업 후 원자적으로 교체한다. 다른 계정과 사용자의
자산은 유지한다. 편집 미리보기는 저장 작업이 아니며 `Apply Changes`와 확인을
거쳐야 반영된다.

SQLite 복구는 50MB 제한, 무결성 검사와 `assets` 테이블 확인을 통과한 파일만
허용한다. 복구 전에 현재 DB 안전 백업을 만들고, 복구 DB에도 동일 자동
마이그레이션을 실행한다. 실패하면 안전 백업으로 되돌린다.

## Deployment note

Streamlit Community Cloud의 로컬 파일은 영구 저장을 보장하지 않는다. 배포 전
설정에서 SQLite 백업을 내려받고, 영구 다중 인스턴스 운영 시에는 동일한
`AssetRepository` 계약의 원격 구현으로 교체해야 한다.
