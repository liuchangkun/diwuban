#!/usr/bin/env python3
"""
CI 配置健全性检查（无第三方依赖）
- py_compile 关键模块
- load_settings 从仓库 configs/ 加载并做最小字段校验
"""
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# 1) 关键模块语法检查
TARGETS = [
    ROOT / "app" / "core" / "config" / "loader.py",
    ROOT / "app" / "adapters" / "logging" / "init.py",
    ROOT / "app" / "adapters" / "db" / "gateway.py",
    ROOT / "app" / "services" / "ingest" / "backpressure.py",
    ROOT / "app" / "services" / "ingest" / "copy_workers.py",
    ROOT / "app" / "adapters" / "fs" / "reader.py",
]
for t in TARGETS:
    py_compile.compile(str(t), doraise=True)
print("[CONFIG_SANITY] py_compile: OK")

# 2) 最小化加载与字段断言（不脱敏打印）
from app.core.config.loader import load_settings  # noqa: E402

cfg_dir = ROOT / "configs"
s = load_settings(cfg_dir)
# 数据库
assert s.db.host and isinstance(s.db.host, str)
assert s.db.pool.min_size >= 0
assert s.db.timeouts.connect_timeout_ms >= 0
# 日志
assert s.logging.level and isinstance(s.logging.level, str)
assert s.logging.format in ("json", "text")
# 导入
assert s.ingest.csv.encoding
assert s.ingest.batch.size > 0
assert s.ingest.error_handling.max_errors_per_file >= 0
assert s.ingest.performance.read_buffer_size > 0
assert s.ingest.backpressure.thresholds.p95_ms > 0

print("[CONFIG_SANITY] load_settings(configs): OK")
print("[CONFIG_SANITY] SUMMARY:")
print({
    "db.host": s.db.host,
    "logging.level": s.logging.level,
    "ingest.batch.size": s.ingest.batch.size,
    "ingest.backpressure.p95_ms": s.ingest.backpressure.thresholds.p95_ms,
})

sys.exit(0)

