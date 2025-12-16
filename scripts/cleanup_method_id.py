"""
清理calculation_parameters表中的method_id字段和外键约束
"""
from app.adapters.db.pool import get_connection

def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 删除外键约束
            print('1. 删除外键约束...')
            cur.execute("""
                ALTER TABLE calculation_parameters
                DROP CONSTRAINT IF EXISTS calculation_parameters_method_id_fkey;
            """)
            print('   ✅ 外键约束已删除')
            
            # 2. 删除method_id字段
            print('\n2. 删除method_id字段...')
            cur.execute("""
                ALTER TABLE calculation_parameters
                DROP COLUMN IF EXISTS method_id;
            """)
            print('   ✅ method_id字段已删除')
            
            # 3. 删除pump_shaft_power在废弃表中的记录
            print('\n3. 删除pump_shaft_power在废弃表中的记录...')
            cur.execute("""
                DELETE FROM "废弃_calculation_method_registry"
                WHERE method_id = 'pump_shaft_power_method_a';
            """)
            deleted = cur.rowcount
            print(f'   ✅ 删除了{deleted}条记录')
            
            # 4. 验证
            print('\n4. 验证修改...')
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'calculation_parameters' 
                  AND column_name = 'method_id';
            """)
            if cur.fetchone():
                print('   ❌ method_id字段仍然存在')
            else:
                print('   ✅ method_id字段已成功删除')
            
            conn.commit()
            print('\n✅ 所有修改已提交')

if __name__ == '__main__':
    from pathlib import Path
    from app.adapters.db import init_database
    from app.core.config.loader_new import load_settings
    
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    main()

