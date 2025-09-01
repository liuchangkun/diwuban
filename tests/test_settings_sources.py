from __future__ import annotations

# import os  # 未使用，移除以通过 ruff F401
from pathlib import Path

from app.core.config.loader import load_settings_with_sources


def test_load_settings_with_sources_env_over_yaml(tmp_path: Path, monkeypatch):
    # 准备临时配置目录
    cdir = tmp_path / "configs"
    cdir.mkdir(parents=True, exist_ok=True)

    # YAML: logging.level=DEBUG, format=json; ingest.workers=9
    (cdir / "logging.yaml").write_text(
        """
level: DEBUG
format: json
routing: by_run
sampling:
  loop_log_every_n: 777
        """.strip(),
        encoding="utf-8",
    )
    (cdir / "ingest.yaml").write_text(
        """
workers: 9
commit_interval: 123
p95_window: 33
        """.strip(),
        encoding="utf-8",
    )
    (cdir / "database.yaml").write_text(
        """
host: localhost
name: pump_station_optimization
user: postgres
dsn_read: null
dsn_write: null
        """.strip(),
        encoding="utf-8",
    )

    # ENV 覆盖 YAML：LOG_LEVEL=WARNING，INGEST_WORKERS=12
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("INGEST_WORKERS", "12")

    settings, sources = load_settings_with_sources(cdir)

    # 值断言：根据新规范，logging 仅来自 YAML，不接受 ENV 覆盖；ingest 仍允许 ENV 覆盖
    assert settings.logging.level == "DEBUG"  # YAML 值
    assert settings.logging.format == "json"
    assert settings.ingest.workers == 12  # ENV 覆盖 YAML
    assert settings.ingest.commit_interval == 123
    assert settings.ingest.p95_window == 33

    # 来源断言
    assert sources["logging"]["level"] == "YAML"
    assert sources["logging"]["format"] == "YAML"
    assert sources["ingest"]["workers"] == "ENV"
    assert sources["ingest"]["commit_interval"] == "YAML"
    assert sources["ingest"]["p95_window"] == "YAML"

    # base_dir 固定为 data（不可覆盖），来源应标注 DEFAULT
    assert settings.ingest.base_dir == "data"
    assert sources["ingest"]["base_dir"] == "DEFAULT"
