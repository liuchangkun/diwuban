#!/usr/bin/env python
"""
测试6层参数优先级系统
验证device_rated_params表的三级参数体系（全局→泵站→设备）
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db.gateway import get_conn

def test_parameter_priority():
    """测试参数优先级"""
    settings = load_settings(Path("configs"))
    
    print("=" * 80)
    print("测试6层参数优先级系统")
    print("=" * 80)
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 测试1：查询泵站级参数
            print("\n[测试1] 泵站级参数（station_id=1, device_id=NULL）")
            cur.execute("""
                SELECT param_key, value_numeric, unit, source
                FROM device_rated_params
                WHERE station_id = 1 AND device_id IS NULL
                ORDER BY param_key
            """)
            station_params = cur.fetchall()
            print(f"  找到 {len(station_params)} 个泵站级参数：")
            for row in station_params:
                print(f"    - {row[0]}: {row[1]} {row[2] or ''} (来源: {row[3]})")
            
            # 测试2：查询设备级参数
            print("\n[测试2] 设备级参数（device_id=1）")
            cur.execute("""
                SELECT param_key, value_numeric, unit, source
                FROM device_rated_params
                WHERE device_id = 1
                ORDER BY param_key
            """)
            device_params = cur.fetchall()
            print(f"  找到 {len(device_params)} 个设备级参数：")
            for row in device_params[:5]:  # 只显示前5个
                print(f"    - {row[0]}: {row[1]} {row[2] or ''}")
            if len(device_params) > 5:
                print(f"    ... 还有 {len(device_params) - 5} 个参数")
            
            # 测试3：模拟参数加载优先级
            print("\n[测试3] 模拟参数加载优先级（device_id=1, station_id=1）")
            
            # 层级1：全局计算参数（这里跳过，因为需要method_id）
            
            # 层级2：全局默认额定参数（这里跳过）
            
            # 层级3：设备额定参数
            cur.execute("""
                SELECT param_key, value_numeric
                FROM device_rated_params
                WHERE device_id = 1 AND value_numeric IS NOT NULL
            """)
            params_layer3 = {row[0]: row[1] for row in cur.fetchall()}
            print(f"  层级3（设备额定参数）: {len(params_layer3)} 个参数")
            
            # 层级3.5：泵站级额定参数
            cur.execute("""
                SELECT param_key, value_numeric
                FROM device_rated_params
                WHERE station_id = 1 AND device_id IS NULL AND value_numeric IS NOT NULL
            """)
            params_layer35 = {row[0]: row[1] for row in cur.fetchall()}
            print(f"  层级3.5（泵站级额定参数）: {len(params_layer35)} 个参数")
            
            # 合并参数（层级3.5覆盖层级3）
            merged_params = {**params_layer3, **params_layer35}
            print(f"  合并后参数总数: {len(merged_params)} 个")
            
            # 显示泵站级参数覆盖的情况
            overridden = set(params_layer3.keys()) & set(params_layer35.keys())
            if overridden:
                print(f"  泵站级参数覆盖了设备级参数: {overridden}")
            else:
                print(f"  泵站级参数与设备级参数无重叠（符合预期）")
            
            # 测试4：验证三级参数体系统计
            print("\n[测试4] 三级参数体系统计")
            cur.execute("""
                WITH levels AS (
                    SELECT 
                        CASE 
                            WHEN station_id IS NULL AND device_id IS NULL THEN '全局级'
                            WHEN station_id IS NOT NULL AND device_id IS NULL THEN '泵站级'
                            WHEN station_id IS NOT NULL AND device_id IS NOT NULL THEN '设备级'
                            ELSE '未知'
                        END as level,
                        param_key
                    FROM device_rated_params
                )
                SELECT level, COUNT(*) as count, COUNT(DISTINCT param_key) as param_types
                FROM levels
                GROUP BY level
                ORDER BY 
                    CASE level
                        WHEN '全局级' THEN 1
                        WHEN '泵站级' THEN 2
                        WHEN '设备级' THEN 3
                        ELSE 4
                    END
            """)
            stats = cur.fetchall()
            print("  参数分布：")
            for row in stats:
                print(f"    {row[0]}: {row[1]} 行, {row[2]} 种参数类型")
            
            # 测试5：验证唯一索引
            print("\n[测试5] 验证唯一索引")
            cur.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' 
                  AND tablename = 'device_rated_params'
                  AND indexname = 'uq_device_rated_params_3tier'
            """)
            index_info = cur.fetchone()
            if index_info:
                print(f"  ✓ 唯一索引已创建: {index_info[0]}")
                print(f"    定义: {index_info[1][:100]}...")
            else:
                print(f"  ✗ 唯一索引不存在")
            
            # 测试6：验证外键约束
            print("\n[测试6] 验证外键约束")
            cur.execute("""
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE conrelid = 'public.device_rated_params'::regclass
                  AND contype = 'f'
                ORDER BY conname
            """)
            fkeys = cur.fetchall()
            print(f"  找到 {len(fkeys)} 个外键约束：")
            for row in fkeys:
                print(f"    - {row[0]}: {row[1][:80]}...")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    test_parameter_priority()

