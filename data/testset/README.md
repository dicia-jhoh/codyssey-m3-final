# 고지서 테스트셋 — 담당: 김기훈

성공 기준(기획서): **고지서 30장에서 금액·기한·할 일 추출 정확도 90% 이상.**

| 폴더·파일 | 무엇 | 지금 |
|---|---|---|
| [`synthetic/`](synthetic/) | 합성 고지서 30장(6종류 × 5장, 지어낸 이름·주소)과 정답·실측 기록 | **91.2%** (93/102) — 배포 서버, 2026-11-01 |
| `labels.jsonl` + `images/` | 실물 고지서 정답(김기훈, 5장) — 사진은 개인정보라 커밋하지 않는다(`.gitignore`) | 정답 5줄 |
| [`example/`](example/) | 채점기가 끝까지 도는지 보는 합성 1장 | 스모크 테스트용 |

- 정답은 한 줄 한 장으로 적는다. 모양은 `labels.example.jsonl` 을 따른다.
- 이름·주소·주민번호는 정답에도 적지 않는다. 금액·기한·할 일만 적는다.
- 정확도 = (맞힌 항목 수) ÷ (정답 항목 수 + 잘못 뽑은 수). 금액은 원 단위까지, 기한은 날짜까지 같아야 맞힌 것이다.

## 정확도 자동으로 재기

`backend/scripts/score_testset.py`. 배포 서버로 재는 법은 [`synthetic/README.md`](synthetic/README.md).

```bash
cd backend
LLM_API_KEY=sk-... python -m scripts.score_testset
```

이미지별 맞힌 항목·틀린 항목과 전체 정확도(90% 기준 달성 여부)를 출력한다. 서류는
문장이 달라도 될 수 있어 부분 일치로 채점하고, 할 일은 (기한, 금액) 쌍이 같아야, 금액·기한은 완전 일치만 인정한다.

## 합성 예시 (`example/`) — 진짜 30장이 아니다

`images/`가 통째로 gitignore 대상이라, 처음엔 `score_testset.py`를 **실제 이미지 파일로**
돌려 볼 수 없었다. `example/example.jpg`는 `sample.py`의 가짜 고지서와 같은 성격의
**합성 이미지**(지어낸 글자를 PIL로 그려 만듦, 실제 고지서 아님) — 도구 자체가 끝까지
도는지 확인하는 스모크 테스트용이다. 정확도 90% 집계에는 안 들어간다.

```bash
cd backend
LLM_API_KEY=sk-... python -m scripts.score_testset --labels ../data/testset/example/labels.jsonl
```

재생성하려면 `data/testset/example/make_example.py` 참고(Pillow 필요, 평소엔 안 돌려도 됨
— `example.jpg`는 이미 커밋돼 있다).
