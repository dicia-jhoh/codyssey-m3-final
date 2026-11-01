"""과태료 의견 제출 초안 — 담당: 오주현.

과태료를 미리 알리는 통지를 받으면 의견 제출 기한 안에 의견을 낼 수 있고(질서위반행위규제법
제16조), 그 기한 안에 스스로 내면 과태료를 20%까지 깎아 준다(제18조, 시행령 제5조).
어르신이 「무엇을 써서 내야 하나」에서 막히지 않게 보낼 글의 초안을 만든다.
"""

from __future__ import annotations

import logging

import httpx
from anthropic import Anthropic

from . import extract

log = logging.getLogger(__name__)

# 초안 옆에 붙이는 근거 — rag 에 적재된 조문이다(data/legal/articles.jsonl)
BASIS_ARTICLES = (
    ("질서위반행위규제법", "16"),
    ("질서위반행위규제법", "18"),
    ("질서위반행위규제법 시행령", "5"),
)
_MAX_TOKENS = 1024
_TIMEOUT_SECONDS = 60

_SYSTEM_PROMPT = """\
너는 과태료 사전통지서를 받은 어르신을 돕는다. 아래 고지서 글(개인정보는 이미 가렸다)을 보고
행정청에 낼 「의견 제출서」 초안을 쓴다.

- 고지서에 적힌 사실(위반 일시·장소·금액·의견 제출 기한·받는 기관)만 옮긴다.
- 없는 사실은 지어내지 않는다.
- 사정을 적을 자리는 「[여기에 사정을 적어 주세요]」처럼 대괄호 빈칸으로 둔다.
- 차례: 제목 / 받는 곳 / 위반 내용 / 의견 / 첨부 서류 / 날짜·이름 칸.
- 쉬운 말, 한 문장에 한 가지. 600자 이내. 초안 본문만 출력한다.
"""

TEMPLATE = """\
의견 제출서

받는 곳: [과태료를 알린 기관]

위반 내용: [고지서에 적힌 위반 일시·장소]
과태료: [고지서에 적힌 금액]

의견:
[여기에 사정을 적어 주세요. 예: 그날 그 자리에 있었던 이유]

첨부 서류: [사정을 보여 주는 자료가 있으면 적어 주세요]

제출일: [날짜]   이름: [이름]   연락처: [연락처]
"""


def draft_reply(text: str, api_key: str) -> str:
    """고지서 글로 의견 제출서 초안을 쓴다. LLM 이 실패하면 빈칸 양식(TEMPLATE)을 준다."""
    try:
        draft = _ask(text, api_key).strip()
    except Exception:
        log.exception("답장 초안 실패 — 빈칸 양식으로 넘어감")
        return TEMPLATE
    return draft or TEMPLATE


def _ask(text: str, api_key: str) -> str:
    """키 모양으로 고른 LLM 에 글만 보낸다 — extract 와 같은 규칙(Google 키 = Gemini)."""
    if api_key.startswith(extract._GEMINI_KEY_PREFIXES):
        response = httpx.post(
            extract._GEMINI_URL.format(model=extract._GEMINI_MODEL),
            headers={"x-goog-api-key": api_key},  # URL 에 키를 싣지 않는다(오류 로그에 남는다)
            json={
                "systemInstruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": text}]}],
            },
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        parts = response.json()["candidates"][0]["content"]["parts"]
        return "".join(part.get("text", "") for part in parts)
    message = Anthropic(api_key=api_key).messages.create(
        model=extract._MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
