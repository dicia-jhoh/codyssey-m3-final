"""FastAPI 서버 — 담당: 이정관. 실행: uvicorn app.main:app --reload (backend/ 에서)."""

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .agent import decode
from .schema import Decoded
from .share import create_share, get_share

MAX_BYTES = 10 * 1024 * 1024  # 휴대폰 사진 한 장이면 충분하다
ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"  # 서비스 화면(송유영)

app = FastAPI(title="또박또박 API", description="고지서 사진 → 할 일·근거")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOW_ORIGINS", "http://localhost:5500").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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
    return {"ok": True, "sample_mode": not os.environ.get("LLM_API_KEY")}


@app.post("/decode", response_model=Decoded)
async def decode_photo(file: UploadFile = File(...)) -> Decoded:
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "사진 파일만 올릴 수 있어요")
    image = await file.read()
    if len(image) > MAX_BYTES:
        raise HTTPException(413, "사진이 너무 커요(10MB 이하)")
    # 사진은 메모리에서만 쓰고 저장하지 않는다(AI 윤리 — 동의 없이 보관 금지)
    return decode(image)


@app.post("/share")
def share_decoded(decoded: Decoded) -> dict:
    """해독 결과를 짧은 링크로 공유한다(FR-07 손주 모드). 사진은 안 보내고 안 받는다."""
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
