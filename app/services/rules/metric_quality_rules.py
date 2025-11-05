from __future__ import annotations

from typing import Any, Dict, Optional

from app.adapters.db.gateway import get_conn
import logging

_act = logging.getLogger(__name__)


def compute_metric_quality_rules(
    settings,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    基于自动基线(metric_rule_auto_baseline)填充/补全 metric_quality_rules：
    - 若不存在对应(station_id,device_id,metric_id)的规则，则按基线插入一条（remark=seed:auto_baseline）
    - 若已存在，则仅在相应字段为 NULL 时用基线值补全（不覆盖人工配置）
    - 默认计算所有设备；可按站/设备过滤
    返回：执行摘要（写入行数/更新行数/样例）
    """
    _act.info(
        "[流程-开始] [质量规则生成]",
        extra={"extra_data": {"station_id": station_id, "device_id": device_id}},
    )

    result: Dict[str, Any] = {
        "filters": {"station_id": station_id, "device_id": device_id},
        "inserted": 0,
        "updated": 0,
        "samples": [],
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            _act.info("[数据库-执行] [规则行插入]")
            # 插入缺失行（与迁移过程逻辑一致，避免重复）
            cur.execute(
                """
                WITH base AS (
                  SELECT b.station_id, b.device_id, b.metric_id,
                         b.p05, b.p95, b.spike_abs, b.roc_abs, b.roc_ratio,
                         b.flatline_eps, b.flatline_delta
                  FROM public.metric_rule_auto_baseline b
                  WHERE (%s::bigint IS NULL OR b.station_id = %s::bigint)
                    AND (%s::bigint IS NULL OR b.device_id  = %s::bigint)
                ), missing AS (
                  SELECT base.*
                  FROM base
                  LEFT JOIN public.metric_quality_rules r
                    ON r.station_id IS NOT DISTINCT FROM base.station_id
                   AND r.device_id  IS NOT DISTINCT FROM base.device_id
                   AND r.metric_id  IS NOT DISTINCT FROM base.metric_id
                  WHERE r.metric_id IS NULL
                )
                INSERT INTO public.metric_quality_rules(
                  station_id, device_id, metric_id,
                  value_min, value_max,
                  spike_abs, roc_abs, roc_ratio,
                  flatline_eps, flatline_delta,
                  remark
                )
                SELECT station_id, device_id, metric_id,
                       p05, p95, spike_abs, roc_abs, roc_ratio, flatline_eps, flatline_delta,
                       'seed:auto_baseline'
                FROM missing
                RETURNING metric_id
                """,
                (station_id, station_id, device_id, device_id),
            )
            inserted_rows = cur.rowcount or 0
            _act.info(
                "[数据库-执行] [规则行插入完成]",
                extra={"extra_data": {"inserted_rows": inserted_rows}},
            )

            # 仅在现有规则字段为 NULL 时进行补全（不覆盖人工设置）
            _act.info("[数据库-执行] [NULL字段补全]")
            cur.execute(
                """
                WITH base AS (
                  SELECT b.station_id, b.device_id, b.metric_id,
                         b.p05, b.p95, b.spike_abs, b.roc_abs, b.roc_ratio,
                         b.flatline_eps, b.flatline_delta
                  FROM public.metric_rule_auto_baseline b
                  WHERE (%s::bigint IS NULL OR b.station_id = %s::bigint)
                    AND (%s::bigint IS NULL OR b.device_id  = %s::bigint)
                )
                UPDATE public.metric_quality_rules r
                SET value_min = COALESCE(r.value_min, base.p05),
                    value_max = COALESCE(r.value_max, base.p95),
                    spike_abs = COALESCE(r.spike_abs, base.spike_abs),
                    roc_abs   = COALESCE(r.roc_abs,   base.roc_abs),
                    roc_ratio = COALESCE(r.roc_ratio, base.roc_ratio),
                    flatline_eps   = COALESCE(r.flatline_eps,   base.flatline_eps),
                    flatline_delta = COALESCE(r.flatline_delta, base.flatline_delta)
                FROM base
                WHERE r.metric_id = base.metric_id
                  AND r.station_id IS NOT DISTINCT FROM base.station_id
                  AND r.device_id  IS NOT DISTINCT FROM base.device_id
                  AND (
                    r.value_min IS NULL OR r.value_max IS NULL OR
                    r.spike_abs IS NULL OR r.roc_abs IS NULL OR r.roc_ratio IS NULL OR
                    r.flatline_eps IS NULL OR r.flatline_delta IS NULL
                  )
                """,
                (station_id, station_id, device_id, device_id),
            )
            updated_rows = cur.rowcount or 0
            _act.info(
                "[数据库-执行] [NULL字段补全完成]",
                extra={"extra_data": {"updated_rows": updated_rows}},
            )

            conn.commit()
            _act.info("[数据库-事务] [事务提交成功]")

        # 样例输出
        _act.info("[数据库-查询] [样例数据查询]")
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT station_id, device_id, metric_id,
                       value_min, value_max, spike_abs, roc_abs, roc_ratio,
                       flatline_eps, flatline_delta
                FROM public.metric_quality_rules
                WHERE (%s::bigint IS NULL OR station_id=%s::bigint)
                  AND (%s::bigint IS NULL OR device_id=%s::bigint)
                ORDER BY station_id NULLS FIRST, device_id NULLS FIRST, metric_id
                LIMIT 5
                """,
                (station_id, station_id, device_id, device_id),
            )
            rows = cur.fetchall() or []
            samples = [
                {
                    "station_id": r[0],
                    "device_id": r[1],
                    "metric_id": r[2],
                    "value_min": float(r[3]) if r[3] is not None else None,
                    "value_max": float(r[4]) if r[4] is not None else None,
                    "spike_abs": float(r[5]) if r[5] is not None else None,
                    "roc_abs": float(r[6]) if r[6] is not None else None,
                    "roc_ratio": float(r[7]) if r[7] is not None else None,
                    "flatline_eps": float(r[8]) if r[8] is not None else None,
                    "flatline_delta": float(r[9]) if r[9] is not None else None,
                }
                for r in rows
            ]

        # 提交事务，确保数据持久化
        conn.commit()

    result.update(
        {"inserted": inserted_rows, "updated": updated_rows, "samples": samples}
    )

    _act.info(
        "[流程-完成] [质量规则生成]",
        extra={
            "extra_data": {
                "inserted": inserted_rows,
                "updated": updated_rows,
                "samples_count": len(samples),
            }
        },
    )

    return result
