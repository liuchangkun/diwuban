"""
集成测试：main_pipeline_inlet_pressure 端到端流水线验证
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 初始化数据库和日志
from app.adapters.db import init_database
from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings

# 加载配置
config_dir = project_root / "configs"
settings = load_settings(config_dir)

# 初始化日志
init_logging(config_dir, settings.system.timezone.default)

# 初始化数据库
init_database(settings)

from app.services.calculation.metrics.main_pipeline_inlet_pressure.data_loader import DataLoader
from app.services.calculation.metrics.main_pipeline_inlet_pressure.data_filter import DataFilter
from app.services.calculation.metrics.main_pipeline_inlet_pressure.method_selector import MethodSelector
from app.services.calculation.metrics.main_pipeline_inlet_pressure.calculator import Calculator
from app.services.calculation.metrics.main_pipeline_inlet_pressure.validator import Validator
from app.services.calculation.shared.shared_services import SharedServices
from datetime import datetime
import time
import pandas as pd
import numpy as np

def main():
    print('=' * 80)
    print('步骤3：集成测试验证 - main_pipeline_inlet_pressure')
    print('=' * 80)

    # 初始化服务
    print('\n[1/5] 初始化服务...')
    services = SharedServices()
    print('✅ 服务初始化完成')

    # 查询时间范围
    print('\n[2/5] 查询时间范围...')
    station_id = 1
    device_id = 7
    start_time = datetime(2025, 10, 22, 8, 0, 0)
    end_time = datetime(2025, 10, 23, 7, 13, 29)
    print(f'时间范围: {start_time} ~ {end_time}')
    print(f'预计数据量: 83,609 条记录')

    # 运行流水线（不写入数据库）
    print('\n[3/5] 运行流水线...')
    exec_start = time.time()
    try:
        # 1. 加载参数
        params = services.parameter_manager.get_parameters(
            metric_key='main_pipeline_inlet_pressure',
            station_id=station_id,
            device_id=device_id
        )
        print(f'  - 加载参数: {len(params)} 个')

        # 2. 加载数据
        data_loader = DataLoader(trace_id='integration_test')
        data = data_loader.load_data(
            station_id=station_id,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time
        )
        print(f'  - 加载数据: {len(data)} 条')

        # 3. 过滤数据
        data_filter = DataFilter(params=params, trace_id='integration_test')
        filtered_data = data_filter.filter_data(data)
        print(f'  - 过滤数据: {len(filtered_data)} 条')

        # 4. 选择方法
        method_selector = MethodSelector(params=params, trace_id='integration_test')
        method_result = method_selector.select_method(filtered_data)
        if method_result is None:
            print('  ❌ 无法选择计算方法')
            return False
        method_id, priority = method_result
        print(f'  - 选择方法: {method_id} (优先级: {priority})')

        # 5. 执行计算
        calculator = Calculator(params=params, trace_id='integration_test')
        calculated_data = calculator.calculate(filtered_data, method_id)
        print(f'  - 计算结果: {len(calculated_data)} 条')

        # 6. 验证结果
        validator = Validator(params=params, trace_id='integration_test')
        result_df = validator.validate(calculated_data)
        print(f'  - 验证结果: {len(result_df)} 条')

        exec_elapsed = time.time() - exec_start
        print(f'✅ 流水线执行成功')
        print(f'执行时间: {exec_elapsed:.2f} 秒')
        print(f'结果数量: {len(result_df)}')
    except Exception as e:
        print(f'❌ 流水线执行失败: {e}')
        import traceback
        traceback.print_exc()
        return False

    # 验证结果
    print('\n[4/5] 验证结果...')
    print('\n=== 结果统计 ===')
    print(result_df['main_pipeline_inlet_pressure'].describe())

    print('\n=== 有效性统计 ===')
    valid_count = result_df['main_pipeline_inlet_pressure'].notna().sum()
    invalid_count = result_df['main_pipeline_inlet_pressure'].isna().sum()
    coverage_rate = valid_count / len(result_df) * 100 if len(result_df) > 0 else 0
    print(f'有效值数量: {valid_count}')
    print(f'无效值数量: {invalid_count}')
    print(f'覆盖率: {coverage_rate:.2f}%')

    print('\n=== 范围检查 ===')
    if valid_count > 0:
        valid_range = (result_df['main_pipeline_inlet_pressure'] >= 0.05) & (result_df['main_pipeline_inlet_pressure'] <= 0.50)
        in_range_count = valid_range.sum()
        out_range_count = (~valid_range & result_df['main_pipeline_inlet_pressure'].notna()).sum()
        print(f'范围内数量 (0.05~0.50 MPa): {in_range_count}')
        print(f'范围外数量: {out_range_count}')
        print(f'范围内占比: {in_range_count / valid_count * 100:.2f}%')

    print('\n=== 物理一致性检查 ===')
    if 'pool_liquid_level' in result_df.columns and valid_count > 0:
        P_atm = 0.101325
        rho = 1000.0
        g = 9.81
        h = result_df['pool_liquid_level'].astype(float)
        expected_P = P_atm + rho * g * h / 1e6
        deviation = np.abs(result_df['main_pipeline_inlet_pressure'] - expected_P) / expected_P
        deviation_valid = deviation[result_df['main_pipeline_inlet_pressure'].notna()]
        print(f'平均偏差: {deviation_valid.mean():.2%}')
        print(f'中位数偏差: {deviation_valid.median():.2%}')
        print(f'最大偏差: {deviation_valid.max():.2%}')
        print(f'偏差 ≤ 10% 的比例: {(deviation_valid <= 0.10).sum() / len(deviation_valid) * 100:.2f}%')
        print(f'偏差 ≤ 20% 的比例: {(deviation_valid <= 0.20).sum() / len(deviation_valid) * 100:.2f}%')

    # 总结
    print('\n[5/5] 测试总结')
    print('=' * 80)
    success = True
    
    if coverage_rate < 95:
        print(f'❌ 覆盖率不足: {coverage_rate:.2f}% < 95%')
        success = False
    else:
        print(f'✅ 覆盖率达标: {coverage_rate:.2f}% ≥ 95%')

    if valid_count > 0:
        in_range_rate = in_range_count / valid_count * 100
        if in_range_rate < 95:
            print(f'❌ 范围内占比不足: {in_range_rate:.2f}% < 95%')
            success = False
        else:
            print(f'✅ 范围内占比达标: {in_range_rate:.2f}% ≥ 95%')
        
        if 'pool_liquid_level' in result_df.columns:
            physics_rate = (deviation_valid <= 0.20).sum() / len(deviation_valid) * 100
            if physics_rate < 95:
                print(f'❌ 物理一致性不足: {physics_rate:.2f}% < 95%')
                success = False
            else:
                print(f'✅ 物理一致性达标: {physics_rate:.2f}% ≥ 95%')

    print('=' * 80)
    if success:
        print('✅ 集成测试通过！')
        return True
    else:
        print('❌ 集成测试失败！')
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

