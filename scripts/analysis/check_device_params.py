# -*- coding: utf-8 -*-
"""
检查所有设备的额定参数完整性
"""
import psycopg
import yaml
from pathlib import Path

# 读取数据库配置
config_path = Path("configs/database.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    db_config = yaml.safe_load(f)

# 连接数据库
conn_str = f"host={db_config['host']} port={db_config['port']} dbname={db_config['dbname']} user={db_config['user']} password={db_config['password']}"

with psycopg.connect(conn_str) as conn:
    with conn.cursor() as cur:
        print("=" * 100)
        print("检查所有设备的额定参数完整性")
        print("=" * 100)
        
        # 获取所有设备
        cur.execute("""
            SELECT id, station_id, name, type, pump_type
            FROM dim_devices
            WHERE is_active = TRUE
            ORDER BY id
        """)
        devices = cur.fetchall()
        
        print(f"\n找到 {len(devices)} 个活跃设备：")
        for device in devices:
            print(f"  设备ID={device[0]}, 泵站ID={device[1]}, 名称={device[2]}, 类型={device[3]}, 泵类型={device[4]}")
        
        print("\n" + "=" * 100)
        print("检查每个设备的额定参数")
        print("=" * 100)
        
        # 定义必需的额定参数
        required_params = [
            'rated_frequency',    # 额定频率
            'poles_pair',         # 极对数
            'rated_efficiency',   # 额定效率
            'rated_flow',         # 额定流量
            'rated_head',         # 额定扬程
        ]
        
        missing_params_summary = {}
        
        for device in devices:
            device_id = device[0]
            device_name = device[2]
            
            print(f"\n【设备 {device_id}: {device_name}】")
            
            # 查询该设备的所有额定参数
            cur.execute("""
                SELECT param_key, value_numeric, unit
                FROM device_rated_params
                WHERE device_id = %s
                ORDER BY param_key
            """, (device_id,))
            params = cur.fetchall()
            
            if not params:
                print(f"  ⚠️  没有任何额定参数")
                missing_params_summary[device_id] = required_params.copy()
                continue
            
            # 检查必需参数是否存在
            existing_params = {row[0] for row in params}
            missing_params = [p for p in required_params if p not in existing_params]
            
            if missing_params:
                print(f"  ⚠️  缺少 {len(missing_params)} 个必需参数：{missing_params}")
                missing_params_summary[device_id] = missing_params
            else:
                print(f"  ✅ 所有必需参数都存在")
            
            # 显示现有参数
            print(f"  现有参数：")
            for row in params:
                print(f"    - {row[0]:<20} = {row[1]:<10} {row[2] or ''}")
        
        print("\n" + "=" * 100)
        print("总结")
        print("=" * 100)
        
        if missing_params_summary:
            print(f"\n⚠️  发现 {len(missing_params_summary)} 个设备缺少额定参数：")
            for device_id, missing in missing_params_summary.items():
                device_name = next(d[2] for d in devices if d[0] == device_id)
                print(f"  设备 {device_id} ({device_name}): 缺少 {len(missing)} 个参数")
                for param in missing:
                    print(f"    - {param}")
        else:
            print("\n✅ 所有设备的额定参数都完整！")

print("\n✅ 检查完成")

