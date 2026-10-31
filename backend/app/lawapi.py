"""법제처 Open API 로 조문 원문을 받아 articles.jsonl 의 quote 와 대조하는 도구.

articles.jsonl 의 quote 가 원문과 한 글자라도 다르면 화면에 "원문 인용"으로 틀린 글이
나간다(#32). 사람 눈 대조 대신 법제처 원문과 기계로 맞춰 본다.
"""

from __future__ import annotations

import re


def jo_code(article_no: str) -> str:
    """조문 번호("80", "80의2")를 법제처 API 의 6자리 JO 코드로 바꾼다.

    조 번호 4자리(앞을 0으로 채움) + 「의N」 2자리(없으면 00).
    "80" → "008000", "80의2" → "008002", "234의2" → "023402".
    """
    m = re.fullmatch(r"(\d+)(?:의(\d+))?", article_no.strip())
    if not m:
        raise ValueError(f"조문 번호 모양이 아니다: {article_no!r} (예: \"80\", \"80의2\")")
    return f"{int(m.group(1)):04d}{int(m.group(2) or 0):02d}"