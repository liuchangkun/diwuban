"""
临时更新 max_flow 参数（从 500 调整为 5000）
原因：实际单泵流量可以达到 2700+ m³/h，500 的阈值过小
"""

from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
from app.core.logging.setup import init_logging
from app.adapters.db.pool import get_connection

def main():
    # 初始化应用
    config_dir = Path("configs")
    settings = load_settings(config_dir)
    init_logging(config_dir, settings.system.timezone.default)
    init_database(settings)
    
    print("=" * 80)
    print("更新 max_flow 参数")
    print("=" * 80)
    
    # 更新参数
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 更新
            cur.execute("""
                UPDATE calculation_parameters
                SET param_value = '5000.0',
                    updated_at = NOW(),
                    updated_by = 'manual_fix'
                WHERE metric_key = 'pump_flow_rate'
                  AND method_id = 'data_filter'
                  AND param_name = 'max_flow'
            """)
            
            updated_count = cur.rowcount
            print(f"✅ 更新了 {updated_count} 条记录")
            
            # 验证
            cur.execute("""
                SELECT 
                    id,
                    metric_key,
                    method_id,
                    param_name,
                    param_value,
                    updated_at,
                    updated_by
                FROM calculation_parameters
                WHERE metric_key = 'pump_flow_rate'
                  AND method_id = 'data_filter'
                  AND param_name = 'max_flow'
            """)
            
            result = cur.fetchone()
            if result:
                print("\n📊 更新后的参数：")
                print(f"   - ID: {result[0]}")
                print(f"   - metric_key: {result[1]}")
                print(f"   - method_id: {result[2]}")
                print(f"   - param_name: {result[3]}")
                print(f"   - param_value: {result[4]}")
                print(f"   - updated_at: {result[5]}")
                print(f"   - updated_by: {result[6]}")
        
        conn.commit()
    
    print("\n" + "=" * 80)
    print("✅ 更新完成")
    print("=" * 80)

if __name__ == '__main__':
    main()

