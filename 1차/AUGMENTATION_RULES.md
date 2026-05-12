# Dataset Augmentation Rules

이 문서는 `train_data_mixed.jsonl`을 기준으로 데이터를 증강할 때 반드시 유지해야 하는 규칙을 정의한다.

## 1. 기본 구조

각 JSONL row는 반드시 아래 최상위 구조를 유지한다. 아래 예시는 실제 값이 아니라 필드 타입과 의미를 나타내는 스키마 예시다.

```json
{
  "instruction": "<string: 생성 지시문>",
  "input": {
    "job_description": "<string: 채용공고 요약>",
    "analysis_summary": {
      "best_id": "<Q1|Q2|Q3>",
      "best_reason": "<string: 상단 BEST 선정 사유>",
      "worst_id": "<Q1|Q2|Q3>",
      "worst_reason": "<string: 상단 WORST 선정 사유>"
    },
    "interview_session": [
      {
        "id": "<Q1|Q2|Q3>",
        "question": "<string: 면접 질문>",
        "answer": "<string: 지원자 답변>",
        "metrics": {
          "cpm": "<number>",
          "dead_air_count": "<number>",
          "star_status": {
            "S": "<boolean>",
            "T": "<boolean>",
            "A": "<boolean>",
            "R": "<boolean>"
          }
        }
      }
    ]
  },
  "output": {
    "top_analysis": {
      "best": {
        "id": "<Q1|Q2|Q3>",
        "reason": "<string: BEST 분석>"
      },
      "worst": {
        "id": "<Q1|Q2|Q3>",
        "reason": "<string: WORST 분석>"
      }
    },
    "mid_analysis": [
      {
        "requirement": "<string: 공고 요구사항>",
        "status": "<PASS|PARTIAL|FAIL>",
        "analysis": "<string: Fit-Gap 분석>"
      }
    ],
    "bottom_analysis": [
      {
        "id": "<Q1|Q2|Q3>",
        "question": "<string: 면접 질문>",
        "sentences": [
          {
            "text": "<string: 문장 단위 답변>",
            "rule_id": "<null|1|2|3|4>",
            "reason": "<string: 판정 사유>"
          }
        ],
        "metrics_summary": "<string: 정량 지표 및 STAR 요약>",
        "score": "<integer: 1~5>",
        "judgement_basis": "<string: 최종 판단 근거>"
      }
    ]
  }
}
```

- `interview_session`은 항상 3개 문답으로 구성한다.
- 각 문답의 `id`는 `Q1`, `Q2`, `Q3`만 사용한다.
- `analysis_summary.best_id`, `analysis_summary.worst_id`, `output.top_analysis.best.id`, `output.top_analysis.worst.id`는 서로 일치해야 한다.
- `bottom_analysis[].id`는 `interview_session[].id`와 대응되어야 한다.

## 2. 상단 BEST/WORST 선정 기준

BEST/WORST는 오직 아래 기준으로만 선정한다.

### 정량 지표

- `cpm`이 350 초과이면 너무 빠른 답변으로 감점한다.
- `cpm`이 200 미만이면 너무 느린 답변으로 감점한다.
- `dead_air_count`가 1 이상이면 3초 이상 침묵 발생으로 감점한다.
- 문장별 단어 수가 25개를 초과하는 문장이 전체 문장의 30% 이상이면 만연체로 감점한다.
- 문장당 평균 단어 수 15~20개는 정상 범위로 본다.

### STAR 기준

- `S` Situation: 특정 시점, 프로젝트명, 소속, 자신의 역할 중 하나라도 있으면 `true`.
- `T` Task: 해결해야 했던 구체적인 목표나 문제 상황이 있으면 `true`.
- `A` Action: 팀이 아닌 본인 중심의 구체적인 기술, 방법, 실행이 있으면 `true`.
- `R` Result: 수치적 성과, 명확한 산출물, 또는 배운 점이 있으면 `true`.
- `A`가 `false`이면 최종 별점은 최대 3점으로 제한한다.

## 3. 중단 Fit-Gap Status

`mid_analysis[].status`는 아래 세 값만 사용한다.

```text
PASS
PARTIAL
FAIL
```

- `PASS`: 공고 요구사항을 구체적인 경험, 기술, 성과로 충분히 충족한다.
- `PARTIAL`: 관련 경험이나 기술 이해는 있으나 결과, 구체성, 전달력 중 일부가 부족하다.
- `FAIL`: 요구 역량을 검증할 수 없거나 질문 의도와 맞지 않는 답변이다.

`V`, `X`, `△` 같은 기호형 라벨은 사용하지 않는다.

## 4. 하단 평가 스크립트

`bottom_analysis`는 각 질문별 세부 평가를 담는다.

필수 필드 예시도 실제 값이 아니라 타입/의미 중심으로 작성한다.

```json
{
  "id": "<Q1|Q2|Q3>",
  "question": "<string: 면접 질문>",
  "sentences": [
    {
      "text": "<string: 문장 단위 답변>",
      "rule_id": "<null|1|2|3|4>",
      "reason": "<string: 판정 사유>"
    }
  ],
  "metrics_summary": "<string: 정량 지표 및 STAR 요약>",
  "score": "<integer: 1~5>",
  "judgement_basis": "<string: 최종 판단 근거>"
}
```

### Rule ID

- `null`: 정상 문장.
- `1`: 구체성 결여. 구체적인 Action, 기술, 방법론이 부족한 문장.
- `2`: 직무 적합도 오류. 공고와 무관한 경험을 강조하는 문장.
- `3`: 가독성 저하. 만연체, 접속사 남발, 지나치게 긴 문장.
- `4`: 동문서답. 질문 의도와 다른 방향으로 답한 문장.

## 5. Score 기준

`score`는 1~5 정수만 사용한다.

- `5`: 정량 감점 없음, STAR 4요소 충족, 답변이 구체적이다.
- `4`: 핵심 기준은 충족하지만 문장 품질이나 일부 근거가 약하다.
- `3`: 관련성은 있으나 STAR 일부 누락, 만연체, 결과 부족 등이 있다.
- `2`: 정량 감점 또는 STAR 누락이 크며 실무 역량 검증이 제한적이다.
- `1`: 질문 의도와 맞지 않거나 Action/Result가 거의 없고 답변 신뢰도가 낮다.

`Action`이 없으면 점수는 최대 3점이다.

## 6. 문장 품질 규칙

증강 데이터의 출력 문장은 아래 표현을 지킨다.

- STAR 용어는 `Situation`, `Task`, `Action`, `Result`로 통일한다.
- status는 `PASS`, `PARTIAL`, `FAIL`로 통일한다.
- `BEST`, `WORST`는 대문자로 표기한다.
- `CPM 290으로`보다 `CPM 수치가 290으로`처럼 자연스러운 표현을 사용한다.
- `3초 이상 침묵 없습니다`는 사용하지 않고 `3초 이상 침묵이 없습니다`로 쓴다.
- `장황하고가독성`, `장황하여가독성`처럼 띄어쓰기나 조사가 깨진 문장을 만들지 않는다.
- `부족됨`보다 `부족합니다`를 사용한다.
- `행동`, `결과`를 STAR 용어로 쓸 때는 `Action`, `Result`로 표기한다.

## 7. 증강 시 유지해야 할 균형

- 각 row는 좋은 답변 1개, 중간 답변 1개, 나쁜 답변 1개가 섞이도록 구성하는 것을 권장한다.
- BEST/WORST 위치는 `Q1`, `Q2`, `Q3`에 고르게 분산한다.
- 좋은 답변을 항상 `Q1`, 나쁜 답변을 항상 `Q3`에 배치하지 않는다.
- 답변 품질과 질문 ID 사이에 고정된 패턴이 생기면 안 된다. 모델이 답변 내용을 보지 않고 위치만으로 BEST/WORST를 예측할 수 있기 때문이다.
- 10개 단위 증강 배치에서는 BEST와 WORST가 각각 `Q1`, `Q2`, `Q3`에 최소 2회 이상 등장하도록 한다.
- 동일한 BEST/WORST 조합이 과도하게 반복되지 않도록 한다. 예를 들어 `BEST=Q1`, `WORST=Q3` 조합만 반복되는 데이터는 폐기하거나 재배치한다.
- 직무 도메인은 백엔드, 프론트엔드, 데이터, AI, 임베디드, 모바일, 클라우드, 보안, 게임 등으로 다양화한다.
- 같은 문장 템플릿을 반복하지 말고 질문, 답변, 평가 사유를 직무별로 변형한다.

## 8. 검증 체크리스트

증강 후 반드시 확인한다.

- 모든 줄이 JSON으로 파싱되는가?
- 각 row에 `instruction`, `input`, `output`이 존재하는가?
- `interview_session`은 정확히 3개인가?
- `status` 값은 `PASS`, `PARTIAL`, `FAIL` 중 하나인가?
- `score`는 1~5 정수인가?
- BEST/WORST ID가 `analysis_summary`와 `top_analysis`에서 일치하는가?
- BEST ID 분포가 `Q1`, `Q2`, `Q3`에 분산되어 있는가?
- WORST ID 분포가 `Q1`, `Q2`, `Q3`에 분산되어 있는가?
- 모든 row가 `BEST=Q1`, `WORST=Q3`처럼 같은 위치 패턴을 반복하지 않는가?
- `Action`이 false인 답변의 점수가 3점을 초과하지 않는가?
- 깨진 표현이나 어색한 붙임말이 없는가?
