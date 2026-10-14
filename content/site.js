// 팀 공용 내용. 한 사람이 고친 줄은 한 PR 에 담는다(충돌 방지).
// 비어 있는 칸은 페이지에 "채울 자리" 로 보인다 — 지어낸 내용으로 채우지 말 것.
window.SITE = {
  // 서비스 이름과 한 줄 소개. 주제가 정해지기 전까지 비워 둔다
  name: "",
  oneLiner: "",

  // 별자리 색 순서. content/members/<id>.js 의 id 와 맞춘다
  team: ["juhyun", "jeonggwan", "kihoon", "jiyoung", "yuyoung"],

  // 필수 기술 요소 — 두 개 이상 true
  tech: {
    agent: false,
    rag: false,
    multimodal: false,
    workflow: false,
    memory: false,
  },

  // 문제 → 해결 → 구조 → 기술 스택. 각 칸은 문단 하나
  problem: "",
  users: "",
  solution: "",
  architecture: "",
  stack: [], // 예: { part: "Backend", pick: "FastAPI", why: "M1-2 부터 써 온 스택" }

  // 최종 결과물 여섯 가지
  deliverables: {
    plan: false,     // 기획서 — docs/01-기획서.md
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
