"""
回滚刚才的错误修改
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
print("🔙 回滚错误的修改")
print("="*100)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 回滚 method_b
        cur.execute("""
            UPDATE calculation_method_registry
            SET 
                priority = 90,
                accuracy_level = 'medium',
                updated_at = NOW()
            WHERE method_id = 'pump_outlet_pressure_method_b'
              AND metric_key = 'pump_outlet_pressure'
        """)
        
        # 回滚 method_c
        cur.execute("""
            UPDATE calculation_method_registry
            SET 
                priority = 80,
                accuracy_level = 'high',
                updated_at = NOW()
            WHERE method_id = 'pump_outlet_pressure_method_c'
              AND metric_key = 'pump_outlet_pressure'
        """)
        
        # 回滚 method_a
        cur.execute("""
            UPDATE calculation_method_registry
            SET 
                is_enabled = true,
                updated_at = NOW()
            WHERE method_id = 'pump_outlet_pressure_method_a'
              AND metric_key = 'pump_outlet_pressure'
        """)
        
        conn.commit()
        print("✅ 已回滚所有修改")

print("="*100)

