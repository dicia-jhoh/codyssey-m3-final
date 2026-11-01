# 합성 고지서 30장

실제 양식을 본떠 코드로 그린 고지서 30장과 정답이다. 이름·주소·번호는 모두 지어냈다(김또박, 대전 또박로).
주민번호·계좌번호는 처음부터 가린 모양으로 그렸다. 그래서 개인정보가 없어 저장소에 올린다.

| 종류 | 사진 |
|---|---|
| 건강보험료 | b01~b05 |
| 자동차세 | b06~b10 |
| 재산세 | b11~b15 |
| 전기요금 | b16~b20 |
| 수도요금 | b21~b25 |
| 과태료 | b26~b30 |

- 그린 코드: 발표 자료 저장소 `awesomeboard` 의 `boards/ttobak-m3/bills.py`(같은 값을 그리고 정답에 적는다).
- `labels.jsonl` 의 `bill` = 종류(종류별 정확도용). 과태료 5장의 `doc_type` 은 `과태료`다.

배포 서버로 재기(서버 요청 제한 때문에 장마다 6.5초 간격):

```bash
cd backend
python -m scripts.score_testset --server http://localhost:8037 \
  --labels ../data/testset/synthetic/labels.jsonl --out ../data/testset/synthetic/score.json
```
