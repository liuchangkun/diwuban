#!/usr/bin/env python3
"""
恢复测试数据脚本
将设备9999恢复为153，重新创建设备154
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def restore_data():
    """恢复测试数据"""
    
    print("\n" + "="*80)
    print("恢复测试数据")
    print("="*80 + "\n")
    
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    with get_connection() as conn:
        # 禁用autocommit，使用显式事务
        conn.autocommit = False
        
        with conn.cursor() as cur:
            try:
                print("--- 步骤1：将设备9999恢复为153 ---")
                cur.execute("UPDATE dim_devices SET id = 153 WHERE id = 9999")
                print(f"  ✅ 更新了 {cur.rowcount} 行")
                
                print("\n--- 步骤2：重新创建设备154 ---")
                # 检查设备154是否存在
                cur.execute("SELECT COUNT(*) FROM dim_devices WHERE id = 154")
                exists = cur.fetchone()[0]
                
                if exists == 0:
                    # 重新插入设备154
                    cur.execute("""
                        INSERT INTO dim_devices (id, station_id, name, type, pump_type, is_active)
                        VALUES (154, 20, '二期供水泵房2#泵', 'pump', 'variable_frequency', true)
                    """)
                    print(f"  ✅ 创建了设备154")
                    
                    # 重新创建设备154的额定参数
                    cur.execute("""
                        INSERT INTO device_rated_params (device_id, param_key, value_numeric, unit, source)
                        SELECT 154, param_key, value_numeric, unit, source
                        FROM device_rated_params
                        WHERE device_id = 153
                    """)
                    print(f"  ✅ 创建了 {cur.rowcount} 个额定参数")
                else:
                    print(f"  ℹ️ 设备154已存在，跳过创建")
                
                # 提交事务
                conn.commit()
                print("\n✅ 数据恢复完成")
                
                # 验证恢复结果
                print("\n--- 验证恢复结果 ---")
                cur.execute("""
                    SELECT 
                        d.id as device_id,
                        d.name as device_name,
                        COUNT(drp.id) as rated_params_count
                    FROM dim_devices d
                    LEFT JOIN device_rated_params drp ON drp.device_id = d.id
                    WHERE d.id IN (153, 154)
                    GROUP BY d.id, d.name
                    ORDER BY d.id
                """)
                for row in cur.fetchall():
                    print(f"  设备ID: {row[0]}, 名称: {row[1]}, 参数数量: {row[2]}")
                
            except Exception as e:
                print(f"\n❌ 恢复失败: {e}")
                conn.rollback()
                raise


if __name__ == "__main__":
    restore_data()

