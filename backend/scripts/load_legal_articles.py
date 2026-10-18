"""data/legal/articles.jsonl → Chroma 적재.

사용:
    cd backend
    python -m scripts.load_legal_articles

Chroma DB(data/legal/chroma/)는 .gitignore 대상이라 사람마다 로컬에 따로 생긴다 —
이 스크립트로 커밋된 articles.jsonl에서 언제든 다시 만들 수 있다. articles.jsonl에
조문을 추가하는 법은 data/legal/README.md 참고.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app import rag

_DEFAULT_ARTICLES = Path(__file__).resolve().parents[2] / "data" / "legal" / "articles.jsonl"

_REQUIRED_FIELDS = ("law_name", "article_no", "quote", "claim")


def load(path: Path = _DEFAULT_ARTICLES) -> int:
    """articles.jsonl의 조문을 전부 rag.add_article()로 넣는다. 넣은 개수를 돌려준다."""
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        missing = [f for f in _REQUIRED_FIELDS if not row.get(f)]
        if missing:
            raise ValueError(f"{path}: 필수 필드 누락 {missing} — {row}")
        rag.add_article(
            law_name=row["law_name"],
            article_no=row["article_no"],
            quote=row["quote"],
            claim=row["claim"],
        )
        count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    path = Path(argv[0]) if argv else _DEFAULT_ARTICLES
    if not path.exists():
        print(f"[!] 파일 없음: {path}")
        return 1

    count = load(path)
    print(f"[✓] {count}건 적재 완료 — {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
