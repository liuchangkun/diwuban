"""执行pump_shaft_power参数初始化"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings

# 加载配置并初始化数据库
settings = load_settings(Path("configs"))
init_database(settings)

print("开始执行参数初始化...")

with get_connection() as conn:
    with conn.cursor() as cur:
        # 1. 删除旧的eta_motor和eta_vfd参数
        print("\n1. 删除旧参数...")
        cur.execute("""
            DELETE FROM device_rated_params
            WHERE device_id IN (1, 2, 3, 4, 5, 6)
              AND param_key IN ('eta_motor', 'eta_vfd')
        """)
        deleted_count = cur.rowcount
        print(f"   ✅ 删除{deleted_count}条旧记录")

        # 2. 插入device_rated_params
        print("\n2. 插入device_rated_params...")
        cur.execute("""
            INSERT INTO device_rated_params (
                station_id, device_id, param_key, value_numeric, unit, source, effective_from
            ) VALUES
                (1, 1, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 1, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 2, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 2, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 3, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 3, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 4, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 4, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 5, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 5, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 6, 'eta_motor', 0.92, '-', 'manual', '2025-10-22 00:00:00+08'),
                (1, 6, 'eta_vfd', 0.97, '-', 'manual', '2025-10-22 00:00:00+08')
        """)
        print(f"   ✅ 插入12条记录")
        
        # 3. 删除旧的calculation_parameters（不再使用废弃的method_registry）
        print("\n3. 删除旧的calculation_parameters...")
        cur.execute("""
            DELETE FROM calculation_parameters
            WHERE metric_key = 'pump_shaft_power'
        """)
        deleted_count = cur.rowcount
        print(f"   ✅ 删除{deleted_count}条旧记录")

        # 4. 插入calculation_parameters（不再包含method_id字段）
        print("\n4. 插入calculation_parameters...")
        cur.execute("""
            INSERT INTO calculation_parameters (
                station_id, device_id, metric_key, param_name, param_value, param_type
            ) VALUES
                (NULL, NULL, 'pump_shaft_power', 'max_power', 200.0, 'float'),
                (NULL, NULL, 'pump_shaft_power', 'min_power', 0.0, 'float'),
                (NULL, NULL, 'pump_shaft_power', 'max_shaft_power', 500.0, 'float'),
                (NULL, NULL, 'pump_shaft_power', 'max_change_rate', 50.0, 'float')
        """)
        print(f"   ✅ 插入4条记录")
        
        conn.commit()

        # 6. 验证device_rated_params
        print("\n6. 验证device_rated_params...")
        cur.execute("""
            SELECT device_id, param_key, value_numeric, unit
            FROM device_rated_params
            WHERE device_id IN (1, 2, 3, 4, 5, 6)
              AND param_key IN ('eta_motor', 'eta_vfd')
            ORDER BY device_id, param_key
        """)
        results = cur.fetchall()
        print(f"   ✅ 查询到{len(results)}条记录")
        for row in results[:4]:
            print(f"      device_id={row[0]}, {row[1]}={row[2]}")

        # 7. 验证calculation_parameters
        print("\n7. 验证calculation_parameters...")
        cur.execute("""
            SELECT metric_key, param_name, param_value
            FROM calculation_parameters
            WHERE metric_key = 'pump_shaft_power'
            ORDER BY param_name
        """)
        results = cur.fetchall()
        print(f"   ✅ 查询到{len(results)}条记录")
        for row in results:
            print(f"      {row[1]}={row[2]}")

print("\n✅ 参数初始化完成")

