from __future__ import annotations

"""
插入示例阈值到 public.device_running_thresholds（全部设备）。
- 选择规则：dim_devices 中排除 type='main_pipeline' 的所有设备
- 阈值：仅启用电流 I，i_on=10, i_off=5；其余关闭；grace_hold_secs=30；min_run/stop=10；smoothing=5
- 幂等：ON CONFLICT(device_id) DO UPDATE
"""
from pathlib import Path
from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn


def main() -> None:
    s = load_settings(Path("configs"))
    with get_conn(s) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT d.id
                FROM public.dim_devices d
                WHERE COALESCE(NULLIF(d.type,''),'') <> 'main_pipeline'
                ORDER BY d.id
                """
            )
            dids = [int(r[0]) for r in (cur.fetchall() or [])]
            if not dids:
                print("NO_DEVICES")
                return
            sql = (
                "INSERT INTO public.device_running_thresholds ("
                "device_id, enable_i, enable_p, enable_f, "
                "i_on, i_off, p_on, p_off, f_on, f_off, "
                "grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs, updated_by"
                ") VALUES ("
                "%s, TRUE, FALSE, FALSE, "
                "10, 5, NULL, NULL, NULL, NULL, "
                "30, 10, 10, 5, %s) "
                "ON CONFLICT (device_id) DO UPDATE SET "
                "enable_i=EXCLUDED.enable_i, enable_p=EXCLUDED.enable_p, enable_f=EXCLUDED.enable_f, "
                "i_on=EXCLUDED.i_on, i_off=EXCLUDED.i_off, p_on=EXCLUDED.p_on, p_off=EXCLUDED.p_off, "
                "f_on=EXCLUDED.f_on, f_off=EXCLUDED.f_off, grace_hold_secs=EXCLUDED.grace_hold_secs, "
                "min_run_secs=EXCLUDED.min_run_secs, min_stop_secs=EXCLUDED.min_stop_secs, smoothing_secs=EXCLUDED.smoothing_secs, "
                "updated_by=EXCLUDED.updated_by"
            )
            for did in dids:
                cur.execute(sql, (did, "seed:demo"))
        conn.commit()
    print("SEEDED", {"count": len(dids), "device_ids": dids[:10]})


if __name__ == "__main__":
    main()
