import pytest

from app import extract
from app.schema import Mark


def test_media_type_detects_png():
    assert extract._media_type(b"\x89PNG\r\n\x1a\n...") == "image/png"


def test_media_type_detects_webp():
    assert extract._media_type(b"RIFF\x00\x00\x00\x00WEBP...") == "image/webp"


def test_media_type_detects_gif():
    assert extract._media_type(b"GIF89a...") == "image/gif"


def test_media_type_defaults_to_jpeg():
    assert extract._media_type(b"\xff\xd8\xff\xe0...") == "image/jpeg"
    assert extract._media_type(b"anything-else") == "image/jpeg"


def test_media_type_rejects_heic():
    # ftyp 박스 + heic 브랜드 — 아이폰 카메라 기본 형식. 예전엔 이것도 그냥 image/jpeg로
    # 둔갑시켜서, API가 거부해도 이유가 안 보였다(아이폰이 주 사용 기기인데도).
    heic_bytes = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00..."

    with pytest.raises(extract.UnsupportedImageFormatError, match="HEIC"):
        extract._media_type(heic_bytes)


def test_extract_falls_back_to_sample_mode_on_heic(monkeypatch):
    # _call_vision 안에서 _media_type이 HEIC를 거부하면, extract()의 광범위한
    # except가 이를 잡아 빈 결과를 내고(agent.py가 샘플 모드로 넘어감), 조용히
    # image/jpeg로 속여 보내던 예전 동작으로 되돌아가지 않는다.
    heic_bytes = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00..."
    assert extract.extract(heic_bytes, "dummy-key") == ("", [])


class _FakeTextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAnthropicResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, calls: list[dict]) -> None:
        self._calls = calls

    def create(self, **kwargs):
        self._calls.append(kwargs)
        return _FakeAnthropicResponse('{"document_text": "x", "items": []}')


class _FakeAnthropicClient:
    def __init__(self, calls: list[dict], **_kwargs) -> None:
        self.messages = _FakeMessages(calls)


def test_call_vision_sends_current_model_and_detected_media_type(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(extract, "Anthropic", lambda **kwargs: _FakeAnthropicClient(calls, **kwargs))

    extract._call_vision(b"\x89PNG\r\n\x1a\n...", "dummy-key")

    assert len(calls) == 1
    assert calls[0]["model"] == extract._MODEL
    image_block = calls[0]["messages"][0]["content"][0]
    assert image_block["source"]["media_type"] == "image/png"


class _FakeGeminiResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"candidates": [{"content": {"parts": [{"text": '{"document_text": "g", "items": []}'}]}}]}


@pytest.mark.parametrize("key", ["AIzaDummy", "AQ.Dummy"])  # 옛 키·새 키 모양 둘 다
def test_call_vision_sends_gemini_key_to_gemini_in_header(monkeypatch, key):
    calls: list[dict] = []
    monkeypatch.setattr(extract, "Anthropic", lambda **kwargs: pytest.fail("Gemini 키가 Claude 로 갔다"))
    monkeypatch.setattr(extract.httpx, "post", lambda url, **kw: calls.append({"url": url, **kw}) or _FakeGeminiResponse())

    raw = extract._call_vision(b"\x89PNG\r\n\x1a\n...", key)

    assert raw == {"document_text": "g", "items": []}
    assert extract._GEMINI_MODEL in calls[0]["url"]
    assert key not in calls[0]["url"]  # 키가 URL(=오류 로그)에 실리지 않는다
    assert calls[0]["headers"] == {"x-goog-api-key": key}
    image_part = calls[0]["json"]["contents"][0]["parts"][0]
    assert image_part["inline_data"]["mime_type"] == "image/png"


def test_call_gemini_rejects_gif_before_sending(monkeypatch):
    monkeypatch.setattr(extract.httpx, "post", lambda *a, **kw: pytest.fail("GIF 를 보냈다"))
    with pytest.raises(extract.UnsupportedImageFormatError):
        extract._call_vision(b"GIF89a...", "AIzaDummy")


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


def test_double_check_keeps_deadline_in_month_day_format():
    # 연도 없이 "10월 31일"만 적힌 공문이 흔함 — fallback_year로 교차 대조되어야 한다.
    marks = extract._double_check(
        document_text="납부기한: 10월 31일까지",
        items=[{"kind": "deadline", "text": "10월 31일까지", "value": "10월 31일", "bbox": [0, 0, 0.1, 0.1]}],
        fallback_year=2026,
    )
    assert marks == [
        Mark(kind="deadline", text="10월 31일까지", value="2026-10-31", bbox=[0, 0, 0.1, 0.1])
    ]


@pytest.mark.parametrize(
    ("document_text", "value", "expected"),
    [
        ("납부기한: 2026. 10. 31.(토)까지", "2026-10-31", ["2026-10-31"]),
        ("2027년 1월 15일까지 내세요", "2027-01-15", ["2027-01-15"]),
        ("2025년 10월 31일까지 내세요", "2026-10-31", []),  # 연도가 다르면 통과시키지 않는다
    ],
)
def test_double_check_deadline_formats(document_text, value, expected):
    marks = extract._double_check(
        document_text=document_text,
        items=[{"kind": "deadline", "text": "기한", "value": value, "bbox": [0, 0, 0.1, 0.1]}],
        fallback_year=2026,
    )
    assert [m.value for m in marks] == expected


def test_double_check_ignores_calendar_invalid_date():
    marks = extract._double_check(
        document_text="납부기한: 13월 31일까지",
        items=[{"kind": "deadline", "text": "13월 31일까지", "value": "13월 31일", "bbox": [0, 0, 0.1, 0.1]}],
        fallback_year=2026,
    )
    assert marks == []


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


@pytest.mark.parametrize(
    "raw",
    [
        [{"document_text": "48,200원"}],
        {"document_text": 123},
        {"document_text": "48,200원", "items": "money"},
    ],
)
def test_extract_returns_empty_or_skips_on_wrong_shape(monkeypatch, raw):
    monkeypatch.setattr(extract, "_call_vision", lambda image, api_key: raw)
    _, marks = extract.extract(b"fake", "key")
    assert marks == []


@pytest.mark.parametrize(
    "item",
    [
        "money",
        {"kind": "money", "text": "48,200원", "value": "48,200원", "bbox": ["a", 0, 0, 0]},
        {"kind": "money", "text": "48,200원", "value": "48,200원", "bbox": 0.5},
        {"kind": "money", "text": "48,200원", "value": "48,200원", "bbox": [float("nan"), 0, 0, 0]},
        {"kind": "money", "text": 48200, "value": "48,200원", "bbox": [0, 0, 0.1, 0.1]},
    ],
)
def test_double_check_skips_wrong_shape_item(item):
    assert extract._double_check(document_text="합계 48,200원", items=[item]) == []


def test_double_check_accepts_numeric_value():
    marks = extract._double_check(
        document_text="합계 48,200원",
        items=[{"kind": "money", "text": "48,200원", "value": 48200, "bbox": [0, 0, 0.1, 0.1]}],
    )
    assert [m.value for m in marks] == ["48200"]


def test_extract_returns_empty_when_vision_call_fails(monkeypatch):
    def boom(image, api_key):
        raise RuntimeError("API 호출 실패")

    monkeypatch.setattr(extract, "_call_vision", boom)
    assert extract.extract(b"fake", "key") == ("", [])


def test_main_fails_without_api_key(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    exit_code = extract._main([str(tmp_path / "a.jpg")])
    assert exit_code == 1
    assert "API 키 없음" in capsys.readouterr().out


def test_main_fails_when_image_missing(tmp_path, capsys):
    missing = tmp_path / "없음.jpg"
    exit_code = extract._main([str(missing), "--api-key", "dummy"])
    assert exit_code == 1
    assert "이미지 없음" in capsys.readouterr().out


def test_main_prints_marks_on_success(monkeypatch, tmp_path, capsys):
    image_path = tmp_path / "a.jpg"
    image_path.write_bytes(b"fake")

    def fake_extract(image, api_key):
        return "납부금액: 금 48,200원", [
            Mark(kind="money", text="금 48,200원", value="48200", bbox=[0, 0, 0.1, 0.1])
        ]

    monkeypatch.setattr(extract, "extract", fake_extract)
    exit_code = extract._main([str(image_path), "--api-key", "dummy"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Mark 1건" in out
    assert "48200" in out


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
