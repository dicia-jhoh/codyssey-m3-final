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


def test_root_serves_homepage():
    r = client.get("/")
    assert r.status_code == 200
    assert 'id="sky"' in r.text  # 팀 홈페이지(별자리)
    assert client.get("/content/site.js").status_code == 200


def test_app_serves_service_screen():
    r = client.get("/app/")
    assert r.status_code == 200
    assert 'id="photo"' in r.text  # 사진 올리기 화면


def test_repo_files_not_exposed():
    for path in ("/backend/.env.example", "/backend/app/main.py", "/README.md", "/.gitignore"):
        assert client.get(path).status_code == 404, path
