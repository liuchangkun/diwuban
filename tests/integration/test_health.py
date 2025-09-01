import pytest

from app.main import app

TestClient = pytest.importorskip("fastapi").testclient.TestClient  # type: ignore[attr-defined]

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
