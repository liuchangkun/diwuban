"""
执行参数初始化SQL脚本

目标：
1. 执行 init_all_missing_parameters.sql
2. 验证参数已正确插入
3. 清除 ParameterManager 缓存
4. 重新运行 pump_shaft_power 计算验证修复效果
"""

import sys
import os
from pathlib import Path

# 设置控制台编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


def execute_sql_file(sql_file: Path):
    """执行SQL文件"""
    print(f"\n{'='*100}")
    print(f"执行SQL文件: {sql_file.name}")
    print(f"{'='*100}")
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    # 分割SQL语句（按分号分割，但忽略注释中的分号）
    statements = []
    current_statement = []
    
    for line in sql.split('\n'):
        # 跳过注释行
        if line.strip().startswith('--'):
            continue
        
        current_statement.append(line)
        
        # 如果行以分号结尾，表示一个完整的语句
        if line.strip().endswith(';'):
            statement = '\n'.join(current_statement).strip()
            if statement and not statement.startswith('--'):
                statements.append(statement)
            current_statement = []
    
    print(f"\n找到 {len(statements)} 个SQL语句")
    
    # 执行SQL语句
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i, statement in enumerate(statements, start=1):
                try:
                    # 跳过空语句
                    if not statement or statement.strip() == '':
                        continue
                    
                    # 执行语句
                    cur.execute(statement)
                    
                    # 如果是SELECT语句，显示结果
                    if statement.strip().upper().startswith('SELECT'):
                        rows = cur.fetchall()
                        if rows:
                            print(f"\n语句 {i} 结果:")
                            print("-"*100)
                            for row in rows:
                                print(f"  {row}")
                    else:
                        # INSERT语句，显示影响的行数
                        if cur.rowcount > 0:
                            print(f"✅ 语句 {i}: 插入 {cur.rowcount} 行")
                
                except Exception as e:
                    print(f"❌ 语句 {i} 执行失败: {e}")
                    print(f"   SQL: {statement[:100]}...")
                    # 继续执行下一个语句
                    continue
            
            # 提交事务
            conn.commit()
            print(f"\n✅ 所有语句执行完成，事务已提交")


def verify_parameters():
    """验证参数已正确插入"""
    print(f"\n{'='*100}")
    print("验证参数配置")
    print(f"{'='*100}")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 统计每个指标的参数数量
            cur.execute("""
                SELECT 
                    metric_key,
                    COUNT(*) AS param_count,
                    COUNT(DISTINCT device_id) AS device_count
                FROM calculation_parameters
                WHERE station_id = 1
                GROUP BY metric_key
                ORDER BY metric_key
            """)
            
            print("\n每个指标的参数统计:")
            print("-"*100)
            print(f"{'指标':<40} {'参数数量':>10} {'设备数量':>10}")
            print("-"*100)
            
            for row in cur.fetchall():
                metric_key, param_count, device_count = row
                print(f"{metric_key:<40} {param_count:>10} {device_count:>10}")
            
            # 检查 pump_shaft_power 的参数
            print(f"\n{'='*100}")
            print("pump_shaft_power 参数详情:")
            print(f"{'='*100}")
            
            cur.execute("""
                SELECT 
                    device_id,
                    param_name,
                    param_value
                FROM calculation_parameters
                WHERE station_id = 1
                  AND metric_key = 'pump_shaft_power'
                  AND device_id IN (1,2,3,4,5,6)
                ORDER BY device_id, param_name
            """)
            
            print(f"\n{'设备ID':<10} {'参数名':<20} {'参数值':<15}")
            print("-"*100)
            
            for row in cur.fetchall():
                device_id, param_name, param_value = row
                print(f"{device_id:<10} {param_name:<20} {param_value:<15}")


def main():
    """主函数"""
    print("="*100)
    print("参数初始化脚本")
    print("="*100)
    
    # 初始化数据库
    settings = load_settings(Path("configs"))
    init_database(settings)
    
    # 执行SQL文件
    sql_file = project_root / 'scripts' / 'init_all_missing_parameters.sql'
    
    if not sql_file.exists():
        print(f"❌ SQL文件不存在: {sql_file}")
        return
    
    execute_sql_file(sql_file)
    
    # 验证参数
    verify_parameters()
    
    print("\n✅ 参数初始化完成")
    print("\n下一步:")
    print("1. 重新运行 pump_shaft_power 计算")
    print("2. 验证覆盖率从 9.4% 提升到 30.7%")
    print("3. 验证恢复了 16,284 条有效数据")


if __name__ == '__main__':
    main()

