import json
from collections import Counter
from pathlib import Path

import generate_augmented_batch_1 as base


OUTPUT = Path("augmented_batch_2.jsonl")

base.SOURCE_FILES = [
    "readable_data.jsonl",
    "train_data.jsonl",
    "train_data_mixed.jsonl",
    "sanity_check_10.jsonl",
    "sanity_check_extra_10.jsonl",
    "sanity_check_v3.jsonl",
    "sanity_check_v4.jsonl",
    "augmented_batch_1.jsonl",
]


CASES = [
    {
        "job": "Backend Engineer - Java/Spring 기반 재고 API, 동시성 제어, 이벤트 소싱 경험자",
        "good_q": "재고 차감 로직의 경합 문제를 안정화한 경험이 있나요?",
        "good_a": [
            "플래시 세일 중 동일 상품 재고가 음수로 내려가는 문제가 발생했습니다.",
            "낙관적 락은 재시도 폭증 리스크가 있었음에도 불구하고, 주문 API 응답 안정성을 위해 재고 예약 테이블을 분리하는 방식을 우선순위에 두었습니다.",
            "저는 예약 상태를 먼저 기록하고 결제 성공 이벤트를 받은 뒤 최종 차감되도록 흐름을 바꿨습니다.",
            "이후 음수 재고가 발생하지 않았고 피크 시간 주문 실패율도 1% 미만으로 유지됐습니다.",
        ],
        "good_score": 4,
        "partial_q": "이벤트 소싱을 적용할 때 무엇을 조심하나요?",
        "partial_a": [
            "저는 상태 변경 이력을 남길 수 있다는 점이 장점이라고 봅니다.",
            "주문 상태 변경 이벤트를 append-only로 저장한 경험이 있습니다.",
            "다만 snapshot 생성 주기와 이벤트 replay 시간이 길어질 때의 운영 기준은 명확히 설명하지 못했습니다.",
        ],
        "partial_reason": "snapshot과 replay 운영 기준이 부족함",
        "fail_q": "재고 동기화가 늦어지면 어떻게 처리하나요?",
        "fail_a": [
            "저는 일단 화면에 보이는 재고 수량을 직접 수정해 맞췄습니다.",
            "동기화가 늦는 이유는 나중에 보면 된다고 생각했습니다.",
            "결제 취소, 반품, 예약 만료 같은 예외 케이스는 고려하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Backend Engineer - Python/FastAPI 기반 정산 API, 배치 검증, 외부 연동 경험자",
        "good_q": "외부 정산 파일 불일치를 줄인 경험이 있나요?",
        "good_a": [
            "제휴사 정산 파일과 내부 원장의 금액이 일부 날짜에서 다르게 집계됐습니다.",
            "수동 대사표를 유지하는 방식은 빠르게 시작할 수 있었지만 재발 가능성이 높아, 자동 검증 규칙을 먼저 만들기로 결정했습니다.",
            "저는 거래 ID, 승인 시각, 환불 상태를 기준으로 대사 키를 표준화하고 차이 금액을 배치 리포트로 분리했습니다.",
            "그 결과 월말 정산 검토 시간이 2일에서 반나절로 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "외부 API 장애를 배치에서 어떻게 처리하나요?",
        "partial_a": [
            "저는 timeout과 retry를 분리해야 한다고 생각합니다.",
            "실제로 실패 건을 별도 테이블에 저장해 재처리한 적이 있습니다.",
            "하지만 외부사가 중복 응답을 보내는 경우의 idempotency key 설계는 부족했습니다.",
        ],
        "partial_reason": "외부 중복 응답에 대한 idempotency 설계가 부족함",
        "fail_q": "정산 오류를 발견하면 어떻게 커뮤니케이션하나요?",
        "fail_a": [
            "저는 제가 계산한 값이 맞다고 판단되면 바로 제휴사에 수정 요청을 보냅니다.",
            "회계팀 확인을 기다리면 일정이 늦어질 수 있다고 생각했습니다.",
            "근거 데이터 공유나 승인 절차를 거치지 않아도 된다고 답했습니다.",
        ],
        "fail_reason": "협업 불가능한 독단적 답변",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Frontend Engineer - Next.js, 검색 UI, 서버 컴포넌트 성능 최적화 경험자",
        "good_q": "검색 결과 첫 화면 속도를 개선한 경험이 있나요?",
        "good_a": [
            "검색 결과 페이지에서 필터가 많아 첫 화면 렌더링이 느려졌습니다.",
            "클라이언트에서 모두 조합하면 개발은 쉬웠지만 초기 로딩이 계속 느려지는 한계가 있어, 서버에서 기본 결과를 먼저 구성하는 대안을 도입하기로 결정했습니다.",
            "저는 서버 컴포넌트에서 초기 결과를 내려주고 상호작용 필터만 클라이언트 컴포넌트로 분리했습니다.",
            "배포 후 첫 콘텐츠 표시 시간이 2.9초에서 1.3초로 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "Next.js 캐싱 전략은 어떻게 정하나요?",
        "partial_a": [
            "저는 데이터 변경 주기에 따라 캐시 시간을 나눠야 한다고 생각합니다.",
            "상품 상세처럼 자주 바뀌지 않는 데이터에는 revalidate를 둔 경험이 있습니다.",
            "다만 개인화 결과와 공용 캐시가 섞이는 경우의 보안 위험은 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "개인화 데이터 캐시 보안 고려가 부족함",
        "fail_q": "검색 UI가 느리다는 피드백을 받으면 어떻게 하나요?",
        "fail_a": [
            "저는 디자인을 더 단순하게 바꾸면 대부분 해결된다고 봤습니다.",
            "개발팀에서 성능 지표를 보자고 했지만 체감이 중요하다고 판단해 무시했습니다.",
            "LCP, hydration, API 병목은 확인하지 못했습니다.",
        ],
        "fail_reason": "동료의 피드백을 무시하는 태도",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Frontend Engineer - Angular, RxJS, 대시보드 상태 동기화 경험자",
        "good_q": "RxJS 스트림 과부하를 줄인 경험이 있나요?",
        "good_a": [
            "운영 대시보드에서 필터 입력마다 여러 API가 동시에 호출되어 화면이 자주 멈췄습니다.",
            "즉시 반영을 유지하면 반응성은 좋지만 서버 부하가 커지는 문제가 있어, 사용자 경험을 해치지 않는 선에서 debounce와 distinctUntilChanged를 우선 적용했습니다.",
            "저는 검색 조건 스트림을 합치고 중복 요청을 cancel하도록 switchMap 구조로 바꿨습니다.",
            "그 결과 API 호출 수가 70% 줄었고 입력 지연도 눈에 띄게 감소했습니다.",
        ],
        "good_score": 4,
        "partial_q": "대시보드 권한별 UI 처리는 어떻게 설계하나요?",
        "partial_a": [
            "저는 사용자 권한에 따라 메뉴를 숨기는 방식부터 생각합니다.",
            "route guard를 사용해 접근을 막은 경험도 있습니다.",
            "다만 프론트 숨김 처리와 서버 권한 검증을 함께 설계해야 하는 이유는 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "프론트와 서버 권한 검증 경계 설명이 부족함",
        "fail_q": "Observable 구독 해제는 어떻게 관리하나요?",
        "fail_a": [
            "저는 화면이 사라져도 구독은 그대로 둬도 된다고 생각했습니다.",
            "데이터가 계속 들어오면 최신 상태를 유지할 수 있기 때문입니다.",
            "메모리 누수나 중복 이벤트 발생 가능성은 고려하지 못했습니다.",
        ],
        "fail_reason": "기술 원리에 대한 근거 없는 고집",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "Data Engineer - Snowflake, ELT, 데이터 공유 및 접근 제어 경험자",
        "good_q": "데이터 공유 비용과 보안을 함께 개선한 경험이 있나요?",
        "good_a": [
            "외부 파트너에게 분석 데이터를 제공하면서 별도 복제 테이블 비용이 계속 늘었습니다.",
            "복제를 유지하면 격리는 쉬웠지만 최신성이 떨어지는 문제가 있어, 비용 효율성보다는 접근 통제와 최신성에 무게를 두어 secure view를 적용했습니다.",
            "저는 컬럼 마스킹 정책과 row access policy를 함께 설정해 파트너별 노출 범위를 제한했습니다.",
            "이후 데이터 복제 비용이 줄었고 민감 컬럼 노출 이슈도 발생하지 않았습니다.",
        ],
        "good_score": 5,
        "partial_q": "ELT 모델이 복잡해지면 어떻게 관리하나요?",
        "partial_a": [
            "저는 staging, intermediate, mart 계층을 나눕니다.",
            "공통 변환 로직은 재사용 가능한 모델로 분리한 경험이 있습니다.",
            "다만 모델 owner와 변경 승인 흐름을 데이터 소비자와 어떻게 합의했는지는 설명이 부족했습니다.",
        ],
        "partial_reason": "데이터 소비자와의 변경 관리 합의가 부족함",
        "fail_q": "민감 데이터 요청을 받으면 어떻게 하나요?",
        "fail_a": [
            "분석 속도가 중요하면 우선 전체 테이블을 공유했습니다.",
            "나중에 필요 없는 컬럼을 지우면 된다고 생각했습니다.",
            "마스킹, 최소 권한, 요청 승인 기록은 고려하지 못했습니다.",
        ],
        "fail_reason": "보안 예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Data Engineer - Flink, 실시간 이상 탐지, 스트림 상태 관리 경험자",
        "good_q": "스트림 처리에서 중복 알림을 줄인 경험이 있나요?",
        "good_a": [
            "거래 이상 탐지 파이프라인에서 같은 이벤트가 재처리될 때 알림이 반복 발송됐습니다.",
            "알림 서버에서 중복을 막는 방식은 빠르게 붙일 수 있었지만 원천 이벤트 재처리까지 통제하기 어려워, Flink state 기반 deduplication을 우선 도입했습니다.",
            "저는 event_id와 window를 기준으로 상태 TTL을 두고 exactly-once sink 설정을 함께 점검했습니다.",
            "이후 중복 알림이 85% 감소했고 탐지 지연은 3초 이내로 유지됐습니다.",
        ],
        "good_score": 5,
        "partial_q": "Flink checkpoint 실패는 어떻게 분석하나요?",
        "partial_a": [
            "저는 checkpoint duration과 state size를 먼저 확인합니다.",
            "backpressure가 있는 operator도 같이 봅니다.",
            "다만 savepoint 복구 절차와 state schema 변경 시 호환성 검증은 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "복구 절차와 state 호환성 검증이 부족함",
        "fail_q": "실시간 이상 탐지 규칙을 바꿀 때 무엇을 고려하나요?",
        "fail_a": [
            "저는 임계값을 높이면 오탐이 줄어든다고 생각해 바로 수정했습니다.",
            "분석팀이 샘플 검증을 요청했지만 시간이 없어 생략했습니다.",
            "미탐 증가나 고객 영향도는 별도로 확인하지 않았습니다.",
        ],
        "fail_reason": "동료의 피드백을 무시하는 태도",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "ML Engineer - NLP 분류 모델, active learning, 라벨 품질 개선 경험자",
        "good_q": "라벨 품질이 낮은 데이터로 모델을 개선한 경험이 있나요?",
        "good_a": [
            "고객 문의 분류 모델에서 유사 카테고리 간 오분류가 반복됐습니다.",
            "전체 데이터를 다시 라벨링하는 것은 정확하지만 비용이 컸기 때문에, 불확실성이 높은 샘플부터 active learning으로 재검수하는 방식을 우선했습니다.",
            "저는 confidence가 낮은 샘플과 모델 간 disagreement 샘플을 추출해 라벨러 가이드와 함께 재검수했습니다.",
            "그 결과 macro F1이 0.74에서 0.82로 상승했습니다.",
        ],
        "good_score": 5,
        "partial_q": "텍스트 전처리는 어떻게 결정하나요?",
        "partial_a": [
            "저는 도메인 단어를 보존하는 것이 중요하다고 봅니다.",
            "불용어 제거와 형태소 분석을 비교해 본 경험이 있습니다.",
            "다만 전처리 변경이 특정 클래스 성능을 악화시키는지 class별로 검증한 설명은 부족했습니다.",
        ],
        "partial_reason": "class별 영향 검증이 부족함",
        "fail_q": "모델이 특정 카테고리를 잘 못 맞히면 어떻게 하나요?",
        "fail_a": [
            "저는 해당 카테고리 이름을 더 많이 prompt에 적으면 해결된다고 봤습니다.",
            "왜 틀리는지 보지 않고 문구만 계속 바꿨습니다.",
            "데이터 분포, 라벨 혼동, 평가 샘플은 확인하지 못했습니다.",
        ],
        "fail_reason": "기술적 근거 없는 고집",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "MLOps Engineer - Feature pipeline, 모델 재학습 자동화, 실험 추적 경험자",
        "good_q": "재학습 파이프라인의 재현성을 높인 경험이 있나요?",
        "good_a": [
            "모델 성능 회귀가 발생했지만 어떤 데이터와 코드로 학습했는지 바로 추적하기 어려웠습니다.",
            "단순히 최신 데이터로 다시 학습하면 빠르지만 원인 추적이 불가능한 한계가 있어, 데이터 버전과 실험 메타데이터를 함께 고정하기로 결정했습니다.",
            "저는 feature snapshot ID, git commit, 하이퍼파라미터를 MLflow run에 기록하고 승인된 run만 배포되도록 했습니다.",
            "이후 성능 회귀 발생 시 이전 모델 재현 시간이 하루에서 1시간으로 줄었습니다.",
        ],
        "good_score": 4,
        "partial_q": "Feature pipeline 실패는 어떻게 감지하나요?",
        "partial_a": [
            "저는 row count와 null 비율 변화를 확인합니다.",
            "스케줄 실패 알림도 설정한 경험이 있습니다.",
            "다만 피처 freshness가 모델 성능에 미치는 영향을 경고 기준에 연결하지는 못했습니다.",
        ],
        "partial_reason": "피처 freshness와 모델 품질 연결이 부족함",
        "fail_q": "실험 결과가 좋으면 바로 배포해도 되나요?",
        "fail_a": [
            "offline metric이 좋아지면 바로 배포하는 편이 낫다고 생각했습니다.",
            "검증 절차를 늘리면 속도가 느려져서 의미가 없다고 봤습니다.",
            "online guardrail이나 rollback 기준은 따로 보지 않았습니다.",
        ],
        "fail_reason": "예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Security Engineer - API 보안, 인증 우회 점검, 보안 테스트 자동화 경험자",
        "good_q": "API 인증 우회 취약점을 예방한 경험이 있나요?",
        "good_a": [
            "관리자 API 일부가 프론트 메뉴에서는 숨겨졌지만 직접 호출하면 접근 가능한 문제가 있었습니다.",
            "프론트 라우팅에서 막는 방식은 구현이 쉬웠지만 우회 가능성이 남아, 서버 권한 검증을 공통 미들웨어로 강제하는 것을 우선했습니다.",
            "저는 role과 resource scope를 검증하는 middleware를 추가하고 누락된 endpoint를 테스트로 막았습니다.",
            "그 결과 권한 누락 회귀 테스트가 CI에서 자동으로 검출되도록 개선됐습니다.",
        ],
        "good_score": 5,
        "partial_q": "보안 테스트 자동화는 어디까지 해야 하나요?",
        "partial_a": [
            "저는 반복 가능한 취약점 패턴은 자동화해야 한다고 봅니다.",
            "인증 누락과 기본 입력 검증은 테스트로 만든 경험이 있습니다.",
            "다만 자동화 결과를 개발팀 workflow에 어떻게 녹여 false positive를 줄였는지는 설명이 부족했습니다.",
        ],
        "partial_reason": "개발 workflow와 false positive 관리 설명이 부족함",
        "fail_q": "API 보안 리뷰에서 개발자가 반대하면 어떻게 하나요?",
        "fail_a": [
            "저는 보안 기준이 맞다고 생각하면 개발자 의견은 크게 반영하지 않았습니다.",
            "일정 지연이 생겨도 보안팀 판단을 그대로 적용해야 한다고 답했습니다.",
            "위험도와 대안 설계를 함께 논의하지는 못했습니다.",
        ],
        "fail_reason": "협업 불가능한 독단적 답변",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Security Engineer - 클라우드 침해 대응, 로그 분석, 포렌식 기초 경험자",
        "good_q": "클라우드 계정 탈취 의심 이벤트를 분석한 경험이 있나요?",
        "good_a": [
            "해외 리전에서 평소 없던 AssumeRole 호출이 발생해 계정 탈취가 의심됐습니다.",
            "바로 모든 키를 폐기하면 영향 범위가 컸기 때문에, 안정성을 위해 의심 principal 격리와 증거 보존을 먼저 우선순위에 두었습니다.",
            "저는 CloudTrail, VPC Flow Log, IAM Access Analyzer 결과를 묶어 호출 경로와 영향 리소스를 추적했습니다.",
            "분석 결과 노출된 access key를 확인해 폐기했고 동일 패턴 탐지 룰을 추가했습니다.",
        ],
        "good_score": 5,
        "partial_q": "침해 대응 로그를 보존할 때 무엇을 고려하나요?",
        "partial_a": [
            "저는 원본 로그를 훼손하지 않는 것이 중요하다고 봅니다.",
            "별도 버킷에 복제하고 접근 권한을 제한한 경험이 있습니다.",
            "다만 법적 보존 기간과 타임라인 작성 형식까지는 구체적으로 설명하지 못했습니다.",
        ],
        "partial_reason": "법적 보존 기준과 타임라인 작성 설명이 부족함",
        "fail_q": "의심스러운 접근이 보이면 어떻게 하나요?",
        "fail_a": [
            "저는 우선 로그를 삭제해 공격자가 봤을 흔적을 지우려고 했습니다.",
            "그 다음 비밀번호를 바꾸면 된다고 생각했습니다.",
            "증거 보존이나 영향 범위 분석은 고려하지 못했습니다.",
        ],
        "fail_reason": "침해 대응 예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "Cloud Engineer - GCP GKE, 서비스 메시, 멀티 리전 운영 경험자",
        "good_q": "멀티 리전 장애 전환을 개선한 경험이 있나요?",
        "good_a": [
            "주 리전 장애 시 트래픽 전환은 가능했지만 세션 손실과 DNS 전파 지연이 컸습니다.",
            "DNS TTL만 줄이는 방식은 비용은 낮았지만 복구 시간이 불안정해, 확장성에 무게를 두어 글로벌 로드밸런서 기반 전환을 적용했습니다.",
            "저는 health check 기준을 강화하고 상태 저장 데이터는 리전 간 복제 지연을 모니터링하도록 구성했습니다.",
            "이후 장애 훈련에서 전환 시간이 25분에서 5분 이내로 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "서비스 메시를 도입할 때 무엇을 검토하나요?",
        "partial_a": [
            "저는 mTLS와 트래픽 정책을 중앙에서 관리할 수 있는 점을 봅니다.",
            "canary routing을 적용해 본 경험이 있습니다.",
            "다만 sidecar 리소스 비용과 장애 시 디버깅 복잡도를 충분히 비교하지 못했습니다.",
        ],
        "partial_reason": "운영 비용과 디버깅 복잡도 비교가 부족함",
        "fail_q": "리전 장애가 생기면 어떻게 판단하나요?",
        "fail_a": [
            "저는 클라우드 콘솔이 느리면 바로 전체 서비스를 다른 리전으로 옮기겠다고 답했습니다.",
            "부분 장애인지 네트워크 문제인지는 먼저 보지 않아도 된다고 생각했습니다.",
            "데이터 복제 상태나 rollback 경로는 확인하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스와 원인 분석을 무시함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "DevOps Engineer - GitOps, Helm, 배포 표준화 및 릴리즈 자동화 경험자",
        "good_q": "Helm chart 표준화를 통해 배포 오류를 줄인 경험이 있나요?",
        "good_a": [
            "팀마다 Helm values 구조가 달라 신규 서비스 배포 때 설정 누락이 반복됐습니다.",
            "각 팀 자유도를 유지하면 빠르게 개발할 수 있었지만 운영 검증이 어려워, 공통 chart와 예외 override 구조를 두는 방향으로 결정했습니다.",
            "저는 probe, resource limit, autoscaling 기본값을 chart에 포함하고 values schema 검증을 CI에 추가했습니다.",
            "이후 배포 설정 누락으로 인한 rollback이 절반 이하로 감소했습니다.",
        ],
        "good_score": 5,
        "partial_q": "GitOps 운영에서 drift는 어떻게 다루나요?",
        "partial_a": [
            "저는 클러스터 상태와 Git 상태가 달라지면 알림을 받아야 한다고 생각합니다.",
            "Argo CD sync 상태를 모니터링한 경험이 있습니다.",
            "다만 긴급 수동 변경을 어떤 승인 절차로 다시 Git에 반영할지는 설명이 부족했습니다.",
        ],
        "partial_reason": "긴급 변경의 사후 반영 절차가 부족함",
        "fail_q": "배포가 실패하면 어떻게 해결하나요?",
        "fail_a": [
            "저는 실패한 manifest를 클러스터에서 직접 고쳤습니다.",
            "Git에 반영하면 시간이 오래 걸려서 운영 중에는 직접 수정이 낫다고 봤습니다.",
            "나중에 Git 상태와 달라지는 문제는 크게 고려하지 않았습니다.",
        ],
        "fail_reason": "기술적 근거 없는 고집",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "SRE - 로그 플랫폼, 에러 예산, 장애 감지 자동화 경험자",
        "good_q": "로그 폭증으로 인한 비용과 탐지 품질 문제를 개선한 경험이 있나요?",
        "good_a": [
            "일부 서비스가 debug 로그를 대량 전송해 로그 비용이 급증하고 주요 에러 검색도 느려졌습니다.",
            "전체 로그 보존 기간을 줄이면 비용은 바로 줄지만 사고 분석력이 떨어지는 문제가 있어, 중요도별 샘플링과 보존 정책을 분리했습니다.",
            "저는 에러 로그는 장기 보존하고 반복 debug 로그는 fingerprint 기준으로 샘플링했습니다.",
            "그 결과 월 로그 비용이 35% 감소했고 장애 분석에 필요한 에러 로그는 유지됐습니다.",
        ],
        "good_score": 4,
        "partial_q": "에러 예산을 서비스 팀과 어떻게 공유하나요?",
        "partial_a": [
            "저는 SLO와 burn rate를 대시보드로 보여주는 것이 중요하다고 생각합니다.",
            "주간 회의에서 주요 서비스 지표를 공유한 경험이 있습니다.",
            "다만 배포 중단 기준이나 제품팀과의 의사결정 룰까지 합의한 경험은 부족했습니다.",
        ],
        "partial_reason": "제품팀과의 의사결정 룰 합의가 부족함",
        "fail_q": "장애 알림이 너무 많으면 어떻게 하나요?",
        "fail_a": [
            "저는 시끄러운 알림은 그냥 꺼두는 편이 낫다고 생각했습니다.",
            "중요한 장애면 사용자가 먼저 알려줄 수 있다고 봤습니다.",
            "알림 등급이나 SLO 영향도 기준은 따로 만들지 못했습니다.",
        ],
        "fail_reason": "예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "iOS Developer - Swift Concurrency, 이미지 캐싱, 앱 반응성 개선 경험자",
        "good_q": "이미지 로딩으로 인한 스크롤 끊김을 개선한 경험이 있나요?",
        "good_a": [
            "피드 화면에서 고해상도 이미지가 많아 빠르게 스크롤할 때 프레임 드랍이 발생했습니다.",
            "이미지 품질을 낮추면 즉시 개선되지만 브랜드 요구를 만족하기 어려워, 안정성을 위해 비동기 decoding과 캐시 계층 분리를 우선했습니다.",
            "저는 thumbnail URL을 먼저 로드하고 원본 이미지는 task cancellation을 적용해 화면 밖 요청을 중단했습니다.",
            "그 결과 빠른 스크롤 구간의 프레임 유지율이 크게 개선됐습니다.",
        ],
        "good_score": 5,
        "partial_q": "Swift Concurrency에서 cancellation은 어떻게 다루나요?",
        "partial_a": [
            "저는 화면이 사라지면 작업도 취소되어야 한다고 생각합니다.",
            "Task handle을 보관해 cancel한 경험이 있습니다.",
            "다만 cancellation이 전파되지 않는 하위 작업이나 cleanup 처리까지는 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "취소 전파와 cleanup 처리 설명이 부족함",
        "fail_q": "이미지가 늦게 뜨면 어떻게 처리하나요?",
        "fail_a": [
            "저는 모든 이미지를 앱 시작 시 한 번에 받아두면 된다고 생각했습니다.",
            "초기 로딩이 길어져도 이후 화면은 빠를 것이라고 봤습니다.",
            "메모리 압박이나 네트워크 실패는 고려하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Android Developer - Compose, Paging, 대용량 피드 성능 개선 경험자",
        "good_q": "대용량 피드 화면의 로딩 체감을 개선한 경험이 있나요?",
        "good_a": [
            "콘텐츠 피드에서 첫 페이지 이후 스크롤할 때 빈 화면이 자주 노출됐습니다.",
            "한 번에 많은 데이터를 받아오면 구현은 단순했지만 메모리 사용량이 커져, 사용자 체감 안정성을 위해 Paging prefetch와 placeholder 전략을 적용했습니다.",
            "저는 RemoteMediator로 로컬 캐시를 먼저 보여주고 네트워크 결과를 이어 붙이도록 구성했습니다.",
            "배포 후 빈 화면 노출 비율이 줄었고 피드 체류 시간도 증가했습니다.",
        ],
        "good_score": 5,
        "partial_q": "Paging에서 에러 상태는 어떻게 보여주나요?",
        "partial_a": [
            "저는 로딩과 실패 상태를 분리해 보여줘야 한다고 생각합니다.",
            "append 실패 시 retry 버튼을 넣은 경험이 있습니다.",
            "다만 첫 페이지 실패와 다음 페이지 실패를 UX상 어떻게 다르게 처리할지는 설명이 부족했습니다.",
        ],
        "partial_reason": "에러 상태별 UX 분리 설명이 부족함",
        "fail_q": "피드 성능이 느리면 어떤 결정을 하나요?",
        "fail_a": [
            "저는 기획자에게 콘텐츠 수를 무조건 줄이자고 주장했습니다.",
            "개발 최적화보다 화면을 줄이는 것이 빠르다고 봤습니다.",
            "이미지 크기, recomposition, paging 설정은 확인하지 않았습니다.",
        ],
        "fail_reason": "기술적 근거 없는 고집",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Embedded Engineer - Zephyr RTOS, OTA 업데이트, 센서 게이트웨이 경험자",
        "good_q": "OTA 업데이트 실패율을 낮춘 경험이 있나요?",
        "good_a": [
            "현장 센서 게이트웨이에서 OTA 중 전원이 끊기면 장비가 복구되지 않는 문제가 있었습니다.",
            "업데이트 속도를 높이는 것보다 복구 가능성이 더 중요해, dual bank와 rollback marker를 우선 적용하기로 결정했습니다.",
            "저는 새 이미지 검증 후 boot flag를 전환하고 부팅 성공 신호가 없으면 이전 이미지로 돌아가도록 구현했습니다.",
            "이후 OTA 실패 장비의 현장 회수 건수가 크게 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "저전력 센서에서 sampling 주기는 어떻게 정하나요?",
        "partial_a": [
            "저는 데이터 정확도와 배터리 수명을 같이 봐야 한다고 생각합니다.",
            "정상 구간에서는 sampling 간격을 늘린 경험이 있습니다.",
            "다만 급격한 변화가 생기는 edge case에서 데이터 손실을 어떻게 막을지는 설명이 부족했습니다.",
        ],
        "partial_reason": "edge case 데이터 손실 방지 설명이 부족함",
        "fail_q": "OTA가 실패하면 현장에서 어떻게 복구하나요?",
        "fail_a": [
            "저는 엔지니어가 직접 방문해서 케이블로 다시 굽는 방식이면 충분하다고 봤습니다.",
            "장비 수가 늘어나도 사람이 처리하면 된다고 생각했습니다.",
            "원격 rollback이나 실패 상태 보고는 고려하지 못했습니다.",
        ],
        "fail_reason": "확장성을 고려하지 않은 수동 운영 방식",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "Embedded Linux Engineer - 카메라 드라이버, GStreamer, 영상 처리 파이프라인 경험자",
        "good_q": "영상 프레임 드랍을 줄인 경험이 있나요?",
        "good_a": [
            "산업용 카메라 스트림에서 고해상도 입력 시 프레임 드랍이 발생했습니다.",
            "해상도를 낮추면 쉽게 해결됐지만 검출 정확도가 떨어지는 리스크가 있어, DMA buffer copy를 줄이는 방향을 우선했습니다.",
            "저는 GStreamer pipeline에서 불필요한 colorspace 변환을 제거하고 zero-copy 경로를 적용했습니다.",
            "그 결과 30fps 입력을 안정적으로 유지했고 CPU 사용률도 낮아졌습니다.",
        ],
        "good_score": 4,
        "partial_q": "카메라 드라이버 초기화 문제는 어떻게 분석하나요?",
        "partial_a": [
            "저는 dmesg와 I2C register 값을 먼저 확인합니다.",
            "데이터시트의 power sequence도 비교합니다.",
            "다만 온도나 케이블 길이에 따른 간헐적 실패 재현 조건은 충분히 정리하지 못했습니다.",
        ],
        "partial_reason": "간헐적 실패 재현 조건 정리가 부족함",
        "fail_q": "영상이 끊기면 어떻게 대응하나요?",
        "fail_a": [
            "저는 일단 프로세스를 재시작하고 카메라를 다시 연결했습니다.",
            "현장에서는 그렇게 하면 대부분 다시 보였습니다.",
            "buffer underrun, timestamp drift, pipeline queue 상태는 확인하지 못했습니다.",
        ],
        "fail_reason": "원인을 모르고 재시작만 반복함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Game Server Engineer - 실시간 파티 매칭, 음성 채널, Redis Pub/Sub 경험자",
        "good_q": "파티 매칭 실패율을 낮춘 경험이 있나요?",
        "good_a": [
            "친구 초대 후 파티 매칭에 들어가면 일부 사용자가 다른 방으로 배정되는 문제가 있었습니다.",
            "매칭 큐를 하나로 단순화하면 구현은 쉬웠지만 파티 일관성이 깨질 수 있어, 파티 단위 reservation을 우선 적용했습니다.",
            "저는 파티 ID 기준으로 slot을 예약하고 timeout 시 전체 파티를 같은 상태로 되돌리도록 처리했습니다.",
            "이후 파티 분리 매칭 건수가 사라졌고 매칭 실패 CS도 감소했습니다.",
        ],
        "good_score": 5,
        "partial_q": "Redis Pub/Sub을 사용할 때 어떤 한계를 보나요?",
        "partial_a": [
            "저는 빠르게 메시지를 전달할 수 있다는 점을 장점으로 봅니다.",
            "서버 간 알림 전파에 사용한 경험이 있습니다.",
            "다만 subscriber 장애 시 메시지 유실 가능성과 재처리 전략은 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "메시지 유실과 재처리 전략 설명이 부족함",
        "fail_q": "매칭 로직 의견 충돌이 있으면 어떻게 하나요?",
        "fail_a": [
            "저는 서버에서 결정한 로직이 맞다고 보고 클라이언트 의견은 반영하지 않았습니다.",
            "클라이언트팀이 UX 문제를 말해도 서버 안정성이 우선이라고만 답했습니다.",
            "공통 지표나 실험으로 판단하려는 과정은 없었습니다.",
        ],
        "fail_reason": "동료의 피드백을 무시하는 태도",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Game Client Developer - Unity Addressables, 로딩 최적화, 라이브 업데이트 경험자",
        "good_q": "라이브 업데이트 후 로딩 실패를 줄인 경험이 있나요?",
        "good_a": [
            "이벤트 리소스를 Addressables로 배포한 뒤 일부 국가에서 다운로드 실패가 늘었습니다.",
            "모든 리소스를 앱에 포함하면 실패는 줄지만 앱 용량이 커지는 한계가 있어, CDN fallback과 catalog 검증을 강화하는 대안을 도입했습니다.",
            "저는 catalog hash 불일치 시 fallback CDN으로 전환하고 필수 번들은 사전 검증하도록 로딩 흐름을 바꿨습니다.",
            "그 결과 이벤트 첫날 리소스 로딩 실패율이 4.5%에서 0.6%로 감소했습니다.",
        ],
        "good_score": 5,
        "partial_q": "메모리 누수를 줄일 때 무엇을 확인하나요?",
        "partial_a": [
            "저는 사용하지 않는 asset을 release 하는 것이 중요하다고 봅니다.",
            "Addressables.Release 호출을 점검한 경험이 있습니다.",
            "다만 씬 전환 후 참조가 남는 객체를 profiler snapshot으로 추적하는 과정은 설명이 부족했습니다.",
        ],
        "partial_reason": "profiler 기반 참조 추적 설명이 부족함",
        "fail_q": "로딩 실패가 발생하면 어떻게 처리하나요?",
        "fail_a": [
            "저는 실패 팝업을 띄우지 않고 계속 재시도하도록 만들었습니다.",
            "사용자가 기다리면 언젠가는 받아질 것이라고 생각했습니다.",
            "네트워크 제한, 저장 공간 부족, CDN 장애는 고려하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스를 전혀 고려하지 않은 설계",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "QA Automation Engineer - Playwright, 시각 회귀 테스트, 디자인 시스템 검증 경험자",
        "good_q": "시각 회귀 테스트의 오탐을 줄인 경험이 있나요?",
        "good_a": [
            "디자인 시스템 버튼 변경 후 스냅샷 테스트가 대량 실패해 실제 결함을 구분하기 어려웠습니다.",
            "모든 화면을 pixel 단위로 비교하면 엄격하지만 오탐이 많아, 안정성을 위해 컴포넌트 단위 기준 이미지와 허용 오차를 분리했습니다.",
            "저는 Playwright screenshot 옵션을 고정하고 동적 영역을 mask 처리해 비교 범위를 줄였습니다.",
            "이후 시각 회귀 테스트 실패 중 실제 결함 비율이 높아졌습니다.",
        ],
        "good_score": 5,
        "partial_q": "디자인 시스템 변경은 어떻게 검증하나요?",
        "partial_a": [
            "저는 핵심 컴포넌트별 스토리를 먼저 확인합니다.",
            "버튼, 입력창, 모달은 기본 상태와 disabled 상태를 테스트한 경험이 있습니다.",
            "다만 접근성 속성과 키보드 조작까지 자동 검증하는 범위는 부족했습니다.",
        ],
        "partial_reason": "접근성 자동 검증 범위가 부족함",
        "fail_q": "테스트가 자주 깨지면 어떻게 하나요?",
        "fail_a": [
            "저는 실패하는 테스트를 우선 주석 처리하고 배포가 진행되게 했습니다.",
            "나중에 시간이 나면 다시 보면 된다고 생각했습니다.",
            "불안정 원인이나 품질 게이트 영향은 분석하지 못했습니다.",
        ],
        "fail_reason": "품질 기준을 무시한 임시 대응",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "QA Engineer - IoT 기기 테스트, 현장 로그 수집, 재현 환경 구성 경험자",
        "good_q": "현장에서만 발생하는 IoT 장애를 재현한 경험이 있나요?",
        "good_a": [
            "일부 매장에서 게이트웨이가 새벽 시간대에만 센서 데이터를 누락했습니다.",
            "장비를 전부 회수하면 확실하지만 영업 영향이 커서, 현장 로그 수집과 시간대별 네트워크 조건 재현을 먼저 진행하기로 했습니다.",
            "저는 전원 상태, Wi-Fi RSSI, 센서 송신 주기를 함께 기록하는 진단 빌드를 배포했습니다.",
            "분석 결과 특정 공유기 절전 모드와 충돌하는 조건을 찾아 재현에 성공했습니다.",
        ],
        "good_score": 5,
        "partial_q": "현장 로그는 어떤 기준으로 수집하나요?",
        "partial_a": [
            "저는 장애 시간대와 기기 상태를 함께 남겨야 한다고 생각합니다.",
            "기기 ID와 펌웨어 버전을 기록한 경험이 있습니다.",
            "다만 개인정보가 포함될 수 있는 네트워크 식별자 마스킹 기준은 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "로그 개인정보 마스킹 기준이 부족함",
        "fail_q": "현장 담당자가 재현이 안 된다고 하면 어떻게 하나요?",
        "fail_a": [
            "저는 담당자가 테스트를 제대로 안 한 것이라고 판단했습니다.",
            "제가 작성한 절차가 맞으니 그대로 다시 하라고만 안내했습니다.",
            "환경 차이나 추가 로그 수집 필요성은 고려하지 못했습니다.",
        ],
        "fail_reason": "동료의 피드백을 무시하는 태도",
        "fail_rule": 1,
        "fail_score": 1,
    },
]


def validate_batch(rows):
    assert len(rows) == 20
    existing = base.existing_questions()
    questions = []
    scores = Counter()
    rule_counts = Counter()
    best_counts = Counter()
    worst_counts = Counter()
    fail_reasons = Counter()
    trade_phrases = [
        "리스크가",
        "한계가",
        "무게를 두어",
        "우선순위에",
        "도입하기로 결정",
        "결정했습니다",
        "우선 적용",
        "우선 도입",
        "우선했습니다",
        "먼저 진행하기로",
        "방향으로 결정",
        "안정성을 위해",
    ]
    for row in rows:
        best_id = row["input"]["analysis_summary"]["best_id"]
        worst_id = row["input"]["analysis_summary"]["worst_id"]
        best_counts[best_id] += 1
        worst_counts[worst_id] += 1
        best_answer = next(x["answer"] for x in row["input"]["interview_session"] if x["id"] == best_id)
        assert any(p in best_answer for p in trade_phrases), best_answer
        for session in row["input"]["interview_session"]:
            assert session["question"] not in existing, session["question"]
            questions.append(session["question"])
        for item in row["output"]["bottom_analysis"]:
            scores[item["score"]] += 1
            for sentence in item["sentences"]:
                if sentence["rule_id"] is not None:
                    rule_counts[sentence["rule_id"]] += 1
        fail_analysis = next(m["analysis"] for m in row["output"]["mid_analysis"] if m["status"] == "FAIL")
        fail_reasons[fail_analysis.split(" 답변은 ", 1)[1].split("에 해당", 1)[0]] += 1
    assert len(questions) == len(set(questions))
    assert scores[4] == 4 and scores[2] == 4, scores
    assert scores[5] == 16 and scores[3] == 20 and scores[1] == 16, scores
    assert min(best_counts.values()) >= 6, best_counts
    assert min(worst_counts.values()) >= 6, worst_counts
    assert len(fail_reasons) >= 8, fail_reasons
    assert rule_counts[1] >= 30, rule_counts


def main():
    selected_cases = CASES[:12] + CASES[13:]
    rows = [base.make_row(case, idx) for idx, case in enumerate(selected_cases)]
    validate_batch(rows)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {OUTPUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
