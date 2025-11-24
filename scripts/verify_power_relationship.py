"""
验证功率关系：P_hydraulic < P_shaft < P_active

物理约束：
- 水力功率 < 轴功率 < 有功功率
- P_h < P_shaft < P_active
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def verify_power_relationship():
    """验证功率关系"""
    print("="*80)
    print("验证功率关系：P_hydraulic < P_shaft < P_active")
    print("="*80)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 查询三个功率指标的数据
            cur.execute("""
                WITH power_data AS (
                    SELECT 
                        fm.ts_bucket,
                        fm.device_id,
                        mc.metric_key,
                        fm.value
                    FROM fact_measurements fm
                    JOIN dim_metric_config mc ON mc.id = fm.metric_id
                    WHERE fm.station_id = 1
                      AND fm.device_id IN (1, 2, 3, 4, 5, 6)
                      AND mc.metric_key IN ('pump_active_power', 'pump_shaft_power', 'pump_hydraulic_power')
                      AND fm.ts_bucket >= '2025-10-22 08:00:00+00:00'
                      AND fm.ts_bucket < '2025-10-23 07:13:29+00:00'
                )
                SELECT 
                    p_active.device_id,
                    COUNT(*) as count,
                    AVG(p_active.value) as avg_active,
                    AVG(p_shaft.value) as avg_shaft,
                    AVG(p_hydro.value) as avg_hydro,
                    SUM(CASE WHEN p_hydro.value < p_shaft.value THEN 1 ELSE 0 END) as valid_h_s,
                    SUM(CASE WHEN p_shaft.value < p_active.value THEN 1 ELSE 0 END) as valid_s_a,
                    SUM(CASE WHEN p_hydro.value < p_shaft.value AND p_shaft.value < p_active.value THEN 1 ELSE 0 END) as valid_all
                FROM power_data p_active
                JOIN power_data p_shaft 
                    ON p_shaft.ts_bucket = p_active.ts_bucket 
                    AND p_shaft.device_id = p_active.device_id
                    AND p_shaft.metric_key = 'pump_shaft_power'
                JOIN power_data p_hydro 
                    ON p_hydro.ts_bucket = p_active.ts_bucket 
                    AND p_hydro.device_id = p_active.device_id
                    AND p_hydro.metric_key = 'pump_hydraulic_power'
                WHERE p_active.metric_key = 'pump_active_power'
                GROUP BY p_active.device_id
                ORDER BY p_active.device_id
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\n找到 {len(rows)} 个设备的功率数据:")
                print(f"\n{'设备':<6} {'记录数':<8} {'P_active':<10} {'P_shaft':<10} {'P_hydro':<10} {'P_h<P_s':<10} {'P_s<P_a':<10} {'全部满足':<10}")
                print("-" * 80)
                
                total_count = 0
                total_valid = 0
                
                for row in rows:
                    device_id, count, avg_active, avg_shaft, avg_hydro, valid_h_s, valid_s_a, valid_all = row
                    total_count += count
                    total_valid += valid_all
                    
                    h_s_pct = (valid_h_s / count * 100) if count > 0 else 0
                    s_a_pct = (valid_s_a / count * 100) if count > 0 else 0
                    all_pct = (valid_all / count * 100) if count > 0 else 0
                    
                    print(f"{device_id:<6} {count:<8} {avg_active:<10.2f} {avg_shaft:<10.2f} {avg_hydro:<10.2f} "
                          f"{h_s_pct:<9.1f}% {s_a_pct:<9.1f}% {all_pct:<9.1f}%")
                
                print("-" * 80)
                print(f"总计: {total_count} 条记录, {total_valid} 条满足约束 ({total_valid/total_count*100:.1f}%)")
                
                if total_valid == total_count:
                    print("\n✅ 所有数据都满足物理约束：P_hydraulic < P_shaft < P_active")
                else:
                    print(f"\n⚠️ 有 {total_count - total_valid} 条数据不满足物理约束")
            else:
                print("\n⚠️ 未找到功率数据")


if __name__ == '__main__':
    # 初始化数据库连接
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 验证功率关系
    verify_power_relationship()

