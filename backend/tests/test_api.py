from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert client.get("/health").json() == {"ok": True, "sample_mode": True}


def test_decode_sample_mode(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    r = client.post("/decode", files={"file": ("a.jpg", b"fake", "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["sample"] is True
    assert {m["kind"] for m in body["marks"]} == {"money", "deadline", "document"}
    assert all(b["quote"] for b in body["basis"])  # 근거 없는 풀이는 없다


def test_decode_rejects_non_image():
    r = client.post("/decode", files={"file": ("a.txt", b"hi", "text/plain")})
    assert r.status_code == 400
