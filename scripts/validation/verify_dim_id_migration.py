#!/usr/bin/env python3
"""
验证维度表ID迁移结果

用途：验证 dim_stations 和 dim_devices 表的ID是否已更新为配置文件中的固定ID
作者：AI
创建日期：2025-10-29
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


class MigrationVerifier:
    """迁移验证器"""
    
    def __init__(self):
        self.config_file = project_root / "configs" / "data_mapping.v2.json"
        self.config_data = None
        self.issues = []
    
    def load_config(self) -> bool:
        """加载配置文件"""
        if not self.config_file.exists():
            print(f"❌ 配置文件不存在: {self.config_file}")
            return False
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config_data = json.load(f)
        
        return True
    
    def verify_stations(self) -> bool:
        """验证泵站ID"""
        print("=" * 80)
        print("验证泵站ID")
        print("=" * 80)
        
        # 从配置文件获取期望的泵站
        expected_stations = {}
        for station in self.config_data['stations']:
            expected_stations[station['id']] = station['name']
        
        print(f"配置文件中的泵站数量: {len(expected_stations)}")
        print(f"期望的泵站ID: {sorted(expected_stations.keys())}")
        print()
        
        # 从数据库查询实际的泵站
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name FROM dim_stations ORDER BY id")
                actual_stations = {row[0]: row[1] for row in cur.fetchall()}
        
        print(f"数据库中的泵站数量: {len(actual_stations)}")
        print(f"实际的泵站ID: {sorted(actual_stations.keys())}")
        print()
        
        # 验证
        success = True
        
        # 检查数量
        if len(actual_stations) != len(expected_stations):
            print(f"❌ 泵站数量不匹配！期望: {len(expected_stations)}, 实际: {len(actual_stations)}")
            self.issues.append(f"泵站数量不匹配")
            success = False
        
        # 检查每个泵站
        for station_id, station_name in expected_stations.items():
            if station_id not in actual_stations:
                print(f"❌ 缺少泵站 ID={station_id}: {station_name}")
                self.issues.append(f"缺少泵站 ID={station_id}")
                success = False
            elif actual_stations[station_id] != station_name:
                print(f"❌ 泵站名称不匹配 ID={station_id}: 期望'{station_name}', 实际'{actual_stations[station_id]}'")
                self.issues.append(f"泵站名称不匹配 ID={station_id}")
                success = False
            else:
                print(f"✅ 泵站 ID={station_id}: {station_name}")
        
        print()
        if success:
            print("✅ 泵站ID验证通过")
        else:
            print("❌ 泵站ID验证失败")
        
        print()
        return success
    
    def verify_devices(self) -> bool:
        """验证设备ID"""
        print("=" * 80)
        print("验证设备ID")
        print("=" * 80)
        
        # 从配置文件获取期望的设备
        expected_devices = {}
        for station in self.config_data['stations']:
            for device in station['devices']:
                expected_devices[device['id']] = {
                    'name': device['name'],
                    'station_id': station['id'],
                    'type': device['type']
                }
        
        print(f"配置文件中的设备数量: {len(expected_devices)}")
        print(f"期望的设备ID范围: {min(expected_devices.keys())} - {max(expected_devices.keys())}")
        print()
        
        # 从数据库查询实际的设备
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, station_id, type FROM dim_devices ORDER BY id")
                actual_devices = {
                    row[0]: {
                        'name': row[1],
                        'station_id': row[2],
                        'type': row[3]
                    }
                    for row in cur.fetchall()
                }
        
        print(f"数据库中的设备数量: {len(actual_devices)}")
        print(f"实际的设备ID范围: {min(actual_devices.keys())} - {max(actual_devices.keys())}")
        print()
        
        # 验证
        success = True
        
        # 检查数量
        if len(actual_devices) != len(expected_devices):
            print(f"❌ 设备数量不匹配！期望: {len(expected_devices)}, 实际: {len(actual_devices)}")
            self.issues.append(f"设备数量不匹配")
            success = False
        
        # 检查每个设备
        for device_id, expected_info in expected_devices.items():
            if device_id not in actual_devices:
                print(f"❌ 缺少设备 ID={device_id}: {expected_info['name']}")
                self.issues.append(f"缺少设备 ID={device_id}")
                success = False
            else:
                actual_info = actual_devices[device_id]
                match = True
                
                if actual_info['name'] != expected_info['name']:
                    print(f"❌ 设备名称不匹配 ID={device_id}: 期望'{expected_info['name']}', 实际'{actual_info['name']}'")
                    self.issues.append(f"设备名称不匹配 ID={device_id}")
                    match = False
                
                if actual_info['station_id'] != expected_info['station_id']:
                    print(f"❌ 设备所属泵站不匹配 ID={device_id}: 期望{expected_info['station_id']}, 实际{actual_info['station_id']}")
                    self.issues.append(f"设备所属泵站不匹配 ID={device_id}")
                    match = False
                
                if actual_info['type'] != expected_info['type']:
                    print(f"❌ 设备类型不匹配 ID={device_id}: 期望'{expected_info['type']}', 实际'{actual_info['type']}'")
                    self.issues.append(f"设备类型不匹配 ID={device_id}")
                    match = False
                
                if match:
                    print(f"✅ 设备 ID={device_id}: {expected_info['name']}")
                else:
                    success = False
        
        print()
        if success:
            print("✅ 设备ID验证通过")
        else:
            print("❌ 设备ID验证失败")
        
        print()
        return success
    
    def verify_sequences_deleted(self) -> bool:
        """验证序列是否已删除"""
        print("=" * 80)
        print("验证序列是否已删除")
        print("=" * 80)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 检查 dim_stations_id_seq
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM pg_sequences 
                    WHERE schemaname = 'public' AND sequencename = 'dim_stations_id_seq'
                """)
                stations_seq_exists = cur.fetchone()[0] > 0
                
                # 检查 dim_devices_id_seq
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM pg_sequences 
                    WHERE schemaname = 'public' AND sequencename = 'dim_devices_id_seq'
                """)
                devices_seq_exists = cur.fetchone()[0] > 0
        
        success = True
        
        if stations_seq_exists:
            print("❌ 序列 dim_stations_id_seq 仍然存在（应该已被删除）")
            self.issues.append("序列 dim_stations_id_seq 未删除")
            success = False
        else:
            print("✅ 序列 dim_stations_id_seq 已删除")
        
        if devices_seq_exists:
            print("❌ 序列 dim_devices_id_seq 仍然存在（应该已被删除）")
            self.issues.append("序列 dim_devices_id_seq 未删除")
            success = False
        else:
            print("✅ 序列 dim_devices_id_seq 已删除")
        
        print()
        if success:
            print("✅ 序列删除验证通过")
        else:
            print("❌ 序列删除验证失败")
        
        print()
        return success
    
    def verify_foreign_keys(self) -> bool:
        """验证外键关联（抽样检查）"""
        print("=" * 80)
        print("验证外键关联（抽样检查）")
        print("=" * 80)
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 检查设备的station_id是否都有效
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM dim_devices d
                    WHERE NOT EXISTS (
                        SELECT 1 FROM dim_stations s WHERE s.id = d.station_id
                    )
                """)
                orphan_devices = cur.fetchone()[0]
                
                # 检查一些关联表（抽样）
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM device_rated_params drp
                    WHERE NOT EXISTS (
                        SELECT 1 FROM dim_devices d WHERE d.id = drp.device_id
                    )
                """)
                orphan_params = cur.fetchone()[0]
        
        success = True
        
        if orphan_devices > 0:
            print(f"❌ 发现 {orphan_devices} 个设备的station_id引用不存在的泵站")
            self.issues.append(f"{orphan_devices} 个设备的station_id无效")
            success = False
        else:
            print("✅ 所有设备的station_id都有效")
        
        if orphan_params > 0:
            print(f"❌ 发现 {orphan_params} 个device_rated_params记录引用不存在的设备")
            self.issues.append(f"{orphan_params} 个device_rated_params记录的device_id无效")
            success = False
        else:
            print("✅ device_rated_params表的外键关联正常")
        
        print()
        if success:
            print("✅ 外键关联验证通过")
        else:
            print("❌ 外键关联验证失败")
        
        print()
        return success
    
    def run_all_verifications(self) -> bool:
        """运行所有验证"""
        print()
        print("=" * 80)
        print("开始验证维度表ID迁移结果")
        print("=" * 80)
        print()
        
        if not self.load_config():
            return False
        
        results = []
        results.append(("泵站ID验证", self.verify_stations()))
        results.append(("设备ID验证", self.verify_devices()))
        results.append(("序列删除验证", self.verify_sequences_deleted()))
        results.append(("外键关联验证", self.verify_foreign_keys()))
        
        # 打印总结
        print("=" * 80)
        print("验证结果总结")
        print("=" * 80)
        
        all_passed = True
        for name, passed in results:
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"{name}: {status}")
            if not passed:
                all_passed = False
        
        print()
        
        if all_passed:
            print("🎉🎉🎉 所有验证通过！迁移成功！🎉🎉🎉")
        else:
            print("❌ 发现以下问题：")
            for issue in self.issues:
                print(f"  - {issue}")
        
        print("=" * 80)
        print()
        
        return all_passed


def main():
    """主函数"""
    # 初始化数据库连接
    settings = load_settings(project_root / "configs")
    init_database(settings)
    
    # 执行验证
    verifier = MigrationVerifier()
    success = verifier.run_all_verifications()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

