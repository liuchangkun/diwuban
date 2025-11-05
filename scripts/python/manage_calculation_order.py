"""
管理计算顺序的工具脚本

功能：
1. 查看当前计算顺序
2. 更新计算顺序
3. 删除计算顺序
4. 验证计算顺序
5. 查看缓存统计
"""

import sys
from pathlib import Path
from typing import List

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import init_database, get_connection
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.services.calculation.dependency_analyzer import DependencyAnalyzer


def view_calculation_order(metrics: List[str]):
    """查看计算顺序"""
    print("\n" + "="*80)
    print("查看计算顺序")
    print("="*80)
    
    analyzer = DependencyAnalyzer()
    
    print(f"\n指标列表: {metrics}")
    
    # 从数据库读取
    db_order = analyzer.load_calculation_order_from_db(metrics)
    if db_order:
        print(f"\n数据库中的计算顺序:")
        for idx, metric in enumerate(db_order):
            deps = analyzer.get_dependencies(metric)
            print(f"  {idx+1}. {metric}")
            if deps:
                print(f"     依赖: {', '.join(deps)}")
    else:
        print(f"\n数据库中没有找到计算顺序记录")
    
    # 动态计算
    print(f"\n动态计算的计算顺序:")
    dynamic_order = analyzer.get_calculation_order(metrics, use_cache=False)
    for idx, metric in enumerate(dynamic_order):
        deps = analyzer.get_dependencies(metric)
        print(f"  {idx+1}. {metric}")
        if deps:
            print(f"     依赖: {', '.join(deps)}")
    
    # 比较
    if db_order and db_order != dynamic_order:
        print(f"\n⚠️ 警告：数据库中的顺序与动态计算的顺序不一致！")
        print(f"   数据库: {' → '.join(db_order)}")
        print(f"   动态计算: {' → '.join(dynamic_order)}")


def update_calculation_order(metrics: List[str], new_order: List[str], updated_by: str = "manual"):
    """更新计算顺序"""
    print("\n" + "="*80)
    print("更新计算顺序")
    print("="*80)
    
    analyzer = DependencyAnalyzer()
    
    print(f"\n原指标列表: {metrics}")
    print(f"新计算顺序: {new_order}")
    print(f"更新者: {updated_by}")
    
    # 验证并更新
    success = analyzer.update_calculation_order(metrics, new_order, updated_by)
    
    if success:
        print(f"\n✅ 更新成功！")
    else:
        print(f"\n❌ 更新失败！请检查依赖关系是否满足。")


def delete_calculation_order(metrics: List[str]):
    """删除计算顺序"""
    print("\n" + "="*80)
    print("删除计算顺序")
    print("="*80)
    
    print(f"\n指标列表: {metrics}")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    DELETE FROM metric_calculation_order
                    WHERE metric_key = ANY(%s)
                """
                cur.execute(query, (metrics,))
                deleted_count = cur.rowcount
                conn.commit()
                
                print(f"\n✅ 删除成功！删除了 {deleted_count} 条记录。")
    except Exception as e:
        print(f"\n❌ 删除失败：{e}")


def validate_calculation_order(metrics: List[str], order: List[str]):
    """验证计算顺序"""
    print("\n" + "="*80)
    print("验证计算顺序")
    print("="*80)
    
    analyzer = DependencyAnalyzer()
    
    print(f"\n指标列表: {metrics}")
    print(f"计算顺序: {order}")
    
    # 1. 验证指标集合
    if set(order) != set(metrics):
        print(f"\n❌ 验证失败：指标集合不一致")
        print(f"   缺少: {set(metrics) - set(order)}")
        print(f"   多余: {set(order) - set(metrics)}")
        return False
    
    # 2. 验证依赖关系
    print(f"\n验证依赖关系:")
    all_valid = True
    for idx, metric_key in enumerate(order):
        deps = analyzer.get_dependencies(metric_key)
        print(f"  {idx+1}. {metric_key}")
        if deps:
            print(f"     依赖: {', '.join(deps)}")
            for dep in deps:
                if dep not in order:
                    continue
                dep_idx = order.index(dep)
                if dep_idx >= idx:
                    print(f"     ❌ 依赖关系违反: {dep} 在 {metric_key} 之后")
                    all_valid = False
                else:
                    print(f"     ✅ {dep} 在 {metric_key} 之前")
    
    if all_valid:
        print(f"\n✅ 验证通过：计算顺序满足所有依赖关系")
    else:
        print(f"\n❌ 验证失败：计算顺序违反依赖关系")
    
    return all_valid


def view_cache_stats():
    """查看缓存统计"""
    print("\n" + "="*80)
    print("缓存统计")
    print("="*80)
    
    analyzer = DependencyAnalyzer()
    stats = analyzer.get_cache_stats()
    
    print(f"\n缓存大小: {stats['cache_size']}")
    print(f"缓存命中: {stats['cache_hits']}")
    print(f"缓存未命中: {stats['cache_misses']}")
    print(f"总查询次数: {stats['total_queries']}")
    print(f"命中率: {stats['hit_rate']:.1%}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="管理计算顺序")
    parser.add_argument('action', choices=['view', 'update', 'delete', 'validate', 'cache'],
                        help="操作类型")
    parser.add_argument('--metrics', nargs='+', help="指标列表")
    parser.add_argument('--order', nargs='+', help="计算顺序")
    parser.add_argument('--updated-by', default='manual', help="更新者标识")
    
    args = parser.parse_args()
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 执行操作
    if args.action == 'view':
        if not args.metrics:
            print("错误：需要指定 --metrics 参数")
            return 1
        view_calculation_order(args.metrics)
    
    elif args.action == 'update':
        if not args.metrics or not args.order:
            print("错误：需要指定 --metrics 和 --order 参数")
            return 1
        update_calculation_order(args.metrics, args.order, args.updated_by)
    
    elif args.action == 'delete':
        if not args.metrics:
            print("错误：需要指定 --metrics 参数")
            return 1
        delete_calculation_order(args.metrics)
    
    elif args.action == 'validate':
        if not args.metrics or not args.order:
            print("错误：需要指定 --metrics 和 --order 参数")
            return 1
        validate_calculation_order(args.metrics, args.order)
    
    elif args.action == 'cache':
        view_cache_stats()
    
    return 0


if __name__ == "__main__":
    exit(main())

