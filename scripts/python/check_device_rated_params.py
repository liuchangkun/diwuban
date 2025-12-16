"""检查设备额定参数表"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, get_connection

init_logging(project_root / 'configs')
settings = load_settings(project_root / 'configs')
init_database(settings)

print('=' * 100)
print('1. 检查 device_rated_params 表结构')
print('=' * 100)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 查看表结构
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'device_rated_params'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        
        print(f'{"列名":<30} {"数据类型":<20} {"可空":<10} {"默认值":<20}')
        print('-' * 100)
        for col in columns:
            print(f'{col[0]:<30} {col[1]:<20} {col[2]:<10} {str(col[3]):<20}')
        print()

print('=' * 100)
print('2. 检查 device_rated_params 表数据')
print('=' * 100)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 查看数据内容（设备129-136）
        cur.execute("""
            SELECT device_id, param_key, value_numeric, value_text, unit, source
            FROM device_rated_params
            WHERE device_id BETWEEN 129 AND 136
            ORDER BY device_id, param_key;
        """)
        rows = cur.fetchall()

        if rows:
            print(f'找到 {len(rows)} 条记录')
            print()

            # 按设备分组打印
            current_device = None
            for row in rows:
                device_id, param_key, value_numeric, value_text, unit, source = row
                if device_id != current_device:
                    if current_device is not None:
                        print()
                    print(f'设备 {device_id}:')
                    current_device = device_id

                value = value_numeric if value_numeric is not None else value_text
                unit_str = f' {unit}' if unit else ''
                source_str = f' (来源: {source})' if source else ''
                print(f'  {param_key}: {value}{unit_str}{source_str}')
        else:
            print('❌ 没有找到设备129-136的额定参数数据！')
            print()

            # 检查表中有哪些设备
            cur.execute("SELECT DISTINCT device_id FROM device_rated_params ORDER BY device_id;")
            devices = cur.fetchall()
            if devices:
                print(f'表中存在的device_id: {[d[0] for d in devices]}')
            else:
                print('表中没有任何数据！')

print('=' * 100)
print('3. 检查 pump_characteristic_curves 表')
print('=' * 100)

with get_connection() as conn:
    with conn.cursor() as cur:
        # 查看表结构
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'pump_characteristic_curves'
            ORDER BY ordinal_position;
        """)
        columns = cur.fetchall()
        
        print('表结构：')
        for col in columns:
            print(f'  - {col[0]} ({col[1]})')
        print()
        
        # 查看数据
        cur.execute("""
            SELECT COUNT(*) 
            FROM pump_characteristic_curves
            WHERE station_id = 17;
        """)
        count = cur.fetchone()[0]
        print(f'station_id=17的数据条数: {count}')

