# 배포 — OCI (mc-osaka-1)

| 대상 | 주소 |
|---|---|
| 팀 홈페이지 | http://129.225.184.224:8037/ |
| 서비스 화면 | http://129.225.184.224:8037/app/ |
| API | http://129.225.184.224:8037/health · `/decode` · `/docs` |

셋 다 systemd `ttobak` 하나(FastAPI, `~/codyssey-m3-final` = 이 저장소 clone)가 낸다.
포트는 코디세이 배포 규칙(8000 + 문항 번호 끝 두 자리)의 **M3 자리 8037** 이다. 8033~8036 은 다른 미션 자리라 쓰지 않는다.
홈페이지는 `index.html`·`assets/`·`content/`·`docs/plan/` 만 연다 — 저장소의 다른 파일(`backend/.env` 등)은 404 다.

포트 8033~8037 은 서버 방화벽(iptables)과 OCI 보안 목록에 이미 열려 있다.

## 처음 한 번

의존성(chromadb 포함)을 새 가상환경에 설치한 데스크톱 실측은 `.venv` 약 520MB, 설치 시간 약 21초다
(2026-10-18, [리뷰 이슈 #43](https://github.com/dicia-jhoh/codyssey-m3-final/issues/43)에 보고된 값).
OCI 서버(mc-osaka-1)의 설치 시간과 사용량은 아직 실측하지 않았다. CPU·네트워크·패키지 버전에 따라 달라질 수 있다.

서버에 저장소를 받고 백엔드를 설치한 뒤, 서비스 파일을 등록한다.

```bash
git clone https://github.com/dicia-jhoh/codyssey-m3-final.git ~/codyssey-m3-final
cd ~/codyssey-m3-final/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m scripts.load_legal_articles
sudo cp ../deploy/ttobak.service /etc/systemd/system/
sudo systemctl disable --now codyssey-m3-final 2>/dev/null   # 예전 정적 홈페이지(같은 8037)
sudo systemctl daemon-reload && sudo systemctl enable --now ttobak
```

## 새 버전 올리기 (main 에 merge 된 뒤)

최신 main 을 받고 의존성을 맞춘 뒤 서비스를 다시 띄운다. 홈페이지는 정적 파일이라 받기만 하면 바로 바뀐다.

```bash
cd ~/codyssey-m3-final
deploy_before_pull=$(git rev-parse HEAD)
git pull --ff-only
backend/.venv/bin/pip install -q -r backend/requirements.txt
# 법령 데이터가 바뀐 경우에만 다시 적재한다(같은 조문은 upsert로 갱신).
if ! git diff --quiet "$deploy_before_pull" HEAD -- data/legal/articles.jsonl; then
    (cd backend && .venv/bin/python -m scripts.load_legal_articles)
fi
sudo systemctl restart ttobak
bash deploy/smoke.sh http://localhost:8037  # 화면·API·빈 업로드 확인
```

다른 컴퓨터에서는 `bash deploy/smoke.sh http://129.225.184.224:8037`로 확인한다.
스크립트는 `curl`·`python3`를 사용하며 하나라도 실패하면 종료 코드 1을 낸다.

## 진짜 해독 켜기

서버의 `backend/.env` 에 `LLM_API_KEY=...` 를 넣고 `sudo systemctl restart ttobak`. 이 파일은 커밋하지 않는다.

## 브라우저 캐시

HTML·JS·CSS 는 서버가 `Cache-Control: no-cache` 로 낸다 — 브라우저는 쓰기 전에 서버에 다시 묻고, 안 바뀌었으면 304 로 끝난다.
2026-10-14 에 9/30 정적 페이지의 옛 `site.js`(이름 빈 칸)가 캐시에 남아 「아직 이름이 없는 AI 서비스」로 보인 일이 있어,
`index.html` 의 스크립트·스타일 주소에 `?v=20261014b` 를 한 번 붙여 끊었다. 이후 갱신은 no-cache 가 맡으니 `?v=` 를 매번 올릴 필요는 없다.
