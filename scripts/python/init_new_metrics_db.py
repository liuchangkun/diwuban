"""
初始化新增指标的数据库配置

执行SQL脚本：
1. init_new_metrics_methods.sql - 注册计算方法
2. init_new_metrics_params.sql - 添加方法参数
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def execute_sql_file(sql_file: Path):
    """执行SQL文件"""
    print(f"\n执行SQL文件: {sql_file.name}")
    print("=" * 80)
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        
        # 获取最后一条SELECT的结果
        if cur.description:
            result = cur.fetchall()
            if result:
                print(f"\n结果:")
                for row in result:
                    print(f"  {row}")
    
    print(f"✅ {sql_file.name} 执行完成")


def main():
    """主函数"""
    print("=" * 80)
    print("初始化新增指标的数据库配置")
    print("=" * 80)

    # 初始化数据库连接
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    print("✅ 数据库连接初始化完成\n")

    sql_dir = project_root / "scripts" / "sql" / "calculation"

    # 0. 添加缺失的指标到dim_metric_config表
    add_metrics_sql = sql_dir / "add_missing_metrics_to_dim.sql"
    if add_metrics_sql.exists():
        execute_sql_file(add_metrics_sql)
    else:
        print(f"❌ 文件不存在: {add_metrics_sql}")
        return 1

    # 1. 注册计算方法
    methods_sql = sql_dir / "init_new_metrics_methods.sql"
    if methods_sql.exists():
        execute_sql_file(methods_sql)
    else:
        print(f"❌ 文件不存在: {methods_sql}")
        return 1
    
    # 2. 添加方法参数
    params_sql = sql_dir / "init_new_metrics_params_v2.sql"
    if params_sql.exists():
        execute_sql_file(params_sql)
    else:
        print(f"❌ 文件不存在: {params_sql}")
        return 1
    
    # 3. 验证注册结果
    print("\n" + "=" * 80)
    print("验证注册结果")
    print("=" * 80)
    
    with get_connection() as conn:
        cur = conn.cursor()
        
        # 查询新增方法数量
        cur.execute("""
            SELECT metric_key, COUNT(*) as method_count
            FROM calculation_method_registry
            WHERE metric_key IN ('pump_speed', 'pump_torque', 'main_pipeline_outlet_pressure', 
                                 'main_pipeline_inlet_pressure', 'pump_cumulative_flow')
            GROUP BY metric_key
            ORDER BY metric_key
        """)
        
        print("\n新增指标的计算方法数量:")
        total_methods = 0
        for row in cur.fetchall():
            metric_key, method_count = row
            print(f"  - {metric_key}: {method_count}种方法")
            total_methods += method_count
        
        print(f"\n总计: {total_methods}种方法")
        
        # 查询参数数量
        cur.execute("""
            SELECT COUNT(*) as param_count
            FROM calculation_parameters
            WHERE method_id IN (
                SELECT method_id FROM calculation_method_registry
                WHERE metric_key IN ('pump_speed', 'pump_torque', 'main_pipeline_outlet_pressure',
                                     'main_pipeline_inlet_pressure', 'pump_cumulative_flow')
            )
        """)
        
        param_count = cur.fetchone()[0]
        print(f"\n新增方法的参数数量: {param_count}个")
    
    print("\n" + "=" * 80)
    print("✅ 所有数据库配置初始化完成！")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

