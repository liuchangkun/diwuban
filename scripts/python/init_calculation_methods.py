"""
初始化缺失指标计算功能的计算方法注册表

用途: 执行scripts/sql/calculation/init_methods.sql文件，初始化calculation_method_registry表
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
    """执行SQL文件初始化方法"""
    # 初始化日志
    init_logging()
    
    # 加载配置
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    
    # 初始化数据库连接池
    init_database(settings)
    print("✅ 数据库连接池初始化成功")
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "init_methods.sql"
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return 1
    
    sql_content = sql_file.read_text(encoding="utf-8")
    print(f"📄 读取SQL文件: {sql_file}")
    print(f"📏 SQL文件大小: {len(sql_content)} 字符")
    
    # 执行SQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                print("🔄 开始执行SQL...")
                cur.execute(sql_content)
                conn.commit()
                print("✅ SQL执行成功！")
                
                # 验证方法是否录入成功
                print("\n🔍 验证方法是否录入成功...")
                cur.execute("""
                    SELECT metric_key, COUNT(*) as method_count
                    FROM calculation_method_registry
                    GROUP BY metric_key
                    ORDER BY metric_key
                """)
                results = cur.fetchall()
                
                expected = {
                    'pump_flow_rate': 6,
                    'pump_head': 1,
                    'pump_outlet_pressure': 4
                }
                
                all_correct = True
                for row in results:
                    metric_key, count = row
                    expected_count = expected.get(metric_key, 0)
                    if count == expected_count:
                        print(f"✅ {metric_key}: {count} 个方法（符合预期）")
                    else:
                        print(f"⚠️  {metric_key}: {count} 个方法（预期 {expected_count}）")
                        all_correct = False
                
                # 显示详细信息
                print("\n📋 详细方法列表:")
                cur.execute("""
                    SELECT method_id, metric_key, method_name, method_code, priority, accuracy_level, is_enabled
                    FROM calculation_method_registry
                    ORDER BY metric_key, priority DESC
                """)
                methods = cur.fetchall()
                
                for method in methods:
                    method_id, metric_key, method_name, method_code, priority, accuracy_level, is_enabled = method
                    status = "✅" if is_enabled else "❌"
                    print(f"  {status} [{metric_key}] 方案{method_code}: {method_name} (优先级:{priority}, 精度:{accuracy_level})")
                
                if all_correct:
                    print("\n✅ 所有方法录入成功！")
                    return 0
                else:
                    print("\n⚠️  部分方法录入不符合预期")
                    return 1
                    
    except Exception as e:
        print(f"❌ 执行SQL失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

