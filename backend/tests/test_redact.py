from app.redact import redact


def test_rrn_keeps_birth_and_gender_only():
    assert redact("주민번호 900101-1234567 입니다") == "주민번호 900101-1****** 입니다"


def test_account_number_hidden():
    assert redact("입금 계좌 123-456-789012") == "입금 계좌 [계좌번호 가림]"


def test_money_and_dates_untouched():
    text = "48,200원을 2026. 10. 31.까지"
    assert redact(text) == text


def test_hyphen_date_is_not_an_account():
    assert redact("납부기한 2026-10-31") == "납부기한 2026-10-31"


def test_four_part_account_hidden():
    assert redact("농협 352-1234-5678-13") == "농협 [계좌번호 가림]"


def test_rrn_masked_even_when_particle_attached_with_no_space():
    # \b는 한글을 \w로 쳐서 숫자-한글 사이에 경계가 안 생긴다 — 조사가 바로 붙으면
    # (예: "...이며") 기존 \b 기반 정규식은 이 주민번호를 통째로 놓쳤다.
    assert redact("주민번호 900101-1234567이며") == "주민번호 900101-1******이며"
    assert redact("900101-1234567로 확인됩니다") == "900101-1******로 확인됩니다"


def test_account_masked_even_when_particle_attached_with_no_space():
    assert redact("계좌 123-456-789012로 입금") == "계좌 [계좌번호 가림]로 입금"


def test_rrn_without_separator():
    assert redact("9001011234567 입니다") == "900101-1****** 입니다"


def test_rrn_foreign_resident_gender_digit():
    # 외국인 주민번호 뒷자리 첫 숫자는 5~8
    assert redact("외국인등록 900101-5234567") == "외국인등록 900101-5******"


def test_rrn_invalid_gender_digit_not_masked_as_rrn():
    # 뒷자리 첫 숫자가 9/0이면 주민번호 모양이 아니다 — RRN으로는 안 가린다
    # (계좌 패턴에도 안 걸림: 하이픈이 중간에 있어 10~14자리 연속 숫자가 아님).
    assert redact("900101-9234567") == "900101-9234567"


def test_multiple_pii_in_one_text():
    text = "주민번호 900101-1234567, 계좌 123-456-789012"
    assert redact(text) == "주민번호 900101-1******, 계좌 [계좌번호 가림]"
