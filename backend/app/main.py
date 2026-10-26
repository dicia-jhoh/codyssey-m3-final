"""FastAPI 서버 — 담당: 이정관. 실행: uvicorn app.main:app --reload (backend/ 에서)."""

import os
import subprocess
from collections import deque
from pathlib import Path
from time import monotonic

from fastapi import BackgroundTasks
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from .agent import decode
from .schema import Decoded
from .notify import notify_deadlines
from .share import create_share, get_share

MAX_BYTES = 10 * 1024 * 1024  # 휴대폰 사진 한 장이면 충분하다
MULTIPART_OVERHEAD = 64 * 1024  # multipart 경계·파일명 등 파일 외 메타데이터 여유
MAX_SHARE_BYTES = 64 * 1024  # 해독 결과 JSON 은 몇 KB — 이보다 크면 해독 결과가 아니다
DECODE_PER_MINUTE = max(1, int(os.environ.get("DECODE_PER_MINUTE", "10")))
_decode_requests: dict[str, deque[float]] = {}
ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"  # 서비스 화면(송유영)

def _read_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, check=True, timeout=2,
        )
        return result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


COMMIT = _read_commit()  # 서버 시작 때 한 번만 읽는다

app = FastAPI(title="또박또박 API", description="고지서 사진 → 할 일·근거")


class LimitDecodeUpload:
    """/decode 본문을 받으면서 센다 — 넘으면 그 자리에서 413.

    Content-Length 만 보면 그 헤더가 없는 청크 전송은 그대로 통과해, multipart 파서가
    끝없이 임시 파일에 받아 적는다(OCR 리뷰). 헤더가 크면 본문을 읽기 전에 거절하고,
    헤더가 없거나 거짓이면 받은 바이트를 세다가 넘는 순간 멈춘다.
    """

    LIMIT = MAX_BYTES + MULTIPART_OVERHEAD

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/decode":
            return await self.app(scope, receive, send)
        length = dict(scope["headers"]).get(b"content-length", b"")
        if length.isdigit() and int(length) > self.LIMIT:
            return await self._too_large(scope, receive, send)
        received = 0
        exceeded = False

        async def counted():
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.LIMIT:
                    exceeded = True
                    # 더 받지 않게 본문을 여기서 끝낸다 — 파서는 잘린 본문으로 실패한다
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        started = False

        async def guarded(message):
            nonlocal started
            if exceeded:
                return  # 파서가 낸 400 대신 아래에서 413 을 보낸다
            started = True
            await send(message)

        await self.app(scope, counted, guarded)
        if exceeded and not started:
            await self._too_large(scope, receive, send)

    @staticmethod
    async def _too_large(scope, receive, send):
        await JSONResponse({"detail": "사진이 너무 커요(10MB 이하)"}, status_code=413)(
            scope, receive, send
        )


app.add_middleware(LimitDecodeUpload)


@app.middleware("http")
async def limit_decode_requests(request, call_next):
    if request.method == "POST" and request.url.path == "/decode":
        now = monotonic()
        # 만료된 IP도 지워 새 주소가 계속 들어와도 기록이 쌓이지 않게 한다.
        for ip, times in list(_decode_requests.items()):
            while times and times[0] <= now - 60:
                times.popleft()
            if not times:
                del _decode_requests[ip]
        ip = request.client.host if request.client else "unknown"
        times = _decode_requests.setdefault(ip, deque())
        if len(times) >= DECODE_PER_MINUTE:
            return JSONResponse({"detail": "잠시 뒤 다시 올려 주세요"}, status_code=429)
        # await 전에 기록하므로 같은 이벤트 루프의 동시 요청도 한도를 공유한다.
        times.append(now)
    return await call_next(request)


@app.middleware("http")
async def revalidate_pages(request, call_next):
    # 글·코드가 바뀌면 바로 보이게 — 브라우저가 옛 site.js 를 캐시에서 꺼내 「이름 없는 서비스」를 보인 적이 있다.
    # no-cache 는 「저장은 하되 쓰기 전에 서버에 물어본다」라 바뀌지 않았으면 304 로 가볍게 끝난다.
    response = await call_next(request)
    path = request.url.path
    if path.endswith(("/", ".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/health")
def health() -> dict:
    return {"ok": True, "sample_mode": not os.environ.get("LLM_API_KEY"), "commit": COMMIT}


@app.post("/decode", response_model=Decoded)
async def decode_photo(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> Decoded:
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "사진 파일만 올릴 수 있어요")
    image = await file.read(MAX_BYTES + 1)
    if len(image) > MAX_BYTES:
        raise HTTPException(413, "사진이 너무 커요(10MB 이하)")
    if not image:
        raise HTTPException(400, "빈 사진 파일이에요")
    # 사진은 메모리에서만 쓰고 저장하지 않는다(AI 윤리 — 동의 없이 보관 금지)
    decoded = await run_in_threadpool(decode, image)
    background_tasks.add_task(notify_deadlines, decoded)
    return decoded


@app.post("/share")
def share_decoded(decoded: Decoded) -> dict:
    """해독 결과를 짧은 링크로 공유한다(FR-07 손주 모드). 사진은 안 보내고 안 받는다."""
    # 인증 없는 공개 주소라 크기를 안 막으면 아무나 큰 JSON 으로 서버 메모리를 채운다
    if len(decoded.model_dump_json().encode()) > MAX_SHARE_BYTES:
        raise HTTPException(413, "공유할 내용이 너무 커요")
    return {"share_id": create_share(decoded)}


@app.get("/share/{share_id}", response_model=Decoded)
def get_shared_decoded(share_id: str) -> Decoded:
    shared = get_share(share_id)
    if shared is None:
        raise HTTPException(404, "링크가 만료됐거나 없는 공유예요")
    return shared


# 포트 하나(M3 = 8037)로 팀 홈페이지·서비스 화면·API 를 같이 낸다(CORS 불필요).
#   /       팀 홈페이지(index.html)     /app/   서비스 화면(web/)     /health · /decode   API
# 홈페이지는 필요한 폴더만 연다 — 저장소 루트를 통째로 열면 backend/.env 같은 비밀이 새어 나간다.
app.mount("/app", StaticFiles(directory=WEB_DIR, html=True), name="web")
for _dir in ("assets", "content", "docs/plan"):
    app.mount(f"/{_dir}", StaticFiles(directory=ROOT / _dir), name=_dir.replace("/", "-"))


@app.get("/", include_in_schema=False)
def homepage() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/app", include_in_schema=False)
def app_slash() -> RedirectResponse:
    return RedirectResponse("/app/")
