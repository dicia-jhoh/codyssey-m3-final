# 법령 조문 — 담당: 김기훈 (지금은 검증된 샘플 1건만)

`rag.py`가 근거로 인용하는 법령 원문. `articles.jsonl`에 한 줄 한 조문씩 적고,
`backend/scripts/load_legal_articles.py`로 Chroma에 넣는다(Chroma DB 자체는
`data/legal/chroma/`에 생기는데 `.gitignore` 대상이라 — 이 JSONL이 진짜
원본이고, DB는 이 파일에서 언제든 다시 만들 수 있는 생성물이다).

## 형식

`data/testset/labels.jsonl`과 같은 패턴 — 한 줄 = JSON 객체 하나.

```json
{"law_name": "국민건강보험법", "article_no": "80", "quote": "원문 그대로", "claim": "쉬운 말 풀이 한 줄", "source_url": "검증한 출처", "verified_at": "YYYY-MM-DD"}
```

- `quote`: 조문 원문. 지어내지 않는다 — `source_url`에서 실제로 확인한 문장만 적는다.
- `claim`: `quote`를 쉬운 말로 풀어쓴 한 줄(`schema.Basis.claim`에 그대로 들어감).
- `article_no`: "제80조의2"처럼 가지조문이면 `"80의2"`로 적는다(`rag._citations()` 참고).
- `source_url`·`verified_at`: 나중에 다시 확인할 때 쓴다. 법은 개정된다 — 특히 벌금·연체금
  같은 숫자는 주기적으로 재확인이 필요하다.

## 지금 들어있는 것과 검증 방법

국민건강보험법 제80조(연체금) 1건. law.go.kr의 "조문정보" 링크(시행일자 2026.10.8로
명시됨)와 다른 출처(nepla.ai) 두 곳의 내용이 일치하는 걸 교차 확인하고 넣었다 —
처음 검색했을 때 한 출처(위키문헌)가 더 예전 버전(연체금 계산식이 다름: 월단위 vs
일단위)을 보여줘서, 교차 확인 없이 하나만 믿으면 틀린 조문이 "근거"로 나갈 뻔했다.

⚠️ **2027-01-01 시행 예정 개정**(법률 제21687호, 2026-05-26 일부개정)이 이미 확인됨 —
연체금 비율이 인하된다. 그 날짜가 지나면 이 조문도 다시 확인해야 한다.

## 다음 할 일 (김기훈 담당)

기획서 범위(국민건강보험법·지방세법·초중등교육법 등 고지서가 자주 인용하는 법)로
조문을 더 모은다. 숫자(금액·비율·기한)가 들어간 조문은 **반드시 law.go.kr에서
시행일자까지 확인**하고, 가능하면 서로 다른 출처 두 곳 이상을 교차 확인한다 — 위
사례처럼 개정 전후 버전이 섞여 나올 수 있다.

```bash
cd backend
python scripts/load_legal_articles.py   # data/legal/articles.jsonl → Chroma에 적재
```
