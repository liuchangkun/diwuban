from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

SQL_PATH = Path("scripts/dev/seed_from_mapping.sql")


def run() -> int:
    settings = load_settings(Path("configs"))
    sql = SQL_PATH.read_text(encoding="utf-8")
    # 仅执行 dim_mapping_items 的 INSERT 语句，避免碰触 dim_metric_config 等已存在数据
    stmts: list[str] = []
    for part in sql.split(";"):
        s = part.strip()
        if not s or s.startswith("--"):
            continue
        ss = s.replace("\n", " ").replace("\r", " ").strip()
        if "INSERT INTO public.dim_mapping_items" in ss:
            stmts.append(s)
    if not stmts:
        print("[SEED] no mapping_items statements found")
        return 0
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            for st in stmts:
                cur.execute(st)
        conn.commit()
    print(f"[SEED] executed {len(stmts)} mapping statements into dim_mapping_items")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
