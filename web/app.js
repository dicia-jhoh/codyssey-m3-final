// 담당: 송유영. 사진 → POST /decode → 3색 표시 · 할 일 카드 · 근거
// 백엔드가 화면을 같이 내준다(/app/) — API 는 같은 주소다

const $ = (id) => document.getElementById(id);

const MAX_PHOTO_DIMENSION = 2000; // 긴 변이 이보다 크면 줄여 보낸다 — 업로드 시간이 준다
const JPEG_QUALITY = 0.85;
const SLOW_SECONDS = 10; // 이보다 오래 걸리면 「조금만 더」를 붙인다
const SOON_DAYS = 3; // 오늘~사흘 남은 할 일은 눈에 띄게
const DONE_KEEP_DAYS = 30; // 기한이 이만큼 지난 「다 했어요」 기록은 지운다
const DAY_MS = 24 * 60 * 60 * 1000;
const SYNC_SECONDS = 20; // 공유한 카드의 「다 했어요」를 이 간격으로 다시 읽는다
const PEN_NAME = { money: "낼 돈", deadline: "기한", document: "챙길 서류" };

let currentDecoded = null; // 「가족에게 보내기」가 보낼 최근 해독 결과
let previewUrl = null;
const sharedId = new URLSearchParams(location.search).get("share");

// ── 브라우저 저장소 — 사생활 모드에선 막혀 있을 수 있어 실패해도 화면은 돈다 ──

function readStored(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function store(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {}
}

// "2026-10-31" → 그 날 0시(현지). 날짜가 아니면 null
function parseLocalDate(iso) {
  const date = iso ? new Date(`${iso}T00:00:00`) : null;
  return date && Number.isFinite(date.getTime()) ? date : null;
}

// ── 글자 크게 ──

let largeText = readStored("largeText") === "true";

function updateTextSize() {
  document.documentElement.classList.toggle("large-text", largeText);
  $("textSizeBtn").setAttribute("aria-pressed", String(largeText));
  $("textSizeBtn").textContent = largeText ? "기본 글자" : "글자 크게";
}

updateTextSize();
$("textSizeBtn").addEventListener("click", () => {
  largeText = !largeText;
  updateTextSize();
  store("largeText", String(largeText));
});

// ── 「다 했어요」 기록 — 키 = [문서 제목, 할 일 제목, 기한, 금액] ──

const COMPLETED_KEY = "completedTodos";
const completedTodos = loadCompletedTodos();

function loadCompletedTodos() {
  let saved;
  try {
    saved = JSON.parse(readStored(COMPLETED_KEY) || "[]");
  } catch {
    return new Set();
  }
  if (!Array.isArray(saved)) return new Set();
  const cutoff = new Date();
  cutoff.setHours(0, 0, 0, 0);
  cutoff.setDate(cutoff.getDate() - DONE_KEEP_DAYS);
  const kept = saved.filter((key) => isKeptTodoKey(key, cutoff));
  store(COMPLETED_KEY, JSON.stringify(kept));
  return new Set(kept);
}

function isKeptTodoKey(key, cutoff) {
  if (typeof key !== "string") return false;
  let parts;
  try {
    parts = JSON.parse(key);
  } catch {
    return false;
  }
  if (!Array.isArray(parts) || parts.length !== 4) return false;
  const [docTitle, todoTitle, due, amount] = parts;
  const wellFormed =
    typeof docTitle === "string" &&
    typeof todoTitle === "string" &&
    typeof due === "string" &&
    (amount === null || Number.isInteger(amount));
  if (!wellFormed) return false;
  const dueDate = parseLocalDate(due);
  return !(dueDate && dueDate < cutoff);
}

function saveCompletedTodos() {
  store(COMPLETED_KEY, JSON.stringify([...completedTodos]));
}

// ── 가족과 함께 보는 「다 했어요」 — 공유한 카드는 서버의 기록을 같이 쓴다 ──
// 어르신이 누르면 서버에 적고, 같은 링크를 연 자녀 화면은 SYNC_SECONDS 마다 읽어 완료로 바꾼다.

const SHARE_LINKS_KEY = "shareLinks"; // {문서 제목: 공유 id} — 내가 보낸 링크

function readShareLinks() {
  try {
    return JSON.parse(readStored(SHARE_LINKS_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function rememberShareLink(decoded, id) {
  const links = readShareLinks();
  links[decoded.title] = id;
  store(SHARE_LINKS_KEY, JSON.stringify(links));
}

function linkedShareId(decoded) {
  return sharedId || readShareLinks()[decoded.title] || null;
}

function doneUrl(id) {
  return `/share/${encodeURIComponent(id)}/done`;
}

async function sendDone(decoded, key, done) {
  const id = linkedShareId(decoded);
  if (!id) return;
  try {
    await fetch(doneUrl(id), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, done }),
    });
  } catch (err) {
    console.error(err); // 내 화면 기록은 이미 남았다 — 다음에 누를 때 다시 보낸다
  }
}

// 서버 기록을 내 기록에 맞춘다. 바뀐 것이 있으면 true
async function pullDone(decoded) {
  const id = linkedShareId(decoded);
  if (!id) return false;
  const response = await fetch(doneUrl(id));
  if (!response.ok) return false;
  const remote = new Set((await response.json()).done);
  let changed = false;
  for (const todo of decoded.todos) {
    const key = todoKey(decoded, todo);
    if (remote.has(key) === completedTodos.has(key)) continue;
    if (remote.has(key)) completedTodos.add(key);
    else completedTodos.delete(key);
    changed = true;
  }
  if (changed) saveCompletedTodos();
  return changed;
}

async function refreshDone() {
  if (!currentDecoded || document.hidden) return;
  try {
    if (await pullDone(currentDecoded)) renderTodos(currentDecoded);
  } catch (err) {
    console.error(err);
  }
}

setInterval(refreshDone, SYNC_SECONDS * 1000);

// ── 손주 모드: ?share=<id> 로 열리면 사진 올리기 없이 저장된 해독 결과를 보여 준다 ──
// 원본 사진은 공유 저장소에 아예 없다(share.py) — 그래서 3색 사진 없이 할 일·근거만 보인다.

if (sharedId) openShared(sharedId);

async function openShared(id) {
  $("upload-section").hidden = true;
  $("photoSection").hidden = true;
  $("status").textContent = "불러오는 중…";
  try {
    const response = await fetch(`/share/${encodeURIComponent(id)}`);
    if (!response.ok) throw new Error(String(response.status));
    const decoded = await response.json();
    await pullDone(decoded).catch(console.error);
    $("grandchildNotice").hidden = false;
    show(decoded);
    $("status").textContent = "";
  } catch (err) {
    console.error(err);
    $("status").textContent =
      err.message === "404"
        ? "링크 기한이 지났어요. 가족에게 새 링크를 받아 주세요."
        : "지금은 열 수 없어요. 잠시 뒤 다시 열어 주세요.";
  }
}

// ── 사진 올리기 ──

const photoInput = $("photo");
photoInput.addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file || photoInput.disabled) return;
  photoInput.disabled = true;
  $("upload-section").classList.add("is-loading");
  showPreview(file);
  $("result").hidden = true;
  const stopProgress = startProgress();
  try {
    const message = await uploadPhoto(file);
    $("status").textContent = message;
    if (!message) $("result").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    console.error(err);
    $("status").textContent = "사진을 읽지 못했어요. 밝은 곳에서 다시 찍어 올려 주세요.";
  } finally {
    stopProgress();
    photoInput.disabled = false;
    $("upload-section").classList.remove("is-loading");
    event.target.value = "";
  }
});

function showPreview(file) {
  const previous = previewUrl;
  previewUrl = URL.createObjectURL(file);
  $("preview").src = previewUrl;
  if (previous) URL.revokeObjectURL(previous);
}

function startProgress() {
  const startedAt = Date.now();
  const update = () => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    const waiting = seconds > SLOW_SECONDS ? " · 조금만 더 기다려 주세요" : "";
    $("status").textContent = `고지서를 읽고 있어요… ${seconds}초${waiting}`;
  };
  update();
  const timer = setInterval(update, 1000);
  return () => clearInterval(timer);
}

// 해독해 화면에 그린다. 사람에게 보일 안내가 있으면 그 글을, 다 됐으면 "" 를 돌려준다
async function uploadPhoto(file) {
  const photo = await shrinkPhoto(file);
  const form = new FormData();
  form.append("file", photo, photo.name || file.name);
  const response = await fetch("/decode", { method: "POST", body: form });
  if (response.ok) {
    const decoded = await response.json();
    await pullDone(decoded).catch(console.error); // 전에 보낸 고지서면 가족이 누른 것도 보인다
    show(decoded);
    return "";
  }
  const body = await response.json().catch(() => ({}));
  const retryAfter = response.headers.get("Retry-After");
  if (response.status === 429 && /^\d+$/.test(retryAfter || "")) {
    return `${retryAfter}초 뒤에 다시 올려 주세요`;
  }
  // 4xx detail 은 서버가 사람에게 하는 말(크기·형식) — 다시 찍어도 안 되니 그대로 보여 준다
  if (response.status < 500 && typeof body.detail === "string") return body.detail;
  throw new Error(String(response.status));
}

async function shrinkPhoto(file) {
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
    const jpeg = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
    if (!jpeg) return file;
    return new File([jpeg], "photo.jpg", { type: "image/jpeg", lastModified: file.lastModified });
  } catch {
    return file; // 브라우저가 못 줄이는 형식이면 원본을 보낸다 — 서버가 크기를 다시 본다
  } finally {
    bitmap?.close();
  }
}

// ── 가족에게 보내기 ──

$("shareBtn").addEventListener("click", async () => {
  if (!currentDecoded) return;
  $("shareResult").textContent = "링크 만드는 중…";
  try {
    const response = await fetch("/share", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentDecoded),
    });
    if (!response.ok) throw new Error(String(response.status));
    const { share_id, expires_at } = await response.json();
    await linkShare(currentDecoded, share_id);
    await handOver(`${location.origin}${location.pathname}?share=${share_id}`, openUntil(expires_at));
  } catch (err) {
    console.error(err);
    $("shareResult").textContent = "링크를 만들지 못했어요. 잠시 뒤 다시 눌러 주세요.";
  }
});

// 이 고지서를 링크에 묶고, 이미 누른 「다 했어요」도 가족 화면에 보낸다
async function linkShare(decoded, id) {
  rememberShareLink(decoded, id);
  const done = decoded.todos.map((todo) => todoKey(decoded, todo)).filter((key) => completedTodos.has(key));
  await Promise.all(done.map((key) => sendDone(decoded, key, true)));
}

// 서버가 준 만료 시각(UTC ISO) → 「11월 30일까지 열려요」
function openUntil(expiresAt) {
  const until = expiresAt ? new Date(expiresAt) : null;
  if (!until || !Number.isFinite(until.getTime())) return "";
  return ` 링크는 ${until.getMonth() + 1}월 ${until.getDate()}일까지 열려요.`;
}

// 공유 창 → 클립보드 → 직접 복사할 칸 순서로 링크를 건넨다
async function handOver(link, untilNote) {
  if (navigator.share) {
    try {
      await navigator.share({ title: "또박또박 해독 결과", text: "가족과 함께 확인해 주세요.", url: link });
      $("shareResult").textContent = `공유 창을 열었어요.${untilNote}`;
      return;
    } catch (err) {
      if (err.name === "AbortError") {
        $("shareResult").textContent = "공유를 취소했어요.";
        return;
      }
      // 공유 창을 못 연 다른 오류는 클립보드로 넘어간다
    }
  }
  try {
    await navigator.clipboard.writeText(link);
    $("shareResult").textContent = `링크를 복사했어요. 가족에게 붙여넣어 보내세요.${untilNote}`;
    return;
  } catch {
    // http 주소에선 클립보드가 막혀 있다 — 직접 복사할 칸을 보여 준다
  }
  showCopyableLink(link, untilNote);
}

function showCopyableLink(link, untilNote) {
  const label = document.createElement("span");
  label.textContent = `링크를 복사해 가족에게 보내세요.${untilNote} `;
  const input = document.createElement("input");
  input.readOnly = true;
  input.value = link;
  input.setAttribute("aria-label", "가족에게 보낼 링크");
  input.onclick = () => input.select();
  $("shareResult").replaceChildren(label, input);
}

// ── 해독 결과 그리기 ──

function show(decoded) {
  currentDecoded = decoded;
  $("sample").hidden = !decoded.sample;
  $("aiNotice").textContent = decoded.ai_notice;
  $("title").textContent = decoded.title;
  $("marks").replaceChildren(...decoded.marks.map(markBox));
  renderTodos(decoded);
  renderAlerts(decoded.alerts || []);
  $("basis").replaceChildren(...basisItems(decoded.basis));
  showReply(decoded);
  $("shareResult").textContent = "";
  $("shareBtn").hidden = !!sharedId; // 손주 모드 화면에선 또 보내기 버튼을 안 띄운다
  $("result").hidden = false;
}

function renderTodos(decoded) {
  $("todos").replaceChildren(...todoItems(decoded, displayToday(decoded)));
}

// bbox = [x, y, w, h] 사진 대비 비율 → 퍼센트 위치. 누르면 그 글자가 펼쳐진다
function markBox(mark) {
  const box = document.createElement("button");
  box.className = `mark ${mark.kind}`;
  box.type = "button";
  box.setAttribute("aria-label", `${PEN_NAME[mark.kind] || "고지서 글"}: ${mark.text}`);
  box.setAttribute("aria-expanded", "false");
  const [left, top, width, height] = mark.bbox.map((v) => `${v * 100}%`);
  Object.assign(box.style, { left, top, width, height });
  const text = document.createElement("span");
  text.className = "mark-text";
  text.textContent = mark.text;
  text.hidden = true;
  box.append(text);
  box.addEventListener("click", () => toggleMark(box, text));
  return box;
}

// 한 번에 하나만 — 열려 있던 다른 표시의 글자는 접는다(겹치면 읽기 어렵다)
function toggleMark(box, text) {
  const expanded = box.getAttribute("aria-expanded") === "true";
  for (const other of $("marks").querySelectorAll('.mark[aria-expanded="true"]')) {
    if (other === box) continue;
    other.setAttribute("aria-expanded", "false");
    other.querySelector(".mark-text").hidden = true;
  }
  box.setAttribute("aria-expanded", String(!expanded));
  text.hidden = expanded;
}

// 오늘 날짜. 샘플 화면만 ?today=YYYY-MM-DD 로 바꿀 수 있다(시연·스크린샷용)
function displayToday(decoded) {
  const requested = decoded.sample ? new URLSearchParams(location.search).get("today") : null;
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(requested || "");
  let today = new Date();
  if (parts) {
    const [year, month, day] = parts.slice(1).map(Number);
    const override = new Date(year, month - 1, day);
    const real = override.getMonth() === month - 1 && override.getDate() === day;
    if (real) today = override;
  }
  today.setHours(0, 0, 0, 0);
  return today;
}

// 기한이 가까운 할 일부터 — 기한이 없거나 이상한 날짜는 맨 뒤, 같으면 원래 순서
function byDue(todos) {
  const dueTime = (todo) => parseLocalDate(todo.due)?.getTime() ?? Infinity;
  return [...todos].sort((a, b) => dueTime(a) - dueTime(b) || 0);
}

function todoItems(decoded, today) {
  if (!decoded.todos.length) {
    return [emptyListItem("해야 할 일은 찾지 못했어요. 받은 고지서를 함께 확인해 주세요.")];
  }
  return byDue(decoded.todos).map((todo) => todoItem(decoded, todo, today));
}

function todoItem(decoded, todo, today) {
  const dueDate = parseLocalDate(todo.due);
  const daysLeft = dueDate ? Math.round((dueDate - today) / DAY_MS) : null;
  const li = document.createElement("li");
  const title = document.createElement("strong");
  title.textContent = todo.title;
  const due = document.createElement("span");
  due.className = "due";
  due.textContent = dueText(todo.due, dueDate, daysLeft);
  if (daysLeft !== null && daysLeft < 0) due.classList.add("overdue");
  else if (daysLeft !== null && daysLeft <= SOON_DAYS) due.classList.add("soon");
  const details = document.createElement("span");
  details.className = "details";
  const money = todo.amount != null ? `${todo.amount.toLocaleString("ko-KR")}원` : "";
  details.textContent = [money, todo.how].filter(Boolean).join(" · ");
  li.append(title, due, details, doneButton(li, decoded, todoKey(decoded, todo)));
  return li;
}

function dueText(rawDue, dueDate, daysLeft) {
  if (!rawDue) return "기한 없음";
  if (!dueDate) return `${rawDue}까지`;
  const weekday = dueDate.toLocaleDateString("ko-KR", { weekday: "short" });
  const label = `${dueDate.getMonth() + 1}월 ${dueDate.getDate()}일(${weekday})`;
  if (daysLeft > 0) return `${label}까지 · ${daysLeft}일 남았어요`;
  if (daysLeft === 0) return "오늘까지예요";
  return `${label}까지였어요 · 기한이 지났어요`;
}

function todoKey(decoded, todo) {
  return JSON.stringify([decoded.title, todo.title, todo.due || "", todo.amount ?? null]);
}

function doneButton(li, decoded, key) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "todo-complete";
  const paint = (done) => {
    li.classList.toggle("completed", done);
    button.textContent = done ? "아직 안 했어요" : "다 했어요";
  };
  paint(completedTodos.has(key));
  button.addEventListener("click", () => {
    const done = !li.classList.contains("completed");
    paint(done);
    if (done) completedTodos.add(key);
    else completedTodos.delete(key);
    saveCompletedTodos();
    sendDone(decoded, key, done);
  });
  return button;
}

// 기한 사흘 전·당일 알림 — 카카오톡 말풍선 모양 미리보기(가상 발송, notify.py)
function renderAlerts(alerts) {
  $("alertSection").hidden = !alerts.length;
  $("alerts").replaceChildren(...alerts.map((alert) => {
    const li = document.createElement("li");
    const when = document.createElement("span");
    const sendOn = parseLocalDate(alert.send_on);
    when.className = "when";
    when.textContent = sendOn ? `${sendOn.getMonth() + 1}월 ${sendOn.getDate()}일 오전 9시 · ${alert.when}` : alert.when;
    const bubble = document.createElement("span");
    bubble.className = "bubble";
    bubble.textContent = alert.message;
    li.append(when, bubble);
    return li;
  }));
}

// 과태료 고지서의 의견 제출서 초안 — 의견 제출 기한 안에 내면 20%까지 줄어든다(시행령 제5조)
function showReply(decoded) {
  $("replySection").hidden = !decoded.reply_draft;
  $("replyDraft").textContent = decoded.reply_draft || "";
  $("replyNote").textContent =
    decoded.doc_type === "과태료"
      ? "의견 제출 기한 안에 스스로 내면 과태료를 20%까지 줄일 수 있어요. 사정이 있으면 아래 글을 고쳐 내세요."
      : "";
  $("replyResult").textContent = "";
}

$("copyReplyBtn").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("replyDraft").textContent);
    $("replyResult").textContent = "초안을 복사했어요. 빈칸을 채워 내세요.";
  } catch {
    // http 주소에선 클립보드가 막혀 있다 — 글을 골라 두면 길게 눌러 복사할 수 있다
    getSelection().selectAllChildren($("replyDraft"));
    $("replyResult").textContent = "글을 골라 두었어요. 길게 눌러 복사하세요.";
  }
});

function basisItems(basis) {
  if (!basis.length) return [emptyListItem("이 고지서에서 관련 법 조항은 찾지 못했어요.")];
  return basis.map((b) => {
    const li = document.createElement("li");
    li.textContent = b.claim;
    const quote = document.createElement("blockquote");
    quote.textContent = `법 조문 원문: ${b.quote}${b.law ? ` (${b.law})` : ""}`;
    li.append(quote);
    return li;
  });
}

function emptyListItem(message) {
  const item = document.createElement("li");
  item.textContent = message;
  return item;
}
