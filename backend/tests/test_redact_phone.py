from app.redact import redact


def test_mobile_number_is_hidden_as_phone_not_account():
    assert redact("담당자 010-1234-5678") == "담당자 [전화번호 가림]"


def test_office_numbers_are_hidden_as_phone():
    assert redact("문의 042-123-4567, 02-1234-5678") == "문의 [전화번호 가림], [전화번호 가림]"


def test_account_number_is_still_an_account():
    assert redact("계좌 110-123-456789") == "계좌 [계좌번호 가림]"