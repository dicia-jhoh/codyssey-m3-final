# 또박또박 — AI 공문 해독기

코디세이 AI 네이티브 대전 **M3 AI 네이티브 Final Project 자율 주제** 팀 저장소.

## 프로젝트 소개

고지서·가정통신문·주민센터 안내문을 받고도 「그래서 뭘 해야 하는지」 모르는 사람이 많다. 한자어와 법령 인용, 본문·표·뒷면에 흩어진 기한과 금액 때문이다.
또박또박은 공문 사진 한 장을 받아 **원본 위에** 빨강 = 낼 돈, 파랑 = 기한, 초록 = 챙길 서류를 긋고, 할 일 카드와 근거 문장을 붙여 준다.
1차 사용자는 대전의 60대 이상 어르신과 그 자녀다.

- 기획서: [docs/01-기획서.md](docs/01-기획서.md) (제출본 [PDF](docs/plan/상세기획서-또박또박.pdf))
- 기능 명세·아키텍처: [docs/02-기능명세.md](docs/02-기능명세.md)
- AI 설계: [docs/03-AI-설계.md](docs/03-AI-설계.md)

> 지금은 **뼈대 단계**다. 백엔드는 샘플 모드(가짜 공문 1건)로 끝까지 돌아가고, 각 단계의 진짜 구현은 담당자가 자기 파일에서 채운다.
> 빈 칸은 빈 그대로 둔다 — 지어낸 결과·피드백으로 채우지 않는다.

## 팀원 및 역할

| 이름 | 역할 | 담당 업무 | 내 파일 | GitHub |
|------|------|-----------|---------|--------|
| 오주현(팀장) | PM · AI Agent | 일정·PR 리뷰·통합, Agent 4단계, 프롬프트 JSON 스키마 | `backend/app/agent.py` · `schema.py` | [@dicia-jhoh](https://github.com/dicia-jhoh) |
| 황지영 | 멀티모달 추출 | 비전 LLM 추출·파싱, 3색 좌표, 금액·날짜 이중 확인 | `backend/app/extract.py` | [@ppungee-maker](https://github.com/ppungee-maker) |
| 이정관 | Backend · 배포 · 자동화 | FastAPI, OCI 배포, n8n 기한 알림 | `backend/app/main.py` · `automation/` | [@ljk-cidy](https://github.com/ljk-cidy) |
| 송유영 | Frontend | 모바일 화면, 3색 오버레이, 할 일 카드, 손주 모드 | `web/` | [@youyu10012-glitch](https://github.com/youyu10012-glitch) |
| 김기훈 | RAG 데이터 · 품질 | 법령·정부24 수집과 근거 검색, 테스트셋 30장, 정확도·설문 | `backend/app/rag.py` · `data/testset/` | [@duplgabszin](https://github.com/duplgabszin) |
| 송유진 | UX 라이팅 · 사용자 테스트 | 쉬운 말 풀이 문체 가이드, 어르신 실사용자 테스트 진행, 시연 영상·발표 자료 | `docs/04-사용자테스트.md` · `docs/05-발표.md` | [@youjinni11](https://github.com/youjinni11) |

홈페이지의 팀 칸은 `content/members/<내 id>.js` 에서 온다 — 역할이 바뀌면 그 파일과 이 표를 같이 고친다.

## 필수 기술 요소 (2개 이상 → 4개)

| 기술 요소 | 사용 | 어디에 |
|---|---|---|
| AI Agent | ✅ | 공문 판별 → 추출 → 근거 → 답장 판단, 알림 도구 호출 (`backend/app/agent.py`) |
| RAG (검색 증강 생성) | ✅ | 국가법령정보·정부24 안내를 찾아 근거로 인용 (`backend/app/rag.py`) |
| 멀티모달 AI | ✅ | 사진 속 표·도장·뒷면을 읽고 좌표까지 뽑기 (`backend/app/extract.py`) |
| 자동화 워크플로우 | ✅ | n8n 기한 D-3·D-day 알림, 손주 모드 링크 (`automation/n8n/`) |
| Long-term Memory | ☐ | 쓰지 않는다 — 공문은 개인정보라 저장할수록 위험하다 |

## 기술 스택 — 선택과 이유

| 영역 | 선택 | 대안 | 선정 이유 |
|---|---|---|---|
| AI | 비전 LLM API + 임베딩 API | OCR 엔진 + 텍스트 LLM | 사진 이해와 좌표 추출을 한 번에 한다 |
| Backend | Python FastAPI | Flask | A 과정의 Python 그대로, 입력·출력 모양을 Pydantic 으로 고정한다 |
| RAG | Chroma | Pinecone | 설치가 가볍고 법령 문서 수천 건 규모에 충분하다 |
| Frontend | HTML · CSS · JS(모바일 우선) | React | 어르신이 앱 설치 없이 링크 하나로 연다, 빌드가 없다 |
| 배포 | OCI 서버 + systemd | Render · Vercel | 팀이 이미 쓰는 OCI 서버에 올려 화면과 API 를 주소 하나로 낸다(무료, 잠들지 않음) |
| 자동화 | n8n | 직접 짠 스케줄러 | B1-3 노코드 자동화에서 쓴 도구라 알림 흐름을 바로 짠다 |

## 시스템 아키텍처

아래 그림은 사진 한 장이 해독 결과가 되기까지의 흐름이다. 정본은 [docs/02-기능명세.md](docs/02-기능명세.md).

```
[모바일 웹 web/] ──사진──▶ [FastAPI backend/]
                              │ ① redact   개인정보 가림
                              │ ② agent    판별 → 추출(extract) → 근거(rag) → 답장 판단
                              ▼
                        Decoded JSON ──▶ 3색 표시 · 할 일 카드 · 근거 링크
                              └─ 기한 ──▶ [n8n] ──▶ D-3·D-day 알림
```

## 준비물

- Python 3.11 이상 (`python3 --version` 으로 확인)
- Git, 그리고 이 저장소에 초대된 GitHub 계정(초대 메일에서 수락)
- 웹 브라우저(크롬 권장)
- LLM API 키는 **없어도 된다** — 없으면 샘플 모드로 돈다. 진짜 해독을 시험할 때만 `backend/.env` 에 넣는다(커밋 금지)

## 따라 하기

1. 저장소를 받는다. 아래 명령은 내 컴퓨터에 폴더 하나를 만든다.
   ```bash
   git clone https://github.com/dicia-jhoh/codyssey-m3-final.git
   cd codyssey-m3-final
   ```
2. 백엔드를 설치하고 테스트를 돌린다. 가상환경(`.venv`)을 만들어 이 프로젝트 전용으로 설치한다.
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pytest                             # 전부 passed 면 성공
   ```
3. 백엔드 서버를 띄운다. 켜 두면 http://localhost:8000/docs 에서 API 를 눌러 볼 수 있다.
   ```bash
   uvicorn app.main:app --reload
   ```
4. 브라우저로 http://localhost:8000/app/ 을 연다. 백엔드가 서비스 화면(`web/`)과 팀 홈페이지(http://localhost:8000/)도 같이 내준다. 아무 사진이나 올리면 샘플 해독 결과가 나온다.
   화면만 고칠 땐 새 터미널에서 아래처럼 따로 띄워도 된다(그때도 API 는 8000 을 쓴다).
   ```bash
   python3 -m http.server 5500 --directory web
   ```
5. 홈페이지만 고칠 땐 백엔드 없이 저장소 맨 위 폴더에서 띄워도 된다. http://localhost:8001 을 연다.
   ```bash
   python3 -m http.server 8001
   ```
6. 내 일을 시작한다. 브랜치를 만들고, 위 「내 파일」만 고치고, PR 을 올린다 — 자세한 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md).

## 배포

배포 방법과 새 버전 올리기는 [deploy/README.md](deploy/README.md).

| 대상 | 주소 |
|---|---|
| 서비스 화면 | http://129.225.184.224:8037/app/ |
| 팀 홈페이지 | http://129.225.184.224:8037/ |

## 결과

| 산출물 | 위치 | 상태 |
|---|---|---|
| 기획서 | [docs/01-기획서.md](docs/01-기획서.md) | 확정 |
| 기능 요구 명세서·아키텍처 | [docs/02-기능명세.md](docs/02-기능명세.md) | 초안 |
| AI 설계(프롬프트·Agent·RAG) | [docs/03-AI-설계.md](docs/03-AI-설계.md) | 초안 |
| 사용자 테스트(5명 이상) | [docs/04-사용자테스트.md](docs/04-사용자테스트.md) | 설계만 |
| 발표 자료 | [docs/05-발표.md](docs/05-발표.md) | 순서만 |
| 서비스 | `backend/` · `web/` | 뼈대(샘플 모드) |
| 서비스 배포 | 위 표 · [deploy/](deploy/README.md) | OCI 배포됨(샘플 모드) |

## AI 윤리

- 모든 풀이 화면에 **「AI 풀이 — 원문을 함께 확인하세요」** 를 표시한다.
- 주민등록번호·계좌번호는 **LLM 에 보내기 전에** 가린다(`backend/app/redact.py`).
- 사진 원본은 처리가 끝나면 지운다. 실물 공문 사진은 저장소에 올리지 않는다(`data/testset/images/` 는 `.gitignore`).
- 사용자 테스트 기록에는 실명 대신 `사용자 1` 처럼 적는다.
- 이 저장소의 문서·코드 초안은 AI(Claude)가 쓰고 팀이 검토했다. 이후 AI 가 쓴 부분은 커밋·PR 에 적는다.

## 저장소 구조

```
backend/                FastAPI — app/(main·agent·schema·extract·rag·redact·sample), tests/
web/                    서비스 화면(모바일 웹, 빌드 없음) — 백엔드가 같이 내준다
deploy/                 OCI 배포(systemd 서비스 파일, 절차)
automation/n8n/         기한 알림 워크플로우
data/testset/           공문 테스트셋 라벨(사진은 커밋하지 않는다)
docs/                   미션 산출물 문서, plan/ = 제출한 기획서 원본
index.html · assets/ · content/   팀 홈페이지(빌드 없음) — 로고 키트·사용 가이드 = assets/brand/
```

## 용어 사전

- **공문**: 관공서·학교·공단이 보내는 고지서, 안내문, 가정통신문을 통틀어 이르는 말
- **해독**: 공문을 쉬운 말로 풀고 할 일(금액·기한·서류)을 뽑아내는 일
- **멀티모달**: 글자뿐 아니라 사진 같은 다른 형태의 입력도 이해하는 AI
- **RAG**: 답하기 전에 외부 문서(여기선 법령)를 찾아 근거로 붙이는 방식
- **AI Agent**: 목표를 받으면 단계를 스스로 정하고 도구를 불러 끝까지 처리하는 AI 프로그램
- **샘플 모드**: LLM 키가 없을 때 가짜 공문 해독 결과를 돌려주는 동작. 화면에 배너로 알린다
- **FastAPI**: Python 으로 웹 API 서버를 만드는 도구
- **n8n**: 여러 서비스를 이어 자동으로 돌리는 노코드 도구
- **PR(Pull Request)**: 내 브랜치의 변경을 main 에 합쳐 달라고 요청하는 것. 기여 기록이 된다
