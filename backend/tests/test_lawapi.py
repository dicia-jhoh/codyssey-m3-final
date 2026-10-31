import pytest

from app.lawapi import jo_code


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