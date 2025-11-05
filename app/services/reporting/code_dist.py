from __future__ import annotations

import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings
from app.core.time_utils import format_for_display

import logging

_act = logging.getLogger(__name__)


# 统一对外时间格式：使用 app.core.time_utils.format_for_display
# 已删除重复的 _fmt_local 函数，直接使用统一的时间格式化函数

def _parse_code_from_stage(stage: str) -> int | None:
    # stage 形如 'update_501'，解析出 501
    try:
        if not stage:
            return None
        if stage.startswith("update_"):
            return int(stage.split("_")[-1])
    except Exception:
        return None
    return None


def export_window_code_distribution(
    settings: Settings,
    start_iso: str,
    end_iso: str,
    out_dir: Path | None = None,
) -> Dict[str, Any]:
    """按窗口导出质量码分布（JSON + CSV）。
    - 源：fact_measurements（窗口内，quality_status>0）
    - 输出：reports/quality_code_dist.window.json + .csv
    返回：包含 paths 与统计对象
    """
    _act.info(
        "[流程-开始] [质量码分布导出]",
        extra={"extra_data": {"start": start_iso, "end": end_iso}},
    )

    s = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    e = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    out_dir = out_dir or Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    out: Dict[str, Any] = {"window": {"start": format_for_display(s, settings), "end": format_for_display(e, settings)}}

    rows: List[Tuple[int, int, str]] = []  # (code, cnt, label)
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT f.quality_status AS code,
                       COUNT(*)::bigint AS cnt,
                       COALESCE(q.label_zh, q.description, '') AS label
                FROM public.fact_measurements f
                LEFT JOIN public.quality_code_dict q ON q.code = f.quality_status
                WHERE f.ts_bucket >= %s AND f.ts_bucket < %s AND COALESCE(f.quality_status,0) > 0
                GROUP BY f.quality_status, q.label_zh, q.description
                ORDER BY f.quality_status
                """,
                (s, e),
            )
            for r in cur.fetchall():
                rows.append((int(r[0]), int(r[1]), str(r[2] or "")))

    out["distribution"] = [
        {"code": c, "count": n, "label": lbl} for (c, n, lbl) in rows
    ]

    # 写 JSON
    json_path = out_dir / "quality_code_dist.window.json"
    json_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # 写 CSV
    csv_path = out_dir / "quality_code_dist.window.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "label", "count"])  # 列标题
        for c, n, lbl in rows:
            w.writerow([c, lbl, n])

    return {"json": str(json_path), "csv": str(csv_path), "data": out}


def export_recent_code_distribution(
    settings: Settings,
    hours_24: bool = True,
    days_7: bool = True,
    out_dir: Path | None = None,
) -> Dict[str, Any]:
    """基于 quality_profile_log 的近 24h / 7d 质量码命中分布（JSON）。
    - 源：quality_profile_log（stage like 'update_XXX'）
    - 聚合：sum(rows_affected) 按 code 汇总
    - 输出：reports/quality_code_dist.recent.json
    """
    out_dir = out_dir or Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    res: Dict[str, Any] = {}
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            if hours_24:
                cur.execute(
                    """
                    SELECT stage, SUM(rows_affected)::bigint AS cnt
                    FROM public.quality_profile_log
                    WHERE window_end >= now() - interval '24 hours' AND stage LIKE 'update_%'
                    GROUP BY stage
                    """
                )
                rows_24 = cur.fetchall()
                dist_24: Dict[str, int] = {}
                for st, cnt in rows_24:
                    code = _parse_code_from_stage(st)
                    if code is not None:
                        dist_24[str(code)] = int(cnt or 0)
                res["last_24h"] = dist_24

            if days_7:
                cur.execute(
                    """
                    SELECT stage, SUM(rows_affected)::bigint AS cnt
                    FROM public.quality_profile_log
                    WHERE window_end >= now() - interval '7 days' AND stage LIKE 'update_%'
                    GROUP BY stage
                    """
                )
                rows_7 = cur.fetchall()
                dist_7: Dict[str, int] = {}
                for st, cnt in rows_7:
                    code = _parse_code_from_stage(st)
                    if code is not None:
                        dist_7[str(code)] = int(cnt or 0)
                res["last_7d"] = dist_7

    json_path = out_dir / "quality_code_dist.recent.json"
    json_path.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"json": str(json_path), "data": res}

