"""
修复 pump_outlet_pressure 的计算方法优先级

问题：
当前 method_c（从扬程回推）正在使用，但计算结果偏高120-180%
method_b（使用总管出口压力代替）优先级较低，没有被使用

解决方案：
1. 提高 method_b 的优先级到 110
2. 降低 method_c 的优先级到 70
3. 禁用 method_a（因为没有传感器）
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from pathlib import Path
from app.core.config.loader import load_settings
from app.adapters.db import init_database, get_connection

# 初始化数据库
settings = load_settings(Path('configs'))
init_database(settings)

print("="*100)
print("🔧 修复 pump_outlet_pressure 计算方法优先级")
print("="*100)

with get_connection() as conn:
    with conn.cursor() as cur:
        print("\n📊 修改前的配置:")
        cur.execute("""
            SELECT 
                method_id,
                method_name,
                priority,
                accuracy_level,
                is_enabled
            FROM calculation_method_registry
            WHERE metric_key = 'pump_outlet_pressure'
            ORDER BY priority DESC
        """)
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]} (优先级={row[2]}, 精度={row[3]}, 启用={row[4]})")
        
        print("\n🔧 执行修改...")
        
        # 1. 提高 method_b 的优先级
        cur.execute("""
            UPDATE calculation_method_registry
            SET 
                priority = 110,
                accuracy_level = 'high',
                updated_at = NOW()
            WHERE method_id = 'pump_outlet_pressure_method_b'
              AND metric_key = 'pump_outlet_pressure'
        """)
        print("  ✅ method_b 优先级提升到 110")
        
        # 2. 降低 method_c 的优先级
        cur.execute("""
            UPDATE calculation_method_registry
            SET 
                priority = 70,
                accuracy_level = 'low',
                updated_at = NOW()
            WHERE method_id = 'pump_outlet_pressure_method_c'
              AND metric_key = 'pump_outlet_pressure'
        """)
        print("  ✅ method_c 优先级降低到 70")
        
        # 3. 禁用 method_a
        cur.execute("""
            UPDATE calculation_method_registry
            SET 
                is_enabled = false,
                updated_at = NOW()
            WHERE method_id = 'pump_outlet_pressure_method_a'
              AND metric_key = 'pump_outlet_pressure'
        """)
        print("  ✅ method_a 已禁用")
        
        conn.commit()
        
        print("\n📊 修改后的配置:")
        cur.execute("""
            SELECT 
                method_id,
                method_name,
                priority,
                accuracy_level,
                is_enabled
            FROM calculation_method_registry
            WHERE metric_key = 'pump_outlet_pressure'
            ORDER BY priority DESC
        """)
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]} (优先级={row[2]}, 精度={row[3]}, 启用={row[4]})")

print("\n" + "="*100)
print("✅ 修复完成！")
print("="*100)
print("\n💡 下一步：")
print("  1. 删除旧的 pump_outlet_pressure 数据")
print("  2. 重新运行计算")
print("  3. 验证新数据与实测总管出口压力的误差 < 5%")
print()

