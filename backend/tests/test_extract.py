from app import extract
from app.schema import Mark


def test_parse_json_handles_bare_json():
    assert extract._parse_json('{"document_text": "x", "items": []}') == {
        "document_text": "x",
        "items": [],
    }


def test_parse_json_strips_code_fence():
    text = '```json\n{"document_text": "x", "items": []}\n```'
    assert extract._parse_json(text) == {"document_text": "x", "items": []}


def test_double_check_keeps_money_matching_document_text():
    marks = extract._double_check(
        document_text="납부금액: 금 48,200원",
        items=[{"kind": "money", "text": "금 48,200원", "value": "48200", "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert marks == [Mark(kind="money", text="금 48,200원", value="48200", bbox=[0, 0, 0.1, 0.1])]


def test_double_check_drops_money_not_found_in_document_text():
    marks = extract._double_check(
        document_text="납부금액: 금 48,200원",
        items=[{"kind": "money", "text": "금 99,999원", "value": "99999", "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert marks == []


def test_double_check_keeps_deadline_matching_document_text():
    marks = extract._double_check(
        document_text="납부기한: 2026.10.31까지",
        items=[{"kind": "deadline", "text": "2026.10.31까지", "value": "2026-10-31", "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert marks == [
        Mark(kind="deadline", text="2026.10.31까지", value="2026-10-31", bbox=[0, 0, 0.1, 0.1])
    ]


def test_double_check_drops_deadline_not_found_in_document_text():
    marks = extract._double_check(
        document_text="아무 날짜도 없음",
        items=[{"kind": "deadline", "text": "2026.10.31까지", "value": "2026-10-31", "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert marks == []


def test_double_check_passes_document_kind_without_verification():
    marks = extract._double_check(
        document_text="구비서류: 신분증",
        items=[{"kind": "document", "text": "신분증", "value": "", "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert marks == [Mark(kind="document", text="신분증", value="", bbox=[0, 0, 0.1, 0.1])]


def test_double_check_drops_malformed_item():
    marks = extract._double_check(
        document_text="아무 내용",
        items=[{"kind": "money", "text": "", "value": "", "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert marks == []


def test_extract_returns_empty_when_vision_call_fails(monkeypatch):
    def boom(image, api_key):
        raise RuntimeError("API 호출 실패")

    monkeypatch.setattr(extract, "_call_vision", boom)
    assert extract.extract(b"fake", "key") == ("", [])


def test_extract_wires_call_vision_and_double_check(monkeypatch):
    def fake_call_vision(image, api_key):
        return {
            "document_text": "납부금액: 금 48,200원",
            "items": [
                {"kind": "money", "text": "금 48,200원", "value": "48200", "bbox": [0.1, 0.1, 0.2, 0.05]},
            ],
        }

    monkeypatch.setattr(extract, "_call_vision", fake_call_vision)
    text, marks = extract.extract(b"fake", "key")
    assert text == "납부금액: 금 48,200원"
    assert marks == [
        Mark(kind="money", text="금 48,200원", value="48200", bbox=[0.1, 0.1, 0.2, 0.05])
    ]
