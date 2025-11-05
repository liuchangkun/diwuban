#!/usr/bin/env python3
"""
添加缺失的指标到 dim_metric_config

用途：添加 pump_shaft_power 和 pump_hydraulic_power 到 dim_metric_config 表
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings


def main():
    """主函数"""
    # 加载配置
    settings = Settings()
    
    # SQL语句
    sql = """
    -- 添加 pump_shaft_power 和 pump_hydraulic_power 到 dim_metric_config
    INSERT INTO dim_metric_config (metric_key, unit, unit_display, decimals_policy, value_type, valid_min, valid_max)
    VALUES 
        ('pump_shaft_power', 'kW', '泵轴功率', 'as_is', 'number', '0', '10000'),
        ('pump_hydraulic_power', 'kW', '泵水力功率', 'as_is', 'number', '0', '10000')
    ON CONFLICT (metric_key) DO UPDATE SET
        unit = EXCLUDED.unit,
        unit_display = EXCLUDED.unit_display,
        decimals_policy = EXCLUDED.decimals_policy,
        value_type = EXCLUDED.value_type,
        valid_min = EXCLUDED.valid_min,
        valid_max = EXCLUDED.valid_max,
        updated_at = CURRENT_TIMESTAMP
    RETURNING id, metric_key, unit, unit_display;
    """
    
    try:
        print("\n" + "="*80)
        print("添加缺失的指标到 dim_metric_config")
        print("="*80 + "\n")
        
        # 执行SQL
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                results = cur.fetchall()
                
                print("✅ 成功添加/更新以下指标：\n")
                for row in results:
                    print(f"  - ID: {row[0]}, metric_key: {row[1]}, unit: {row[2]}, unit_display: {row[3]}")
                
            conn.commit()
        
        print("\n" + "="*80)
        print("✅ 指标添加完成")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

