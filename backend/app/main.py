"""FastAPI 서버 — 담당: 이정관. 실행: uvicorn app.main:app --reload (backend/ 에서)."""

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .agent import decode
from .schema import Decoded

MAX_BYTES = 10 * 1024 * 1024  # 휴대폰 사진 한 장이면 충분하다
ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"  # 서비스 화면(송유영)

app = FastAPI(title="또박또박 API", description="공문 사진 → 할 일·근거")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOW_ORIGINS", "http://localhost:5500").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


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
