"""
应用设备运行阈值学习存储过程迁移

职责：
- 执行4个新创建的存储过程SQL文件
- 验证存储过程是否成功创建
- 提供详细的执行日志

作者：AI
创建日期：2025-10-24
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.gateway import get_conn
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
_log = logging.getLogger(__name__)


def apply_migrations():
    """应用存储过程迁移"""
    
    # 要执行的SQL文件列表
    migration_files = [
        "scripts/sql/migrations/052_create_sp_refresh_device_running_thresholds_current.sql",
        "scripts/sql/migrations/053_create_sp_refresh_device_running_thresholds_power.sql",
        "scripts/sql/migrations/054_create_sp_refresh_device_running_thresholds_frequency.sql",
        "scripts/sql/migrations/055_create_sp_refresh_device_running_thresholds_timing.sql",
    ]
    
    # 对应的存储过程名称
    procedure_names = [
        "sp_refresh_device_running_thresholds_current",
        "sp_refresh_device_running_thresholds_power",
        "sp_refresh_device_running_thresholds_frequency",
        "sp_refresh_device_running_thresholds_timing",
    ]
    
    _log.info("=" * 80)
    _log.info("开始应用设备运行阈值学习存储过程迁移")
    _log.info("=" * 80)

    settings = load_settings(Path("configs"))
    success_count = 0
    failed_count = 0

    with get_conn(settings) as conn:
        for i, (sql_file, proc_name) in enumerate(zip(migration_files, procedure_names), 1):
            _log.info(f"\n[{i}/4] 执行迁移：{sql_file}")
            
            sql_path = Path(sql_file)
            if not sql_path.exists():
                _log.error(f"  ❌ SQL文件不存在：{sql_path}")
                failed_count += 1
                continue
            
            try:
                # 读取SQL文件
                sql_content = sql_path.read_text(encoding="utf-8")
                _log.info(f"  📄 SQL文件大小：{len(sql_content)} 字符")

                # 执行SQL（使用独立的事务）
                with conn.cursor() as cur:
                    # 先提交任何待处理的事务
                    conn.commit()
                    # 执行SQL
                    cur.execute(sql_content)
                    # 提交
                    conn.commit()
                    _log.info(f"  ✅ SQL执行成功")

                # 验证存储过程是否创建成功
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname = 'public'
                          AND p.proname = %s
                        """,
                        (proc_name,)
                    )
                    count = cur.fetchone()[0]

                    if count > 0:
                        _log.info(f"  ✅ 存储过程已创建：{proc_name}")
                        success_count += 1
                    else:
                        _log.error(f"  ❌ 存储过程未找到：{proc_name}")
                        failed_count += 1

            except Exception as e:
                _log.error(f"  ❌ 执行失败：{e}")
                failed_count += 1
                try:
                    conn.rollback()
                except:
                    pass
                # 继续执行下一个
    
    _log.info("\n" + "=" * 80)
    _log.info(f"迁移完成：成功 {success_count}/4，失败 {failed_count}/4")
    _log.info("=" * 80)
    
    return success_count == 4


if __name__ == "__main__":
    try:
        success = apply_migrations()
        sys.exit(0 if success else 1)
    except Exception as e:
        _log.error(f"迁移失败：{e}", exc_info=True)
        sys.exit(1)

