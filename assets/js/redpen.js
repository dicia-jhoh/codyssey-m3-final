// 첫 화면 — 고지서 위에 빨간펜이 한 번 지나간다.
// [data-mark] 글자마다 손으로 그은 듯한 선(돈 = 동그라미, 기한 = 물결 밑줄, 서류 = 형광펜)을 SVG 로 얹고,
// 순서대로 그은 뒤 손글씨 메모를 달고, 마지막에 할 일 카드를 붙인다. 페이지 로드 때 딱 한 번.
(function () {
  const doc = document.querySelector('[data-slot="doc"]');
  const card = document.querySelector('[data-slot="todo"]');
  if (!doc) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NS = "http://www.w3.org/2000/svg";
  const ORDER = ["money", "deadline", "document"];
  let svg;

  // 같은 모양이 매번 나오도록 고정 난수(손 떨림)
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5);

  function shape(kind, r) {
    const { x, y, w, h } = r;
    if (kind === "money") {
      // 살짝 기운 타원 두 바퀴 — 빨간펜으로 동그라미 친 모양
      const cx = x + w / 2, cy = y + h / 2, rx = w / 2 + 14, ry = h / 2 + 10;
      let d = "";
      for (let i = 0; i <= 44; i++) {
        const a = (i / 40) * Math.PI * 2 - 0.6;
        const px = cx + Math.cos(a) * (rx + rnd() * 3);
        const py = cy + Math.sin(a) * (ry + rnd() * 2) + Math.cos(a) * 2;
        d += (i ? "L" : "M") + px.toFixed(1) + " " + py.toFixed(1);
      }
      return d;
    }
    if (kind === "deadline") {
      // 물결 밑줄
      const by = y + h + 5;
      let d = `M${x - 4} ${by}`;
      for (let px = x - 4; px < x + w + 6; px += 9) d += ` q4.5 ${-5 + rnd() * 2} 9 0`;
      return d;
    }
    // document: 형광펜 한 획(굵은 선)
    const my = y + h / 2 + 1;
    return `M${x - 6} ${my + rnd() * 2} L${x + w + 6} ${my + rnd() * 2}`;
  }

  function draw(animate) {
    seed = 7;
    svg?.remove();
    doc.querySelectorAll(".memo").forEach((m) => m.remove());
    const box = doc.getBoundingClientRect();
    svg = document.createElementNS(NS, "svg");
    svg.setAttribute("class", "pen-layer");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("viewBox", `0 0 ${box.width} ${box.height}`);
    doc.append(svg);

    const marks = [...doc.querySelectorAll("[data-mark]")].sort(
      (a, b) => ORDER.indexOf(a.dataset.mark) - ORDER.indexOf(b.dataset.mark)
    );
    let t = 400;
    marks.forEach((m) => {
      const r0 = m.getBoundingClientRect();
      const r = { x: r0.left - box.left, y: r0.top - box.top, w: r0.width, h: r0.height };
      const kind = m.dataset.mark;
      const p = document.createElementNS(NS, "path");
      p.setAttribute("d", shape(kind, r));
      p.setAttribute("class", `stroke stroke-${kind}`);
      svg.append(p);

      const memo = document.createElement("span");
      memo.className = `memo memo-${kind}`;
      memo.textContent = m.dataset.memo;
      memo.style.left = `${Math.min(r.x + r.w + 26, box.width - 110)}px`;
      memo.style.top = `${r.y - 14}px`;
      memo.setAttribute("aria-hidden", "true");
      doc.append(memo);

      if (animate) {
        const len = p.getTotalLength();
        p.style.strokeDasharray = len;
        p.style.strokeDashoffset = len;
        p.getBoundingClientRect();
        p.style.transition = `stroke-dashoffset ${kind === "document" ? 380 : 620}ms cubic-bezier(.6,.1,.3,1) ${t}ms`;
        p.style.strokeDashoffset = 0;
        memo.style.transitionDelay = `${t + 450}ms`;
        t += 700;
      }
      if (animate) requestAnimationFrame(() => memo.classList.add("is-in"));
      else { memo.style.transition = "none"; memo.classList.add("is-in"); }
    });
    if (card) {
      if (animate) {
        card.style.transitionDelay = `${t + 200}ms`;
        requestAnimationFrame(() => card.classList.add("is-in"));
      } else {
        // 움직임을 끈 사람·다시 맞출 때는 기다리지 않고 바로 보인다
        card.style.transition = "none";
        card.classList.add("is-in");
      }
    }
  }

  const start = () => draw(!reduce);
  // 글꼴이 늦게 오면 글자 폭이 바뀌어 선이 어긋난다 — 글꼴을 기다린 뒤 긋는다
  (document.fonts?.ready || Promise.resolve()).then(start);

  // 화면 폭이 바뀌면 애니메이션 없이 다시 맞춘다
  let timer;
  addEventListener("resize", () => {
    clearTimeout(timer);
    timer = setTimeout(() => draw(false), 150);
  });
})();
