import subprocess
from types import SimpleNamespace

import pytest

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_health(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert client.get("/health").json() == {"ok": True, "sample_mode": True, "commit": main.COMMIT}


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


def test_share_round_trip():
    decode_body = client.post("/decode", files={"file": ("a.jpg", b"fake", "image/jpeg")}).json()

    share_id = client.post("/share", json=decode_body).json()["share_id"]
    shared = client.get(f"/share/{share_id}")

    assert shared.status_code == 200
    assert shared.json() == decode_body


def test_share_rejects_oversized_body():
    body = {"doc_type": "고지서", "title": "가" * 70_000, "plain": [], "marks": [], "todos": [], "basis": []}
    assert client.post("/share", json=body).status_code == 413


def test_share_unknown_id_is_404():
    r = client.get("/share/없는-아이디")
    assert r.status_code == 404


def test_pages_revalidate():
    for path in ("/", "/content/site.js", "/assets/css/site.css", "/app/"):
        assert client.get(path).headers.get("cache-control") == "no-cache", path


@pytest.mark.parametrize("error", [FileNotFoundError(), subprocess.CalledProcessError(1, "git"), subprocess.TimeoutExpired("git", 2)])
def test_commit_lookup_failure_is_unknown(monkeypatch, error):
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(main.subprocess, "run", fail)
    assert main._read_commit() == "unknown"
    assert client.get("/health").status_code == 200


def test_commit_lookup_and_health_cache(monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        assert kwargs["cwd"] == main.ROOT
        assert kwargs["timeout"] == 2
        return SimpleNamespace(stdout="abc1234\n")

    monkeypatch.setattr(main.subprocess, "run", run)
    assert main._read_commit() == "abc1234"
    for _ in range(2):
        assert client.get("/health").json()["commit"] == main.COMMIT
    assert calls == [["git", "rev-parse", "--short", "HEAD"]]
