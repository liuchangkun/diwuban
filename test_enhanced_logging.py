#!/usr/bin/env python
"""
测试增强日志功能

这个脚本用于测试新增的日志功能，包括：
1. 函数内部执行过程日志
2. SQL执行日志配置
3. 关键指标日志记录
4. 条件分支和循环日志
"""

import logging
import time
from pathlib import Path
from app.core.config.loader import load_settings
from app.utils.logging_decorators import (
    enhanced_logger,
    create_internal_step_logger,
    log_business_milestone,
    log_data_quality_check,
    log_key_metrics,
    business_logger
)
from app.adapters.logging.init import init_logging


def setup_test_logging():
    """设置测试日志环境"""
    settings = load_settings(Path('configs'))
    run_dir = Path('logs/test_run')
    run_dir.mkdir(parents=True, exist_ok=True)
    
    init_logging(settings, run_dir)
    return settings


@enhanced_logger(
    log_entry=True,
    log_exit=True,
    log_parameters=True,
    log_performance=True,
    business_context="测试函数"
)
def test_basic_logging_features(data_size: int, enable_validation: bool = True):
    """测试基本日志功能"""
    logger = logging.getLogger(__name__)
    
    # 创建内部步骤日志记录器
    step_logger = create_internal_step_logger("test_basic_logging_features", logger)
    
    step_logger.step("开始处理数据", data_size=data_size)
    
    # 模拟数据处理
    processed_items = 0
    
    # 测试条件分支日志
    if enable_validation:
        step_logger.branch("数据验证启用检查", True, "启用数据验证")
        
        # 测试数据验证日志
        step_logger.validation("数据大小检查", data_size > 0, f"数据大小: {data_size}")
        step_logger.validation("数据范围检查", data_size < 10000, f"数据在合理范围内")
    else:
        step_logger.branch("数据验证启用检查", False, "跳过数据验证")
    
    # 测试循环迭代日志
    if data_size > 0:
        step_logger.step("开始数据处理循环")
        iteration_logger = step_logger.iteration_start("数据处理", data_size)
        
        for i in range(data_size):
            # 模拟处理时间
            time.sleep(0.001)
            processed_items += 1
            
            # 每100项更新一次进度
            if i % 100 == 0 or i == data_size - 1:
                iteration_logger.update(1 if i == 0 else 100, f"处理项目 {i+1}")
        
        iteration_logger.complete(f"成功处理 {processed_items} 项数据")
    
    # 测试数据转换日志
    step_logger.transformation("数据格式转换", f"{data_size} 原始项", f"{processed_items} 处理后项")
    
    # 测试检查点日志
    step_logger.checkpoint("数据处理完成", {
        "input_size": data_size,
        "output_size": processed_items,
        "success_rate": processed_items / data_size if data_size > 0 else 0
    })
    
    return processed_items


@business_logger("文件处理模拟", enable_progress=True)
def test_file_processing_simulation():
    """测试文件处理模拟场景"""
    logger = logging.getLogger(__name__)
    
    # 记录业务里程碑
    log_business_milestone("文件处理开始", {
        "file_count": 5,
        "expected_size": "1MB",
        "processing_mode": "batch"
    }, logger)
    
    # 模拟文件处理
    files_processed = 0
    total_size = 0
    
    for i in range(5):
        file_size = (i + 1) * 1024  # 模拟文件大小
        files_processed += 1
        total_size += file_size
        
        # 记录关键指标
        log_key_metrics("文件处理进度", {
            "current_file": i + 1,
            "total_files": 5,
            "file_size_bytes": file_size,
            "cumulative_size_bytes": total_size,
            "progress_percent": (i + 1) / 5 * 100
        }, logger)
        
        time.sleep(0.1)  # 模拟处理时间
    
    # 数据质量检查
    log_data_quality_check("文件完整性检查", True, {
        "files_processed": files_processed,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "error_count": 0
    }, logger)
    
    log_business_milestone("文件处理完成", {
        "files_processed": files_processed,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "processing_time_seconds": 0.5
    }, logger)
    
    return files_processed, total_size


def test_sql_execution_logging():
    """测试SQL执行日志功能"""
    from app.utils.logging_decorators import log_sql_execution, log_sql_statement
    
    logger = logging.getLogger("sql")
    
    # 测试SQL语句记录
    test_sql = "SELECT * FROM test_table WHERE id = %s AND status = %s"
    test_params = {"id": 123, "status": "active", "password": "secret123"}
    
    log_sql_statement(test_sql, test_params, logger)
    
    # 测试SQL执行结果记录
    log_sql_execution(
        sql_type="SELECT",
        sql_summary="查询测试表中的活跃记录",
        execution_time_ms=45.67,
        affected_rows=10,
        table_name="test_table",
        parameters=test_params,
        logger=logger
    )
    
    # 测试慢查询记录
    log_sql_execution(
        sql_type="UPDATE",
        sql_summary="批量更新用户状态",
        execution_time_ms=1500.0,  # 超过阈值
        affected_rows=1000,
        table_name="users",
        logger=logger
    )
    
    # 测试SQL执行失败记录
    log_sql_execution(
        sql_type="INSERT",
        sql_summary="插入新用户记录",
        execution_time_ms=25.3,
        affected_rows=0,
        table_name="users",
        error="重复的主键值",
        logger=logger
    )


def main():
    """主测试函数"""
    print("🧪 开始测试增强日志功能...")
    
    # 设置日志环境
    settings = setup_test_logging()
    print("✅ 日志环境设置完成")
    
    # 测试基本日志功能
    print("\n📝 测试基本日志功能...")
    result1 = test_basic_logging_features(500, True)
    print(f"✅ 基本日志功能测试完成，处理了 {result1} 项数据")
    
    # 测试文件处理模拟
    print("\n📁 测试文件处理模拟...")
    files, size = test_file_processing_simulation()
    print(f"✅ 文件处理模拟完成，处理了 {files} 个文件，总大小 {size} 字节")
    
    # 测试SQL执行日志
    print("\n🗃️ 测试SQL执行日志...")
    test_sql_execution_logging()
    print("✅ SQL执行日志测试完成")
    
    # 记录测试完成里程碑
    logger = logging.getLogger(__name__)
    log_business_milestone("增强日志功能测试完成", {
        "test_cases": 3,
        "basic_logging": "通过",
        "file_processing": "通过", 
        "sql_logging": "通过",
        "config_features": {
            "detailed_logging": len([attr for attr in dir(settings.logging.detailed_logging) if not attr.startswith('_')]),
            "key_metrics": len([attr for attr in dir(settings.logging.key_metrics) if not attr.startswith('_')]),
            "sql_execution": len([attr for attr in dir(settings.logging.sql_execution) if not attr.startswith('_')]),
            "internal_execution": len([attr for attr in dir(settings.logging.internal_execution) if not attr.startswith('_')])
        }
    }, logger)
    
    print("\n🎉 所有测试完成！请查看 logs/test_run/ 目录下的日志文件")
    print("📋 新增功能总结：")
    print("   - ✅ 函数内部执行步骤日志")
    print("   - ✅ 条件分支执行日志") 
    print("   - ✅ 循环迭代进度日志")
    print("   - ✅ 数据验证和转换日志")
    print("   - ✅ 检查点和里程碑日志")
    print("   - ✅ SQL执行详细日志")
    print("   - ✅ 业务关键指标日志")
    print("   - ✅ 通过 logging.yaml 完全配置控制")


if __name__ == "__main__":
    main()