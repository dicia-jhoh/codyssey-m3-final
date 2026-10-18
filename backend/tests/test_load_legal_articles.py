import json
from pathlib import Path

import pytest

from app import rag
from scripts.load_legal_articles import _DEFAULT_ARTICLES, load


@pytest.fixture(autouse=True)
def isolated_chroma_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(rag, "_CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(rag, "_client", None)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def test_load_adds_each_article_and_find_basis_can_see_it(tmp_path: Path):
    articles_path = tmp_path / "articles.jsonl"
    _write_jsonl(
        articles_path,
        [
            {
                "law_name": "국민건강보험법",
                "article_no": "80",
                "quote": "원문",
                "claim": "풀이",
                "source_url": "https://law.go.kr/...",
                "verified_at": "2026-10-18",
            }
        ],
    )

    count = load(articles_path)

    assert count == 1
    basis = rag.find_basis("국민건강보험법 제80조에 따라")
    assert basis == [rag.Basis(claim="풀이", quote="원문", law="국민건강보험법 제80조")]


def test_load_skips_blank_lines(tmp_path: Path):
    articles_path = tmp_path / "articles.jsonl"
    articles_path.write_text(
        '{"law_name": "지방세법", "article_no": "15", "quote": "q", "claim": "c"}\n\n\n',
        encoding="utf-8",
    )
    assert load(articles_path) == 1


def test_load_raises_on_missing_required_field(tmp_path: Path):
    articles_path = tmp_path / "articles.jsonl"
    _write_jsonl(articles_path, [{"law_name": "지방세법", "article_no": "15", "quote": "q"}])  # claim 없음

    with pytest.raises(ValueError, match="claim"):
        load(articles_path)


def test_real_articles_file_is_well_formed_and_loadable():
    """data/legal/articles.jsonl(실제 커밋되는 데이터)이 깨진 줄 없이 전부 로드되는지
    확인 — 필수 필드 누락이나 JSON 문법 오류가 섞여 들어가는 걸 CI 수준에서 막는다."""
    count = load(_DEFAULT_ARTICLES)
    assert count >= 2  # 국민건강보험법 제80조, 지방세기본법 제55조 — 더 늘면 이 숫자도 올릴 것

    assert rag.find_basis("국민건강보험법 제80조에 따라")
    assert rag.find_basis("지방세기본법 제55조에 따라")
