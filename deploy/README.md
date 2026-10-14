# 배포 — OCI (mc-osaka-1)

| 대상 | 주소 | 서비스(systemd) | 코드 위치 |
|---|---|---|---|
| 서비스(화면 + API) | http://129.225.184.224:8035/ | `ttobak` | `~/codyssey-m3-final` (이 저장소 clone) |
| 팀 홈페이지 | http://129.225.184.224:8037/ | `codyssey-m3-final` | 같은 clone 의 맨 위 폴더 |

포트 8033~8037 은 서버 방화벽(iptables)과 OCI 보안 목록에 이미 열려 있다.

## 처음 한 번

서버에 저장소를 받고 백엔드를 설치한 뒤, 서비스 파일을 등록한다.

```bash
git clone https://github.com/dicia-jhoh/codyssey-m3-final.git ~/codyssey-m3-final
cd ~/codyssey-m3-final/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
sudo cp ../deploy/ttobak.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ttobak
```

## 새 버전 올리기 (main 에 merge 된 뒤)

최신 main 을 받고 의존성을 맞춘 뒤 서비스를 다시 띄운다. 홈페이지는 정적 파일이라 받기만 하면 바로 바뀐다.

```bash
cd ~/codyssey-m3-final && git pull --ff-only
backend/.venv/bin/pip install -q -r backend/requirements.txt
sudo systemctl restart ttobak
curl -s localhost:8035/health          # {"ok":true,...} 이면 성공
```

## 진짜 해독 켜기

서버의 `backend/.env` 에 `LLM_API_KEY=...` 를 넣고 `sudo systemctl restart ttobak`. 이 파일은 커밋하지 않는다.
