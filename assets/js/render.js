// content/ 의 데이터를 페이지에 꽂는다. 빈 칸은 숨기지 않고 "어느 파일의 어느 칸" 인지 보여 준다 —
// 팀원이 페이지만 보고도 자기가 채울 곳을 찾게 하려는 것.
// example: true 인 값(아직 재지 않은 측정값·피드백)에는 「예시」 표시를 붙인다 — 실제 값을 넣으면 사라진다.
(function () {
  const SITE = window.SITE || {};
  const MEMBERS = window.MEMBERS || {};
  const TEAM = (SITE.team || []).map((id, i) => ({ id, i, ...(MEMBERS[id] || { name: id }) }));

  const TECH = [
    ["agent", "AI Agent", "판별 → 추출 → 근거 → 답장을 스스로 계획하고 알림 도구를 부른다"],
    ["rag", "RAG", "국가법령정보·정부24 안내를 찾아 풀이의 근거로 붙인다"],
    ["multimodal", "멀티모달", "구겨진 사진 속 표·도장·뒷면까지 읽고 좌표를 뽑는다"],
    ["workflow", "자동화 워크플로우", "n8n 이 기한 D-3·D-day 알림을 보낸다"],
    ["memory", "Long-term Memory", "쓰지 않는다 — 공문은 개인정보라 저장할수록 위험하다"],
  ];

  const DELIVERABLES = [
    ["plan", "기획서", "문제·타겟 사용자·AI 활용 방식·일정", "docs/01-기획서.md"],
    ["spec", "기능 요구 명세서", "기능·비기능 요구사항과 시스템 아키텍처", "docs/02-기능명세.md"],
    ["service", "AI 서비스", "생성형 AI 또는 AI Agent 가 핵심인 서비스", "backend/ · web/"],
    ["repo", "GitHub 저장소", "소스·문서·버전 관리 기록", ""],
    ["slides", "발표 자료", "문제 해결 과정·기술 결정 근거·피드백 반영", "docs/05-발표.md"],
    ["deploy", "서비스 배포", "외부에서 접근 가능한 주소", "deploy/"],
  ];

  // 펜 3색 — 뜻이 정해진 색이다(빨강 = 낼 돈, 파랑 = 기한, 초록 = 챙길 서류). 서비스 화면 web/ 과 같은 약속
  const PENS = [["money", "낼 돈"], ["deadline", "기한"], ["document", "챙길 서류"]];

  const $ = (sel) => document.querySelector(`[data-slot="${sel}"]`);

  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
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
  const fill = (slot, ...kids) => { const n = $(slot); if (n) n.replaceChildren(...kids.flat()); };

  // 빈 칸 표시 — 무엇을 어디에 적으면 되는지
  const todo = (what, where) =>
    el("span", { class: "todo" }, what, el("code", {}, where));
  const example = (on) => (on ? el("span", { class: "example", title: "실제 값으로 바꿀 자리" }, "예시") : null);
  const img = (sc, cls) =>
    sc && sc.src ? el("img", { class: cls, src: sc.src, alt: sc.alt || "", loading: "lazy", width: "960", height: "720" }) : null;

  const filled = (m) => Boolean(m.role && m.role.trim());
  const color = (i) => `var(--m${i % 5})`;

  // 첫 화면
  const name = (SITE.name || "").trim();
  $("name").textContent = name || "M3 Final Project";
  $("name").classList.toggle("is-empty", !name);
  $("brand").textContent = name || "M3 Final";
  document.title = name ? `${name} · M3 Final Project` : "M3 Final Project";
  fill("oneLiner", SITE.oneLiner || "다섯 명이 문제 하나를 골라 AI 서비스로 만들고, 배포한 뒤 실사용자 다섯 명에게 검증받는다.");
  if (SITE.repoUrl) $("contribute").href = `${SITE.repoUrl}/blob/main/CONTRIBUTING.md`;
  for (const s of ["open", "open2"]) { const n = $(s); if (n && SITE.deployUrl) n.href = SITE.deployUrl; }
  if ($("plan")) $("plan").href = SITE.planPdf || "docs/01-기획서.md";

  fill(
    "legend",
    ...TEAM.map((m) =>
      el(
        "li",
        { class: filled(m) ? "" : "is-empty", "data-member": m.i, tabindex: "0" },
        el("span", { class: "dot", style: `--c:${color(m.i)}` }),
        m.name
      )
    )
  );

  // 기획의도
  const it = SITE.intent || {};
  const hero = SITE.hero || {};
  fill("question", ...(hero.question || "").split("\n").flatMap((l, i) => (i ? [el("br"), l] : [l])));
  fill("problem", it.problem || "");
  fill("why", ...(it.why || []).map((w) => el("li", {}, w)));
  const sc = it.scenes || {};
  const chat = (it.chat || []).filter(([who]) => who === "parent").map(([, t]) => t).filter((t) => t !== "[사진]");
  fill(
    "scenes",
    el("figure", { class: "scene" },
      img(sc.before),
      el("figcaption", {},
        el("span", { class: "scene-tag" }, "지금"),
        el("span", { class: "scene-quote" }, chat.map((t) => `“${t}”`).join(" ")),
        el("span", { class: "scene-note" }, "사진을 찍어 자녀에게 묻는다. 자녀가 바쁘면 그냥 쌓아 둔다."))),
    el("figure", { class: "scene" },
      img(sc.after),
      el("figcaption", {},
        el("span", { class: "scene-tag is-on" }, "또박또박"),
        el("span", { class: "scene-marks" },
          ...PENS.map(([k], i) => el("span", { class: "pen", style: `--c:var(--pen-${k})` }, ["48,200원", "10.31까지", "납부서 챙기기"][i]))),
        el("span", { class: "scene-note" }, "사진 한 장으로 끝. 자녀에게도 해독본 링크가 간다.")))
  );
  fill("insight", it.insight || "");
  fill("users", ...(it.users || []).map(([k, v]) =>
    el("li", { class: "pitch" }, el("span", { class: "pitch-who" }, k), el("div", {}, el("p", { class: "pitch-problem is-lead" }, v)))));

  // 핵심 기능 — 주제 후보 행과 같은 모양
  fill("features", ...(SITE.features || []).map((f) =>
    el("li", { class: "pitch" },
      el("span", { class: "pitch-who" },
        f.look === "pens" ? PENS.map(([k]) => el("span", { class: "dot", style: `--c:var(--pen-${k})` })) : el("span", { class: "dot", style: "--c:var(--iris)" })),
      el("div", { class: f.look === "share" && SITE.shareScene ? "pitch-with-img" : "" },
        el("div", {}, el("p", { class: "pitch-title" }, f.name), el("p", { class: "pitch-problem" }, f.what)),
        f.look === "share" ? img(SITE.shareScene, "pitch-img") : null))));

  // 기술 요소
  const tech = SITE.tech || {};
  const picked = TECH.filter(([k]) => tech[k]).length;
  fill("tech", ...TECH.map(([k, label, desc]) =>
    el("li", { class: tech[k] ? "is-on" : "" }, el("span", { class: "tech-name" }, label), el("span", { class: "tech-desc" }, desc))));
  fill("techTally",
    el("span", { class: picked >= 2 ? "ok" : "short" }, `${picked}개 선택`),
    picked >= 2 ? ", 요건 충족" : `, ${2 - picked}개 더 필요`);

  // AI 4단계 — 실제 순서라 번호를 단다
  fill("pipeline", ...(SITE.pipeline || []).map((p, i) =>
    el("li", {},
      el("span", { class: "step-no" }, String(i + 1)),
      el("span", { class: "del-head" }, p.step),
      el("span", { class: "del-desc" }, p.what, el("span", { class: "step-meta" }, `${p.tech} · ${p.who}`)))));
  fill("guard", SITE.guard || "");

  // 문제 → 사용자 → 해결 → 구조 → 스택
  const story = [
    ["problem", "해결할 문제", "누가, 어떤 상황에서, 무엇 때문에 곤란한가"],
    ["users", "타겟 사용자", "실사용자 다섯 명을 어디서 구할 수 있는가"],
    ["solution", "AI 로 푸는 방식", "AI 를 빼면 이 서비스가 무엇으로 퇴화하는가"],
    ["architecture", "구조", "프런트·백엔드·AI·데이터가 어떻게 이어지는가"],
  ];
  fill(
    "story",
    ...story.map(([k, head, hint]) =>
      el("article", { class: "story-row" },
        el("h3", { class: "story-head" }, head),
        SITE[k]
          ? el("p", { class: "body" }, SITE[k])
          : el("p", { class: "body is-empty" }, hint, el("br"), todo("", `content/site.js 의 ${k}`)))),
    el("article", { class: "story-row" },
      el("h3", { class: "story-head" }, "기술 스택과 이유"),
      (SITE.stack || []).length
        ? el("dl", { class: "stack" }, ...SITE.stack.map((s) => [el("dt", {}, s.part), el("dd", {}, el("strong", {}, s.pick), s.why ? ` — ${s.why}` : "")]))
        : el("p", { class: "body is-empty" }, "고른 것과 고른 이유를 함께", el("br"), todo("", "content/site.js 의 stack")))
  );

  // 팀
  fill("team", ...TEAM.map((m) =>
    el("li", { class: filled(m) ? "member" : "member is-empty", "data-member": m.i, tabindex: "0", style: `--c:${color(m.i)}` },
      el("p", { class: "member-role" }, m.role || "역할 미정", m.id === "juhyun" ? " · 팀장" : ""),
      el("p", { class: "member-name" }, m.name),
      m.github
        ? el("a", { class: "member-gh", href: `https://github.com/${m.github}` }, `@${m.github}`)
        : el("span", { class: "member-gh" }, "GitHub 미등록"),
      (m.work || []).length
        ? el("ul", { class: "member-work" }, ...m.work.map((w) => el("li", {}, w)))
        : todo("", `content/members/${m.id}.js`),
      (m.prs || []).length ? el("p", { class: "member-prs" }, `PR ${m.prs.length}건`) : null)));

  // 일정
  fill("schedule", ...(SITE.schedule || []).map((w, i, all) =>
    el("li", { class: i === all.length - 1 ? "is-done" : "" },
      el("span", { class: "del-state" }, `${w.week}주`),
      el("span", { class: "del-head" }, w.goal),
      el("span", { class: "del-desc" }, w.who))));

  // 기대효과·활용방안·성공 기준
  fill("effects", ...(SITE.effects || []).map(([k, v]) =>
    el("li", { class: "pitch" }, el("span", { class: "pitch-who" }, el("span", { class: "dot", style: "--c:var(--saffron)" })),
      el("div", {}, el("p", { class: "pitch-title" }, k), el("p", { class: "pitch-problem" }, v)))));
  fill("uses", ...(SITE.uses || []).map((u) => el("li", {}, u)));
  fill("criteria", ...(SITE.criteria || []).map((c) =>
    el("li", { class: "is-done" },
      el("span", { class: "del-state" }, c.name),
      el("span", { class: "del-head goal" }, c.goal),
      el("span", { class: "del-desc" }, c.how,
        el("span", { class: "now" }, "지금 ", el("strong", {}, c.now || "측정 전"), example(c.example))))));

  // 결과물
  const del = SITE.deliverables || {};
  fill("deliverables", ...DELIVERABLES.map(([k, head, desc, file]) =>
    el("li", { class: del[k] ? "is-done" : "" },
      el("span", { class: "del-state" }, del[k] ? "완료" : "남음"),
      el("span", { class: "del-head" }, head),
      el("span", { class: "del-desc" }, desc, file ? el("code", {}, file) : ""))));

  const fb = SITE.feedback || [];
  const rows = [];
  for (let i = 0; i < Math.max(5, fb.length); i++) {
    const f = fb[i];
    rows.push(
      f
        ? el("li", { class: "fb" },
            el("span", { class: "fb-who" }, f.who, example(f.example)),
            el("span", {}, `“${f.said}”`),
            el("span", { class: "fb-changed" }, f.changed ? `반영: ${f.changed}` : "반영 전"))
        : el("li", { class: "fb is-empty" }, el("span", { class: "fb-who" }, `사용자 ${i + 1}`), el("span", {}, "아직 받지 않음"))
    );
  }
  fill("feedback", ...rows);

  fill("links",
    SITE.deployUrl ? el("a", { href: SITE.deployUrl }, "서비스") : "배포 주소 미정",
    SITE.repoUrl ? [" / ", el("a", { href: SITE.repoUrl }, "GitHub 저장소")] : "",
    " / ", el("a", { href: SITE.planPdf || "docs/01-기획서.md" }, "기획서 PDF"));

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
