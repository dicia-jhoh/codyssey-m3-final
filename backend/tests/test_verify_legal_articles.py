import json
from pathlib import Path

from app import lawapi
from scripts import verify_legal_articles


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def _fake_api(monkeypatch, article_text: str):
    monkeypatch.setattr(lawapi, "find_mst", lambda law_name, oc: "1")
    monkeypatch.setattr(lawapi, "fetch_article", lambda mst, jo, oc: article_text)


def test_ok_and_fail_rows_exit_1(tmp_path, monkeypatch, capsys):
    _fake_api(monkeypatch, "① 연체금을 징수한다.")
    path = tmp_path / "articles.jsonl"
    _write_jsonl(path, [
        {"law_name": "국민건강보험법", "article_no": "80", "quote": "연체금을 징수한다.", "claim": "풀이"},
        {"law_name": "국민연금법", "article_no": "97", "quote": "연체금이 부과됩니다.", "claim": "풀이"},
    ])

    assert verify_legal_articles.main([str(path)]) == 1

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "[OK] 국민건강보험법 제80조"
    assert out[1].startswith("[FAIL] 국민연금법 제97조 — 원문: ")


def test_all_ok_exit_0(tmp_path, monkeypatch, capsys):
    _fake_api(monkeypatch, "① 연체금을 징수한다.")
    path = tmp_path / "articles.jsonl"
    _write_jsonl(path, [
        {"law_name": "국민건강보험법", "article_no": "80의2", "quote": "연체금을 징수한다.", "claim": "풀이"},
    ])

    assert verify_legal_articles.main([str(path)]) == 0
    assert capsys.readouterr().out == "[OK] 국민건강보험법 제80조의2\n"


def test_missing_law_is_fail(tmp_path, monkeypatch, capsys):
    def not_found(law_name, oc):
        raise LookupError(f"현행 법령을 못 찾았다: {law_name}")

    monkeypatch.setattr(lawapi, "find_mst", not_found)
    path = tmp_path / "articles.jsonl"
    _write_jsonl(path, [{"law_name": "없는법", "article_no": "1", "quote": "x", "claim": "풀이"}])

    assert verify_legal_articles.main([str(path)]) == 1
    assert "[FAIL] 없는법 제1조 — 현행 법령을 못 찾았다: 없는법" in capsys.readouterr().out