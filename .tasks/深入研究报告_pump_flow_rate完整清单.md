# 深入研究报告：pump_flow_rate 完整清单

**研究时间**：2025-11-11
**研究目的**：为重构做准备，识别所有需要删除的代码、脚本、存储过程

---

## 📋 研究目标

根据用户需求：
1. ✅ 识别所有 `pump_flow_rate` 相关的代码、脚本、存储过程
2. ✅ 识别可以复用的数据库表
3. ✅ 为新架构设计做好准备（指标独立的过滤、计算、验证）

---

## 🗑️ 需要删除的内容清单

### 1. Python代码文件

#### 1.1 计算器函数（app/services/calculation/calculators.py）

**需要删除的函数**：
- `calculate_pump_flow_rate_method_a` (行48-101)
- `calculate_pump_flow_rate_method_b` (行158-187)
- `calculate_pump_flow_rate_method_c` (行190-211)
- `calculate_pump_flow_rate_method_d` (行214-242)
- `calculate_pump_flow_rate_method_e` (行245-273)
- `calculate_pump_flow_rate_method_f` (行276-310)

**CALCULATOR_REGISTRY 中需要删除的条目**：
```python
# 行1114-1119
'pump_flow_rate_method_a': calculate_pump_flow_rate_method_a,
'pump_flow_rate_method_b': calculate_pump_flow_rate_method_b,
'pump_flow_rate_method_c': calculate_pump_flow_rate_method_c,
'pump_flow_rate_method_d': calculate_pump_flow_rate_method_d,
'pump_flow_rate_method_e': calculate_pump_flow_rate_method_e,
'pump_flow_rate_method_f': calculate_pump_flow_rate_method_f,
```

#### 1.2 辅助函数（app/services/calculation/orchestrator.py）

**需要删除的函数**：
- `_prepare_flow_rate_share` (行1635-1787)
  - 这是权重计算的核心函数
  - 包含全局过滤逻辑
  - 包含 weight_totals 计算逻辑

**需要删除的调用**：
- 在 `calculate_metric` 方法中调用 `_prepare_flow_rate_share` 的代码

---

### 2. 数据库脚本

#### 2.1 方法注册脚本（scripts/sql/calculation/init_methods.sql）

**需要删除的INSERT语句**：
- 行17-38：pump_flow_rate_method_a
- 行40-61：pump_flow_rate_method_b
- 行63-84：pump_flow_rate_method_c
- 行86-107：pump_flow_rate_method_d
- 行109-130：pump_flow_rate_method_e
- 行132-153：pump_flow_rate_method_f（如果存在）

#### 2.2 参数配置脚本（scripts/sql/calculation/init_params.sql）

**需要删除的INSERT语句**：
- 行17-26：alpha 参数
- 行28-37：beta 参数
- 行39-48：f_thr 参数
- 行50-59：p_thr 参数

#### 2.3 修复脚本

**需要删除的文件**：
- `migrations/fix_pump_flow_rate_method_e.sql`
- `docs/缺失计算修复/03-修复方案/优先级3.1-pump_flow_rate条件字段.md`

#### 2.4 自适应脚本（scripts/sql/adaptive/01_metric_config_related.sql）

**需要删除的部分**：
- 行41-54：pump_flow_rate_method_a 的自适应注册

---

### 3. 测试文件

#### 3.1 单元测试（tests/unit/services/calculation/test_calculators_functions.py）

**需要删除的测试类**：
- `TestPumpFlowRateCalculations` (行47-200+)
  - `test_method_a_with_share`
  - `test_method_a_without_share`
  - `test_method_b_normal_case`
  - `test_method_c_normal_case`
  - `test_method_d_normal_case`
  - `test_method_d_with_low_power`
  - `test_method_e_normal_case`
  - `test_method_f_normal_case`

---

### 4. 文档文件

**需要删除或更新的文档**：
- `docs/缺失计算修复/06-技术参考/现有计算方法清单.md` (pump_flow_rate部分)
- `docs/缺失计算修复/03-修复方案/优先级3.1-pump_flow_rate条件字段.md`
- `docs/缺失计算修复/03-修复方案/优先级3.3-pump_efficiency备选方法.md` (部分引用)
- `docs/缺失计算修复1/19-综合修复报告-深度分析任务.md` (pump_flow_rate部分)
- `docs/_archive/reports/测试用例详细设计-模块2-缺失指标计算-深度补充.md` (pump_flow_rate部分)

---

### 5. 配置文件

#### 5.1 合并配置（configs/merge.yaml）

**需要更新的部分**：
- 行15：移除 `pump_flow_rate` 从 metrics 列表

#### 5.2 计算配置（configs/compute.example.yaml）

**需要更新的部分**：
- 行17：移除 `pump_flow_rate` 从 metrics 列表

---

### 6. 数据库表数据

#### 6.1 calculation_method_registry 表

**需要删除的记录**：
```sql
DELETE FROM calculation_method_registry
WHERE method_id IN (
    'pump_flow_rate_method_a',
    'pump_flow_rate_method_b',
    'pump_flow_rate_method_c',
    'pump_flow_rate_method_d',
    'pump_flow_rate_method_e',
    'pump_flow_rate_method_f'
);
```

#### 6.2 calculation_parameters 表

**需要删除的记录**：
```sql
DELETE FROM calculation_parameters
WHERE metric_key = 'pump_flow_rate';
```

#### 6.3 calculation_validation_config 表

**需要删除的记录**：
```sql
DELETE FROM calculation_validation_config
WHERE metric_key = 'pump_flow_rate';
```

---

## ✅ 可以复用的数据库表

### 1. 核心配置表（完全复用）

| 表名 | 用途 | 复用方式 |
|------|------|---------|
| `calculation_method_registry` | 方法注册表 | ✅ 保留表结构，删除pump_flow_rate数据，添加新方法 |
| `calculation_parameters` | 参数配置表 | ✅ 保留表结构，删除pump_flow_rate数据，添加新参数 |
| `calculation_validation_config` | 验证配置表 | ✅ 保留表结构，删除pump_flow_rate数据，添加新验证规则 |
| `dim_metric_config` | 指标配置表 | ✅ 保留pump_flow_rate记录，只修改元数据 |

### 2. 数据存储表（完全复用）

| 表名 | 用途 | 复用方式 |
|------|------|---------|
| `fact_measurements` | 测量数据表 | ✅ 完全复用，新计算结果写入此表 |
| `mv_device_running_1s` | 设备运行状态表 | ✅ 完全复用，但不作为全局过滤条件 |
| `device_rated_params` | 设备额定参数表 | ✅ 完全复用，提供额定参数 |

### 3. 辅助表（完全复用）

| 表名 | 用途 | 复用方式 |
|------|------|---------|
| `dim_stations` | 泵站维度表 | ✅ 完全复用 |
| `dim_devices` | 设备维度表 | ✅ 完全复用 |
| `device_running_thresholds` | 运行阈值表 | ✅ 完全复用 |

---

## 📊 统计总结

### 需要删除的内容统计

| 类型 | 数量 | 详情 |
|------|------|------|
| Python函数 | 7个 | 6个计算函数 + 1个辅助函数 |
| SQL脚本 | 10+个 | 方法注册、参数配置、修复脚本 |
| 测试用例 | 8+个 | 单元测试 |
| 文档文件 | 5+个 | 技术文档、修复方案 |
| 数据库记录 | 30+条 | 方法注册、参数、验证规则 |

### 可以复用的表统计

| 类型 | 数量 | 复用率 |
|------|------|--------|
| 核心配置表 | 4个 | 100% |
| 数据存储表 | 3个 | 100% |
| 辅助表 | 3个 | 100% |
| **总计** | **10个** | **100%** |

---

## 🔧 可以改造的表结构

### 1. dim_metric_config 表扩展建议

**当前结构**：
```sql
CREATE TABLE dim_metric_config (
    id              BIGSERIAL PRIMARY KEY,
    metric_key      TEXT NOT NULL UNIQUE,
    metric_name_cn  TEXT NOT NULL,
    metric_name_en  TEXT,
    unit            TEXT,
    data_type       TEXT NOT NULL DEFAULT 'float',
    is_cumulative   BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**建议扩展**（支持指标独立过滤）：
```sql
ALTER TABLE dim_metric_config
ADD COLUMN requires_running_state BOOLEAN DEFAULT TRUE,
ADD COLUMN min_frequency NUMERIC,
ADD COLUMN min_power NUMERIC,
ADD COLUMN min_flow NUMERIC,
ADD COLUMN custom_filter_sql TEXT,
ADD COLUMN fallback_strategy TEXT DEFAULT 'skip',
ADD COLUMN allow_low_quality_dependencies BOOLEAN DEFAULT FALSE,
ADD COLUMN max_dependency_quality SMALLINT DEFAULT 1;
```

**字段说明**：
- `requires_running_state`: 是否需要设备运行状态过滤
- `min_frequency/min_power/min_flow`: 指标特定的最小阈值
- `custom_filter_sql`: 自定义过滤SQL（高级用法）
- `fallback_strategy`: 失败时的降级策略（'skip', 'use_last_valid', 'use_default'）
- `allow_low_quality_dependencies`: 是否允许使用低质量依赖
- `max_dependency_quality`: 允许的最大依赖质量状态（0=GOOD, 1=SUSPECT, 2=BAD）

---

### 2. calculation_method_registry 表扩展建议

**当前结构**：
```sql
CREATE TABLE calculation_method_registry (
    method_id           TEXT PRIMARY KEY,
    metric_key          TEXT NOT NULL,
    method_name         TEXT NOT NULL,
    method_code         TEXT NOT NULL,
    priority            INTEGER NOT NULL DEFAULT 100,
    dependencies        TEXT[] NOT NULL DEFAULT '{}',
    conditions          JSONB,
    accuracy_level      TEXT NOT NULL DEFAULT 'medium',
    is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    allowed_device_types TEXT[] NOT NULL DEFAULT '{}'
);
```

**建议扩展**（支持方法独立配置）：
```sql
ALTER TABLE calculation_method_registry
ADD COLUMN filter_config JSONB,
ADD COLUMN validation_config JSONB,
ADD COLUMN quality_impact JSONB;
```

**字段说明**：
- `filter_config`: 方法特定的过滤配置
  ```json
  {
    "requires_running": true,
    "min_frequency": 3.0,
    "min_power": 0.5,
    "custom_filters": ["freq > 0", "power > 0"]
  }
  ```
- `validation_config`: 方法特定的验证配置
  ```json
  {
    "range": {"min": 0, "max": 10000},
    "physics_checks": ["energy_conservation"],
    "tolerance": 0.15
  }
  ```
- `quality_impact`: 质量影响配置
  ```json
  {
    "own_quality_threshold": 0.8,
    "dependency_quality_threshold": 0.6,
    "quality_degradation_factor": 0.5
  }
  ```

---

### 3. 新表建议：metric_calculation_log

**用途**：记录每次计算的详细日志，支持审计和调试

**表结构**：
```sql
CREATE TABLE metric_calculation_log (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              TEXT NOT NULL,
    station_id          BIGINT NOT NULL,
    device_id           BIGINT NOT NULL,
    metric_key          TEXT NOT NULL,
    method_id           TEXT,
    ts_start            TIMESTAMPTZ NOT NULL,
    ts_end              TIMESTAMPTZ NOT NULL,

    -- 执行状态
    status              TEXT NOT NULL,  -- 'SUCCESS', 'FAILED', 'SKIPPED'
    failure_reason      TEXT,

    -- 数据统计
    total_points        INTEGER,
    valid_points        INTEGER,
    filtered_points     INTEGER,

    -- 过滤详情
    filter_applied      JSONB,
    filter_stats        JSONB,

    -- 计算详情
    calculation_params  JSONB,
    calculation_stats   JSONB,

    -- 验证详情
    validation_results  JSONB,
    quality_status      SMALLINT,
    quality_codes       TEXT[],

    -- 性能指标
    duration_ms         INTEGER,
    memory_mb           NUMERIC,

    -- 时间戳
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 索引
    INDEX idx_mcl_run_id (run_id),
    INDEX idx_mcl_device_metric (device_id, metric_key),
    INDEX idx_mcl_status (status),
    INDEX idx_mcl_created_at (created_at)
);
```

---

## 📝 新架构设计要点

### 1. 指标独立的数据获取

**设计原则**：
- ✅ 每个指标独立决定需要加载哪些数据
- ✅ 每个指标独立决定过滤条件
- ✅ 支持指标级别的缓存

**实现方式**：
```python
class MetricDataLoader:
    def load_data_for_metric(
        self,
        metric_key: str,
        device_id: int,
        time_window: Tuple[datetime, datetime],
        filter_config: Dict[str, Any]
    ) -> Dict[str, np.ndarray]:
        """为特定指标加载数据"""

        # 1. 从 dim_metric_config 读取指标配置
        metric_config = self.get_metric_config(metric_key)

        # 2. 构建过滤条件
        filters = self._build_filters(metric_config, filter_config)

        # 3. 加载数据
        data = self._load_from_database(
            device_id=device_id,
            time_window=time_window,
            filters=filters
        )

        return data
```

---

### 2. 指标独立的分批计算

**设计原则**：
- ✅ 每个指标独立决定批量大小
- ✅ 每个指标独立决定并发策略
- ✅ 支持指标级别的性能监控

**实现方式**：
```python
class MetricBatchCalculator:
    def calculate_in_batches(
        self,
        metric_key: str,
        device_ids: List[int],
        time_window: Tuple[datetime, datetime],
        batch_config: Dict[str, Any]
    ) -> List[MetricResult]:
        """分批计算指标"""

        # 1. 确定批量大小
        batch_size = self._determine_batch_size(metric_key, batch_config)

        # 2. 分批处理
        results = []
        for batch in self._create_batches(device_ids, batch_size):
            batch_results = self._calculate_batch(
                metric_key=metric_key,
                device_ids=batch,
                time_window=time_window
            )
            results.extend(batch_results)

        return results
```

---

### 3. 指标独立的计算方法选择

**设计原则**：
- ✅ 每个指标独立选择计算方法
- ✅ 每个指标独立决定降级策略
- ✅ 支持方法级别的A/B测试

**实现方式**：
```python
class MetricMethodSelector:
    def select_method(
        self,
        metric_key: str,
        device_id: int,
        available_data: Dict[str, np.ndarray],
        context: Dict[str, Any]
    ) -> Optional[MethodDescriptor]:
        """为指标选择最佳计算方法"""

        # 1. 获取所有可用方法
        methods = self._get_available_methods(metric_key, device_id)

        # 2. 按优先级排序
        methods = sorted(methods, key=lambda m: m.priority, reverse=True)

        # 3. 逐个检查方法可用性
        for method in methods:
            if self._check_method_availability(method, available_data, context):
                return method

        return None
```

---

### 4. 指标独立的计算公式

**设计原则**：
- ✅ 每个指标的计算公式独立实现
- ✅ 每个公式独立验证
- ✅ 支持公式版本管理

**实现方式**：
```python
class MetricCalculator:
    def calculate(
        self,
        metric_key: str,
        method_id: str,
        data: Dict[str, np.ndarray],
        params: Dict[str, float]
    ) -> np.ndarray:
        """执行指标计算"""

        # 1. 获取计算函数
        calc_func = self._get_calculator_function(metric_key, method_id)

        # 2. 执行计算
        result = calc_func(data, params)

        # 3. 记录计算日志
        self._log_calculation(metric_key, method_id, data, params, result)

        return result
```

---

### 5. 指标独立的计算参数

**设计原则**：
- ✅ 每个指标独立管理参数
- ✅ 支持参数优化
- ✅ 支持参数版本控制

**实现方式**：
```python
class MetricParameterManager:
    def load_parameters(
        self,
        metric_key: str,
        method_id: str,
        device_id: int
    ) -> Dict[str, float]:
        """加载指标计算参数"""

        # 1. 按优先级加载参数（6层优先级）
        params = self._load_with_priority(
            metric_key=metric_key,
            method_id=method_id,
            device_id=device_id
        )

        # 2. 验证参数范围
        params = self._validate_parameters(params)

        return params
```

---

### 6. 指标独立的计算结果验证

**设计原则**：
- ✅ 每个指标独立验证规则
- ✅ 每个指标独立质量评估
- ✅ 支持多层验证

**实现方式**：
```python
class MetricValidator:
    def validate(
        self,
        metric_key: str,
        values: np.ndarray,
        context: Dict[str, Any]
    ) -> ValidationResult:
        """验证指标计算结果"""

        # 1. 加载验证规则
        rules = self._load_validation_rules(metric_key)

        # 2. 执行验证
        validation_result = self._execute_validation(values, rules, context)

        # 3. 计算质量状态
        quality_status = self._calculate_quality_status(validation_result)

        return ValidationResult(
            is_valid=validation_result.is_valid,
            quality_status=quality_status,
            errors=validation_result.errors,
            warnings=validation_result.warnings
        )
```

---

### 7. 指标独立的计算结果优化

**设计原则**：
- ✅ 每个指标独立优化策略
- ✅ 支持异常值处理
- ✅ 支持数据平滑

**实现方式**：
```python
class MetricOptimizer:
    def optimize(
        self,
        metric_key: str,
        values: np.ndarray,
        optimization_config: Dict[str, Any]
    ) -> np.ndarray:
        """优化指标计算结果"""

        # 1. 异常值处理
        values = self._handle_outliers(values, optimization_config)

        # 2. 数据平滑
        values = self._smooth_data(values, optimization_config)

        # 3. 边界处理
        values = self._handle_boundaries(values, optimization_config)

        return values
```

---

### 8. 指标独立的计算结果写入

**设计原则**：
- ✅ 每个指标独立写入策略
- ✅ 支持批量写入
- ✅ 支持事务管理

**实现方式**：
```python
class MetricWriter:
    def write_results(
        self,
        metric_key: str,
        results: List[MetricResult],
        write_config: Dict[str, Any]
    ) -> WriteResult:
        """写入指标计算结果"""

        # 1. 准备写入数据
        records = self._prepare_records(results)

        # 2. 批量写入
        write_result = self._batch_write(
            records=records,
            batch_size=write_config.get('batch_size', 10000)
        )

        # 3. 记录写入日志
        self._log_write(metric_key, write_result)

        return write_result
```

---

### 9. 完整的日志输出

**设计原则**：
- ✅ 每个阶段独立日志
- ✅ 结构化日志格式
- ✅ 支持日志级别控制

**实现方式**：
```python
class MetricCalculationLogger:
    def log_calculation_start(self, metric_key: str, context: Dict):
        """记录计算开始"""
        logger.info(
            f"[计算-开始] [指标: {metric_key}]",
            extra={
                "metric_key": metric_key,
                "device_id": context.get('device_id'),
                "time_window": context.get('time_window'),
                "run_id": context.get('run_id')
            }
        )

    def log_data_loading(self, metric_key: str, stats: Dict):
        """记录数据加载"""
        logger.info(
            f"[数据加载] [指标: {metric_key}]",
            extra={
                "metric_key": metric_key,
                "total_points": stats.get('total_points'),
                "filtered_points": stats.get('filtered_points'),
                "duration_ms": stats.get('duration_ms')
            }
        )

    def log_method_selection(self, metric_key: str, method_id: str):
        """记录方法选择"""
        logger.info(
            f"[方法选择] [指标: {metric_key}] [方法: {method_id}]",
            extra={
                "metric_key": metric_key,
                "method_id": method_id
            }
        )

    def log_calculation_complete(self, metric_key: str, result: MetricResult):
        """记录计算完成"""
        logger.info(
            f"[计算-完成] [指标: {metric_key}]",
            extra={
                "metric_key": metric_key,
                "status": result.status,
                "valid_points": result.valid_points,
                "quality_status": result.quality_status,
                "duration_ms": result.duration_ms
            }
        )

    def log_validation_result(self, metric_key: str, validation: ValidationResult):
        """记录验证结果"""
        logger.info(
            f"[验证结果] [指标: {metric_key}]",
            extra={
                "metric_key": metric_key,
                "is_valid": validation.is_valid,
                "quality_status": validation.quality_status,
                "errors": validation.errors,
                "warnings": validation.warnings
            }
        )
```

---

**下一步**：创建详细的删除脚本和新架构实现计划

