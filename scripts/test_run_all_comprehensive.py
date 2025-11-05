#!/usr/bin/env python3
"""
综合测试：执行 run-all 命令并收集详细日志

用途：验证完整的数据流程，重点关注 optimization_history 的处理
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings


def collect_pre_test_data():
    """收集测试前的数据"""
    print("\n" + "="*80)
    print("收集测试前的数据")
    print("="*80 + "\n")
    
    settings = Settings()
    data = {}
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 收集关键表的记录数
            tables = [
                "dim_stations",
                "dim_devices",
                "dim_metric_config",
                "fact_measurements",
                "optimization_history",
                "calculation_validation_config",
                "metric_capability_policy",
                "quality_code_dict",
            ]
            
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    data[table] = count
                    print(f"  - {table}: {count} 条记录")
                except Exception as e:
                    data[table] = f"ERROR: {e}"
                    print(f"  - {table}: 查询失败 - {e}")
            
            # 收集 optimization_history 的详细信息
            try:
                cur.execute("""
                    SELECT 
                        device_id,
                        station_id,
                        COUNT(*) as count
                    FROM optimization_history
                    GROUP BY device_id, station_id
                    ORDER BY device_id, station_id
                """)
                opt_history_details = cur.fetchall()
                data["optimization_history_details"] = opt_history_details
                
                print(f"\n  optimization_history 详细信息：")
                for row in opt_history_details:
                    print(f"    - device_id={row[0]}, station_id={row[1]}, count={row[2]}")
            except Exception as e:
                data["optimization_history_details"] = f"ERROR: {e}"
                print(f"  optimization_history 详细信息查询失败 - {e}")
    
    return data


def collect_post_test_data():
    """收集测试后的数据"""
    print("\n" + "="*80)
    print("收集测试后的数据")
    print("="*80 + "\n")
    
    settings = Settings()
    data = {}
    
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 收集关键表的记录数
            tables = [
                "dim_stations",
                "dim_devices",
                "dim_metric_config",
                "fact_measurements",
                "optimization_history",
                "calculation_validation_config",
                "metric_capability_policy",
                "quality_code_dict",
            ]
            
            for table in tables:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    data[table] = count
                    print(f"  - {table}: {count} 条记录")
                except Exception as e:
                    data[table] = f"ERROR: {e}"
                    print(f"  - {table}: 查询失败 - {e}")
            
            # 收集 optimization_history 的详细信息
            try:
                cur.execute("""
                    SELECT 
                        device_id,
                        station_id,
                        COUNT(*) as count
                    FROM optimization_history
                    GROUP BY device_id, station_id
                    ORDER BY device_id, station_id
                """)
                opt_history_details = cur.fetchall()
                data["optimization_history_details"] = opt_history_details
                
                print(f"\n  optimization_history 详细信息：")
                if opt_history_details:
                    for row in opt_history_details:
                        print(f"    - device_id={row[0]}, station_id={row[1]}, count={row[2]}")
                else:
                    print(f"    （无记录）")
            except Exception as e:
                data["optimization_history_details"] = f"ERROR: {e}"
                print(f"  optimization_history 详细信息查询失败 - {e}")
            
            # 检查外键约束冲突
            try:
                cur.execute("""
                    SELECT COUNT(*) FROM optimization_history
                    WHERE device_id NOT IN (SELECT id FROM dim_devices)
                       OR station_id NOT IN (SELECT id FROM dim_stations)
                """)
                invalid_count = cur.fetchone()[0]
                data["optimization_history_invalid_fk"] = invalid_count
                
                if invalid_count > 0:
                    print(f"\n  ⚠️  发现 {invalid_count} 条 optimization_history 记录的外键无效")
                else:
                    print(f"\n  ✅ 所有 optimization_history 记录的外键都有效")
            except Exception as e:
                data["optimization_history_invalid_fk"] = f"ERROR: {e}"
                print(f"  外键验证失败 - {e}")
    
    return data


def run_all_command():
    """执行 run-all 命令"""
    print("\n" + "="*80)
    print("执行 run-all 命令")
    print("="*80 + "\n")
    
    # 执行命令
    cmd = [
        sys.executable,
        "-m",
        "app.cli.main",
        "run-all",
        "configs/data_mapping.v2.json"
    ]
    
    print(f"命令: {' '.join(cmd)}\n")
    
    # 执行并捕获输出
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True
    )
    
    return result


def main():
    """主函数"""
    print("\n" + "="*80)
    print("综合测试：run-all 命令")
    print("="*80)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 收集测试前的数据
    pre_data = collect_pre_test_data()
    
    # 执行 run-all 命令
    result = run_all_command()
    
    # 保存日志
    log_dir = Path("logs/test_run_all")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    stdout_file = log_dir / f"stdout_{timestamp}.log"
    stderr_file = log_dir / f"stderr_{timestamp}.log"
    
    stdout_file.write_text(result.stdout, encoding="utf-8")
    stderr_file.write_text(result.stderr, encoding="utf-8")
    
    print(f"\n日志已保存：")
    print(f"  - stdout: {stdout_file}")
    print(f"  - stderr: {stderr_file}")
    
    # 显示执行结果
    print(f"\n执行结果：")
    print(f"  - 返回码: {result.returncode}")
    print(f"  - stdout 长度: {len(result.stdout)} 字符")
    print(f"  - stderr 长度: {len(result.stderr)} 字符")
    
    if result.returncode == 0:
        print(f"\n✅ run-all 命令执行成功")
    else:
        print(f"\n❌ run-all 命令执行失败")
        print(f"\nstderr 内容：")
        print(result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
    
    # 收集测试后的数据
    post_data = collect_post_test_data()
    
    # 对比数据
    print("\n" + "="*80)
    print("数据对比")
    print("="*80 + "\n")
    
    for table in ["dim_stations", "dim_devices", "dim_metric_config", "fact_measurements", "optimization_history"]:
        pre_count = pre_data.get(table, "N/A")
        post_count = post_data.get(table, "N/A")
        
        if isinstance(pre_count, int) and isinstance(post_count, int):
            diff = post_count - pre_count
            status = "✅" if diff >= 0 else "⚠️"
            print(f"{status} {table}: {pre_count} → {post_count} (差异: {diff:+d})")
        else:
            print(f"❌ {table}: {pre_count} → {post_count}")
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80 + "\n")
    
    if result.returncode == 0:
        print("✅ run-all 命令执行成功")
        
        # 检查 optimization_history
        opt_pre = pre_data.get("optimization_history", 0)
        opt_post = post_data.get("optimization_history", 0)
        
        if isinstance(opt_pre, int) and isinstance(opt_post, int):
            if opt_post > 0:
                print(f"✅ optimization_history 恢复成功：{opt_post} 条记录")
            elif opt_pre > 0:
                print(f"⚠️  optimization_history 恢复后为空（备份前有 {opt_pre} 条记录）")
            else:
                print(f"ℹ️  optimization_history 备份前后都为空")
        
        # 检查外键
        invalid_fk = post_data.get("optimization_history_invalid_fk", 0)
        if isinstance(invalid_fk, int):
            if invalid_fk == 0:
                print(f"✅ 所有 optimization_history 记录的外键都有效")
            else:
                print(f"❌ 发现 {invalid_fk} 条 optimization_history 记录的外键无效")
        
        return 0
    else:
        print("❌ run-all 命令执行失败")
        print(f"请查看日志文件：{stderr_file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

