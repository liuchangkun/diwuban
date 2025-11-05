"""
修复 metrics_presence_per_second_device 表 Bug 的执行脚本

此脚本执行以下操作：
1. 清空 metrics_presence_per_second_device 表
2. 从 fact_measurements 表重新生成数据
3. 验证数据格式

作者：AI
创建日期：2025-11-04
"""
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.services.reporting.presence_writer import upsert_window
from app.core.config.loader import load_settings


def main():
    """执行修复流程"""
    print("=" * 80)
    print("修复 metrics_presence_per_second_device 表 Bug")
    print("=" * 80)
    
    # 初始化数据库连接
    print("\n[1/5] 初始化数据库连接...")
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    print("✅ 数据库连接初始化完成")
    
    # 步骤12-13：清空表
    print("\n[2/5] 清空 metrics_presence_per_second_device 表...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询清空前的记录数
            cur.execute("SELECT COUNT(*) FROM metrics_presence_per_second_device")
            count_before = cur.fetchone()[0]
            print(f"  清空前记录数：{count_before}")
            
            # 清空表
            cur.execute("TRUNCATE TABLE metrics_presence_per_second_device")
            conn.commit()
            
            # 验证表已清空
            cur.execute("SELECT COUNT(*) FROM metrics_presence_per_second_device")
            count_after = cur.fetchone()[0]
            print(f"  清空后记录数：{count_after}")
            
            if count_after == 0:
                print("✅ 表已成功清空")
            else:
                print(f"❌ 表清空失败，仍有 {count_after} 条记录")
                return False
    
    # 步骤14：查询 fact_measurements 表的时间范围
    print("\n[3/5] 查询 fact_measurements 表的时间范围...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MIN(ts_bucket), MAX(ts_bucket)
                FROM fact_measurements
            """)
            result = cur.fetchone()
            if result[0] is None or result[1] is None:
                print("❌ fact_measurements 表为空，无法重新生成数据")
                return False
            
            start_time = result[0]
            end_time = result[1]
            print(f"  时间范围：{start_time} 到 {end_time}")
    
    # 步骤15-16：重新生成数据
    print("\n[4/5] 从 fact_measurements 重新生成数据...")
    print(f"  调用 upsert_window(start={start_time}, end={end_time})")
    
    with get_connection() as conn:
        affected = upsert_window(
            conn=conn,
            start=start_time,
            end=end_time,
            station_id=None,  # 所有泵站
            device_id=None    # 所有设备
        )
        conn.commit()
        print(f"✅ 重新生成 {affected} 条记录")
    
    # 步骤17-22：验证数据
    print("\n[5/5] 验证数据格式...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询总记录数
            cur.execute("SELECT COUNT(*) FROM metrics_presence_per_second_device")
            total_count = cur.fetchone()[0]
            print(f"  修复后总记录数：{total_count}")
            
            # 查询数据格式分布
            cur.execute(r"""
                SELECT
                    CASE
                        WHEN available_metrics::text ~ '^\{[0-9,"]+\}$' THEN 'metric_id格式（错误）'
                        WHEN available_metrics::text ~ '\{[a-z_,"]+\}' THEN 'metric_key格式（正确）'
                        ELSE '其他格式'
                    END AS 数据格式,
                    COUNT(*) AS 记录数
                FROM metrics_presence_per_second_device
                WHERE array_length(available_metrics, 1) > 0
                GROUP BY 1
            """)
            format_distribution = cur.fetchall()
            print("  数据格式分布：")
            for row in format_distribution:
                print(f"    - {row[0]}: {row[1]} 条")
            
            # 抽样检查数据
            cur.execute("""
                SELECT 
                    station_id,
                    device_id,
                    ts_second,
                    available_metrics,
                    need_compute_metrics
                FROM metrics_presence_per_second_device
                ORDER BY ts_second DESC
                LIMIT 5
            """)
            samples = cur.fetchall()
            print("  数据样本（前5条）：")
            for i, row in enumerate(samples, 1):
                print(f"    {i}. station_id={row[0]}, device_id={row[1]}, ts={row[2]}")
                print(f"       available_metrics={row[3]}")
                print(f"       need_compute_metrics={row[4]}")
    
    print("\n" + "=" * 80)
    print("修复完成！")
    print("=" * 80)
    
    # 对比修复前后的数据量
    print(f"\n数据量对比：")
    print(f"  修复前：{count_before} 条")
    print(f"  修复后：{total_count} 条")
    if count_before > 0:
        diff_percent = abs(total_count - count_before) / count_before * 100
        print(f"  差异：{diff_percent:.2f}%")
        if diff_percent > 10:
            print(f"  ⚠️  警告：数据量差异超过10%，请检查 fact_measurements 表数据完整性")
        else:
            print(f"  ✅ 数据量差异在合理范围内")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

