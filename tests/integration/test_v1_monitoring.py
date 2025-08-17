from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_monitoring_health():
    r = client.get("/api/v1/monitoring/health")
    assert r.status_code == 200
    assert r.json()["db"] == "healthy"
