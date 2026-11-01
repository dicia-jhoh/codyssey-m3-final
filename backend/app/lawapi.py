"""법제처 Open API 로 조문 원문을 받아 articles.jsonl 의 quote 와 대조하는 도구.

articles.jsonl 의 quote 가 원문과 한 글자라도 다르면 화면에 "원문 인용"으로 틀린 글이
나간다(#32). 사람 눈 대조 대신 법제처 원문과 기계로 맞춰 본다.
"""

from __future__ import annotations

import re

import httpx

_BASE = "https://www.law.go.kr/DRF"


def jo_code(article_no: str) -> str:
    """조문 번호("80", "80의2")를 법제처 API 의 6자리 JO 코드로 바꾼다.

    조 번호 4자리(앞을 0으로 채움) + 「의N」 2자리(없으면 00).
    "80" → "008000", "80의2" → "008002", "234의2" → "023402".
    """
    m = re.fullmatch(r"(\d+)(?:의(\d+))?", article_no.strip())
    if not m:
        raise ValueError(f'조문 번호 모양이 아니다: {article_no!r} (예: "80", "80의2")')
    return f"{int(m.group(1)):04d}{int(m.group(2) or 0):02d}"


def _squash(text: str) -> str:
    """공백·줄바꿈을 전부 지운다.

    원문과 quote 의 띄어쓰기 차이(「말한다) 까지」 vs 「말한다)까지」)를 무시하려고.
    """
    return re.sub(r"\s+", "", text)


def quote_matches(article_text: str, quote: str) -> bool:
    """quote 가 조문 원문 안에 글자 그대로 들어 있는가(공백 차이만 무시).

    quote 는 조문의 일부(①항 하나, 3호 하나)라서 「같다」가 아니라 「포함된다」로 본다.
    """
    q = _squash(quote)
    return bool(q) and q in _squash(article_text)


def _as_list(value) -> list:
    """법제처 JSON 은 항목이 하나면 리스트 대신 그 항목 하나만 준다 — 늘 리스트로 맞춘다."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def find_mst(law_name: str, oc: str) -> str:
    """법령 이름이 정확히 같은 현행 법령의 법령일련번호(MST)를 찾는다."""
    r = httpx.get(
        f"{_BASE}/lawSearch.do",
        params={"OC": oc, "target": "law", "type": "JSON", "query": law_name},
        timeout=20,
    )
    r.raise_for_status()
    for law in _as_list(r.json().get("LawSearch", {}).get("law")):
        if law.get("법령명한글") == law_name and law.get("현행연혁코드") == "현행":
            return law["법령일련번호"]
    raise LookupError(f"현행 법령을 못 찾았다: {law_name}")


def fetch_article(mst: str, jo: str, oc: str) -> str:
    """MST + JO 코드로 조문 하나를 받아 본문 텍스트(조문·항·호·목)를 줄바꿈으로 이어 돌려준다."""
    r = httpx.get(
        f"{_BASE}/lawService.do",
        params={"OC": oc, "target": "law", "type": "JSON", "MST": mst, "JO": jo},
        timeout=20,
    )
    r.raise_for_status()
    units = _as_list((r.json().get("법령", {}).get("조문") or {}).get("조문단위"))
    lines: list[str] = []
    for unit in units:
        lines.append(unit.get("조문내용", ""))
        for hang in _as_list(unit.get("항")):
            lines.append(hang.get("항내용", ""))
            for ho in _as_list(hang.get("호")):
                lines.append(ho.get("호내용", ""))
                for mok in _as_list(ho.get("목")):
                    lines.append(mok.get("목내용", ""))
    text = "\n".join(line for line in lines if line)
    if not text:
        raise LookupError(f"조문을 못 찾았다: MST={mst} JO={jo}")
    return text
