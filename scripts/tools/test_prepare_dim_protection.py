#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 prepare_dim 流程是否保护 calculation_parameters 表

用途: 验证执行 prepare_dim 后，calculation_parameters 表的全局参数是否保留
创建日期: 2025-11-14
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def test_prepare_dim_protection() -> bool:
    """测试 prepare_dim 保护"""
    print("=" * 80)
    print("测试 prepare_dim 流程对 calculation_parameters 表的保护")
    print("=" * 80)
    print()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 步骤1: 记录当前的全局参数数量
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM calculation_parameters 
                    WHERE station_id IS NULL AND device_id IS NULL
                """)
                before_count = cur.fetchone()[0]
                print(f"📋 执行前全局参数数量: {before_count}")
                print()
                
                if before_count == 0:
                    print("⚠️ 警告: calculation_parameters 表中没有全局参数")
                    print()
                
                # 步骤2: 模拟 prepare_dim 的清空操作
                print("🔄 模拟 prepare_dim 的清空操作...")
                print("   1. 清空 dim_devices 表（触发 CASCADE 删除设备参数）")
                print("   2. 清空 dim_stations 表（触发 CASCADE 删除站点参数）")
                print()
                
                # 开始事务
                cur.execute("BEGIN;")
                
                try:
                    # 清空 dim_devices（会触发 CASCADE 删除 device_id IS NOT NULL 的参数）
                    cur.execute("DELETE FROM dim_devices;")
                    deleted_devices = cur.rowcount
                    print(f"   ✅ 删除了 {deleted_devices} 个设备")
                    
                    # 清空 dim_stations（会触发 CASCADE 删除 station_id IS NOT NULL 的参数）
                    cur.execute("DELETE FROM dim_stations;")
                    deleted_stations = cur.rowcount
                    print(f"   ✅ 删除了 {deleted_stations} 个站点")
                    print()
                    
                    # 步骤3: 检查全局参数是否保留
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM calculation_parameters 
                        WHERE station_id IS NULL AND device_id IS NULL
                    """)
                    after_count = cur.fetchone()[0]
                    print(f"📋 执行后全局参数数量: {after_count}")
                    print()
                    
                    # 回滚事务（不真的删除数据）
                    cur.execute("ROLLBACK;")
                    print("✅ 事务已回滚，数据未真正删除")
                    print()
                    
                    # 验证结果
                    if after_count == before_count:
                        print("=" * 80)
                        print("✅ 测试成功: 全局参数被保护，未被删除！")
                        print("=" * 80)
                        print()
                        print("📋 结论:")
                        print(f"  - 执行前全局参数: {before_count} 个")
                        print(f"  - 执行后全局参数: {after_count} 个")
                        print("  - 全局参数完全保留，未受 CASCADE 删除影响")
                        print("  - metric_key 外键的 RESTRICT 约束成功保护了数据")
                        print()
                        return True
                    else:
                        print("=" * 80)
                        print("❌ 测试失败: 全局参数被删除！")
                        print("=" * 80)
                        print()
                        print("📋 结论:")
                        print(f"  - 执行前全局参数: {before_count} 个")
                        print(f"  - 执行后全局参数: {after_count} 个")
                        print(f"  - 丢失了 {before_count - after_count} 个全局参数")
                        print()
                        return False
                        
                except Exception as e:
                    # 回滚事务
                    cur.execute("ROLLBACK;")
                    print(f"❌ 模拟失败: {e}")
                    print()
                    return False

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ 测试失败！")
        print("=" * 80)
        print(f"错误信息: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 加载配置
    settings = load_settings(project_root / "configs")
    
    # 初始化连接池
    try:
        initialize_pool(settings)
    except Exception as e:
        print(f"❌ 初始化连接池失败: {e}")
        return 1
    
    try:
        # 测试保护
        success = test_prepare_dim_protection()
        return 0 if success else 1
    finally:
        # 关闭连接池
        try:
            close_pool()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

