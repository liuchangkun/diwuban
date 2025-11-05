from __future__ import annotations

from pathlib import Path
from typing import Set

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.adapters.db.transaction import transaction

SQL_PATH = Path("scripts/sql/proposals/2025-09-17_quality_code_dict_extend.sql")

NEW_CODES: Set[int] = {
    102, 141, 202, 300, 301, 302, 303, 402, 403, 503, 601, 602, 603, 702, 741, 750, 801, 802, 803
}


def main() -> None:
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"SQL 文件不存在: {SQL_PATH}")

    sql_text = SQL_PATH.read_text(encoding="utf-8")

    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with transaction(conn):
            with conn.cursor() as cur:
                # 执行 SQL（文件内含 BEGIN/COMMIT，幂等 ON CONFLICT DO NOTHING）
                cur.execute(sql_text)
                # 事务自动提交

    # 执行完毕后做一次只读核验
    inserted = verify()
    print({
        "added_codes": sorted(inserted),
        "count_added": len(inserted),
    })


def verify() -> set[int]:
    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT code FROM public.quality_code_dict ORDER BY code")
            have = {int(r[0]) for r in cur.fetchall()}
    return {c for c in NEW_CODES if c in have}


if __name__ == "__main__":
    main()

