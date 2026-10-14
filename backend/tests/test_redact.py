from app.redact import redact


def test_rrn_keeps_birth_and_gender_only():
    assert redact("주민번호 900101-1234567 입니다") == "주민번호 900101-1****** 입니다"


def test_account_number_hidden():
    assert redact("입금 계좌 123-456-789012") == "입금 계좌 [계좌번호 가림]"


def test_money_and_dates_untouched():
    text = "48,200원을 2026. 10. 31.까지"
    assert redact(text) == text
