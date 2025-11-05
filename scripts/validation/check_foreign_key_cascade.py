#!/usr/bin/env python3
"""
外键CASCADE配置检查脚本

用途：检查所有引用 dim_stations.id 和 dim_devices.id 的外键是否配置了 ON UPDATE CASCADE
作者：AI
创建日期：2025-10-29
"""
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


class ForeignKeyChecker:
    """外键配置检查器"""
    
    def __init__(self):
        self.issues: List[Dict] = []
        self.total_fks = 0
        self.cascade_fks = 0
        self.non_cascade_fks = 0
    
    def check_foreign_keys(self) -> bool:
        """
        检查所有外键的CASCADE配置
        
        Returns:
            bool: 如果所有外键都配置了CASCADE则返回True，否则返回False
        """
        print("=" * 80)
        print("外键CASCADE配置检查")
        print("=" * 80)
        print()
        
        # 查询所有引用 dim_stations 和 dim_devices 的外键
        sql = """
        SELECT 
            tc.table_schema AS 源表schema,
            tc.table_name AS 源表名,
            tc.constraint_name AS 约束名称,
            kcu.column_name AS 源列名,
            ccu.table_name AS 目标表名,
            ccu.column_name AS 目标列名,
            rc.update_rule AS UPDATE规则,
            rc.delete_rule AS DELETE规则
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        JOIN information_schema.referential_constraints AS rc
            ON rc.constraint_name = tc.constraint_name
            AND rc.constraint_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND ccu.table_name IN ('dim_stations', 'dim_devices')
            AND tc.table_schema = 'public'
        ORDER BY ccu.table_name, tc.table_name, kcu.column_name
        """
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        
        if not rows:
            print("⚠️  未找到任何引用 dim_stations 或 dim_devices 的外键")
            return True
        
        self.total_fks = len(rows)
        
        # 按目标表分组
        stations_fks = []
        devices_fks = []
        
        for row in rows:
            fk_info = {
                "源表schema": row[0],
                "源表名": row[1],
                "约束名称": row[2],
                "源列名": row[3],
                "目标表名": row[4],
                "目标列名": row[5],
                "UPDATE规则": row[6],
                "DELETE规则": row[7]
            }
            
            if row[4] == 'dim_stations':
                stations_fks.append(fk_info)
            else:
                devices_fks.append(fk_info)
            
            # 检查是否配置了CASCADE
            if row[6] == 'CASCADE':
                self.cascade_fks += 1
            else:
                self.non_cascade_fks += 1
                self.issues.append(fk_info)
        
        # 打印结果
        self._print_results(stations_fks, devices_fks)
        
        return len(self.issues) == 0
    
    def _print_results(self, stations_fks: List[Dict], devices_fks: List[Dict]):
        """打印检查结果"""
        
        # 打印 dim_stations 外键
        print(f"[1] 引用 dim_stations.id 的外键（共 {len(stations_fks)} 个）")
        print("-" * 80)
        self._print_fk_table(stations_fks)
        print()
        
        # 打印 dim_devices 外键
        print(f"[2] 引用 dim_devices.id 的外键（共 {len(devices_fks)} 个）")
        print("-" * 80)
        self._print_fk_table(devices_fks)
        print()
        
        # 打印统计信息
        print("=" * 80)
        print("检查结果统计")
        print("=" * 80)
        print(f"总外键数量: {self.total_fks}")
        print(f"已配置CASCADE: {self.cascade_fks} ({self.cascade_fks/self.total_fks*100:.1f}%)")
        print(f"未配置CASCADE: {self.non_cascade_fks} ({self.non_cascade_fks/self.total_fks*100:.1f}%)")
        print()
        
        # 打印问题列表
        if self.issues:
            print("❌ 发现以下外键未配置 ON UPDATE CASCADE：")
            print()
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. 表: {issue['源表名']}")
                print(f"   列: {issue['源列名']} -> {issue['目标表名']}.{issue['目标列名']}")
                print(f"   约束: {issue['约束名称']}")
                print(f"   UPDATE规则: {issue['UPDATE规则']} (应为 CASCADE)")
                print(f"   DELETE规则: {issue['DELETE规则']}")
                print()
        else:
            print("✅ 所有外键都已正确配置 ON UPDATE CASCADE")
        
        print("=" * 80)
    
    def _print_fk_table(self, fks: List[Dict]):
        """打印外键表格"""
        if not fks:
            print("  （无）")
            return
        
        # 表头
        print(f"{'序号':<4} {'源表名':<35} {'源列名':<20} {'UPDATE规则':<12} {'状态':<10}")
        print("-" * 80)
        
        # 数据行
        for i, fk in enumerate(fks, 1):
            status = "✅ 正确" if fk['UPDATE规则'] == 'CASCADE' else "❌ 错误"
            print(
                f"{i:<4} "
                f"{fk['源表名']:<35} "
                f"{fk['源列名']:<20} "
                f"{fk['UPDATE规则']:<12} "
                f"{status:<10}"
            )
    
    def generate_fix_sql(self) -> str:
        """
        生成修复SQL脚本
        
        Returns:
            str: 修复SQL脚本内容
        """
        if not self.issues:
            return ""
        
        sql_lines = [
            "-- ============================================",
            "-- 外键CASCADE配置修复脚本",
            "-- 自动生成时间：" + str(Path(__file__).stat().st_mtime),
            "-- ============================================",
            "",
            "BEGIN;",
            ""
        ]
        
        for issue in self.issues:
            table_name = issue['源表名']
            constraint_name = issue['约束名称']
            column_name = issue['源列名']
            ref_table = issue['目标表名']
            ref_column = issue['目标列名']
            
            sql_lines.extend([
                f"-- 修复 {table_name}.{column_name} 的外键约束",
                f"ALTER TABLE {table_name}",
                f"DROP CONSTRAINT IF EXISTS {constraint_name},",
                f"ADD CONSTRAINT {constraint_name}",
                f"    FOREIGN KEY ({column_name}) REFERENCES {ref_table}({ref_column})",
                f"    ON UPDATE CASCADE ON DELETE CASCADE;",
                ""
            ])
        
        sql_lines.extend([
            "COMMIT;",
            "",
            "-- 验证修改",
            "SELECT ",
            "    tc.table_name AS 源表名,",
            "    kcu.column_name AS 源列名,",
            "    ccu.table_name AS 目标表名,",
            "    rc.update_rule AS UPDATE规则,",
            "    rc.delete_rule AS DELETE规则",
            "FROM information_schema.table_constraints AS tc ",
            "JOIN information_schema.key_column_usage AS kcu",
            "    ON tc.constraint_name = kcu.constraint_name",
            "JOIN information_schema.constraint_column_usage AS ccu",
            "    ON ccu.constraint_name = tc.constraint_name",
            "JOIN information_schema.referential_constraints AS rc",
            "    ON rc.constraint_name = tc.constraint_name",
            "WHERE tc.constraint_type = 'FOREIGN KEY'",
            "    AND ccu.table_name IN ('dim_stations', 'dim_devices')",
            "    AND tc.table_schema = 'public'",
            "ORDER BY ccu.table_name, tc.table_name;",
            ""
        ])
        
        return "\n".join(sql_lines)


def main():
    """主函数"""
    # 初始化数据库连接
    settings = load_settings(project_root / "configs")
    init_database(settings)
    
    # 执行检查
    checker = ForeignKeyChecker()
    success = checker.check_foreign_keys()
    
    # 如果有问题，生成修复脚本
    if not success:
        fix_sql = checker.generate_fix_sql()
        fix_script_path = project_root / "scripts" / "sql" / "fix_foreign_key_cascade.sql"
        fix_script_path.parent.mkdir(parents=True, exist_ok=True)
        fix_script_path.write_text(fix_sql, encoding='utf-8')
        print(f"📝 已生成修复脚本: {fix_script_path}")
        print()
        print("⚠️  请先执行修复脚本，再进行数据迁移！")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

