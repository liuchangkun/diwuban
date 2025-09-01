#!/usr/bin/env python3
"""
CLI兼容性测试脚本 - 修复Python 3.10+ Union语法问题
"""
from typing import Optional
import typer

app = typer.Typer(help="测试CLI兼容性")

@app.command()
def test_connection(
    verbose: Optional[bool] = typer.Option(False, "--verbose", help="显示详细信息")
) -> None:
    """测试数据库连接"""
    try:
        import psycopg
        
        conn_params = {
            "host": "localhost",
            "dbname": "pump_station_optimization", 
            "user": "postgres",
        }
        
        print(f"连接数据库: {conn_params}")
        
        with psycopg.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 as test, current_database(), current_user")
                result = cur.fetchone()
                if result:
                    test_val, db_name, user = result
                    print(f"✅ 连接成功: test={test_val}, db={db_name}, user={user}")
                    
                    if verbose:
                        # 显示表数量
                        cur.execute("""
                            SELECT count(*) FROM information_schema.tables 
                            WHERE table_schema = 'public'
                        """)
                        table_count = cur.fetchone()[0]
                        
                        # 显示函数数量
                        cur.execute("""
                            SELECT count(*) FROM pg_proc p 
                            JOIN pg_namespace n ON p.pronamespace = n.oid
                            WHERE n.nspname IN ('public', 'api', 'reporting', 'monitoring')
                        """)
                        func_count = cur.fetchone()[0]
                        
                        # 显示数据量
                        cur.execute("SELECT count(*) FROM fact_measurements")
                        data_count = cur.fetchone()[0]
                        
                        print(f"📊 数据库状态:")
                        print(f"  - 表数量: {table_count}")
                        print(f"  - 函数数量: {func_count}")  
                        print(f"  - 事实表记录数: {data_count:,}")
                        
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        raise typer.Exit(1)

@app.command()
def check_imports():
    """检查主要模块导入"""
    print("🔍 检查模块导入...")
    
    modules_to_check = [
        "app.core.config.loader",
        "app.adapters.db.gateway", 
        "app.services.ingest.prepare_dim",
        "app.models",
        "app.schemas"
    ]
    
    for module_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except Exception as e:
            print(f"❌ {module_name}: {e}")
    
    print("\n🎯 核心功能测试...")
    try:
        from app.core.config.loader import load_settings
        from pathlib import Path
        
        settings = load_settings(Path("configs"))
        print(f"✅ 配置加载成功")
        print(f"  - 数据库主机: {settings.db.host}")
        print(f"  - 数据库名称: {settings.db.name}")
        print(f"  - 导入工作线程: {settings.ingest.workers}")
        print(f"  - 日志格式: {settings.logging.format}")
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")

if __name__ == "__main__":
    app()