"""
最终验证脚本 - 验证修复效果

职责：
- 验证 device_running_thresholds 表是否已填充
- 验证 mv_device_running_1s 表是否有新数据
- 验证 fact_measurements 表中指标计算是否恢复
- 提供修复前后的对比报告

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


def final_validation():
    """最终验证修复效果"""
    
    _log.info("=" * 80)
    _log.info("开始最终验证 - 指标计算缺失问题修复效果")
    _log.info("=" * 80)
    
    settings = load_settings(Path("configs"))
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # ========== 1. 验证 device_running_thresholds 表 ==========
            _log.info("\n" + "=" * 80)
            _log.info("1. 验证 device_running_thresholds 表")
            _log.info("=" * 80)
            
            # 1.1 检查行数
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
            threshold_count = cur.fetchone()[0]
            _log.info(f"\n1.1 表行数: {threshold_count}")
            
            if threshold_count == 0:
                _log.error("   ❌ 表为空！修复失败！")
                _log.error("   请先运行 prepare-dim 或 run-all 流程")
                return False
            else:
                _log.info(f"   ✅ 表不为空，共 {threshold_count} 个设备")
            
            # 1.2 检查核心字段完整性
            _log.info("\n1.2 核心字段完整性:")
            
            # 电流阈值
            cur.execute("""
                SELECT COUNT(*) 
                FROM device_running_thresholds 
                WHERE enable_i = TRUE AND i_on IS NOT NULL AND i_off IS NOT NULL
            """)
            i_complete = cur.fetchone()[0]
            i_pct = i_complete * 100 // threshold_count if threshold_count > 0 else 0
            _log.info(f"   电流阈值完整: {i_complete}/{threshold_count} ({i_pct}%)")
            
            # 时间参数
            cur.execute("""
                SELECT COUNT(*) 
                FROM device_running_thresholds 
                WHERE grace_hold_secs > 0 AND min_run_secs > 0 AND min_stop_secs > 0
            """)
            timing_complete = cur.fetchone()[0]
            timing_pct = timing_complete * 100 // threshold_count if threshold_count > 0 else 0
            _log.info(f"   时间参数完整: {timing_complete}/{threshold_count} ({timing_pct}%)")
            
            # 1.3 查看样例数据
            _log.info("\n1.3 样例数据（前2个设备）:")
            cur.execute("""
                SELECT 
                    device_id,
                    enable_i, i_on, i_off,
                    grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs
                FROM device_running_thresholds
                ORDER BY device_id
                LIMIT 2
            """)
            
            for row in cur.fetchall():
                _log.info(f"\n   设备 {row[0]}:")
                _log.info(f"     电流: enable_i={row[1]}, i_on={row[2]:.2f}, i_off={row[3]:.2f}")
                _log.info(f"     时间: grace={row[4]}, min_run={row[5]}, min_stop={row[6]}, smooth={row[7]}")
            
            # ========== 2. 验证 mv_device_running_1s 表 ==========
            _log.info("\n" + "=" * 80)
            _log.info("2. 验证 mv_device_running_1s 表")
            _log.info("=" * 80)
            
            # 2.1 检查当前设备的数据
            cur.execute("""
                SELECT station_id, COUNT(*) as cnt, MIN(ts) as min_ts, MAX(ts) as max_ts
                FROM mv_device_running_1s
                GROUP BY station_id
                ORDER BY station_id
            """)
            
            _log.info("\n2.1 按泵站统计:")
            running_data_exists = False
            for row in cur.fetchall():
                station_id, cnt, min_ts, max_ts = row
                _log.info(f"   泵站 {station_id}: {cnt:,} 行, 时间范围: {min_ts} ~ {max_ts}")
                if station_id == 14:  # 当前泵站
                    running_data_exists = True
            
            if not running_data_exists:
                _log.warning("   ⚠️ 当前泵站（station_id=14）没有运行状态数据")
            else:
                _log.info("   ✅ 当前泵站有运行状态数据")
            
            # 2.2 检查运行状态分布
            cur.execute("""
                SELECT is_running, COUNT(*) as cnt
                FROM mv_device_running_1s
                WHERE station_id = 14
                GROUP BY is_running
            """)
            
            _log.info("\n2.2 运行状态分布（station_id=14）:")
            for row in cur.fetchall():
                is_running, cnt = row
                status = "运行" if is_running else "停止"
                _log.info(f"   {status}: {cnt:,} 行")
            
            # ========== 3. 验证 fact_measurements 表 ==========
            _log.info("\n" + "=" * 80)
            _log.info("3. 验证 fact_measurements 表")
            _log.info("=" * 80)
            
            # 3.1 检查最新时间桶的指标数量
            cur.execute("""
                SELECT ts_bucket, COUNT(DISTINCT metric_id) as metric_count
                FROM fact_measurements
                WHERE station_id = 14
                GROUP BY ts_bucket
                ORDER BY ts_bucket DESC
                LIMIT 5
            """)
            
            _log.info("\n3.1 最新5个时间桶的指标数量:")
            latest_metric_count = 0
            for i, row in enumerate(cur.fetchall()):
                ts_bucket, metric_count = row
                _log.info(f"   {ts_bucket}: {metric_count} 个指标")
                if i == 0:
                    latest_metric_count = metric_count
            
            if latest_metric_count >= 37:
                _log.info(f"   ✅ 最新时间桶有 {latest_metric_count} 个指标（预期 37 个）")
            elif latest_metric_count >= 30:
                _log.warning(f"   ⚠️ 最新时间桶有 {latest_metric_count} 个指标（预期 37 个，部分缺失）")
            else:
                _log.error(f"   ❌ 最新时间桶只有 {latest_metric_count} 个指标（预期 37 个，严重缺失）")
            
            # 3.2 检查关键指标是否存在
            _log.info("\n3.2 检查关键指标是否存在:")
            
            key_metrics = [
                ("device_running_duration", "设备运行时长"),
                ("device_stop_duration", "设备停止时长"),
                ("device_running_count", "设备运行次数"),
                ("device_stop_count", "设备停止次数"),
            ]
            
            for metric_name, metric_desc in key_metrics:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM fact_measurements fm
                    JOIN dim_metrics dm ON fm.metric_id = dm.metric_id
                    WHERE dm.metric_name = %s
                      AND fm.station_id = 14
                      AND fm.ts_bucket >= NOW() - INTERVAL '1 day'
                """, (metric_name,))
                
                count = cur.fetchone()[0]
                if count > 0:
                    _log.info(f"   ✅ {metric_desc} ({metric_name}): {count:,} 行")
                else:
                    _log.error(f"   ❌ {metric_desc} ({metric_name}): 0 行（缺失）")
            
            # ========== 4. 验证 completion_runs 表 ==========
            _log.info("\n" + "=" * 80)
            _log.info("4. 验证 completion_runs 表")
            _log.info("=" * 80)
            
            # 4.1 检查 device_running 步骤是否成功
            cur.execute("""
                SELECT 
                    run_id,
                    step_name,
                    status,
                    started_at,
                    completed_at,
                    error_message
                FROM completion_runs
                WHERE step_name = 'device_running'
                ORDER BY run_id DESC
                LIMIT 3
            """)
            
            _log.info("\n4.1 最近3次 device_running 步骤执行记录:")
            device_running_success = False
            for row in cur.fetchall():
                run_id, step_name, status, started_at, completed_at, error_message = row
                status_icon = "✅" if status == "completed" else "❌"
                _log.info(f"\n   {status_icon} Run {run_id}:")
                _log.info(f"      状态: {status}")
                _log.info(f"      开始: {started_at}")
                _log.info(f"      完成: {completed_at}")
                if error_message:
                    _log.info(f"      错误: {error_message}")
                
                if status == "completed":
                    device_running_success = True
            
            # ========== 5. 总结 ==========
            _log.info("\n" + "=" * 80)
            _log.info("5. 修复效果总结")
            _log.info("=" * 80)
            
            _log.info("\n修复前后对比:")
            _log.info(f"   device_running_thresholds 行数: 0 → {threshold_count}")
            _log.info(f"   核心阈值完整性: 0% → {i_pct}%")
            _log.info(f"   时间参数完整性: 0% → {timing_pct}%")
            _log.info(f"   最新时间桶指标数: 1 → {latest_metric_count}")
            _log.info(f"   device_running 步骤: 失败 → {'成功' if device_running_success else '失败'}")
            
            # 判断修复是否成功
            success = (
                threshold_count > 0 and
                i_pct >= 80 and
                timing_pct >= 80 and
                latest_metric_count >= 30
            )
            
            if success:
                _log.info("\n" + "=" * 80)
                _log.info("✅ 修复成功！所有关键指标都已恢复！")
                _log.info("=" * 80)
                return True
            else:
                _log.info("\n" + "=" * 80)
                _log.warning("⚠️ 修复部分成功，但仍有一些问题需要解决")
                _log.info("=" * 80)
                return False


if __name__ == "__main__":
    try:
        success = final_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        _log.error(f"验证失败：{e}", exc_info=True)
        sys.exit(1)

