# 함께 작업하는 법

미션 요건에 **"모든 팀원이 실질적으로 기여"** 와 **"GitHub 버전 관리 기록"** 이 들어 있다.
누가 무엇을 했는지가 커밋과 PR 에 남아야 평가에서 증명된다. 그래서 규칙은 셋뿐이다.

## 1. 내 자리 채우기 (첫 기여)

| 이름 | 내 파일 |
|---|---|
| 오주현 | `content/members/juhyun.js` |
| 이정관 | `content/members/jeonggwan.js` |
| 김기훈 | `content/members/kihoon.js` |
| 황지영 | `content/members/jiyoung.js` |
| 송유영 | `content/members/yuyoung.js` |

```bash
git clone https://github.com/dicia-jhoh/codyssey-m3-final.git
cd codyssey-m3-final
git switch -c jeonggwan/profile          # <내 id>/<무엇>
# content/members/jeonggwan.js 를 연다 → github·role·work·pitch 채우기
python3 -m http.server 8000         # http://localhost:8000 에서 내 칸 확인
git add content/members/jeonggwan.js
git commit -m "이정관: 역할·주제 후보 추가"
git push -u origin jeonggwan/profile
# GitHub 에서 Pull Request 만들기
```

`role` 을 채우면 첫 화면 별자리에서 내 색이 선명해지고, 팀 칸이 켜진다.
`pitch` 에 주제 후보를 적으면 "주제 후보" 목록에 올라간다.

## 2. 규칙

1. **main 에 직접 push 하지 않는다.** 브랜치 → PR → 한 명 이상 확인 후 merge.
   PR 이 곧 기여 기록이다.
2. **내 파일은 내가, 공용 파일은 PR 하나에 한 가지.** `content/site.js` 는 모두가 고치는
   파일이라 한 PR 에서 한 칸만 바꾼다(충돌을 줄인다).
3. **없는 것을 지어내지 않는다.** 모르는 칸은 비워 둔다. AI 도구가 한 일은 AI 가 했다고 적는다.

## 3. 주제 정하기

1. 각자 `pitch` 를 채운다(제목 한 줄 + 누가 어떤 상황에서 곤란한가).
2. 모여서 하나를 고른다. 기준 — **실사용자 5명을 실제로 구할 수 있는가**, **AI 를 빼면 서비스가
   무너지는가**, 필수 기술 요소 **두 가지 이상**이 자연스럽게 들어가는가.
3. 정해지면 `content/site.js` 의 `name`·`oneLiner`·`tech` 와 README 제목을 바꾼다.

## 4. 홈페이지 고치기

- 색·글자 크기는 `assets/css/tokens.css` 한 곳. 레퍼런스는 Dala
  ([styles.refero.design](https://styles.refero.design/style/e5f5f8cf-e68d-4ed1-bbf5-6b67569af648)) —
  검정 바탕, 굵기 대신 크기로 위계, 채운 버튼은 보라 하나.
- 새 섹션은 `index.html` 에 `data-slot` 자리를 만들고 `assets/js/render.js` 에서 채운다.
- 내용(글)은 HTML 에 직접 쓰지 않고 `content/` 에 둔다 — 디자인을 몰라도 글을 고칠 수 있게.
