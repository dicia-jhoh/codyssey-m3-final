"""data/legal/articles.jsonl 의 quote 를 법제처 원문과 대조한다.

사용:
    cd backend
    python -m scripts.verify_legal_articles

조문마다 [OK]/[FAIL] 한 줄을 찍고, 하나라도 FAIL 이면 exit 1. 법제처 API 키는
LAW_OC 환경변수(없으면 팀 공용 parapuda). 조문을 추가하는 절차는 data/legal/README.md.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from app import lawapi
from app.rag import _format_law  # 화면 근거와 같은 「제80조의2」 표기

_DEFAULT_ARTICLES = Path(__file__).resolve().parents[2] / "data" / "legal" / "articles.jsonl"


def verify(path: Path, oc: str) -> int:
    """조문마다 결과 한 줄을 찍고 FAIL 개수를 돌려준다."""
    failed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        name = _format_law(row["law_name"], row["article_no"])
        try:
            mst = lawapi.find_mst(row["law_name"], oc)
            text = lawapi.fetch_article(mst, lawapi.jo_code(row["article_no"]), oc)
        except (LookupError, ValueError) as e:
            print(f"[FAIL] {name} — {e}")
            failed += 1
            continue
        if lawapi.quote_matches(text, row["quote"]):
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name} — 원문: {text}")
            failed += 1
    return failed


def main(argv: list[str] | None = None) -> int:
    path = Path(argv[0]) if argv else _DEFAULT_ARTICLES
    if not path.exists():
        print(f"[!] 파일 없음: {path}")
        return 1
    return 1 if verify(path, os.environ.get("LAW_OC", "parapuda")) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
