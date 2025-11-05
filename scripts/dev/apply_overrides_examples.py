from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
from app.adapters.db.transaction import transaction
import json


def main():
    s = load_settings(Path('configs'))
    ops = []
    with get_conn(s) as conn:
        with transaction(conn):
            with conn.cursor() as cur:
                # 设备9：voltage 覆盖
                cur.execute(
                    """
                    DELETE FROM public.dim_metric_metadata_override
                    WHERE metric_id = (SELECT id FROM public.dim_metric_config WHERE metric_key=%s)
                      AND device_id = %s AND station_id IS NULL
                    """,
                    ("voltage", 9),
                )
                ops.append({"delete_voltage_device9": cur.rowcount})
                cur.execute(
                    """
                    INSERT INTO public.dim_metric_metadata_override
                        (metric_id, device_id, station_id, resolution, phys_min, phys_max, remark)
                    SELECT id, %s, NULL, %s, %s, %s, %s
                    FROM public.dim_metric_config WHERE metric_key=%s
                    """,
                    (9, 0.1, 0, 1000, "设备9电压-分辨率0.1/边界0~1000", "voltage"),
                )
                ops.append({"insert_voltage_device9": cur.rowcount})

                # 站点2：current 覆盖
                cur.execute(
                    """
                    DELETE FROM public.dim_metric_metadata_override
                    WHERE metric_id = (SELECT id FROM public.dim_metric_config WHERE metric_key=%s)
                      AND station_id = %s AND device_id IS NULL
                    """,
                    ("current", 2),
                )
                ops.append({"delete_current_station2": cur.rowcount})
                cur.execute(
                    """
                    INSERT INTO public.dim_metric_metadata_override
                        (metric_id, device_id, station_id, resolution, phys_min, phys_max, remark)
                    SELECT id, NULL, %s, %s, %s, %s, %s
                    FROM public.dim_metric_config WHERE metric_key=%s
                    """,
                    (2, 1.0, 0, 5000, "站点2电流-分辨率1.0/边界0~5000", "current"),
                )
                ops.append({"insert_current_station2": cur.rowcount})

                # 全局：pf 覆盖
                cur.execute(
                    """
                    DELETE FROM public.dim_metric_metadata_override
                    WHERE metric_id = (SELECT id FROM public.dim_metric_config WHERE metric_key=%s)
                      AND station_id IS NULL AND device_id IS NULL
                    """,
                    ("pf",),
                )
                ops.append({"delete_pf_global": cur.rowcount})
                cur.execute(
                    """
                    INSERT INTO public.dim_metric_metadata_override
                        (metric_id, device_id, station_id, resolution, phys_min, phys_max, remark)
                    SELECT id, NULL, NULL, %s, %s, %s, %s
                    FROM public.dim_metric_config WHERE metric_key=%s
                    """,
                    (0.01, 0, 1, "功率因数-全局分辨率0.01/边界0~1", "pf"),
                )
                ops.append({"insert_pf_global": cur.rowcount})

                # 查询确认
                cur.execute(
                    """
                    SELECT c.metric_key, o.device_id, o.station_id, o.resolution, o.phys_min, o.phys_max, o.remark
                    FROM public.dim_metric_metadata_override o
                    JOIN public.dim_metric_config c ON c.id = o.metric_id
                    WHERE (c.metric_key='voltage' AND o.device_id=9)
                       OR (c.metric_key='current' AND o.station_id=2 AND o.device_id IS NULL)
                       OR (c.metric_key='pf' AND o.station_id IS NULL AND o.device_id IS NULL)
                    ORDER BY c.metric_key
                    """
                )
                rows = cur.fetchall()
            # 事务自动提交

    print(json.dumps({"ok": True, "ops": ops, "overrides": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

