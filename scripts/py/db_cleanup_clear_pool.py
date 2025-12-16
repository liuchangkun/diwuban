# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import sys

# Ensure project root import
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config.loader_new import load_settings
from app.adapters.db import get_connection, init_database


def main() -> None:
    settings = load_settings(PROJECT_ROOT / "configs")
    init_database(settings)

    select_sql = (
        "SELECT id, station_id, name, type FROM dim_devices "
        "WHERE name = '其他' OR name LIKE '%清水池%' ORDER BY station_id, id"
    )
    # 将历史误入的池类设备改为 clear_water_pool 并加注释标记，而不是物理删除（避免外键约束问题）
    update_sql = (
        "UPDATE dim_devices SET type='clear_water_pool', name = name || '（清水池-已忽略）' "
        "WHERE (name = '其他' AND type = 'pump') OR name LIKE '%清水池%'"
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            rows = cur.fetchall()
            print(f"待删除记录数: {len(rows)}")
            for r in rows[:20]:  # preview up to 20
                print({
                    "id": r[0],
                    "station_id": r[1],
                    "name": r[2],
                    "type": r[3],
                })
            cur.execute(update_sql)
            print(f"已更新记录数: {cur.rowcount}")
            conn.commit()

    # 验证
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM dim_devices WHERE name = '其他'")
            cnt = cur.fetchone()[0]
            print(f"验证: 名称为'其他'的剩余记录数: {cnt}")


if __name__ == "__main__":
    main()

