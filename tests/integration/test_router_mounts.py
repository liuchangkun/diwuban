import pytest

from app.main import app

TestClient = pytest.importorskip("fastapi").testclient.TestClient  # type: ignore[attr-defined]

client = TestClient(app)


def test_v1_routes_mounted():
    r = client.get("/api/v1/data/measurements")
    assert r.status_code == 200
