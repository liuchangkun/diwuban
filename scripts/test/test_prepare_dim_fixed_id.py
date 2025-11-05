#!/usr/bin/env python3
"""
测试 prepare_dim() 函数（使用固定ID）

用途：验证修改后的 prepare_dim() 函数能够正确使用配置文件中的固定ID
作者：AI
创建日期：2025-10-29
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.services.ingest.prepare_dim import prepare_dim


def test_prepare_dim():
    """测试 prepare_dim() 函数"""
    print("=" * 80)
    print("测试 prepare_dim() 函数（使用固定ID）")
    print("=" * 80)
    print()
    
    # 记录执行前的数据状态
    print("执行前的数据状态：")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_stations")
            stations_before = cur.fetchone()
            print(f"  dim_stations: 数量={stations_before[0]}, ID范围={stations_before[1]}-{stations_before[2]}")
            
            cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_devices")
            devices_before = cur.fetchone()
            print(f"  dim_devices: 数量={devices_before[0]}, ID范围={devices_before[1]}-{devices_before[2]}")
    
    print()
    print("执行 prepare_dim() 函数（仅阶段1：UPSERT stations和devices）...")
    print()

    # 执行 prepare_dim（仅阶段1，不需要fact_measurements数据）
    try:
        settings = load_settings(project_root / "configs")
        mapping_path = project_root / "configs" / "data_mapping.v2.json"
        result = prepare_dim(settings, mapping_path, stage=1)
        print("✅ prepare_dim(stage=1) 执行成功")
        print(f"执行结果: {result}")
    except Exception as e:
        print(f"❌ prepare_dim(stage=1) 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    
    # 记录执行后的数据状态
    print("执行后的数据状态：")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_stations")
            stations_after = cur.fetchone()
            print(f"  dim_stations: 数量={stations_after[0]}, ID范围={stations_after[1]}-{stations_after[2]}")
            
            cur.execute("SELECT COUNT(*), MIN(id), MAX(id) FROM dim_devices")
            devices_after = cur.fetchone()
            print(f"  dim_devices: 数量={devices_after[0]}, ID范围={devices_after[1]}-{devices_after[2]}")
    
    print()
    
    # 验证数据未发生变化
    success = True
    
    if stations_before != stations_after:
        print(f"⚠️  泵站数据发生变化：{stations_before} -> {stations_after}")
        # 这可能是正常的，如果配置文件有更新
    else:
        print("✅ 泵站数据未发生变化（符合预期）")
    
    if devices_before != devices_after:
        print(f"⚠️  设备数据发生变化：{devices_before} -> {devices_after}")
        # 这可能是正常的，如果配置文件有更新
    else:
        print("✅ 设备数据未发生变化（符合预期）")
    
    print()
    
    # 验证ID仍然是固定值
    print("验证ID是否仍为固定值：")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM dim_stations ORDER BY id")
            stations = cur.fetchall()
            for station_id, station_name in stations:
                if station_id == 1 and station_name == "二期供水泵房":
                    print(f"✅ 泵站 ID={station_id}: {station_name}")
                else:
                    print(f"❌ 泵站 ID={station_id}: {station_name} (不符合预期)")
                    success = False
            
            cur.execute("SELECT id, name FROM dim_devices ORDER BY id")
            devices = cur.fetchall()
            expected_devices = {
                1: "二期供水泵房1#泵",
                2: "二期供水泵房2#泵",
                3: "二期供水泵房3#泵",
                4: "二期供水泵房4#泵",
                5: "二期供水泵房5#泵",
                6: "二期供水泵房6#泵",
                7: "二期供水泵房总管",
                8: "其他"
            }
            
            for device_id, device_name in devices:
                if device_id in expected_devices and device_name == expected_devices[device_id]:
                    print(f"✅ 设备 ID={device_id}: {device_name}")
                else:
                    print(f"❌ 设备 ID={device_id}: {device_name} (不符合预期)")
                    success = False
    
    print()
    print("=" * 80)
    if success:
        print("✅ 测试通过：prepare_dim() 函数正常工作，ID保持固定")
    else:
        print("❌ 测试失败：发现问题")
    print("=" * 80)
    
    return success


def main():
    """主函数"""
    # 初始化数据库连接
    settings = load_settings(project_root / "configs")
    init_database(settings)
    
    # 执行测试
    success = test_prepare_dim()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

