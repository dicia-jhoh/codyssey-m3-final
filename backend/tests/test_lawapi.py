import pytest

from app import lawapi
from app.lawapi import fetch_article, find_mst, jo_code, quote_matches


def test_jo_code_plain_article():
    assert jo_code("80") == "008000"


def test_jo_code_branch_article():
    assert jo_code("80의2") == "008002"


def test_jo_code_three_digit_branch_article():
    assert jo_code("234의2") == "023402"


@pytest.mark.parametrize("bad", ["", "제80조", "80조", "abc", "80의"])
def test_jo_code_rejects_non_numbers(bad):
    with pytest.raises(ValueError):
        jo_code(bad)


def test_quote_matches_part_of_article():
    article = "① 공단은 보험료를 내지 아니하면 연체금을 징수한다.\n② 다음 항."
    assert quote_matches(article, "공단은 보험료를 내지 아니하면 연체금을 징수한다.")


def test_quote_matches_ignores_spacing_around_parenthesis():
    # 실측 사례(국민연금법 제97조) — 원문은 「) 까지」, quote 는 「)까지」
    article = "납부 기한(제89조제5항에 따라 납부 기한을 연장한 경우에는 그 기한을 말한다) 까지 연금보험료를 내지 아니하면"
    quote = "납부 기한(제89조제5항에 따라 납부 기한을 연장한 경우에는 그 기한을 말한다)까지 연금보험료를"
    assert quote_matches(article, quote)


def test_quote_matches_ignores_newlines_and_double_spaces():
    assert quote_matches("연체금을\n  징수한다.", "연체금을 징수한다.")


def test_quote_matches_rejects_changed_words():
    assert not quote_matches("연체금을 징수한다.", "연체금이 부과됩니다.")


def test_quote_matches_rejects_empty_quote():
    assert not quote_matches("연체금을 징수한다.", "")
    assert not quote_matches("연체금을 징수한다.", "   ")


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def _fake_get(data, calls):
    def get(url, params, timeout):
        calls.append((url, params))
        return _FakeResponse(data)

    return get


def test_find_mst_picks_exact_current_law(monkeypatch):
    calls = []
    data = {"LawSearch": {"law": [
        {"법령명한글": "국민건강보험법", "현행연혁코드": "현행", "법령일련번호": "285273"},
        {"법령명한글": "국민건강보험법 시행령", "현행연혁코드": "현행", "법령일련번호": "289701"},
    ]}}
    monkeypatch.setattr(lawapi.httpx, "get", _fake_get(data, calls))
    assert find_mst("국민건강보험법", "parapuda") == "285273"
    assert calls[0][1]["query"] == "국민건강보험법"
    assert calls[0][1]["OC"] == "parapuda"


def test_find_mst_accepts_single_result_dict(monkeypatch):
    # 결과가 1건이면 법제처는 리스트가 아니라 객체 하나를 준다
    data = {"LawSearch": {"law": {"법령명한글": "도로교통법", "현행연혁코드": "현행", "법령일련번호": "291133"}}}
    monkeypatch.setattr(lawapi.httpx, "get", _fake_get(data, []))
    assert find_mst("도로교통법", "parapuda") == "291133"


def test_find_mst_raises_lookup_error_with_name(monkeypatch):
    monkeypatch.setattr(lawapi.httpx, "get", _fake_get({"LawSearch": {"totalCnt": "0"}}, []))
    with pytest.raises(LookupError, match="없는법"):
        find_mst("없는법", "parapuda")


def test_fetch_article_joins_article_paragraphs_and_items(monkeypatch):
    calls = []
    data = {"법령": {"조문": {"조문단위": {
        "조문내용": "제80조(연체금)",
        "항": [
            {"항내용": "① 연체금을 징수한다.", "호": [{"호내용": "1. 첫째 호"}, {"호내용": "2. 둘째 호"}]},
            {"항내용": "② 둘째 항"},
        ],
    }}}}
    monkeypatch.setattr(lawapi.httpx, "get", _fake_get(data, calls))
    text = fetch_article("285273", "008000", "parapuda")
    assert text == "제80조(연체금)\n① 연체금을 징수한다.\n1. 첫째 호\n2. 둘째 호\n② 둘째 항"
    assert calls[0][1]["MST"] == "285273"
    assert calls[0][1]["JO"] == "008000"


def test_fetch_article_raises_lookup_error_when_missing(monkeypatch):
    # 없는 조문이면 법령 정보만 오고 「조문」이 없다(실측)
    monkeypatch.setattr(lawapi.httpx, "get", _fake_get({"법령": {"기본정보": {}}}, []))
    with pytest.raises(LookupError, match="JO=999900"):
        fetch_article("285273", "999900", "parapuda")
