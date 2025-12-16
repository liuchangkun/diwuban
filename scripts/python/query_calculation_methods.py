#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
查询计算方法统计信息
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader import load_settings


def query_method_statistics():
    """查询计算方法统计信息"""
    
    queries = {
        "按指标统计方法数量": """
            SELECT 
                metric_key, 
                COUNT(*) as method_count,
                STRING_AGG(method_code, ', ' ORDER BY priority DESC) as methods
            FROM calculation_method_registry 
            WHERE is_enabled = true 
            GROUP BY metric_key 
            ORDER BY metric_key;
        """,
        
        "总体统计": """
            SELECT 
                COUNT(*) as total_methods,
                COUNT(DISTINCT metric_key) as total_metrics,
                COUNT(CASE WHEN is_enabled THEN 1 END) as enabled_methods,
                COUNT(CASE WHEN NOT is_enabled THEN 1 END) as disabled_methods
            FROM calculation_method_registry;
        """,
        
        "依赖关系统计": """
            SELECT 
                metric_key,
                method_code,
                priority,
                dependencies,
                accuracy_level
            FROM calculation_method_registry 
            WHERE is_enabled = true 
            ORDER BY metric_key, priority DESC;
        """
    }
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询1: 按指标统计
            print("=" * 80)
            print("📊 按指标统计方法数量")
            print("=" * 80)
            cur.execute(queries["按指标统计方法数量"])
            rows = cur.fetchall()
            for row in rows:
                print(f"{row[0]:40s} | {row[1]:2d} 个方法 | {row[2]}")
            
            # 查询2: 总体统计
            print("\n" + "=" * 80)
            print("📊 总体统计")
            print("=" * 80)
            cur.execute(queries["总体统计"])
            row = cur.fetchone()
            print(f"总方法数: {row[0]}")
            print(f"总指标数: {row[1]}")
            print(f"启用方法: {row[2]}")
            print(f"禁用方法: {row[3]}")
            
            # 查询3: 依赖关系
            print("\n" + "=" * 80)
            print("📊 依赖关系详情")
            print("=" * 80)
            cur.execute(queries["依赖关系统计"])
            rows = cur.fetchall()
            
            current_metric = None
            for row in rows:
                metric_key, method_code, priority, dependencies, accuracy = row
                if metric_key != current_metric:
                    print(f"\n【{metric_key}】")
                    current_metric = metric_key
                
                deps_str = ', '.join(dependencies) if dependencies else '无'
                print(f"  - {method_code:15s} | 优先级:{priority:3d} | 精度:{accuracy:6s} | 依赖: {deps_str}")


if __name__ == "__main__":
    try:
        # 初始化数据库连接
        settings = load_settings(Path("configs"))
        init_database(settings)

        query_method_statistics()
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

