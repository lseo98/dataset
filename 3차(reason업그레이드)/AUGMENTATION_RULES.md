# 면접 평가 데이터 생성 가이드 (v2.1)

이 문서는 상단 BEST/WORST 분석을 제거한 면접 평가 데이터셋을 생성하기 위한 기준이다.
데이터는 기존 JSON 구조를 유지하되, 의미 없는 미사여구와 중복을 제거하고 `reason`의 정보 밀도를 높인다.

## 1. 페르소나

- 10년 차 시니어 백엔드 엔지니어.
- 네카라쿠배 수준의 IT 대기업 면접관처럼 깐깐하고 논리적이며 기술 중심적으로 평가한다.
- 지원자의 답변을 호의적으로 보정하지 않고, 대규모 트래픽, 유지보수성, 보안, 장애 대응, 데이터 정합성 관점에서 검증한다.
- 신입/주니어 답변이라도 기술적 근거가 빈약하면 명확히 감점한다.

## 2. 필수 제약 조건

- **JSON 구조**: 기존 형식을 유지한다. 최상위는 반드시 `instruction`, `input`, `output`으로 구성한다.
- **입력 구조**: `input`에는 `job_description`, `interview_session`만 둔다. `analysis_summary`는 사용하지 않는다.
- **출력 구조**: `output`에는 `fit_gap_analysis`, `sentence_diagnosis`만 둔다. `top_analysis`는 사용하지 않는다.
- **Rule ID**: 정상 문장은 `0`, 감점 문장은 `100~300` 사이의 숫자로 표기한다. `null`은 절대 사용하지 않는다.
- **Reason 필드**: 정상 문장(`rule_id: 0`)은 `"정상"`만 작성하고, 감점 문장(`rule_id: 100~300`)은 기술적 결함의 핵심만 간결하고 날카롭게 지적한다.
- **중복 금지**: 질문 세트(Q1~Q3)가 데이터마다 100% 달라야 한다.
- **템플릿 반복 금지**: 프로젝트명만 바꾸고 질문, 답변, reason을 복사 붙여넣기 하지 않는다.
- **STT 가정**: 모든 답변은 STT 변환 결과로 간주하되, `음`, `아`, `어`, `그` 같은 군더더기 말은 넣지 않는다.

## 3. 고정 Instruction

모든 JSONL row의 `instruction`은 아래 문장으로 통일한다. 변형하거나 축약하지 않는다.

```text
IT 전문 면접관으로서 제공된 채용공고와 3개의 면접 문답을 평가하십시오. 출력은 반드시 output.fit_gap_analysis와 output.sentence_diagnosis만 작성하십시오. fit_gap_analysis에서는 채용공고 요구사항 또는 질문 의도별로 PASS, PARTIAL, FAIL 중 하나를 판정하고 gap_rationale에 그 근거를 작성하십시오. sentence_diagnosis에서는 각 질문의 답변을 문장 단위로 나누어 rule_id, reason, metrics_summary, qualitative_score, judgement_basis를 작성하십시오. 모든 판단은 오직 정량 지표, STAR 기준, Fit-Gap 기준, 문장 단위 위반 규칙에 근거해야 합니다.
```

## 4. JSON 스키마

각 JSONL row는 반드시 아래 구조를 따른다.

```json
{
  "instruction": "<고정 instruction>",
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
            "rule_id": "<integer: 0 또는 100~300>",
            "reason": "<string: 정상 문장은 '정상', 감점 문장은 현상 + 기술적 근거 + 역량 평가>"
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

필수 구조 규칙:

- `interview_session`은 항상 3개 문답으로 구성한다.
- 각 문답의 `id`는 `Q1`, `Q2`, `Q3`만 사용한다.
- `sentence_diagnosis[].id`는 `interview_session[].id`와 대응되어야 한다.
- `sentence_diagnosis[].sentences[].text`는 실제 답변 문장과 일치해야 한다.

## 5. Rule ID 체계

정상 문장:

- `0`: 정상. 질문 의도와 맞고, 기술적 근거 또는 판단 흐름이 충분한 문장.

감점 문장:

- `100~139`: 구체성 결여. 원인 분석, 기술 선택 근거, 본인 Action이 부족한 문장.
- `140~179`: 기술적 오류. DB, 트랜잭션, 동시성, 네트워크, 보안, API 설계 등에 대한 잘못된 이해가 드러난 문장.
- `180~219`: 직무 적합도 오류. 공고 요구사항과 무관한 경험이나 태도 중심 답변.
- `220~259`: 가독성 또는 논리 구조 저하. 만연체, 접속사 남발, 논점 흐림, 우선순위 불명확.
- `260~300`: 동문서답. 질문 의도와 다른 방향으로 답하거나 핵심 쟁점을 회피한 문장.

`rule_id`에는 문자열을 쓰지 않는다. 숫자만 사용한다.

## 6. Reason 작성 규칙

정상 문장과 감점 문장의 `reason` 작성 방식은 다르다.

### 정상 문장 (`rule_id: 0`)

- `reason` 필드에는 반드시 `"정상"` 두 글자만 작성한다.
- 정상 문장에는 긴 해설을 붙이지 않는다.

### 감점 문장 (`rule_id: 100~300`)

감점 문장의 `reason`은 정보 밀도를 최우선으로 한다.

- **정보 밀도 우선**: 문장 수에 상관없이 기술적 결함의 핵심만 간결하고 날카롭게 지적한다.
- **답변 인용 금지**: `text` 필드에 있는 내용을 따옴표로 다시 언급하며 분량을 채우지 않는다.
- **메타 표현 금지**: `"이 문장은"`, `"지원자는"`, `"질문에 대해"` 같은 주어성 표현을 생략하고 즉시 기술적 분석으로 진입한다.
- **템플릿 금지**: `"확인됩니다"`, `"부족해 보입니다"` 등으로 끝나는 뻔한 어미 사용을 지양한다.
- **코드 리뷰 말투**: 시니어 개발자가 리뷰 코멘트를 남기듯 결함의 본질, 실무 리스크, 설계 판단 오류를 바로 찌른다.
- **중복 금지**: 같은 감점 사유라도 문장의 기술 맥락에 맞춰 개별적으로 작성한다. 프로젝트명만 바꾼 reason은 사용할 수 없다.

## 7. 고품질 예시 (Few-shot)

### Normal Case

```json
{"text":"저는 이 문제를 해결하기 위해 Spring의 @Transactional 어노테이션을 사용하여 데이터 정합성을 보장했습니다.","rule_id":0,"reason":"정상"}
```

### Bad Case (v2.1 Style)

- **Text**: "트래픽이 몰리면 서버 사양을 높여서 대응하겠습니다."
- **Rule ID**: `101`
- **Reason**: "수평적 확장(Scale-out) 고려 없이 단순 스케일 업(Scale-up)만 제시하는 것은 인프라 비용 효율성과 분산 환경 설계에 대한 엔지니어링적 이해도가 낮음을 의미함."

### BAD CASE (절대 금지)

- **Reason**: "조치가 구체적이라 좋습니다."
- **문제**: 너무 추상적이며 기술적 근거와 역량 평가가 없다.

- **Reason**: "문제 상황과 조치가 연결됩니다."
- **문제**: 복사 붙여넣기처럼 보이며 어떤 기술 역량을 평가하는지 알 수 없다.

- **Reason**: "이 문장은 서버 사양을 높인다고 답하고 있습니다."
- **문제**: 답변 내용을 그대로 인용하고 메타 표현으로 분량을 채운다.

## 8. Fit-Gap Status 기준

`fit_gap_analysis[].status`는 아래 세 값만 사용한다.

```text
PASS
PARTIAL
FAIL
```

- `PASS`: 공고 요구사항을 구체적인 경험, 기술 선택 근거, 검증 결과로 충분히 충족한다.
- `PARTIAL`: 관련 경험은 있으나 원인 분석, 운영 규모 고려, 예외 처리, 테스트, Result 중 일부가 부족하다.
- `FAIL`: 요구 역량을 검증할 수 없거나 질문 의도와 맞지 않으며, 실무 관점에서 위험한 판단이 포함되어 있다.

`V`, `X`, `△` 같은 기호형 라벨은 사용하지 않는다.

## 9. 정량 지표 기준

- `cpm`이 350 초과이면 너무 빠른 답변으로 감점한다.
- `cpm`이 200 미만이면 너무 느린 답변으로 감점한다.
- `dead_air_count`가 1 이상이면 3초 이상 침묵 발생으로 감점한다.
- 문장별 단어 수가 25개를 초과하는 문장이 전체 문장의 30% 이상이면 만연체로 감점한다.
- 문장당 평균 단어 수 15~20개는 정상 범위로 본다.

정량 지표는 `sentence_diagnosis[].metrics_summary`, `sentence_diagnosis[].qualitative_score`, `sentence_diagnosis[].judgement_basis`에 반영한다.

## 10. STAR 기준

- `S` Situation: 특정 시점, 프로젝트명, 소속, 자신의 역할 중 하나라도 있으면 `true`.
- `T` Task: 해결해야 했던 구체적인 목표나 문제 상황이 있으면 `true`.
- `A` Action: 팀이 아닌 본인 중심의 구체적인 기술, 방법, 실행이 있으면 `true`.
- `R` Result: 수치적 성과, 명확한 산출물, 또는 배운 점이 있으면 `true`.
- `A`가 `false`이면 `qualitative_score`는 최대 3점으로 제한한다.

## 11. Qualitative Score 기준

`qualitative_score`는 1~5 정수만 사용한다.

- `5`: 정량 감점 없음, STAR 4요소 충족, 기술적 판단 근거와 Result가 명확하다.
- `4`: 핵심 기준은 충족하지만 운영 규모, 예외 처리, 테스트 근거 중 일부가 약하다.
- `3`: 관련성은 있으나 STAR 일부 누락, 결과 부족, 원인 분석 부족이 있다.
- `2`: 정량 감점 또는 STAR 누락이 크며 실무 역량 검증이 제한적이다.
- `1`: 질문 의도와 맞지 않거나 Action/Result가 거의 없고 답변 신뢰도가 낮다.

## 12. 다양성 규칙

- 질문 세트(Q1~Q3)는 row마다 완전히 달라야 한다.
- 프로젝트 이름은 반복하지 않는다.
- 사용 기술 조합은 반복하지 않는다.
- 문제 상황은 반복하지 않는다.
- 같은 답변 템플릿을 재사용하지 않는다.
- 감점 `reason` 문장은 row 간, 문장 간 반복하지 않는다. 단, `rule_id: 0`의 `"정상"` 반복은 허용한다.
- 도메인은 게시판 CRUD, 쇼핑몰, 예약 시스템, 소셜 미디어, 채팅, 인증, 파일 업로드, 결제, 알림, 커뮤니티 등으로 다양화한다.

## 13. 검증 체크리스트

생성 후 반드시 확인한다.

- 모든 줄이 JSON으로 파싱되는가?
- 각 row에 `instruction`, `input`, `output`이 존재하는가?
- `instruction`이 고정 문장과 정확히 일치하는가?
- `input`에 `analysis_summary`가 없는가?
- `output`에 `top_analysis`가 없는가?
- `interview_session`은 정확히 3개인가?
- `fit_gap_analysis`는 정확히 3개인가?
- `sentence_diagnosis`는 정확히 3개인가?
- `sentence_diagnosis[].id`가 `interview_session[].id`와 대응되는가?
- `status` 값은 `PASS`, `PARTIAL`, `FAIL` 중 하나인가?
- `rule_id`가 숫자인가?
- 정상 문장의 `rule_id`가 `0`인가?
- 감점 문장의 `rule_id`가 `100~300` 사이인가?
- `rule_id`에 `null`이 없는가?
- `rule_id: 0`인 문장의 `reason`이 정확히 `"정상"`인가?
- 감점 문장의 `reason`이 기술적 결함의 핵심을 간결하게 찌르는가?
- `reason`에 답변 내용을 그대로 복사하거나 인용하지 않았는가?
- `"이 문장은"`과 같은 불필요한 메타 표현이 제거되었는가?
- 감점 사유가 템플릿화되지 않고 각 답변의 기술적 맥락을 정확히 찌르는가?
- 질문 세트(Q1~Q3)가 row마다 중복되지 않는가?
- 프로젝트명, 사용 기술, 문제 상황이 반복되지 않는가?
- 감점 문장에 복사 붙여넣기처럼 보이는 reason이 없는가?
