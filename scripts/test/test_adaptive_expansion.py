#!/usr/bin/env python3
"""
测试自适应扩展能力

用途：验证系统能够自动处理配置文件中新增的泵站和设备
作者：AI
创建日期：2025-10-29
"""
import sys
import json
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.services.ingest.prepare_dim import prepare_dim


def test_adaptive_expansion():
    """测试自适应扩展能力"""
    print("=" * 80)
    print("测试自适应扩展能力")
    print("=" * 80)
    print()
    
    # 备份原配置文件
    original_config = project_root / "configs" / "data_mapping.v2.json"
    backup_config = project_root / "configs" / "data_mapping.v2.json.backup"
    
    print(f"备份原配置文件: {original_config} -> {backup_config}")
    shutil.copy(original_config, backup_config)
    
    try:
        # 读取原配置
        with open(original_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("原配置文件内容：")
        print(f"  泵站数量: {len(config['stations'])}")
        total_devices = sum(len(s['devices']) for s in config['stations'])
        print(f"  设备数量: {total_devices}")
        print()
        
        # 添加新的泵站和设备
        print("添加新的泵站和设备到配置文件...")
        new_station = {
            "name": "测试泵站",
            "id": 2,  # 新的泵站ID
            "devices": [
                {
                    "name": "测试泵站1#泵",
                    "id": 9,  # 新的设备ID
                    "type": "pump",
                    "pump_type": "variable_frequency",
                    "metrics": [
                        {
                            "key": "pump_frequency",
                            "files": ["test_pump_frequency.csv"]
                        }
                    ]
                },
                {
                    "name": "测试泵站2#泵",
                    "id": 10,  # 新的设备ID
                    "type": "pump",
                    "pump_type": "soft_start",
                    "metrics": [
                        {
                            "key": "pump_frequency",
                            "files": ["test_pump_frequency_2.csv"]
                        }
                    ]
                }
            ]
        }
        
        config['stations'].append(new_station)
        
        # 保存修改后的配置
        with open(original_config, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print("修改后的配置文件内容：")
        print(f"  泵站数量: {len(config['stations'])}")
        total_devices = sum(len(s['devices']) for s in config['stations'])
        print(f"  设备数量: {total_devices}")
        print()
        
        # 记录执行前的数据库状态
        print("执行前的数据库状态：")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_stations")
                stations_before = cur.fetchone()
                print(f"  dim_stations: 数量={stations_before[0]}, ID范围={stations_before[1]}-{stations_before[2]}")
                
                cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_devices")
                devices_before = cur.fetchone()
                print(f"  dim_devices: 数量={devices_before[0]}, ID范围={devices_before[1]}-{devices_before[2]}")
        
        print()
        print("执行 prepare_dim() 函数...")
        print()
        
        # 执行 prepare_dim
        settings = load_settings(project_root / "configs")
        result = prepare_dim(settings, original_config, stage=1)
        
        print("✅ prepare_dim() 执行成功")
        print(f"执行结果: {result}")
        print()
        
        # 记录执行后的数据库状态
        print("执行后的数据库状态：")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_stations")
                stations_after = cur.fetchone()
                print(f"  dim_stations: 数量={stations_after[0]}, ID范围={stations_after[1]}-{stations_after[2]}")
                
                cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_devices")
                devices_after = cur.fetchone()
                print(f"  dim_devices: 数量={devices_after[0]}, ID范围={devices_after[1]}-{devices_after[2]}")
        
        print()
        
        # 验证新增的数据
        success = True
        
        print("验证新增的泵站和设备：")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 验证新泵站
                cur.execute("SELECT id, name FROM dim_stations WHERE id = 2")
                new_station_row = cur.fetchone()
                if new_station_row and new_station_row[1] == "测试泵站":
                    print(f"✅ 新泵站已添加: ID={new_station_row[0]}, 名称={new_station_row[1]}")
                else:
                    print(f"❌ 新泵站未找到或名称不匹配")
                    success = False
                
                # 验证新设备
                cur.execute("SELECT id, name, station_id, type FROM dim_devices WHERE id IN (9, 10) ORDER BY id")
                new_devices = cur.fetchall()
                
                expected_new_devices = {
                    9: ("测试泵站1#泵", 2, "pump"),
                    10: ("测试泵站2#泵", 2, "pump")
                }
                
                for device_id, device_name, station_id, device_type in new_devices:
                    if device_id in expected_new_devices:
                        expected = expected_new_devices[device_id]
                        if device_name == expected[0] and station_id == expected[1] and device_type == expected[2]:
                            print(f"✅ 新设备已添加: ID={device_id}, 名称={device_name}, 泵站ID={station_id}")
                        else:
                            print(f"❌ 新设备信息不匹配: ID={device_id}")
                            success = False
                    else:
                        print(f"❌ 发现未预期的设备: ID={device_id}")
                        success = False
        
        print()
        
        # 验证原有数据未受影响
        print("验证原有数据未受影响：")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM dim_stations WHERE id = 1")
                original_station = cur.fetchone()
                if original_station and original_station[1] == "二期供水泵房":
                    print(f"✅ 原泵站未受影响: ID={original_station[0]}, 名称={original_station[1]}")
                else:
                    print(f"❌ 原泵站数据异常")
                    success = False
                
                cur.execute("SELECT COUNT(*) FROM dim_devices WHERE id BETWEEN 1 AND 8")
                original_devices_count = cur.fetchone()[0]
                if original_devices_count == 8:
                    print(f"✅ 原设备未受影响: 数量={original_devices_count}")
                else:
                    print(f"❌ 原设备数量异常: {original_devices_count}")
                    success = False
        
        print()
        print("=" * 80)
        if success:
            print("✅ 自适应扩展测试通过：系统能够自动处理配置文件中的新增内容")
        else:
            print("❌ 自适应扩展测试失败")
        print("=" * 80)
        
        return success
        
    finally:
        # 恢复原配置文件
        print()
        print(f"恢复原配置文件: {backup_config} -> {original_config}")
        shutil.copy(backup_config, original_config)
        backup_config.unlink()  # 删除备份文件
        
        # 清理测试数据
        print("清理测试数据...")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 删除测试设备
                cur.execute("DELETE FROM dim_devices WHERE id IN (9, 10)")
                deleted_devices = cur.rowcount
                print(f"  删除了 {deleted_devices} 个测试设备")
                
                # 删除测试泵站
                cur.execute("DELETE FROM dim_stations WHERE id = 2")
                deleted_stations = cur.rowcount
                print(f"  删除了 {deleted_stations} 个测试泵站")
                
                conn.commit()
        
        print("清理完成")


def main():
    """主函数"""
    # 初始化数据库连接
    settings = load_settings(project_root / "configs")
    init_database(settings)
    
    # 执行测试
    success = test_adaptive_expansion()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

