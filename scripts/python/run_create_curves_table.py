"""
执行创建水泵特性曲线表的SQL脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def main():
    """主函数"""
    print("="*80)
    print("创建水泵特性曲线表")
    print("="*80)
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "validation" / "create_pump_characteristic_curves.sql"
    
    print(f"\n读取SQL文件: {sql_file}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 执行SQL
    print("\n执行SQL...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()
                
                # 获取验证结果
                cur.execute("""
                    SELECT 
                        device_id,
                        curve_type,
                        COUNT(*) as point_count,
                        MIN(flow_rate) as min_flow,
                        MAX(flow_rate) as max_flow,
                        MIN(value) as min_value,
                        MAX(value) as max_value
                    FROM pump_characteristic_curves
                    GROUP BY device_id, curve_type
                    ORDER BY device_id, curve_type
                """)
                
                results = cur.fetchall()
                
                print("\n✅ 表创建成功！")
                print("\n示例数据统计：")
                print("-"*80)
                print(f"{'设备ID':<10} {'曲线类型':<12} {'数据点':<8} {'流量范围':<20} {'值范围':<20}")
                print("-"*80)
                
                for row in results:
                    device_id, curve_type, count, min_flow, max_flow, min_val, max_val = row
                    flow_range = f"{min_flow:.1f} - {max_flow:.1f}"
                    val_range = f"{min_val:.1f} - {max_val:.1f}"
                    print(f"{device_id:<10} {curve_type:<12} {count:<8} {flow_range:<20} {val_range:<20}")
                
                print("-"*80)
                print(f"\n总计：{len(results)} 种曲线类型")
                
    except Exception as e:
        print(f"\n❌ 执行失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "="*80)
    print("完成")
    print("="*80)
    
    return 0


if __name__ == "__main__":
    exit(main())

