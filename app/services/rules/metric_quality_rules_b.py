from __future__ import annotations

from typing import Any, Dict, Optional

from app.adapters.db.gateway import get_conn
import logging

_act = logging.getLogger(__name__)


def compute_metric_quality_rules_shadow(
    settings,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
    method: str = "stl_residual",
    version: str = "vB_shadow",
) -> Dict[str, Any]:
    """
    方案B影子：从 metric_rule_auto_baseline_shadow 生成质量规则影子
    - 不影响正式表
    """
    _act.info(
        "[流程-开始] [质量规则生成B]",
        extra={
            "extra_data": {
                "station_id": station_id,
                "device_id": device_id,
                "method": method,
                "version": version,
            }
        },
    )

    result: Dict[str, Any] = {
        "filters": {"station_id": station_id, "device_id": device_id},
        "method": method,
        "version": version,
        "inserted": 0,
        "samples": [],
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            _act.info("[数据库-执行] [质量规则生成]")
            cur.execute(
                """
                INSERT INTO public.metric_quality_rules_shadow(
                  station_id, device_id, metric_id, method, version,
                  value_min, value_max, spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta, computed_at, remark
                )
                SELECT b.station_id, b.device_id, b.metric_id, %s, %s,
                       b.p05, b.p95, b.spike_abs, b.roc_abs, b.roc_ratio, b.flatline_eps, b.flatline_delta, now(), 'seed:auto_baseline_shadow'
                FROM public.metric_rule_auto_baseline_shadow b
                WHERE (%s::bigint IS NULL OR b.station_id = %s::bigint)
                  AND (%s::bigint IS NULL OR b.device_id  = %s::bigint)
                  AND b.method = %s AND b.version = %s
                ON CONFLICT (station_id, device_id, metric_id, method, version) DO UPDATE
                  SET value_min=EXCLUDED.value_min, value_max=EXCLUDED.value_max,
                      spike_abs=EXCLUDED.spike_abs, roc_abs=EXCLUDED.roc_abs, roc_ratio=EXCLUDED.roc_ratio,
                      flatline_eps=EXCLUDED.flatline_eps, flatline_delta=EXCLUDED.flatline_delta, computed_at=now(), remark=EXCLUDED.remark
                RETURNING station_id, device_id, metric_id
                """,
                (
                    method,
                    version,
                    station_id,
                    station_id,
                    device_id,
                    device_id,
                    method,
                    version,
                ),
            )
            result["inserted"] = cur.rowcount or 0
            _act.info(
                "[数据库-执行] [质量规则生成完成]",
                extra={"extra_data": {"inserted": result["inserted"]}},
            )

        _act.info("[数据库-查询] [样例数据查询]")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT station_id, device_id, metric_id, value_min, value_max, flatline_eps
                FROM public.metric_quality_rules_shadow
                WHERE method=%s AND version=%s
                ORDER BY station_id NULLS FIRST, device_id NULLS FIRST, metric_id
                LIMIT 5
                """,
                (method, version),
            )
            rows = cur.fetchall() or []
            for r in rows:
                if len(result["samples"]) < 5:
                    result["samples"].append(
                        {
                            "station_id": r[0],
                            "device_id": r[1],
                            "metric_id": r[2],
                            "value_min": float(r[3]) if r[3] is not None else None,
                            "value_max": float(r[4]) if r[4] is not None else None,
                            "flatline_eps": float(r[5]) if r[5] is not None else None,
                        }
                    )

        # 提交事务，确保数据持久化
        conn.commit()

    _act.info(
        "[流程-完成] [质量规则生成B]",
        extra={
            "extra_data": {
                "inserted": result["inserted"],
                "samples_count": len(result["samples"]),
            }
        },
    )

    return result

