// 첫 화면 별자리 — 외곽선 삼각형 수천 개가 모여 구름 하나가 된다.
// 다섯 덩어리가 팀원 다섯 명이고, 자기 파일을 채운 사람의 덩어리만 제 색으로 빛난다.
(function () {
  const canvas = document.getElementById("sky");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const COLORS = ["#8052ff", "#ffb829", "#1fbf9c", "#ff4fa3", "#3d8bff"];

  let W = 0, H = 0, DPR = 1;
  let cx = 0, cy = 0, R = 0;
  let parts = [];
  let ambient = [];
  const pointer = { x: -9999, y: -9999 };

  // 가우시안 표본 — 덩어리 가장자리가 흩어지게
  function gauss() {
    let u = 0, v = 0;
    while (!u) u = Math.random();
    while (!v) v = Math.random();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  function layout() {
    DPR = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth;
    H = window.innerHeight;
    canvas.width = W * DPR;
    canvas.height = H * DPR;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);

    const wide = W > 900;
    cx = wide ? W * 0.68 : W * 0.5;
    cy = wide ? H * 0.5 : H * 0.42;
    R = Math.min(wide ? W * 0.26 : W * 0.46, H * 0.4);
  }

  function seed() {
    const n = W > 900 ? 2600 : 1300;
    // 다섯 덩어리 — 뇌처럼 가운데로 겹쳐 모인다
    const lobes = [...Array(5)].map((_, i) => {
      const a = -Math.PI / 2 + (i * 2 * Math.PI) / 5 + 0.3;
      return { x: Math.cos(a) * 0.42, y: Math.sin(a) * 0.34, s: 0.34 + (i % 2) * 0.06 };
    });
    parts = [];
    for (let k = 0; k < n; k++) {
      const m = k % 5;
      // 25% 는 이웃 덩어리 쪽으로 섞어 경계를 흐린다
      const lobe = lobes[Math.random() < 0.75 ? m : (m + 1) % 5];
      const hx = lobe.x + gauss() * lobe.s * 0.62;
      const hy = lobe.y + gauss() * lobe.s * 0.52;
      parts.push({
        m,
        hx, hy, // 구름 안의 제자리(반지름 단위)
        x: (Math.random() - 0.5) * 3.2, // 처음엔 화면 밖까지 흩어져 있다가 모인다
        y: (Math.random() - 0.5) * 3.2,
        size: 2.2 + Math.random() * 4.2,
        rot: Math.random() * Math.PI * 2,
        spin: (Math.random() - 0.5) * 0.01,
        phase: Math.random() * Math.PI * 2,
        amp: 0.006 + Math.random() * 0.014,
      });
    }
    ambient = [...Array(W > 900 ? 90 : 40)].map(() => ({
      x: Math.random() * W,
      y: Math.random() * H * 1.2,
      size: 1.5 + Math.random() * 2.5,
      rot: Math.random() * Math.PI * 2,
      c: COLORS[(Math.random() * 5) | 0],
      vy: -(0.05 + Math.random() * 0.15),
    }));
  }

  function tri(x, y, s, r) {
    for (let j = 0; j < 3; j++) {
      const a = r + (j * 2 * Math.PI) / 3;
      const px = x + Math.cos(a) * s;
      const py = y + Math.sin(a) * s;
      j ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.closePath();
  }

  let t0 = performance.now();

  function frame(now) {
    const t = (now - t0) / 1000;
    const team = window.skyTeam || [];
    const hi = typeof window.skyHighlight === "number" ? window.skyHighlight : -1;

    // 스크롤하면 구름이 위로 빠지며 옅어진다 — 아래 섹션 글을 가리지 않게
    const scroll = window.scrollY;
    const fade = Math.max(0, 1 - scroll / (H * 0.9));
    const oy = -scroll * 0.35;

    ctx.clearRect(0, 0, W, H);
    ctx.lineWidth = 1;

    // 배경에 떠다니는 조각 — 스크롤과 무관하게 얕게 깔린다
    ctx.globalAlpha = 0.28;
    for (const a of ambient) {
      if (!reduce) {
        a.y += a.vy;
        a.rot += 0.002;
        if (a.y < -10) a.y = H + 10;
      }
      ctx.strokeStyle = a.c;
      ctx.beginPath();
      tri(a.x, a.y, a.size, a.rot);
      ctx.stroke();
    }

    if (fade > 0.01) {
      const ease = reduce ? 1 : Math.min(1, t / 2.4);
      const k = 1 - Math.pow(1 - ease, 3); // 모여드는 한 번의 순간
      // 구름 전체가 아주 천천히 돈다(한 바퀴 약 3분)
      const swirl = reduce ? 0 : t * 0.035;
      const cs = Math.cos(swirl), sn = Math.sin(swirl);

      // 색별로 경로를 한 번에 그려 stroke 호출을 줄인다
      const paths = COLORS.map(() => new Path2D());
      const dimPaths = COLORS.map(() => new Path2D());
      const hiPaths = COLORS.map(() => new Path2D());

      for (const p of parts) {
        const breathe = reduce ? 0 : Math.sin(t * 0.8 + p.phase) * p.amp;
        const bx = p.hx * (1 + breathe), by = p.hy * (1 + breathe);
        const hx = bx * cs - by * sn;
        const hy = (bx * sn + by * cs) * 0.82; // 가로로 약간 긴 타원
        const nx = p.x + (hx - p.x) * k;
        const ny = p.y + (hy - p.y) * k;
        let x = cx + nx * R;
        let y = cy + ny * R + oy;

        // 포인터 가까이의 조각은 밀려난다
        const dx = x - pointer.x, dy = y - pointer.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < 14000) {
          const push = (1 - d2 / 14000) * 26;
          const d = Math.sqrt(d2) || 1;
          x += (dx / d) * push;
          y += (dy / d) * push;
        }

        if (!reduce) p.rot += p.spin;
        const lit = team[p.m] ? team[p.m].filled : false;
        const path = hi === p.m ? hiPaths[p.m] : lit ? paths[p.m] : dimPaths[p.m];
        const a = p.rot;
        for (let j = 0; j < 3; j++) {
          const ang = a + (j * 2 * Math.PI) / 3;
          const px = x + Math.cos(ang) * p.size;
          const py = y + Math.sin(ang) * p.size;
          j ? path.lineTo(px, py) : path.moveTo(px, py);
        }
        path.closePath();
      }

      // 빈 자리도 제 색을 옅게 띤다 — 채우면 선명해진다. 누군가를 가리키면 나머지는 한 발 물러난다
      const dimmed = hi >= 0 ? 0.3 : 1;
      COLORS.forEach((c, i) => {
        ctx.strokeStyle = c;
        ctx.globalAlpha = 0.38 * fade * dimmed;
        ctx.stroke(dimPaths[i]);
        ctx.globalAlpha = 0.95 * fade * dimmed;
        ctx.stroke(paths[i]);
        ctx.globalAlpha = fade;
        ctx.stroke(hiPaths[i]);
      });
    }
    ctx.globalAlpha = 1;

    if (!reduce) requestAnimationFrame(frame);
  }

  addEventListener("pointermove", (e) => {
    pointer.x = e.clientX;
    pointer.y = e.clientY;
  });
  addEventListener("pointerleave", () => {
    pointer.x = pointer.y = -9999;
  });
  addEventListener("resize", () => {
    layout();
    seed();
    if (reduce) frame(performance.now());
  });
  if (reduce) addEventListener("scroll", () => frame(performance.now()), { passive: true });

  layout();
  seed();
  requestAnimationFrame(frame);
})();
