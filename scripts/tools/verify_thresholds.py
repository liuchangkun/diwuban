"""
验证设备运行阈值表状态

职责：
- 查询 device_running_thresholds 表的当前状态
- 验证阈值字段是否已填充
- 提供详细的统计信息

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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
_log = logging.getLogger(__name__)


def verify_thresholds():
    """验证阈值表状态"""
    
    _log.info("=" * 80)
    _log.info("开始验证 device_running_thresholds 表状态")
    _log.info("=" * 80)
    
    settings = load_settings(Path("configs"))
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 1. 检查表是否为空
            _log.info("\n1. 检查表行数...")
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
            total_count = cur.fetchone()[0]
            _log.info(f"   总行数: {total_count}")
            
            if total_count == 0:
                _log.warning("   ⚠️ 表为空！")
                return
            
            # 2. 检查核心字段的填充情况
            _log.info("\n2. 检查核心字段填充情况...")
            
            # 电流阈值
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds WHERE i_on IS NOT NULL")
            i_on_count = cur.fetchone()[0]
            _log.info(f"   i_on 已填充: {i_on_count}/{total_count} ({i_on_count*100//total_count if total_count > 0 else 0}%)")
            
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds WHERE i_off IS NOT NULL")
            i_off_count = cur.fetchone()[0]
            _log.info(f"   i_off 已填充: {i_off_count}/{total_count} ({i_off_count*100//total_count if total_count > 0 else 0}%)")
            
            # 功率阈值
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds WHERE p_on IS NOT NULL")
            p_on_count = cur.fetchone()[0]
            _log.info(f"   p_on 已填充: {p_on_count}/{total_count} ({p_on_count*100//total_count if total_count > 0 else 0}%)")
            
            # 频率阈值
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds WHERE f_on IS NOT NULL")
            f_on_count = cur.fetchone()[0]
            _log.info(f"   f_on 已填充: {f_on_count}/{total_count} ({f_on_count*100//total_count if total_count > 0 else 0}%)")
            
            # 时间参数
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds WHERE grace_hold_secs > 0")
            grace_count = cur.fetchone()[0]
            _log.info(f"   grace_hold_secs > 0: {grace_count}/{total_count} ({grace_count*100//total_count if total_count > 0 else 0}%)")
            
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds WHERE min_run_secs > 0")
            min_run_count = cur.fetchone()[0]
            _log.info(f"   min_run_secs > 0: {min_run_count}/{total_count} ({min_run_count*100//total_count if total_count > 0 else 0}%)")
            
            # 3. 查看样例数据
            _log.info("\n3. 查看样例数据（前3个设备）...")
            cur.execute("""
                SELECT 
                    device_id,
                    enable_i, i_on, i_off,
                    enable_p, p_on, p_off,
                    enable_f, f_on, f_off,
                    grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs,
                    pf_min, pf_max
                FROM device_running_thresholds
                ORDER BY device_id
                LIMIT 3
            """)
            
            rows = cur.fetchall()
            for row in rows:
                _log.info(f"\n   设备 {row[0]}:")
                _log.info(f"     电流: enable_i={row[1]}, i_on={row[2]}, i_off={row[3]}")
                _log.info(f"     功率: enable_p={row[4]}, p_on={row[5]}, p_off={row[6]}")
                _log.info(f"     频率: enable_f={row[7]}, f_on={row[8]}, f_off={row[9]}")
                _log.info(f"     时间: grace={row[10]}, min_run={row[11]}, min_stop={row[12]}, smooth={row[13]}")
                _log.info(f"     功率因数: pf_min={row[14]}, pf_max={row[15]}")
            
            # 4. 检查存储过程是否存在
            _log.info("\n4. 检查存储过程是否存在...")
            procedures = [
                "sp_refresh_device_running_thresholds_current",
                "sp_refresh_device_running_thresholds_power",
                "sp_refresh_device_running_thresholds_frequency",
                "sp_refresh_device_running_thresholds_timing",
            ]
            
            for proc_name in procedures:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM pg_proc p
                    JOIN pg_namespace n ON n.oid = p.pronamespace
                    WHERE n.nspname = 'public'
                      AND p.proname = %s
                """, (proc_name,))
                count = cur.fetchone()[0]
                status = "✅ 存在" if count > 0 else "❌ 不存在"
                _log.info(f"   {proc_name}: {status}")
    
    _log.info("\n" + "=" * 80)
    _log.info("验证完成")
    _log.info("=" * 80)


if __name__ == "__main__":
    try:
        verify_thresholds()
    except Exception as e:
        _log.error(f"验证失败：{e}", exc_info=True)
        sys.exit(1)

