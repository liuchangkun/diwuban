from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# ensure repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.services.quality.mark_window import mark_quality_window


def _parse_codes(arg: str | None) -> list[int] | None:
    if arg is None or not arg.strip():
        return None
    if arg.strip().upper() in {"ALL", "*"}:
        return None
    return [int(x) for x in arg.split(",") if x.strip()]


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: python scripts/dev/run_mark_with_diag_dump.py <wsZ> <weZ> <device_id|None> [diag_level=trace] [codes_csv|ALL]"
        )
        return 2

    ws = sys.argv[1]
    we = sys.argv[2]
    device_id = None if sys.argv[3] in ("", "None", "null") else int(sys.argv[3])
    diag_level = sys.argv[4] if len(sys.argv) >= 5 and sys.argv[4].strip() else "trace"
    codes = _parse_codes(sys.argv[5] if len(sys.argv) >= 6 else None)

    s = load_settings(Path("configs"))
    # 初始化日志（确保写入文件并按路由分流）
    try:
        init_logging("configs", s.system.timezone.default)
    except Exception:
        pass

    # 执行打标（带诊断包装）
    mark_res = mark_quality_window(
        settings=s,
        start=ws,
        end=we,
        station_id=None,
        device_id=device_id,
        codes=codes,
        diag_level=diag_level,
    )
    run_id = mark_res.get("run_id")
    # 注入上下文，便于跨文件与多日志源关联 run_id
    try:
        from app.core.logging.setup import set_context  # local import

        if run_id:
            set_context(
                request_id=run_id, trace_id=run_id, user_id="system", tenant="diag"
            )
    except Exception:
        pass

    # 从数据库读取诊断记录，并写入 anomaly 日志（便于在文件中留痕、归档）
    anom = logging.getLogger("anomaly")

    diag_rows: list[dict] = []
    prof_rows: list[dict] = []

    with get_conn(s) as conn:
        with conn.cursor() as cur:
            # 读取诊断日志
            cur.execute(
                """
                SELECT id, created_at, window_start, window_end,
                       station_id, device_id, stage, level, message, detail, diag_level, run_id
                FROM public.quality_diagnosis_log
                WHERE run_id = %s AND window_start = %s AND window_end = %s
                ORDER BY id ASC
                """,
                (run_id, ws, we),
            )
            for r in cur.fetchall():
                row = {
                    "id": r[0],
                    "created_at": r[1].isoformat() if r[1] else None,
                    "window_start": r[2].isoformat() if r[2] else None,
                    "window_end": r[3].isoformat() if r[3] else None,
                    "station_id": int(r[4]) if r[4] is not None else None,
                    "device_id": int(r[5]) if r[5] is not None else None,
                    "stage": r[6],
                    "level": r[7],
                    "message": r[8],
                    "detail": r[9],
                    "diag_level": r[10],
                    "run_id": r[11],
                }
                diag_rows.append(row)

        # 读取规则命中摘要（来自 profile 日志）
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT split_part(stage, '_', 2)::int AS code, SUM(rows_affected)::bigint AS cnt
                FROM public.quality_profile_log
                WHERE window_start >= %s AND window_end <= %s AND stage LIKE 'update_%%'
                GROUP BY split_part(stage, '_', 2)
                ORDER BY code
                """,
                (ws, we),
            )
            for r in cur.fetchall():
                prof_rows.append({"code": int(r[0]), "rows": int(r[1])})

    # 脚本不再向 anomaly 文件写入任何行，避免与服务层重复；仅在控制台输出 JSON 摘要

    # 控制台输出 JSON 摘要
    print(
        json.dumps(
            {
                "window": {"start": ws, "end": we, "device_id": device_id},
                "diag_level": diag_level,
                "run_id": run_id,
                "diag_rows": diag_rows,
                "rule_summary": prof_rows,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
