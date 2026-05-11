import json
import re
from collections import Counter
from pathlib import Path


OUTPUT = Path("augmented_batch_1.jsonl")
SOURCE_FILES = [
    "readable_data.jsonl",
    "train_data.jsonl",
    "train_data_mixed.jsonl",
    "sanity_check_10.jsonl",
    "sanity_check_extra_10.jsonl",
    "sanity_check_v3.jsonl",
    "sanity_check_v4.jsonl",
]

INSTRUCTION = (
    "IT 전문 면접관으로서 제공된 문답과 분석 데이터를 바탕으로 상단(BEST/WORST), "
    "중단(Fit-Gap), 하단(평가 스크립트) 보고서를 생성하십시오. 모든 판단은 오직 "
    "[정량 지표], [STAR 기준], [Fit-Gap 기준], [문장 단위 위반 규칙]에 의거해야 합니다."
)

STAR_GOOD = {"S": True, "T": True, "A": True, "R": True}
STAR_PARTIAL = {"S": True, "T": True, "A": True, "R": False}
STAR_FAIL = {"S": True, "T": False, "A": False, "R": False}

PATTERNS = [
    {"good": "Q1", "partial": "Q2", "fail": "Q3"},
    {"good": "Q2", "partial": "Q3", "fail": "Q1"},
    {"good": "Q3", "partial": "Q1", "fail": "Q2"},
    {"good": "Q1", "partial": "Q3", "fail": "Q2"},
    {"good": "Q2", "partial": "Q1", "fail": "Q3"},
    {"good": "Q3", "partial": "Q2", "fail": "Q1"},
    {"good": "Q1", "partial": "Q2", "fail": "Q3"},
    {"good": "Q2", "partial": "Q3", "fail": "Q1"},
    {"good": "Q3", "partial": "Q1", "fail": "Q2"},
    {"good": "Q1", "partial": "Q3", "fail": "Q2"},
    {"good": "Q2", "partial": "Q1", "fail": "Q3"},
    {"good": "Q3", "partial": "Q2", "fail": "Q1"},
    {"good": "Q1", "partial": "Q2", "fail": "Q3"},
    {"good": "Q2", "partial": "Q3", "fail": "Q1"},
    {"good": "Q3", "partial": "Q1", "fail": "Q2"},
    {"good": "Q1", "partial": "Q3", "fail": "Q2"},
    {"good": "Q2", "partial": "Q1", "fail": "Q3"},
    {"good": "Q3", "partial": "Q2", "fail": "Q1"},
    {"good": "Q1", "partial": "Q2", "fail": "Q3"},
    {"good": "Q2", "partial": "Q3", "fail": "Q1"},
]


CASES = [
    {
        "job": "Backend Engineer - Kotlin/Spring 기반 쿠폰 API, 동시성 제어, 이벤트 발행 경험자",
        "good_q": "쿠폰 중복 발급을 줄인 사례를 설명해 주세요.",
        "good_a": [
            "한정 쿠폰 이벤트에서 동시에 요청이 몰려 같은 사용자가 쿠폰을 두 번 받는 문제가 있었습니다.",
            "처음에는 DB unique constraint만 두는 방법과 Redis 분산 락을 쓰는 방법을 비교했고, 이벤트 트래픽이 짧게 몰리는 구조라 Redis 락을 선택했습니다.",
            "저는 사용자 ID와 쿠폰 ID를 조합한 락 키를 만들고 발급 성공 후 이벤트를 비동기로 발행하도록 흐름을 바꿨습니다.",
            "배포 후 중복 발급 건수가 0건으로 줄었고 발급 API 오류율도 0.3% 이하로 유지됐습니다.",
        ],
        "good_score": 5,
        "partial_q": "이벤트 발행 실패를 어떻게 다루나요?",
        "partial_a": [
            "저는 메시지 큐를 쓰면 API 응답과 후속 처리를 분리할 수 있다고 생각합니다.",
            "발행 실패 시 재시도를 넣은 경험도 있습니다.",
            "다만 중복 소비 방지와 dead letter queue 운영 기준은 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "중복 처리와 DLQ 운영 설계가 부족함",
        "fail_q": "동시성 문제가 반복되면 어떻게 대응하나요?",
        "fail_a": [
            "문제가 생기면 담당자가 관리자 화면에서 중복 발급된 쿠폰을 찾아 삭제했습니다.",
            "요청이 많을 때는 여러 명이 나눠서 수동으로 확인했습니다.",
            "락 범위나 트랜잭션 격리 수준은 따로 점검하지 못했습니다.",
        ],
        "fail_reason": "수동으로 하나씩 고치는 비효율적인 방식",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Backend Engineer - Node.js 기반 알림 API, Webhook, 비동기 작업 처리 경험자",
        "good_q": "Webhook 재시도 폭주를 제어한 경험이 있나요?",
        "good_a": [
            "파트너사 장애 때 Webhook 재시도가 한꺼번에 몰려 알림 큐가 지연된 적이 있었습니다.",
            "고정 간격 재시도와 exponential backoff를 비교했고, 파트너 복구 시간을 예측하기 어려워 backoff와 jitter를 선택했습니다.",
            "저는 실패 상태별 재시도 횟수를 분리하고 회로 차단 상태에서는 신규 전송을 지연 큐로 보냈습니다.",
            "이후 큐 적체 시간이 40분에서 6분으로 줄었고 알림 누락도 발생하지 않았습니다.",
        ],
        "good_score": 5,
        "partial_q": "알림 템플릿 변경을 안전하게 배포하려면 무엇을 보나요?",
        "partial_a": [
            "저는 템플릿을 코드와 분리해 관리하는 것이 좋다고 생각합니다.",
            "실제로 관리자 화면에서 문구를 바꾸는 구조를 만든 적이 있습니다.",
            "하지만 승인 절차와 변경 이력 추적, 롤백 권한 설계는 구체적으로 다루지 못했습니다.",
        ],
        "partial_reason": "권한과 변경 이력 관리가 부족함",
        "fail_q": "알림 지연 원인을 어떻게 찾나요?",
        "fail_a": [
            "지연이 생기면 우선 워커 프로세스를 모두 재시작했습니다.",
            "잠시 빨라지면 해결된 것으로 보고 넘어갔습니다.",
            "큐 lag, 외부 API 응답 시간, 실패율을 분리해서 보지는 못했습니다.",
        ],
        "fail_reason": "원인을 모르고 재시작만 반복함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Frontend Engineer - React Native, 오프라인 저장, 모바일 성능 개선 경험자",
        "good_q": "오프라인 상태에서도 앱 기능을 유지한 경험이 있나요?",
        "good_a": [
            "현장 점검 앱에서 지하 구역 진입 시 네트워크가 끊겨 점검 결과가 유실되는 문제가 있었습니다.",
            "모든 요청을 즉시 실패 처리하는 방법과 로컬 큐에 저장하는 방법을 비교했고, 현장 업무 연속성이 더 중요해 로컬 큐 방식을 선택했습니다.",
            "저는 SQLite에 변경 이벤트를 저장하고 네트워크 복구 시 서버와 동기화하도록 충돌 처리 규칙을 추가했습니다.",
            "그 결과 오프라인 점검 데이터 유실이 사라졌고 현장 재입력 시간도 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "모바일 리스트 성능을 개선할 때 무엇을 확인하나요?",
        "partial_a": [
            "저는 렌더링되는 아이템 수를 줄이는 것이 중요하다고 생각합니다.",
            "FlatList windowSize와 keyExtractor를 조정한 경험이 있습니다.",
            "다만 이미지 캐싱, 메모리 사용량, 저사양 기기 측정까지 함께 검증하지는 못했습니다.",
        ],
        "partial_reason": "저사양 기기와 메모리 검증이 부족함",
        "fail_q": "모바일 UI 개선 경험을 설명해 주세요.",
        "fail_a": [
            "저는 예전에 회사 소개 랜딩 페이지의 색상 팔레트를 정리한 경험이 있습니다.",
            "그때 배너와 카드 레이아웃을 예쁘게 바꾸는 데 집중했습니다.",
            "React Native 성능이나 오프라인 저장과 직접 연결되는 경험은 설명하지 못했습니다.",
        ],
        "fail_reason": "직무 공고와 상관없는 엉뚱한 경험을 강조함",
        "fail_rule": 2,
        "fail_score": 1,
    },
    {
        "job": "Frontend Engineer - Vue 3, Pinia, 실시간 대시보드 개발 경험자",
        "good_q": "실시간 대시보드 렌더링 부하를 줄인 경험이 있나요?",
        "good_a": [
            "운영 대시보드에서 초당 수백 건의 이벤트가 들어오며 차트가 끊기는 문제가 있었습니다.",
            "모든 이벤트를 즉시 반영하는 방식과 일정 간격으로 묶어 반영하는 방식을 비교했고, 실시간성보다 화면 안정성이 중요해 배치 업데이트를 선택했습니다.",
            "저는 WebSocket 메시지를 버퍼링하고 Pinia 상태 갱신을 1초 단위로 합쳐 처리했습니다.",
            "배포 후 프레임 드랍이 크게 줄었고 운영자가 알림을 놓치는 사례도 감소했습니다.",
        ],
        "good_score": 4,
        "partial_q": "Pinia store를 나눌 때 어떤 기준을 쓰나요?",
        "partial_a": [
            "저는 도메인 기준으로 store를 나누는 편입니다.",
            "화면 상태와 서버 응답 상태도 분리하려고 합니다.",
            "하지만 store 간 의존성이 커졌을 때 순환 참조를 어떻게 막을지는 구체적으로 설명하지 못했습니다.",
        ],
        "partial_reason": "상태 모듈 간 의존성 관리가 부족함",
        "fail_q": "차트가 느려지면 어떻게 대응하나요?",
        "fail_a": [
            "저는 사용자에게 브라우저를 새로고침하라고 안내했습니다.",
            "그래도 느리면 차트 컴포넌트를 다시 mount 하도록 처리했습니다.",
            "데이터 샘플링이나 렌더링 빈도 조정은 깊게 보지 못했습니다.",
        ],
        "fail_reason": "원인 분석 없이 화면 재생성만 반복함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Data Engineer - BigQuery, dbt, 비용 최적화 및 데이터 품질 관리 경험자",
        "good_q": "분석 쿼리 비용을 줄인 경험이 있나요?",
        "good_a": [
            "마케팅 리포트 쿼리가 매일 전체 이벤트 테이블을 스캔해 월 비용이 급증했습니다.",
            "집계 테이블을 새로 만드는 방법과 파티션 필터를 강제하는 방법을 비교했고, 리포트 패턴이 고정되어 집계 테이블을 선택했습니다.",
            "저는 dbt incremental model을 만들고 날짜 파티션과 cluster key를 함께 적용했습니다.",
            "그 결과 월 쿼리 비용이 58% 감소했고 리포트 생성 시간도 20분에서 4분으로 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "데이터 품질 이상을 어떻게 감지하나요?",
        "partial_a": [
            "저는 null 비율과 row count 변화를 먼저 봅니다.",
            "dbt test로 unique와 not null 조건을 검증한 경험이 있습니다.",
            "다만 계절성 있는 지표나 지연 적재를 고려한 동적 임계값은 설계하지 못했습니다.",
        ],
        "partial_reason": "동적 임계값과 지연 적재 고려가 부족함",
        "fail_q": "비용이 갑자기 늘면 무엇을 확인하나요?",
        "fail_a": [
            "비용이 늘면 일단 큰 테이블을 몇 개 삭제해서 공간을 줄였습니다.",
            "필요하면 다시 만들 수 있다고 생각했습니다.",
            "쿼리 스캔량, 예약 슬롯, 파티션 누락 여부는 확인하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스와 원인 분석을 무시함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Data Engineer - Kafka Connect, CDC, 데이터 동기화 파이프라인 경험자",
        "good_q": "CDC 동기화 지연을 줄인 사례가 있나요?",
        "good_a": [
            "주문 CDC 파이프라인에서 피크 시간대 sink 반영이 15분 이상 늦어졌습니다.",
            "connector task 수를 늘리는 방법과 sink batch 크기를 조정하는 방법을 비교했고, DB 부하를 급격히 늘리지 않기 위해 batch 튜닝을 먼저 선택했습니다.",
            "저는 topic별 처리량을 분리하고 sink connector의 flush size와 retry 정책을 조정했습니다.",
            "이후 평균 반영 지연이 2분 이하로 낮아졌고 재처리 실패도 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "스키마 변경이 생기면 어떻게 대응하나요?",
        "partial_a": [
            "저는 schema registry로 호환성을 확인해야 한다고 생각합니다.",
            "필드 추가나 nullable 변경은 비교적 안전하게 처리한 경험이 있습니다.",
            "하지만 breaking change가 필요한 경우 소비자 팀과 마이그레이션 일정을 어떻게 조율했는지는 설명이 부족했습니다.",
        ],
        "partial_reason": "소비자 팀과의 협업 계획 설명이 부족함",
        "fail_q": "동기화 오류가 반복되면 어떻게 하나요?",
        "fail_a": [
            "오류가 난 레코드는 제가 직접 export해서 대상 DB에 넣었습니다.",
            "건수가 많아지면 엑셀로 나눠서 처리했습니다.",
            "offset 재처리나 poison pill 격리 방식은 적용하지 못했습니다.",
        ],
        "fail_reason": "수동으로 하나씩 고치는 비효율적인 방식",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "MLOps Engineer - Kubernetes 모델 서빙, canary 배포, 모델 모니터링 경험자",
        "good_q": "모델 서빙 배포 위험을 줄인 경험이 있나요?",
        "good_a": [
            "추천 모델 신규 버전 배포 후 일부 세그먼트에서 응답 시간이 늘어날 가능성이 있었습니다.",
            "전체 교체 배포와 canary 배포를 비교했고, 품질과 latency를 동시에 확인해야 해서 canary 방식을 선택했습니다.",
            "저는 5% 트래픽부터 시작해 p95 latency와 클릭률을 함께 모니터링하고 임계치 초과 시 자동 롤백되도록 구성했습니다.",
            "배포 중 이상 징후를 한 번 감지해 자동 롤백했고 전체 장애로 확산되지 않았습니다.",
        ],
        "good_score": 5,
        "partial_q": "모델 drift를 어떻게 감지하나요?",
        "partial_a": [
            "저는 입력 피처 분포와 예측 confidence 변화를 봅니다.",
            "PSI 같은 지표도 실험해 본 적이 있습니다.",
            "다만 drift가 실제 비즈니스 품질 저하로 이어지는지 연결하는 기준은 충분히 세우지 못했습니다.",
        ],
        "partial_reason": "모니터링 지표와 비즈니스 영향 연결이 부족함",
        "fail_q": "모델 성능이 떨어지면 어떻게 대응하나요?",
        "fail_a": [
            "성능이 떨어지면 인터넷에서 비슷한 모델 설정을 찾아 그대로 적용했습니다.",
            "learning rate와 batch size도 블로그 예시 값을 먼저 복사했습니다.",
            "검증 세트나 데이터 분포 변화는 확인하지 못했습니다.",
        ],
        "fail_reason": "기술의 원리 없이 블로그 설정을 복사해서 씀",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "ML Engineer - 검색 랭킹 모델, 피처 실험, 온라인 A/B 테스트 경험자",
        "good_q": "검색 랭킹 품질을 개선한 경험이 있나요?",
        "good_a": [
            "상품 검색에서 인기 상품만 상위에 노출되어 신규 상품 클릭률이 낮았습니다.",
            "인기도 가중치를 낮추는 방법과 신선도 피처를 추가하는 방법을 비교했고, 기존 품질을 크게 흔들지 않기 위해 신선도 피처 추가를 선택했습니다.",
            "저는 최근 등록일과 카테고리 내 전환율을 피처로 추가하고 A/B 테스트를 진행했습니다.",
            "실험 결과 신규 상품 CTR이 11% 상승했고 전체 전환율은 유지됐습니다.",
        ],
        "good_score": 4,
        "partial_q": "온라인 실험을 설계할 때 무엇을 조심하나요?",
        "partial_a": [
            "저는 대조군과 실험군을 분리하는 것이 중요하다고 생각합니다.",
            "주요 지표와 보조 지표도 함께 봐야 합니다.",
            "하지만 실험 중복, novelty effect, 조기 종료 기준까지는 구체적으로 설계하지 못했습니다.",
        ],
        "partial_reason": "실험 편향과 종료 기준 설계가 부족함",
        "fail_q": "검색 품질 개선 경험을 말해 주세요.",
        "fail_a": [
            "저는 예전에 사내 행사 포스터 디자인을 개선한 경험이 있습니다.",
            "사람들이 보기 좋다고 해서 검색 화면도 예뻐야 한다고 생각했습니다.",
            "랭킹 모델이나 검색 피처 개선 경험은 설명하지 못했습니다.",
        ],
        "fail_reason": "직무 공고와 상관없는 엉뚱한 경험을 강조함",
        "fail_rule": 2,
        "fail_score": 1,
    },
    {
        "job": "Security Engineer - IAM 정책, 감사 대응, 권한 자동화 경험자",
        "good_q": "과도한 권한을 줄이면서 운영 영향을 낮춘 경험이 있나요?",
        "good_a": [
            "여러 서비스 계정에 관리자 권한이 남아 있어 감사 지적을 받은 적이 있었습니다.",
            "권한을 한 번에 제거하는 방법과 사용 로그를 보고 단계적으로 줄이는 방법을 비교했고, 배포 장애를 피하기 위해 단계적 축소를 선택했습니다.",
            "저는 CloudTrail 로그를 분석해 실제 사용 권한만 남기고 Terraform 모듈로 정책을 재배포했습니다.",
            "그 결과 고위험 권한이 76% 줄었고 권한 제거로 인한 장애는 발생하지 않았습니다.",
        ],
        "good_score": 5,
        "partial_q": "감사 요청 자료를 준비할 때 무엇을 확인하나요?",
        "partial_a": [
            "저는 접근 권한 목록과 변경 이력을 먼저 확인합니다.",
            "계정별 책임자도 같이 정리합니다.",
            "다만 예외 승인 근거와 만료일, 재검토 주기를 정책으로 연결하는 설명은 부족했습니다.",
        ],
        "partial_reason": "예외 승인과 재검토 주기 관리가 부족함",
        "fail_q": "권한 변경이 필요하면 어떻게 처리하나요?",
        "fail_a": [
            "저는 빠른 처리를 위해 요청자에게 필요한 권한을 넓게 부여했습니다.",
            "보안팀 검토를 기다리면 일이 늦어진다고 생각했습니다.",
            "최소 권한이나 승인 기록은 나중에 정리해도 된다고 답했습니다.",
        ],
        "fail_reason": "협업 불가능한 독단적 답변",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Cloud Engineer - AWS ECS, ALB, 오토스케일링 및 비용 관리 경험자",
        "good_q": "트래픽 급증에 맞춰 오토스케일링을 개선한 경험이 있나요?",
        "good_a": [
            "라이브 커머스 시작 직후 ECS 서비스 CPU가 급등해 결제 진입이 느려졌습니다.",
            "CPU 기준 스케일링과 요청 수 기준 스케일링을 비교했고, 짧은 피크를 더 빨리 감지하기 위해 ALB request count 기준을 선택했습니다.",
            "저는 target tracking 정책을 조정하고 warm task 수를 예약 스케일링으로 미리 확보했습니다.",
            "이후 피크 시간 p95 응답 시간이 1.4초에서 480ms로 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "클라우드 비용을 줄일 때 어떤 순서로 보나요?",
        "partial_a": [
            "저는 사용률이 낮은 리소스부터 확인합니다.",
            "예약 인스턴스와 스토리지 수명 주기도 검토합니다.",
            "다만 비용 절감이 장애 대응 여유 용량을 얼마나 줄이는지 위험 평가를 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "비용 절감과 가용성 trade-off 설명이 부족함",
        "fail_q": "ECS 서비스가 불안정하면 어떻게 하나요?",
        "fail_a": [
            "저는 문제가 생기면 desired count를 크게 올렸습니다.",
            "그래도 장애가 나면 더 큰 인스턴스로 바꿨습니다.",
            "헬스체크 실패 원인이나 배포 중 task 교체 흐름은 확인하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스와 원인 분석을 무시함",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "SRE - Prometheus, SLO, 장애 자동화 및 온콜 운영 경험자",
        "good_q": "온콜 알림 피로도를 줄인 경험이 있나요?",
        "good_a": [
            "검색 서비스 온콜에서 야간 경고가 많아 실제 장애 대응 속도가 늦어졌습니다.",
            "알림 임계값을 단순히 높이는 방법과 SLO burn rate를 적용하는 방법을 비교했고, 장애 영향도를 반영하기 위해 burn rate 알림을 선택했습니다.",
            "저는 Prometheus rule을 재작성하고 에러 예산 소진 속도별로 알림 채널을 분리했습니다.",
            "그 결과 야간 오탐 알림이 62% 줄었고 실제 장애 감지 시간은 유지됐습니다.",
        ],
        "good_score": 5,
        "partial_q": "장애 회고 액션 아이템은 어떻게 관리하나요?",
        "partial_a": [
            "저는 타임라인과 원인 후보를 정리합니다.",
            "액션 아이템 담당자도 회고 문서에 남깁니다.",
            "하지만 완료율, 재발률, 감지 시간 개선처럼 후속 지표로 추적하는 체계는 부족했습니다.",
        ],
        "partial_reason": "회고 후속 지표 관리가 부족함",
        "fail_q": "장애 대응 중 의견이 갈리면 어떻게 하나요?",
        "fail_a": [
            "장애 상황에서는 제가 판단한 방법을 먼저 밀어붙이는 편입니다.",
            "회의가 길어지면 시간이 낭비되므로 다른 의견은 나중에 듣습니다.",
            "incident commander나 역할 분담 체계는 따로 따르지 않았습니다.",
        ],
        "fail_reason": "협업 불가능한 독단적 답변",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Platform Engineer - Kubernetes 개발자 플랫폼, 배포 셀프서비스, 관측성 경험자",
        "good_q": "개발자 배포 대기 시간을 줄인 경험이 있나요?",
        "good_a": [
            "사내 서비스 배포가 운영팀 티켓으로만 처리되어 평균 하루 이상 대기했습니다.",
            "운영팀 승인 절차를 유지하는 방법과 셀프서비스 배포를 제공하는 방법을 비교했고, 반복 배포가 많은 팀부터 셀프서비스를 적용하는 방식을 선택했습니다.",
            "저는 Argo CD 템플릿과 namespace quota를 표준화하고 배포 권한을 서비스 단위로 분리했습니다.",
            "이후 배포 대기 시간이 1일에서 20분 이하로 줄었습니다.",
        ],
        "good_score": 4,
        "partial_q": "플랫폼 사용성을 개선할 때 무엇을 보나요?",
        "partial_a": [
            "저는 개발자가 자주 막히는 지점을 먼저 봅니다.",
            "문서와 예제 템플릿을 제공한 경험이 있습니다.",
            "다만 실제 사용자 인터뷰나 사용 로그 기반으로 우선순위를 정한 과정은 부족했습니다.",
        ],
        "partial_reason": "사용자 피드백 기반 우선순위 설명이 부족함",
        "fail_q": "관측성 플랫폼 경험을 말해 주세요.",
        "fail_a": [
            "저는 예전에 팀 소개용 Notion 페이지를 보기 좋게 정리했습니다.",
            "문서가 깔끔하면 사람들이 시스템을 잘 이해한다고 생각합니다.",
            "로그, 메트릭, 트레이스 운영 경험과는 직접 연결하지 못했습니다.",
        ],
        "fail_reason": "직무 공고와 상관없는 엉뚱한 경험을 강조함",
        "fail_rule": 2,
        "fail_score": 1,
    },
    {
        "job": "iOS Developer - SwiftUI, Combine, 앱 결제 및 크래시 개선 경험자",
        "good_q": "비동기 결제 흐름에서 크래시를 줄인 경험이 있나요?",
        "good_a": [
            "구독 결제 완료 콜백 이후 특정 화면에서 앱이 종료되는 문제가 있었습니다.",
            "콜백을 화면 생명주기에 묶는 방법과 결제 상태를 별도 store로 분리하는 방법을 비교했고, 재진입 안정성을 위해 store 분리를 선택했습니다.",
            "저는 Combine subscription의 weak self 처리와 상태 검증 로직을 추가했습니다.",
            "해당 화면 크래시율은 0.6%에서 0.05%로 낮아졌습니다.",
        ],
        "good_score": 5,
        "partial_q": "SwiftUI에서 상태 객체를 나눌 때 무엇을 보나요?",
        "partial_a": [
            "저는 화면 소유 상태와 공유 상태를 나눠야 한다고 생각합니다.",
            "StateObject와 ObservedObject를 구분해 사용한 경험이 있습니다.",
            "다만 복잡한 화면 전환에서 상태가 해제되는 시점과 메모리 검증 과정은 자세히 설명하지 못했습니다.",
        ],
        "partial_reason": "상태 생명주기와 메모리 검증이 부족함",
        "fail_q": "메모리 누수가 의심되면 어떻게 확인하나요?",
        "fail_a": [
            "앱이 느려지면 우선 앱을 종료했다가 다시 실행했습니다.",
            "사용자에게도 재실행하면 괜찮아진다고 안내했습니다.",
            "Instruments나 retain cycle 분석은 해보지 못했습니다.",
        ],
        "fail_reason": "원인을 모르고 재시작만 반복함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Android Developer - Kotlin, Coroutines, 앱 네트워크 안정성 개선 경험자",
        "good_q": "네트워크 오류가 많은 화면을 안정화한 경험이 있나요?",
        "good_a": [
            "배송 추적 화면에서 지하철 이동 중 API timeout이 자주 발생해 사용자가 빈 화면을 봤습니다.",
            "무조건 재시도하는 방법과 캐시된 마지막 상태를 보여주는 방법을 비교했고, 사용자 혼란을 줄이기 위해 stale cache 표시를 선택했습니다.",
            "저는 timeout별 retry 정책을 분리하고 마지막 성공 응답을 Room에 저장해 상태 배지를 함께 노출했습니다.",
            "배포 후 빈 화면 노출 비율이 9%에서 1%대로 감소했습니다.",
        ],
        "good_score": 5,
        "partial_q": "Coroutine scope를 정할 때 무엇을 고려하나요?",
        "partial_a": [
            "저는 화면 생명주기에 맞춰 scope를 잡아야 한다고 생각합니다.",
            "viewModelScope와 lifecycleScope를 구분해서 사용한 경험이 있습니다.",
            "다만 취소 전파, supervisorScope, 예외 핸들링 차이는 실제 사례로 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "예외 처리와 취소 전파 설명이 부족함",
        "fail_q": "API 오류가 간헐적으로 나면 어떻게 하나요?",
        "fail_a": [
            "저는 실패하면 무조건 while문으로 성공할 때까지 다시 호출했습니다.",
            "사용자가 기다리면 언젠가는 성공한다고 생각했습니다.",
            "backoff, timeout, 사용자 취소 처리는 고려하지 못했습니다.",
        ],
        "fail_reason": "예외 케이스를 무시한 재시도 방식",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "Embedded Engineer - FreeRTOS, BLE 센서, 저전력 펌웨어 경험자",
        "good_q": "센서 장치의 배터리 소모를 줄인 경험이 있나요?",
        "good_a": [
            "BLE 온도 센서가 목표 사용 시간보다 빨리 방전되는 문제가 있었습니다.",
            "광고 주기를 늘리는 방법과 센서 샘플링을 이벤트 기반으로 바꾸는 방법을 비교했고, 데이터 품질을 유지하기 위해 샘플링 조건 최적화를 선택했습니다.",
            "저는 wake-up 조건을 세분화하고 idle task에서 sleep mode 진입을 명확히 분리했습니다.",
            "평균 배터리 지속 시간이 22시간에서 49시간으로 늘었습니다.",
        ],
        "good_score": 5,
        "partial_q": "RTOS task 간 통신은 어떻게 설계하나요?",
        "partial_a": [
            "저는 queue를 사용해 task 사이 데이터를 전달합니다.",
            "센서 task와 통신 task를 분리한 경험이 있습니다.",
            "다만 queue overflow, priority inversion, timeout 처리 기준은 충분히 설명하지 못했습니다.",
        ],
        "partial_reason": "예외 상황과 우선순위 역전 고려가 부족함",
        "fail_q": "BLE 연결이 자주 끊기면 어떻게 하나요?",
        "fail_a": [
            "끊김이 생기면 장치를 재부팅해서 다시 연결했습니다.",
            "필드에서도 전원을 껐다 켜면 대부분 연결됐습니다.",
            "connection interval, RSSI, 전원 노이즈는 따로 보지 못했습니다.",
        ],
        "fail_reason": "원인을 모르고 재시작만 반복함",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Game Client Developer - Unreal Engine, 렌더링 최적화, 메모리 관리 경험자",
        "good_q": "Unreal 프로젝트에서 메모리 사용량을 줄인 경험이 있나요?",
        "good_a": [
            "오픈월드 맵 진입 시 텍스처 로딩이 몰려 메모리 사용량이 급증했습니다.",
            "전체 텍스처 품질을 낮추는 방법과 스트리밍 설정을 조정하는 방법을 비교했고, 시각 품질을 유지하기 위해 스트리밍 튜닝을 선택했습니다.",
            "저는 texture group별 LOD bias를 조정하고 사용하지 않는 asset reference를 제거했습니다.",
            "그 결과 피크 메모리가 1.8GB에서 1.2GB로 줄었습니다.",
        ],
        "good_score": 4,
        "partial_q": "프레임 드랍을 분석할 때 어떤 지표를 보나요?",
        "partial_a": [
            "저는 game thread와 render thread 시간을 먼저 봅니다.",
            "stat unit과 profiler를 사용한 경험이 있습니다.",
            "다만 GPU 병목과 CPU 병목이 섞인 상황에서 원인을 분리하는 과정은 설명이 부족했습니다.",
        ],
        "partial_reason": "복합 병목 분리 설명이 부족함",
        "fail_q": "렌더링 성능을 높이려면 어떻게 하나요?",
        "fail_a": [
            "저는 일단 화면 효과를 전부 끄고 밝기를 낮췄습니다.",
            "프레임이 올라가면 그대로 출시해도 된다고 생각했습니다.",
            "draw call, overdraw, shader cost를 구분해서 보지는 못했습니다.",
        ],
        "fail_reason": "기술 원리를 이해하지 못한 단순 축소 접근",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "Game Server Engineer - WebSocket, 매치 서버, Redis 기반 상태 동기화 경험자",
        "good_q": "플레이어 상태 동기화 지연을 줄인 경험이 있나요?",
        "good_a": [
            "실시간 협동 모드에서 플레이어 위치 상태가 늦게 반영되어 충돌 판정이 어긋났습니다.",
            "모든 상태를 즉시 broadcast하는 방법과 중요 이벤트만 우선 전송하는 방법을 비교했고, 대역폭을 줄이기 위해 이벤트 우선순위 방식을 선택했습니다.",
            "저는 위치 업데이트를 샘플링하고 공격 판정 이벤트는 별도 채널로 분리했습니다.",
            "이후 평균 동기화 지연이 120ms에서 45ms로 줄었습니다.",
        ],
        "good_score": 5,
        "partial_q": "매치 서버 장애 시 세션을 어떻게 복구하나요?",
        "partial_a": [
            "저는 Redis에 세션 상태를 저장해 복구할 수 있다고 생각합니다.",
            "방 ID와 플레이어 목록을 TTL과 함께 관리한 경험이 있습니다.",
            "다만 중복 접속, 재접속 순서, 이미 종료된 방 처리 같은 예외 케이스 설명은 부족했습니다.",
        ],
        "partial_reason": "재접속 예외 케이스 처리가 부족함",
        "fail_q": "게임 서버 장애가 나면 팀과 어떻게 일하나요?",
        "fail_a": [
            "장애가 나면 제가 판단해서 바로 서버 설정을 바꿉니다.",
            "다른 팀과 논의하면 대응이 늦어지기 때문에 먼저 적용하는 편입니다.",
            "변경 기록이나 롤백 공유는 나중에 하면 된다고 생각했습니다.",
        ],
        "fail_reason": "협업 불가능한 독단적 답변",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "QA Automation Engineer - Cypress, 계약 테스트, 배포 품질 게이트 경험자",
        "good_q": "프론트와 백엔드 간 계약 불일치를 줄인 경험이 있나요?",
        "good_a": [
            "배포 후 API 응답 필드명이 바뀌어 프론트 화면이 깨지는 일이 반복됐습니다.",
            "E2E 테스트만 늘리는 방법과 계약 테스트를 추가하는 방법을 비교했고, 원인을 더 빠르게 잡기 위해 계약 테스트를 선택했습니다.",
            "저는 OpenAPI 스펙 기반 검증을 CI에 넣고 breaking change가 있으면 배포를 막도록 구성했습니다.",
            "이후 응답 스키마 변경으로 인한 운영 장애가 발생하지 않았습니다.",
        ],
        "good_score": 5,
        "partial_q": "품질 게이트 기준은 어떻게 정하나요?",
        "partial_a": [
            "저는 smoke test 통과 여부와 치명 결함 수를 봅니다.",
            "배포 전 자동 테스트 결과도 확인합니다.",
            "다만 flaky test를 게이트에서 어떻게 제외하거나 격리할지 기준은 명확히 세우지 못했습니다.",
        ],
        "partial_reason": "flaky test 격리 기준이 부족함",
        "fail_q": "자동화 테스트 경험을 설명해 주세요.",
        "fail_a": [
            "저는 예전에 고객 설문 결과를 엑셀로 정리한 경험이 있습니다.",
            "체크리스트를 꼼꼼히 만들었기 때문에 자동화도 잘할 수 있다고 생각합니다.",
            "Cypress나 API 계약 테스트 경험은 구체적으로 설명하지 못했습니다.",
        ],
        "fail_reason": "직무 공고와 상관없는 엉뚱한 경험을 강조함",
        "fail_rule": 2,
        "fail_score": 1,
    },
    {
        "job": "QA Engineer - 결제 도메인 테스트, 장애 재현, 릴리즈 리스크 평가 경험자",
        "good_q": "간헐적인 결제 실패를 재현한 경험이 있나요?",
        "good_a": [
            "특정 카드사 결제에서 간헐적으로 승인 후 화면이 멈추는 신고가 있었습니다.",
            "전체 결제 플로우를 반복하는 방법과 카드사별 조건을 좁히는 방법을 비교했고, 재현 시간을 줄이기 위해 조건 매트릭스를 선택했습니다.",
            "저는 카드사, OS 버전, 네트워크 상태를 조합해 테스트하고 로그 수집 빌드로 callback 누락을 확인했습니다.",
            "수정 후 동일 조건 재현 테스트에서 실패 건수가 0건이 되었습니다.",
        ],
        "good_score": 5,
        "partial_q": "릴리즈 리스크는 어떻게 판단하나요?",
        "partial_a": [
            "저는 치명도와 영향 범위를 기준으로 봅니다.",
            "결제와 로그인은 더 엄격하게 확인합니다.",
            "다만 사업 일정 압박이 있을 때 어떤 기준으로 릴리즈 보류를 설득했는지는 설명이 부족했습니다.",
        ],
        "partial_reason": "이해관계자 설득 과정 설명이 부족함",
        "fail_q": "버그 리포트를 어떻게 작성하나요?",
        "fail_a": [
            "저는 개발자가 보면 알 것 같아서 화면 캡처만 전달했습니다.",
            "재현 단계는 길게 쓰지 않아도 된다고 생각했습니다.",
            "환경 정보와 기대 결과, 실제 결과를 구분해 적지는 못했습니다.",
        ],
        "fail_reason": "예외 케이스와 재현 정보 수집을 무시함",
        "fail_rule": 1,
        "fail_score": 2,
    },
    {
        "job": "Data Analyst - 제품 지표 분석, SQL, 실험 결과 해석 경험자",
        "good_q": "제품 전환율 하락 원인을 분석한 경험이 있나요?",
        "good_a": [
            "가입 퍼널의 최종 전환율이 일주일 사이 6%p 떨어진 적이 있었습니다.",
            "전체 트래픽 추이를 먼저 보는 방법과 단계별 퍼널을 쪼개는 방법을 비교했고, 원인 구간을 좁히기 위해 퍼널 분해를 선택했습니다.",
            "저는 디바이스와 유입 채널별 전환율을 나눠 보고 특정 Android 버전에서 SMS 인증 실패가 늘어난 것을 찾았습니다.",
            "수정 후 해당 구간 전환율이 이전 수준으로 회복됐습니다.",
        ],
        "good_score": 5,
        "partial_q": "실험 결과가 애매하면 어떻게 해석하나요?",
        "partial_a": [
            "저는 p-value와 효과 크기를 함께 보려고 합니다.",
            "주요 지표가 움직이지 않으면 보조 지표도 확인합니다.",
            "다만 표본 수 부족, 다중 비교, 세그먼트별 해석 위험을 충분히 통제하지 못했습니다.",
        ],
        "partial_reason": "통계적 해석 위험 통제가 부족함",
        "fail_q": "SQL 분석 경험을 말해 주세요.",
        "fail_a": [
            "저는 SQL을 실행해서 나온 숫자가 맞다고 보면 된다고 생각했습니다.",
            "결과가 이상하면 where 조건을 몇 개 빼보며 숫자가 맞아 보일 때까지 고쳤습니다.",
            "join 기준이나 중복 row 발생 여부는 확인하지 못했습니다.",
        ],
        "fail_reason": "기술 원리를 이해하지 못한 임의 조정",
        "fail_rule": 1,
        "fail_score": 1,
    },
    {
        "job": "Product Security Engineer - 보안 리뷰 자동화, 위협 모델링, 개발 보안 교육 경험자",
        "good_q": "보안 리뷰 병목을 줄인 경험이 있나요?",
        "good_a": [
            "신규 기능 출시 전 보안 리뷰 요청이 몰려 개발 일정이 지연됐습니다.",
            "모든 리뷰를 수동으로 유지하는 방법과 위험도 기반 체크리스트를 자동화하는 방법을 비교했고, 반복 질문을 줄이기 위해 자동화를 선택했습니다.",
            "저는 PR 템플릿에 데이터 처리 유형과 인증 변경 여부를 수집하고 고위험 항목만 보안팀 리뷰로 라우팅했습니다.",
            "그 결과 평균 리뷰 대기 시간이 3일에서 8시간으로 줄었습니다.",
        ],
        "good_score": 4,
        "partial_q": "위협 모델링을 진행할 때 무엇을 확인하나요?",
        "partial_a": [
            "저는 데이터 흐름과 신뢰 경계를 먼저 봅니다.",
            "STRIDE 기준으로 위협을 적어 본 경험도 있습니다.",
            "다만 발견된 위협을 개발 우선순위와 보안 예외 정책으로 연결하는 과정은 부족했습니다.",
        ],
        "partial_reason": "위협 결과의 우선순위화 설명이 부족함",
        "fail_q": "개발팀이 보안 리뷰를 거부하면 어떻게 하나요?",
        "fail_a": [
            "저는 보안팀 권한으로 배포를 무조건 막겠다고 말했습니다.",
            "개발팀 사정은 보안보다 중요하지 않다고 생각했습니다.",
            "대안 제시나 위험 수용 절차를 함께 논의하지는 않았습니다.",
        ],
        "fail_reason": "협업 불가능한 독단적 답변",
        "fail_rule": 1,
        "fail_score": 1,
    },
]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?。])\s+", text.strip()) if s.strip()]


def word_counts(sentences):
    return [len(s.split()) for s in sentences]


def is_verbose(sentences):
    counts = word_counts(sentences)
    return bool(counts) and sum(c > 25 for c in counts) / len(counts) >= 0.3


def existing_questions():
    questions = set()
    for path in SOURCE_FILES:
        if not Path(path).exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for item in row.get("input", {}).get("interview_session", []):
                    q = item.get("question")
                    if q:
                        questions.add(q)
    return questions


def top_reason(answer, metrics, best=False):
    sentences = split_sentences(answer)
    counts = word_counts(sentences)
    cpm = metrics["cpm"]
    if cpm > 350:
        cpm_text = f"CPM 수치 {cpm}는 350 초과로 너무 빠릅니다"
    elif cpm < 200:
        cpm_text = f"CPM 수치 {cpm}는 200 미만으로 너무 느립니다"
    else:
        cpm_text = f"CPM 수치 {cpm}는 정상 범위입니다"
    silence = (
        "3초 이상 침묵이 없습니다"
        if metrics["dead_air_count"] == 0
        else f"3초 이상 침묵이 {metrics['dead_air_count']}회 발생했습니다"
    )
    verbose = "만연체입니다" if is_verbose(sentences) else "만연체는 아닙니다"
    star = metrics["star_status"]
    fulfilled = [k for k, v in star.items() if v]
    missing = [k for k, v in star.items() if not v]
    if best:
        star_text = "STAR 4요소(Situation, Task, Action, Result) 모두 충족합니다"
        decision = "Trade-off를 포함한 Action과 Result가 명확해 BEST 답변으로 판단됩니다."
    else:
        star_text = (
            f"STAR 충족 요소는 {', '.join(fulfilled) if fulfilled else '없음'}이며, "
            f"부족 요소는 {', '.join(missing) if missing else '없음'}입니다"
        )
        decision = "정량 감점과 STAR 누락이 가장 커 WORST 답변으로 판단됩니다."
    return f"{cpm_text}, {silence}. 문장별 단어 수({', '.join(map(str, counts))}) 기준으로 {verbose}. {star_text}. {decision}"


def metrics_summary(metrics, detail):
    cpm_state = "CPM 정상" if 200 <= metrics["cpm"] <= 350 else "CPM 감점"
    silence = "침묵 0회" if metrics["dead_air_count"] == 0 else f"침묵 {metrics['dead_air_count']}회 발생"
    star = metrics["star_status"]
    missing = [k for k, v in star.items() if not v]
    star_text = "STAR 4요소 충족" if not missing else f"STAR 요소 중 {', '.join(missing)} 부족"
    return f"{cpm_state}, {silence}, {star_text}, {detail}"


def sentence_rows(sentences, kind, rule_id=None, reason=None):
    rows = []
    for idx, text in enumerate(sentences):
        if kind == "fail" and idx < 2:
            rows.append({"text": text, "rule_id": rule_id, "reason": reason})
        else:
            rows.append({"text": text, "rule_id": None, "reason": "정상"})
    return rows


def make_answer(id_, q, sentences, metrics, kind, score, reason=None, rule_id=None):
    answer = " ".join(sentences)
    if kind == "good":
        detail = "Trade-off 기반 의사결정, 구체적인 Action, 명확한 Result가 확인됩니다."
        sentence_eval = sentence_rows(sentences, kind)
    elif kind == "partial":
        detail = reason
        sentence_eval = sentence_rows(sentences, kind)
    else:
        detail = reason
        sentence_eval = sentence_rows(sentences, kind, rule_id, f"감점: {reason}")
    return {
        "session": {
            "id": id_,
            "question": q,
            "answer": answer,
            "metrics": metrics,
        },
        "bottom": {
            "id": id_,
            "question": q,
            "sentences": sentence_eval,
            "metrics_summary": metrics_summary(metrics, detail),
            "score": score,
            "judgement_basis": detail,
        },
    }


def make_row(case, idx):
    pattern = PATTERNS[idx]
    good_id = pattern["good"]
    partial_id = pattern["partial"]
    fail_id = pattern["fail"]

    good_metrics = {"cpm": 278 + idx, "dead_air_count": 0, "star_status": STAR_GOOD}
    partial_metrics = {"cpm": 312 + (idx % 24), "dead_air_count": 0, "star_status": STAR_PARTIAL}
    fail_metrics = {"cpm": 222 + (idx % 22), "dead_air_count": 1 if case["fail_score"] == 1 else 0, "star_status": STAR_FAIL}
    if case["fail_score"] == 2 and idx % 2 == 0:
        fail_metrics["cpm"] = 196

    answers = {
        good_id: make_answer(good_id, case["good_q"], case["good_a"], good_metrics, "good", case["good_score"]),
        partial_id: make_answer(
            partial_id,
            case["partial_q"],
            case["partial_a"],
            partial_metrics,
            "partial",
            3,
            case["partial_reason"],
        ),
        fail_id: make_answer(
            fail_id,
            case["fail_q"],
            case["fail_a"],
            fail_metrics,
            "fail",
            case["fail_score"],
            case["fail_reason"],
            case["fail_rule"],
        ),
    }

    sessions = [answers[qid]["session"] for qid in ["Q1", "Q2", "Q3"]]
    bottom = [answers[qid]["bottom"] for qid in ["Q1", "Q2", "Q3"]]

    best_reason = top_reason(answers[good_id]["session"]["answer"], good_metrics, best=True)
    worst_reason = top_reason(answers[fail_id]["session"]["answer"], fail_metrics, best=False)

    return {
        "instruction": INSTRUCTION,
        "input": {
            "job_description": case["job"],
            "analysis_summary": {
                "best_id": good_id,
                "best_reason": best_reason,
                "worst_id": fail_id,
                "worst_reason": worst_reason,
            },
            "interview_session": sessions,
        },
        "output": {
            "top_analysis": {
                "best": {"id": good_id, "reason": best_reason},
                "worst": {"id": fail_id, "reason": worst_reason},
            },
            "mid_analysis": [
                {
                    "requirement": case["good_q"].rstrip("?"),
                    "status": "PASS",
                    "analysis": (
                        f"{good_id} 답변은 trade-off와 구체적인 Action, Result가 확인되어 요구 역량을 충족합니다."
                        if case["good_score"] == 5
                        else f"{good_id} 답변은 trade-off와 Action, Result가 있으나 일부 근거가 압축적으로 제시되어 4점 수준입니다."
                    ),
                },
                {
                    "requirement": case["partial_q"].rstrip("?"),
                    "status": "PARTIAL",
                    "analysis": f"{partial_id} 답변은 관련 Action은 있으나 {case['partial_reason']}.",
                },
                {
                    "requirement": case["fail_q"].rstrip("?"),
                    "status": "FAIL",
                    "analysis": f"{fail_id} 답변은 {case['fail_reason']}에 해당하여 실무 역량 검증이 어렵습니다.",
                },
            ],
            "bottom_analysis": bottom,
        },
    }


def validate(rows):
    assert len(rows) == 20
    existing = existing_questions()
    new_questions = []
    best_counts = Counter()
    worst_counts = Counter()
    scores = Counter()
    rule_counts = Counter()
    fail_reasons = Counter()
    for row in rows:
        summary = row["input"]["analysis_summary"]
        assert summary["best_id"] == row["output"]["top_analysis"]["best"]["id"]
        assert summary["worst_id"] == row["output"]["top_analysis"]["worst"]["id"]
        best_counts[summary["best_id"]] += 1
        worst_counts[summary["worst_id"]] += 1
        for item in row["input"]["interview_session"]:
            assert item["question"] not in existing, item["question"]
            new_questions.append(item["question"])
            assert set(item["metrics"]["star_status"]) == {"S", "T", "A", "R"}
        for item in row["output"]["bottom_analysis"]:
            scores[item["score"]] += 1
            assert 1 <= item["score"] <= 5
            for sentence in item["sentences"]:
                rid = sentence["rule_id"]
                assert rid in (None, 1, 2, 3, 4)
                if rid is not None:
                    rule_counts[rid] += 1
            if item["score"] <= 2:
                fail_reasons[item["judgement_basis"]] += 1
    assert len(new_questions) == len(set(new_questions))
    assert min(best_counts.values()) >= 6
    assert min(worst_counts.values()) >= 6
    assert scores[4] == 4, scores
    assert scores[2] == 4, scores
    assert scores[5] == 16 and scores[3] == 20 and scores[1] == 16, scores
    assert rule_counts[2] >= 6, rule_counts
    assert len(fail_reasons) >= 8, fail_reasons
    for row in rows:
        best_id = row["input"]["analysis_summary"]["best_id"]
        answer = next(x["answer"] for x in row["input"]["interview_session"] if x["id"] == best_id)
        assert "비교했고" in answer and "선택" in answer


def main():
    rows = [make_row(case, idx) for idx, case in enumerate(CASES[:20])]
    validate(rows)
    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"wrote {OUTPUT} with {len(rows)} rows")


if __name__ == "__main__":
    main()
