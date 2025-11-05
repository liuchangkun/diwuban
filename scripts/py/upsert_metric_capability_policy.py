# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import List, Dict, Tuple

import sys
from pathlib import Path

# ensure project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db import get_connection, init_database

POLICY_ROWS: List[Dict[str, str]] = [
    # metric_key, acquisition_status(可以/可能/不能), compute_flag(需要/不需要)
    {"metric_key": "pump_flow_rate", "acquisition_status": "不能", "compute_flag": "需要"},
    {"metric_key": "pump_efficiency", "acquisition_status": "不能", "compute_flag": "需要"},
    {"metric_key": "pump_speed", "acquisition_status": "不能", "compute_flag": "需要"},
    {"metric_key": "pump_torque", "acquisition_status": "不能", "compute_flag": "需要"},
    {"metric_key": "main_pipeline_inlet_pressure", "acquisition_status": "可能", "compute_flag": "需要"},
    {"metric_key": "main_pipeline_outlet_pressure", "acquisition_status": "可能", "compute_flag": "需要"},
    {"metric_key": "pump_cumulative_flow", "acquisition_status": "可能", "compute_flag": "需要"},
]


def upsert_policy() -> Tuple[int, int]:
    project_root = Path(__file__).resolve().parents[2]
    settings = load_settings(project_root / "configs")
    init_database(settings)

    inserted = 0
    updated = 0
    now = datetime.now(timezone.utc)

    sql_on_conflict = (
        "INSERT INTO public.metric_capability_policy(metric_key, acquisition_status, compute_flag, updated_at, updated_by) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (metric_key) DO UPDATE SET acquisition_status = EXCLUDED.acquisition_status, compute_flag = EXCLUDED.compute_flag, updated_at = EXCLUDED.updated_at, updated_by = EXCLUDED.updated_by"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            # check if ON CONFLICT is supported by unique index
            try:
                for row in POLICY_ROWS:
                    cur.execute(
                        sql_on_conflict,
                        (
                            row["metric_key"],
                            row["acquisition_status"],
                            row["compute_flag"],
                            now,
                            "augment-agent",
                        ),
                    )
                conn.commit()
                # we cannot easily distinguish insert/update counts per-row here; read back
            except Exception:
                conn.rollback()
                # Fallback: UPDATE then INSERT if not exists
                for row in POLICY_ROWS:
                    cur.execute(
                        "UPDATE public.metric_capability_policy SET acquisition_status=%s, compute_flag=%s, updated_at=%s, updated_by=%s WHERE metric_key=%s",
                        (
                            row["acquisition_status"],
                            row["compute_flag"],
                            now,
                            "augment-agent",
                            row["metric_key"],
                        ),
                    )
                    if cur.rowcount == 0:
                        cur.execute(
                            "INSERT INTO public.metric_capability_policy(metric_key, acquisition_status, compute_flag, updated_at, updated_by) VALUES (%s,%s,%s,%s,%s)",
                            (
                                row["metric_key"],
                                row["acquisition_status"],
                                row["compute_flag"],
                                now,
                                "augment-agent",
                            ),
                        )
                conn.commit()

    # Return counts by re-reading rows
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM public.metric_capability_policy WHERE metric_key = ANY(%s)",
                ([r["metric_key"] for r in POLICY_ROWS],),
            )
            total = int(cur.fetchone()[0])
    return total, len(POLICY_ROWS)


if __name__ == "__main__":
    total, expected = upsert_policy()
    print(f"Upsert metric_capability_policy done. rows_present={total}/{expected}")

