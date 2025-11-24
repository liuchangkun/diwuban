# 真实数据流程说明

## 📋 run-all 命令完整流程

### 1. 命令执行
```bash
python -m app.cli.main run-all configs/data_mapping.v2.json
```

### 2. 流程步骤（由 `configs/merge.yaml` 控制）

#### 阶段1: prepare-dim（维度表准备）
- **执行时机**: merge-fact 之前
- **功能**:
  - 备份手动配置表
  - 清空依赖表
  - 重建维度表（dim_stations, dim_devices, dim_metric_config）
  - 恢复手动配置表
  - 重建基础配置表（calculation_method_registry, calculation_parameters等）

#### 阶段2: create-staging（创建临时表）
- **功能**: 创建 staging_raw 和 staging_rejects 表

#### 阶段3: ingest-copy（数据导入）
- **功能**: 从 CSV 文件导入数据到 staging_raw 表
- **数据源**: `configs/data_mapping.v2.json` 中配置的 CSV 文件路径

#### 阶段4: merge-fact（数据合并）
- **功能**: 将 staging_raw 数据合并到 fact_measurements 表
- **处理**:
  - 时区转换（本地时区 → UTC）
  - 秒级对齐
  - 去重（同一时间戳只保留一条）
  - UPSERT（ON CONFLICT 更新）

#### 阶段5: prepare-dim-stage2（规则表生成）
- **执行时机**: merge-fact 之后
- **功能**:
  - 清空规则表
  - 生成规则表（metric_rule_auto_baseline, metric_quality_rules, device_running_thresholds）

#### 阶段6: device-running（运行状态计算）
- **功能**: 刷新 mv_device_running_1s 物化视图
- **依赖**: device_running_thresholds 表（阈值配置）

#### 阶段7: calculation（缺失指标计算）⭐
- **开关**: `enable_calculation: true`（在 merge.yaml 中）
- **配置**: `calculation_cfg.metrics`（指标列表）
- **功能**: 计算缺失的指标（如 pump_flow_rate）
- **流程**:
  1. 从 fact_measurements 读取依赖数据
  2. 执行计算（使用 CalculationOrchestrator）
  3. 写入结果到 fact_measurements（quality_status=1）

---

## 🔍 真实数据库状态

### 当前数据库（pump_station_optimization）

**泵站数据**:
- ID=1: 二期供水泵房

**设备数据**:
- ID=1-6: 二期供水泵房1#泵 ~ 6#泵（类型=pump）
- ID=7: 二期供水泵房总管（类型=main_pipeline）
- ID=8: 其他（类型=other）

**测量数据**:
- ⚠️ 最近7天没有数据
- 需要通过 run-all 命令导入 CSV 数据

**物化视图**:
- ⚠️ mv_device_running_1s 不存在
- 需要通过 run-all 命令创建和刷新

---

## 🧪 测试数据准备策略

### 方案1: 使用 run-all 导入真实数据（推荐）⭐

**步骤**:
1. 准备 CSV 数据文件（放在 `data/` 目录）
2. 配置 `configs/data_mapping.v2.json`（指定 CSV 文件路径）
3. 执行 `python -m app.cli.main run-all configs/data_mapping.v2.json`
4. 数据自动导入到 fact_measurements 表
5. 物化视图自动刷新

**优点**:
- ✅ 使用真实的数据导入流程
- ✅ 自动处理时区、对齐、去重
- ✅ 自动刷新物化视图
- ✅ 自动生成规则表

**缺点**:
- ⏳ 需要准备 CSV 数据文件

### 方案2: 直接查询现有数据（如果有）

**步骤**:
1. 检查 fact_measurements 表是否有历史数据
2. 如果有，直接使用历史数据进行测试
3. 如果没有，使用方案1

**检查命令**:
```bash
python tests/fixtures/check_real_data.py
```

---

## 📝 测试配置更新

### conftest.py 更新建议

```python
import pytest
from datetime import datetime, timedelta
from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from pathlib import Path

@pytest.fixture(scope="session")
def real_db_connection():
    """真实数据库连接"""
    settings = load_settings(Path("configs"))
    init_database(settings)
    with get_connection() as conn:
        yield conn

@pytest.fixture(scope="session")
def real_test_config(real_db_connection):
    """从真实数据库获取测试配置"""
    with real_db_connection.cursor() as cur:
        # 查找有完整数据的设备
        cur.execute("""
            SELECT device_id, MIN(ts_bucket), MAX(ts_bucket)
            FROM fact_measurements
            WHERE device_id IN (1, 2, 3, 4, 5, 6)
            GROUP BY device_id
            HAVING COUNT(*) > 1000
            ORDER BY COUNT(*) DESC
            LIMIT 1
        """)
        result = cur.fetchone()
        
        if result:
            device_id, min_ts, max_ts = result
            # 使用最近1小时的数据
            end_time = max_ts
            start_time = max_ts - timedelta(hours=1)
            
            return {
                'device_id': device_id,
                'start_time': start_time,
                'end_time': end_time,
                'station_id': 1
            }
        else:
            # 如果没有数据，返回默认配置
            return {
                'device_id': 1,
                'start_time': datetime.now() - timedelta(hours=1),
                'end_time': datetime.now(),
                'station_id': 1
            }
```

---

## 🚀 下一步行动

### ⚠️ 当前问题

run-all 命令失败，原因：
- 元数据表数据不完整（期望112条，实际560条）
- 需要执行迁移脚本 `100_migrate_metadata_to_three_tier.sql`
- 但迁移脚本有编码和语法问题

### 🎯 推荐方案：使用简化的测试流程

**不依赖 run-all 命令，直接使用 Python 代码准备测试数据**

#### 步骤1: 检查数据库状态
```bash
python tests/fixtures/check_real_data.py
```

#### 步骤2: 如果数据库为空，使用 Python 代码插入测试数据
```python
# tests/fixtures/insert_test_data.py
# 直接使用 psycopg 插入测试数据，绕过 run-all 流程
```

#### 步骤3: 创建 mv_device_running_1s 物化视图
```python
# tests/fixtures/create_mv_device_running.py
# 使用 Python 代码创建物化视图
```

#### 步骤4: 更新 conftest.py 使用真实数据
```python
# 从数据库加载真实数据，而不是生成假数据
```

---

**优势**:
- ✅ 绕过 run-all 命令的复杂性
- ✅ 直接控制测试数据
- ✅ 更快的测试准备速度
- ✅ 不依赖 CSV 文件和迁移脚本

