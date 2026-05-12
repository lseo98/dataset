import json
import re
from collections import Counter
from pathlib import Path


OUTPUT = Path("sanity_check_extra_10.jsonl")

INSTRUCTION = (
    "IT 전문 면접관으로서 제공된 문답과 분석 데이터를 바탕으로 상단(BEST/WORST), "
    "중단(Fit-Gap), 하단(평가 스크립트) 보고서를 생성하십시오. 모든 판단은 오직 "
    "[정량 지표], [STAR 기준], [Fit-Gap 기준], [문장 단위 위반 규칙]에 의거해야 합니다."
)

GOOD_STAR = {"S": True, "T": True, "A": True, "R": True}
MID_STAR = {"S": True, "T": True, "A": True, "R": False}
BAD_STAR = {"S": True, "T": False, "A": False, "R": False}

PATTERNS = [
    {"good": "Q1", "mid": "Q2", "bad": "Q3"},
    {"good": "Q2", "mid": "Q3", "bad": "Q1"},
    {"good": "Q3", "mid": "Q1", "bad": "Q2"},
    {"good": "Q2", "mid": "Q1", "bad": "Q3"},
    {"good": "Q3", "mid": "Q2", "bad": "Q1"},
    {"good": "Q1", "mid": "Q3", "bad": "Q2"},
    {"good": "Q2", "mid": "Q3", "bad": "Q1"},
    {"good": "Q3", "mid": "Q1", "bad": "Q2"},
    {"good": "Q1", "mid": "Q2", "bad": "Q3"},
    {"good": "Q2", "mid": "Q1", "bad": "Q3"},
]


CASES = [
    {
        "job": "Platform Engineer - 내부 개발자 플랫폼, Kubernetes 기반 셀프서비스 배포, 관측성 도구 운영 경험자",
        "good_q": "개발자 배포 경험을 개선한 사례가 있나요?",
        "good_a": "작년 사내 플랫폼에서 서비스 배포 요청이 운영팀 티켓으로 몰려 평균 2일이 걸리는 문제가 있었습니다. 저는 Argo CD와 Helm 템플릿을 표준화하고 개발자가 직접 배포할 수 있는 셀프서비스 워크플로우를 구축했습니다. 그 결과 배포 리드타임이 2일에서 30분으로 줄었고 운영팀 반복 요청도 크게 감소했습니다.",
        "mid_q": "관측성 도구를 설계할 때 어떤 기준을 보나요?",
        "mid_a": "저는 로그와 메트릭과 트레이스를 함께 봐야 한다고 생각해서 서비스별 대시보드와 알림 규칙과 공통 태그 기준을 만들었으며 실제 운영에서도 원인 파악이 더 쉬워졌지만 장애 탐지 시간이 얼마나 줄었는지는 별도로 측정하지 못했습니다.",
        "bad_q": "플랫폼 장애가 생기면 어떻게 대응하나요?",
        "bad_a": "저는 장애가 생기면 책임감 있게 끝까지 남습니다. 플랫폼은 모두가 쓰는 것이기 때문에 성실한 태도가 중요합니다. 팀원들과 잘 이야기하면서 최대한 빠르게 처리하겠습니다.",
    },
    {
        "job": "Computer Vision Engineer - 객체 탐지 모델 학습, 데이터 라벨링 품질 관리, 모델 경량화 경험자",
        "good_q": "객체 탐지 모델 성능을 개선한 경험이 있나요?",
        "good_a": "물류 박스 탐지 모델에서 작은 객체의 미탐률이 높은 문제가 있었습니다. 저는 라벨 오류 샘플을 재검수하고 작은 객체 비율을 높인 학습 세트를 구성했으며 anchor 설정도 조정했습니다. 검증 결과 mAP가 0.71에서 0.82로 상승했고 현장 오탐 알림도 줄었습니다.",
        "mid_q": "모델 경량화를 진행할 때 무엇을 고려하나요?",
        "mid_a": "저는 정확도와 추론 속도의 균형이 중요하다고 생각해서 pruning과 quantization을 비교하고 입력 해상도와 배치 크기와 디바이스 환경을 함께 확인했지만 실제 서비스에서 latency가 얼마나 줄었는지는 별도로 정리하지 못했습니다.",
        "bad_q": "데이터 라벨 품질이 낮으면 어떻게 하나요?",
        "bad_a": "라벨링은 사람이 하는 일이라 실수가 있을 수 있습니다. 저는 꼼꼼한 성격이라 데이터를 보면 이상한 점을 잘 찾습니다. 필요하면 라벨러들과 소통하면서 좋은 분위기로 해결하겠습니다.",
    },
    {
        "job": "Payment Backend Developer - 결제 승인 API, 멱등성 처리, 정산 배치 운영 경험자",
        "good_q": "중복 결제 문제를 해결한 경험이 있나요?",
        "good_a": "모바일 네트워크 재시도로 동일 결제 요청이 중복 승인되는 문제가 있었습니다. 저는 주문 번호와 요청 토큰을 기준으로 멱등성 키를 저장하고 승인 처리 전에 상태를 검증하도록 API 흐름을 변경했습니다. 이후 중복 승인 건수가 0건으로 줄었고 고객 환불 CS도 감소했습니다.",
        "mid_q": "정산 배치를 설계할 때 중요하게 보는 점은 무엇인가요?",
        "mid_a": "저는 정산은 정확성이 가장 중요하다고 생각해서 원장 데이터와 결제사 대사 파일과 실패 재처리 이력을 함께 확인하고 재실행 가능한 구조로 만들려고 했지만 실제 정산 오류율 개선 수치를 별도로 기록하지는 못했습니다.",
        "bad_q": "결제 장애가 나면 어떻게 하나요?",
        "bad_a": "결제는 돈과 관련된 일이라 매우 신중해야 합니다. 저는 침착하게 고객 입장에서 생각하고 책임감 있게 대응하겠습니다. 문제가 생기면 팀원들과 함께 최선을 다해 해결하겠습니다.",
    },
    {
        "job": "Frontend Performance Engineer - Core Web Vitals 개선, 번들 최적화, 대규모 SPA 성능 분석 경험자",
        "good_q": "웹 성능 지표를 개선한 경험이 있나요?",
        "good_a": "상품 상세 페이지의 LCP가 4초 이상으로 느려 전환율이 떨어지는 문제가 있었습니다. 저는 이미지 preload 우선순위를 조정하고 route 기반 code splitting을 적용했으며 사용하지 않는 라이브러리를 제거했습니다. 배포 후 LCP가 1.9초로 개선되었고 상세 페이지 이탈률도 감소했습니다.",
        "mid_q": "번들 크기를 줄일 때 어떤 방법을 사용하나요?",
        "mid_a": "저는 번들이 커지면 초기 로딩이 느려진다고 생각해서 webpack analyzer로 큰 모듈을 확인하고 dynamic import와 tree shaking을 적용하려고 했으며 실제로 일부 화면은 가벼워졌지만 전체 번들 크기 감소율은 따로 정리하지 못했습니다.",
        "bad_q": "사용자가 느리다고 하면 어떻게 대응하나요?",
        "bad_a": "사용자 의견을 잘 듣는 것이 중요합니다. 저는 피드백을 긍정적으로 받아들이고 더 좋은 화면을 만들려고 노력합니다. 디자인과 개발 모두 사용자를 생각해야 한다고 봅니다.",
    },
    {
        "job": "Security Analyst - SIEM 룰 튜닝, 침해 지표 분석, 보안 이벤트 대응 경험자",
        "good_q": "오탐이 많은 탐지 룰을 개선한 경험이 있나요?",
        "good_a": "VPN 로그인 실패 이벤트가 과도하게 발생해 관제 알림 피로도가 높았습니다. 저는 정상 사용자 패턴과 공격 의심 패턴을 분리하고 국가, 시간대, 실패 횟수를 조합한 조건으로 SIEM 룰을 재설계했습니다. 이후 오탐 알림이 65% 감소했고 실제 의심 이벤트 대응 속도가 빨라졌습니다.",
        "mid_q": "침해 지표를 분석할 때 어떤 절차를 따르나요?",
        "mid_a": "저는 IP와 도메인과 해시 값을 먼저 확인하고 내부 로그와 외부 평판 정보를 함께 비교하며 연관 이벤트를 추적하는 방식으로 분석했지만 분석 결과가 탐지 정확도에 얼마나 기여했는지는 별도 수치로 관리하지 못했습니다.",
        "bad_q": "보안 이벤트가 많이 쌓이면 어떻게 하나요?",
        "bad_a": "보안 업무는 집중력이 중요합니다. 이벤트가 많아도 저는 포기하지 않고 하나씩 확인할 자신이 있습니다. 평소 책임감이 강해서 위험한 상황도 잘 버틸 수 있습니다.",
    },
    {
        "job": "Data Platform Engineer - Kafka, Flink, 실시간 처리 파이프라인 운영 경험자",
        "good_q": "실시간 파이프라인 지연을 줄인 경험이 있나요?",
        "good_a": "클릭 스트림 처리에서 피크 시간대 이벤트 지연이 10분 이상 발생했습니다. 저는 Flink 체크포인트 간격과 Kafka 파티션 분배를 조정하고 느린 외부 저장소 쓰기를 비동기 배치로 전환했습니다. 그 결과 평균 처리 지연이 45초 이하로 줄었고 알림 누락도 해소되었습니다.",
        "mid_q": "스트리밍 잡을 운영할 때 중요하게 보는 지표는 무엇인가요?",
        "mid_a": "저는 lag과 처리량과 checkpoint 실패율과 backpressure를 함께 봐야 한다고 생각해서 대시보드를 구성하고 알림도 설정했지만 실제 장애 예방 효과를 수치로 정리하지는 못했습니다.",
        "bad_q": "데이터가 늦게 들어오면 어떻게 하나요?",
        "bad_a": "데이터는 언젠가 들어오기 때문에 너무 조급해하지 않는 것도 중요합니다. 저는 차분하게 기다리면서 팀에 상황을 공유하겠습니다. 성실하게 확인하면 대부분 해결된다고 생각합니다.",
    },
    {
        "job": "Embedded Linux Engineer - Yocto, 디바이스 드라이버, 부팅 시간 최적화 경험자",
        "good_q": "임베디드 장비의 부팅 시간을 줄인 경험이 있나요?",
        "good_a": "산업용 게이트웨이 장비의 부팅 시간이 70초 이상 걸려 현장 재시작 시간이 길었습니다. 저는 systemd-analyze로 병목 서비스를 찾고 불필요한 데몬을 제거했으며 드라이버 초기화 순서를 병렬화했습니다. 최종적으로 부팅 시간을 32초로 줄여 현장 복구 시간을 단축했습니다.",
        "mid_q": "디바이스 드라이버 디버깅 시 어떤 정보를 먼저 보나요?",
        "mid_a": "저는 커널 로그와 인터럽트 상태와 레지스터 값을 먼저 확인하고 데이터시트를 보며 초기화 순서를 비교하는 방식으로 접근했지만 문제 해결 전후의 재발률이나 디버깅 시간 개선을 수치화하지는 못했습니다.",
        "bad_q": "하드웨어 이슈가 생기면 어떻게 하나요?",
        "bad_a": "하드웨어는 예민하기 때문에 조심스럽게 다뤄야 합니다. 저는 손재주가 좋은 편이고 장비를 소중히 다룹니다. 문제가 있으면 주변 사람들에게 물어보면서 해결하겠습니다.",
    },
    {
        "job": "CRM Backend Developer - 고객 세그먼트 API, 캠페인 발송 시스템, 대량 배치 처리 경험자",
        "good_q": "대량 캠페인 발송 성능을 개선한 경험이 있나요?",
        "good_a": "마케팅 캠페인 발송 시 대상자 300만 명을 처리하는 데 5시간 이상 걸리는 문제가 있었습니다. 저는 세그먼트 조회 쿼리를 분할하고 발송 작업을 큐 기반 워커로 병렬화했습니다. 이후 전체 발송 시간이 90분으로 줄었고 재시도 실패율도 낮아졌습니다.",
        "mid_q": "고객 세그먼트 조건이 복잡해질 때 어떻게 관리하나요?",
        "mid_a": "저는 조건이 늘어나면 관리가 어려워진다고 생각해서 필터 정의를 공통 DSL 형태로 관리하고 화면과 API가 같은 조건 해석 로직을 쓰도록 맞췄지만 운영자가 조건을 만드는 시간이 얼마나 줄었는지는 측정하지 못했습니다.",
        "bad_q": "고객 데이터 요청이 많으면 어떻게 하나요?",
        "bad_a": "고객 데이터는 중요하므로 신중하게 봐야 합니다. 저는 요청이 많아도 친절하게 응대하고 필요한 자료를 빠르게 전달하려고 노력합니다. 책임감을 가지고 처리하겠습니다.",
    },
    {
        "job": "Cloud Security Engineer - IAM 권한 관리, CSPM, 클라우드 보안 자동화 경험자",
        "good_q": "과도한 클라우드 권한을 줄인 경험이 있나요?",
        "good_a": "여러 프로젝트 계정에서 관리자 권한이 넓게 부여되어 감사 지적을 받은 적이 있었습니다. 저는 IAM 사용 로그를 분석해 실제 사용 권한만 남기는 최소 권한 정책을 재설계하고 Terraform으로 배포했습니다. 그 결과 고위험 권한 부여 건수가 80% 감소했습니다.",
        "mid_q": "CSPM 알림을 운영할 때 중요하게 보는 점은 무엇인가요?",
        "mid_a": "저는 알림이 많으면 중요한 위험을 놓칠 수 있다고 생각해서 심각도와 리소스 노출 범위와 인터넷 접근 여부를 기준으로 우선순위를 나누었지만 오탐률이나 평균 조치 시간을 지표로 관리하지는 못했습니다.",
        "bad_q": "보안 감사가 들어오면 어떻게 하나요?",
        "bad_a": "감사는 긴장되지만 성실하게 임하면 된다고 생각합니다. 저는 자료를 잘 정리하고 담당자에게 친절하게 설명하겠습니다. 평소에도 정직하게 일하려고 노력합니다.",
    },
    {
        "job": "Game Server Engineer - 실시간 매치메이킹, WebSocket, Redis 기반 세션 관리 경험자",
        "good_q": "매치메이킹 대기 시간을 줄인 경험이 있나요?",
        "good_a": "랭크전 피크 시간대에 특정 티어 사용자의 매칭 대기 시간이 90초를 넘는 문제가 있었습니다. 저는 Redis sorted set으로 대기열을 재구성하고 시간이 지날수록 매칭 범위를 점진적으로 확장하는 로직을 적용했습니다. 그 결과 평균 대기 시간이 38초로 줄었고 매칭 실패율도 감소했습니다.",
        "mid_q": "실시간 세션을 관리할 때 중요하게 보는 점은 무엇인가요?",
        "mid_a": "저는 연결 상태와 재접속 처리와 세션 만료 정책이 중요하다고 생각해서 Redis TTL과 heartbeat를 활용하고 서버 재시작 시 복구 흐름도 고려했지만 실제 재접속 성공률 개선 수치는 따로 정리하지 못했습니다.",
        "bad_q": "게임 서버가 불안정하면 어떻게 하나요?",
        "bad_a": "게임은 재미가 중요하기 때문에 사용자가 불편하지 않게 노력해야 합니다. 저는 문제가 생기면 빠르게 공지하고 열심히 고치겠습니다. 팀 분위기를 좋게 유지하는 것도 중요하다고 생각합니다.",
    },
]


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def word_counts(text):
    return [len(re.findall(r"\S+", sentence)) for sentence in split_sentences(text)]


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
    return "3초 이상 침묵이 없습니다" if dead_air_count == 0 else f"3초 이상 침묵이 {dead_air_count}회 발생했습니다"


def star_text(star):
    names = {"S": "Situation", "T": "Task", "A": "Action", "R": "Result"}
    passed = [names[key] for key in ("S", "T", "A", "R") if star[key]]
    missing = [names[key] for key in ("S", "T", "A", "R") if not star[key]]
    if not missing:
        return "STAR 4요소(Situation, Task, Action, Result) 모두 충족합니다"
    return f"STAR 충족 요소는 {', '.join(passed) if passed else '없음'}이며, 부족 요소는 {', '.join(missing)}입니다"


def top_reason(question, kind):
    metrics = question["metrics"]
    _, counts, verbose = evaluate(question)
    concision = (
        f"문장별 단어 수({', '.join(map(str, counts))}) 기준으로 만연체에 해당합니다"
        if verbose
        else f"문장별 단어 수({', '.join(map(str, counts))}) 기준으로 만연체는 아닙니다"
    )
    base = f"{cpm_text(metrics['cpm'])}이며, {silence_text(metrics['dead_air_count'])}. {concision}. {star_text(metrics['star_status'])}."
    if kind == "best":
        return base + " 정량 감점이 없고 STAR 기준 충족도가 가장 높아 BEST 답변으로 판단됩니다."
    return base + " 정량 감점과 STAR 누락이 가장 커 WORST 답변으로 판단됩니다."


def make_question(id_, question, answer, kind, index):
    if kind == "good":
        cpm, dead_air, star = 284 + index, 0, GOOD_STAR
    elif kind == "mid":
        cpm, dead_air, star = 326 + index, 0, MID_STAR
    else:
        cpm, dead_air, star = 228 + index, 1, BAD_STAR
    return {"id": id_, "question": question, "answer": answer, "metrics": {"cpm": cpm, "dead_air_count": dead_air, "star_status": star}}


def bottom_item(question, kind):
    if kind == "good":
        return {
            "id": question["id"],
            "question": question["question"],
            "sentences": [{"text": sentence, "rule_id": None, "reason": "정상"} for sentence in split_sentences(question["answer"])],
            "metrics_summary": "CPM 정상, 침묵 0회, STAR 4요소 충족",
            "score": 5,
            "judgement_basis": "정량 감점이 없고 STAR 4요소가 모두 명확합니다.",
        }
    if kind == "mid":
        return {
            "id": question["id"],
            "question": question["question"],
            "sentences": [{"text": question["answer"], "rule_id": 3, "reason": "가독성 저하: 여러 내용을 한 문장에 길게 연결한 만연체"}],
            "metrics_summary": "침묵 0회, STAR 요소 중 Result 부족, 만연체 감점",
            "score": 3,
            "judgement_basis": "Action은 있으나 Result가 부족하고 문장이 장황하여 3점으로 평가됩니다.",
        }
    sentences = []
    for idx, sentence in enumerate(split_sentences(question["answer"])):
        if idx == 0:
            rule_id, reason = 4, "동문서답: 질문 의도보다 태도나 일반론을 강조"
        elif idx == 1:
            rule_id, reason = 1, "구체성 결여: 본인의 구체적 Action 부재"
        else:
            rule_id, reason = None, "정상"
        sentences.append({"text": sentence, "rule_id": rule_id, "reason": reason})
    return {
        "id": question["id"],
        "question": question["question"],
        "sentences": sentences,
        "metrics_summary": "침묵 1회 발생, STAR 요소 중 Task, Action, Result 부족",
        "score": 1,
        "judgement_basis": "정량 감점이 있고 Action과 Result가 확인되지 않아 낮은 평가를 받았습니다.",
    }


def make_row(case, pattern, index):
    questions_by_kind = {
        "good": make_question(pattern["good"], case["good_q"], case["good_a"], "good", index),
        "mid": make_question(pattern["mid"], case["mid_q"], case["mid_a"], "mid", index),
        "bad": make_question(pattern["bad"], case["bad_q"], case["bad_a"], "bad", index),
    }
    session = sorted(questions_by_kind.values(), key=lambda item: item["id"])
    scored = [(question, evaluate(question)[0]) for question in session]
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
                {"requirement": case["good_q"].replace("?", ""), "status": "PASS", "analysis": f"{pattern['good']} 답변에서 구체적인 Action과 Result가 확인되어 요구 역량을 충족합니다."},
                {"requirement": case["mid_q"].replace("?", ""), "status": "PARTIAL", "analysis": f"{pattern['mid']} 답변에서 관련 Action은 확인되나 정량적 Result가 부족합니다."},
                {"requirement": case["bad_q"].replace("?", ""), "status": "FAIL", "analysis": f"{pattern['bad']} 답변은 태도나 일반론 중심으로 구성되어 구체적인 Task, Action, Result를 검증하기 어렵습니다."},
            ],
            "bottom_analysis": [
                bottom_item(questions_by_kind["good"], "good"),
                bottom_item(questions_by_kind["mid"], "mid"),
                bottom_item(questions_by_kind["bad"], "bad"),
            ],
        },
    }


rows = [make_row(case, PATTERNS[index], index) for index, case in enumerate(CASES)]


def validate(rows):
    assert len(rows) == 10
    best_counts = Counter()
    worst_counts = Counter()
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
        for item in row["output"]["mid_analysis"]:
            assert item["status"] in {"PASS", "PARTIAL", "FAIL"}
        for item in row["output"]["bottom_analysis"]:
            assert item["id"] in ids
            assert isinstance(item["score"], int)
            assert 1 <= item["score"] <= 5
            source = next(question for question in session if question["id"] == item["id"])
            if not source["metrics"]["star_status"]["A"]:
                assert item["score"] <= 3
    assert all(best_counts[qid] >= 2 for qid in ("Q1", "Q2", "Q3"))
    assert all(worst_counts[qid] >= 2 for qid in ("Q1", "Q2", "Q3"))


validate(rows)
OUTPUT.write_text("\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
print(f"wrote {OUTPUT} with {len(rows)} rows")
