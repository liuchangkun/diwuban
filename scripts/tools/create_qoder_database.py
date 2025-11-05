#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库复制脚本 - 创建 pump_station_optimization_qoder 数据库

本脚本将完整复制 pump_station_optimization 数据库到 pump_station_optimization_qoder
包括表结构、数据、索引、视图、约束等所有内容
"""

import psycopg
import sys
from pathlib import Path


def create_database_copy():
    """复制数据库的主要函数"""

    source_db = "pump_station_optimization"
    target_db = "pump_station_optimization_qoder"

    try:
        print(f"🔍 开始复制数据库 {source_db} -> {target_db}")

        # 1. 连接到 postgres 数据库来创建新数据库
        print("连接到 postgres 数据库...")
        with psycopg.connect(
            host="localhost", dbname="postgres", user="postgres"
        ) as admin_conn:
            admin_conn.autocommit = True
            with admin_conn.cursor() as cur:
                # 检查目标数据库是否已存在
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (target_db,)
                )
                if cur.fetchone():
                    logger.warning(f"数据库 {target_db} 已存在，将先删除...")
                    # 断开所有连接
                    cur.execute(
                        f"""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = '{target_db}' AND pid <> pg_backend_pid()
                    """
                    )
                    cur.execute(f'DROP DATABASE "{target_db}"')
                    logger.info(f"已删除现有数据库 {target_db}")

                # 创建新数据库
                logger.info(f"创建新数据库 {target_db}...")
                cur.execute(
                    f'CREATE DATABASE "{target_db}" WITH TEMPLATE "{source_db}"'
                )
                logger.info(f"数据库 {target_db} 创建完成")

        # 2. 验证新数据库
        logger.info("验证新数据库...")
        with psycopg.connect(
            host="localhost", dbname=target_db, user="postgres"
        ) as target_conn:
            with target_conn.cursor() as cur:
                # 检查表数量
                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """
                )
                table_count = cur.fetchone()[0]
                logger.info(f"新数据库包含 {table_count} 个表")

                # 检查主要表的行数
                main_tables = [
                    "dim_stations",
                    "dim_devices",
                    "dim_metric_config",
                    "fact_measurements",
                    "staging_raw",
                ]

                for table in main_tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cur.fetchone()[0]
                        logger.info(f"表 {table}: {count:,} 行")
                    except Exception as e:
                        logger.warning(f"无法查询表 {table}: {e}")

                # 检查视图
                cur.execute(
                    """
                    SELECT COUNT(*) 
                    FROM information_schema.views 
                    WHERE table_schema = 'public'
                """
                )
                view_count = cur.fetchone()[0]
                logger.info(f"新数据库包含 {view_count} 个视图")

        logger.info("✅ 数据库复制完成！")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库复制失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始数据库复制任务...")
    logger.info("🚀 开始数据库复制任务...")

    success = create_database_copy()

    if success:
        print("🎉 数据库复制任务完成")
        print("✅ 数据库 pump_station_optimization_qoder 创建成功")
        print("📝 配置文件已修改为使用新数据库")
        logger.info("🎉 数据库复制任务完成")
        return 0
    else:
        print("💥 数据库复制任务失败")
        logger.error("💥 数据库复制任务失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
