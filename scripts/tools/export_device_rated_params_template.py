# -*- coding: utf-8 -*-
"""
导出 device_rated_params 待填模板：
- 从 dim_devices、dim_stations 读取站点/设备清单
- 结合泵类型（variable_frequency/soft_start）给出建议 param_key 行
- 输出 CSV：device_id, station_id, station_name, device_name, pump_type, param_key, unit, example, zh_desc
"""
from __future__ import annotations

import csv
import psycopg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "_archive" / "reports" / "device_rated_params_template.csv"

PARAM_ROWS_COMMON = [
    ("rated_frequency", "Hz", 50, "额定频率"),
    ("poles_pair", None, 2, "极对数"),
    ("rated_efficiency", None, 0.78, "额定效率(0-1)"),
    ("rated_flow", "m3/h", 400, "额定流量"),
    ("rated_head", "m", 25, "额定扬程"),
    ("eta_motor", None, 0.93, "电机效率(0-1)"),
    ("eta_vfd", None, 0.97, "变频器效率(0-1)；软启取1.00"),
]

PARAM_ROWS_PIPELINE = [
    ("pipe_diameter", "m", 0.40, "主管内径(米)"),
    ("pipe_length", "m", 150.0, "代表性管段长度(米)"),
    ("roughness_rel", None, 0.0005, "相对粗糙度ε/D(无量纲)"),
    ("C_hazen", None, 120, "海泽-威廉系数"),
]


def export_csv():
    dsn = None
    # 优先读取 dsn_read；如果为 None 则尝试 host/name/user 无密码连接
    cfg = (ROOT / "configs" / "database.yaml").read_text(encoding="utf-8")
    # 这里简化处理：使用 psycopg.connect() 依赖 .pgpass 或 trust
    with psycopg.connect(
        dbname="pump_station_optimization", host="localhost", user="postgres"
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM public.dim_stations ORDER BY id")
            stations = {row[0]: row[1] for row in cur.fetchall()}
            cur.execute(
                "SELECT id, station_id, name, type, pump_type FROM public.dim_devices ORDER BY station_id, id"
            )
            devices = cur.fetchall()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(
            [
                "device_id",
                "station_id",
                "station_name",
                "device_name",
                "pump_type",
                "param_key",
                "unit",
                "example",
                "zh_desc",
            ]
        )
        for dev_id, st_id, dev_name, dev_type, pump_type in devices:
            if dev_type == "main_pipeline":
                for key, unit, ex, zh in PARAM_ROWS_PIPELINE:
                    w.writerow(
                        [
                            dev_id,
                            st_id,
                            stations.get(st_id, ""),
                            dev_name,
                            dev_type,
                            key,
                            unit or "",
                            ex,
                            zh,
                        ]
                    )
            elif dev_type == "pump":
                # 根据变频/软启调整默认示例
                rows = list(PARAM_ROWS_COMMON)
                if pump_type == "variable_frequency":
                    rows[2] = (
                        "rated_efficiency",
                        None,
                        0.76,
                        "额定效率(0-1)",
                    )  # 调低一点用于示例
                elif pump_type == "soft_start":
                    rows[2] = ("rated_efficiency", None, 0.74, "额定效率(0-1)")
                    rows[6] = ("eta_vfd", None, 1.00, "变频器效率(软启取1.00)")
                for key, unit, ex, zh in rows:
                    w.writerow(
                        [
                            dev_id,
                            st_id,
                            stations.get(st_id, ""),
                            dev_name,
                            pump_type or dev_type,
                            key,
                            unit or "",
                            ex,
                            zh,
                        ]
                    )
    print(f"已导出: {OUT}")


if __name__ == "__main__":
    export_csv()
