import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def run(
    cmd: list[str], cwd: Path | None = None, timeout: int = 300
) -> tuple[int, str, str]:
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
    return p.returncode, out, err


def test_cli_help():
    code, out, _ = run([PY, "-m", "app.cli.main", "--help"])
    assert code == 0
    assert "Commands" in out or "命令" in out


def test_cli_db_ping():
    code, out, _ = run([PY, "-m", "app.cli.main", "db-ping", "--verbose"])
    assert code == 0
    assert "db:ping ok" in out


def test_prepare_staging_ingest_merge():
    # prepare-dim（不启用文件日志，避免 Windows 上文件占用导致清理失败）
    code, out, err = run(
        [PY, "-m", "app.cli.main", "prepare-dim", "configs/data_mapping.v2.json"]
    )
    assert code == 0, f"prepare-dim failed: {err}\n{out}"
    # create-staging
    code, out, err = run([PY, "-m", "app.cli.main", "create-staging"])
    assert code == 0, f"create-staging failed: {err}\n{out}"
    # ingest-copy
    code, out, err = run(
        [PY, "-m", "app.cli.main", "ingest-copy", "configs/data_mapping.v2.json"]
    )
    assert code == 0, f"ingest-copy failed: {err}\n{out}"
    # merge-fact 使用固定窗口（存在数据即可通过）
    code, out, err = run(
        [
            PY,
            "-m",
            "app.cli.main",
            "merge-fact",
            "--window-start",
            "2025-02-27T18:00:00Z",
            "--window-end",
            "2025-02-27T22:00:00Z",
        ]
    )
    assert code == 0, f"merge-fact failed: {err}\n{out}"


def _start_server():
    p = subprocess.Popen(
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"],
        cwd=str(ROOT),
    )
    # 等待服务就绪
    for _ in range(50):
        try:
            r = requests.get("http://127.0.0.1:8002/health", timeout=1)
            if r.status_code == 200:
                return p
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("server not ready")


def test_api_endpoints():
    p = _start_server()
    try:
        # /health
        r = requests.get("http://127.0.0.1:8002/health", timeout=3)
        assert r.status_code == 200
        j = r.json()
        assert j.get("status") == "ok"

        # /data/stations
        r = requests.get("http://127.0.0.1:8002/api/v1/data/stations", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        # /data/metrics
        r = requests.get("http://127.0.0.1:8002/api/v1/data/metrics", timeout=5)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

        # /data/measurements (device_id)
        r = requests.get(
            "http://127.0.0.1:8002/api/v1/data/measurements",
            params={
                "device_id": 1,
                "start_time": "2025-02-27T18:00:00Z",
                "end_time": "2025-02-27T20:00:00Z",
                "limit": 10,
            },
            timeout=10,
        )
        assert r.status_code == 200
        jr = r.json()
        assert isinstance(jr, dict)
        assert "data" in jr
    finally:
        p.terminate()
        p.wait(timeout=10)
