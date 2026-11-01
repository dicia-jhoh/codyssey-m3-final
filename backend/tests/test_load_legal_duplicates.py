import json
from pathlib import Path

import pytest

from app import rag
from scripts.load_legal_articles import load


@pytest.fixture(autouse=True)
def isolated_chroma_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rag, "_CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(rag, "_client", None)


def _row(article_no: str, quote: str) -> str:
    return json.dumps(
        {"law_name": "지방세법", "article_no": article_no, "quote": quote, "claim": "풀이"},
        ensure_ascii=False,
    )


def test_same_article_twice_stops_loading(tmp_path: Path):
    path = tmp_path / "articles.jsonl"
    path.write_text(_row("115", "앞 원문") + "\n" + _row("115", "뒤 원문"), encoding="utf-8")
    with pytest.raises(ValueError, match="두 번"):
        load(path)