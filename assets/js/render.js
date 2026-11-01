// content/ 의 데이터를 페이지에 꽂는다. 빈 칸은 숨기지 않고 "어느 파일의 어느 칸" 인지 보여 준다 —
// 팀원이 페이지만 보고도 자기가 채울 곳을 찾게 하려는 것. 숫자는 잰 값만 넣는다(content/site.js).
(function () {
  const SITE = window.SITE || {};
  const MEMBERS = window.MEMBERS || {};
  const TEAM = (SITE.team || []).map((id, i) => ({ id, i, ...(MEMBERS[id] || { name: id }) }));
  const LEAD = "juhyeon"; // 팀장 — 팀 칸에 「· 팀장」을 붙인다
  const MEMBER_COLORS = 6; // assets/css 의 --m0..--m5, constellation.js 의 COLORS 와 같은 수
  const MIN_TECH = 2; // 필수 기술 요소 최소 개수(미션 요건)

  const TECH = [
    ["agent", "AI Agent", "추출 → 가림 → 근거 → 판별 → 할 일을 차례로 부르고, 과태료면 답장 초안을 쓴다"],
    ["rag", "RAG", "고지서가 인용한 조문 번호로 법제처 원문 10개 중에서 찾아 근거로 붙인다"],
    ["multimodal", "멀티모달", "사진 속 표·도장·뒷면까지 읽고 금액·기한·서류의 좌표를 뽑는다"],
    ["workflow", "자동화 워크플로우", "기한 사흘 전·당일 알림 일정을 만들어 n8n 웹훅으로 넘긴다"],
    ["memory", "Long-term Memory", "쓰지 않는다 — 고지서는 개인정보라 저장할수록 위험하다"],
  ];

  const DELIVERABLES = [
    ["plan", "기획서", "문제·타겟 사용자·AI 활용 방식·일정", "docs/01-기획서.md"],
    ["spec", "기능 요구 명세서", "기능·비기능 요구사항과 시스템 아키텍처", "docs/02-기능명세.md"],
    ["service", "AI 서비스", "생성형 AI 또는 AI Agent 가 핵심인 서비스", "backend/ · web/"],
    ["repo", "GitHub 저장소", "소스·문서·버전 관리 기록", ""],
    ["slides", "발표 자료", "문제 해결 과정·기술 결정 근거·피드백 반영", "docs/05-발표.md"],
    ["deploy", "서비스 배포", "외부에서 접근 가능한 주소", "deploy/"],
  ];

  const STORY = [
    ["problem", "해결할 문제", "누가, 어떤 상황에서, 무엇 때문에 곤란한가"],
    ["users", "타겟 사용자", "실사용자 다섯 명을 어디서 구할 수 있는가"],
    ["solution", "AI 로 푸는 방식", "AI 를 빼면 이 서비스가 무엇으로 퇴화하는가"],
    ["architecture", "구조", "프런트·백엔드·AI·데이터가 어떻게 이어지는가"],
  ];

  // 펜 3색 — 뜻이 정해진 색이다(빨강 = 낼 돈, 파랑 = 기한, 초록 = 챙길 서류). 서비스 화면 web/ 과 같은 약속
  const PENS = [["money", "낼 돈"], ["deadline", "기한"], ["document", "챙길 서류"]];

  // ── 작은 부품 ──

  const $ = (slot) => document.querySelector(`[data-slot="${slot}"]`);

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs || {})) {
      if (value == null || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "style") node.style.cssText = value;
      else node.setAttribute(key, value);
    }
    for (const kid of kids.flat()) {
      if (kid == null || kid === false) continue;
      node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return node;
  }

  function fill(slot, ...kids) {
    const node = $(slot);
    if (node) node.replaceChildren(...kids.flat());
  }

  // 빈 칸 표시 — 무엇을 어디에 적으면 되는지
  const todo = (what, where) => el("span", { class: "todo" }, what, el("code", {}, where));
  const picture = (scene, cls) =>
    scene && scene.src
      ? el("img", { class: cls, src: scene.src, alt: scene.alt || "", loading: "lazy", width: "960", height: "720" })
      : null;
  const dot = (color) => el("span", { class: "dot", style: `--c:${color}` });
  const pitchRow = (who, ...body) =>
    el("li", { class: "pitch" }, el("span", { class: "pitch-who" }, who), el("div", {}, ...body));

  const hasRole = (member) => Boolean(member.role && member.role.trim());
  const memberColor = (i) => `var(--m${i % MEMBER_COLORS})`;
  const planHref = SITE.planPdf || "docs/01-기획서.md";

  // ── 구역 ──

  function renderHero() {
    const name = (SITE.name || "").trim();
    $("name").textContent = name || "M3 Final Project";
    $("name").classList.toggle("is-empty", !name);
    $("brand").textContent = name || "M3 Final";
    document.title = name ? `${name} · M3 Final Project` : "M3 Final Project";
    fill("oneLiner", SITE.oneLiner || "여섯 명이 문제 하나를 골라 AI 서비스로 만들고, 배포한 뒤 실사용자 다섯 명에게 검증받는다.");
    if (SITE.repoUrl) $("contribute").href = `${SITE.repoUrl}/blob/main/CONTRIBUTING.md`;
    for (const slot of ["open", "open2"]) {
      const link = $(slot);
      if (link && SITE.deployUrl) link.href = SITE.deployUrl;
    }
    if ($("plan")) $("plan").href = planHref;
    fill("legend", ...TEAM.map((m) =>
      el("li", { class: hasRole(m) ? "" : "is-empty", "data-member": m.i, tabindex: "0" }, dot(memberColor(m.i)), m.name)));
  }

  function renderIntent() {
    const intent = SITE.intent || {};
    const question = (SITE.hero || {}).question || "";
    fill("question", ...question.split("\n").flatMap((line, i) => (i ? [el("br"), line] : [line])));
    fill("problem", intent.problem || "");
    fill("why", ...(intent.why || []).map((w) => el("li", {}, w)));
    fill("scenes", beforeScene(intent), afterScene(intent));
    fill("insight", intent.insight || "");
    fill("users", ...(intent.users || []).map(([who, what]) =>
      pitchRow(who, el("p", { class: "pitch-problem is-lead" }, what))));
  }

  function beforeScene(intent) {
    const asked = (intent.chat || [])
      .filter(([who, text]) => who === "parent" && text !== "[사진]")
      .map(([, text]) => `“${text}”`);
    return el("figure", { class: "scene" },
      picture((intent.scenes || {}).before),
      el("figcaption", {},
        el("span", { class: "scene-tag" }, "지금"),
        el("span", { class: "scene-quote" }, asked.join(" ")),
        el("span", { class: "scene-note" }, "사진을 찍어 자녀에게 묻는다. 자녀가 바쁘면 그냥 쌓아 둔다.")));
  }

  // 첫 화면 고지서(site.js 의 hero)와 같은 값으로 세 펜을 보여 준다
  function afterScene(intent) {
    const hero = SITE.hero || {};
    const card = hero.todo || {};
    const attach = ((hero.doc || {}).attach || [""])[0].replace(/\(.*\)/, "");
    const penText = [card.amount, card.due, `${attach} 챙기기`];
    return el("figure", { class: "scene" },
      picture((intent.scenes || {}).after),
      el("figcaption", {},
        el("span", { class: "scene-tag is-on" }, "또박또박"),
        el("span", { class: "scene-marks" },
          ...PENS.map(([kind], i) => el("span", { class: "pen", style: `--c:var(--pen-${kind})` }, penText[i]))),
        el("span", { class: "scene-note" }, "사진 한 장으로 끝. 자녀에게도 해독본 링크가 간다.")));
  }

  function renderFeatures() {
    fill("features", ...(SITE.features || []).map((f) => {
      const marker = f.look === "pens" ? PENS.map(([kind]) => dot(`var(--pen-${kind})`)) : dot("var(--iris)");
      const withScene = f.look === "share" && SITE.shareScene;
      return el("li", { class: "pitch" },
        el("span", { class: "pitch-who" }, marker),
        el("div", { class: withScene ? "pitch-with-img" : "" },
          el("div", {}, el("p", { class: "pitch-title" }, f.name), el("p", { class: "pitch-problem" }, f.what)),
          withScene ? picture(SITE.shareScene, "pitch-img") : null));
    }));
  }

  function renderTech() {
    const tech = SITE.tech || {};
    const picked = TECH.filter(([key]) => tech[key]).length;
    fill("tech", ...TECH.map(([key, label, desc]) =>
      el("li", { class: tech[key] ? "is-on" : "" }, el("span", { class: "tech-name" }, label), el("span", { class: "tech-desc" }, desc))));
    fill("techTally",
      el("span", { class: picked >= MIN_TECH ? "ok" : "short" }, `${picked}개 선택`),
      picked >= MIN_TECH ? ", 요건 충족" : `, ${MIN_TECH - picked}개 더 필요`);
  }

  // Agent 단계 — 실제 순서라 번호를 단다
  function renderPipeline() {
    fill("pipeline", ...(SITE.pipeline || []).map((p, i) =>
      el("li", {},
        el("span", { class: "step-no" }, String(i + 1)),
        el("span", { class: "del-head" }, p.step),
        el("span", { class: "del-desc" }, p.what, el("span", { class: "step-meta" }, `${p.tech} · ${p.who}`)))));
    fill("guard", SITE.guard || "");
  }

  // 문제 → 사용자 → 해결 → 구조 → 스택
  function renderStory() {
    const rows = STORY.map(([key, head, hint]) =>
      el("article", { class: "story-row" },
        el("h3", { class: "story-head" }, head),
        SITE[key]
          ? el("p", { class: "body" }, SITE[key])
          : el("p", { class: "body is-empty" }, hint, el("br"), todo("", `content/site.js 의 ${key}`))));
    const stack = SITE.stack || [];
    const stackRow = el("article", { class: "story-row" },
      el("h3", { class: "story-head" }, "기술 스택과 이유"),
      stack.length
        ? el("dl", { class: "stack" }, ...stack.map((s) => [el("dt", {}, s.part), el("dd", {}, el("strong", {}, s.pick), s.why ? ` — ${s.why}` : "")]))
        : el("p", { class: "body is-empty" }, "고른 것과 고른 이유를 함께", el("br"), todo("", "content/site.js 의 stack")));
    fill("story", ...rows, stackRow);
  }

  function renderTeam() {
    fill("team", ...TEAM.map((m) =>
      el("li", { class: hasRole(m) ? "member" : "member is-empty", "data-member": m.i, tabindex: "0", style: `--c:${memberColor(m.i)}` },
        el("p", { class: "member-role" }, m.role || "역할 미정", m.id === LEAD ? " · 팀장" : ""),
        el("p", { class: "member-name" }, m.name),
        m.github
          ? el("a", { class: "member-gh", href: `https://github.com/${m.github}` }, `@${m.github}`)
          : el("span", { class: "member-gh" }, "GitHub 미등록"),
        (m.work || []).length
          ? el("ul", { class: "member-work" }, ...m.work.map((w) => el("li", {}, w)))
          : todo("", `content/members/${m.id}.js`),
        (m.prs || []).length ? el("p", { class: "member-prs" }, `PR ${m.prs.length}건`) : null)));
  }

  // 걸어온 길 — 날짜는 머지된 PR 의 날짜다
  function renderSchedule() {
    fill("schedule", ...(SITE.schedule || []).map((step) =>
      el("li", { class: "is-done" },
        el("span", { class: "del-state" }, step.date),
        el("span", { class: "del-head" }, step.what),
        el("span", { class: "del-desc" }, step.who))));
  }

  // 기대효과·활용방안·성공 기준
  function renderOutcomes() {
    fill("effects", ...(SITE.effects || []).map(([title, what]) =>
      pitchRow(dot("var(--saffron)"), el("p", { class: "pitch-title" }, title), el("p", { class: "pitch-problem" }, what))));
    fill("uses", ...(SITE.uses || []).map((u) => el("li", {}, u)));
    fill("criteria", ...(SITE.criteria || []).map((c) =>
      el("li", { class: "is-done" },
        el("span", { class: "del-state" }, c.name),
        el("span", { class: "del-head goal" }, c.goal),
        el("span", { class: "del-desc" }, c.how,
          el("span", { class: "now" }, "잰 값 ", el("strong", {}, c.now))))));
  }

  function renderDeliverables() {
    const done = SITE.deliverables || {};
    fill("deliverables", ...DELIVERABLES.map(([key, head, desc, file]) =>
      el("li", { class: done[key] ? "is-done" : "" },
        el("span", { class: "del-state" }, done[key] ? "완료" : "남음"),
        el("span", { class: "del-head" }, head),
        el("span", { class: "del-desc" }, desc, file ? el("code", {}, file) : ""))));
  }

  function renderFeedback() {
    fill("feedback", ...(SITE.feedback || []).map((f) =>
      el("li", { class: "fb" },
        el("span", { class: "fb-who" }, f.who),
        el("span", {}, f.saw),
        el("span", { class: "fb-changed" }, `고침: ${f.changed}`))));
  }

  function renderLinks() {
    fill("links",
      SITE.deployUrl ? el("a", { href: SITE.deployUrl }, "서비스") : "배포 주소 미정",
      SITE.repoUrl ? [" / ", el("a", { href: SITE.repoUrl }, "GitHub 저장소")] : "",
      " / ", el("a", { href: planHref }, "기획서 PDF"));
  }

  // 팀원 이름에 올리거나 초점을 주면 별자리에서 그 사람 몫만 밝힌다
  function followMemberHighlight() {
    const highlight = (event) => {
      const member = event.target.closest("[data-member]");
      window.skyHighlight = member ? Number(member.dataset.member) : -1;
    };
    document.addEventListener("pointerover", highlight);
    document.addEventListener("focusin", highlight);
  }

  renderHero();
  renderIntent();
  renderFeatures();
  renderTech();
  renderPipeline();
  renderStory();
  renderTeam();
  renderSchedule();
  renderOutcomes();
  renderDeliverables();
  renderFeedback();
  renderLinks();
  followMemberHighlight();
  // 별자리가 읽는 값 — 파일을 채운 사람만 밝게
  window.skyTeam = TEAM.map((m) => ({ filled: hasRole(m) }));
})();
