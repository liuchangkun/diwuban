# main_pipeline_inlet_pressure 实施计划

> **任务ID**: main_pipeline_inlet_pressure_plan_20251122  
> **创建时间**: 2025-11-22  
> **协议**: RIPER-5 计划模式  
> **状态**: 进行中

---

## 📋 实施方案

**选定方案**: 方案A（保守渐进式）

**实施步骤**:
1. ✅ 调度器集成（已完成 - main_pipeline_inlet_pressure 已在 METRIC_ORDER 第3位）
2. ⏳ 单元测试验证（各模块独立测试）
3. ⏳ 集成测试验证（全时间范围）
4. ⏳ 全量计算（完整时间范围）
5. ⏳ 数据质量分析和性能优化

---

## 🔍 调度器位置分析

### METRIC_ORDER 当前状态

```python
METRIC_ORDER = [
    "pump_flow_rate",                  # 1. 水泵流量（基础指标）
    "pump_inlet_pressure",             # 2. 水泵入口压力（基础指标）
    "main_pipeline_inlet_pressure",    # 3. 总管进口压力（基础指标，仅依赖pool_liquid_level）✅
    "pump_head",                       # 4. 水泵扬程（依赖 pump_inlet_pressure, main_pipeline_outlet_pressure, pump_flow_rate）
    "pump_efficiency",                 # 5. 水泵效率（依赖 pump_flow_rate, pump_head）
    "pump_speed",                      # 6. 水泵转速（基础指标）
    "pump_torque",                     # 7. 水泵扭矩（依赖 pump_active_power, pump_speed）
    "main_pipeline_outlet_pressure",   # 8. 总管出口压力（依赖 pump_outlet_pressure）
]
```

### 位置决策

**结论**: ✅ **main_pipeline_inlet_pressure 已在正确位置（第3位）**

**理由**:
1. **依赖关系正确**: 仅依赖 pool_liquid_level（原始测量数据，metric_id=5, device_id=8）
2. **层次划分正确**: 属于第1层计算指标（基础指标）
3. **顺序合理**: 在 pump_head 之前（pump_head 可能未来会依赖它）
4. **无需修改**: 调度器集成已完成

---

## 📝 步骤2：单元测试验证

### 测试目标

验证各模块的独立功能正确性，确保代码质量。

### 测试范围

#### 2.1 DataLoader 测试
- [ ] 测试从 device_id=8 加载 pool_liquid_level 数据
- [ ] 测试时间范围过滤
- [ ] 测试空数据处理
- [ ] 测试数据类型转换

#### 2.2 DataFilter 测试
- [ ] 测试 running=1 过滤
- [ ] 测试 running=NULL 保留（总管设备特殊处理）
- [ ] 测试空数据处理

#### 2.3 MethodSelector 测试
- [ ] 测试方法选择逻辑（method_b vs PIN_COEF_V1）
- [ ] 测试依赖检查（pool_liquid_level）
- [ ] 测试优先级排序

#### 2.4 Calculator 测试
- [ ] 测试 method_b 计算（静压法）
- [ ] 测试 PIN_COEF_V1 计算（多项式拟合法）
- [ ] 测试参数加载
- [ ] 测试异常处理

#### 2.5 Validator 测试
- [ ] 测试范围验证（0.05 ~ 0.50 MPa）
- [ ] 测试物理约束验证（P_in ≈ P_atm + ρ×g×h/1e6）
- [ ] 测试异常值检测（IQR方法）
- [ ] 测试 NaN/Inf 检测

#### 2.6 Pipeline 测试
- [ ] 测试完整流水线执行
- [ ] 测试错误传播
- [ ] 测试日志记录

### 测试执行方式

**方式1**: 创建单元测试文件（推荐）
- 文件路径: `tests/unit/calculation/metrics/test_main_pipeline_inlet_pressure.py`
- 使用 pytest 框架
- 覆盖所有模块

**方式2**: 手动验证（快速验证）
- 使用 Python REPL 或 Jupyter Notebook
- 逐模块验证功能
- 记录验证结果

### 预期结果

- ✅ 所有模块测试通过
- ✅ 代码覆盖率 ≥ 80%
- ✅ 无明显错误或警告

---

## 📝 步骤3：集成测试验证

### 测试目标

验证端到端流水线的正确性，使用全时间范围数据。

### 测试配置

**时间范围**: 全部时间（用户要求）
- 开始时间: 数据库中最早时间
- 结束时间: 数据库中最晚时间
- 预计数据量: ~83,609 条记录（pool_liquid_level）

**设备范围**: device_id=7（总管设备）

**指标**: main_pipeline_inlet_pressure (metric_id=61)

### 测试步骤

1. **准备阶段**
   - [ ] 确认数据库连接正常
   - [ ] 确认 calculation_parameters 表已填充
   - [ ] 确认 pool_liquid_level 数据存在

2. **执行阶段**
   - [ ] 运行完整流水线
   - [ ] 记录执行时间
   - [ ] 记录计算结果数量
   - [ ] 记录错误和警告

3. **验证阶段**
   - [ ] 检查计算结果数量是否合理
   - [ ] 检查计算结果范围是否合理（0.05 ~ 0.50 MPa）
   - [ ] 检查是否有异常值
   - [ ] 检查日志是否完整

### 预期结果

- ✅ 流水线执行成功
- ✅ 计算结果数量 > 0
- ✅ 计算结果范围合理
- ✅ 无严重错误

---

## 📝 步骤4：全量计算

### 计算目标

将计算结果写入数据库，完成指标填充。

### 计算配置

**时间范围**: 全部时间
**设备**: device_id=7
**指标**: metric_id=61
**写入表**: fact_measurements

### 执行步骤

1. **准备阶段**
   - [ ] 备份现有数据（如有）
   - [ ] 确认数据库写入权限
   - [ ] 确认存储空间充足

2. **执行阶段**
   - [ ] 运行调度器（仅 main_pipeline_inlet_pressure）
   - [ ] 监控执行进度
   - [ ] 记录执行时间
   - [ ] 记录写入数量

3. **验证阶段**
   - [ ] 检查写入数量是否正确
   - [ ] 检查数据完整性
   - [ ] 检查数据一致性

### 预期结果

- ✅ 数据写入成功
- ✅ 写入数量 > 0
- ✅ 数据完整性验证通过

---

## 📝 步骤5：数据质量分析

### 分析目标

评估计算结果的质量，识别潜在问题。

### 分析维度

1. **覆盖率分析**
   - [ ] 计算覆盖率（有效值 / 总记录数）
   - [ ] 识别缺失数据的时间段
   - [ ] 分析缺失原因

2. **数值分布分析**
   - [ ] 统计描述（min, max, mean, median, std）
   - [ ] 绘制直方图
   - [ ] 识别异常值

3. **物理一致性分析**
   - [ ] 验证 P_in ≈ P_atm + ρ×g×h/1e6
   - [ ] 计算偏差分布
   - [ ] 识别不一致的记录

4. **时间序列分析**
   - [ ] 绘制时间序列图
   - [ ] 识别突变点
   - [ ] 分析趋势

### 预期结果

- ✅ 覆盖率 ≥ 95%
- ✅ 数值分布合理
- ✅ 物理一致性良好
- ✅ 无明显异常

---

## 🔧 详细执行检查清单

### 检查清单1: 调度器集成验证

**目标**: 验证 main_pipeline_inlet_pressure 已正确集成到调度器

**检查项**:
- [x] METRIC_ORDER 包含 main_pipeline_inlet_pressure
- [x] 位置在第3位（pump_inlet_pressure 之后，pump_head 之前）
- [ ] 调度器能正确识别该指标
- [ ] 调度器能正确加载对应的 Pipeline 类

**验证方式**:
```python
# 1. 检查 METRIC_ORDER
from app.services.calculation.shared.scheduler import METRIC_ORDER
assert "main_pipeline_inlet_pressure" in METRIC_ORDER
assert METRIC_ORDER.index("main_pipeline_inlet_pressure") == 2  # 第3位（索引2）

# 2. 检查 Pipeline 导入
from app.services.calculation.metrics.main_pipeline_inlet_pressure import Pipeline
pipeline = Pipeline()
assert pipeline is not None
```

**预期结果**: 所有检查项通过

---

### 检查清单2: 单元测试执行

**目标**: 验证各模块功能正确性

**测试文件**: `tests/unit/calculation/metrics/test_main_pipeline_inlet_pressure.py`

**测试用例**:

#### 2.1 DataLoader 测试
```python
def test_data_loader_basic():
    """测试基本数据加载功能"""
    # 测试从 device_id=8 加载 pool_liquid_level
    # 测试时间范围过滤
    # 测试数据类型转换

def test_data_loader_empty():
    """测试空数据处理"""
    # 测试无数据时的行为

def test_data_loader_time_range():
    """测试时间范围过滤"""
    # 测试开始/结束时间过滤
```

#### 2.2 DataFilter 测试
```python
def test_data_filter_running():
    """测试 running 状态过滤"""
    # 测试 running=1 保留
    # 测试 running=NULL 保留（总管设备特殊处理）
    # 测试 running=0 过滤

def test_data_filter_empty():
    """测试空数据处理"""
```

#### 2.3 MethodSelector 测试
```python
def test_method_selector_priority():
    """测试方法优先级选择"""
    # 测试 method_b (priority=100) 优先于 PIN_COEF_V1 (priority=90)

def test_method_selector_dependencies():
    """测试依赖检查"""
    # 测试缺少 pool_liquid_level 时的行为
```

#### 2.4 Calculator 测试
```python
def test_calculator_method_b():
    """测试 method_b 计算"""
    # 公式: P_in = P_atm + ρ×g×h/1e6
    # 验证计算结果正确性

def test_calculator_pin_coef_v1():
    """测试 PIN_COEF_V1 计算"""
    # 公式: P_in = b0 + b1×h + b2×h² + b3×h³
    # 验证计算结果正确性

def test_calculator_params():
    """测试参数加载"""
    # 验证从 calculation_parameters 加载参数
```

#### 2.5 Validator 测试
```python
def test_validator_range():
    """测试范围验证"""
    # 验证 0.05 ~ 0.50 MPa 范围

def test_validator_physics():
    """测试物理约束验证"""
    # 验证 P_in ≈ P_atm + ρ×g×h/1e6

def test_validator_outliers():
    """测试异常值检测"""
    # 验证 IQR 方法
```

#### 2.6 Pipeline 测试
```python
def test_pipeline_end_to_end():
    """测试完整流水线"""
    # 测试 DataLoader → DataFilter → MethodSelector → Calculator → Validator
```

**执行方式**:
```bash
# 运行所有测试
pytest tests/unit/calculation/metrics/test_main_pipeline_inlet_pressure.py -v

# 运行单个测试
pytest tests/unit/calculation/metrics/test_main_pipeline_inlet_pressure.py::test_data_loader_basic -v

# 生成覆盖率报告
pytest tests/unit/calculation/metrics/test_main_pipeline_inlet_pressure.py --cov=app.services.calculation.metrics.main_pipeline_inlet_pressure --cov-report=html
```

**预期结果**:
- ✅ 所有测试通过
- ✅ 代码覆盖率 ≥ 80%
- ✅ 无错误或警告

---

### 检查清单3: 集成测试执行

**目标**: 验证端到端流水线（全时间范围）

**测试脚本**: 创建临时测试脚本或使用 Jupyter Notebook

**测试步骤**:

#### 3.1 准备阶段
```python
# 1. 导入模块
from app.services.calculation.metrics.main_pipeline_inlet_pressure import Pipeline
from app.services.calculation.shared.services import SharedServices
from datetime import datetime

# 2. 初始化服务
services = SharedServices()

# 3. 查询时间范围
sql = """
SELECT
    MIN(ts_bucket) as start_time,
    MAX(ts_bucket) as end_time,
    COUNT(*) as record_count
FROM fact_measurements
WHERE metric_id = 5  -- pool_liquid_level
  AND device_id = 8
"""
result = services.db.execute_query(sql)
print(f"时间范围: {result[0]['start_time']} ~ {result[0]['end_time']}")
print(f"记录数: {result[0]['record_count']}")
```

#### 3.2 执行阶段
```python
# 4. 运行流水线
pipeline = Pipeline()
start_time = result[0]['start_time']
end_time = result[0]['end_time']

import time
start = time.time()
result_df = pipeline.run(
    device_id=7,  # 总管设备
    start_time=start_time,
    end_time=end_time
)
elapsed = time.time() - start

print(f"执行时间: {elapsed:.2f} 秒")
print(f"结果数量: {len(result_df)}")
```

#### 3.3 验证阶段
```python
# 5. 检查结果
print("\n=== 结果统计 ===")
print(result_df['main_pipeline_inlet_pressure'].describe())

print("\n=== 有效性统计 ===")
print(f"有效值数量: {result_df['main_pipeline_inlet_pressure'].notna().sum()}")
print(f"无效值数量: {result_df['main_pipeline_inlet_pressure'].isna().sum()}")
print(f"覆盖率: {result_df['main_pipeline_inlet_pressure'].notna().sum() / len(result_df) * 100:.2f}%")

print("\n=== 范围检查 ===")
valid_range = (result_df['main_pipeline_inlet_pressure'] >= 0.05) & (result_df['main_pipeline_inlet_pressure'] <= 0.50)
print(f"范围内数量: {valid_range.sum()}")
print(f"范围外数量: {(~valid_range).sum()}")

print("\n=== 物理一致性检查 ===")
if 'pool_liquid_level' in result_df.columns:
    P_atm = 0.101325
    rho = 1000.0
    g = 9.81
    h = result_df['pool_liquid_level'].astype(float)
    expected_P = P_atm + rho * g * h / 1e6
    deviation = np.abs(result_df['main_pipeline_inlet_pressure'] - expected_P) / expected_P
    print(f"平均偏差: {deviation.mean():.2%}")
    print(f"最大偏差: {deviation.max():.2%}")
    print(f"偏差 ≤ 20% 的比例: {(deviation <= 0.20).sum() / len(deviation) * 100:.2f}%")
```

**预期结果**:
- ✅ 执行成功，无严重错误
- ✅ 结果数量 > 0
- ✅ 覆盖率 ≥ 95%
- ✅ 范围内数量占比 ≥ 95%
- ✅ 物理一致性良好（偏差 ≤ 20% 的比例 ≥ 95%）

---

### 检查清单4: 全量计算执行

**目标**: 将计算结果写入数据库

**执行方式**: 使用调度器

**执行步骤**:

#### 4.1 准备阶段
```python
# 1. 备份现有数据（如有）
sql_backup = """
CREATE TABLE IF NOT EXISTS fact_measurements_backup_main_pipeline_inlet_pressure AS
SELECT *
FROM fact_measurements
WHERE metric_id = 61  -- main_pipeline_inlet_pressure
  AND device_id = 7
"""
# 执行备份（可选）

# 2. 查询现有数据量
sql_check = """
SELECT COUNT(*) as count
FROM fact_measurements
WHERE metric_id = 61
  AND device_id = 7
"""
result = services.db.execute_query(sql_check)
print(f"现有数据量: {result[0]['count']}")
```

#### 4.2 执行阶段
```python
# 3. 运行调度器（仅 main_pipeline_inlet_pressure）
from app.services.calculation.shared.scheduler import Scheduler

scheduler = Scheduler()
start_time = datetime(2025, 10, 22, 0, 0, 0)  # 根据实际数据调整
end_time = datetime(2025, 10, 23, 0, 0, 0)    # 根据实际数据调整

import time
start = time.time()
scheduler.run(
    metrics=["main_pipeline_inlet_pressure"],
    start_time=start_time,
    end_time=end_time
)
elapsed = time.time() - start

print(f"执行时间: {elapsed:.2f} 秒")
```

#### 4.3 验证阶段
```python
# 4. 检查写入结果
sql_verify = """
SELECT
    COUNT(*) as total_count,
    COUNT(CASE WHEN value IS NOT NULL THEN 1 END) as valid_count,
    MIN(value) as min_value,
    MAX(value) as max_value,
    AVG(value) as avg_value,
    STDDEV(value) as std_value
FROM fact_measurements
WHERE metric_id = 61
  AND device_id = 7
  AND ts_bucket >= %s
  AND ts_bucket < %s
"""
result = services.db.execute_query(sql_verify, (start_time, end_time))
print("\n=== 写入结果统计 ===")
print(f"总记录数: {result[0]['total_count']}")
print(f"有效值数量: {result[0]['valid_count']}")
print(f"覆盖率: {result[0]['valid_count'] / result[0]['total_count'] * 100:.2f}%")
print(f"数值范围: [{result[0]['min_value']:.4f}, {result[0]['max_value']:.4f}]")
print(f"平均值: {result[0]['avg_value']:.4f}")
print(f"标准差: {result[0]['std_value']:.4f}")
```

**预期结果**:
- ✅ 调度器执行成功
- ✅ 写入数量 > 0
- ✅ 覆盖率 ≥ 95%
- ✅ 数值范围合理（0.05 ~ 0.50 MPa）

---

### 检查清单5: 数据质量分析

**目标**: 评估计算结果质量

**分析脚本**: 创建数据质量分析脚本

**分析步骤**:

#### 5.1 覆盖率分析
```python
sql_coverage = """
SELECT
    DATE(ts_bucket) as date,
    COUNT(*) as total_count,
    COUNT(CASE WHEN value IS NOT NULL THEN 1 END) as valid_count,
    COUNT(CASE WHEN value IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as coverage_rate
FROM fact_measurements
WHERE metric_id = 61
  AND device_id = 7
GROUP BY DATE(ts_bucket)
ORDER BY date
"""
coverage_df = pd.read_sql(sql_coverage, services.db.connection)

print("\n=== 覆盖率分析 ===")
print(f"平均覆盖率: {coverage_df['coverage_rate'].mean():.2f}%")
print(f"最低覆盖率: {coverage_df['coverage_rate'].min():.2f}%")
print(f"最高覆盖率: {coverage_df['coverage_rate'].max():.2f}%")

# 识别低覆盖率日期
low_coverage = coverage_df[coverage_df['coverage_rate'] < 95]
if not low_coverage.empty:
    print(f"\n低覆盖率日期（< 95%）:")
    print(low_coverage)
```

#### 5.2 数值分布分析
```python
sql_distribution = """
SELECT value
FROM fact_measurements
WHERE metric_id = 61
  AND device_id = 7
  AND value IS NOT NULL
"""
values_df = pd.read_sql(sql_distribution, services.db.connection)

print("\n=== 数值分布分析 ===")
print(values_df['value'].describe())

# 绘制直方图
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.hist(values_df['value'], bins=50, edgecolor='black')
plt.xlabel('main_pipeline_inlet_pressure (MPa)')
plt.ylabel('Frequency')
plt.title('main_pipeline_inlet_pressure Distribution')
plt.grid(True, alpha=0.3)
plt.savefig('main_pipeline_inlet_pressure_distribution.png')
print("直方图已保存: main_pipeline_inlet_pressure_distribution.png")
```

#### 5.3 物理一致性分析
```python
sql_physics = """
SELECT
    fm1.ts_bucket,
    fm1.value as main_pipeline_inlet_pressure,
    fm2.value as pool_liquid_level
FROM fact_measurements fm1
LEFT JOIN fact_measurements fm2
    ON fm1.ts_bucket = fm2.ts_bucket
    AND fm2.metric_id = 5  -- pool_liquid_level
    AND fm2.device_id = 8
WHERE fm1.metric_id = 61
  AND fm1.device_id = 7
  AND fm1.value IS NOT NULL
  AND fm2.value IS NOT NULL
"""
physics_df = pd.read_sql(sql_physics, services.db.connection)

# 计算物理一致性
P_atm = 0.101325
rho = 1000.0
g = 9.81
h = physics_df['pool_liquid_level'].astype(float)
expected_P = P_atm + rho * g * h / 1e6
deviation = np.abs(physics_df['main_pipeline_inlet_pressure'] - expected_P) / expected_P

print("\n=== 物理一致性分析 ===")
print(f"平均偏差: {deviation.mean():.2%}")
print(f"中位数偏差: {deviation.median():.2%}")
print(f"最大偏差: {deviation.max():.2%}")
print(f"偏差 ≤ 10% 的比例: {(deviation <= 0.10).sum() / len(deviation) * 100:.2f}%")
print(f"偏差 ≤ 20% 的比例: {(deviation <= 0.20).sum() / len(deviation) * 100:.2f}%")

# 识别不一致记录
inconsistent = physics_df[deviation > 0.20]
if not inconsistent.empty:
    print(f"\n不一致记录数量: {len(inconsistent)}")
    print(inconsistent.head(10))
```

#### 5.4 时间序列分析
```python
sql_timeseries = """
SELECT
    ts_bucket,
    value as main_pipeline_inlet_pressure
FROM fact_measurements
WHERE metric_id = 61
  AND device_id = 7
  AND value IS NOT NULL
ORDER BY ts_bucket
"""
timeseries_df = pd.read_sql(sql_timeseries, services.db.connection)

print("\n=== 时间序列分析 ===")
print(f"时间范围: {timeseries_df['ts_bucket'].min()} ~ {timeseries_df['ts_bucket'].max()}")
print(f"数据点数量: {len(timeseries_df)}")

# 绘制时间序列图
plt.figure(figsize=(15, 6))
plt.plot(timeseries_df['ts_bucket'], timeseries_df['main_pipeline_inlet_pressure'], linewidth=0.5)
plt.xlabel('Time')
plt.ylabel('main_pipeline_inlet_pressure (MPa)')
plt.title('main_pipeline_inlet_pressure Time Series')
plt.grid(True, alpha=0.3)
plt.savefig('main_pipeline_inlet_pressure_timeseries.png')
print("时间序列图已保存: main_pipeline_inlet_pressure_timeseries.png")
```

**预期结果**:
- ✅ 平均覆盖率 ≥ 95%
- ✅ 数值分布合理（集中在 0.1 ~ 0.3 MPa）
- ✅ 物理一致性良好（偏差 ≤ 20% 的比例 ≥ 95%）
- ✅ 时间序列无明显异常

---

**计划创建时间**: 2025-11-22

