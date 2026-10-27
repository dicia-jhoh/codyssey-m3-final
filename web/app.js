// 담당: 송유영. 사진 → POST /decode → 3색 표시 · 할 일 카드 · 근거
// 백엔드가 화면을 같이 내준다(/app/) — API 는 같은 주소다

const $ = (id) => document.getElementById(id);

let currentDecoded = null; // "가족에게 보내기"가 다시 보낼 최근 해독 결과
let previewUrl = null;
let largeTextEnabled = false;
try {
  largeTextEnabled = localStorage.getItem("largeText") === "true";
} catch {}

function updateTextSize() {
  document.documentElement.classList.toggle("large-text", largeTextEnabled);
  $("textSizeBtn").setAttribute("aria-pressed", String(largeTextEnabled));
  $("textSizeBtn").textContent = largeTextEnabled ? "기본 글자" : "글자 크게";
}

updateTextSize();
$("textSizeBtn").addEventListener("click", () => {
  largeTextEnabled = !largeTextEnabled;
  updateTextSize();
  try {
    localStorage.setItem("largeText", String(largeTextEnabled));
  } catch {}
});
const completedTodos = loadCompletedTodos();

function loadCompletedTodos() {
  try {
    const saved = JSON.parse(localStorage.getItem("completedTodos") || "[]");
    return new Set(Array.isArray(saved) ? saved.filter((key) => typeof key === "string") : []);
  } catch {
    return new Set();
  }
}

function saveCompletedTodos() {
  try {
    localStorage.setItem("completedTodos", JSON.stringify([...completedTodos]));
  } catch {}
}

// 손주 모드: ?share=<id> 로 열리면 사진 올리기 없이 저장된 해독 결과를 바로 보여준다.
// 원본 사진은 공유 저장소에 아예 없다(AI 윤리 — share.py 참고) — 그래서 3색 사진
// 오버레이 없이 글자 정보(할 일·근거)만 보여준다.
const sharedId = new URLSearchParams(location.search).get("share");
if (sharedId) {
  $("upload-section").hidden = true;
  $("photoSection").hidden = true;
  $("status").textContent = "불러오는 중…";
  fetch(`/share/${encodeURIComponent(sharedId)}`)
    .then((r) => {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    })
    .then((d) => {
      $("grandchildNotice").hidden = false;
      show(d);
      $("status").textContent = "";
    })
    .catch((err) => {
      console.error(err);
      $("status").textContent =
        err.message === "404"
          ? "링크 기한이 지났어요. 가족에게 새 링크를 받아 주세요."
          : "지금은 열 수 없어요. 잠시 뒤 다시 열어 주세요.";
    });
}

$("photo").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const previousPreviewUrl = previewUrl;
  previewUrl = URL.createObjectURL(file);
  $("preview").src = previewUrl;
  if (previousPreviewUrl) URL.revokeObjectURL(previousPreviewUrl);
  $("status").textContent = "고지서를 읽고 있어요…";
  $("result").hidden = true;

  const form = new FormData();
  form.append("file", file);
  try {
    const r = await fetch("/decode", { method: "POST", body: form });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      // 4xx detail 은 서버가 사용자에게 하는 말(크기·형식) — 다시 찍어도 안 되니 그대로 보여 준다
      if (r.status < 500 && typeof body.detail === "string") {
        $("status").textContent = body.detail;
        return;
      }
      throw new Error(String(r.status));
    }
    show(await r.json());
    $("status").textContent = "";
  } catch (err) {
    console.error(err);
    $("status").textContent = "사진을 읽지 못했어요. 밝은 곳에서 다시 찍어 올려 주세요.";
  } finally {
    e.target.value = "";
  }
});

$("shareBtn").addEventListener("click", async () => {
  if (!currentDecoded) return;
  $("shareResult").textContent = "링크 만드는 중…";
  try {
    const r = await fetch("/share", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentDecoded),
    });
    if (!r.ok) throw new Error(String(r.status));
    const { share_id } = await r.json();
    const link = `${location.origin}${location.pathname}?share=${share_id}`;
    if (navigator.share) {
      try {
        await navigator.share({
          title: "또박또박 해독 결과",
          text: "가족과 함께 확인해 주세요.",
          url: link,
        });
        $("shareResult").textContent = "공유 창을 열었어요.";
        return;
      } catch (err) {
        if (err.name === "AbortError") {
          $("shareResult").textContent = "공유를 취소했어요.";
          return;
        }
      }
    }
    try {
      if (!navigator.clipboard?.writeText) throw new Error("클립보드를 사용할 수 없어요");
      await navigator.clipboard.writeText(link);
      $("shareResult").textContent = "링크를 복사했어요. 가족에게 붙여넣어 보내세요.";
      return;
    } catch {
      // Clipboard access can be unavailable outside secure browser contexts.
    }
    $("shareResult").innerHTML = "";
    const label = document.createElement("span");
    label.textContent = "링크를 복사해 가족에게 보내세요: ";
    const input = document.createElement("input");
    input.readOnly = true;
    input.value = link;
    input.onclick = () => input.select();
    $("shareResult").append(label, input);
  } catch (err) {
    console.error(err);
    $("shareResult").textContent = "링크를 만들지 못했어요. 잠시 뒤 다시 눌러 주세요.";
  }
});

function show(d) {
  currentDecoded = d;
  $("sample").hidden = !d.sample;
  $("aiNotice").textContent = d.ai_notice;
  $("title").textContent = d.title;

  // bbox = [x, y, w, h] 사진 대비 비율 → 퍼센트 위치
  $("marks").replaceChildren(
    ...d.marks.map((m) => {
      const box = document.createElement("button");
      const kindLabel = { money: "낼 돈", deadline: "기한", document: "챙길 서류" }[m.kind] || "원문";
      box.className = `mark ${m.kind}`;
      box.type = "button";
      box.setAttribute("aria-label", `${kindLabel}: ${m.text}`);
      box.setAttribute("aria-expanded", "false");
      const [x, y, w, h] = m.bbox.map((v) => `${v * 100}%`);
      Object.assign(box.style, { left: x, top: y, width: w, height: h });
      const text = document.createElement("span");
      text.className = "mark-text";
      text.textContent = m.text;
      text.hidden = true;
      box.append(text);
      box.addEventListener("click", () => {
        const expanded = box.getAttribute("aria-expanded") === "true";
        box.setAttribute("aria-expanded", String(!expanded));
        text.hidden = expanded;
      });
      return box;
    })
  );

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  $("todos").replaceChildren(
    ...d.todos.map((t) => {
      const li = document.createElement("li");
      const dueDate = t.due ? new Date(`${t.due}T00:00:00`) : null;
      const validDueDate = dueDate && Number.isFinite(dueDate.getTime());
      const daysRemaining = validDueDate
        ? Math.round((dueDate - today) / 86400000)
        : null;
      const dueDateLabel = validDueDate
        ? `${dueDate.getMonth() + 1}월 ${dueDate.getDate()}일(${dueDate.toLocaleDateString("ko-KR", { weekday: "short" })})`
        : "";
      let due = "기한 없음";
      if (t.due && !validDueDate) due = `${t.due}까지`;
      else if (daysRemaining > 0) {
        due = `${dueDateLabel}까지 · ${daysRemaining}일 남았어요`;
      } else if (daysRemaining === 0) due = "오늘까지예요";
      else if (daysRemaining < 0) due = `${dueDateLabel}까지였어요 · 기한이 지났어요`;
      const money = t.amount != null ? `${t.amount.toLocaleString("ko-KR")}원` : "";
      const title = document.createElement("strong");
      const dueElement = document.createElement("span");
      const details = document.createElement("span");
      const button = document.createElement("button");
      const key = JSON.stringify([t.title, t.due || ""]);
      const completed = completedTodos.has(key);
      title.textContent = t.title;
      dueElement.className = "due";
      dueElement.textContent = due;
      if (daysRemaining < 0) dueElement.classList.add("overdue");
      details.className = "details";
      // 금액·방법이 둘 다 없으면 빈 줄, 하나만 있으면 앞에 「 · 」 없이
      details.textContent = [money, t.how].filter(Boolean).join(" · ");
      button.type = "button";
      button.className = "todo-complete";
      button.setAttribute("aria-pressed", String(completed));
      button.textContent = completed ? "아직 안 했어요" : "다 했어요";
      if (completed) li.classList.add("completed");
      button.addEventListener("click", () => {
        const isCompleted = li.classList.toggle("completed");
        button.setAttribute("aria-pressed", String(isCompleted));
        button.textContent = isCompleted ? "아직 안 했어요" : "다 했어요";
        if (isCompleted) completedTodos.add(key);
        else completedTodos.delete(key);
        saveCompletedTodos();
      });
      li.append(title, dueElement, details, button);
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

  $("shareResult").textContent = "";
  $("shareBtn").hidden = !!sharedId; // 손주 모드 화면에선 또 보내기 버튼을 안 띄운다
  $("result").hidden = false;
}
