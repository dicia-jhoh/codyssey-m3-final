import sys
from pathlib import Path

import pytest

# backend/ 에서 pytest 를 치면 app 패키지를 찾게 한다
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))



@pytest.fixture(autouse=True)
def isolate_share_database(monkeypatch, tmp_path):
    monkeypatch.setenv("SHARE_DB", str(tmp_path / "share.db"))
