// content/ 의 데이터를 페이지에 꽂는다. 글은 HTML 에 직접 쓰지 않는다 — 디자인을 몰라도 글을 고칠 수 있게.
// example: true 인 값은 「예시」 표시를 붙인다 — 실제 값을 넣으면 그 표시가 사라진다.
(function () {
  const SITE = window.SITE || {};
  const MEMBERS = window.MEMBERS || {};
  const TEAM = (SITE.team || []).map((id, i) => ({ id, i, ...(MEMBERS[id] || { name: id }) }));

  const TECH = [
    ["agent", "AI Agent", "판별 → 추출 → 근거 → 답장을 스스로 계획한다"],
    ["rag", "RAG", "국가법령정보·정부24 를 찾아 근거로 붙인다"],
    ["multimodal", "멀티모달", "사진 속 표·도장·뒷면까지 읽는다"],
    ["workflow", "자동화 워크플로우", "n8n 으로 기한 알림을 보낸다"],
    ["memory", "Long-term Memory", "쓰지 않는다 — 공문은 개인정보라 저장할수록 위험하다"],
  ];
  const DELIVERABLES = [
    ["plan", "기획서", "docs/01-기획서.md"],
    ["spec", "기능 요구 명세서·아키텍처", "docs/02-기능명세.md"],
    ["service", "AI 서비스", "backend/ · web/"],
    ["repo", "GitHub 저장소", ""],
    ["slides", "발표 자료", "docs/05-발표.md"],
    ["deploy", "서비스 배포", "deploy/"],
  ];
  const PEN = { money: "낼 돈", deadline: "기한", document: "챙길 서류" };

  const $ = (sel) => document.querySelector(`[data-slot="${sel}"]`);
  function el(tag, attrs, ...kids) {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else n.setAttribute(k, v);
    }
    for (const k of kids.flat()) {
      if (k == null || k === false) continue;
      n.append(k.nodeType ? k : document.createTextNode(String(k)));
    }
    return n;
  }
  const example = (on) => (on ? el("span", { class: "example", title: "실제 값으로 바꿀 자리" }, "예시") : null);
  const fill = (slot, ...kids) => { const n = $(slot); if (n) n.replaceChildren(...kids.flat()); };

  // 링크
  const deploy = SITE.deployUrl || "#";
  for (const s of ["open", "open2"]) { const n = $(s); if (n) n.href = deploy; }
  if ($("plan")) $("plan").href = SITE.planPdf || "docs/01-기획서.md";

  // 첫 화면
  const hero = SITE.hero || {};
  fill("question", ...(hero.question || "").split("\n").flatMap((l, i) => (i ? [el("br"), l] : [l])));
  fill("answer", hero.answer || SITE.oneLiner || "");

  const doc = hero.doc || {};
  const penText = (text, kind, memo) =>
    kind
      ? el("span", { class: `mark mark-${kind}`, "data-mark": kind, "data-memo": memo || PEN[kind] }, text)
      : text;
  fill(
    "doc",
    el("header", { class: "doc-head" },
      el("span", { class: "doc-issuer" }, doc.issuer || ""),
      el("span", { class: "doc-sample" }, "예시 공문")),
    el("h2", { class: "doc-title" }, doc.title || ""),
    el("table", { class: "doc-table" },
      el("tbody", {}, ...(doc.lines || []).map(([k, v, kind, memo]) =>
        el("tr", {}, el("th", { scope: "row" }, k), el("td", {}, penText(v, kind, memo)))))),
    el("p", { class: "doc-notice" }, doc.notice || ""),
    doc.attach ? el("p", { class: "doc-attach" }, "붙임 ", penText(doc.attach[0], doc.attach[1], doc.attach[2])) : null,
    el("div", { class: "doc-seal", "aria-hidden": "true" }, "직인")
  );
  const t = hero.todo || {};
  fill(
    "todo",
    el("p", { class: "todo-label" }, "할 일 1"),
    el("p", { class: "todo-title" }, t.title || ""),
    el("p", { class: "todo-meta" },
      el("span", { class: "c-deadline" }, t.due || ""), " ",
      el("span", { class: "c-money" }, t.amount || ""), " ",
      el("span", {}, t.how || "")),
    el("p", { class: "todo-ai" }, "AI 풀이 — 원문을 함께 확인하세요")
  );

  // 기획의도
  const it = SITE.intent || {};
  fill("problem", it.problem || "");
  fill("why", ...(it.why || []).map((w) => el("li", {}, w)));
  fill("chat", ...(it.chat || []).map(([who, text]) =>
    who === "note" ? el("li", { class: "chat-note" }, text)
    : el("li", { class: `bubble ${who}` }, text === "[사진]" ? el("span", { class: "photo", "aria-label": "공문 사진" }, "공문 사진") : text)));
  fill("after",
    el("p", { class: "after-photo" }, "사진 한 장"),
    el("ul", { class: "after-marks" },
      el("li", { class: "c-money" }, "48,200원"),
      el("li", { class: "c-deadline" }, "10.31까지"),
      el("li", { class: "c-document" }, "납부서 챙기기")),
    el("p", { class: "after-done" }, "끝. 자녀에게도 링크가 갔어요"));
  const scene = (sc) => (sc && sc.src ? el("img", { src: sc.src, alt: sc.alt || "", loading: "lazy", width: "960", height: "720" }) : null);
  fill("sceneBefore", scene((it.scenes || {}).before));
  fill("sceneAfter", scene((it.scenes || {}).after));
  fill("insight", it.insight || "");
  fill("users", ...(it.users || []).map(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));

  // 기능 — 오른쪽 칸은 작은 그림
  const looks = {
    pens: () => el("span", { class: "look look-pens" },
      el("span", { class: "pen money" }, "돈"), el("span", { class: "pen deadline" }, "기한"), el("span", { class: "pen document" }, "서류")),
    basis: () => el("span", { class: "look look-basis" }, "기한을 넘기면 돈을 조금 더 내요",
      el("q", {}, "연체금이 부과됩니다 — 국민건강보험법 제80조")),
    card: () => el("span", { class: "look look-card" }, el("b", {}, "건강보험료 내기"), " 10.31까지 · 48,200원"),
    share: () => el("span", { class: "look look-share" },
      SITE.shareScene ? el("img", { src: SITE.shareScene.src, alt: SITE.shareScene.alt, loading: "lazy", width: "960", height: "720" }) : null,
      "엄마가 보낸 공문, 해독본으로 확인"),
    reply: () => el("span", { class: "look look-reply" }, "「위와 같이 신청합니다.」", el("small", {}, "준비물: 신분증, 통장 사본")),
  };
  fill("features", ...(SITE.features || []).map((f) =>
    el("tr", {}, el("th", { scope: "row" }, f.name), el("td", {}, f.what), el("td", { class: "look-cell" }, (looks[f.look] || (() => ""))()))));

  // AI
  fill("pipeline", ...(SITE.pipeline || []).map((p) =>
    el("li", {}, el("p", { class: "pipe-step" }, p.step), el("p", { class: "pipe-what" }, p.what),
      el("p", { class: "pipe-meta" }, el("span", { class: "chip" }, p.tech), " ", p.who))));
  fill("guard", SITE.guard || "");
  const tech = SITE.tech || {};
  const picked = TECH.filter(([k]) => tech[k]).length;
  fill("techTally", `다섯 중 ${picked}개를 쓴다. 요건은 2개 이상이다.`);
  fill("tech", ...TECH.map(([k, label, desc]) =>
    el("li", { class: tech[k] ? "is-on" : "is-off" },
      el("span", { class: "box", "aria-hidden": "true" }, tech[k] ? "✓" : ""),
      el("span", { class: "tech-name" }, label, tech[k] ? "" : el("span", { class: "sr" }, " (쓰지 않음)")),
      el("span", { class: "tech-desc" }, desc))));
  fill("stack", ...(SITE.stack || []).map((s) => [el("dt", {}, s.part), el("dd", {}, el("b", {}, s.pick), el("span", {}, s.why))]));

  // 팀 — 결재란
  fill("team", ...TEAM.map((m) =>
    el("div", { class: "sign-cell", role: "listitem" },
      el("p", { class: "sign-role" }, m.role || "역할 미정"),
      el("p", { class: "sign-stamp", "aria-hidden": "true" }, el("span", {}, m.name)),
      el("p", { class: "sign-name" }, m.name, m.id === "juhyun" ? el("span", { class: "lead-mark" }, " 팀장") : ""),
      m.github ? el("a", { class: "sign-gh", href: `https://github.com/${m.github}` }, `@${m.github}`) : null,
      (m.work || []).length ? el("ul", { class: "sign-work" }, ...m.work.map((w) => el("li", {}, w))) : null)));

  // 일정
  fill("schedule", ...(SITE.schedule || []).map((w) =>
    el("li", {}, el("p", { class: "wk" }, `${w.week}주`), el("p", { class: "wk-goal" }, w.goal), el("p", { class: "wk-who" }, w.who))));

  // 기대효과
  fill("effects", ...(SITE.effects || []).map(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
  fill("criteria", ...(SITE.criteria || []).map((c) =>
    el("tr", {}, el("th", { scope: "row" }, c.name), el("td", {}, c.how), el("td", { class: "goal" }, c.goal),
      el("td", { class: "now" }, c.now || "측정 전", example(c.example)))));
  fill("uses", ...(SITE.uses || []).map((u) => el("li", {}, u)));

  // 진행
  const del = SITE.deliverables || {};
  fill("deliverables", ...DELIVERABLES.map(([k, head, file]) =>
    el("li", { class: del[k] ? "is-done" : "" },
      el("span", { class: "box", "aria-hidden": "true" }, del[k] ? "✓" : ""),
      el("span", { class: "del-head" }, head, el("span", { class: "sr" }, del[k] ? " 완료" : " 진행 중")),
      file ? el("code", {}, file) : null)));
  const fb = SITE.feedback || [];
  fill("feedback", ...Array.from({ length: Math.max(5, fb.length) }, (_, i) => {
    const f = fb[i];
    if (!f) return el("li", { class: "fb is-empty" }, el("p", { class: "fb-who" }, `사용자 ${i + 1}`), el("p", {}, "아직 받지 않음"));
    return el("li", { class: "fb" },
      el("p", { class: "fb-who" }, f.who, example(f.example)),
      el("p", { class: "fb-said" }, `“${f.said}”`),
      el("p", { class: "fb-changed" }, f.changed ? `반영: ${f.changed}` : "반영 계획 없음"));
  }));

  fill("links",
    el("a", { href: deploy }, "서비스"), " ",
    SITE.repoUrl ? el("a", { href: SITE.repoUrl }, "GitHub 저장소") : null, " ",
    el("a", { href: SITE.planPdf || "docs/01-기획서.md" }, "기획서 PDF"));
})();
