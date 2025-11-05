"""
调试设备行插入和存储过程执行

职责：
- 手动插入设备行到 device_running_thresholds 表
- 调用电流阈值学习存储过程
- 验证数据是否被正确更新

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
import psycopg

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_log = logging.getLogger(__name__)


# 定义 NOTICE 处理器
def notice_handler(diag):
    """处理 PostgreSQL NOTICE 消息"""
    _log.info(f"  [NOTICE] {diag.message_primary}")


def main():
    """主函数"""
    
    _log.info("=" * 80)
    _log.info("开始调试设备行插入和存储过程执行")
    _log.info("=" * 80)
    
    settings = load_settings(Path("configs"))
    
    with get_conn(settings) as conn:
        # 添加 NOTICE 处理器
        conn.add_notice_handler(notice_handler)

        with conn.cursor() as cur:
            # 步骤1：清空表
            _log.info("\n步骤1：清空 device_running_thresholds 表")
            cur.execute("DELETE FROM device_running_thresholds")
            _log.info(f"  删除了 {cur.rowcount} 行")
            
            # 步骤2：插入设备行
            _log.info("\n步骤2：插入设备行")
            cur.execute("""
                INSERT INTO device_running_thresholds(device_id)
                SELECT id FROM dim_devices
                ON CONFLICT (device_id) DO NOTHING
            """)
            inserted = cur.rowcount
            _log.info(f"  插入了 {inserted} 行")
            
            # 步骤3：查询表
            _log.info("\n步骤3：查询表（插入后）")
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
            count = cur.fetchone()[0]
            _log.info(f"  表中现在有 {count} 行")
            
            # 步骤4：查询详细数据
            cur.execute("""
                SELECT device_id, enable_i, i_on, i_off, updated_by
                FROM device_running_thresholds
                ORDER BY device_id
            """)
            rows = cur.fetchall()
            _log.info(f"\n  详细数据（{len(rows)}行）：")
            for r in rows:
                _log.info(f"    设备{r[0]}: enable_i={r[1]}, i_on={r[2]}, i_off={r[3]}, updated_by={r[4]}")
            
            # 步骤5：调用电流阈值学习存储过程（使用正确的时间窗口）
            _log.info("\n步骤5：调用电流阈值学习存储过程")
            _log.info("  使用时间窗口: 2025-05-31 00:00:00 到 2025-06-01 00:00:00")
            try:
                cur.execute("""
                    CALL sp_refresh_device_running_thresholds_current(
                        '2025-05-31 00:00:00+00'::timestamptz,
                        '2025-06-01 00:00:00+00'::timestamptz,
                        NULL,
                        NULL
                    )
                """)
                _log.info("  存储过程调用成功")
            except Exception as e:
                _log.error(f"  存储过程调用失败：{e}")
                return
            
            # 步骤6：查询更新后的表
            _log.info("\n步骤6：查询更新后的表")
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
            count = cur.fetchone()[0]
            _log.info(f"  表中现在有 {count} 行")
            
            # 步骤7：查询详细数据
            cur.execute("""
                SELECT device_id, enable_i, i_on, i_off, updated_by
                FROM device_running_thresholds
                ORDER BY device_id
            """)
            rows = cur.fetchall()
            _log.info(f"\n  详细数据（{len(rows)}行）：")
            for r in rows:
                i_on_str = f"{r[2]:.2f}" if r[2] is not None else "None"
                i_off_str = f"{r[3]:.2f}" if r[3] is not None else "None"
                _log.info(f"    设备{r[0]}: enable_i={r[1]}, i_on={i_on_str}, i_off={i_off_str}, updated_by={r[4]}")
            
            # 步骤8：提交事务
            _log.info("\n步骤8：提交事务")
            conn.commit()
            _log.info("  事务已提交")
    
    _log.info("\n" + "=" * 80)
    _log.info("调试完成")
    _log.info("=" * 80)


if __name__ == "__main__":
    main()

