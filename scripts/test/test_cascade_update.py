#!/usr/bin/env python3
"""
级联更新机制测试脚本
测试维度表ID变化时的参数表自动同步
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
import logging

logger = logging.getLogger(__name__)


def test_cascade_update():
    """测试级联更新机制"""
    
    print("\n" + "="*80)
    print("测试11：级联更新机制测试（使用事务回滚）")
    print("="*80 + "\n")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # 开始事务
                print("📝 开始事务...")
                
                # 步骤1：记录测试前的状态
                print("\n--- 步骤1：测试前状态 ---")
                cur.execute("""
                    SELECT 
                        d.id as device_id,
                        d.name as device_name,
                        COUNT(drp.id) as rated_params_count
                    FROM dim_devices d
                    LEFT JOIN device_rated_params drp ON drp.device_id = d.id
                    WHERE d.id = 153
                    GROUP BY d.id, d.name
                """)
                before_state = cur.fetchone()
                if before_state:
                    print(f"  设备ID: {before_state[0]}")
                    print(f"  设备名称: {before_state[1]}")
                    print(f"  额定参数数量: {before_state[2]}")
                else:
                    print("  ❌ 设备153不存在")
                    return
                
                # 步骤2：模拟修改设备ID
                print("\n--- 步骤2：执行ID更新 (153 -> 9999) ---")
                cur.execute("UPDATE dim_devices SET id = 9999 WHERE id = 153")
                print(f"  ✅ 更新了 {cur.rowcount} 行")
                
                # 步骤3：验证级联更新效果
                print("\n--- 步骤3：验证级联更新效果 ---")
                cur.execute("""
                    SELECT 
                        d.id as device_id,
                        d.name as device_name,
                        COUNT(drp.id) as rated_params_count
                    FROM dim_devices d
                    LEFT JOIN device_rated_params drp ON drp.device_id = d.id
                    WHERE d.id = 9999
                    GROUP BY d.id, d.name
                """)
                after_state = cur.fetchone()
                if after_state:
                    print(f"  设备ID: {after_state[0]}")
                    print(f"  设备名称: {after_state[1]}")
                    print(f"  额定参数数量: {after_state[2]}")
                    
                    # 验证参数数量是否一致
                    if after_state[2] == before_state[2]:
                        print(f"  ✅ 级联更新成功！参数数量保持一致: {after_state[2]}")
                    else:
                        print(f"  ❌ 级联更新失败！参数数量不一致: {before_state[2]} -> {after_state[2]}")
                else:
                    print("  ❌ 更新后的设备9999不存在")
                
                # 步骤4：检查旧ID是否还有残留参数
                print("\n--- 步骤4：检查旧ID残留 ---")
                cur.execute("SELECT COUNT(*) FROM device_rated_params WHERE device_id = 153")
                old_id_count = cur.fetchone()[0]
                if old_id_count == 0:
                    print(f"  ✅ 旧ID(153)无残留参数")
                else:
                    print(f"  ❌ 旧ID(153)仍有 {old_id_count} 个残留参数")
                
                # 步骤5：检查optimization_history表的级联更新
                print("\n--- 步骤5：检查optimization_history表的级联更新 ---")
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM optimization_history 
                    WHERE device_id = 9999
                """)
                opt_history_count = cur.fetchone()[0]
                print(f"  新ID(9999)的优化历史记录数: {opt_history_count}")
                
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM optimization_history 
                    WHERE device_id = 153
                """)
                old_opt_history_count = cur.fetchone()[0]
                print(f"  旧ID(153)的优化历史记录数: {old_opt_history_count}")
                
                if old_opt_history_count == 0:
                    print(f"  ✅ optimization_history表级联更新成功")
                else:
                    print(f"  ❌ optimization_history表级联更新失败")
                
                # 步骤6：回滚事务
                print("\n--- 步骤6：回滚事务 ---")
                conn.rollback()
                print("  ✅ 事务已回滚")
                
                # 步骤7：验证回滚后状态
                print("\n--- 步骤7：验证回滚后状态 ---")
                cur.execute("""
                    SELECT 
                        d.id as device_id,
                        d.name as device_name,
                        COUNT(drp.id) as rated_params_count
                    FROM dim_devices d
                    LEFT JOIN device_rated_params drp ON drp.device_id = d.id
                    WHERE d.id = 153
                    GROUP BY d.id, d.name
                """)
                rollback_state = cur.fetchone()
                if rollback_state:
                    print(f"  设备ID: {rollback_state[0]}")
                    print(f"  设备名称: {rollback_state[1]}")
                    print(f"  额定参数数量: {rollback_state[2]}")
                    
                    if rollback_state[2] == before_state[2]:
                        print(f"  ✅ 回滚成功！数据恢复到测试前状态")
                    else:
                        print(f"  ❌ 回滚异常！参数数量不一致")
                else:
                    print("  ❌ 回滚后设备153不存在")
                
                print("\n" + "="*80)
                print("✅ 级联更新测试完成")
                print("="*80 + "\n")
                
            except Exception as e:
                print(f"\n❌ 测试失败: {e}")
                conn.rollback()
                raise


def test_cascade_delete():
    """测试级联删除机制"""
    
    print("\n" + "="*80)
    print("测试12：级联删除机制测试（使用事务回滚）")
    print("="*80 + "\n")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                # 步骤1：记录测试前的状态
                print("--- 步骤1：测试前状态 ---")
                cur.execute("""
                    SELECT 
                        d.id as device_id,
                        d.name as device_name,
                        COUNT(drp.id) as rated_params_count
                    FROM dim_devices d
                    LEFT JOIN device_rated_params drp ON drp.device_id = d.id
                    WHERE d.id = 154
                    GROUP BY d.id, d.name
                """)
                before_state = cur.fetchone()
                if before_state:
                    print(f"  设备ID: {before_state[0]}")
                    print(f"  设备名称: {before_state[1]}")
                    print(f"  额定参数数量: {before_state[2]}")
                else:
                    print("  ❌ 设备154不存在")
                    return
                
                # 步骤2：模拟删除设备
                print("\n--- 步骤2：执行设备删除 ---")
                cur.execute("DELETE FROM dim_devices WHERE id = 154")
                print(f"  ✅ 删除了 {cur.rowcount} 个设备")
                
                # 步骤3：验证级联删除效果
                print("\n--- 步骤3：验证级联删除效果 ---")
                cur.execute("SELECT COUNT(*) FROM device_rated_params WHERE device_id = 154")
                remaining_params = cur.fetchone()[0]
                
                if remaining_params == 0:
                    print(f"  ✅ 级联删除成功！参数已全部删除")
                else:
                    print(f"  ❌ 级联删除失败！仍有 {remaining_params} 个残留参数")
                
                # 步骤4：回滚事务
                print("\n--- 步骤4：回滚事务 ---")
                conn.rollback()
                print("  ✅ 事务已回滚")
                
                # 步骤5：验证回滚后状态
                print("\n--- 步骤5：验证回滚后状态 ---")
                cur.execute("""
                    SELECT 
                        d.id as device_id,
                        d.name as device_name,
                        COUNT(drp.id) as rated_params_count
                    FROM dim_devices d
                    LEFT JOIN device_rated_params drp ON drp.device_id = d.id
                    WHERE d.id = 154
                    GROUP BY d.id, d.name
                """)
                rollback_state = cur.fetchone()
                if rollback_state and rollback_state[2] == before_state[2]:
                    print(f"  ✅ 回滚成功！数据恢复到测试前状态")
                    print(f"  设备ID: {rollback_state[0]}")
                    print(f"  设备名称: {rollback_state[1]}")
                    print(f"  额定参数数量: {rollback_state[2]}")
                else:
                    print(f"  ❌ 回滚异常")
                
                print("\n" + "="*80)
                print("✅ 级联删除测试完成")
                print("="*80 + "\n")
                
            except Exception as e:
                print(f"\n❌ 测试失败: {e}")
                conn.rollback()
                raise


if __name__ == "__main__":
    try:
        # 初始化数据库连接
        settings = load_settings(Path("configs"))
        init_database(settings)

        # 执行测试
        test_cascade_update()
        test_cascade_delete()
    except Exception as e:
        logger.error(f"测试执行失败: {e}", exc_info=True)
        sys.exit(1)

