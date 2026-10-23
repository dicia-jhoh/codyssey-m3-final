import asyncio

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app import main
from app.sample import SAMPLE


@pytest.mark.parametrize(
    "size, content_type, status, detail",
    [
        (0, "image/jpeg", 400, "빈 사진 파일이에요"),
        (1, "image/jpeg", 200, None),
        (main.MAX_BYTES - 1, "image/jpeg", 200, None),
        (main.MAX_BYTES, "image/jpeg", 200, None),
        (main.MAX_BYTES + 1, "image/jpeg", 413, "사진이 너무 커요(10MB 이하)"),
        (1, "text/plain", 400, "사진 파일만 올릴 수 있어요"),
    ],
)
def test_decode_upload_validation(monkeypatch, size, content_type, status, detail):
    read_sizes = []
    decoded_sizes = []
    original_read = UploadFile.read

    async def tracked_read(file, size=-1):
        read_sizes.append(size)
        return await original_read(file, size)

    def fake_decode(image):
        decoded_sizes.append(len(image))
        return SAMPLE

    monkeypatch.setattr(UploadFile, "read", tracked_read)
    monkeypatch.setattr(main, "decode", fake_decode)
    with TestClient(main.app) as client:
        response = client.post(
            "/decode", files={"file": ("photo.jpg", b"x" * size, content_type)}
        )

    assert response.status_code == status
    assert read_sizes == ([main.MAX_BYTES + 1] if content_type == "image/jpeg" else [])
    assert decoded_sizes == ([size] if status == 200 else [])
    if detail:
        assert response.json() == {"detail": detail}
    else:
        assert response.json() == SAMPLE.model_dump()


def test_oversized_header_rejected_without_reading_body(monkeypatch):
    async def scenario():
        sent = []

        async def receive():
            pytest.fail("request body must not be read")

        async def send(message):
            sent.append(message)

        def decode(image):
            pytest.fail("decode must not run")

        monkeypatch.setattr(main, "decode", decode)
        scope = {
            "type": "http", "http_version": "1.1", "method": "POST", "path": "/decode",
            "scheme": "http", "query_string": b"", "root_path": "",
            "headers": [(b"content-length", str(main.MAX_BYTES + main.MULTIPART_OVERHEAD + 1).encode())],
            "server": ("test", 80), "client": ("test", 123),
        }
        await main.app(scope, receive, send)
        assert sent[0]["status"] == 413

    asyncio.run(scenario())


@pytest.mark.parametrize("length", [None, "invalid", str(main.MAX_BYTES + main.MULTIPART_OVERHEAD)])
def test_acceptable_headers_still_decode(monkeypatch, length):
    monkeypatch.setattr(main, "decode", lambda image: SAMPLE)
    headers = {"content-length": length} if length is not None else {}
    with TestClient(main.app) as client:
        request = client.build_request("POST", "/decode", files={"file": ("a.jpg", b"ok", "image/jpeg")})
        request.headers.pop("content-length", None)
        request.headers.update(headers)
        response = client.send(request)
    assert response.status_code == 200


def test_other_routes_ignore_decode_upload_limit():
    with TestClient(main.app) as client:
        response = client.post("/share", json=SAMPLE.model_dump(), headers={"content-length": str(main.MAX_BYTES * 2)})
    assert response.status_code == 200
