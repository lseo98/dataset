import json
import re
from collections import Counter, defaultdict
from pathlib import Path


OUTPUT = Path("sanity_check_v3.jsonl")

INSTRUCTION = (
    "IT 전문 면접관으로서 제공된 문답과 분석 데이터를 바탕으로 상단(BEST/WORST), "
    "중단(Fit-Gap), 하단(평가 스크립트) 보고서를 생성하십시오. 모든 판단은 오직 "
    "[정량 지표], [STAR 기준], [Fit-Gap 기준], [문장 단위 위반 규칙]에 의거해야 합니다."
)

STAR_GOOD = {"S": True, "T": True, "A": True, "R": True}
STAR_PARTIAL = {"S": True, "T": True, "A": True, "R": False}
STAR_FAIL = {"S": True, "T": False, "A": False, "R": False}
STAR_EMPTY = {"S": False, "T": False, "A": False, "R": False}

PATTERNS = [
    {"good": "Q1", "partial": "Q2", "fail": "Q3"},
    {"good": "Q2", "partial": "Q3", "fail": "Q1"},
    {"good": "Q3", "partial": "Q1", "fail": "Q2"},
    {"good": "Q2", "partial": "Q1", "fail": "Q3"},
    {"good": "Q3", "partial": "Q2", "fail": "Q1"},
    {"good": "Q1", "partial": "Q3", "fail": "Q2"},
]


CASES = [
    {
        "job_key": "backend",
        "job": "Backend Engineer - Java/Spring 기반 주문 API, Redis 캐시, 장애 대응 경험자",
        "good_q": "주문 API 성능 병목을 해결한 경험이 있나요?",
        "good_a": "작년 커머스 주문 조회 API의 p95 응답 시간이 3초까지 늘어난 문제가 있었습니다. 저는 APM trace로 반복 호출되는 상품 조회 쿼리를 찾고 Redis 캐시와 TTL 정책을 적용했습니다. 배포 후 p95 응답 시간이 620ms로 줄었고 DB read 부하도 45% 감소했습니다.",
        "partial_q": "Redis 캐시를 적용할 때 어떤 점을 고려하나요?",
        "partial_a": "캐시는 빠릅니다. 다만 모든 데이터를 캐시에 넣으면 안 된다고 생각합니다. 저는 TTL과 캐시 무효화 정책을 같이 봅니다. 왜냐하면 오래된 데이터가 노출될 수 있기 때문입니다. 하지만 write-through와 cache-aside 방식의 장단점 비교는 충분히 설명하지 못했습니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "트랜잭션 정합성 문제를 어떻게 해결했나요?",
        "fail_a": "저희 팀은 결제 정합성 문제를 잘 해결했습니다. 저는 회의에 참여했고 전체 방향을 이해했습니다. 실제 락 전략이나 보상 트랜잭션 설계는 다른 팀원이 주도했습니다.",
        "fail_reason": "본인의 역할(Action) 없이 팀의 성과 뒤에 숨음",
    },
    {
        "job_key": "backend",
        "job": "Backend Engineer - Go 기반 인증 API, JWT, OAuth2, 대용량 트래픽 처리 경험자",
        "good_q": "인증 API 장애를 해결한 경험이 있나요?",
        "good_a": "소셜 로그인 트래픽이 몰릴 때 토큰 검증 API가 간헐적으로 timeout 되는 문제가 있었습니다. 저는 외부 공개키 조회를 요청마다 수행하는 구조를 발견하고 JWKS 캐시와 circuit breaker를 추가했습니다. 이후 timeout 비율이 2.1%에서 0.1% 이하로 낮아졌습니다.",
        "partial_q": "JWT를 사용할 때 가장 조심해야 할 점은 무엇인가요?",
        "partial_a": "JWT는 서버 세션을 줄일 수 있어서 편리하다고 생각합니다. 저는 만료 시간과 서명 알고리즘을 확인합니다. 운영에서는 refresh token도 분리했습니다. 다만 키 회전, 폐기 목록, 탈취 시 대응 절차까지는 구체적으로 설명하지 못했습니다.",
        "partial_reason": "검증 범위가 제한적임",
        "fail_q": "OAuth2 authorization code flow를 설명해 주세요.",
        "fail_a": "OAuth2는 비밀번호를 암호화해서 DB에 안전하게 저장하는 기술입니다. 그래서 salt를 길게 잡으면 대부분 해결됩니다. access token은 사용자가 입력하는 비밀번호라고 보면 됩니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "frontend",
        "job": "Frontend Engineer - React, 상태 관리, Core Web Vitals 개선 경험자",
        "good_q": "웹 성능 지표를 개선한 경험이 있나요?",
        "good_a": "프로모션 페이지의 LCP가 4.2초로 측정되어 이탈률이 높았습니다. 저는 hero 이미지를 AVIF로 변환하고 preload 우선순위를 조정했으며 route 단위 code splitting도 적용했습니다. 배포 후 LCP가 1.8초로 개선되었고 이탈률은 12% 감소했습니다.",
        "partial_q": "상태 관리 라이브러리를 선택할 때 무엇을 보나요?",
        "partial_a": "저는 팀이 이해하기 쉬운 도구가 좋다고 생각합니다. 작은 화면에서는 Context API도 충분했습니다. 복잡한 도메인에서는 Zustand를 사용해 본 적이 있습니다. 다만 서버 상태와 클라이언트 상태를 분리하는 기준을 실제 사례로 깊게 설명하지 못했습니다.",
        "partial_reason": "운영 지표와 연결한 검증이 부족함",
        "fail_q": "React 렌더링 최적화를 어떻게 하나요?",
        "fail_a": "저는 CSS 애니메이션을 부드럽게 만드는 것이 렌더링 최적화라고 생각합니다. 색상과 여백을 잘 맞추면 사용자도 빠르다고 느낍니다. React.memo나 re-render 원인은 잘 모르겠습니다.",
        "fail_reason": "근거 없는 일반론으로 답변함",
    },
    {
        "job_key": "frontend",
        "job": "Frontend Engineer - Vue/Nuxt 기반 SSR, 접근성, 대시보드 UI 개발 경험자",
        "good_q": "SSR 화면의 초기 로딩 문제를 해결한 경험이 있나요?",
        "good_a": "관리자 대시보드 첫 진입 시 서버 렌더링 시간이 2초 이상 걸렸습니다. 저는 API 호출을 병렬화하고 사용자 권한 데이터만 서버에서 먼저 가져오도록 쿼리를 분리했습니다. 그 결과 TTFB가 1.9초에서 780ms로 줄었습니다.",
        "partial_q": "접근성을 개선할 때 어떤 점을 확인하나요?",
        "partial_a": "접근성은 키보드 이동과 대체 텍스트가 중요하다고 생각합니다. 실제로 버튼 aria-label과 focus outline을 정리한 적이 있습니다. 하지만 스크린리더 검증, 명도 대비, 폼 오류 안내까지 체계적인 체크리스트로 운영하지는 못했습니다.",
        "partial_reason": "검증 범위가 제한적임",
        "fail_q": "Nuxt의 hydration mismatch가 생기면 어떻게 하나요?",
        "fail_a": "hydration은 물을 충분히 마시는 것처럼 화면을 촉촉하게 유지하는 개념이라고 이해했습니다. 그래서 저는 이미지가 깨지지 않도록 CSS를 먼저 확인할 것 같습니다. 정확한 원인은 아직 설명이 어렵습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "data",
        "job": "Data Engineer - Spark, Airflow, 대규모 ETL 파이프라인 운영 경험자",
        "good_q": "Spark 작업 시간을 줄인 경험이 있나요?",
        "good_a": "일별 로그 집계 작업에서 특정 user_id에 데이터가 몰려 shuffle 시간이 크게 늘었습니다. 저는 salting으로 skew key를 분산하고 join 전에 필요한 컬럼만 projection 하도록 ETL을 수정했습니다. 전체 작업 시간은 140분에서 52분으로 줄었습니다.",
        "partial_q": "Airflow DAG를 설계할 때 어떤 기준을 적용하나요?",
        "partial_a": "DAG는 실패했을 때 다시 실행하기 쉬워야 합니다. 저는 task를 작게 나누고 retry 정책을 설정합니다. 하지만 외부 API가 느린 상황에서 backfill이 길게 밀리면 이 방식만으로는 충분하지 않았습니다. 특수한 배치 환경에서만 잘 동작한 해결책이었습니다.",
        "partial_reason": "특수한 상황에서만 작동하는 해결책임",
        "fail_q": "Kafka lag이 증가하면 어떻게 대응하나요?",
        "fail_a": "Kafka lag은 로그 파일 크기가 커지는 현상이라고 알고 있습니다. 그래서 디스크를 정리하면 해결될 것 같습니다. 컨슈머 그룹이나 파티션은 아직 자세히 보지 못했습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "data",
        "job": "Analytics Engineer - dbt, 데이터 마트, 지표 정의 및 품질 검증 경험자",
        "good_q": "지표 불일치 문제를 해결한 경험이 있나요?",
        "good_a": "매출 대시보드와 정산 리포트의 일 매출 수치가 다르게 나오는 문제가 있었습니다. 저는 주문 취소 시점과 환불 반영 기준이 다른 것을 확인하고 dbt 모델의 metric layer를 통합했습니다. 이후 두 리포트의 차이가 0.3% 이내로 줄었습니다.",
        "partial_q": "데이터 마트를 설계할 때 무엇을 중요하게 보나요?",
        "partial_a": "저는 분석가가 쉽게 쓸 수 있는 구조가 중요하다고 생각합니다. fact와 dimension을 나누고 컬럼 설명도 작성했습니다. 다만 slowly changing dimension이나 late arriving data 처리 방식은 실제 운영 수준으로 깊게 다뤄보지 못했습니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "dbt test가 실패하면 어떻게 하나요?",
        "fail_a": "테스트가 실패하면 일단 다시 실행해 봅니다. 음, 그 다음에는... 아마 로그를 보고... 정확히는 지금 바로 떠오르지 않습니다. 팀원에게 물어볼 것 같습니다.",
        "fail_reason": "당황해서 말을 끝맺지 못함",
    },
    {
        "job_key": "ml",
        "job": "Machine Learning Engineer - 추천 모델, 피처 스토어, 온라인 실험 경험자",
        "good_q": "추천 모델 성능을 개선한 경험이 있나요?",
        "good_a": "신규 사용자의 클릭률이 낮아 개인화 추천 품질이 떨어지는 문제가 있었습니다. 저는 최근 세션 행동 기반 피처를 추가하고 cold-start 후보군을 별도 랭커로 분리했습니다. A/B 테스트에서 CTR이 8.4% 상승했고 7일 재방문율도 개선되었습니다.",
        "partial_q": "피처 스토어를 도입할 때 어떤 점을 고려하나요?",
        "partial_a": "학습과 서빙의 피처 정의가 같아야 한다고 생각합니다. 저는 피처 계산 로직을 공통화하려고 했습니다. 하지만 online/offline consistency 검증, point-in-time join, freshness SLA 같은 운영 디테일은 충분히 설계하지 못했습니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "모델 과적합을 어떻게 줄이나요?",
        "fail_a": "과적합은 GPU 메모리가 부족해서 생기는 문제라고 알고 있습니다. 그래서 더 큰 GPU를 쓰면 해결될 수 있습니다. 데이터 분할이나 regularization은 아직 익숙하지 않습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "ml",
        "job": "MLOps Engineer - 모델 배포, 모니터링, drift 탐지 및 롤백 자동화 경험자",
        "good_q": "모델 배포 후 품질 저하를 탐지한 경험이 있나요?",
        "good_a": "문서 분류 모델 배포 후 특정 고객군의 오분류율이 급증했습니다. 저는 입력 토큰 길이 분포와 예측 confidence 변화를 모니터링해 데이터 drift를 확인했습니다. 임계치 기반 롤백과 재학습 파이프라인을 연결해 오분류율을 기존 수준으로 복구했습니다.",
        "partial_q": "모델 롤백 전략은 어떻게 설계하나요?",
        "partial_a": "저는 이전 모델을 바로 되돌릴 수 있어야 한다고 생각합니다. 그래서 버전 태그와 artifact 저장소를 분리했습니다. 다만 shadow deployment와 canary 기준, 롤백 임계치 산정 방식은 실제 장애 사례로 충분히 검증하지 못했습니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "모델 모니터링 지표를 설명해 주세요.",
        "fail_a": "모니터링은 서버가 켜져 있는지 보는 것이라고 생각합니다. CPU와 메모리만 괜찮으면 모델도 정상입니다. 예측 분포나 데이터 drift는 아직 잘 모르겠습니다.",
        "fail_reason": "질문의 의도와 완전히 다른 기술을 설명함",
    },
    {
        "job_key": "mobile",
        "job": "Android Developer - Kotlin, Jetpack Compose, 앱 안정성 및 성능 최적화 경험자",
        "good_q": "앱 시작 속도를 개선한 경험이 있나요?",
        "good_a": "쇼핑 앱 콜드 스타트 시간이 4초 이상 걸려 첫 화면 이탈이 많았습니다. 저는 Application 초기화 작업을 lazy init으로 분리하고 불필요한 SDK 로딩을 첫 화면 이후로 미뤘습니다. 콜드 스타트는 1.7초로 줄었고 첫 화면 이탈률도 감소했습니다.",
        "partial_q": "Compose에서 recomposition을 줄이려면 무엇을 보나요?",
        "partial_a": "상태가 너무 넓게 전달되면 recomposition이 늘어난다고 생각합니다. 저는 state hoisting과 remember 사용 위치를 확인합니다. 하지만 stable class 설계, snapshot state 관찰 범위, measurement 도구 활용은 아직 실무 디테일이 부족합니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "ANR이 발생하면 어떻게 분석하나요?",
        "fail_a": "ANR은 네트워크가 느릴 때만 생긴다고 알고 있습니다. 그래서 와이파이를 바꾸거나 서버를 재시작하면 됩니다. main thread block 분석은 해본 적이 없습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "mobile",
        "job": "iOS Developer - Swift, SwiftUI, Combine 기반 앱 개발 및 크래시 개선 경험자",
        "good_q": "앱 크래시율을 낮춘 경험이 있나요?",
        "good_a": "구독 화면에서 비동기 결제 콜백 이후 앱이 종료되는 문제가 있었습니다. 저는 Crashlytics stack trace를 분석해 해제된 ViewModel을 참조하는 경로를 확인했습니다. weak self 처리와 상태 검증을 추가했고 해당 화면 크래시율을 0.7%에서 0.04%로 낮췄습니다.",
        "partial_q": "Combine을 사용할 때 메모리 누수를 어떻게 막나요?",
        "partial_a": "저는 cancellable을 보관하고 순환 참조를 조심해야 한다고 생각합니다. 실제로 sink 내부에서 weak self를 사용한 적이 있습니다. 다만 복잡한 operator chain에서 retain cycle을 추적하는 방법과 Instruments 검증 과정은 자세히 설명하지 못했습니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "SwiftUI 상태 관리는 어떻게 하나요?",
        "fail_a": "SwiftUI는 화면을 예쁘게 만드는 도구라고 생각합니다. 상태 관리는 디자이너가 정한 화면 순서대로 만들면 됩니다. StateObject와 ObservedObject 차이는 아직 헷갈립니다.",
        "fail_reason": "질문의 의도와 완전히 다른 기술을 설명함",
    },
    {
        "job_key": "security",
        "job": "Security Engineer - 웹 취약점 진단, 시큐어 코딩, 침해 사고 대응 경험자",
        "good_q": "SQL Injection 취약점을 조치한 경험이 있나요?",
        "good_a": "고객 검색 API에서 파라미터 조작으로 인증 우회 가능성이 있는 SQL Injection 취약점을 발견했습니다. 저는 Prepared Statement를 적용하고 입력 검증 로직과 WAF 탐지 룰을 함께 보완했습니다. 재검증 결과 취약점이 제거되었고 보안 점검을 통과했습니다.",
        "partial_q": "침해 사고 초기 대응에서 무엇을 우선하나요?",
        "partial_a": "저는 증거 보존이 중요하다고 생각합니다. 그래서 로그를 확보하고 영향을 받은 서버를 격리해야 한다고 설명할 수 있습니다. 다만 메모리 덤프, 타임라인 작성, 법무 보고 체계까지 실제 절차로 수행한 경험은 부족합니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "XSS와 CSRF의 차이를 설명해 주세요.",
        "fail_a": "XSS는 서버가 다운되는 공격이고 CSRF는 데이터베이스가 깨지는 공격입니다. 둘 다 방화벽을 켜면 대부분 막을 수 있습니다. 브라우저 보안 정책은 자세히 모릅니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "security",
        "job": "Cloud Security Engineer - IAM, CSPM, 클라우드 권한 자동화 경험자",
        "good_q": "과도한 클라우드 권한을 줄인 경험이 있나요?",
        "good_a": "여러 프로젝트 계정에서 관리자 권한이 넓게 부여되어 감사 지적을 받은 적이 있었습니다. 저는 IAM 사용 로그를 분석해 실제 사용 권한만 남기는 최소 권한 정책을 재설계하고 Terraform으로 배포했습니다. 그 결과 고위험 권한 부여 건수가 80% 감소했습니다.",
        "partial_q": "CSPM 알림 우선순위는 어떻게 정하나요?",
        "partial_a": "저는 심각도와 외부 노출 여부를 함께 봅니다. 인터넷에 열린 리소스는 먼저 확인합니다. 하지만 업무 중요도, 예외 승인, 조치 SLA를 반영한 운영 모델까지는 구체화하지 못했습니다.",
        "partial_reason": "특수한 상황에서만 작동하는 해결책임",
        "fail_q": "IAM role과 policy의 차이를 설명해 주세요.",
        "fail_a": "저희 팀이 AWS 권한 관리를 잘했습니다. 저는 전체 회의에서 내용을 들었고 결과도 좋았습니다. 구체적인 role 설계나 policy 조건 작성은 다른 담당자가 했습니다.",
        "fail_reason": "본인의 역할(Action) 없이 팀의 성과 뒤에 숨음",
    },
    {
        "job_key": "infra",
        "job": "DevOps Engineer - Terraform, CI/CD, Kubernetes 운영 및 비용 최적화 경험자",
        "good_q": "Terraform 변경 사고를 줄인 경험이 있나요?",
        "good_a": "수동 콘솔 변경으로 보안 그룹 설정이 코드와 달라지는 문제가 반복되었습니다. 저는 Terraform plan 결과를 PR에 자동 첨부하고 drift detection 잡을 매일 실행하도록 구성했습니다. 이후 승인되지 않은 변경을 14건 사전에 발견했고 배포 사고도 줄었습니다.",
        "partial_q": "CI/CD 파이프라인에서 가장 중요하게 보는 지표는 무엇인가요?",
        "partial_a": "저는 배포 성공률과 빌드 시간이 중요하다고 생각합니다. 캐시와 병렬 실행도 적용했습니다. 다만 실패 원인 분류, rollback lead time, 변경 실패율을 함께 비교하지 못해 지표 간 장단점 설명이 부족했습니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "Kubernetes Pod가 Pending이면 어떻게 보나요?",
        "fail_a": "Pending은 배포가 성공했다는 뜻으로 알고 있습니다. 그래서 조금 기다리면 Running이 됩니다. 스케줄링 실패나 리소스 부족 이벤트는 아직 확인해 본 적이 없습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "infra",
        "job": "SRE - 서비스 가용성, SLO, 장애 회고 및 자동 복구 시스템 경험자",
        "good_q": "SLO 기반으로 장애 대응을 개선한 경험이 있나요?",
        "good_a": "검색 API의 99% latency SLO가 반복적으로 위반되는 문제가 있었습니다. 저는 error budget 소진 속도를 알림 기준에 반영하고 느린 쿼리를 자동 태깅하는 대시보드를 만들었습니다. 이후 SLO 위반 시간이 월 180분에서 35분으로 감소했습니다.",
        "partial_q": "장애 회고에서 무엇을 중요하게 보나요?",
        "partial_a": "저는 사람을 탓하지 않는 문화가 중요하다고 생각합니다. 타임라인과 액션 아이템을 정리한 경험도 있습니다. 다만 액션 아이템 완료율, 재발률, 감지 시간 개선을 회고 지표로 연결하지는 못했습니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "자동 복구 시스템을 설계해 본 적이 있나요?",
        "fail_a": "자동 복구는 팀에서 만든 적이 있습니다. 저는 그 시스템을 사용했고 장애가 줄었다고 들었습니다. 어떤 health check와 rollback 조건을 넣었는지는 직접 설계하지 않았습니다.",
        "fail_reason": "본인의 역할(Action) 없이 팀의 성과 뒤에 숨음",
    },
    {
        "job_key": "embedded",
        "job": "Embedded Linux Engineer - Yocto, 디바이스 드라이버, 부팅 최적화 경험자",
        "good_q": "임베디드 장비 부팅 시간을 줄인 경험이 있나요?",
        "good_a": "산업용 게이트웨이 장비의 부팅 시간이 70초 이상 걸려 현장 재시작 시간이 길었습니다. 저는 systemd-analyze로 병목 서비스를 찾고 불필요한 데몬을 제거했으며 드라이버 초기화 순서를 병렬화했습니다. 최종적으로 부팅 시간을 32초로 줄여 현장 복구 시간을 단축했습니다.",
        "partial_q": "드라이버 디버깅 시 어떤 정보를 먼저 보나요?",
        "partial_a": "저는 커널 로그와 레지스터 값을 먼저 봅니다. 데이터시트의 초기화 순서도 확인합니다. 하지만 인터럽트 타이밍 문제나 DMA 버퍼 동기화 같은 특수 상황에서는 이 절차만으로 원인 파악이 어려웠습니다.",
        "partial_reason": "특수한 상황에서만 작동하는 해결책임",
        "fail_q": "커널 패닉 로그를 보면 무엇을 확인하나요?",
        "fail_a": "커널 패닉은 보통 화면이 깜빡이는 문제라고 생각합니다. 그래서 디스플레이 케이블을 먼저 바꾸면 됩니다. stack trace나 oops 메시지는 아직 읽어본 적이 없습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "embedded",
        "job": "Firmware Engineer - RTOS, 센서 제어, 저전력 최적화 경험자",
        "good_q": "배터리 사용 시간을 늘린 경험이 있나요?",
        "good_a": "웨어러블 센서 장치가 하루를 넘기지 못하고 방전되는 문제가 있었습니다. 저는 센서 polling 주기를 이벤트 기반 인터럽트로 바꾸고 sleep mode 진입 조건을 세분화했습니다. 평균 배터리 지속 시간이 18시간에서 42시간으로 늘었습니다.",
        "partial_q": "RTOS task 우선순위를 정할 때 무엇을 고려하나요?",
        "partial_a": "저는 실시간성이 높은 작업을 높은 우선순위에 둬야 한다고 생각합니다. 센서 읽기와 통신 task를 분리해 본 적도 있습니다. 다만 priority inversion이나 mutex 설계까지 포함한 실무 적용 디테일은 부족합니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "I2C 통신 오류를 어떻게 분석하나요?",
        "fail_a": "I2C는 인터넷 통신 프로토콜이라 네트워크 방화벽을 먼저 보면 됩니다. 포트가 막히면 센서 통신도 실패합니다. 오실로스코프나 pull-up 저항은 잘 모르겠습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "game",
        "job": "Game Server Engineer - 실시간 매치메이킹, Redis 세션, WebSocket 운영 경험자",
        "good_q": "매치메이킹 대기 시간을 줄인 경험이 있나요?",
        "good_a": "랭크전 피크 시간대에 특정 티어 사용자의 매칭 대기 시간이 90초를 넘는 문제가 있었습니다. 저는 Redis sorted set으로 대기열을 재구성하고 시간이 지날수록 매칭 범위를 점진적으로 확장하는 로직을 적용했습니다. 그 결과 평균 대기 시간이 38초로 줄었고 매칭 실패율도 감소했습니다.",
        "partial_q": "WebSocket 세션을 안정적으로 운영하려면 무엇을 보나요?",
        "partial_a": "연결 상태와 재접속 처리가 중요합니다. 저는 heartbeat와 Redis TTL을 활용했습니다. 다만 모바일 네트워크 전환, 서버 재시작, 중복 세션 처리 상황에서 각각의 장단점을 충분히 비교하지 못했습니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "게임 서버 지연이 증가하면 어떻게 하나요?",
        "fail_a": "저는 클라이언트 FPS를 올리면 서버 지연도 같이 줄어든다고 생각합니다. 그래서 그래픽 옵션을 낮추면 해결될 수 있습니다. 서버 tick이나 네트워크 RTT는 아직 잘 모릅니다.",
        "fail_reason": "질문의 의도와 완전히 다른 기술을 설명함",
    },
    {
        "job_key": "game",
        "job": "Game Client Developer - Unity, C#, 메모리 최적화 및 UI 구현 경험자",
        "good_q": "프레임 드랍을 해결한 경험이 있나요?",
        "good_a": "전투 화면에서 이펙트가 많이 발생할 때 GC spike로 프레임이 30 이하로 떨어졌습니다. 저는 projectile과 hit effect에 object pooling을 적용하고 Update 호출이 많은 UI 컴포넌트를 이벤트 기반으로 바꿨습니다. 최저 프레임이 30에서 58로 개선되었습니다.",
        "partial_q": "UI 최적화에서 무엇을 중요하게 보나요?",
        "partial_a": "저는 Canvas rebuild를 줄이는 것이 중요하다고 생각합니다. 정적 UI와 동적 UI를 분리한 경험이 있습니다. 하지만 draw call, atlas 구성, overdraw 측정까지 함께 비교하지 못해 최적화 근거가 제한적입니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "벡터 내적을 어디에 활용할 수 있나요?",
        "fail_a": "벡터 내적은 캐릭터의 체력을 계산하는 공식이라고 알고 있습니다. 숫자를 곱하면 데미지가 커집니다. 시야 판정이나 방향 유사도와의 관계는 설명하기 어렵습니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "qa",
        "job": "QA Automation Engineer - Playwright, API 테스트, CI 품질 게이트 운영 경험자",
        "good_q": "회귀 테스트 시간을 줄인 경험이 있나요?",
        "good_a": "배포 전 수동 회귀 테스트가 6시간 이상 걸려 릴리즈가 지연되었습니다. 저는 핵심 사용자 플로우를 Playwright로 자동화하고 GitHub Actions에서 병렬 실행되도록 구성했습니다. 회귀 테스트 시간이 50분으로 줄었고 배포 전 결함 발견도 빨라졌습니다.",
        "partial_q": "불안정한 테스트를 줄이려면 무엇을 보나요?",
        "partial_a": "저는 wait 조건이 중요하다고 생각합니다. 고정 sleep을 줄이고 selector를 안정화한 적이 있습니다. 하지만 네트워크 mocking, 테스트 데이터 격리, retry 정책의 장단점까지 비교하지 못했습니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "API 테스트와 E2E 테스트의 차이는 무엇인가요?",
        "fail_a": "API 테스트는 화면 색상을 보는 테스트이고 E2E는 서버 CPU를 보는 테스트라고 생각합니다. 둘 다 자동화하면 비슷합니다. HTTP status나 사용자 플로우 검증 기준은 아직 모릅니다.",
        "fail_reason": "기술적 팩트가 틀림",
    },
    {
        "job_key": "qa",
        "job": "QA Engineer - 모바일 앱 테스트, 장애 재현, 릴리즈 품질 관리 경험자",
        "good_q": "재현이 어려운 모바일 장애를 분석한 경험이 있나요?",
        "good_a": "일부 Android 기기에서 결제 완료 후 화면이 멈추는 문제가 간헐적으로 발생했습니다. 저는 기기 모델, OS 버전, 네트워크 상태별로 재현 매트릭스를 만들고 로그 수집 빌드를 배포했습니다. 원인이 특정 WebView 버전의 callback 누락임을 확인해 수정했고 재발 건수가 0건이 되었습니다.",
        "partial_q": "릴리즈 품질 기준은 어떻게 정하나요?",
        "partial_a": "저는 치명도 높은 결함이 없어야 릴리즈할 수 있다고 생각합니다. smoke test와 주요 회귀 테스트를 체크합니다. 다만 crash-free rate, 결함 유입률, 고객 영향 범위를 함께 반영한 릴리즈 게이트는 아직 체계화하지 못했습니다.",
        "partial_reason": "이론은 알지만 실무 적용 디테일이 부족함",
        "fail_q": "버그가 재현되지 않으면 어떻게 하나요?",
        "fail_a": "음... 다시 눌러보고, 그래도 안 되면... 일단 개발자에게 물어볼 것 같습니다. 정확히 어떤 로그를 봐야 하는지는 지금 생각이 잘 나지 않습니다.",
        "fail_reason": "당황해서 말을 끝맺지 못함",
    },
]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def word_counts(text):
    return [len(re.findall(r"\S+", sentence)) for sentence in split_sentences(text)]


def is_verbose(text):
    counts = word_counts(text)
    return bool(counts) and sum(1 for count in counts if count > 25) / len(counts) >= 0.3


def cpm_text(cpm):
    if cpm > 350:
        return f"CPM 수치 {cpm}는 350 초과(너무 빠름)"
    if cpm < 200:
        return f"CPM 수치 {cpm}는 200 미만(너무 느림)"
    return f"CPM 수치 {cpm}는 정상 범위"


def star_text(star):
    names = {"S": "Situation", "T": "Task", "A": "Action", "R": "Result"}
    missing = [names[key] for key in ("S", "T", "A", "R") if not star[key]]
    if not missing:
        return "STAR 4요소(Situation, Task, Action, Result) 모두 충족합니다"
    passed = [names[key] for key in ("S", "T", "A", "R") if star[key]]
    return f"STAR 충족 요소는 {', '.join(passed) if passed else '없음'}이며, 부족 요소는 {', '.join(missing)}입니다"


def score_for(question):
    metrics = question["metrics"]
    star = metrics["star_status"]
    missing = sum(1 for key in ("S", "T", "A", "R") if not star[key])
    penalties = int(metrics["cpm"] > 350 or metrics["cpm"] < 200) + int(metrics["dead_air_count"] >= 1) + int(is_verbose(question["answer"]))
    score = max(1, 5 - missing - penalties)
    if not star["A"]:
        score = min(score, 3)
    return score


def top_reason(question, kind):
    metrics = question["metrics"]
    counts = word_counts(question["answer"])
    silence = "3초 이상 침묵이 없습니다" if metrics["dead_air_count"] == 0 else f"3초 이상 침묵이 {metrics['dead_air_count']}회 발생했습니다"
    concision = (
        f"문장별 단어 수({', '.join(map(str, counts))}) 기준으로 만연체에 해당합니다"
        if is_verbose(question["answer"])
        else f"문장별 단어 수({', '.join(map(str, counts))}) 기준으로 만연체는 아닙니다"
    )
    base = f"{cpm_text(metrics['cpm'])}이며, {silence}. {concision}. {star_text(metrics['star_status'])}."
    if kind == "best":
        return base + " 정량 감점이 없고 STAR 기준 충족도가 가장 높아 BEST 답변으로 판단됩니다."
    return base + " 정량 감점과 STAR 누락이 가장 커 WORST 답변으로 판단됩니다."


def make_question(id_, question, answer, kind, index, fail_reason=None):
    if kind == "good":
        cpm, dead, star = 276 + index, 0, STAR_GOOD
    elif kind == "partial":
        cpm, dead, star = 318 + index, 0, STAR_PARTIAL
    else:
        cpm = 182 + index if fail_reason == "당황해서 말을 끝맺지 못함" else 224 + index
        dead = 2 if fail_reason == "당황해서 말을 끝맺지 못함" else 1
        star = STAR_EMPTY if fail_reason in {"기술적 팩트가 틀림", "질문의 의도와 완전히 다른 기술을 설명함"} else STAR_FAIL
    return {"id": id_, "question": question, "answer": answer, "metrics": {"cpm": cpm, "dead_air_count": dead, "star_status": star}}


def bottom_for(question, kind, reason_label):
    if kind == "good":
        return {
            "id": question["id"],
            "question": question["question"],
            "sentences": [{"text": sentence, "rule_id": None, "reason": "정상"} for sentence in split_sentences(question["answer"])],
            "metrics_summary": "CPM 정상, 침묵 0회, STAR 4요소 충족",
            "score": 5,
            "judgement_basis": "정량 감점이 없고 STAR 4요소가 모두 명확합니다.",
        }
    if kind == "partial":
        return {
            "id": question["id"],
            "question": question["question"],
            "sentences": [{"text": sentence, "rule_id": 3 if is_verbose(sentence) else None, "reason": "가독성 저하: 만연체 또는 설명 밀도 과다" if is_verbose(sentence) else "정상"} for sentence in split_sentences(question["answer"])],
            "metrics_summary": f"침묵 0회, STAR 요소 중 Result 부족, {reason_label}",
            "score": 3,
            "judgement_basis": f"Action은 있으나 Result가 부족하고 {reason_label}으로 인해 3점으로 평가됩니다.",
        }
    sentences = []
    for index, sentence in enumerate(split_sentences(question["answer"])):
        if reason_label == "기술적 팩트가 틀림":
            rule_id, reason = 4, "동문서답: 기술적 사실관계가 잘못됨"
        elif reason_label == "질문의 의도와 완전히 다른 기술을 설명함":
            rule_id, reason = 4, "동문서답: 질문과 다른 기술 영역을 설명함"
        elif reason_label == "본인의 역할(Action) 없이 팀의 성과 뒤에 숨음":
            rule_id, reason = 1, "구체성 결여: 본인의 Action 부재"
        elif reason_label == "당황해서 말을 끝맺지 못함":
            rule_id, reason = 4, "동문서답: 답변을 완결하지 못함"
        elif reason_label == "근거 없는 일반론으로 답변함":
            rule_id, reason = 4, "동문서답: 검증 가능한 기술 근거 없이 일반론 제시"
        else:
            rule_id, reason = 4, "동문서답"
        if index == len(split_sentences(question["answer"])) - 1 and index > 0:
            rule_id = None
            reason = "정상"
        sentences.append({"text": sentence, "rule_id": rule_id, "reason": reason})
    return {
        "id": question["id"],
        "question": question["question"],
        "sentences": sentences,
        "metrics_summary": "정량 감점 발생, STAR 요소 중 Task, Action, Result 부족",
        "score": 1,
        "judgement_basis": f"{reason_label}에 해당하며 Action과 Result가 확인되지 않아 낮은 평가를 받았습니다.",
    }


def make_row(case, pattern, index):
    questions_by_kind = {
        "good": make_question(pattern["good"], case["good_q"], case["good_a"], "good", index),
        "partial": make_question(pattern["partial"], case["partial_q"], case["partial_a"], "partial", index),
        "fail": make_question(pattern["fail"], case["fail_q"], case["fail_a"], "fail", index, case["fail_reason"]),
    }
    session = sorted(questions_by_kind.values(), key=lambda item: item["id"])
    scored = [(question, score_for(question)) for question in session]
    best = max(scored, key=lambda item: (item[1], item[0]["metrics"]["cpm"], item[0]["id"]))[0]
    worst = min(scored, key=lambda item: (item[1], -item[0]["metrics"]["cpm"], item[0]["id"]))[0]

    return {
        "instruction": INSTRUCTION,
        "input": {
            "job_description": case["job"],
            "analysis_summary": {
                "best_id": best["id"],
                "best_reason": top_reason(best, "best"),
                "worst_id": worst["id"],
                "worst_reason": top_reason(worst, "worst"),
            },
            "interview_session": session,
        },
        "output": {
            "top_analysis": {
                "best": {"id": best["id"], "reason": top_reason(best, "best")},
                "worst": {"id": worst["id"], "reason": top_reason(worst, "worst")},
            },
            "mid_analysis": [
                {"requirement": case["good_q"].rstrip("?"), "status": "PASS", "analysis": f"{pattern['good']} 답변에서 구체적인 Action과 Result가 확인되어 요구 역량을 충족합니다."},
                {"requirement": case["partial_q"].rstrip("?"), "status": "PARTIAL", "analysis": f"{pattern['partial']} 답변은 관련 Action은 있으나 {case['partial_reason']}."},
                {"requirement": case["fail_q"].rstrip("?"), "status": "FAIL", "analysis": f"{pattern['fail']} 답변은 {case['fail_reason']}에 해당하여 Task, Action, Result를 검증하기 어렵습니다."},
            ],
            "bottom_analysis": [
                bottom_for(questions_by_kind["good"], "good", ""),
                bottom_for(questions_by_kind["partial"], "partial", case["partial_reason"]),
                bottom_for(questions_by_kind["fail"], "fail", case["fail_reason"]),
            ],
        },
    }


rows = [make_row(case, PATTERNS[index % len(PATTERNS)], index) for index, case in enumerate(CASES)]


def validate(rows):
    assert len(rows) == 20
    by_job_key = Counter(case["job_key"] for case in CASES)
    assert len(by_job_key) == 10
    assert all(count == 2 for count in by_job_key.values())
    best_counts = Counter()
    worst_counts = Counter()
    partial_reasons = Counter(case["partial_reason"] for case in CASES)
    fail_reasons = Counter(case["fail_reason"] for case in CASES)
    for row in rows:
        session = row["input"]["interview_session"]
        ids = {question["id"] for question in session}
        assert ids == {"Q1", "Q2", "Q3"}
        best_id = row["output"]["top_analysis"]["best"]["id"]
        worst_id = row["output"]["top_analysis"]["worst"]["id"]
        assert row["input"]["analysis_summary"]["best_id"] == best_id
        assert row["input"]["analysis_summary"]["worst_id"] == worst_id
        best_counts[best_id] += 1
        worst_counts[worst_id] += 1
        statuses = {item["status"] for item in row["output"]["mid_analysis"]}
        assert statuses == {"PASS", "PARTIAL", "FAIL"}
        for item in row["output"]["bottom_analysis"]:
            assert 1 <= item["score"] <= 5
            source = next(question for question in session if question["id"] == item["id"])
            if not source["metrics"]["star_status"]["A"]:
                assert item["score"] <= 3
    assert all(best_counts[qid] >= 5 for qid in ("Q1", "Q2", "Q3"))
    assert all(worst_counts[qid] >= 5 for qid in ("Q1", "Q2", "Q3"))
    assert len(partial_reasons) >= 4
    assert len(fail_reasons) >= 5


validate(rows)
OUTPUT.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
print(f"wrote {OUTPUT} with {len(rows)} rows")
