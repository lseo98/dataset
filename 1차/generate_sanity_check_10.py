import json
import re
from pathlib import Path


OUTPUT = Path("sanity_check_10.jsonl")

INSTRUCTION = (
    "IT 전문 면접관으로서 제공된 문답과 분석 데이터를 바탕으로 상단(BEST/WORST), "
    "중단(Fit-Gap), 하단(평가 스크립트) 보고서를 생성하십시오. 모든 판단은 오직 "
    "[정량 지표], [STAR 기준], [Fit-Gap 기준], [문장 단위 위반 규칙]에 의거해야 합니다."
)


def word_counts(answer):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。！？])\s+", answer.strip()) if s.strip()]
    return [len(re.findall(r"\S+", sentence)) for sentence in sentences]


def evaluate(question):
    metrics = question["metrics"]
    star = metrics["star_status"]
    counts = word_counts(question["answer"])
    verbose = bool(counts) and sum(1 for count in counts if count > 25) / len(counts) >= 0.3
    missing = [key for key in ("S", "T", "A", "R") if not star[key]]
    penalties = int(metrics["cpm"] > 350 or metrics["cpm"] < 200) + int(metrics["dead_air_count"] >= 1) + int(verbose)
    score = max(1, 5 - penalties - len(missing))
    if not star["A"]:
        score = min(score, 3)
    return score, counts, verbose


def cpm_text(cpm):
    if cpm > 350:
        return f"CPM 수치가 {cpm}으로 350 초과(너무 빠름)"
    if cpm < 200:
        return f"CPM 수치가 {cpm}으로 200 미만(너무 느림)"
    return f"CPM 수치가 {cpm}으로 정상 범위"


def silence_text(dead_air_count):
    if dead_air_count == 0:
        return "3초 이상 침묵이 없습니다"
    return f"3초 이상 침묵이 {dead_air_count}회 발생했습니다"


def star_text(star):
    names = {"S": "Situation", "T": "Task", "A": "Action", "R": "Result"}
    passed = [names[key] for key in ("S", "T", "A", "R") if star[key]]
    missing = [names[key] for key in ("S", "T", "A", "R") if not star[key]]
    if not missing:
        return "STAR 4요소(Situation, Task, Action, Result) 모두 충족합니다"
    return f"STAR 충족 요소는 {', '.join(passed) if passed else '없음'}이며, 부족 요소는 {', '.join(missing)}입니다"


def top_reason(question, selected):
    score, counts, verbose = evaluate(question)
    metrics = question["metrics"]
    concision = (
        f"문장별 단어 수({', '.join(map(str, counts))}) 기준으로 만연체에 해당합니다"
        if verbose
        else f"문장별 단어 수({', '.join(map(str, counts))}) 기준으로 만연체는 아닙니다"
    )
    base = (
        f"{cpm_text(metrics['cpm'])}이며, {silence_text(metrics['dead_air_count'])}. "
        f"{concision}. {star_text(metrics['star_status'])}."
    )
    if selected == "best":
        return base + " 정량 감점이 없고 STAR 기준 충족도가 가장 높아 BEST 답변으로 판단됩니다."
    return base + " 정량 감점과 STAR 누락이 가장 커 WORST 답변으로 판단됩니다."


def make_row(job_description, interview_session, mid_analysis, bottom_analysis):
    scored = [(question, evaluate(question)[0]) for question in interview_session]
    best = max(scored, key=lambda item: (item[1], item[0]["metrics"]["cpm"], item[0]["id"]))[0]
    worst = min(scored, key=lambda item: (item[1], -item[0]["metrics"]["cpm"], item[0]["id"]))[0]

    return {
        "instruction": INSTRUCTION,
        "input": {
            "job_description": job_description,
            "analysis_summary": {
                "best_id": best["id"],
                "best_reason": top_reason(best, "best"),
                "worst_id": worst["id"],
                "worst_reason": top_reason(worst, "worst"),
            },
            "interview_session": interview_session,
        },
        "output": {
            "top_analysis": {
                "best": {"id": best["id"], "reason": top_reason(best, "best")},
                "worst": {"id": worst["id"], "reason": top_reason(worst, "worst")},
            },
            "mid_analysis": mid_analysis,
            "bottom_analysis": bottom_analysis,
        },
    }


def q(id_, question, answer, cpm, dead_air_count, star):
    return {
        "id": id_,
        "question": question,
        "answer": answer,
        "metrics": {
            "cpm": cpm,
            "dead_air_count": dead_air_count,
            "star_status": star,
        },
    }


GOOD_STAR = {"S": True, "T": True, "A": True, "R": True}
MID_STAR = {"S": True, "T": True, "A": True, "R": False}
BAD_STAR = {"S": True, "T": False, "A": False, "R": False}
EMPTY_STAR = {"S": False, "T": False, "A": False, "R": False}


rows = [
    make_row(
        "Site Reliability Engineer - Kubernetes 운영, 장애 대응 자동화, Prometheus 기반 모니터링 경험자",
        [
            q("Q1", "서비스 지연 장애를 어떻게 탐지하고 복구했나요?", "지난 분기 결제 API의 p95 지연 시간이 2초를 넘는 장애가 있었습니다. 저는 Prometheus 알림과 Grafana 대시보드를 확인해 특정 파드의 CPU throttling을 원인으로 좁혔습니다. HPA 임계값과 리소스 request를 조정한 뒤 재배포했고 p95 지연 시간을 480ms까지 낮췄습니다.", 288, 0, GOOD_STAR),
            q("Q2", "장애 대응 문서를 만들 때 중요하게 보는 항목은 무엇인가요?", "런북은 누구나 따라 할 수 있어야 한다고 생각해서 저는 알림 조건과 담당자 연락망과 롤백 절차와 확인 쿼리와 배포 이력 확인 방법을 한 문서에 계속 추가했으며 실제 운영 중에도 문서를 보며 대응했지만 복구 시간이 얼마나 줄었는지는 따로 측정하지 못했습니다.", 338, 0, MID_STAR),
            q("Q3", "야간 장애가 발생하면 가장 먼저 무엇을 하나요?", "저는 책임감이 강해서 밤에도 연락을 잘 받습니다. 장애가 나면 끝까지 남아서 팀원들과 같이 해결하려고 노력합니다. 평소에도 성실하다는 평가를 많이 받아서 어떤 상황도 버틸 자신이 있습니다.", 230, 1, BAD_STAR),
        ],
        [
            {"requirement": "Kubernetes 기반 장애 분석 및 복구", "status": "PASS", "analysis": "Q1에서 원인 분석, 리소스 조정, 재배포, 지연 시간 개선 결과가 모두 확인되어 요구 역량을 충족합니다."},
            {"requirement": "운영 자동화 및 런북 체계화", "status": "PARTIAL", "analysis": "Q2에서 운영 문서화 경험은 확인되나, 복구 시간 개선 등 명확한 Result가 부족합니다."},
            {"requirement": "야간 장애 초기 대응 절차", "status": "FAIL", "analysis": "Q3은 태도 중심 답변에 머물러 구체적인 장애 격리, 원인 분석, 복구 Action을 검증하기 어렵습니다."},
        ],
        [
            {"id": "Q1", "question": "서비스 지연 장애를 어떻게 탐지하고 복구했나요?", "sentences": [{"text": "지난 분기 결제 API의 p95 지연 시간이 2초를 넘는 장애가 있었습니다.", "rule_id": None, "reason": "정상"}, {"text": "저는 Prometheus 알림과 Grafana 대시보드를 확인해 특정 파드의 CPU throttling을 원인으로 좁혔습니다.", "rule_id": None, "reason": "정상"}, {"text": "HPA 임계값과 리소스 request를 조정한 뒤 재배포했고 p95 지연 시간을 480ms까지 낮췄습니다.", "rule_id": None, "reason": "정상"}], "metrics_summary": "CPM 288 정상, 침묵 0회, STAR 4요소 충족", "score": 5, "judgement_basis": "정량 감점이 없고 Situation, Task, Action, Result가 모두 명확합니다."},
            {"id": "Q2", "question": "장애 대응 문서를 만들 때 중요하게 보는 항목은 무엇인가요?", "sentences": [{"text": "런북은 누구나 따라 할 수 있어야 한다고 생각해서 저는 알림 조건과 담당자 연락망과 롤백 절차와 확인 쿼리와 배포 이력 확인 방법을 한 문서에 계속 추가했으며 실제 운영 중에도 문서를 보며 대응했지만 복구 시간이 얼마나 줄었는지는 따로 측정하지 못했습니다.", "rule_id": 3, "reason": "가독성 저하: 여러 내용을 한 문장에 길게 연결한 만연체"}], "metrics_summary": "침묵 0회, STAR 요소 중 Result 부족, 만연체 감점", "score": 3, "judgement_basis": "Action은 있으나 Result가 부족하고 문장이 장황하여 3점으로 평가됩니다."},
            {"id": "Q3", "question": "야간 장애가 발생하면 가장 먼저 무엇을 하나요?", "sentences": [{"text": "저는 책임감이 강해서 밤에도 연락을 잘 받습니다.", "rule_id": 4, "reason": "동문서답: 기술적 초기 대응 절차 대신 태도 강조"}, {"text": "장애가 나면 끝까지 남아서 팀원들과 같이 해결하려고 노력합니다.", "rule_id": 1, "reason": "구체성 결여: 본인의 구체적 Action 부재"}, {"text": "평소에도 성실하다는 평가를 많이 받아서 어떤 상황도 버틸 자신이 있습니다.", "rule_id": None, "reason": "정상"}], "metrics_summary": "침묵 1회 발생, STAR 요소 중 Task, Action, Result 부족", "score": 1, "judgement_basis": "정량 감점이 있고 Action과 Result가 확인되지 않아 낮은 평가를 받았습니다."},
        ],
    ),
    make_row(
        "QA Automation Engineer - Playwright/Selenium 기반 E2E 테스트 구축 및 CI 연동 경험자",
        [
            q("Q1", "회귀 테스트 시간을 줄인 경험이 있나요?", "정기 배포 전 수동 회귀 테스트가 6시간 이상 걸리는 문제가 있었습니다. 저는 핵심 사용자 플로우를 Playwright 시나리오로 자동화하고 GitHub Actions에 병렬 실행 잡을 구성했습니다. 그 결과 회귀 테스트 시간이 55분으로 줄었고 배포 전 결함 발견률도 높아졌습니다.", 276, 0, GOOD_STAR),
            q("Q2", "테스트 케이스 우선순위는 어떻게 정하나요?", "저는 사용자가 자주 쓰는 기능을 먼저 본다는 원칙으로 로그인과 결제와 검색과 관리자 기능을 중요하게 보고 있으며 프로젝트 상황에 따라 위험도를 판단해서 테스트를 나누려고 노력했지만 실제 장애 빈도나 결함 밀도를 기준으로 정량화한 경험은 아직 부족합니다.", 326, 0, MID_STAR),
            q("Q3", "불안정한 테스트는 어떻게 다루나요?", "테스트가 가끔 실패하면 다시 돌려보는 편입니다. 자동화는 원래 예민해서 어느 정도 실패할 수 있다고 생각합니다. 저는 꼼꼼하게 확인하는 성격이라 시간이 걸려도 계속 확인합니다.", 185, 2, EMPTY_STAR),
        ],
        [
            {"requirement": "E2E 테스트 자동화 및 CI 연동", "status": "PASS", "analysis": "Q1에서 Playwright 자동화와 GitHub Actions 병렬 실행 경험이 확인되어 요구사항을 충족합니다."},
            {"requirement": "테스트 전략 및 리스크 기반 우선순위화", "status": "PARTIAL", "analysis": "Q2에서 우선순위 판단 기준은 있으나 결함 밀도 등 정량적 Result가 부족합니다."},
            {"requirement": "불안정한 테스트 원인 분석 및 안정화", "status": "FAIL", "analysis": "Q3은 재실행 외에 구체적인 flaky test 분석, 격리, 안정화 Action을 제시하지 못했습니다."},
        ],
        [
            {"id": "Q1", "question": "회귀 테스트 시간을 줄인 경험이 있나요?", "sentences": [{"text": "정기 배포 전 수동 회귀 테스트가 6시간 이상 걸리는 문제가 있었습니다.", "rule_id": None, "reason": "정상"}, {"text": "저는 핵심 사용자 플로우를 Playwright 시나리오로 자동화하고 GitHub Actions에 병렬 실행 잡을 구성했습니다.", "rule_id": None, "reason": "정상"}, {"text": "그 결과 회귀 테스트 시간이 55분으로 줄었고 배포 전 결함 발견률도 높아졌습니다.", "rule_id": None, "reason": "정상"}], "metrics_summary": "CPM 276 정상, 침묵 0회, STAR 4요소 충족", "score": 5, "judgement_basis": "정량 감점이 없고 자동화 Action과 Result가 구체적입니다."},
            {"id": "Q2", "question": "테스트 케이스 우선순위는 어떻게 정하나요?", "sentences": [{"text": "저는 사용자가 자주 쓰는 기능을 먼저 본다는 원칙으로 로그인과 결제와 검색과 관리자 기능을 중요하게 보고 있으며 프로젝트 상황에 따라 위험도를 판단해서 테스트를 나누려고 노력했지만 실제 장애 빈도나 결함 밀도를 기준으로 정량화한 경험은 아직 부족합니다.", "rule_id": 3, "reason": "가독성 저하: 긴 문장과 접속사 연결"}], "metrics_summary": "침묵 0회, STAR 요소 중 Result 부족, 만연체 감점", "score": 3, "judgement_basis": "Action은 있으나 정량 Result가 부족하고 문장이 장황합니다."},
            {"id": "Q3", "question": "불안정한 테스트는 어떻게 다루나요?", "sentences": [{"text": "테스트가 가끔 실패하면 다시 돌려보는 편입니다.", "rule_id": 1, "reason": "구체성 결여: flaky test 원인 분석 Action 부재"}, {"text": "자동화는 원래 예민해서 어느 정도 실패할 수 있다고 생각합니다.", "rule_id": 4, "reason": "동문서답: 개선 절차 대신 일반론 제시"}, {"text": "저는 꼼꼼하게 확인하는 성격이라 시간이 걸려도 계속 확인합니다.", "rule_id": None, "reason": "정상"}], "metrics_summary": "CPM 185 미만, 침묵 2회 발생, STAR 4요소 부족", "score": 1, "judgement_basis": "정량 감점과 STAR 누락이 모두 커 실무 역량 검증이 어렵습니다."},
        ],
    ),
]


domains = [
    ("Database Reliability Engineer - PostgreSQL 튜닝, 장애 복구, 백업 전략 경험자", "슬로우 쿼리 장애를 해결한 경험을 설명해주세요.", "월말 정산 배치에서 특정 조인 쿼리가 40분 이상 실행되는 문제가 있었습니다. 저는 실행 계획을 분석해 불필요한 시퀀셜 스캔을 확인했고 복합 인덱스와 통계 갱신을 적용했습니다. 이후 배치 시간이 8분으로 줄었고 재시도 없이 안정적으로 마감할 수 있었습니다.", "백업 정책을 설계할 때 중요하게 보는 기준은 무엇인가요?", "저는 백업은 자주 할수록 좋다고 생각해서 전체 백업과 증분 백업을 함께 보고 있으며 보관 주기와 복구 시나리오와 권한 관리까지 같이 고려하려고 했지만 실제 RTO와 RPO를 기준으로 복구 훈련 결과를 수치화하지는 못했습니다.", "장애가 나면 어떤 마음가짐으로 대응하나요?", "데이터베이스는 회사의 핵심이라 책임감이 중요합니다. 저는 문제가 생기면 당황하지 않고 팀과 함께 열심히 해결하겠습니다. 평소에도 꼼꼼한 편이라 실수 없이 처리할 자신이 있습니다."),
    ("Android Developer - Kotlin, Jetpack Compose, 앱 성능 최적화 경험자", "앱 시작 속도를 개선한 경험이 있나요?", "작년 커머스 앱에서 콜드 스타트가 4초 이상 걸리는 문제가 있었습니다. 저는 Application 초기화 로직을 지연 로딩으로 분리하고 불필요한 SDK 초기화를 백그라운드로 이동했습니다. 그 결과 콜드 스타트 시간이 1.6초로 줄었고 이탈률도 감소했습니다.", "Compose 화면을 설계할 때 중요하게 보는 점은 무엇인가요?", "저는 상태가 예측 가능해야 한다고 생각해서 화면 상태와 이벤트를 분리하고 remember 사용 위치와 recomposition 범위를 계속 확인했으며 팀 코드 리뷰에서도 관련 기준을 공유했지만 성능 개선 폭을 수치로 정리하지는 못했습니다.", "새로운 안드로이드 기술은 어떻게 학습하나요?", "저는 최신 기술을 좋아해서 블로그를 많이 봅니다. 팀에서 필요하면 빠르게 배워서 적용할 수 있습니다. 꾸준히 공부하는 개발자라 어떤 기술도 해낼 자신이 있습니다."),
    ("Machine Learning Engineer - 추천 모델 학습, 피처 엔지니어링, 온라인 실험 경험자", "추천 모델 성능을 개선한 경험이 있나요?", "음악 추천 서비스에서 신규 사용자의 클릭률이 낮은 문제가 있었습니다. 저는 최근 청취 세션 기반 피처를 추가하고 후보 생성 모델의 negative sampling 방식을 조정했습니다. A/B 테스트 결과 CTR이 7.8% 상승했고 신규 사용자 재방문율도 개선되었습니다.", "모델 학습 데이터 품질은 어떻게 관리하나요?", "저는 데이터가 모델 성능의 대부분을 좌우한다고 생각해서 결측치와 중복과 라벨 분포와 학습 기간을 함께 확인하며 이상치가 보이면 샘플을 추적했지만 이런 점검이 실제 성능에 얼마나 기여했는지는 별도로 분리해 측정하지 못했습니다.", "모델이 틀리면 어떻게 하나요?", "모델도 사람이 만든 것이기 때문에 완벽할 수는 없습니다. 저는 실패를 두려워하지 않고 계속 실험하는 태도가 중요하다고 생각합니다. 팀원들과 논의하면서 더 나은 방향을 찾겠습니다."),
    ("DevOps Engineer - Terraform, CI/CD, 클라우드 비용 최적화 경험자", "Terraform으로 인프라 변경 사고를 줄인 경험이 있나요?", "멀티 계정 환경에서 수동 보안 그룹 변경으로 설정이 자주 달라지는 문제가 있었습니다. 저는 Terraform 모듈을 표준화하고 plan 결과를 PR에 자동 첨부하도록 CI를 구성했습니다. 이후 승인되지 않은 변경이 줄었고 배포 전 설정 오류를 12건 사전에 차단했습니다.", "CI/CD 파이프라인에서 가장 중요하게 보는 지표는 무엇인가요?", "저는 배포가 빠르고 안정적이어야 한다고 생각해서 빌드 시간과 실패율과 롤백 절차와 승인 단계를 함께 관리하려고 했으며 실제 프로젝트에서도 캐시와 병렬 실행을 적용했지만 지표를 대시보드로 계속 추적하지는 못했습니다.", "클라우드 비용이 늘면 어떻게 대응하나요?", "비용은 아껴 쓰는 습관이 중요합니다. 저는 평소에도 낭비를 싫어해서 회사 리소스도 소중히 다루겠습니다. 매일 확인하면서 책임감 있게 관리하겠습니다."),
    ("iOS Developer - Swift, SwiftUI, 네트워크 계층 설계 및 앱 안정화 경험자", "앱 크래시를 줄인 경험이 있나요?", "구독 결제 화면에서 간헐적으로 앱이 종료되는 문제가 있었습니다. 저는 Crashlytics 로그를 분석해 비동기 콜백 이후 해제된 객체를 참조하는 흐름을 확인했습니다. weak self 처리와 상태 검증을 추가했고 해당 화면 크래시율을 0.8%에서 0.05%로 낮췄습니다.", "네트워크 레이어를 설계할 때 중요하게 보는 점은 무엇인가요?", "저는 API 호출이 여러 화면에 흩어지지 않게 공통 클라이언트를 만들고 에러 매핑과 재시도 정책과 토큰 갱신 처리를 한곳에서 관리하려고 했으며 실제로 유지보수는 편해졌지만 변경 전후 결함 수를 따로 비교하지는 못했습니다.", "새 기능 일정이 촉박하면 어떻게 하나요?", "저는 책임감 있게 야근해서라도 맞추려고 합니다. 일정이 급하면 집중해서 빠르게 개발하는 것이 중요합니다. 팀과 잘 소통하면서 최대한 맞추겠습니다."),
    ("Data Analyst - SQL, 대시보드 설계, 실험 분석 및 지표 정의 경험자", "비즈니스 지표를 개선한 분석 경험이 있나요?", "구독 전환율이 특정 유입 채널에서 낮게 나오는 문제가 있었습니다. 저는 퍼널 단계별 이탈률을 SQL로 분해하고 결제 페이지 로딩 지연 구간을 찾아냈습니다. 개선안 반영 후 해당 채널 전환율이 3.2%p 상승했습니다.", "대시보드 지표를 설계할 때 무엇을 중요하게 보나요?", "저는 대시보드는 보는 사람이 바로 의사결정할 수 있어야 한다고 생각해서 핵심 지표와 보조 지표와 필터와 기간 기준을 같이 정리했지만 실제 사용자가 얼마나 자주 활용했는지는 로그로 추적하지 못했습니다.", "분석 요청이 많으면 어떻게 처리하나요?", "저는 요청자와 좋은 관계를 유지하는 것이 중요하다고 생각합니다. 바쁘더라도 최대한 친절하게 응대하려고 합니다. 필요하면 야근해서라도 자료를 만들어 드리겠습니다."),
    ("Network Engineer - L4/L7 로드밸런싱, 방화벽 정책, 트래픽 분석 경험자", "트래픽 병목을 해결한 경험이 있나요?", "사내 API 게이트웨이 구간에서 특정 시간대 연결 지연이 급증했습니다. 저는 NetFlow와 로드밸런서 로그를 분석해 특정 백엔드 풀에 세션이 몰리는 문제를 확인했습니다. 가중치와 헬스체크 조건을 조정한 뒤 평균 연결 시간이 60% 감소했습니다.", "방화벽 정책을 관리할 때 중요하게 보는 점은 무엇인가요?", "저는 보안 정책은 명확해야 한다고 생각해서 출발지와 목적지와 포트와 만료일을 함께 기록하고 정기적으로 미사용 정책을 검토했지만 제거 정책 수나 위험도 감소를 정량적으로 관리하지는 못했습니다.", "네트워크 장애가 생기면 어떻게 하나요?", "네트워크는 연결이 중요하니까 침착함이 필요합니다. 저는 차분하게 상황을 보고 팀원들과 같이 해결하겠습니다. 경험이 쌓이면 더 잘할 수 있다고 생각합니다."),
    ("Backend Engineer - Go 기반 API 개발, 메시지 큐, 대용량 트래픽 처리 경험자", "메시지 큐 적체를 해결한 경험이 있나요?", "주문 이벤트 컨슈머 처리량이 부족해 Kafka lag이 빠르게 증가한 적이 있었습니다. 저는 프로파일링으로 외부 API 호출 병목을 확인하고 배치 처리와 타임아웃 정책을 적용했습니다. 컨슈머 처리량이 초당 400건에서 1,500건으로 증가했고 lag이 안정화되었습니다.", "API 에러 처리는 어떻게 설계하나요?", "저는 에러가 사용자와 운영자 모두에게 이해 가능해야 한다고 생각해서 에러 코드를 표준화하고 로깅 필드와 추적 ID와 재시도 가능 여부를 함께 내려주도록 설계했지만 장애 분석 시간이 얼마나 줄었는지는 측정하지 못했습니다.", "트래픽이 늘면 어떻게 대응하나요?", "트래픽이 늘면 서버를 더 늘리면 된다고 생각합니다. 저는 열심히 모니터링하고 문제가 보이면 바로 팀에 공유하겠습니다. 서비스가 커지는 것은 좋은 일이니 긍정적으로 대응하겠습니다."),
]


for idx, domain in enumerate(domains, start=3):
    job, good_q, good_a, mid_q, mid_a, bad_q, bad_a = domain
    order = [
        ("Q1", good_q, good_a, 292 + idx, 0, GOOD_STAR),
        ("Q2", mid_q, mid_a, 330 + idx, 0, MID_STAR),
        ("Q3", bad_q, bad_a, 225 + idx, 1, BAD_STAR),
    ]
    if idx % 3 == 1:
        order = [order[2], order[0], order[1]]
    elif idx % 3 == 2:
        order = [order[1], order[2], order[0]]
    session = [q(*item) for item in order]

    good_id = next(item[0] for item in order if item[2] == good_a)
    mid_id = next(item[0] for item in order if item[2] == mid_a)
    bad_id = next(item[0] for item in order if item[2] == bad_a)

    rows.append(
        make_row(
            job,
            session,
            [
                {"requirement": good_q.replace("?", ""), "status": "PASS", "analysis": f"{good_id} 답변에서 구체적인 Action과 Result가 확인되어 요구 역량을 충족합니다."},
                {"requirement": mid_q.replace("?", ""), "status": "PARTIAL", "analysis": f"{mid_id} 답변에서 관련 Action은 확인되나 정량적 Result가 부족합니다."},
                {"requirement": bad_q.replace("?", ""), "status": "FAIL", "analysis": f"{bad_id} 답변은 태도나 일반론 중심으로 구성되어 구체적인 Task, Action, Result를 검증하기 어렵습니다."},
            ],
            [
                {"id": good_id, "question": good_q, "sentences": [{"text": s, "rule_id": None, "reason": "정상"} for s in re.split(r"(?<=[.!?])\s+", good_a) if s], "metrics_summary": "CPM 정상, 침묵 0회, STAR 4요소 충족", "score": 5, "judgement_basis": "정량 감점이 없고 STAR 4요소가 모두 명확합니다."},
                {"id": mid_id, "question": mid_q, "sentences": [{"text": mid_a, "rule_id": 3, "reason": "가독성 저하: 여러 내용을 한 문장에 길게 연결한 만연체"}], "metrics_summary": "침묵 0회, STAR 요소 중 Result 부족, 만연체 감점", "score": 3, "judgement_basis": "Action은 있으나 Result가 부족하고 문장이 장황하여 3점으로 평가됩니다."},
                {"id": bad_id, "question": bad_q, "sentences": [{"text": s, "rule_id": 4 if n == 0 else (1 if n == 1 else None), "reason": "동문서답: 질문 의도보다 태도나 일반론을 강조" if n == 0 else ("구체성 결여: 본인의 구체적 Action 부재" if n == 1 else "정상")} for n, s in enumerate([s for s in re.split(r"(?<=[.!?])\s+", bad_a) if s])], "metrics_summary": "침묵 1회 발생, STAR 요소 중 Task, Action, Result 부족", "score": 1, "judgement_basis": "정량 감점이 있고 Action과 Result가 확인되지 않아 낮은 평가를 받았습니다."},
            ],
        )
    )


def remap_ids(row, mapping):
    for question in row["input"]["interview_session"]:
        question["id"] = mapping[question["id"]]

    summary = row["input"]["analysis_summary"]
    summary["best_id"] = mapping[summary["best_id"]]
    summary["worst_id"] = mapping[summary["worst_id"]]

    top = row["output"]["top_analysis"]
    top["best"]["id"] = mapping[top["best"]["id"]]
    top["worst"]["id"] = mapping[top["worst"]["id"]]

    for item in row["output"]["bottom_analysis"]:
        item["id"] = mapping[item["id"]]


id_rotations = [
    {"Q1": "Q1", "Q2": "Q2", "Q3": "Q3"},
    {"Q1": "Q2", "Q2": "Q3", "Q3": "Q1"},
    {"Q1": "Q3", "Q2": "Q1", "Q3": "Q2"},
    {"Q1": "Q2", "Q2": "Q1", "Q3": "Q3"},
    {"Q1": "Q3", "Q2": "Q2", "Q3": "Q1"},
]

for index, row in enumerate(rows):
    remap_ids(row, id_rotations[index % len(id_rotations)])


def validate(rows):
    assert len(rows) == 10
    for row in rows:
        assert set(row) == {"instruction", "input", "output"}
        session = row["input"]["interview_session"]
        assert len(session) == 3
        ids = {item["id"] for item in session}
        assert ids == {"Q1", "Q2", "Q3"}
        top = row["output"]["top_analysis"]
        assert row["input"]["analysis_summary"]["best_id"] == top["best"]["id"]
        assert row["input"]["analysis_summary"]["worst_id"] == top["worst"]["id"]
        for item in row["output"]["mid_analysis"]:
            assert item["status"] in {"PASS", "PARTIAL", "FAIL"}
        for item in row["output"]["bottom_analysis"]:
            assert item["id"] in ids
            assert isinstance(item["score"], int)
            assert 1 <= item["score"] <= 5
            source = next(q for q in session if q["id"] == item["id"])
            if not source["metrics"]["star_status"]["A"]:
                assert item["score"] <= 3


validate(rows)
OUTPUT.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
print(f"wrote {OUTPUT} with {len(rows)} rows")
