#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 RESTRICT 外键约束是否生效

用途: 验证删除 dim_metric_config 记录时，如果有依赖的 calculation_parameters 记录，会抛出错误
创建日期: 2025-11-14
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import get_connection, initialize_pool, close_pool


def test_restrict_constraint() -> bool:
    """测试 RESTRICT 约束"""
    print("=" * 80)
    print("测试 RESTRICT 外键约束")
    print("=" * 80)
    print()

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查询一个被引用的 metric_key
                cur.execute("""
                    SELECT metric_key 
                    FROM calculation_parameters 
                    LIMIT 1
                """)
                row = cur.fetchone()
                
                if not row:
                    print("❌ calculation_parameters 表为空，无法测试")
                    return False
                
                test_metric_key = row[0]
                print(f"📋 测试 metric_key: {test_metric_key}")
                print()
                
                # 尝试删除这个 metric_key（应该失败）
                print("🔄 尝试删除 dim_metric_config 中的记录...")
                print(f"   DELETE FROM dim_metric_config WHERE metric_key = '{test_metric_key}'")
                print()
                
                try:
                    cur.execute(f"""
                        DELETE FROM dim_metric_config 
                        WHERE metric_key = '{test_metric_key}'
                    """)
                    conn.commit()
                    
                    # 如果执行到这里，说明删除成功了（不应该发生）
                    print("❌ 测试失败: 删除成功，RESTRICT 约束未生效！")
                    print()
                    
                    # 回滚删除
                    conn.rollback()
                    return False
                    
                except Exception as e:
                    # 预期会抛出外键约束错误
                    error_msg = str(e)
                    
                    if "violates foreign key constraint" in error_msg or "RESTRICT" in error_msg:
                        print("✅ 测试成功: 删除被阻止，RESTRICT 约束生效！")
                        print()
                        print(f"📋 错误信息: {error_msg}")
                        print()
                        
                        # 回滚事务
                        conn.rollback()
                        return True
                    else:
                        print(f"❌ 测试失败: 抛出了意外的错误")
                        print(f"   错误信息: {error_msg}")
                        print()
                        
                        # 回滚事务
                        conn.rollback()
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
        # 测试约束
        success = test_restrict_constraint()
        
        if success:
            print("=" * 80)
            print("✅ RESTRICT 约束测试通过！")
            print("=" * 80)
            print()
            print("📋 结论:")
            print("  - calculation_parameters.metric_key 外键使用 ON DELETE RESTRICT")
            print("  - 删除 dim_metric_config 记录时，如果有依赖的 calculation_parameters 记录，会抛出错误")
            print("  - 这防止了意外的级联删除，保护了 calculation_parameters 表的数据")
            print()
        
        return 0 if success else 1
    finally:
        # 关闭连接池
        try:
            close_pool()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

