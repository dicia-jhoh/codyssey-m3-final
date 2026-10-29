// 담당: 송유영. 사진 → POST /decode → 3색 표시 · 할 일 카드 · 근거
// 백엔드가 화면을 같이 내준다(/app/) — API 는 같은 주소다

const $ = (id) => document.getElementById(id);
const MAX_PHOTO_DIMENSION = 2000;

async function prepareUploadPhoto(file) {
  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
    const longestSide = Math.max(bitmap.width, bitmap.height);
    if (longestSide <= MAX_PHOTO_DIMENSION) return file;

    const scale = MAX_PHOTO_DIMENSION / longestSide;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const jpeg = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    return jpeg ? new File([jpeg], "photo.jpg", { type: "image/jpeg", lastModified: file.lastModified }) : file;
  } catch {
    return file;
  } finally {
    bitmap?.close();
  }
}

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
    if (!Array.isArray(saved)) return new Set();

    const cutoff = new Date();
    cutoff.setHours(0, 0, 0, 0);
    cutoff.setDate(cutoff.getDate() - 30);
    const validKeys = saved.filter((key) => {
      if (typeof key !== "string") return false;
      let parts;
      try {
        parts = JSON.parse(key);
      } catch {
        return false;
      }
      if (
        !Array.isArray(parts) ||
        parts.length !== 4 ||
        typeof parts[0] !== "string" ||
        typeof parts[1] !== "string" ||
        typeof parts[2] !== "string" ||
        (parts[3] !== null && !Number.isInteger(parts[3]))
      ) return false;

      if (parts[2]) {
        const dueDate = new Date(`${parts[2]}T00:00:00`);
        if (Number.isFinite(dueDate.getTime()) && dueDate < cutoff) return false;
      }
      return true;
    });
    try {
      localStorage.setItem("completedTodos", JSON.stringify(validKeys));
    } catch {}
    return new Set(validKeys);
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

const photoInput = $("photo");
photoInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || photoInput.disabled) return;
  photoInput.disabled = true;
  $("upload-section").classList.add("is-loading");
  const previousPreviewUrl = previewUrl;
  previewUrl = URL.createObjectURL(file);
  $("preview").src = previewUrl;
  if (previousPreviewUrl) URL.revokeObjectURL(previousPreviewUrl);
  $("result").hidden = true;
  const startedAt = Date.now();
  const updateProgress = () => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    const waiting = seconds > 10 ? " · 조금만 더 기다려 주세요" : "";
    $("status").textContent = `고지서를 읽고 있어요… ${seconds}초${waiting}`;
  };
  updateProgress();
  const progressTimer = setInterval(updateProgress, 1000);

  const form = new FormData();
  const uploadFile = await prepareUploadPhoto(file);
  form.append("file", uploadFile, uploadFile.name || file.name);
  try {
    const r = await fetch("/decode", { method: "POST", body: form });
    if (!r.ok) {
      const body = await r.json().catch(() => ({}));
      const retryAfter = r.headers.get("Retry-After");
      if (r.status === 429 && retryAfter && /^\d+$/.test(retryAfter)) {
        $("status").textContent = `${retryAfter}초 뒤에 다시 올려 주세요`;
        return;
      }
      // 4xx detail 은 서버가 사용자에게 하는 말(크기·형식) — 다시 찍어도 안 되니 그대로 보여 준다
      if (r.status < 500 && typeof body.detail === "string") {
        $("status").textContent = body.detail;
        return;
      }
      throw new Error(String(r.status));
    }
    show(await r.json());
    $("status").textContent = "";
    // 결과가 사진 아래라 폰에선 화면 밖일 수 있다 — 결과 제목이 보이게 내려 준다
    $("result").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    console.error(err);
    $("status").textContent = "사진을 읽지 못했어요. 밝은 곳에서 다시 찍어 올려 주세요.";
  } finally {
    clearInterval(progressTimer);
    photoInput.disabled = false;
    $("upload-section").classList.remove("is-loading");
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

function emptyListItem(message) {
  const item = document.createElement("li");
  item.textContent = message;
  return item;
}

function show(d) {
  currentDecoded = d;
  $("sample").hidden = !d.sample;
  $("aiNotice").textContent = d.ai_notice;
  $("title").textContent = d.title;

  // bbox = [x, y, w, h] 사진 대비 비율 → 퍼센트 위치
  $("marks").replaceChildren(
    ...d.marks.map((m) => {
      const box = document.createElement("button");
      const kindLabel = { money: "낼 돈", deadline: "기한", document: "챙길 서류" }[m.kind] || "고지서 글";
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
        // 한 번에 하나만 — 열려 있던 다른 표시의 글자는 접는다(겹치면 읽기 어렵다)
        for (const other of $("marks").querySelectorAll('.mark[aria-expanded="true"]')) {
          if (other === box) continue;
          other.setAttribute("aria-expanded", "false");
          other.querySelector(".mark-text").hidden = true;
        }
        box.setAttribute("aria-expanded", String(!expanded));
        text.hidden = expanded;
      });
      return box;
    })
  );

  let today = new Date();
  const requestedToday = d.sample ? new URLSearchParams(location.search).get("today") : null;
  const dateParts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(requestedToday || "");
  if (dateParts) {
    const [year, month, day] = dateParts.slice(1).map(Number);
    const override = new Date(year, month - 1, day);
    if (
      override.getFullYear() === year &&
      override.getMonth() === month - 1 &&
      override.getDate() === day
    ) today = override;
  }
  today.setHours(0, 0, 0, 0);
  // 기한이 가까운 할 일부터 — 기한이 없거나 이상한 날짜는 맨 뒤, 같으면 원래 순서
  const dueTime = (t) => {
    const time = t.due ? new Date(`${t.due}T00:00:00`).getTime() : NaN;
    return Number.isFinite(time) ? time : Infinity;
  };
  const sortedTodos = [...d.todos].sort((a, b) => {
    const [x, y] = [dueTime(a), dueTime(b)];
    return x === y ? 0 : x < y ? -1 : 1;
  });
  const todoItems = sortedTodos.length
    ? sortedTodos.map((t) => {
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
      const key = JSON.stringify([d.title, t.title, t.due || "", t.amount ?? null]);
      const completed = completedTodos.has(key);
      title.textContent = t.title;
      dueElement.className = "due";
      dueElement.textContent = due;
      if (daysRemaining < 0) dueElement.classList.add("overdue");
      // 오늘~3일 남은 할 일은 눈에 띄게 — 기한 없는 할 일(null)은 빼고
      else if (daysRemaining !== null && daysRemaining <= 3) dueElement.classList.add("soon");
      details.className = "details";
      // 금액·방법이 둘 다 없으면 빈 줄, 하나만 있으면 앞에 「 · 」 없이
      details.textContent = [money, t.how].filter(Boolean).join(" · ");
      button.type = "button";
      button.className = "todo-complete";
      button.textContent = completed ? "아직 안 했어요" : "다 했어요";
      if (completed) li.classList.add("completed");
      button.addEventListener("click", () => {
        const isCompleted = li.classList.toggle("completed");
        button.textContent = isCompleted ? "아직 안 했어요" : "다 했어요";
        if (isCompleted) completedTodos.add(key);
        else completedTodos.delete(key);
        saveCompletedTodos();
      });
      li.append(title, dueElement, details, button);
      return li;
    })
    : [emptyListItem("해야 할 일은 찾지 못했어요. 받은 고지서를 함께 확인해 주세요.")];
  $("todos").replaceChildren(...todoItems);

  const basisItems = d.basis.length
    ? d.basis.map((b) => {
      const li = document.createElement("li");
      li.textContent = b.claim;
      const q = document.createElement("blockquote");
      q.textContent = `고지서에 적힌 말: ${b.quote}${b.law ? ` (${b.law})` : ""}`;
      li.append(q);
      return li;
    })
    : [emptyListItem("이 고지서에서 관련 법 조항은 찾지 못했어요.")];
  $("basis").replaceChildren(...basisItems);

  $("shareResult").textContent = "";
  $("shareBtn").hidden = !!sharedId; // 손주 모드 화면에선 또 보내기 버튼을 안 띄운다
  $("result").hidden = false;
}
