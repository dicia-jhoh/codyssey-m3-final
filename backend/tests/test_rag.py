from pathlib import Path

import pytest

from app import rag


@pytest.fixture(autouse=True)
def isolated_chroma_dir(tmp_path: Path, monkeypatch):
    """테스트마다 격리된 Chroma 디렉터리를 쓴다 — 실제 data/legal/chroma/를 안 건드린다."""
    monkeypatch.setattr(rag, "_CHROMA_DIR", tmp_path)
    monkeypatch.setattr(rag, "_client", None)


def test_citations_extracts_law_name_and_article_number():
    assert rag._citations("국민건강보험법 제80조에 따라 연체금이 부과됩니다") == [
        ("국민건강보험법", "80")
    ]


def test_citations_handles_multiple_and_no_match():
    assert rag._citations("지방세법 제15조, 국민건강보험법 제80조") == [
        ("지방세법", "15"),
        ("국민건강보험법", "80"),
    ]
    assert rag._citations("아무 법 언급도 없는 문장") == []


def test_citations_distinguishes_sub_article():
    # "제80조의2"를 "80"으로 뭉뚱그리면 제80조(다른 조문)가 근거로 잘못 붙는다.
    assert rag._citations("국민건강보험법 제80조의2에 따라") == [("국민건강보험법", "80의2")]


def test_citations_deduplicates_keeping_order():
    text = "국민건강보험법 제80조... 지방세법 제15조... 국민건강보험법 제80조"
    assert rag._citations(text) == [("국민건강보험법", "80"), ("지방세법", "15")]


def test_find_basis_formats_sub_article_law_string():
    rag.add_article(law_name="국민건강보험법", article_no="80의2", quote="원문", claim="풀이")
    basis = rag.find_basis("국민건강보험법 제80조의2에 따라")
    assert basis[0].law == "국민건강보험법 제80조의2"


def test_find_basis_returns_empty_when_collection_raises(monkeypatch):
    def boom():
        raise RuntimeError("디스크 권한 없음")

    monkeypatch.setattr(rag, "_collection", boom)
    assert rag.find_basis("국민건강보험법 제80조에 따라") == []


def test_find_basis_returns_empty_when_collection_empty():
    assert rag.find_basis("국민건강보험법 제80조에 따라") == []


def test_find_basis_returns_empty_when_no_citation_in_text():
    rag.add_article(
        law_name="국민건강보험법", article_no="80", quote="원문", claim="풀이"
    )
    assert rag.find_basis("인용 없는 문장") == []


def test_find_basis_returns_matching_article_after_add_article():
    rag.add_article(
        law_name="국민건강보험법",
        article_no="80",
        quote="납부기한이 지나면 연체금이 부과됩니다.",
        claim="기한을 넘기면 돈을 조금 더 내야 해요.",
    )

    basis = rag.find_basis("국민건강보험법 제80조에 따라 연체금이 부과됩니다")

    assert len(basis) == 1
    assert basis[0].claim == "기한을 넘기면 돈을 조금 더 내야 해요."
    assert basis[0].quote == "납부기한이 지나면 연체금이 부과됩니다."
    assert basis[0].law == "국민건강보험법 제80조"


def test_find_basis_ignores_unrelated_article_in_collection():
    rag.add_article(law_name="지방세법", article_no="15", quote="원문", claim="풀이")
    assert rag.find_basis("국민건강보험법 제80조에 따라") == []
