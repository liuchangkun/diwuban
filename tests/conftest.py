"""
pytest 配置文件

提供全局 fixtures 和测试配置

⚠️ **数据库数据保护规则**：

1. **禁止清空原始测量数据**：
   - `fact_measurements` 表中的原始测量数据（5,366,308 行）不能被测试清空
   - 禁止使用 TRUNCATE, DELETE, DROP 等操作清空原始数据

2. **禁止清空维度表**：
   - `dim_devices`, `dim_stations`, `dim_metric_config`, `dim_metric_metadata`, `mv_device_running_1s` 等表不能被测试清空

3. **允许清空计算结果数据**：
   - `fact_measurements` 表中由 calculation 阶段计算出来的数据（pump_flow_rate, pump_head, pump_efficiency 等指标）可以根据测试需要清空和重新计算
   - 但建议使用事务回滚而不是真正删除数据

4. **使用事务回滚**：
   - 如果测试需要修改数据，应该使用 `db_transaction` fixture
   - 测试结束后会自动回滚，不会污染数据库

5. **推荐做法**：
   - 单元测试：使用 mock 数据或 `sample_data` fixture（假数据）
   - 集成测试：使用 `db_connection` fixture（只读）或 `db_transaction` fixture（写入后自动回滚）
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Dict, Any
import psycopg
from psycopg.rows import dict_row
import yaml


@pytest.fixture(scope="session", autouse=True)
def initialize_db_pool():
    """初始化数据库连接池（session级别，自动使用）"""
    from app.core.config.loader_new import load_settings
    from app.adapters.db.pool import initialize_pool, close_pool

    # 初始化连接池
    settings = load_settings(Path("configs"))
    initialize_pool(settings)

    yield

    # 测试结束后关闭连接池
    close_pool()


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        'min_flow': 0.0,
        'max_flow': 500.0,
        'max_ratio': 1.1,
        'alpha': 1.0,
        'beta': 1.0,
        'derivative_window': 5,
        'batch_size': 1000,
        'target_duration_ms': 500,
    }


@pytest.fixture(scope="session")
def db_config():
    """数据库配置（从 configs/database.yaml 读取）"""
    config_path = Path(__file__).parent.parent / "configs" / "database.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


@pytest.fixture(scope="session")
def db_connection(db_config):
    """真实数据库连接（session级别，所有测试共享）

    注意：此连接仅用于读取数据，不应该用于写入操作。
    如果测试需要写入数据，应该使用 db_transaction fixture。
    """
    dsn = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    conn = psycopg.connect(dsn, row_factory=dict_row)
    # 设置为只读模式（可选，但建议）
    # conn.read_only = True  # psycopg3 不支持此属性，改用事务控制
    yield conn
    conn.close()


@pytest.fixture
def db_transaction(db_config):
    """数据库事务 fixture（function级别，每个测试独立）

    此 fixture 会在测试开始时开启事务，测试结束后自动回滚。
    用于需要写入数据的测试，确保测试不会污染数据库。

    使用示例：
        def test_something(db_transaction):
            with db_transaction.cursor() as cur:
                cur.execute("INSERT INTO ...")
            # 测试结束后自动回滚，数据不会真正写入
    """
    dsn = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=False)

    # 开启事务
    # psycopg3 默认就是事务模式，不需要显式 BEGIN

    yield conn

    # 测试结束后回滚事务
    conn.rollback()
    conn.close()


@pytest.fixture
def real_device_ids(db_connection):
    """获取真实设备ID列表"""
    try:
        with db_connection.cursor() as cur:
            cur.execute("SELECT id FROM dim_devices WHERE type = 'pump' ORDER BY id LIMIT 6")
            return [row['id'] for row in cur.fetchall()]
    except Exception:
        db_connection.rollback()
        raise


@pytest.fixture
def real_time_range(db_connection):
    """获取真实数据的时间范围"""
    try:
        with db_connection.cursor() as cur:
            cur.execute("""
                SELECT
                    MIN(ts_bucket) as min_ts,
                    MAX(ts_bucket) as max_ts
                FROM fact_measurements
                WHERE device_id IN (SELECT id FROM dim_devices WHERE type = 'pump' LIMIT 6)
            """)
            result = cur.fetchone()
            return {
                'start': result['min_ts'],
                'end': result['max_ts']
            }
    except Exception:
        db_connection.rollback()
        raise


@pytest.fixture
def mock_db_connection():
    """Mock 数据库连接"""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cursor
    return conn


@pytest.fixture
def sample_data():
    """生成示例数据（单设备）- 使用假数据用于单元测试"""
    timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1s')
    data = pd.DataFrame({
        'ts_bucket': timestamps,
        'device_id': 105,
        'main_pipeline_flow_rate': np.random.uniform(100, 150, 100),
        'pump_active_power': np.random.uniform(40, 50, 100),
        'pump_frequency': np.random.uniform(45, 50, 100),
        'running': 1,
        'other_devices': [[] for _ in range(100)]
    })
    return data


@pytest.fixture
def real_sample_data(db_connection, real_device_ids):
    """加载真实数据（单设备）- 用于集成测试

    从数据库加载设备3的真实数据（有 pump_flow_rate 计算结果）
    时间范围：2025-10-23 10:48:06 ~ 2025-10-23 12:20:28（约1.5小时，5543条记录）
    """
    device_id = 3  # 设备3有完整的 pump_flow_rate 数据

    with db_connection.cursor() as cur:
        # 加载设备3的数据，包含 running 状态
        cur.execute("""
            SELECT
                fm.ts_bucket,
                fm.device_id,
                fm.value,
                dmc.metric_key,
                mvr.running
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            LEFT JOIN mv_device_running_1s mvr ON
                fm.device_id = mvr.device_id AND
                fm.ts_bucket = mvr.ts_bucket
            WHERE fm.device_id = %s
                AND fm.ts_bucket >= '2025-10-23 10:48:00+08'::timestamptz
                AND fm.ts_bucket < '2025-10-23 11:00:00+08'::timestamptz
                AND dmc.metric_key IN (
                    'main_pipeline_flow_rate',
                    'pump_active_power',
                    'pump_frequency',
                    'pump_flow_rate',
                    'pump_cumulative_flow'
                )
            ORDER BY fm.ts_bucket, dmc.metric_key
        """, (device_id,))

        rows = cur.fetchall()

    # 转换为 DataFrame（宽表格式）
    if not rows:
        raise ValueError(f"设备 {device_id} 没有找到真实数据")

    # 按时间戳分组，转换为宽表
    data_dict = {}
    for row in rows:
        ts = row['ts_bucket']
        if ts not in data_dict:
            data_dict[ts] = {
                'ts_bucket': ts,
                'device_id': row['device_id'],
                'running': row['running'] or 0
            }
        data_dict[ts][row['metric_key']] = row['value']

    df = pd.DataFrame(list(data_dict.values()))
    df = df.sort_values('ts_bucket').reset_index(drop=True)

    # 添加 other_devices 列（空列表，因为这是单设备测试）
    df['other_devices'] = [[] for _ in range(len(df))]

    return df


@pytest.fixture
def sample_multi_device_data():
    """生成示例数据（多设备）- 使用假数据用于单元测试"""
    timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1s')

    # 其他设备数据
    other_devices = []
    for _ in range(100):
        other_devices.append([
            {'device_id': 106, 'pump_active_power': 45.0, 'pump_frequency': 48.0, 'running': 1},
            {'device_id': 107, 'pump_active_power': 42.0, 'pump_frequency': 46.0, 'running': 1}
        ])

    data = pd.DataFrame({
        'ts_bucket': timestamps,
        'device_id': 105,
        'main_pipeline_flow_rate': np.random.uniform(200, 300, 100),
        'pump_active_power': np.random.uniform(40, 50, 100),
        'pump_frequency': np.random.uniform(45, 50, 100),
        'running': 1,
        'other_devices': other_devices
    })
    return data


@pytest.fixture
def real_multi_device_data(db_connection):
    """加载真实数据（多设备）- 用于集成测试

    从数据库加载设备3、4、5的真实数据
    时间范围：2025-10-23 10:48:00 ~ 2025-10-23 11:00:00（12分钟）
    """
    target_device_id = 3  # 主设备
    other_device_ids = [4, 5]  # 其他运行设备

    with db_connection.cursor() as cur:
        # 加载主设备数据
        cur.execute("""
            SELECT
                fm.ts_bucket,
                fm.device_id,
                fm.value,
                dmc.metric_key,
                mvr.running
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            LEFT JOIN mv_device_running_1s mvr ON
                fm.device_id = mvr.device_id AND
                fm.ts_bucket = mvr.ts_bucket
            WHERE fm.device_id = %s
                AND fm.ts_bucket >= '2025-10-23 10:48:00+08'::timestamptz
                AND fm.ts_bucket < '2025-10-23 11:00:00+08'::timestamptz
                AND dmc.metric_key IN (
                    'main_pipeline_flow_rate',
                    'pump_active_power',
                    'pump_frequency',
                    'pump_flow_rate'
                )
            ORDER BY fm.ts_bucket, dmc.metric_key
        """, (target_device_id,))
        main_rows = cur.fetchall()

        # 加载其他设备数据
        cur.execute("""
            SELECT
                fm.ts_bucket,
                fm.device_id,
                fm.value,
                dmc.metric_key,
                mvr.running
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            LEFT JOIN mv_device_running_1s mvr ON
                fm.device_id = mvr.device_id AND
                fm.ts_bucket = mvr.ts_bucket
            WHERE fm.device_id = ANY(%s)
                AND fm.ts_bucket >= '2025-10-23 10:48:00+08'::timestamptz
                AND fm.ts_bucket < '2025-10-23 11:00:00+08'::timestamptz
                AND dmc.metric_key IN (
                    'pump_active_power',
                    'pump_frequency'
                )
                AND mvr.running = 1
            ORDER BY fm.ts_bucket, fm.device_id, dmc.metric_key
        """, (other_device_ids,))
        other_rows = cur.fetchall()

    # 转换主设备数据为 DataFrame
    main_data_dict = {}
    for row in main_rows:
        ts = row['ts_bucket']
        if ts not in main_data_dict:
            main_data_dict[ts] = {
                'ts_bucket': ts,
                'device_id': row['device_id'],
                'running': row['running'] or 0
            }
        main_data_dict[ts][row['metric_key']] = row['value']

    # 构建 other_devices 数据
    other_data_dict = {}
    for row in other_rows:
        ts = row['ts_bucket']
        device_id = row['device_id']
        if ts not in other_data_dict:
            other_data_dict[ts] = {}
        if device_id not in other_data_dict[ts]:
            other_data_dict[ts][device_id] = {
                'device_id': device_id,
                'running': row['running'] or 0
            }
        other_data_dict[ts][device_id][row['metric_key']] = row['value']

    # 合并数据
    for ts in main_data_dict:
        if ts in other_data_dict:
            main_data_dict[ts]['other_devices'] = list(other_data_dict[ts].values())
        else:
            main_data_dict[ts]['other_devices'] = []

    df = pd.DataFrame(list(main_data_dict.values()))
    df = df.sort_values('ts_bucket').reset_index(drop=True)

    return df


@pytest.fixture
def sample_data_with_stopped_pump():
    """生成示例数据（包含停机泵）- 使用假数据用于单元测试"""
    timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1s')

    # 前50条运行，后50条停机
    running = [1] * 50 + [0] * 50

    data = pd.DataFrame({
        'ts_bucket': timestamps,
        'device_id': 105,
        'main_pipeline_flow_rate': np.random.uniform(100, 150, 100),
        'pump_active_power': [np.random.uniform(40, 50) if r == 1 else 0 for r in running],
        'pump_frequency': [np.random.uniform(45, 50) if r == 1 else 0 for r in running],
        'running': running,
        'other_devices': [[] for _ in range(100)]
    })
    return data


@pytest.fixture
def real_data_with_stopped_pump(db_connection):
    """加载真实数据（包含停机泵）- 用于集成测试

    从数据库加载设备3的数据，包含运行和停机状态
    时间范围：2025-10-23 10:00:00 ~ 2025-10-23 13:00:00（3小时，包含启停）
    """
    device_id = 3

    with db_connection.cursor() as cur:
        cur.execute("""
            SELECT
                fm.ts_bucket,
                fm.device_id,
                fm.value,
                dmc.metric_key,
                mvr.running
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            LEFT JOIN mv_device_running_1s mvr ON
                fm.device_id = mvr.device_id AND
                fm.ts_bucket = mvr.ts_bucket
            WHERE fm.device_id = %s
                AND fm.ts_bucket >= '2025-10-23 10:00:00+08'::timestamptz
                AND fm.ts_bucket < '2025-10-23 13:00:00+08'::timestamptz
                AND dmc.metric_key IN (
                    'main_pipeline_flow_rate',
                    'pump_active_power',
                    'pump_frequency'
                )
            ORDER BY fm.ts_bucket, dmc.metric_key
        """, (device_id,))

        rows = cur.fetchall()

    # 转换为 DataFrame
    data_dict = {}
    for row in rows:
        ts = row['ts_bucket']
        if ts not in data_dict:
            data_dict[ts] = {
                'ts_bucket': ts,
                'device_id': row['device_id'],
                'running': row['running'] or 0
            }
        data_dict[ts][row['metric_key']] = row['value']

    df = pd.DataFrame(list(data_dict.values()))
    df = df.sort_values('ts_bucket').reset_index(drop=True)
    df['other_devices'] = [[] for _ in range(len(df))]

    return df


@pytest.fixture
def sample_calculation_results():
    """生成示例计算结果 - 使用假数据用于单元测试"""
    timestamps = pd.date_range('2025-01-01 00:00:00', periods=100, freq='1s')
    results = pd.DataFrame({
        'ts_bucket': timestamps,
        'device_id': 105,
        'pump_flow_rate': np.random.uniform(50, 75, 100)
    })
    return results


@pytest.fixture
def real_calculation_results(db_connection):
    """加载真实计算结果 - 用于集成测试

    从数据库加载设备3的 pump_flow_rate 计算结果
    """
    device_id = 3

    with db_connection.cursor() as cur:
        cur.execute("""
            SELECT
                fm.ts_bucket,
                fm.device_id,
                fm.value as pump_flow_rate
            FROM fact_measurements fm
            JOIN dim_metric_config dmc ON fm.metric_id = dmc.id
            WHERE fm.device_id = %s
                AND dmc.metric_key = 'pump_flow_rate'
                AND fm.ts_bucket >= '2025-10-23 10:48:00+08'::timestamptz
                AND fm.ts_bucket < '2025-10-23 11:00:00+08'::timestamptz
            ORDER BY fm.ts_bucket
        """, (device_id,))

        rows = cur.fetchall()

    if not rows:
        raise ValueError(f"设备 {device_id} 没有找到 pump_flow_rate 计算结果")

    df = pd.DataFrame(rows)
    return df


@pytest.fixture
def mock_parameter_manager():
    """Mock ParameterManager"""
    manager = MagicMock()
    manager.get_parameters.return_value = {
        'alpha': 1.0,
        'beta': 1.0,
        'min_flow': 0.0,
        'max_flow': 500.0,
        'max_ratio': 1.1,
        'derivative_window': 5
    }
    return manager


@pytest.fixture
def mock_data_writer():
    """Mock DataWriter"""
    writer = MagicMock()
    writer.write.return_value = None
    writer.get_stats.return_value = {
        'total_records': 100,
        'total_batches': 1,
        'total_duration': 0.5,
        'avg_batch_size': 100,
        'avg_duration': 0.5
    }
    return writer


@pytest.fixture(autouse=True)
def reset_singletons():
    """每个测试后重置单例"""
    yield
    # 清理单例实例（如果需要）
    pass

