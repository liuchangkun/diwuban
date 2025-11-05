from __future__ import annotations

from pathlib import Path
import re
from typing import List

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn

ROOT = Path(".")
F_VFAST = ROOT / "scripts/sql/migrations/036_create_sp_mark_quality_window_vfast.sql"
F_STD = ROOT / "scripts/sql/migrations/033_update_sp_mark_quality_window.sql"

CODES = [
    751,
    701,
    702,
    401,
    402,
    403,
    201,
    202,
    503,
    141,
    101,
    102,
    111,
    112,
    131,
    132,
    121,
]


def add_param_signature(sql: str) -> str:
    # 若已包含 p_codes 参数则跳过
    if re.search(r"IN\s+p_codes\s+int\[\]", sql, flags=re.IGNORECASE):
        return sql
    pattern = r"\)\nLANGUAGE plpgsql"
    replacement = ",\n  IN p_codes int[] DEFAULT NULL\n)\nLANGUAGE plpgsql"
    return re.sub(pattern, replacement, sql, count=1)


def patch_update_blocks(sql: str, codes: List[int]) -> str:
    # For each code, find occurrences of "SET quality_status=<code>" and patch the WHERE clause
    for code in codes:
        idx = 0
        while True:
            m = re.search(
                rf"SET\s+quality_status\s*=\s*{code}\s*,",
                sql[idx:],
                flags=re.IGNORECASE,
            )
            if not m:
                break
            start = idx + m.start()
            # Find WHERE after this match
            m_where = re.search(r"\bWHERE\b", sql[start:], flags=re.IGNORECASE)
            if not m_where:
                idx = start + 1
                continue
            where_pos = start + m_where.start()
            # Find semicolon ending this UPDATE statement
            m_end = re.search(r";", sql[where_pos:])
            if not m_end:
                idx = start + 1
                continue
            end_pos = where_pos + m_end.start()
            # Insert condition before semicolon
            insert_text = f" AND (p_codes IS NULL OR {code} = ANY(p_codes))"
            sql = sql[:end_pos] + insert_text + sql[end_pos:]
            idx = end_pos + len(insert_text)
    return sql


def build_and_apply(file_path: Path) -> int:
    src = file_path.read_text(encoding="utf-8")
    # Only operate on CREATE OR REPLACE PROCEDURE bodies
    if (
        "CREATE OR REPLACE PROCEDURE public.sp_mark_quality_window" not in src
        and "CREATE OR REPLACE PROCEDURE public.sp_mark_quality_window_vfast" not in src
    ):
        raise RuntimeError(f"Unexpected file content: {file_path}")
    patched = add_param_signature(src)
    patched = patch_update_blocks(patched, CODES)

    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(patched)
        conn.commit()
    return len(patched)


def main() -> None:
    sizes = {}
    for fp in (F_STD, F_VFAST):
        sizes[fp.name] = build_and_apply(fp)
    print({"updated_procedures": sizes})


if __name__ == "__main__":
    main()
