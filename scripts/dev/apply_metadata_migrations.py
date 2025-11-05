from __future__ import annotations

"""
应用元数据相关迁移与种子（017~021），用于方案A落地：
- 017_create_dim_metric_metadata.sql
- 018_create_dim_metric_metadata_override.sql
- 019_create_dim_device_capabilities.sql
- 020_create_v_effective_metric_metadata.sql
- 021_seed_dim_metric_metadata.sql

安全说明：
- 仅 DDL/只增不改，幂等 CREATE/VIEW/INSERT 缺失即补
- DEV 环境执行；PROD 前请审阅
"""
from pathlib import Path
from typing import Sequence

import sys

# 确保可导入仓库根下的 app 包
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


SQL_FILES: Sequence[str] = (
    "scripts/sql/migrations/017_create_dim_metric_metadata.sql",
    "scripts/sql/migrations/018_create_dim_metric_metadata_override.sql",
    "scripts/sql/migrations/019_create_dim_device_capabilities.sql",
    "scripts/sql/migrations/020_create_v_effective_metric_metadata.sql",
    "scripts/sql/migrations/021_seed_dim_metric_metadata.sql",
)


def main() -> None:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            for f in SQL_FILES:
                p = Path(f)
                if not p.exists():
                    print(f"[SKIP] {f} 不存在")
                    continue
                sql = p.read_text(encoding="utf-8")
                print(f"[EXEC] {f}")
                cur.execute(sql)
        conn.commit()
    print("[OK] 元数据迁移与种子执行完成")


if __name__ == "__main__":
    main()
