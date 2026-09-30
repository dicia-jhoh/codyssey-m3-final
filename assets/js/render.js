// content/ 의 데이터를 페이지에 꽂는다. 빈 칸은 숨기지 않고 "어느 파일의 어느 칸" 인지 보여 준다 —
// 팀원이 페이지만 보고도 자기가 채울 곳을 찾게 하려는 것.
(function () {
  const SITE = window.SITE || {};
  const MEMBERS = window.MEMBERS || {};
  const TEAM = (SITE.team || []).map((id, i) => ({ id, i, ...(MEMBERS[id] || { name: id }) }));

  const TECH = [
    ["agent", "AI Agent", "사용자 의도를 파악하고 도구를 써서 목표를 달성한다"],
    ["rag", "RAG", "외부 지식을 검색해 LLM 응답의 근거로 쓴다"],
    ["multimodal", "멀티모달", "텍스트·이미지·음성을 입력이나 출력으로 다룬다"],
    ["workflow", "자동화 워크플로우", "여러 서비스를 이어 붙인 자동 파이프라인"],
    ["memory", "Long-term Memory", "사용자별 기록과 선호를 저장해 다음 대화에 쓴다"],
  ];

  const DELIVERABLES = [
    ["plan", "기획서", "문제·타겟 사용자·AI 활용 방식·일정", "docs/01-기획서.md"],
    ["spec", "기능 요구 명세서", "기능·비기능 요구사항과 시스템 아키텍처", "docs/02-기능명세.md"],
    ["service", "AI 서비스", "생성형 AI 또는 AI Agent 가 핵심인 서비스", ""],
    ["repo", "GitHub 저장소", "소스·문서·버전 관리 기록", ""],
    ["slides", "발표 자료", "문제 해결 과정·기술 결정 근거·피드백 반영", "docs/05-발표.md"],
    ["deploy", "서비스 배포", "외부에서 접근 가능한 주소", ""],
  ];

  const $ = (sel) => document.querySelector(`[data-slot="${sel}"]`);

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") n.className = v;
      else if (k === "style") n.style.cssText = v;
      else n.setAttribute(k, v);
    }
    for (const k of kids.flat()) {
      if (k == null || k === false) continue;
      n.append(k.nodeType ? k : document.createTextNode(String(k)));
    }
    return n;
  }

  // 빈 칸 표시 — 무엇을 어디에 적으면 되는지
  const todo = (what, where) =>
    el("span", { class: "todo" }, what, el("code", {}, where));

  const filled = (m) => Boolean(m.role && m.role.trim());
  const color = (i) => `var(--m${i % 5})`;

  // 첫 화면
  const name = (SITE.name || "").trim();
  $("name").textContent = name || "아직 이름이 없는 AI 서비스";
  $("name").classList.toggle("is-empty", !name);
  $("brand").textContent = name || "M3 Final";
  document.title = name ? `${name} · M3 Final Project` : "M3 Final Project";
  $("oneLiner").replaceChildren(
    SITE.oneLiner
      ? SITE.oneLiner
      : "다섯 명이 문제 하나를 골라 AI 서비스로 만들고, 배포한 뒤 실사용자 다섯 명에게 검증받는다. 주제는 아래 후보에서 정한다."
  );
  if (SITE.repoUrl) $("contribute").href = `${SITE.repoUrl}/blob/main/CONTRIBUTING.md`;

  $("legend").replaceChildren(
    ...TEAM.map((m) =>
      el(
        "li",
        { class: filled(m) ? "" : "is-empty", "data-member": m.i, tabindex: "0" },
        el("span", { class: "dot", style: `--c:${color(m.i)}` }),
        m.name
      )
    )
  );

  // 주제 후보
  $("pitches").replaceChildren(
    ...TEAM.map((m) => {
      const p = m.pitch || {};
      const has = p.title && p.title.trim();
      return el(
        "li",
        { class: has ? "pitch" : "pitch is-empty", "data-member": m.i },
        el("span", { class: "pitch-who" }, el("span", { class: "dot", style: `--c:${color(m.i)}` }), m.name),
        has
          ? el("div", {}, el("p", { class: "pitch-title" }, p.title), el("p", { class: "pitch-problem" }, p.problem || ""))
          : el("div", {}, el("p", { class: "pitch-title" }, "제안 대기"), todo("", `content/members/${m.id}.js 의 pitch`))
      );
    })
  );

  // 기술 요소
  const tech = SITE.tech || {};
  const picked = TECH.filter(([k]) => tech[k]).length;
  $("tech").replaceChildren(
    ...TECH.map(([k, label, desc]) =>
      el(
        "li",
        { class: tech[k] ? "is-on" : "" },
        el("span", { class: "tech-name" }, label),
        el("span", { class: "tech-desc" }, desc)
      )
    )
  );
  $("techTally").replaceChildren(
    el("span", { class: picked >= 2 ? "ok" : "short" }, `${picked}개 선택`),
    picked >= 2 ? ", 요건 충족" : `, ${2 - picked}개 더 필요`
  );

  // 문제 → 해결 → 구조 → 스택
  const story = [
    ["problem", "해결할 문제", "누가, 어떤 상황에서, 무엇 때문에 곤란한가"],
    ["users", "타겟 사용자", "실사용자 다섯 명을 어디서 구할 수 있는가"],
    ["solution", "AI 로 푸는 방식", "AI 를 빼면 이 서비스가 무엇으로 퇴화하는가"],
    ["architecture", "구조", "프런트·백엔드·AI·데이터가 어떻게 이어지는가"],
  ];
  $("story").replaceChildren(
    ...story.map(([k, head, hint], idx) =>
      el(
        "article",
        { class: "story-row" },
        el("h3", { class: "story-head" }, head),
        SITE[k]
          ? el("p", { class: "body" }, SITE[k])
          : el("p", { class: "body is-empty" }, hint, el("br"), todo("", `content/site.js 의 ${k}`))
      )
    ),
    el(
      "article",
      { class: "story-row" },
      el("h3", { class: "story-head" }, "기술 스택과 이유"),
      (SITE.stack || []).length
        ? el(
            "dl",
            { class: "stack" },
            ...SITE.stack.map((s) => [el("dt", {}, s.part), el("dd", {}, el("strong", {}, s.pick), s.why ? ` — ${s.why}` : "")])
          )
        : el("p", { class: "body is-empty" }, "고른 것과 고른 이유를 함께", el("br"), todo("", "content/site.js 의 stack"))
    )
  );

  // 팀
  $("team").replaceChildren(
    ...TEAM.map((m) =>
      el(
        "li",
        { class: filled(m) ? "member" : "member is-empty", "data-member": m.i, tabindex: "0", style: `--c:${color(m.i)}` },
        el("p", { class: "member-role" }, m.role || "역할 미정"),
        el("p", { class: "member-name" }, m.name),
        m.github
          ? el("a", { class: "member-gh", href: `https://github.com/${m.github}` }, `@${m.github}`)
          : el("span", { class: "member-gh" }, "GitHub 미등록"),
        (m.work || []).length
          ? el("ul", { class: "member-work" }, ...m.work.map((w) => el("li", {}, w)))
          : todo("", `content/members/${m.id}.js`),
        (m.prs || []).length
          ? el("p", { class: "member-prs" }, `PR ${m.prs.length}건`)
          : null
      )
    )
  );

  // 결과물
  const del = SITE.deliverables || {};
  $("deliverables").replaceChildren(
    ...DELIVERABLES.map(([k, head, desc, file]) =>
      el(
        "li",
        { class: del[k] ? "is-done" : "" },
        el("span", { class: "del-state" }, del[k] ? "완료" : "남음"),
        el("span", { class: "del-head" }, head),
        el("span", { class: "del-desc" }, desc, file ? el("code", {}, file) : "")
      )
    )
  );

  const fb = SITE.feedback || [];
  const rows = [];
  for (let i = 0; i < Math.max(5, fb.length); i++) {
    const f = fb[i];
    rows.push(
      f
        ? el("li", { class: "fb" }, el("span", { class: "fb-who" }, f.who), el("span", {}, f.said), el("span", { class: "fb-changed" }, f.changed ? `반영: ${f.changed}` : "반영 전"))
        : el("li", { class: "fb is-empty" }, el("span", { class: "fb-who" }, `사용자 ${i + 1}`), el("span", {}, "아직 받지 않음"))
    );
  }
  $("feedback").replaceChildren(...rows);

  $("deploy").replaceChildren(
    SITE.deployUrl ? el("a", { href: SITE.deployUrl }, SITE.deployUrl) : "배포 주소 미정",
    SITE.repoUrl ? [" / ", el("a", { href: SITE.repoUrl }, "GitHub 저장소")] : ""
  );

  // 팀원 이름에 올리면 별자리에서 그 사람 몫만 밝힌다
  document.addEventListener("pointerover", (e) => {
    const t = e.target.closest("[data-member]");
    window.skyHighlight = t ? Number(t.dataset.member) : -1;
  });
  document.addEventListener("focusin", (e) => {
    const t = e.target.closest("[data-member]");
    window.skyHighlight = t ? Number(t.dataset.member) : -1;
  });

  // 별자리가 읽는 값 — 파일을 채운 사람만 밝게
  window.skyTeam = TEAM.map((m) => ({ filled: filled(m) }));
})();
