"""
初始化缺失指标计算功能的计算参数表

用途: 执行scripts/sql/calculation/init_params.sql文件，初始化calculation_parameters表
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
    """执行SQL文件初始化参数"""
    # 初始化日志
    init_logging()
    
    # 加载配置
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    
    # 初始化数据库连接池
    init_database(settings)
    print("✅ 数据库连接池初始化成功")
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "init_params.sql"
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
                
                # 验证参数是否录入成功
                print("\n🔍 验证参数是否录入成功...")
                cur.execute("""
                    SELECT COUNT(*) as param_count
                    FROM calculation_parameters
                    WHERE device_id IS NULL
                """)
                result = cur.fetchone()
                param_count = result[0]
                
                if param_count == 7:
                    print(f"✅ 成功录入 {param_count} 个全局默认参数（符合预期）")
                else:
                    print(f"⚠️  录入了 {param_count} 个全局默认参数（预期 7）")
                
                # 显示详细信息
                print("\n📋 详细参数列表:")
                cur.execute("""
                    SELECT metric_key, method_id, param_name, param_value, param_type, is_optimizable
                    FROM calculation_parameters
                    WHERE device_id IS NULL
                    ORDER BY metric_key, method_id, param_name
                """)
                params = cur.fetchall()
                
                for param in params:
                    metric_key, method_id, param_name, param_value, param_type, is_optimizable = param
                    opt_status = "可优化" if is_optimizable else "固定"
                    print(f"  [{metric_key}] {param_name} = {param_value} ({param_type}, {opt_status})")
                
                if param_count == 7:
                    print("\n✅ 所有参数录入成功！")
                    return 0
                else:
                    print("\n⚠️  参数录入不符合预期")
                    return 1
                    
    except Exception as e:
        print(f"❌ 执行SQL失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

