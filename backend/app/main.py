"""FastAPI 서버 — 담당: 이정관. 실행: uvicorn app.main:app --reload (backend/ 에서)."""

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .agent import decode
from .schema import Decoded

MAX_BYTES = 10 * 1024 * 1024  # 휴대폰 사진 한 장이면 충분하다
WEB_DIR = Path(__file__).resolve().parents[2] / "web"  # 서비스 화면(송유영)

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


# 화면도 같은 서버가 내준다 — 배포 주소 하나로 화면과 API 가 같이 열린다(CORS 불필요).
# 위의 API 경로가 먼저 잡히고, 나머지 경로만 web/ 로 간다.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
