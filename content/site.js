// 팀 공용 내용. 한 사람이 고친 줄은 한 PR 에 담는다(충돌 방지).
// 비어 있는 칸은 페이지에 "채울 자리" 로 보인다 — 지어낸 내용으로 채우지 말 것.
window.SITE = {
  // 서비스 이름과 한 줄 소개. 주제가 정해지기 전까지 비워 둔다
  name: "또박또박",
  oneLiner: "사진 한 장이면 공문 원본 위에 「얼마를 · 언제까지 · 무엇을」이 보이는 AI 공문 해독기",

  // 별자리 색 순서. content/members/<id>.js 의 id 와 맞춘다
  team: ["juhyun", "jeonggwan", "kihoon", "jiyoung", "yuyoung"],

  // 필수 기술 요소 — 두 개 이상 true
  tech: {
    agent: true,
    rag: true,
    multimodal: true,
    workflow: true,
    memory: false,
  },

  // 문제 → 해결 → 구조 → 기술 스택. 각 칸은 문단 하나
  problem:
    "고지서·가정통신문·주민센터 안내문은 한자어, 법령 인용, 본문·표·뒷면에 흩어진 기한과 금액 때문에 읽기 어렵다. 그 결과 기한을 넘겨 가산금을 내고, 받을 수 있던 감면·지원금을 놓친다. 지금은 사진을 찍어 자녀에게 카톡으로 묻는 것으로 버틴다.",
  users:
    "1차는 대전 거주 60대 이상 어르신과 그 자녀(대리 확인자), 2차는 공문이 낯선 결혼이주민과 처음 자취하는 사회초년생. 팀원 5명의 가족이 실제로 집에 온 공문으로 써 본다.",
  solution:
    "공문을 줄이지 않고 원본 위에 긋는다. 3색 빨간펜(빨강 = 낼 돈, 파랑 = 기한, 초록 = 챙길 서류), 풀이 한 줄마다 원문 위치와 법령 조문을 붙이는 근거 링크, 할 일 카드, 자녀에게 해독본을 보내는 손주 모드, 회신이 필요한 공문의 답장 초안.",
  architecture:
    "모바일 웹에서 사진을 올리면 FastAPI 백엔드가 개인정보를 가린 뒤 Agent 파이프라인을 돈다 — 공문 판별 → 비전 LLM 추출(좌표 포함) → RAG 근거 검색(국가법령정보·정부24) → 답장 필요 판단. 기한은 n8n 이 받아 D-3·D-day 알림을 보낸다.",
  stack: [
    { part: "AI", pick: "비전 LLM API + 임베딩 API", why: "사진 이해와 근거 검색을 한 API 계열로 묶는다" },
    { part: "Backend", pick: "Python FastAPI", why: "A 과정의 Python 그대로, Agent 단계를 함수로 노출한다" },
    { part: "RAG", pick: "Chroma", why: "설치가 가볍고 법령 문서 수천 건 규모에 충분하다" },
    { part: "자동화", pick: "n8n", why: "B1-3 노코드 자동화에서 쓴 도구라 알림 흐름을 바로 짠다" },
    { part: "Frontend", pick: "HTML · CSS · JS(모바일 우선)", why: "어르신이 앱 설치 없이 링크 하나로 연다" },
    { part: "배포", pick: "Render · Vercel", why: "무료 티어로 외부 접속 주소를 바로 낸다" },
  ],

  // 최종 결과물 여섯 가지
  deliverables: {
    plan: true,      // 기획서 — docs/01-기획서.md
    spec: false,     // 기능 요구 명세서·아키텍처 — docs/02-기능명세.md
    service: false,  // AI 서비스 구현
    repo: true,      // GitHub 저장소 — 이 저장소
    slides: false,   // 발표 자료 — docs/05-발표.md
    deploy: false,   // 외부 접근 가능한 배포
  },
  deployUrl: "",

  // 실사용자 피드백 — 최소 5건. 이름 대신 "사용자 1" 처럼 적는다(개인정보)
  feedback: [
    // { who: "사용자 1", said: "", changed: "" },
  ],

  repoUrl: "https://github.com/dicia-jhoh/codyssey-m3-final",
};
