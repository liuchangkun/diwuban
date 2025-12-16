#!/usr/bin/env python3
"""
补充 calculation_method_registry 表的 allowed_device_types 字段

功能：根据 metric_key 前缀填充 allowed_device_types 字段
作者：AI
创建日期：2025-01-17
最后修改：2025-01-17

使用方法：
    # 干运行模式（只查询，不更新）
    python backfill_allowed_device_types.py --dry-run

    # 正常执行（更新数据）
    python backfill_allowed_device_types.py

    # 详细日志模式
    python backfill_allowed_device_types.py --verbose

说明：
    - 本脚本是幂等的，可以安全地多次执行
    - 只更新 allowed_device_types 为空数组的记录
    - 使用事务确保原子性，失败时自动回滚
    - 生成详细的更新报告（更新前/后对比）

更新规则：
    - pump_% → '{pump}'::text[]
    - main_pipeline_% → '{main_pipeline}'::text[]
    - pool_% 或 clear_water_pool_% → '{clear_water_pool}'::text[]
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import get_connection, init_database, cleanup_database
from app.core.logging.setup import log_sql

# 配置日志
logger = logging.getLogger(__name__)


def query_current_state(cur) -> List[Dict[str, Any]]:
    """
    查询当前状态

    Args:
        cur: 数据库游标

    Returns:
        当前所有记录的列表
    """
    sql = """
        SELECT 
            method_id,
            metric_key,
            allowed_device_types
        FROM calculation_method_registry
        ORDER BY metric_key, method_id
    """
    cur.execute(sql)
    rows = cur.fetchall()
    
    results = []
    for row in rows:
        results.append({
            'method_id': row[0],
            'metric_key': row[1],
            'allowed_device_types': row[2] if row[2] else []
        })
    
    return results


def count_empty_records(cur) -> int:
    """
    统计空数组的记录数

    Args:
        cur: 数据库游标

    Returns:
        空数组记录数
    """
    sql = """
        SELECT COUNT(*)
        FROM calculation_method_registry
        WHERE allowed_device_types = '{}'::text[]
    """
    cur.execute(sql)
    return cur.fetchone()[0]


def update_allowed_device_types(cur, dry_run: bool = False) -> Dict[str, int]:
    """
    执行更新操作

    Args:
        cur: 数据库游标
        dry_run: 是否为干运行模式

    Returns:
        更新统计信息
    """
    stats = {
        'pump': 0,
        'main_pipeline': 0,
        'clear_water_pool': 0,
        'total': 0
    }

    if dry_run:
        logger.info("干运行模式：只查询，不执行更新")
        
        # 查询将要更新的记录数
        sql_pump = """
            SELECT COUNT(*)
            FROM calculation_method_registry
            WHERE metric_key LIKE 'pump_%'
              AND allowed_device_types = '{}'::text[]
        """
        cur.execute(sql_pump)
        stats['pump'] = cur.fetchone()[0]
        
        sql_pipeline = """
            SELECT COUNT(*)
            FROM calculation_method_registry
            WHERE metric_key LIKE 'main_pipeline_%'
              AND allowed_device_types = '{}'::text[]
        """
        cur.execute(sql_pipeline)
        stats['main_pipeline'] = cur.fetchone()[0]
        
        sql_pool = """
            SELECT COUNT(*)
            FROM calculation_method_registry
            WHERE (metric_key LIKE 'pool_%' OR metric_key LIKE 'clear_water_pool_%')
              AND allowed_device_types = '{}'::text[]
        """
        cur.execute(sql_pool)
        stats['clear_water_pool'] = cur.fetchone()[0]
        
    else:
        logger.info("执行更新操作...")
        
        # 更新1：pump_% 指标
        sql_pump = """
            UPDATE calculation_method_registry
            SET allowed_device_types = '{pump}'::text[]
            WHERE metric_key LIKE 'pump_%'
              AND allowed_device_types = '{}'::text[]
        """
        cur.execute(sql_pump)
        stats['pump'] = cur.rowcount
        logger.info(f"更新 pump_% 指标：{stats['pump']} 条记录")
        
        # 更新2：main_pipeline_% 指标
        sql_pipeline = """
            UPDATE calculation_method_registry
            SET allowed_device_types = '{main_pipeline}'::text[]
            WHERE metric_key LIKE 'main_pipeline_%'
              AND allowed_device_types = '{}'::text[]
        """
        cur.execute(sql_pipeline)
        stats['main_pipeline'] = cur.rowcount
        logger.info(f"更新 main_pipeline_% 指标：{stats['main_pipeline']} 条记录")
        
        # 更新3：pool_% 和 clear_water_pool_% 指标
        sql_pool = """
            UPDATE calculation_method_registry
            SET allowed_device_types = '{clear_water_pool}'::text[]
            WHERE (metric_key LIKE 'pool_%' OR metric_key LIKE 'clear_water_pool_%')
              AND allowed_device_types = '{}'::text[]
        """
        cur.execute(sql_pool)
        stats['clear_water_pool'] = cur.rowcount
        logger.info(f"更新 pool_% 和 clear_water_pool_% 指标：{stats['clear_water_pool']} 条记录")
    
    stats['total'] = stats['pump'] + stats['main_pipeline'] + stats['clear_water_pool']
    
    return stats


def generate_report(before: List[Dict[str, Any]], after: List[Dict[str, Any]], stats: Dict[str, int], dry_run: bool):
    """
    生成更新报告

    Args:
        before: 更新前的数据
        after: 更新后的数据
        stats: 更新统计信息
        dry_run: 是否为干运行模式
    """
    print("\n" + "=" * 80)
    print("📊 更新报告")
    print("=" * 80)
    
    if dry_run:
        print("\n🔍 干运行模式 - 预览将要更新的记录")
    else:
        print("\n✅ 更新完成")
    
    print(f"\n📈 更新统计：")
    print(f"  - pump_% 指标：{stats['pump']} 条")
    print(f"  - main_pipeline_% 指标：{stats['main_pipeline']} 条")
    print(f"  - pool_% 和 clear_water_pool_% 指标：{stats['clear_water_pool']} 条")
    print(f"  - 总计：{stats['total']} 条")
    
    # 统计更新前的空数组数量
    empty_before = sum(1 for r in before if not r['allowed_device_types'])
    empty_after = sum(1 for r in after if not r['allowed_device_types'])
    
    print(f"\n📋 数据状态：")
    print(f"  - 更新前空数组记录：{empty_before} 条")
    print(f"  - 更新后空数组记录：{empty_after} 条")
    
    if not dry_run and empty_after > 0:
        print(f"\n⚠️  警告：仍有 {empty_after} 条记录的 allowed_device_types 为空数组")
        print("这些记录可能不符合更新规则，请手动检查：")
        for record in after:
            if not record['allowed_device_types']:
                print(f"  - {record['metric_key']} ({record['method_id']})")
    
    print("\n" + "=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='补充 calculation_method_registry 表的 allowed_device_types 字段')
    parser.add_argument('--dry-run', action='store_true', help='干运行模式（只查询，不更新）')
    parser.add_argument('--verbose', action='store_true', help='详细日志模式')
    args = parser.parse_args()
    
    # 配置日志级别
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        # 加载配置
        logger.info("加载配置...")
        settings = load_settings(Path('configs'))

        # 初始化数据库连接池
        logger.info("初始化数据库连接池...")
        init_database(settings)

        # 连接数据库
        logger.info("连接数据库...")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 查询更新前状态
                logger.info("查询更新前状态...")
                before = query_current_state(cur)
                empty_count_before = count_empty_records(cur)
                logger.info(f"更新前空数组记录数：{empty_count_before}")
                
                # 执行更新
                stats = update_allowed_device_types(cur, dry_run=args.dry_run)
                
                # 查询更新后状态
                logger.info("查询更新后状态...")
                after = query_current_state(cur)
                empty_count_after = count_empty_records(cur)
                logger.info(f"更新后空数组记录数：{empty_count_after}")
                
                # 生成报告
                generate_report(before, after, stats, dry_run=args.dry_run)
                
                if not args.dry_run:
                    # 提交事务
                    conn.commit()
                    logger.info("事务已提交")
                else:
                    # 回滚事务
                    conn.rollback()
                    logger.info("干运行模式：事务已回滚")
        
        logger.info("脚本执行完成")
        return 0

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        return 1
    finally:
        # 关闭数据库连接池
        try:
            cleanup_database()
            logger.info("数据库连接池已关闭")
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

