"""
备份管理器模块

负责数据库表的备份和恢复，支持版本管理和增量备份。
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2

_log = logging.getLogger(__name__)


class BackupManager:
    """
    备份管理器
    
    功能：
    1. 备份指定的数据库表到SQL文件
    2. 支持版本管理（保留最新N个版本）
    3. 支持增量备份（只备份变化的表）
    4. 从备份恢复表数据
    """
    
    def __init__(self, backup_dir: Path = Path("backups"), keep_versions: int = 60):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份目录路径
            keep_versions: 保留的版本数量（默认60个）
        """
        self.backup_dir = backup_dir
        self.keep_versions = keep_versions
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        _log.info(f"[备份管理器] 初始化完成，备份目录: {self.backup_dir}, 保留版本数: {self.keep_versions}")
    
    def backup_tables(self, cur, tables: List[str]) -> Dict[str, Any]:
        """
        备份指定的表
        
        Args:
            cur: 数据库游标
            tables: 需要备份的表名列表
            
        Returns:
            备份结果字典，格式：
            {
                "table_name": {
                    "status": "ok" | "skipped" | "error",
                    "version": 版本号,
                    "rows": 行数,
                    "file": 备份文件路径,
                    "message": 消息
                }
            }
        """
        result = {}
        
        for table_name in tables:
            try:
                _log.info(f"[备份表] 开始备份表: {table_name}")
                
                # 检查表是否存在
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """, (table_name,))
                
                if not cur.fetchone()[0]:
                    result[table_name] = {
                        "status": "error",
                        "message": f"表 {table_name} 不存在"
                    }
                    _log.warning(f"[备份表] {table_name}: 表不存在")
                    continue
                
                # 检查表是否发生变化
                if not self._table_has_changed(cur, table_name):
                    result[table_name] = {
                        "status": "skipped",
                        "message": "表未发生变化，跳过备份"
                    }
                    _log.info(f"[备份表] {table_name}: 未发生变化，跳过")
                    continue
                
                # 生成SQL备份
                sql_content = self._generate_sql_backup(cur, table_name)
                
                # 获取下一个版本号
                version = self._get_next_version(table_name)
                
                # 保存备份文件
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{table_name}_v{version}_{timestamp}.sql"
                table_backup_dir = self.backup_dir / table_name
                table_backup_dir.mkdir(parents=True, exist_ok=True)
                backup_file = table_backup_dir / filename
                
                backup_file.write_text(sql_content, encoding="utf-8")
                
                # 获取行数
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cur.fetchone()[0]
                
                # 清理旧版本
                self._cleanup_old_versions(table_name)
                
                result[table_name] = {
                    "status": "ok",
                    "version": version,
                    "rows": row_count,
                    "file": str(backup_file),
                    "message": f"备份成功，版本 v{version}"
                }
                
                _log.info(f"[备份表] {table_name}: 备份成功，版本 v{version}，{row_count} 行")
                
            except Exception as e:
                result[table_name] = {
                    "status": "error",
                    "message": str(e)
                }
                _log.error(f"[备份表] {table_name}: 备份失败 - {e}")
        
        return result
    
    def restore_table(self, cur, table_name: str, version: Optional[int] = None, target_table: Optional[str] = None) -> Dict[str, Any]:
        """
        从备份恢复表数据

        Args:
            cur: 数据库游标
            table_name: 表名
            version: 版本号（None表示使用最新版本）
            target_table: 目标表名（None表示与table_name相同，用于恢复到临时表）

        Returns:
            恢复结果字典，格式：
            {
                "status": "ok" | "error",
                "version": 版本号,
                "file": 备份文件路径,
                "message": 消息
            }
        """
        try:
            _log.info(f"[恢复表] 开始恢复表: {table_name}, 版本: {version or '最新'}")
            
            # 查找备份文件
            table_backup_dir = self.backup_dir / table_name
            
            if not table_backup_dir.exists():
                return {
                    "status": "error",
                    "message": f"表 {table_name} 没有备份"
                }
            
            # 获取所有备份文件
            backup_files = sorted(
                table_backup_dir.glob(f"{table_name}_v*.sql"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if not backup_files:
                return {
                    "status": "error",
                    "message": f"表 {table_name} 没有备份文件"
                }
            
            # 选择备份文件
            if version is None:
                # 使用最新版本
                backup_file = backup_files[0]
            else:
                # 查找指定版本
                backup_file = None
                for f in backup_files:
                    if f"_v{version}_" in f.name:
                        backup_file = f
                        break
                
                if backup_file is None:
                    return {
                        "status": "error",
                        "message": f"表 {table_name} 的版本 v{version} 不存在"
                    }
            
            # 读取并执行SQL
            sql_content = backup_file.read_text(encoding="utf-8")

            # 如果指定了目标表，替换表名
            if target_table and target_table != table_name:
                sql_content = sql_content.replace(f"INSERT INTO {table_name}", f"INSERT INTO {target_table}")

            cur.execute(sql_content)
            
            # 提取版本号
            import re
            match = re.search(r'_v(\d+)_', backup_file.name)
            actual_version = int(match.group(1)) if match else 0
            
            _log.info(f"[恢复表] {table_name}: 恢复成功，版本 v{actual_version}")
            
            return {
                "status": "ok",
                "version": actual_version,
                "file": str(backup_file),
                "message": f"恢复成功，版本 v{actual_version}"
            }
            
        except Exception as e:
            _log.error(f"[恢复表] {table_name}: 恢复失败 - {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _table_has_changed(self, cur, table_name: str) -> bool:
        """
        检测表是否发生变化
        
        策略：
        1. 检查行数是否变化
        2. 如果行数相同，计算整表数据的MD5
        
        Args:
            cur: 数据库游标
            table_name: 表名
            
        Returns:
            True表示表已变化，False表示未变化
        """
        try:
            # 获取当前行数
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            current_row_count = cur.fetchone()[0]
            
            # 查找最新备份文件
            table_backup_dir = self.backup_dir / table_name
            
            if not table_backup_dir.exists():
                # 没有备份，认为已变化
                return True
            
            backup_files = sorted(
                table_backup_dir.glob(f"{table_name}_v*.sql"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if not backup_files:
                # 没有备份文件，认为已变化
                return True
            
            # 从最新备份文件中提取行数
            latest_backup = backup_files[0]
            content = latest_backup.read_text(encoding="utf-8")
            
            import re
            match = re.search(r'-- 行数: (\d+)', content)
            
            if not match:
                # 无法提取行数，认为已变化
                return True
            
            backup_row_count = int(match.group(1))
            
            # 行数不同，认为已变化
            if current_row_count != backup_row_count:
                return True
            
            # 行数相同，计算MD5
            cur.execute(f"SELECT md5(CAST((array_agg(t.* ORDER BY (t.*)::text))AS text)) FROM {table_name} t")
            current_md5 = cur.fetchone()[0]
            
            # 从备份文件中提取MD5
            match = re.search(r'-- MD5: ([a-f0-9]+)', content)
            
            if not match:
                # 无法提取MD5，认为已变化
                return True
            
            backup_md5 = match.group(1)
            
            # 比较MD5
            return current_md5 != backup_md5
            
        except Exception as e:
            _log.warning(f"[变化检测] {table_name}: 检测失败 - {e}，默认认为已变化")
            return True
    
    def _generate_sql_backup(self, cur, table_name: str) -> str:
        """
        生成SQL备份脚本
        
        格式：INSERT ... ON CONFLICT DO UPDATE
        
        Args:
            cur: 数据库游标
            table_name: 表名
            
        Returns:
            SQL脚本内容
        """
        # 获取表结构
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))

        columns = cur.fetchall()
        column_names = [col[0] for col in columns]
        column_types = {col[0]: col[1] for col in columns}  # 保存类型映射
        
        # 获取主键
        cur.execute("""
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """, (table_name,))
        
        primary_keys = [row[0] for row in cur.fetchall()]
        
        # 获取数据
        cur.execute(f"SELECT * FROM {table_name}")
        rows = cur.fetchall()
        
        # 计算MD5
        cur.execute(f"SELECT md5(CAST((array_agg(t.* ORDER BY (t.*)::text))AS text)) FROM {table_name} t")
        table_md5 = cur.fetchone()[0] or ""
        
        # 生成SQL
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql_lines = [
            f"-- 备份表: {table_name}",
            f"-- 时间: {timestamp}",
            f"-- 行数: {len(rows)}",
            f"-- MD5: {table_md5}",
            "",
        ]
        
        if not rows:
            sql_lines.append(f"-- 表 {table_name} 为空，无数据需要备份")
            return "\n".join(sql_lines)
        
        # 生成INSERT语句
        column_list = ", ".join(column_names)

        # 生成ON CONFLICT子句（如果有主键）
        on_conflict_clause = ""
        if primary_keys:
            pk_list = ", ".join(primary_keys)
            update_set = ", ".join([
                f"{col} = EXCLUDED.{col}"
                for col in column_names
                if col not in primary_keys
            ])

            if update_set:
                on_conflict_clause = f" ON CONFLICT ({pk_list}) DO UPDATE SET {update_set}"
            else:
                on_conflict_clause = f" ON CONFLICT ({pk_list}) DO NOTHING"

        for row in rows:
            values = []
            for col_name, val in zip(column_names, row):
                data_type = column_types.get(col_name, '')

                if val is None:
                    values.append("NULL")
                elif isinstance(val, bool):
                    # 布尔类型（必须在int检查之前，因为bool是int的子类）
                    values.append("TRUE" if val else "FALSE")
                elif isinstance(val, (int, float)):
                    # 数值类型
                    values.append(str(val))
                elif data_type in ('timestamp without time zone', 'timestamp with time zone', 'timestamptz', 'date', 'time without time zone', 'time with time zone'):
                    # 时间戳类型：转换为字符串并加引号
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")
                elif isinstance(val, (list, dict)):
                    # JSON/JSONB/数组类型
                    import json
                    escaped = json.dumps(val).replace("'", "''")
                    values.append(f"'{escaped}'")
                elif isinstance(val, str):
                    # 字符串类型：转义单引号
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    # 其他类型：转换为字符串并加引号
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")

            value_list = ", ".join(values)
            sql_lines.append(f"INSERT INTO {table_name} ({column_list}) VALUES ({value_list}){on_conflict_clause};")

        return "\n".join(sql_lines)
    
    def _get_next_version(self, table_name: str) -> int:
        """
        获取下一个版本号
        
        Args:
            table_name: 表名
            
        Returns:
            下一个版本号
        """
        table_backup_dir = self.backup_dir / table_name
        
        if not table_backup_dir.exists():
            return 1
        
        backup_files = list(table_backup_dir.glob(f"{table_name}_v*.sql"))
        
        if not backup_files:
            return 1
        
        # 提取所有版本号
        import re
        versions = []
        for f in backup_files:
            match = re.search(r'_v(\d+)_', f.name)
            if match:
                versions.append(int(match.group(1)))
        
        if not versions:
            return 1
        
        return max(versions) + 1
    
    def _cleanup_old_versions(self, table_name: str) -> None:
        """
        清理旧版本（保留最新N个）
        
        Args:
            table_name: 表名
        """
        table_backup_dir = self.backup_dir / table_name
        
        if not table_backup_dir.exists():
            return
        
        backup_files = sorted(
            table_backup_dir.glob(f"{table_name}_v*.sql"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # 删除超出保留数量的备份
        files_to_remove = backup_files[self.keep_versions:]
        
        for f in files_to_remove:
            try:
                f.unlink()
                _log.info(f"[清理备份] 删除旧版本: {f.name}")
            except Exception as e:
                _log.warning(f"[清理备份] 删除失败: {f.name} - {e}")

