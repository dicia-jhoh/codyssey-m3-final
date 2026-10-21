"""사진 → 글자·표시(Mark) 추출 — 담당: 황지영.

할 일
1. 비전 LLM 에 사진을 보내 schema.Mark 목록과 원문 글자를 JSON 으로 받는다(docs/03-AI-설계.md 「프롬프트」).
2. 금액·날짜는 LLM 값과 사진 속 숫자를 한 번 더 대조한다. 어긋나면 그 Mark 는 빼고 「직접 확인 필요」로 남긴다.
3. bbox 는 사진 크기 대비 비율(0~1)로 바꾼다 — 화면이 사진 크기와 상관없이 3색을 그리게 하려는 것.
"""

import base64
import json
import logging
import math
import re
from datetime import date

import httpx
from anthropic import Anthropic

from .schema import Mark

log = logging.getLogger(__name__)

_MODEL = "claude-sonnet-5-5"
# LLM_API_KEY 가 Google AI Studio 키("AIza…")면 Gemini 로 보낸다 — 서버 키가 Gemini 라서(10-21)
_GEMINI_MODEL = "gemini-flash-lite-latest"  # 무료 한도가 넉넉한 쪽
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_USER_PROMPT = "이 고지서 사진에서 항목을 뽑아 JSON으로만 답하라."

_SYSTEM_PROMPT = """\
너는 한국 고지서(납부고지서·가정통신문·주민센터 안내문 등) 사진을 읽는 비전 분석기다.
원본 위에 3색 표시를 긋기 위한 항목을 뽑아라:
- money: 내야 할 돈 (납부 금액)
- deadline: 지켜야 할 기한 (마감일, 신청 기간)
- document: 챙겨야 할 서류/준비물

반드시 아래 JSON 스키마만 출력한다. 설명 문장, 코드펜스, 다른 텍스트는 절대 포함하지 마라:

{
  "document_text": "<사진에서 읽은 본문 전체 텍스트>",
  "items": [
    {
      "kind": "money|deadline|document",
      "text": "<원문에 적힌 그대로의 값, 예: \\"48,200원\\">",
      "value": "<다루기 쉬운 값, 예: \\"48200\\", \\"2026-10-31\\">",
      "bbox": [x, y, w, h]
    }
  ]
}

bbox는 이미지 전체를 1x1로 봤을 때의 비율 좌표다 (x,y=좌상단, w,h=너비/높이, 모두 0~1).
표·도장·뒷면에 적힌 내용도 빠뜨리지 말고 찾아서 포함하라. 해당 종류의 항목이 없으면
items에서 그냥 생략한다(빈 값으로 억지로 채우지 않는다).
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class UnsupportedImageFormatError(ValueError):
    """_media_type()이 처리 못 하는 형식(지금은 HEIC/HEIF)."""


# HEIC/HEIF(ISO 기반 미디어 파일) 브랜드 코드 — ftyp 박스 뒤에 온다.
_HEIC_BRANDS = (b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"hevm", b"hevs", b"mif1", b"msf1")


def _media_type(image: bytes) -> str:
    """파일 앞부분 바이트로 이미지 형식을 판별한다 — 폰 스크린샷은 PNG·WebP도 흔하다.

    HEIC/HEIF(아이폰 카메라 기본 형식)는 Claude 비전 API가 못 받는다. 예전엔 여기서
    인식 못 하는 형식을 전부 기본값 image/jpeg로 둔갑시켰다 — HEIC 사진이 "JPEG"로
    속아서 전송되고, API가 거부하면 extract()의 광범위한 except가 그 이유를 삼켜서
    실패 원인이 아예 안 보였다(아이폰이 주 사용 기기인 이 서비스의 핵심 입력 경로인데도).
    지금은 HEIC를 명시적으로 걸러내 분명한 에러로 남긴다 — HEIC 변환 자체는 아직
    구현 안 함(업로드 단계에서 변환하는 건 별도 작업, README 「추출 모듈 상세」
    「알려진 한계」 참고).
    """
    if image.startswith(b"\x89PNG"):
        return "image/png"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    if image.startswith(b"GIF8"):
        return "image/gif"
    if image[4:8] == b"ftyp" and image[8:12] in _HEIC_BRANDS:
        raise UnsupportedImageFormatError(
            "HEIC/HEIF 사진은 아직 지원하지 않음 — 업로드 전 JPEG/PNG로 변환 필요"
        )
    return "image/jpeg"


def _call_vision(image: bytes, api_key: str) -> dict:
    """비전 LLM 에 사진을 보내 (document_text, items) 원시 JSON을 받는다.

    키 모양으로 고른다: "AIza…" = Gemini, 그 밖 = Claude.
    """
    if api_key.startswith("AIza"):
        return _call_gemini(image, api_key)
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": _media_type(image),
                            "data": base64.b64encode(image).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": _USER_PROMPT},
                ],
            }
        ],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_json(text)


def _call_gemini(image: bytes, api_key: str) -> dict:
    """Gemini generateContent 로 같은 프롬프트·스키마를 보낸다.

    키는 URL 이 아니라 헤더에 싣는다 — 실패하면 extract() 가 예외를 로그에 남기는데,
    httpx 오류 문구에는 URL 이 들어가서 ?key= 로 보내면 키가 로그에 찍힌다.
    """
    response = httpx.post(
        _GEMINI_URL.format(model=_GEMINI_MODEL),
        headers={"x-goog-api-key": api_key},
        json={
            "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": _media_type(image),
                                "data": base64.b64encode(image).decode("ascii"),
                            }
                        },
                        {"text": _USER_PROMPT},
                    ],
                }
            ],
            "generationConfig": {"responseMimeType": "application/json"},
        },
        timeout=90,
    )
    response.raise_for_status()
    parts = response.json()["candidates"][0]["content"]["parts"]
    return _parse_json("".join(part.get("text", "") for part in parts))


def _parse_json(text: str) -> dict:
    """```json ... ``` 코드펜스가 섞여 와도 흡수해서 파싱한다 (API 응답은 모델 출력이라 흔들림)."""
    stripped = text.strip()
    fence_match = _FENCE_RE.search(stripped)
    payload = fence_match.group(1) if fence_match else stripped
    return json.loads(payload)


_AMOUNT_RE = re.compile(r"([\d][\d,]*)\s*원")
# "2026.10.31" · "2026. 10. 31." · "2026년 10월 31일" — 공문은 점 뒤에 한 칸씩 띄우는 표기가 흔하다
_DATE_RE_FULL = re.compile(r"(?<!\d)(\d{4})\s*(?:[.\-/]|년)\s*(\d{1,2})\s*(?:[.\-/]|월)\s*(\d{1,2})")
_DATE_RE_MD = re.compile(r"(\d{1,2})월\s*(\d{1,2})일")  # "10월 31일" — 연도를 안 적는 공문이 흔함


def _parse_amount_won(text: str) -> int | None:
    m = _AMOUNT_RE.search(text)
    return int(m.group(1).replace(",", "")) if m else None


def _to_iso(y: int, mo: int, d: int) -> str | None:
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None  # 13월·32일처럼 달력에 없는 값 — 모델이 잘못 읽은 것으로 보고 버린다


def _dates(text: str, *, fallback_year: int):
    """본문의 날짜를 "YYYY.MM.DD" 형식부터, 다음 "MM월 DD일" 형식 순서로 ISO 로 낸다(달력에 없으면 None)."""
    for y, mo, d in _DATE_RE_FULL.findall(text):
        yield _to_iso(int(y), int(mo), int(d))
    # 연도가 있는 날짜는 지우고 찾는다 — 안 지우면 "2027년 1월 15일" 의 "1월 15일" 에 올해가 붙는다
    for mo, d in _DATE_RE_MD.findall(_DATE_RE_FULL.sub(" ", text)):
        yield _to_iso(fallback_year, int(mo), int(d))


def _parse_date_iso(text: str, *, fallback_year: int) -> str | None:
    return next(_dates(text, fallback_year=fallback_year), None)


def _document_dates(document_text: str, *, fallback_year: int) -> set[str]:
    """본문에 실제로 등장하는 날짜를 두 형식 다 모아 ISO로 정규화."""
    return {iso for iso in _dates(document_text, fallback_year=fallback_year) if iso}


def _is_bbox(bbox: object) -> bool:
    """[x, y, w, h] 숫자 4개인지 — 아니면 화면에 그릴 수 없다."""
    return (
        isinstance(bbox, list)
        and len(bbox) == 4
        and all(
            isinstance(x, int | float) and not isinstance(x, bool) and math.isfinite(x)
            for x in bbox
        )
    )


def _double_check(document_text: str, items: list[dict], *, fallback_year: int | None = None) -> list[Mark]:
    """money/deadline 항목을 document_text 본문과 교차 대조한다.

    고지서의 금액·기한은 놓치면 손해로 이어지는 민감 필드라, LLM이 함께 돌려준
    document_text에도 같은 값이 실제로 등장하는지 다시 확인한다. 어긋나면 그
    Mark는 만들지 않고 빼서 「직접 확인 필요」 상태(화면에 색이 안 칠해짐)로 남긴다.

    fallback_year: "10월 31일"처럼 연도가 없는 날짜를 만났을 때 쓸 연도(기본값: 올해).
    """
    fallback_year = fallback_year or date.today().year
    doc_amounts = {int(m.group(1).replace(",", "")) for m in _AMOUNT_RE.finditer(document_text)}
    doc_dates = _document_dates(document_text, fallback_year=fallback_year)

    marks: list[Mark] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        text = item.get("text")
        value = str(item.get("value") or "")
        bbox = item.get("bbox")
        if kind not in ("money", "deadline", "document") or not isinstance(text, str) or not text:
            continue  # 모양이 안 맞는 항목은 버린다 — 모델 출력은 신뢰 못 함
        if not _is_bbox(bbox):
            continue

        if kind == "money":
            amount = _parse_amount_won(value) or _parse_amount_won(text)
            if amount is None or amount not in doc_amounts:
                continue
            value = str(amount)
        elif kind == "deadline":
            date_iso = _parse_date_iso(value, fallback_year=fallback_year) or _parse_date_iso(
                text, fallback_year=fallback_year
            )
            if date_iso is None or date_iso not in doc_dates:
                continue
            value = date_iso
        # document 종류는 금액·날짜가 아니므로 이중 확인 대상이 아니다

        marks.append(Mark(kind=kind, text=text, value=value, bbox=[float(x) for x in bbox]))

    return marks


def extract(image: bytes, api_key: str) -> tuple[str, list[Mark]]:
    """(원문 글자, 표시 목록) 을 돌려준다.

    비전 LLM 호출이나 응답 파싱이 실패하면 빈 결과를 낸다 — agent.py가 이를
    보고 샘플 모드로 끝까지 돈다(docs/03-AI-설계.md 「실패했을 때」).
    """
    try:
        raw = _call_vision(image, api_key)
    except Exception:
        log.exception("비전 추출 실패 — 샘플 모드로 넘어감")
        return "", []

    # JSON 은 맞아도 모양이 다를 수 있다 — 여기서 예외가 나면 /decode 가 500 이 된다
    if not isinstance(raw, dict):
        log.warning("비전 응답이 객체가 아님(%s) — 샘플 모드로 넘어감", type(raw).__name__)
        return "", []
    document_text = raw.get("document_text")
    items = raw.get("items")
    if not isinstance(document_text, str) or not document_text:
        return "", []
    if not isinstance(items, list):
        items = []

    return document_text, _double_check(document_text, items)


def _main(argv: list[str] | None = None) -> int:
    """실제 비전 LLM으로 고지서 사진 한 장을 돌려보는 수동 검증 도구.

    사용: cd backend && LLM_API_KEY=... python -m app.extract <사진경로>
    agent.py를 거치지 않고 extract()만 바로 호출하므로, 키가 맞게 동작하는지
    빠르게 확인하고 싶을 때 쓴다 — 샘플 모드로 숨겨지지 않고 실패가 그대로 보인다.
    """
    import argparse
    import os
    from pathlib import Path

    parser = argparse.ArgumentParser(description=_main.__doc__)
    parser.add_argument("image", help="고지서 사진 경로")
    parser.add_argument(
        "--api-key", default=os.environ.get("LLM_API_KEY", ""), help="기본값: LLM_API_KEY 환경변수"
    )
    args = parser.parse_args(argv)

    if not args.api_key:
        print("[!] API 키 없음 — LLM_API_KEY 환경변수를 설정하거나 --api-key로 넘기세요")
        return 1

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"[!] 이미지 없음: {image_path}")
        return 1

    text, marks = extract(image_path.read_bytes(), args.api_key)
    if not text:
        print("[!] 추출 실패 — 호출/파싱 문제로 보임 (agent.py라면 여기서 샘플 모드로 넘어감)")
        return 1

    print(f"[✓] 원문 ({len(text)}자):\n{text}\n")
    print(f"[✓] Mark {len(marks)}건:")
    for mark in marks:
        print(f"  ({mark.kind}) {mark.text} → {mark.value}  bbox={mark.bbox}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
