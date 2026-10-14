// 담당: 송유영. 사진 → POST /decode → 3색 표시 · 할 일 카드 · 근거
const API_BASE = "http://localhost:8000"; // 배포하면 Render 주소로 바꾼다

const $ = (id) => document.getElementById(id);

$("photo").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  $("preview").src = URL.createObjectURL(file);
  $("status").textContent = "공문을 읽고 있어요…";
  $("result").hidden = true;

  const form = new FormData();
  form.append("file", file);
  try {
    const r = await fetch(`${API_BASE}/decode`, { method: "POST", body: form });
    if (!r.ok) throw new Error((await r.json()).detail || r.status);
    show(await r.json());
    $("status").textContent = "";
  } catch (err) {
    $("status").textContent = `읽지 못했어요: ${err.message}. 서버가 켜져 있는지 확인해 주세요.`;
  }
});

function show(d) {
  $("sample").hidden = !d.sample;
  $("aiNotice").textContent = d.ai_notice;
  $("title").textContent = d.title;

  // bbox = [x, y, w, h] 사진 대비 비율 → 퍼센트 위치
  $("marks").replaceChildren(
    ...d.marks.map((m) => {
      const box = document.createElement("span");
      box.className = `mark ${m.kind}`;
      const [x, y, w, h] = m.bbox.map((v) => `${v * 100}%`);
      Object.assign(box.style, { left: x, top: y, width: w, height: h });
      box.title = m.text;
      return box;
    })
  );

  $("todos").replaceChildren(
    ...d.todos.map((t) => {
      const li = document.createElement("li");
      const money = t.amount != null ? ` · ${t.amount.toLocaleString("ko-KR")}원` : "";
      li.innerHTML = `<strong></strong><span></span>`;
      li.querySelector("strong").textContent = t.title;
      li.querySelector("span").textContent = `${t.due ?? "기한 없음"}까지${money} · ${t.how}`;
      return li;
    })
  );

  $("basis").replaceChildren(
    ...d.basis.map((b) => {
      const li = document.createElement("li");
      li.textContent = b.claim;
      const q = document.createElement("blockquote");
      q.textContent = `원문: ${b.quote}${b.law ? ` (${b.law})` : ""}`;
      li.append(q);
      return li;
    })
  );
  $("result").hidden = false;
}
