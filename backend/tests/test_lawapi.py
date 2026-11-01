import pytest

from app.lawapi import jo_code, quote_matches


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
