# AI Advisor Specification

## Purpose

AI Advisor는 구조화된 포트폴리오 분석 결과를 설명하는 의사결정 지원 서비스다.
매수·매도 종목을 지시하거나 미래 수익을 예측하지 않는다.

## Output contract

Feature Pack #1의 Portfolio AI provider는 다음 항목을 반환한다.

- overall_score
- strengths
- weaknesses
- risks
- recommendations
- next_action

Feature Pack #2 Dashboard·One Page Report 계약은 위 호환 필드와 함께 다음
구조화 필드를 제공한다.

- risk_level, diversification_score, cash_ratio, currency_exposure
- top_strengths(최대 3), top_risks(최대 3)
- recommended_actions(최대 5)

PDF·PNG·JSON은 같은 진단 인스턴스를 사용한다. PDF는 기존 Portfolio Report
생성기를 재사용하고 장점·위험·추천·다음 행동을 한 페이지에 포함한다.

진단 화면 호환을 위해 세부 점수와 배분 비율을 `metrics`로 함께 제공한다.

기존 Dashboard Summary provider는 다음 설명 항목을 반환한다.

- diversification
- concentration
- currency risk
- sector risk
- account advice
- investment summary

v1.0 RC의 `StructuredRulesAdvisorProvider`는 자산 수, 유효 분산 자산 수,
HHI·상위 비중, 통화·섹터·계정 배분과 평가손익에서 결과를 결정적으로 생성한다.
데이터가 없으면 값을 추정하지 않고 판단 불가 이유를 반환한다.

## Provider boundary

UI는 provider 구현을 직접 알지 않는다. 향후 OpenAI provider는 같은
구조화 입력과 출력 계약을 구현한다. 원격 provider를 활성화할 때는
전송 필드, 사용자 동의, 보존 정책, 제한시간과 실패 fallback을 별도로 정의한다.

자산 원본, 이메일, 계정 자격증명, API 키와 로컬 경로는 provider 입력에 넣지
않는다. 모든 응답은 투자 권유가 아니라 현재 포트폴리오 구조 설명으로 표시한다.

## Sprint 5 rule diagnosis

총자산 화면의 `🤖 AI Portfolio Advisor`와 상세 진단은 외부 API를 호출하지 않는다.
`portfolio_ai_service`가 기존 Portfolio Analyzer 결과로 Portfolio Score,
Diversification Score, Risk Score와 현금·미국·한국·ETF·주식·가상자산·부동산
비중을 계산한다.

장점·리스크·추천사항은 실제 비중에 적용된 결정적 규칙의 결과다. v1 기준 주요
규칙은 레버리지 20% 이상, 현금 3% 미만, ETF 40% 이상, 단일 자산 50% 이상,
가상자산 20% 이상이다. 현재 계정 필터와 부동산 포함 여부가 진단 범위에 그대로
적용되며 결과는 투자 권유가 아니다.
