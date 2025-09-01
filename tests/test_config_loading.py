from pathlib import Path
from app.core.config.loader import load_settings, load_settings_with_sources, Settings


def test_load_settings_from_repo_configs():
    s: Settings = load_settings(Path("configs"))
    # database.yaml 基础字段
    assert s.db.host
    assert s.db.pool.min_size >= 1
    assert s.db.timeouts.connect_timeout_ms >= 0
    assert s.db.retry.max_retries >= 0
    # logging.yaml 基础字段
    assert s.logging.level
    assert s.logging.rotation.backup_count >= 0
    assert s.logging.formatting.timestamp_format
    # ingest.yaml 基础字段
    assert s.ingest.csv.encoding.lower() in ("utf-8", "utf8")
    assert s.ingest.batch.size > 0
    assert s.ingest.error_handling.max_errors_per_file >= 0
    assert s.ingest.performance.read_buffer_size > 0
    # 背压配置
    assert s.ingest.backpressure.thresholds.p95_ms > 0


def test_env_overrides_for_ingest(tmp_path):
    cdir = tmp_path / "c"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "ingest.yaml").write_text("workers: 2\ncommit_interval: 100\np95_window: 5\n", encoding="utf-8")
    (cdir / "logging.yaml").write_text("level: INFO\n", encoding="utf-8")
    (cdir / "database.yaml").write_text("host: localhost\nname: db\nuser: postgres\n", encoding="utf-8")

    import os

    os.environ["INGEST_WORKERS"] = "9"
    os.environ["INGEST_COMMIT_INTERVAL"] = "12345"
    os.environ["INGEST_P95_WINDOW"] = "7"
    try:
        s = load_settings(cdir)
        assert s.ingest.workers == 9
        assert s.ingest.commit_interval == 12345
        assert s.ingest.p95_window == 7
    finally:
        os.environ.pop("INGEST_WORKERS", None)
        os.environ.pop("INGEST_COMMIT_INTERVAL", None)
        os.environ.pop("INGEST_P95_WINDOW", None)


def test_load_settings_with_sources(tmp_path):
    cdir = tmp_path / "c2"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "ingest.yaml").write_text("workers: 6\ncommit_interval: 1000000\n", encoding="utf-8")
    (cdir / "logging.yaml").write_text("level: DEBUG\nformat: json\n", encoding="utf-8")
    (cdir / "database.yaml").write_text("host: localhost\nname: db\nuser: postgres\n", encoding="utf-8")
    s, sources = load_settings_with_sources(cdir)
    assert isinstance(s, Settings)
    assert isinstance(sources, dict)
    assert sources.get("ingest", {}).get("workers") in ("YAML", "ENV", "DEFAULT")

