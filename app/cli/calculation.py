"""
缺失指标计算功能 CLI命令

提供以下命令:
- calc:init-tables: 初始化数据库表
- calc:init-methods: 初始化计算方法注册表
- calc:init-params: 初始化计算参数表
- calc:init-device-params: 初始化设备额定参数表
- calc:missing-metrics: 计算缺失指标
"""

import sys
from pathlib import Path
from typing import List, Optional

import typer

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging
from app.services.calculation.orchestrator import CalculationOrchestrator

import logging

_act = logging.getLogger(__name__)

app = typer.Typer(help="缺失指标计算功能命令")


@app.command("init-tables")
def init_tables():
    """
    初始化数据库表

    执行 scripts/sql/calculation/create_tables.sql
    """
    _act.info("[流程-开始] [初始化数据库表]")
    typer.echo("📋 初始化数据库表...")
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "create_tables.sql"
    if not sql_file.exists():
        typer.echo(f"❌ SQL文件不存在: {sql_file}", err=True)
        raise typer.Exit(1)
    
    sql_content = sql_file.read_text(encoding="utf-8")
    
    # 执行SQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()
        
        typer.echo("✅ 数据库表初始化成功！")
    except Exception as e:
        typer.echo(f"❌ 执行失败: {e}", err=True)
        raise typer.Exit(1)


@app.command("init-methods")
def init_methods():
    """
    初始化计算方法注册表
    
    执行 scripts/sql/calculation/init_methods.sql
    """
    typer.echo("📋 初始化计算方法注册表...")
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "init_methods.sql"
    if not sql_file.exists():
        typer.echo(f"❌ SQL文件不存在: {sql_file}", err=True)
        raise typer.Exit(1)
    
    sql_content = sql_file.read_text(encoding="utf-8")
    
    # 执行SQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()
                
                # 验证
                cur.execute("SELECT metric_key, COUNT(*) FROM calculation_method_registry GROUP BY metric_key")
                results = cur.fetchall()
                
                typer.echo("✅ 计算方法注册表初始化成功！")
                for metric_key, count in results:
                    typer.echo(f"   {metric_key}: {count} 个方法")
    except Exception as e:
        typer.echo(f"❌ 执行失败: {e}", err=True)
        raise typer.Exit(1)


@app.command("init-params")
def init_params():
    """
    初始化计算参数表

    执行 scripts/sql/calculation/init_params.sql
    """
    typer.echo("📋 初始化计算参数表...")

    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)

    # 读取SQL文件
    sql_file = project_root / "scripts" / "sql" / "calculation" / "init_params.sql"
    if not sql_file.exists():
        typer.echo(f"❌ SQL文件不存在: {sql_file}", err=True)
        raise typer.Exit(1)

    sql_content = sql_file.read_text(encoding="utf-8")

    # 执行SQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()

                # 验证
                cur.execute("SELECT COUNT(*) FROM calculation_parameters WHERE device_id IS NULL")
                count = cur.fetchone()[0]

                typer.echo(f"✅ 计算参数表初始化成功！录入 {count} 个全局默认参数")
    except Exception as e:
        typer.echo(f"❌ 执行失败: {e}", err=True)
        raise typer.Exit(1)


@app.command("init-device-params")
def init_device_params():
    """
    初始化设备额定参数表

    执行 scripts/migrations/20250829_seed_device_rated_params.sql
    """
    typer.echo("📋 初始化设备额定参数表...")

    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)

    # 读取SQL文件
    sql_file = project_root / "scripts" / "migrations" / "20250829_seed_device_rated_params.sql"
    if not sql_file.exists():
        typer.echo(f"❌ SQL文件不存在: {sql_file}", err=True)
        raise typer.Exit(1)

    sql_content = sql_file.read_text(encoding="utf-8")

    # 执行SQL
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_content)
                conn.commit()

                # 验证
                cur.execute("SELECT COUNT(*) FROM device_rated_params")
                count = cur.fetchone()[0]

                typer.echo(f"✅ 设备额定参数表初始化成功！录入 {count} 个参数记录")
    except Exception as e:
        typer.echo(f"❌ 执行失败: {e}", err=True)
        raise typer.Exit(1)


@app.command("missing-metrics")
def calculate_missing_metrics(
    station_id: int = typer.Option(..., "--station-id", "-s", help="泵站ID"),
    device_id: int = typer.Option(..., "--device-id", "-d", help="设备ID"),
    start_time: str = typer.Option(..., "--start-time", "-t", help="开始时间（YYYY-MM-DD HH:MM:SS）"),
    end_time: str = typer.Option(..., "--end-time", "-e", help="结束时间（YYYY-MM-DD HH:MM:SS）"),
    metrics: Optional[List[str]] = typer.Option(None, "--metric", "-m", help="需要计算的指标（可多次指定）"),
    write: bool = typer.Option(False, "--write", "-w", help="写入数据库（默认只计算不写入）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="试运行模式（只计算不写入，与--write互斥）"),
):
    """
    计算缺失指标

    示例:
        # 只计算不写入（默认）
        python -m app.cli.calculation missing-metrics \\
            --station-id 1 --device-id 1 \\
            --start-time "2025-01-01 00:00:00" \\
            --end-time "2025-01-01 01:00:00" \\
            --metric pump_flow_rate --metric pump_head

        # 计算并写入数据库
        python -m app.cli.calculation missing-metrics \\
            --station-id 1 --device-id 1 \\
            --start-time "2025-01-01 00:00:00" \\
            --end-time "2025-01-01 01:00:00" \\
            --metric pump_flow_rate --metric pump_head \\
            --write
    """
    # 检查参数冲突
    if write and dry_run:
        typer.echo("❌ --write 和 --dry-run 参数互斥，请只使用其中一个", err=True)
        raise typer.Exit(1)
    typer.echo("📋 开始计算缺失指标...")
    typer.echo(f"   泵站ID: {station_id}")
    typer.echo(f"   设备ID: {device_id}")
    typer.echo(f"   时间范围: {start_time} ~ {end_time}")
    typer.echo(f"   指标: {metrics}")
    typer.echo(f"   模式: {'写入数据库' if write else '只计算不写入（试运行）'}")
    typer.echo()
    
    # 默认指标
    if not metrics:
        metrics = ['pump_flow_rate', 'pump_head', 'pump_outlet_pressure']
        typer.echo(f"⚠️  未指定指标，使用默认指标: {metrics}")
        typer.echo()
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 创建编排器
    orchestrator = CalculationOrchestrator()
    
    # 执行计算
    try:
        result = orchestrator.calculate_missing_metrics(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            metrics=metrics,
            write_to_db=write
        )
        
        # 显示结果
        typer.echo("=" * 60)
        typer.echo("📊 计算结果")
        typer.echo("=" * 60)
        
        if result['success']:
            typer.echo(f"✅ 计算成功")
        else:
            typer.echo(f"⚠️  计算部分成功或失败")
        
        typer.echo()
        typer.echo(f"成功计算的指标 ({len(result['metrics_calculated'])}):")
        for metric in result['metrics_calculated']:
            typer.echo(f"  ✅ {metric}")
        
        if result['metrics_failed']:
            typer.echo()
            typer.echo(f"失败的指标 ({len(result['metrics_failed'])}):")
            for metric in result['metrics_failed']:
                typer.echo(f"  ❌ {metric}")
        
        typer.echo()
        typer.echo(f"总数据点: {result['total_points']}")
        typer.echo(f"有效数据点: {result['valid_points']}")
        if result['total_points'] > 0:
            valid_rate = result['valid_points'] / result['total_points'] * 100
            typer.echo(f"有效率: {valid_rate:.2f}%")

        if write:
            typer.echo(f"已写入数据库: {result['written_points']} 条")
        
        if result['errors']:
            typer.echo()
            typer.echo("错误信息:")
            for error in result['errors']:
                typer.echo(f"  ⚠️  {error}")
        
        typer.echo("=" * 60)
        
        if not result['success']:
            raise typer.Exit(1)
        
    except Exception as e:
        typer.echo(f"❌ 计算失败: {e}", err=True)
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

