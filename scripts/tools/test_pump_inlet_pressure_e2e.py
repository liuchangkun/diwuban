#!/usr/bin/env python3
"""
pump_inlet_pressure 端到端测试

测试目标：
1. 测试完整的6阶段计算流程
2. 验证参数加载（包括设备参数）
3. 验证计算结果写入
4. 测试参数缺失情况的降级处理

测试范围：
- 泵站1的设备（device_id = 1-6）
- 选择有完整数据的1小时时间窗口
- 使用真实数据库数据
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db import init_database
from app.core.logging.setup import init_logging

# 导入共用模块
from app.services.calculation.shared.shared_services import SharedServices

# 导入 pump_inlet_pressure 专用模块
from app.services.calculation.metrics.pump_inlet_pressure.data_loader import DataLoader
from app.services.calculation.metrics.pump_inlet_pressure.data_filter import DataFilter
from app.services.calculation.metrics.pump_inlet_pressure.method_selector import MethodSelector
from app.services.calculation.metrics.pump_inlet_pressure.calculator import Calculator
from app.services.calculation.metrics.pump_inlet_pressure.validator import Validator

TZ_SH = timezone(timedelta(hours=8))


def test_e2e():
    """端到端测试"""
    print("=" * 80)
    print("pump_inlet_pressure 端到端测试")
    print("=" * 80)
    
    # 步骤1: 初始化应用
    print("\n📋 步骤1: 初始化应用")
    config_dir = Path("configs")
    settings = load_settings(config_dir)
    init_logging(config_dir, settings.system.timezone.default)
    init_database(settings)
    print("✅ 应用初始化成功")
    
    # 步骤2: 初始化共用服务
    print("\n📋 步骤2: 初始化共用服务（SharedServices）")
    shared_services = SharedServices()
    print(f"✅ 共用服务初始化成功")
    print(f"   - Scheduler: {shared_services.scheduler}")
    print(f"   - DataWriter: {shared_services.data_writer}")
    print(f"   - ParameterManager: {shared_services.parameter_manager}")
    
    # 步骤3: 配置测试参数
    print("\n📋 步骤3: 配置测试参数")
    station_id = 1
    device_ids = [1, 2, 3]  # 测试前3个设备
    start_time = datetime(2025, 10, 23, 11, 0, 0, tzinfo=TZ_SH)
    end_time = datetime(2025, 10, 23, 12, 0, 0, tzinfo=TZ_SH)
    
    print(f"   - 泵站ID: {station_id}")
    print(f"   - 设备ID: {device_ids}")
    print(f"   - 时间范围: {start_time} ~ {end_time}")
    
    # 步骤4: 插入临时设备参数（用于测试）
    print("\n📋 步骤4: 插入临时设备参数（用于测试）")
    from app.adapters.db.pool import get_connection

    # 为设备1-3插入临时参数
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 删除旧的设备参数
            cur.execute("""
                DELETE FROM calculation_parameters
                WHERE metric_key = 'pump_inlet_pressure'
                  AND device_id IN (1, 2, 3)
            """)

            # 插入新的设备参数（L_offset 和 pipe_diameter）
            for device_id in [1, 2, 3]:
                cur.execute("""
                    INSERT INTO calculation_parameters
                    (station_id, device_id, metric_key, method_id, param_name, param_value, param_type, is_optimizable)
                    VALUES
                    (1, %s, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'L_offset', 2.5, 'float', FALSE),
                    (1, %s, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b', 'pipe_diameter', 0.3, 'float', FALSE)
                    ON CONFLICT (device_id, metric_key, method_id, param_name)
                    DO UPDATE SET param_value = EXCLUDED.param_value
                """, (device_id, device_id))

            conn.commit()

    print(f"✅ 临时设备参数插入成功（L_offset=2.5m, pipe_diameter=0.3m）")

    # 步骤5: 测试 ParameterManager
    print("\n📋 步骤5: 测试 ParameterManager（从数据库读取配置）")
    params = shared_services.parameter_manager.get_parameters(
        metric_key='pump_inlet_pressure',
        method_id=None,
        station_id=station_id,
        device_id=None
    )
    print(f"✅ 全局参数加载成功: {params}")
    
    # 步骤6: 开始端到端测试
    print("\n📋 步骤6: 开始端到端测试")
    
    all_results = []
    success_count = 0
    failed_devices = []
    
    for device_id in device_ids:
        print(f"\n{'=' * 60}")
        print(f"处理设备 {device_id}")
        print(f"{'=' * 60}")
        
        try:
            # 加载设备参数
            device_params = shared_services.parameter_manager.get_parameters(
                metric_key='pump_inlet_pressure',
                method_id=None,
                station_id=station_id,
                device_id=device_id
            )
            print(f"\n  📦 设备参数: {device_params}")
            
            # 阶段1: DataLoader
            print(f"\n  🔹 阶段1: DataLoader")
            data_loader = DataLoader()
            df_raw = data_loader.load_data(station_id, device_id, start_time, end_time)
            print(f"    ✅ 加载了 {len(df_raw)} 行数据")
            
            if df_raw.empty:
                print(f"    ⚠️ 没有数据，跳过")
                failed_devices.append((device_id, "no data"))
                continue
            
            # 阶段2: DataFilter
            print(f"\n  🔹 阶段2: DataFilter")
            data_filter = DataFilter()
            df_filtered = data_filter.filter_data(df_raw)
            print(f"    ✅ 过滤后剩余 {len(df_filtered)} 行")
            
            if df_filtered.empty:
                print(f"    ⚠️ 过滤后没有数据，跳过")
                failed_devices.append((device_id, "no data after filter"))
                continue

            # 阶段3: MethodSelector
            print(f"\n  🔹 阶段3: MethodSelector")
            method_selector = MethodSelector(device_params=device_params)
            method_id = method_selector.select_method(df_filtered)
            print(f"    ✅ 选择方法: {method_id}")

            # 阶段4: Calculator
            print(f"\n  🔹 阶段4: Calculator")
            calculator = Calculator()
            df_calculated = calculator.calculate(df_filtered, method_id, device_params)
            print(f"    ✅ 计算完成: {len(df_calculated)} 行")

            if not df_calculated.empty:
                print(f"    ✅ 压力统计: min={df_calculated['pump_inlet_pressure'].min():.4f} MPa, "
                      f"max={df_calculated['pump_inlet_pressure'].max():.4f} MPa, "
                      f"mean={df_calculated['pump_inlet_pressure'].mean():.4f} MPa")

            # 阶段5: Validator
            print(f"\n  🔹 阶段5: Validator")
            validator = Validator(params=device_params)
            validation_result = validator.validate(df_calculated, df_filtered)
            print(f"    ✅ 验证完成: 有效={validation_result['valid_count']}, "
                  f"无效={validation_result['invalid_count']}, "
                  f"质量代码={validation_result['quality_code']}")

            # 阶段6: DataWriter
            print(f"\n  🔹 阶段6: DataWriter")
            if validation_result['valid_count'] > 0:
                from app.services.calculation.shared.data_writer import WriteRecord
                import pytz

                TZ_SH_PYTZ = pytz.timezone('Asia/Shanghai')
                calculated_at = datetime.now(TZ_SH_PYTZ)

                records = []
                for _, row in validation_result['valid_results'].iterrows():
                    if not pd.isna(row['pump_inlet_pressure']):
                        records.append(WriteRecord(
                            device_id=device_id,
                            metric_key='pump_inlet_pressure',
                            timestamp=row['ts_bucket'],
                            value=float(row['pump_inlet_pressure']),
                            quality_code=int(row.get('quality_code', 0)),
                            method_id=method_id,
                            calculated_at=calculated_at
                        ))

                written_count = shared_services.data_writer.write(records, station_id=station_id)
                print(f"    ✅ 写入数据库: {written_count} 条记录")

                all_results.append({
                    'device_id': device_id,
                    'method_id': method_id,
                    'calculated_rows': len(df_calculated),
                    'valid_rows': validation_result['valid_count'],
                    'written_rows': written_count,
                    'quality_code': validation_result['quality_code']
                })
                success_count += 1
            else:
                print(f"    ⚠️ 没有有效数据，跳过写入")
                failed_devices.append((device_id, "no valid data"))

        except Exception as e:
            print(f"    ❌ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            failed_devices.append((device_id, str(e)))

    # 步骤7: 汇总结果
    print(f"\n{'=' * 80}")
    print("测试汇总")
    print(f"{'=' * 80}")
    print(f"✅ 成功设备数: {success_count}/{len(device_ids)}")
    print(f"❌ 失败设备数: {len(failed_devices)}")

    if failed_devices:
        print(f"\n失败设备详情:")
        for device_id, reason in failed_devices:
            print(f"  - 设备{device_id}: {reason}")

    if all_results:
        print(f"\n成功设备详情:")
        for result in all_results:
            print(f"  - 设备{result['device_id']}: 方法={result['method_id']}, "
                  f"计算={result['calculated_rows']}行, 有效={result['valid_rows']}行, "
                  f"写入={result['written_rows']}行, 质量={result['quality_code']}")

    print(f"\n{'=' * 80}")
    print("测试完成")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    import pandas as pd
    test_e2e()

