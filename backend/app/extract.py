"""사진 → 글자·표시(Mark) 추출 — 담당: 황지영.

할 일
1. 비전 LLM 에 사진을 보내 schema.Mark 목록과 원문 글자를 JSON 으로 받는다(docs/03-AI-설계.md 「프롬프트」).
2. 금액·날짜는 LLM 값과 사진 속 숫자를 한 번 더 대조한다. 어긋나면 그 Mark 는 빼고 「직접 확인 필요」로 남긴다.
3. bbox 는 사진 크기 대비 비율(0~1)로 바꾼다 — 화면이 사진 크기와 상관없이 3색을 그리게 하려는 것.
"""

import base64
import json
import re

from anthropic import Anthropic

from .schema import Mark

_MODEL = "claude-sonnet-5"

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


def _call_vision(image: bytes, api_key: str) -> dict:
    """Claude 비전에 사진을 보내 (document_text, items) 원시 JSON을 받는다."""
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
                            "media_type": "image/jpeg",
                            "data": base64.b64encode(image).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": "이 고지서 사진에서 항목을 뽑아 JSON으로만 답하라."},
                ],
            }
        ],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _parse_json(text)


def _parse_json(text: str) -> dict:
    """```json ... ``` 코드펜스가 섞여 와도 흡수해서 파싱한다 (API 응답은 모델 출력이라 흔들림)."""
    stripped = text.strip()
    fence_match = _FENCE_RE.search(stripped)
    payload = fence_match.group(1) if fence_match else stripped
    return json.loads(payload)


def extract(image: bytes, api_key: str) -> tuple[str, list[Mark]]:
    """(원문 글자, 표시 목록) 을 돌려준다. 아직 구현 전이라 빈 결과를 낸다."""
    return "", []
