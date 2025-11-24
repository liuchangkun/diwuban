"""
数据质量分析脚本
分析所有已实现指标的数据质量（覆盖率、数值分布、物理一致性、时间序列）
"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 初始化数据库和日志
from app.adapters.db import init_database, get_connection
from app.core.logging.setup import init_logging
from app.core.config.loader_new import load_settings

# 加载配置
config_dir = project_root / "configs"
settings = load_settings(config_dir)

# 初始化日志
init_logging(config_dir, settings.system.timezone.default)

# 初始化数据库
init_database(settings)


def analyze_metric_quality(metric_key: str, device_ids: list, start_time: datetime, end_time: datetime):
    """
    分析单个指标的数据质量
    
    Args:
        metric_key: 指标键
        device_ids: 设备ID列表
        start_time: 开始时间
        end_time: 结束时间
    """
    print(f'\n{"=" * 80}')
    print(f'指标: {metric_key}')
    print(f'{"=" * 80}')
    
    # 获取指标ID
    with get_connection() as conn:
        metric_id_query = """
            SELECT id FROM dim_metric_config WHERE metric_key = %s
        """
        metric_id = pd.read_sql(metric_id_query, conn, params=(metric_key,))['id'].iloc[0]
    
    # 查询数据
    query = """
        SELECT
            ts_bucket,
            device_id,
            value
        FROM fact_measurements
        WHERE metric_id = %s
          AND device_id = ANY(%s)
          AND ts_bucket >= %s
          AND ts_bucket <= %s
        ORDER BY device_id, ts_bucket
    """

    with get_connection() as conn:
        df = pd.read_sql(query, conn, params=(metric_id, device_ids, start_time, end_time))

    if df.empty:
        print('  ⚠️  无数据')
        return

    # 1. 覆盖率分析
    print(f'\n[1] 覆盖率分析')
    total_records = len(df)
    # 检查有效值（非NaN, 非Inf）
    valid_mask = np.isfinite(df['value'])
    valid_records = valid_mask.sum()
    coverage = valid_records / total_records * 100 if total_records > 0 else 0

    print(f'  - 总记录数: {total_records:,}')
    print(f'  - 有效记录数: {valid_records:,}')
    print(f'  - 覆盖率: {coverage:.2f}%')

    # 按设备统计
    print(f'\n  按设备统计:')
    for device_id in sorted(df['device_id'].unique()):
        device_df = df[df['device_id'] == device_id]
        device_total = len(device_df)
        device_valid = np.isfinite(device_df['value']).sum()
        device_coverage = device_valid / device_total * 100 if device_total > 0 else 0
        print(f'    设备{device_id}: {device_valid:,}/{device_total:,} ({device_coverage:.2f}%)')

    # 2. 数值分布分析
    print(f'\n[2] 数值分布分析')
    valid_df = df[valid_mask]
    
    if not valid_df.empty:
        print(f'  - 平均值: {valid_df["value"].mean():.4f}')
        print(f'  - 标准差: {valid_df["value"].std():.4f}')
        print(f'  - 最小值: {valid_df["value"].min():.4f}')
        print(f'  - 25%分位: {valid_df["value"].quantile(0.25):.4f}')
        print(f'  - 50%分位(中位数): {valid_df["value"].quantile(0.50):.4f}')
        print(f'  - 75%分位: {valid_df["value"].quantile(0.75):.4f}')
        print(f'  - 最大值: {valid_df["value"].max():.4f}')
        
        # 检测异常值（使用IQR方法）
        Q1 = valid_df["value"].quantile(0.25)
        Q3 = valid_df["value"].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = valid_df[(valid_df["value"] < lower_bound) | (valid_df["value"] > upper_bound)]
        outlier_ratio = len(outliers) / len(valid_df) * 100 if len(valid_df) > 0 else 0
        
        print(f'\n  异常值检测 (IQR方法):')
        print(f'    - 下界: {lower_bound:.4f}')
        print(f'    - 上界: {upper_bound:.4f}')
        print(f'    - 异常值数量: {len(outliers):,}')
        print(f'    - 异常值比例: {outlier_ratio:.2f}%')
    
    # 3. 时间序列分析
    print(f'\n[3] 时间序列分析')
    df['date'] = pd.to_datetime(df['ts_bucket']).dt.date
    df['is_valid'] = valid_mask

    daily_stats = df.groupby('date').agg({
        'value': ['count', 'mean', 'std', 'min', 'max'],
        'is_valid': 'sum'
    }).round(4)

    print(f'  按日期统计:')
    print(f'    日期         | 记录数  | 有效数  | 平均值    | 标准差    | 最小值    | 最大值')
    print(f'    {"-" * 85}')
    for date, row in daily_stats.iterrows():
        print(f'    {date} | {int(row[("value", "count")]):7,} | {int(row[("is_valid", "sum")]):7,} | '
              f'{row[("value", "mean")]:9.4f} | {row[("value", "std")]:9.4f} | '
              f'{row[("value", "min")]:9.4f} | {row[("value", "max")]:9.4f}')


def main():
    print('=' * 80)
    print('数据质量分析')
    print('=' * 80)
    
    # 时间范围
    start_time = datetime(2025, 10, 22, 8, 0, 0)
    end_time = datetime(2025, 10, 23, 7, 13, 29)
    
    # 分析所有指标
    metrics_config = [
        ("pump_flow_rate", [1, 2, 3, 4, 5, 6]),
        ("pump_inlet_pressure", [1, 2, 3, 4, 5, 6]),
        ("main_pipeline_inlet_pressure", [7]),
        ("pump_head", [1, 2, 3, 4, 5, 6]),
        ("pump_efficiency", [1, 2, 3, 4, 5, 6]),
        ("pump_speed", [1, 2, 3, 4, 5, 6])
    ]
    
    for metric_key, device_ids in metrics_config:
        try:
            analyze_metric_quality(metric_key, device_ids, start_time, end_time)
        except Exception as e:
            print(f'\n  ❌ 分析失败: {e}')
            import traceback
            traceback.print_exc()
    
    print(f'\n{"=" * 80}')
    print('数据质量分析完成')
    print('=' * 80)


if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f'\n❌ 执行失败: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

