from __future__ import annotations

"""
source_hint 生成（ingest.source_hint）
- v2 格式：data/<rel>|batch=<run_id>|ver=2（始终使用正斜杠）
- 允许回退为文件名；run_id 优先来自 runtime 注入，否则生成当前 UTC 时间戳
"""


from datetime import datetime
from pathlib import Path

from app.core.config.loader import Settings


def make_source_hint(settings: Settings, base_dir: Path, csv_path: Path) -> str:
    """生成 source_hint v2：data/<rel>|batch=<run_id>|ver=2。
    - <rel>：相对 data/ 路径（统一正斜杠），若失败回退为文件名
    - run_id：优先取 runtime 注入的 _runtime_run_id；若无则取当前 UTC 时间戳
    - 当 enhanced_source_hint 为 False 时，降级为文件名
    """
    if not settings.ingest.enhanced_source_hint:
        return csv_path.name
    # 强制 data/ 相对路径
    rel_path: Path | str

    try:
        rel_path = csv_path.relative_to(base_dir)
    except Exception:
        rel_path = csv_path.name  # 回退为文件名（字符串）
    # 统一转为字符串并使用正斜杠
    rel: str
    if isinstance(rel_path, Path):
        rel = rel_path.as_posix()
    else:
        rel = str(rel_path).replace("\\", "/")
    run_id = getattr(settings.ingest, "_runtime_run_id", None) or getattr(
        settings, "_runtime_run_id", None
    )
    if not run_id:
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"data/{rel}|batch={run_id}|ver=2"
