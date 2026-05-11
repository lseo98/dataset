import json
import re
from collections import Counter
from pathlib import Path


OUTPUT = Path("sanity_check_v4.jsonl")

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
    {"good": "Q2", "partial": "Q1", "fail": "Q3"},
    {"good": "Q3", "partial": "Q2", "fail": "Q1"},
    {"good": "Q1", "partial": "Q3", "fail": "Q2"},
    {"good": "Q2", "partial": "Q3", "fail": "Q1"},
    {"good": "Q3", "partial": "Q1", "fail": "Q2"},
    {"good": "Q1", "partial": "Q2", "fail": "Q3"},
    {"good": "Q2", "partial": "Q1", "fail": "Q3"},
]

CASES = [
    {
        "job": "Backend Engineer - Java/Spring 기반 주문 API, Redis 캐시, 장애 대응 경험자",
        "good_q": "주문 API 성능 병목을 해결한 경험이 있나요?",
        "good_a": "작년 커머스 주문 조회 API의 p95 응답 시간이 3초까지 늘어난 문제가 있었습니다. 처음에는 DB 인덱스 추가와 캐시 도입 중 고민했지만, 읽기 비율이 높고 상품 정보 변경 주기가 짧지 않아 Redis 캐시를 선택했습니다. 저는 APM trace로 반복 호출되는 상품 조회 쿼리를 찾고 TTL 정책을 적용했습니다. 배포 후 p95 응답 시간이 620ms로 줄었고 DB read 부하도 45% 감소했습니다.",
        "partial_q": "Redis 캐시를 적용할 때 어떤 점을 고려하나요?",
        "partial_a": "캐시는 응답 시간을 줄이는 데 효과적이라고 생각합니다. 저는 TTL과 캐시 무효화 정책을 같이 봅니다. 다만 장애 시 원본 DB로 fallback 되는 흐름과 캐시 장애 모니터링은 충분히 설명하지 못했습니다.",
        "partial_reason": "에러 핸들링과 장애 fallback 고려가 부족함",
        "fail_q": "트랜잭션 정합성 문제를 어떻게 해결했나요?",
        "fail_a": "결제 정합성 문제가 생겼을 때 저는 실패한 주문을 관리자 화면에서 수동으로 하나씩 확인했습니다. 문제가 보이면 상태값을 직접 수정했습니다. 왜 중복 승인이나 부분 실패가 발생했는지까지는 추적하지 못했습니다.",
        "fail_reason": "수동으로 하나씩 고치는 비효율적인 방식",
    },
    {
        "job": "Frontend Engineer - React, 상태 관리, Core Web Vitals 개선 경험자",
        "good_q": "웹 성능 지표를 개선한 경험이 있나요?",
        "good_a": "프로모션 페이지의 LCP가 4.2초로 측정되어 이탈률이 높았습니다. 이미지 품질을 낮추는 방법과 로딩 우선순위를 조정하는 방법을 비교했고, 브랜드 이미지 품질을 유지해야 해서 preload와 code splitting을 선택했습니다. 저는 hero 이미지를 AVIF로 변환하고 route 단위 chunk를 분리했습니다. 배포 후 LCP가 1.8초로 개선되었고 이탈률은 12% 감소했습니다.",
        "partial_q": "상태 관리 라이브러리를 선택할 때 무엇을 보나요?",
        "partial_a": "저는 팀이 이해하기 쉬운 도구가 좋다고 생각합니다. 작은 화면에서는 Context API도 충분했습니다. 복잡한 도메인에서는 Zustand를 사용해 본 적이 있습니다. 다만 팀원들과 상태 소유권을 어떻게 나눴는지, 코드 리뷰에서 어떤 기준을 합의했는지는 설명이 부족했습니다.",
        "partial_reason": "팀원과의 협업 과정 설명 부족",
        "fail_q": "React 렌더링 최적화를 어떻게 하나요?",
        "fail_a": "렌더링이 느리면 우선 화면을 새로고침하거나 컴포넌트를 다시 마운트하도록 처리했습니다. 일부 화면에서는 key 값을 바꿔 강제로 다시 그리게 했습니다. 원인이 props 변경인지 상태 범위 문제인지는 깊게 확인하지 못했습니다.",
        "fail_reason": "원인 분석 없이 재렌더링을 반복하는 접근",
    },
    {
        "job": "Data Engineer - Spark, Airflow, 대규모 ETL 파이프라인 운영 경험자",
        "good_q": "Spark 작업 시간을 줄인 경험이 있나요?",
        "good_a": "일별 로그 집계 작업에서 특정 user_id에 데이터가 몰려 shuffle 시간이 크게 늘었습니다. repartition만 늘리는 방법과 salting을 적용하는 방법을 비교했고, 클러스터 비용을 더 늘리기 어려워 salting을 선택했습니다. 저는 skew key를 분산하고 join 전에 필요한 컬럼만 projection 하도록 ETL을 수정했습니다. 전체 작업 시간은 140분에서 52분으로 줄었습니다.",
        "partial_q": "Airflow DAG를 설계할 때 어떤 기준을 적용하나요?",
        "partial_a": "DAG는 실패했을 때 다시 실행하기 쉬워야 합니다. 저는 task를 작게 나누고 retry 정책을 설정합니다. 하지만 외부 API가 부분 실패를 반환할 때 idempotent 하게 재처리하는 방식은 충분히 설계하지 못했습니다.",
        "partial_reason": "재처리와 idempotency 설계가 부족함",
        "fail_q": "Kafka lag이 증가하면 어떻게 대응하나요?",
        "fail_a": "lag이 늘면 일단 컨슈머를 재시작했습니다. 그래도 줄지 않으면 다시 재시작했고, 잠시 후 정상화되는지 기다렸습니다. 파티션 분배나 처리 병목을 따로 확인하지는 않았습니다.",
        "fail_reason": "원인을 모르고 재시작만 반복함",
    },
    {
        "job": "Machine Learning Engineer - 추천 모델, 피처 스토어, 온라인 실험 경험자",
        "good_q": "추천 모델 성능을 개선한 경험이 있나요?",
        "good_a": "신규 사용자의 클릭률이 낮아 개인화 추천 품질이 떨어지는 문제가 있었습니다. 모델 구조를 바꾸는 방법과 피처를 보강하는 방법을 비교했고, 데이터가 부족한 구간이라 세션 기반 피처 추가를 먼저 선택했습니다. 저는 최근 행동 피처를 추가하고 cold-start 후보군을 별도 랭커로 분리했습니다. A/B 테스트에서 CTR이 8.4% 상승했고 7일 재방문율도 개선되었습니다.",
        "partial_q": "피처 스토어를 도입할 때 어떤 점을 고려하나요?",
        "partial_a": "학습과 서빙의 피처 정의가 같아야 한다고 생각합니다. 저는 피처 계산 로직을 공통화하려고 했습니다. 다만 개인정보성 피처의 보관 기간과 접근 권한 같은 보안 고려는 구체적으로 다루지 못했습니다.",
        "partial_reason": "보안 및 개인정보 고려가 부족함",
        "fail_q": "모델 과적합을 어떻게 줄이나요?",
        "fail_a": "저는 블로그에서 본 dropout 설정을 그대로 넣어 본 적이 있습니다. 성능이 좋아지는 것 같아서 다른 모델에도 같은 값을 복사했습니다. 데이터 분할이나 validation curve를 보고 판단하지는 않았습니다.",
        "fail_reason": "기술의 원리 없이 블로그 코드를 복사해서 씀",
    },
    {
        "job": "Android Developer - Kotlin, Jetpack Compose, 앱 안정성 및 성능 최적화 경험자",
        "good_q": "앱 시작 속도를 개선한 경험이 있나요?",
        "good_a": "쇼핑 앱 콜드 스타트 시간이 4초 이상 걸려 첫 화면 이탈이 많았습니다. Splash 화면을 늘려 체감만 감추는 방법과 초기화 작업을 늦추는 방법을 비교했고, 실제 속도를 줄이기 위해 lazy init을 선택했습니다. 저는 불필요한 SDK 로딩을 첫 화면 이후로 미루고 초기 API 호출도 병렬화했습니다. 콜드 스타트는 1.7초로 줄었고 첫 화면 이탈률도 감소했습니다.",
        "partial_q": "Compose에서 recomposition을 줄이려면 무엇을 보나요?",
        "partial_a": "상태가 너무 넓게 전달되면 recomposition이 늘어난다고 생각합니다. 저는 state hoisting과 remember 사용 위치를 확인합니다. 다만 실제 recomposition count를 측정하거나 baseline profile과 연결해 검증한 경험은 부족했습니다.",
        "partial_reason": "검증 도구를 활용한 측정이 부족함",
        "fail_q": "ANR이 발생하면 어떻게 분석하나요?",
        "fail_a": "ANR이 생기면 우선 앱을 강제 종료하고 다시 실행해 보았습니다. 사용자에게도 재실행을 안내했습니다. main thread block이나 trace 파일은 확인하지 못했습니다.",
        "fail_reason": "원인을 모르고 재시작만 반복함",
    },
    {
        "job": "Security Engineer - 웹 취약점 진단, 시큐어 코딩, 침해 사고 대응 경험자",
        "good_q": "SQL Injection 취약점을 조치한 경험이 있나요?",
        "good_a": "고객 검색 API에서 파라미터 조작으로 인증 우회 가능성이 있는 SQL Injection 취약점을 발견했습니다. WAF 룰만 추가하는 방법과 코드 레벨에서 쿼리를 수정하는 방법을 비교했고, 우회 가능성을 줄이기 위해 Prepared Statement 적용을 우선했습니다. 저는 입력 검증 로직과 WAF 탐지 룰도 함께 보완했습니다. 재검증 결과 취약점이 제거되었고 보안 점검을 통과했습니다.",
        "partial_q": "침해 사고 초기 대응에서 무엇을 우선하나요?",
        "partial_a": "저는 증거 보존이 중요하다고 생각합니다. 그래서 로그를 확보하고 영향을 받은 서버를 격리해야 한다고 설명할 수 있습니다. 다만 법무 보고 체계와 개인정보 유출 가능성 판단 기준까지는 구체적으로 다루지 못했습니다.",
        "partial_reason": "법무 및 개인정보 영향도 고려가 부족함",
        "fail_q": "XSS 의심 신고가 들어오면 어떻게 하나요?",
        "fail_a": "저는 우선 신고된 화면의 HTML을 직접 찾아서 의심되는 스크립트를 지웠습니다. 비슷한 화면도 하나씩 열어 보며 수동으로 수정했습니다. 입력값 escaping이나 공통 sanitizer 적용까지는 생각하지 못했습니다.",
        "fail_reason": "수동으로 하나씩 고치는 비효율적인 방식",
    },
    {
        "job": "DevOps Engineer - Terraform, CI/CD, Kubernetes 운영 및 비용 최적화 경험자",
        "good_q": "Terraform 변경 사고를 줄인 경험이 있나요?",
        "good_a": "수동 콘솔 변경으로 보안 그룹 설정이 코드와 달라지는 문제가 반복되었습니다. 변경을 전면 금지하는 방법과 drift detection을 자동화하는 방법을 비교했고, 운영 유연성을 유지하기 위해 자동 탐지를 선택했습니다. 저는 Terraform plan 결과를 PR에 첨부하고 drift detection 잡을 매일 실행하도록 구성했습니다. 이후 승인되지 않은 변경을 14건 사전에 발견했고 배포 사고도 줄었습니다.",
        "partial_q": "CI/CD 파이프라인에서 가장 중요하게 보는 지표는 무엇인가요?",
        "partial_a": "저는 배포 성공률과 빌드 시간이 중요하다고 생각합니다. 캐시와 병렬 실행도 적용했습니다. 다만 빠른 배포와 안전한 승인 절차 사이의 trade-off를 팀 기준으로 어떻게 합의했는지는 설명이 부족했습니다.",
        "partial_reason": "의사결정 기준과 협업 합의 설명 부족",
        "fail_q": "Kubernetes Pod가 Pending이면 어떻게 보나요?",
        "fail_a": "Pending 상태가 보이면 저는 우선 deployment를 삭제하고 다시 만들었습니다. 그래도 안 되면 노드를 재부팅했습니다. 이벤트, resource request, taint 같은 원인은 확인하지 않았습니다.",
        "fail_reason": "원인을 모르고 재시작만 반복함",
    },
    {
        "job": "Embedded Linux Engineer - Yocto, 디바이스 드라이버, 부팅 최적화 경험자",
        "good_q": "임베디드 장비 부팅 시간을 줄인 경험이 있나요?",
        "good_a": "산업용 게이트웨이 장비의 부팅 시간이 70초 이상 걸려 현장 재시작 시간이 길었습니다. 커널 설정을 크게 바꾸는 방법과 user-space 서비스를 줄이는 방법을 비교했고, 리스크가 낮은 systemd 병목 제거부터 선택했습니다. 저는 불필요한 데몬을 제거하고 드라이버 초기화 순서를 병렬화했습니다. 최종적으로 부팅 시간을 32초로 줄여 현장 복구 시간을 단축했습니다.",
        "partial_q": "드라이버 디버깅 시 어떤 정보를 먼저 보나요?",
        "partial_a": "저는 커널 로그와 레지스터 값을 먼저 봅니다. 데이터시트의 초기화 순서도 확인합니다. 하지만 인터럽트 타이밍 문제나 DMA 버퍼 동기화처럼 장비 의존성이 큰 상황에서는 재현 조건을 충분히 정리하지 못했습니다.",
        "partial_reason": "재현 조건 정리가 부족함",
        "fail_q": "커널 패닉 로그를 보면 무엇을 확인하나요?",
        "fail_a": "패닉이 나면 장비 전원을 껐다 켜며 다시 올라오는지 확인했습니다. 같은 문제가 반복되면 펌웨어 이미지를 다시 굽는 방식으로 처리했습니다. stack trace나 oops 메시지를 분석하지는 못했습니다.",
        "fail_reason": "원인을 모르고 재시작만 반복함",
    },
    {
        "job": "Game Server Engineer - 실시간 매치메이킹, Redis 세션, WebSocket 운영 경험자",
        "good_q": "매치메이킹 대기 시간을 줄인 경험이 있나요?",
        "good_a": "랭크전 피크 시간대에 특정 티어 사용자의 매칭 대기 시간이 90초를 넘는 문제가 있었습니다. 서버를 증설하는 방법과 매칭 조건을 점진적으로 완화하는 방법을 비교했고, 비용보다 품질 균형이 중요해 조건 완화 로직을 선택했습니다. 저는 Redis sorted set으로 대기열을 재구성했습니다. 그 결과 평균 대기 시간이 38초로 줄었고 매칭 실패율도 감소했습니다.",
        "partial_q": "WebSocket 세션을 안정적으로 운영하려면 무엇을 보나요?",
        "partial_a": "연결 상태와 재접속 처리가 중요합니다. 저는 heartbeat와 Redis TTL을 활용했습니다. 다만 모바일 네트워크 전환, 서버 재시작, 중복 세션 처리 상황에서 각각의 장단점을 충분히 비교하지 못했습니다.",
        "partial_reason": "사용한 기술의 장단점 비교가 부족함",
        "fail_q": "게임 서버 지연이 증가하면 어떻게 하나요?",
        "fail_a": "지연이 늘면 우선 문제가 되는 방을 찾아 유저를 다른 방으로 수동 이동시켰습니다. 몇 번은 임시로 해결됐지만 같은 문제가 다시 생겼습니다. tick 처리나 네트워크 RTT 병목은 분석하지 못했습니다.",
        "fail_reason": "수동으로 하나씩 고치는 비효율적인 방식",
    },
    {
        "job": "QA Automation Engineer - Playwright, API 테스트, CI 품질 게이트 운영 경험자",
        "good_q": "회귀 테스트 시간을 줄인 경험이 있나요?",
        "good_a": "배포 전 수동 회귀 테스트가 6시간 이상 걸려 릴리즈가 지연되었습니다. 모든 케이스를 자동화하는 방법과 핵심 플로우부터 자동화하는 방법을 비교했고, 유지보수 비용을 고려해 핵심 플로우 우선 전략을 선택했습니다. 저는 Playwright 시나리오를 만들고 GitHub Actions에서 병렬 실행되도록 구성했습니다. 회귀 테스트 시간이 50분으로 줄었고 배포 전 결함 발견도 빨라졌습니다.",
        "partial_q": "불안정한 테스트를 줄이려면 무엇을 보나요?",
        "partial_a": "저는 wait 조건이 중요하다고 생각합니다. 고정 sleep을 줄이고 selector를 안정화한 적이 있습니다. 하지만 테스트 데이터 격리와 네트워크 mocking을 함께 설계하지 않아 환경 의존 실패를 충분히 줄이지 못했습니다.",
        "partial_reason": "테스트 데이터와 환경 격리 설계가 부족함",
        "fail_q": "버그가 재현되지 않으면 어떻게 하나요?",
        "fail_a": "재현이 안 되면 같은 버튼을 여러 번 눌러 보았습니다. 그래도 안 되면 개발자에게 영상만 전달했습니다. 로그, 기기 조건, 계정 상태를 체계적으로 수집하지는 못했습니다.",
        "fail_reason": "수동으로 하나씩 고치는 비효율적인 방식",
    },
]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def word_counts(text):
    return [len(re.findall(r"\S+", sentence)) for sentence in split_sentences(text)]


def verbose(text):
    counts = word_counts(text)
    return bool(counts) and sum(1 for count in counts if count > 25) / len(counts) >= 0.3


def score(question):
    metrics = question["metrics"]
    star = metrics["star_status"]
    missing = sum(1 for key in ("S", "T", "A", "R") if not star[key])
    penalties = int(metrics["cpm"] > 350 or metrics["cpm"] < 200) + int(metrics["dead_air_count"] >= 1) + int(verbose(question["answer"]))
    value = max(1, 5 - missing - penalties)
    if not star["A"]:
        value = min(value, 3)
    return value


def top_reason(question, kind):
    metrics = question["metrics"]
    counts = word_counts(question["answer"])
    cpm = metrics["cpm"]
    if cpm < 200:
        cpm_text = f"CPM 수치 {cpm}는 200 미만(너무 느림)"
    elif cpm > 350:
        cpm_text = f"CPM 수치 {cpm}는 350 초과(너무 빠름)"
    else:
        cpm_text = f"CPM 수치 {cpm}는 정상 범위"
    silence = "3초 이상 침묵이 없습니다" if metrics["dead_air_count"] == 0 else f"3초 이상 침묵이 {metrics['dead_air_count']}회 발생했습니다"
    concision = "만연체에 해당합니다" if verbose(question["answer"]) else "만연체는 아닙니다"
    star = metrics["star_status"]
    names = {"S": "Situation", "T": "Task", "A": "Action", "R": "Result"}
    missing = [names[key] for key in ("S", "T", "A", "R") if not star[key]]
    if missing:
        passed = [names[key] for key in ("S", "T", "A", "R") if star[key]]
        star_text = f"STAR 충족 요소는 {', '.join(passed) if passed else '없음'}이며, 부족 요소는 {', '.join(missing)}입니다"
    else:
        star_text = "STAR 4요소(Situation, Task, Action, Result) 모두 충족합니다"
    result = f"{cpm_text}이며, {silence}. 문장별 단어 수({', '.join(map(str, counts))}) 기준으로 {concision}. {star_text}."
    if kind == "best":
        return result + " Trade-off를 포함한 Action과 Result가 명확해 BEST 답변으로 판단됩니다."
    return result + " 정량 감점과 STAR 누락이 가장 커 WORST 답변으로 판단됩니다."


def make_question(id_, q, a, kind, i):
    if kind == "good":
        return {"id": id_, "question": q, "answer": a, "metrics": {"cpm": 282 + i, "dead_air_count": 0, "star_status": STAR_GOOD}}
    if kind == "partial":
        return {"id": id_, "question": q, "answer": a, "metrics": {"cpm": 316 + i, "dead_air_count": 0, "star_status": STAR_PARTIAL}}
    return {"id": id_, "question": q, "answer": a, "metrics": {"cpm": 222 + i, "dead_air_count": 1, "star_status": STAR_FAIL}}


def bottom_item(question, kind, reason):
    if kind == "good":
        return {
            "id": question["id"],
            "question": question["question"],
            "sentences": [{"text": sentence, "rule_id": None, "reason": "정상"} for sentence in split_sentences(question["answer"])],
            "metrics_summary": "CPM 정상, 침묵 0회, STAR 4요소 충족",
            "score": 5,
            "judgement_basis": "Trade-off 기반 의사결정, 구체적인 Action, 명확한 Result가 모두 확인됩니다.",
        }
    if kind == "partial":
        return {
            "id": question["id"],
            "question": question["question"],
            "sentences": [{"text": sentence, "rule_id": None, "reason": "정상"} for sentence in split_sentences(question["answer"])],
            "metrics_summary": f"침묵 0회, STAR 요소 중 Result 부족, {reason}",
            "score": 3,
            "judgement_basis": f"Action은 있으나 {reason}으로 인해 3점으로 평가됩니다.",
        }
    sentences = []
    for index, sentence in enumerate(split_sentences(question["answer"])):
        if index == len(split_sentences(question["answer"])) - 1:
            rule_id, sentence_reason = None, "정상"
        else:
            rule_id = 1
            sentence_reason = f"구체성 결여: {reason}"
        sentences.append({"text": sentence, "rule_id": rule_id, "reason": sentence_reason})
    return {
        "id": question["id"],
        "question": question["question"],
        "sentences": sentences,
        "metrics_summary": "침묵 1회 발생, STAR 요소 중 Task, Action, Result 부족",
        "score": 1,
        "judgement_basis": f"{reason}에 해당하며 원인 분석과 본인 Action이 부족합니다.",
    }


def make_row(case, pattern, i):
    questions = {
        "good": make_question(pattern["good"], case["good_q"], case["good_a"], "good", i),
        "partial": make_question(pattern["partial"], case["partial_q"], case["partial_a"], "partial", i),
        "fail": make_question(pattern["fail"], case["fail_q"], case["fail_a"], "fail", i),
    }
    session = sorted(questions.values(), key=lambda item: item["id"])
    ranked = [(item, score(item)) for item in session]
    best = max(ranked, key=lambda item: (item[1], item[0]["metrics"]["cpm"], item[0]["id"]))[0]
    worst = min(ranked, key=lambda item: (item[1], -item[0]["metrics"]["cpm"], item[0]["id"]))[0]
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
                {"requirement": case["good_q"].rstrip("?"), "status": "PASS", "analysis": f"{pattern['good']} 답변은 trade-off와 구체적인 Action, Result가 확인되어 요구 역량을 충족합니다."},
                {"requirement": case["partial_q"].rstrip("?"), "status": "PARTIAL", "analysis": f"{pattern['partial']} 답변은 관련 Action은 있으나 {case['partial_reason']}."},
                {"requirement": case["fail_q"].rstrip("?"), "status": "FAIL", "analysis": f"{pattern['fail']} 답변은 {case['fail_reason']}에 해당하여 실무 역량 검증이 어렵습니다."},
            ],
            "bottom_analysis": [
                bottom_item(questions["good"], "good", ""),
                bottom_item(questions["partial"], "partial", case["partial_reason"]),
                bottom_item(questions["fail"], "fail", case["fail_reason"]),
            ],
        },
    }


rows = [make_row(case, PATTERNS[i], i) for i, case in enumerate(CASES)]


def validate(rows):
    assert len(rows) == 10
    best_counts = Counter()
    worst_counts = Counter()
    partial_reasons = Counter(case["partial_reason"] for case in CASES)
    fail_reasons = Counter(case["fail_reason"] for case in CASES)
    for row in rows:
        ids = {item["id"] for item in row["input"]["interview_session"]}
        assert ids == {"Q1", "Q2", "Q3"}
        assert row["input"]["analysis_summary"]["best_id"] == row["output"]["top_analysis"]["best"]["id"]
        assert row["input"]["analysis_summary"]["worst_id"] == row["output"]["top_analysis"]["worst"]["id"]
        best_counts[row["output"]["top_analysis"]["best"]["id"]] += 1
        worst_counts[row["output"]["top_analysis"]["worst"]["id"]] += 1
        assert {item["status"] for item in row["output"]["mid_analysis"]} == {"PASS", "PARTIAL", "FAIL"}
        for item in row["output"]["bottom_analysis"]:
            assert 1 <= item["score"] <= 5
            source = next(q for q in row["input"]["interview_session"] if q["id"] == item["id"])
            if not source["metrics"]["star_status"]["A"]:
                assert item["score"] <= 3
        best_answer = next(q for q in row["input"]["interview_session"] if q["id"] == row["output"]["top_analysis"]["best"]["id"])["answer"]
        assert any(token in best_answer for token in ["비교했고", "고민했지만", "선택했습니다"])
    assert all(best_counts[key] >= 2 for key in ("Q1", "Q2", "Q3"))
    assert all(worst_counts[key] >= 2 for key in ("Q1", "Q2", "Q3"))
    assert len(partial_reasons) >= 6
    assert len(fail_reasons) >= 4


validate(rows)
OUTPUT.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
print(f"wrote {OUTPUT} with {len(rows)} rows")
