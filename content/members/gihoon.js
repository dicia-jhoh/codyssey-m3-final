// 김기훈 — 이 파일만 고치면 페이지의 내 자리가 채워진다. 다른 사람 파일은 건드리지 않는다.
window.MEMBERS = window.MEMBERS || {};
window.MEMBERS.gihoon = {
  name: "김기훈",
  github: "duplgabszin", // GitHub 아이디
  role: "RAG 데이터 · 품질", // 예: "PM / Backend", "Frontend", "AI / Data"
  work: [
    "법 조문 모으기·법제처 원문 대조와 근거 검색 (backend/app/rag.py · lawapi.py)",
    "개인정보 가림 — 전화번호도 가리기 (backend/app/redact.py)",
    "테스트셋 첫 5장 정답 (data/testset/labels.jsonl)",
    "같은 조문이 두 번 적재되지 않게 막기 (backend/scripts/load_legal_articles.py)",
  ],
  prs: [
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/117",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/144",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/147",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/230",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/268",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/269",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/270",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/294",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/295",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/296",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/297",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/298",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/299",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/300",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/301",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/302",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/303",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/304",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/305",
    "https://github.com/dicia-jhoh/codyssey-m3-final/pull/306",
  ],
  // 주제 후보 — 제안이 없으면 비워 둔다
  pitch: {
    title: "또박또박 — 고지서 속 법 조항을 쉬운 말로 (채택 주제)",
    problem: "고지서에 「○○법 제○조」가 찍혀 있어도 어르신은 무슨 뜻인지 몰라 가산금·기한을 놓친다", // 누가, 어떤 상황에서, 무엇 때문에 곤란한가
  },
};
