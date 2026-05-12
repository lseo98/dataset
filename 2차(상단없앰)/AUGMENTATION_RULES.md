# 2차 Dataset Augmentation Rules

이 문서는 2차 데이터셋을 만들기 전 유지해야 할 기준을 정의한다.

2차 데이터셋의 목표는 LLM이 상단 BEST/WORST 분석을 생성하지 않고, 공고-답변 적합도 분석과 문장 단위 진단만 생성하도록 학습시키는 것이다.

## 0. Professional Schema Naming

2차 데이터셋은 위치 중심 이름 대신 역할 중심 이름을 사용한다.

| 기존 변수명 | 2차 변수명 | 의미 |
| --- | --- | --- |
| `mid_analysis` | `fit_gap_analysis` | 공고 요구사항과 답변 사이의 적합도 분석 |
| `bottom_analysis` | `sentence_diagnosis` | 질문별 문장 단위 진단 |
| `score` | `qualitative_score` | 정량 계산값과 구분되는 정성적 논리 점수 |
| `analysis` | `gap_rationale` | PASS, PARTIAL, FAIL 판정의 근거 |

## 1. 기본 구조

각 JSONL row는 반드시 아래 최상위 구조를 유지한다.

```json
{
  "instruction": "IT 전문 면접관으로서 제공된 채용공고와 3개의 면접 문답을 평가하십시오. 출력은 반드시 output.fit_gap_analysis와 output.sentence_diagnosis만 작성하십시오. fit_gap_analysis에서는 채용공고 요구사항 또는 질문 의도별로 PASS, PARTIAL, FAIL 중 하나를 판정하고 gap_rationale에 그 근거를 작성하십시오. sentence_diagnosis에서는 각 질문의 답변을 문장 단위로 나누어 rule_id, reason, metrics_summary, qualitative_score, judgement_basis를 작성하십시오. 모든 판단은 오직 정량 지표, STAR 기준, Fit-Gap 기준, 문장 단위 위반 규칙에 근거해야 합니다.",
  "input": {
    "job_description": "<string: 채용공고 요약>",
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
    "fit_gap_analysis": [
      {
        "requirement": "<string: 공고 요구사항 또는 질문 의도>",
        "status": "<PASS|PARTIAL|FAIL>",
        "gap_rationale": "<string: Fit-Gap 판정 근거>"
      }
    ],
    "sentence_diagnosis": [
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
        "qualitative_score": "<integer: 1~5>",
        "judgement_basis": "<string: 최종 판단 근거>"
      }
    ]
  }
}
```

- `interview_session`은 항상 3개 문답으로 구성한다.
- 각 문답의 `id`는 `Q1`, `Q2`, `Q3`만 사용한다.
- `output`에는 `top_analysis`를 넣지 않는다.
- `input`에는 `analysis_summary`를 넣지 않는다.
- `instruction`에도 상단, BEST/WORST, 최상위 요약 생성을 요구하는 문구를 넣지 않는다.
- `sentence_diagnosis[].id`는 `interview_session[].id`와 대응되어야 한다.

## 2. 생성 대상

2차 데이터셋에서 LLM이 생성해야 하는 출력은 아래 두 영역뿐이다.

- `fit_gap_analysis`: 채용공고 요구사항과 답변 간 Fit-Gap 평가.
- `sentence_diagnosis`: 질문별 문장 단위 진단, 정량 지표 요약, 정성 점수, 최종 판단 근거.

아래 항목은 생성 대상에서 제외한다.

- BEST 답변 선정.
- WORST 답변 선정.
- BEST/WORST 선정 사유.
- 상단 요약 보고서.
- `top_analysis` 객체.
- `analysis_summary` 객체.

## 3. Instruction 고정값

모든 JSONL row의 `instruction`은 아래 문장으로 통일한다. 변형하거나 축약하지 않는다.

고정 문장:

```text
IT 전문 면접관으로서 제공된 채용공고와 3개의 면접 문답을 평가하십시오. 출력은 반드시 output.fit_gap_analysis와 output.sentence_diagnosis만 작성하십시오. fit_gap_analysis에서는 채용공고 요구사항 또는 질문 의도별로 PASS, PARTIAL, FAIL 중 하나를 판정하고 gap_rationale에 그 근거를 작성하십시오. sentence_diagnosis에서는 각 질문의 답변을 문장 단위로 나누어 rule_id, reason, metrics_summary, qualitative_score, judgement_basis를 작성하십시오. 모든 판단은 오직 정량 지표, STAR 기준, Fit-Gap 기준, 문장 단위 위반 규칙에 근거해야 합니다.
```

Instruction 작성 시 지켜야 할 사항:

- 모든 row에서 위 고정 문장을 그대로 사용한다.
- `output.fit_gap_analysis`와 `output.sentence_diagnosis` 외의 출력 영역을 요구하지 않는다.
- `fit_gap_analysis`에는 `requirement`, `status`, `gap_rationale`를 작성하게 한다.
- `sentence_diagnosis`에는 `id`, `question`, `sentences`, `metrics_summary`, `qualitative_score`, `judgement_basis`를 작성하게 한다.

사용하지 말아야 할 표현:

- 상단 보고서를 생성하십시오.
- BEST/WORST를 선정하십시오.
- 가장 좋은 답변과 가장 나쁜 답변을 고르십시오.
- `top_analysis`를 작성하십시오.

## 4. 정량 지표 기준

- `cpm`이 350 초과이면 너무 빠른 답변으로 감점한다.
- `cpm`이 200 미만이면 너무 느린 답변으로 감점한다.
- `dead_air_count`가 1 이상이면 3초 이상 침묵 발생으로 감점한다.
- 문장별 단어 수가 25개를 초과하는 문장이 전체 문장의 30% 이상이면 만연체로 감점한다.
- 문장당 평균 단어 수 15~20개는 정상 범위로 본다.

정량 지표는 `sentence_diagnosis[].metrics_summary`, `sentence_diagnosis[].qualitative_score`, `sentence_diagnosis[].judgement_basis`에 반영한다.

## 5. STAR 기준

- `S` Situation: 특정 시점, 프로젝트명, 소속, 자신의 역할 중 하나라도 있으면 `true`.
- `T` Task: 해결해야 했던 구체적인 목표나 문제 상황이 있으면 `true`.
- `A` Action: 팀이 아닌 본인 중심의 구체적인 기술, 방법, 실행이 있으면 `true`.
- `R` Result: 수치적 성과, 명확한 산출물, 또는 배운 점이 있으면 `true`.
- `A`가 `false`이면 최종 별점은 최대 3점으로 제한한다.

## 6. Fit-Gap Status

`fit_gap_analysis[].status`는 아래 세 값만 사용한다.

```text
PASS
PARTIAL
FAIL
```

- `PASS`: 공고 요구사항을 구체적인 경험, 기술, 성과로 충분히 충족한다.
- `PARTIAL`: 관련 경험이나 기술 이해는 있으나 결과, 구체성, 전달력 중 일부가 부족하다.
- `FAIL`: 요구 역량을 검증할 수 없거나 질문 의도와 맞지 않는 답변이다.

`V`, `X`, `△` 같은 기호형 라벨은 사용하지 않는다.

## 7. 문장 단위 진단

`sentence_diagnosis`는 각 질문별 세부 평가를 담는다.

필수 필드:

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
  "qualitative_score": "<integer: 1~5>",
  "judgement_basis": "<string: 최종 판단 근거>"
}
```

### Rule ID

- `null`: 정상 문장.
- `1`: 구체성 결여. 구체적인 Action, 기술, 방법론이 부족한 문장.
- `2`: 직무 적합도 오류. 공고와 무관한 경험을 강조하는 문장.
- `3`: 가독성 저하. 만연체, 접속사 남발, 지나치게 긴 문장.
- `4`: 동문서답. 질문 의도와 다른 방향으로 답한 문장.

## 8. Qualitative Score 기준

`qualitative_score`는 1~5 정수만 사용한다.

- `5`: 정량 감점 없음, STAR 4요소 충족, 답변이 구체적이다.
- `4`: 핵심 기준은 충족하지만 문장 품질이나 일부 근거가 약하다.
- `3`: 관련성은 있으나 STAR 일부 누락, 만연체, 결과 부족 등이 있다.
- `2`: 정량 감점 또는 STAR 누락이 크며 실무 역량 검증이 제한적이다.
- `1`: 질문 의도와 맞지 않거나 Action/Result가 거의 없고 답변 신뢰도가 낮다.

`Action`이 없으면 점수는 최대 3점이다.

## 9. 문장 품질 규칙

증강 데이터의 출력 문장은 아래 표현을 지킨다.

- STAR 용어는 `Situation`, `Task`, `Action`, `Result`로 통일한다.
- status는 `PASS`, `PARTIAL`, `FAIL`로 통일한다.
- `CPM 290으로`보다 `CPM 수치가 290으로`처럼 자연스러운 표현을 사용한다.
- `3초 이상 침묵 없습니다`는 사용하지 않고 `3초 이상 침묵이 없습니다`로 쓴다.
- `장황하고가독성`, `장황하여가독성`처럼 띄어쓰기나 조사가 깨진 문장을 만들지 않는다.
- `부족됨`보다 `부족합니다`를 사용한다.
- `행동`, `결과`를 STAR 용어로 쓸 때는 `Action`, `Result`로 표기한다.
- 상단 분석을 암시하는 `BEST`, `WORST`, `최고 답변`, `최저 답변` 표현은 사용하지 않는다.

## 10. 증강 시 유지해야 할 균형

- 각 row는 좋은 답변 1개, 중간 답변 1개, 나쁜 답변 1개가 섞이도록 구성하는 것을 권장한다.
- 단, 좋은 답변과 나쁜 답변을 명시적으로 BEST/WORST로 라벨링하지 않는다.
- 답변 품질과 질문 ID 사이에 고정된 패턴이 생기면 안 된다.
- 좋은 답변을 항상 `Q1`, 나쁜 답변을 항상 `Q3`에 배치하지 않는다.
- 10개 단위 증강 배치에서는 고득점 답변과 저득점 답변의 위치가 `Q1`, `Q2`, `Q3`에 고르게 분산되도록 한다.
- 직무 도메인은 백엔드, 프론트엔드, 데이터, AI, 임베디드, 모바일, 클라우드, 보안, 게임 등으로 다양화한다.
- 같은 문장 템플릿을 반복하지 말고 질문, 답변, 평가 사유를 직무별로 변형한다.

## 11. 검증 체크리스트

증강 후 반드시 확인한다.

- 모든 줄이 JSON으로 파싱되는가?
- 각 row에 `instruction`, `input`, `output`이 존재하는가?
- `instruction`이 3번 섹션의 고정 문장과 정확히 일치하는가?
- `input`에 `analysis_summary`가 없는가?
- `output`에 `top_analysis`가 없는가?
- `instruction`에 상단 또는 BEST/WORST 생성을 요구하는 문구가 없는가?
- `interview_session`은 정확히 3개인가?
- `fit_gap_analysis`가 존재하는가?
- `fit_gap_analysis[].gap_rationale`가 존재하는가?
- `sentence_diagnosis`는 정확히 3개인가?
- `sentence_diagnosis[].id`가 `interview_session[].id`와 대응되는가?
- `status` 값은 `PASS`, `PARTIAL`, `FAIL` 중 하나인가?
- `qualitative_score`는 1~5 정수인가?
- `Action`이 false인 답변의 점수가 3점을 초과하지 않는가?
- 깨진 표현이나 어색한 붙임말이 없는가?
