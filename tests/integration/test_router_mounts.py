from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_v1_routes_mounted():
    r = client.get("/api/v1/data/measurements")
    assert r.status_code == 200
