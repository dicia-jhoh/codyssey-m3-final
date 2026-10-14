"""사진 → 글자·표시(Mark) 추출 — 담당: 황지영.

할 일
1. 비전 LLM 에 사진을 보내 schema.Mark 목록과 원문 글자를 JSON 으로 받는다(docs/03-AI-설계.md 「프롬프트」).
2. 금액·날짜는 LLM 값과 사진 속 숫자를 한 번 더 대조한다. 어긋나면 그 Mark 는 빼고 「직접 확인 필요」로 남긴다.
3. bbox 는 사진 크기 대비 비율(0~1)로 바꾼다 — 화면이 사진 크기와 상관없이 3색을 그리게 하려는 것.
"""

from .schema import Mark


def extract(image: bytes, api_key: str) -> tuple[str, list[Mark]]:
    """(원문 글자, 표시 목록) 을 돌려준다. 아직 구현 전이라 빈 결과를 낸다."""
    return "", []
