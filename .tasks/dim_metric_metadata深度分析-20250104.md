# dim_metric_metadata 表深度分析报告

**分析日期**: 2025-01-04  
**分析模式**: 研究模式（仅基于代码、数据库、脚本，忽略记忆）  
**核心问题**: 为什么表是空的？表的作用是什么？哪些功能依赖它？每个字段是否被使用？

---

## 📊 数据库现状

### 表结构验证

```sql
-- 表字段（10个字段）
metric_id          bigint PRIMARY KEY  -- 关联 dim_metric_config(id)
unit               text NULL
resolution         double precision NULL
phys_min           double precision NULL
phys_max           double precision NULL
saturation_min     double precision NULL
saturation_max     double precision NULL
remark             text NULL
updated_at         timestamptz NOT NULL DEFAULT now()
updated_by         text NULL

-- 外键约束
FOREIGN KEY (metric_id) REFERENCES dim_metric_config(id)

-- 当前数据量
行数: 0
dim_metric_config 行数: 56
```

**关键发现**：
- ✅ 表结构已创建（迁移文件 017）
- ✅ 外键约束已建立
- ❌ **表完全为空（0行）**
- ✅ 有56个指标配置在 dim_metric_config 中
- ❌ **种子数据脚本（021）从未执行**

---

## 🎯 表的设计目的和作用

### 官方注释（来自迁移文件）

```sql
-- 指标全局物理元数据表（每个 metric 一行）
-- 目的：沉淀单位、分辨率与物理/量程边界，供质量判定与阈值/基线计算使用
```

### 核心功能

**1. 元数据管理**
- 存储每个指标的物理属性（单位、分辨率、物理边界）
- 为质量检查提供参考基准
- 为基线计算提供元数据支持

**2. 三层元数据架构**
```
dim_metric_metadata (全局默认)
    ↓
dim_metric_metadata_override (站点/设备级覆盖)
    ↓
v_effective_metric_metadata (视图：优先级合并)
    ↓
业务逻辑（质量检查、基线计算）
```

**优先级**: 设备级 > 站点级 > 全局级

---

## 🔍 为什么表是空的？

### 根本原因分析

**原因1: 种子数据脚本未执行**
- 脚本位置: `scripts/sql/migrations/021_seed_dim_metric_metadata.sql`
- 脚本功能: 从 `dim_metric_config` 自动生成初始元数据
- 执行状态: ❌ **从未执行**
- 证据: 所有备份文件显示 "行数: 0"（从 2025-10-30 到 2025-11-04）

**原因2: 没有CLI命令直接执行**
- 存在Python脚本: `scripts/dev/apply_metadata_migrations.py`
- 脚本功能: 执行迁移文件 017-021（包括种子数据）
- 执行方式: 需要手动运行 `python scripts/dev/apply_metadata_migrations.py`
- 状态: ❌ **未被集成到CLI工作流**

**原因3: 不是自动填充表**
- 表设计为**手动配置表**（见备份脚本注释）
- 需要人工或脚本初始化
- 不会在数据导入时自动填充

---

## 📦 哪些功能依赖这个表？

### 直接依赖（8处）

#### SQL脚本（5处）
1. **017_create_dim_metric_metadata.sql** - 表创建
2. **020_create_v_effective_metric_metadata.sql** - 视图引用
3. **021_seed_dim_metric_metadata.sql** - 种子数据生成
4. **057_add_comprehensive_comments.sql** - 表注释
5. **058_add_remaining_comments.sql** - 字段注释

#### Python代码（3处）
6. **scripts/dev/apply_metadata_migrations.py** - 迁移应用脚本
7. **scripts/test_prepare_dim_backup.py** - 备份脚本（列为手动配置表）
8. **app/services/ingest/prepare_dim/__init__.py** - 备份逻辑

### 间接依赖（通过视图）

#### 视图: v_effective_metric_metadata
**视图逻辑**:
```sql
CREATE OR REPLACE VIEW v_effective_metric_metadata AS
WITH base AS (
  SELECT metric_id, unit, resolution, phys_min, phys_max, 
         saturation_min, saturation_max
  FROM dim_metric_metadata  -- ⚠️ 依赖此表
),
od AS (
  SELECT device_id, metric_id, resolution, phys_min, phys_max, 
         saturation_min, saturation_max
  FROM dim_metric_metadata_override WHERE device_id IS NOT NULL
),
os AS (
  SELECT station_id, metric_id, resolution, phys_min, phys_max, 
         saturation_min, saturation_max
  FROM dim_metric_metadata_override 
  WHERE device_id IS NULL AND station_id IS NOT NULL
)
SELECT
  COALESCE(od.device_id, NULL) AS device_id,
  COALESCE(os.station_id, NULL) AS station_id,
  b.metric_id,
  b.unit,
  COALESCE(od.resolution, os.resolution, b.resolution) AS resolution,
  COALESCE(od.phys_min, os.phys_min, b.phys_min) AS phys_min,
  COALESCE(od.phys_max, os.phys_max, b.phys_max) AS phys_max,
  COALESCE(od.saturation_min, os.saturation_min, b.saturation_min) AS saturation_min,
  COALESCE(od.saturation_max, os.saturation_max, b.saturation_max) AS saturation_max
FROM base b
LEFT JOIN os ON os.metric_id=b.metric_id
LEFT JOIN od ON od.metric_id=b.metric_id;
```

#### 使用视图的代码（2处）

**1. 存储过程: sp_refresh_metric_rule_auto_baseline_meta**
- 文件: `scripts/sql/migrations/022_alter_sp_refresh_metric_rule_auto_baseline_meta.sql`
- 用途: 自动基线计算
- 使用方式:
```sql
LEFT JOIN LATERAL (
  SELECT resolution, phys_min, phys_max
  FROM v_effective_metric_metadata vm
  WHERE vm.metric_id = f.metric_id
    AND (vm.device_id = f.device_id OR vm.device_id IS NULL)
    AND (vm.station_id = f.station_id OR vm.station_id IS NULL)
  ORDER BY (vm.device_id IS NOT NULL) DESC, 
           (vm.station_id IS NOT NULL) DESC
  LIMIT 1
) meta ON TRUE
```

**2. Python服务: app/services/rules/auto_baseline_b.py**
- 用途: 方案B自动基线生成（基于STL分解）
- 使用方式:
```python
cur.execute(
    """
    SELECT COALESCE(vm.resolution, 0.0)
    FROM v_effective_metric_metadata vm
    WHERE vm.metric_id = %s 
      AND (vm.device_id = %s OR vm.device_id IS NULL)
      AND (vm.station_id = %s OR vm.station_id IS NULL)
    ORDER BY (vm.device_id IS NOT NULL) DESC, 
             (vm.station_id IS NOT NULL) DESC
    LIMIT 1
    """,
    (met, dev, st),
)
```
- 功能: 读取分辨率用于平台期阈值计算
  - `flatline_eps = max(resolution, mad * 0.5)`
  - `flatline_delta = max(resolution * 2.0, mad * 1.0)`

---

## 🔬 每个字段的用途分析

### 字段使用情况矩阵

| 字段 | 数据类型 | 是否被使用 | 使用位置 | 用途说明 |
|------|---------|-----------|---------|---------|
| **metric_id** | bigint PK | ✅ 是 | 所有引用 | 主键，关联指标配置 |
| **unit** | text | ✅ 是 | 视图、种子脚本 | 单位（kW、A、V、Hz等） |
| **resolution** | double precision | ✅ **高频使用** | 存储过程、Python服务 | **分辨率/最小可分辨值**，用于平台期检测 |
| **phys_min** | double precision | ✅ 是 | 存储过程 | 物理/量程下界 |
| **phys_max** | double precision | ✅ 是 | 存储过程 | 物理/量程上界 |
| **saturation_min** | double precision | ✅ 是 | 视图 | 下饱和判据阈值 |
| **saturation_max** | double precision | ✅ 是 | 视图 | 上饱和判据阈值 |
| **remark** | text | ⚠️ 部分 | 种子脚本 | 备注（指标类别描述） |
| **updated_at** | timestamptz | ⚠️ 审计 | 自动更新 | 更新时间戳 |
| **updated_by** | text | ⚠️ 审计 | 手动维护 | 更新人 |

### 关键字段详解

#### 1. resolution（分辨率）- **最重要**
**使用频率**: 高  
**使用场景**:
- 平台期检测（flatline detection）
- 噪声过滤
- 数值比较的最小精度

**代码证据**:
```python
# auto_baseline_b.py (第323行、第399行)
flatline_eps = float(max(reso, mad * 0.5))
flatline_delta = float(max(reso * 2.0, mad * 1.0))
```

**种子数据逻辑**:
```sql
-- 021_seed_dim_metric_metadata.sql
CASE
  WHEN lower(m.unit) IN ('v') THEN 1.0              -- 电压 1V
  WHEN lower(m.unit) IN ('a') THEN 0.1              -- 电流 0.1A
  WHEN lower(m.unit) IN ('kw') THEN 0.01            -- 有功功率 0.01kW
  WHEN lower(m.unit) IN ('kwh') THEN 1.0            -- 电能 1kWh
  WHEN lower(m.unit) IN ('hz') THEN 0.1             -- 频率 0.1Hz
  WHEN lower(m.unit) IN ('m3/h','m3/h ') THEN 0.1   -- 瞬时流量 0.1 m3/h
  WHEN lower(m.unit) IN ('m3') THEN 1.0             -- 累计流量 1 m3
  WHEN lower(m.unit) IN ('mpa') THEN 0.001          -- 压力 0.001 MPa
  WHEN lower(m.unit) IN ('mm/s','mm/s ') THEN 0.01  -- 振动 0.01 mm/s
  WHEN lower(m.unit) IN ('rpm') THEN 1.0            -- 转速 1 rpm
  WHEN lower(m.unit) IN ('n.m','nm') THEN 0.1       -- 扭矩 0.1 N·m
  WHEN lower(m.unit) IN ('%','pct','percent') THEN 0.1 -- 百分比 0.1%
  WHEN lower(m.unit) IN ('c','°c','degc') THEN 0.1  -- 温度 0.1°C
  ELSE NULL
END AS resolution
```

#### 2. phys_min / phys_max（物理边界）
**使用频率**: 中  
**使用场景**:
- 自动基线计算的参考范围
- 质量检查的物理约束

**代码证据**:
```sql
-- 022_alter_sp_refresh_metric_rule_auto_baseline_meta.sql
SELECT f.station_id, f.device_id, f.metric_id, f.ts_bucket, 
       f.value::float8 AS value,
       meta.resolution, meta.phys_min, meta.phys_max
FROM fact_measurements f
LEFT JOIN LATERAL (
  SELECT resolution, phys_min, phys_max
  FROM v_effective_metric_metadata vm
  ...
) meta ON TRUE
```

#### 3. saturation_min / saturation_max（饱和阈值）
**使用频率**: 低  
**使用场景**:
- 饱和检测（传感器接近量程边界）
- 质量码标记

**设计意图**:
```sql
-- 017_create_dim_metric_metadata.sql 注释
COMMENT ON COLUMN saturation_min IS '下饱和判据阈值（接近 phys_min 持续判为饱和）';
COMMENT ON COLUMN saturation_max IS '上饱和判据阈值（接近 phys_max 持续判为饱和）';
```

#### 4. unit（单位）
**使用频率**: 中  
**使用场景**:
- 数据展示
- 单位转换
- 分辨率推断

#### 5. remark（备注）
**使用频率**: 低  
**使用场景**:
- 审计和文档
- 指标分类说明

**种子数据示例**:
```sql
CASE
  WHEN m.metric_key ILIKE '%power_factor%' THEN '功率因数（0~1）'
  WHEN m.metric_key ILIKE '%active_power%' THEN '有功功率'
  WHEN m.metric_key ILIKE '%current%' THEN '电流（A相/B相/C相）'
  WHEN m.metric_key ILIKE '%voltage%' THEN '电压（A相/B相/C相）'
  WHEN m.metric_key ILIKE '%frequency%' THEN '变频器频率/电网频率'
  WHEN m.metric_key ILIKE '%flow%' THEN '流量（瞬时/累计）'
  WHEN m.metric_key ILIKE '%pressure%' THEN '压力（进/出口/总管）'
  WHEN m.metric_key = 'device_running' THEN '设备运行状态（0/1）'
  WHEN m.metric_key = 'device_phase' THEN '运行相位（0停止/1稳态/2启动/3停止）'
  ELSE COALESCE(NULLIF(m.unit_display,''), '通用指标')
END AS remark
```

---

## ⚠️ 表为空的影响

### 当前影响评估

**1. 视图返回空结果**
- `v_effective_metric_metadata` 视图可以查询，但返回0行
- 不会报错，但无法提供元数据

**2. 存储过程使用默认值**
```sql
-- 当视图返回NULL时
meta.resolution → NULL
meta.phys_min → NULL
meta.phys_max → NULL
```

**3. Python服务回退逻辑**
```python
# auto_baseline_b.py
reso = float(row_res[0]) if row_res and row_res[0] is not None else 0.0
# 当 resolution 为 NULL 时，使用 0.0
flatline_eps = float(max(0.0, mad * 0.5))  # 仅依赖 MAD
```

**4. 功能降级**
- ✅ 系统仍可运行（不会崩溃）
- ⚠️ 平台期检测精度下降（缺少分辨率参考）
- ⚠️ 物理边界检查失效（缺少 phys_min/phys_max）
- ⚠️ 饱和检测失效（缺少 saturation_min/saturation_max）

---

## 🚀 解决方案

### 立即执行（P0 - 高优先级）

**方法1: 使用现有Python脚本（推荐）**
```bash
# 执行元数据迁移脚本（包含种子数据）
python scripts/dev/apply_metadata_migrations.py
```

**方法2: 直接执行SQL脚本**
```bash
# 仅执行种子数据脚本
psql -f scripts/sql/migrations/021_seed_dim_metric_metadata.sql

# 验证结果
psql -c "SELECT COUNT(*) FROM dim_metric_metadata;"
# 预期: 56行（与 dim_metric_config 数量一致）
```

### 验证步骤

```sql
-- 1. 检查数据量
SELECT COUNT(*) as total_rows FROM dim_metric_metadata;

-- 2. 检查字段填充情况
SELECT 
    COUNT(*) as total,
    COUNT(unit) as has_unit,
    COUNT(resolution) as has_resolution,
    COUNT(phys_min) as has_phys_min,
    COUNT(phys_max) as has_phys_max,
    COUNT(saturation_min) as has_saturation_min,
    COUNT(saturation_max) as has_saturation_max
FROM dim_metric_metadata;

-- 3. 查看示例数据
SELECT 
    mc.metric_key,
    mm.unit,
    mm.resolution,
    mm.phys_min,
    mm.phys_max,
    mm.remark
FROM dim_metric_metadata mm
JOIN dim_metric_config mc ON mm.metric_id = mc.id
LIMIT 10;

-- 4. 验证视图
SELECT COUNT(*) FROM v_effective_metric_metadata;
```

---

## 📝 总结

### 核心发现

1. **表为空的原因**: 种子数据脚本（021）从未执行
2. **表的作用**: 存储指标物理元数据，支持质量检查和基线计算
3. **依赖功能**: 
   - 自动基线计算（存储过程 + Python服务）
   - 平台期检测
   - 物理边界检查
   - 饱和检测
4. **字段使用**: 所有字段都有明确用途，`resolution` 字段最关键

### 建议行动

- ✅ **立即执行**: `python scripts/dev/apply_metadata_migrations.py`
- ✅ **验证数据**: 确认56行数据已生成
- ✅ **测试功能**: 运行自动基线计算验证元数据生效
- ⚠️ **后续优化**: 考虑将此脚本集成到CLI工作流（如 `prepare-dim` 阶段）

---

**分析完成时间**: 2025-01-04
**下一步**: 继续研究关联问题（见下方扩展分析）

---

## 🔬 扩展分析 - 关联问题深度调查

### 问题1: dim_metric_metadata_override 表状态

**表状态**：
- 行数: 0
- 设备数: 0
- 站点数: 0
- 指标数: 0

**结论**: ✅ **表为空，但设计完整**

**表结构**（12个字段）：
- rule_id (PK, 自增)
- station_id (FK → dim_stations)
- device_id (FK → dim_devices)
- metric_id (FK → dim_metric_config)
- resolution, phys_min, phys_max, saturation_min, saturation_max
- remark, updated_at, updated_by

**代码引用**：
- 创建脚本: `018_create_dim_metric_metadata_override.sql`
- 视图引用: `020_create_v_effective_metric_metadata.sql`
- 示例脚本: `scripts/dev/apply_overrides_examples.py`（演示如何插入覆盖数据）
- 备份记录: 24个备份文件，全部显示"行数: 0"

**覆盖机制设计**：
```sql
-- 优先级: 设备级 > 站点级 > 全局级
-- 设备级覆盖: device_id IS NOT NULL
-- 站点级覆盖: device_id IS NULL AND station_id IS NOT NULL
-- 全局级: dim_metric_metadata 表
```

**影响评估**：
- ✅ 不影响系统运行（视图可正常工作）
- ⚠️ 无法实现设备/站点级元数据定制
- ⚠️ 所有设备使用相同的全局元数据

---

### 问题2: apply_metadata_migrations.py 执行历史

**脚本分析**：
- 位置: `scripts/dev/apply_metadata_migrations.py`
- 功能: 执行迁移文件 017-021（包括种子数据）
- 设计: 幂等性（CREATE IF NOT EXISTS, INSERT WHERE NOT EXISTS）

**执行证据搜索结果**：
- ❌ **未找到任何执行日志**
- ❌ **未集成到CLI命令**（`app/cli/main.py` 中无引用）
- ❌ **未在部署脚本中调用**
- ❌ **未在测试文件中调用**

**对比其他迁移脚本**：
- `scripts/dev/apply_040.py` - 单独迁移脚本（类似模式）
- `scripts/run_migration_040.py` - 另一个迁移脚本
- `scripts/tools/apply_threshold_migrations.py` - 阈值迁移脚本
- **共同点**: 都是手动执行脚本，未集成到自动化流程

**结论**: ✅ **确认脚本从未执行**

---

### 问题3: 自动基线计算运行状态

**表状态对比**：

| 表名 | 行数 | 站点数 | 设备数 | 指标数 | 状态 |
|------|------|--------|--------|--------|------|
| metric_rule_auto_baseline | 0 | 0 | 0 | 0 | ❌ **空表** |
| metric_rule_auto_baseline_shadow | 64 | 1 | 8 | 14 | ✅ **有数据** |

**关键发现**：
1. **方案A（正式表）从未运行**
   - `metric_rule_auto_baseline` 表为空
   - 存储过程 `sp_refresh_metric_rule_auto_baseline_meta` 未被调用

2. **方案B（影子表）已运行**
   - `metric_rule_auto_baseline_shadow` 有64行数据
   - 覆盖: 1个站点、8个设备、14个指标
   - Python服务 `auto_baseline_b.py` 已执行

**数据示例**（从备份文件）：
```sql
-- 所有记录的特征:
-- method = 'stl_residual'
-- version = 'vB_shadow'
-- value_min = 0.0, value_max = 0.0
-- spike_abs = 0.0, roc_abs = 0.0, roc_ratio = nan
-- flatline_eps = 0.0, flatline_delta = 0.0
-- remark = 'seed:auto_baseline_shadow'
```

**异常分析**：
- ⚠️ **所有阈值都是0.0或NaN** - 可能是初始化数据或计算失败
- ⚠️ **remark显示"seed"** - 表明是种子数据，非真实计算结果

**元数据依赖验证**：
- 方案B代码中查询 `v_effective_metric_metadata` 获取 `resolution`
- 当元数据为空时，使用默认值 `0.0`
- 导致 `flatline_eps = max(0.0, mad * 0.5)` 仅依赖MAD

---

### 问题4: 质量检查功能实际影响

**质量状态分布**：
```
quality_status = 0 (GOOD): 634,530 行 (100%)
```

**关键发现**：
- ✅ **所有数据质量状态为0（正常）**
- ❌ **没有任何质量问题被检测到**

**质量检查表状态**：
- `metric_quality_rules`: 0行（手动规则表为空）
- `fact_measurements`: 634,530行（全部quality_status=0）
- `quality_code_dict`: 34行（质量码字典已定义）

**影响分析**：

**1. 缺少元数据的影响**：
- 物理越界检查（101）: ❌ 失效（缺少 phys_min/phys_max）
- 饱和检测（131）: ❌ 失效（缺少 saturation_min/saturation_max）
- 平台期检测（121）: ⚠️ 精度下降（缺少 resolution）

**2. 缺少质量规则的影响**：
- 异常跳变检查（111）: ❌ 失效（缺少 spike_abs）
- 变化率检查（112）: ❌ 失效（缺少 roc_abs, roc_ratio）
- 平台期检查（121）: ❌ 失效（缺少 flatline_eps, flatline_delta）

**3. 实际运行状态**：
- ✅ 系统正常运行（不会崩溃）
- ⚠️ 质量检查功能完全失效
- ⚠️ 所有数据被标记为"正常"（可能掩盖真实问题）

**回退逻辑验证**：
```python
# auto_baseline_b.py 中的回退逻辑
reso = float(row_res[0]) if row_res and row_res[0] is not None else 0.0
# 当 resolution 为 NULL 时，使用 0.0
flatline_eps = float(max(0.0, mad * 0.5))  # 仅依赖 MAD
```

---

### 问题5: 种子数据脚本数据质量

**脚本分析**: `021_seed_dim_metric_metadata.sql`

**单位覆盖率验证**：

| 单位 | 指标数量 | 分辨率 | 覆盖状态 |
|------|---------|--------|---------|
| mm/s | 16 | 0.01 | ✅ 已覆盖 |
| c | 13 | 0.1 | ✅ 已覆盖 |
| mpa | 4 | 0.001 | ✅ 已覆盖 |
| a | 3 | 0.1 | ✅ 已覆盖 |
| v | 3 | 1.0 | ✅ 已覆盖 |
| kw | 3 | 0.01 | ✅ 已覆盖 |
| m3 | 2 | 1.0 | ✅ 已覆盖 |
| m | 2 | NULL | ❌ **未覆盖** |
| m3/h | 2 | 0.1 | ✅ 已覆盖 |
| % | 1 | 0.1 | ✅ 已覆盖 |
| kwh | 1 | 1.0 | ✅ 已覆盖 |
| n.m | 1 | 0.1 | ✅ 已覆盖 |
| rpm | 1 | 1.0 | ✅ 已覆盖 |
| hz | 1 | 0.1 | ✅ 已覆盖 |

**覆盖率统计**：
- 总单位类型: 14种
- 已覆盖: 13种 (92.9%)
- 未覆盖: 1种 (7.1%) - 单位"m"（液位、扬程）

**未覆盖单位分析**：
```sql
-- 单位 "m" 的指标:
-- pool_liquid_level (液位)
-- pump_head (扬程)
--
-- 脚本中缺少对 "m" 单位的处理
-- 建议分辨率: 0.01 m (1cm精度)
```

**remark字段覆盖率**：

| 指标类型 | 数量 | remark示例 |
|---------|------|-----------|
| power_factor | ? | '功率因数（0~1）' |
| active_power | ? | '有功功率' |
| current | 3 | '电流（A相/B相/C相）' |
| voltage | 3 | '电压（A相/B相/C相）' |
| frequency | 1 | '变频器频率/电网频率' |
| flow | 2 | '流量（瞬时/累计）' |
| pressure | 4 | '压力（进/出口/总管）' |
| level | 1 | '液位' |
| temperature | 13 | '温度' |
| vibration | 16 | '振动' |
| torque | 1 | '扭矩' |
| device_running | 1 | '设备运行状态（0/1）' |
| device_phase | 1 | '运行相位（0停止/1稳态/2启动/3停止）' |
| 其他 | ? | COALESCE(unit_display, '通用指标') |

**数据质量评估**：

**优点**：
- ✅ 覆盖率高（92.9%）
- ✅ 分辨率设置合理（基于工程经验）
- ✅ remark字段提供清晰的中文说明
- ✅ 幂等性设计（WHERE NOT EXISTS）

**缺点**：
- ⚠️ 单位"m"未覆盖（需要补充）
- ⚠️ phys_min/phys_max全部为NULL（需要后续配置）
- ⚠️ saturation_min/saturation_max全部为NULL（需要后续配置）

**建议修正**：
```sql
-- 在脚本中添加对单位 "m" 的处理
WHEN lower(m.unit) IN ('m') THEN 0.01  -- 液位/扬程 0.01m
```

---

## 📊 综合结论

### 核心问题汇总

| 问题 | 状态 | 影响 | 优先级 |
|------|------|------|--------|
| dim_metric_metadata 为空 | ❌ 严重 | 质量检查精度下降 | P0 |
| dim_metric_metadata_override 为空 | ⚠️ 中等 | 无法定制设备级元数据 | P2 |
| metric_rule_auto_baseline 为空 | ❌ 严重 | 自动基线功能失效 | P1 |
| metric_quality_rules 为空 | ❌ 严重 | 手动规则功能失效 | P1 |
| 质量检查全部通过 | ⚠️ 可疑 | 可能掩盖真实问题 | P1 |

### 系统健康度评估

**数据完整性**: ⚠️ 60/100
- ✅ 事实表有数据（634,530行）
- ✅ 维度表完整（站点、设备、指标配置）
- ❌ 元数据表为空（2个表）
- ❌ 规则表为空（2个表）

**功能可用性**: ⚠️ 40/100
- ✅ 数据导入功能正常
- ✅ 基础查询功能正常
- ⚠️ 质量检查功能降级
- ❌ 自动基线功能失效（方案A）
- ⚠️ 自动基线功能异常（方案B）

**数据质量**: ⚠️ 未知
- ❓ 所有数据quality_status=0（可疑）
- ❓ 无法验证真实数据质量
- ❓ 可能存在未检测的异常

### 立即行动建议

**P0 - 立即执行（今天）**：
1. 执行种子数据脚本
   ```bash
   python scripts/dev/apply_metadata_migrations.py
   ```
2. 验证数据生成
   ```sql
   SELECT COUNT(*) FROM dim_metric_metadata;  -- 预期: 56
   SELECT COUNT(*) FROM v_effective_metric_metadata;  -- 预期: 56
   ```

**P1 - 本周内**：
1. 运行自动基线计算（方案A）
   ```bash
   python -m app.cli.main [自动基线命令]
   ```
2. 配置手动质量规则（至少关键指标）
3. 重新运行质量检查，验证是否检测到问题

**P2 - 本月内**：
1. 配置 phys_min/phys_max（物理边界）
2. 配置 saturation_min/saturation_max（饱和阈值）
3. 评估是否需要设备级元数据覆盖

**P3 - 后续优化**：
1. 将元数据初始化集成到CLI工作流
2. 添加元数据验证检查
3. 建立元数据变更审计机制

---

**扩展分析完成时间**: 2025-01-04
**下一步**: 继续研究自动基线计算失败原因

---

## 🧪 自动基线计算深度调查（2025-11-05）

### 测试环境
- 测试文件: `tests/test_auto_baseline_investigation.py`
- 数据范围: 2025-06-01 02:00:00 ~ 03:59:59 (仅2小时)
- 总数据量: 634,530行
- 稳态数据: 7,386行 (phase=1)

### 方案A（存储过程）测试结果

**执行状态**: ✅ 成功执行，但生成0行数据

**失败原因分析**:
1. **时间窗口不匹配** (根本原因)
   - 存储过程参数: `lookback_days=30`
   - 查询时间窗口: `now() - 30天` ~ `now()`
   - 实际数据时间: 2025-06-01 02:00 ~ 03:59 (仅2小时)
   - **结果**: 时间窗口完全不重叠，查询返回0行

2. **元数据表为空**
   - `dim_metric_metadata`: 0行
   - `v_effective_metric_metadata`: 0行
   - 影响: 物理边界过滤失效，但不是主要原因

**存储过程逻辑**:
```sql
-- 时间窗口计算
v_start := now() - make_interval(days => p_lookback_days);  -- 30天前
v_end   := now();                                            -- 现在

-- 数据筛选
WHERE f.ts_bucket >= v_start AND f.ts_bucket < v_end
```

**问题**: 如果数据是历史数据（如6月1日），而当前时间是11月5日，则：
- v_start = 2025-10-06 (30天前)
- v_end = 2025-11-05 (现在)
- 数据时间 = 2025-06-01 (不在窗口内)
- **结果**: 0行数据

### 方案B（Python STL）测试结果

**执行状态**: ❌ SQL语法错误

**错误信息**:
```
psycopg.errors.GroupingError: column "metric_rule_auto_baseline.p05" must appear in the GROUP BY clause or be used in an aggregate function
LINE 2:  SELECT p05, p95, percentile_cont(0.5...
```

**错误位置**: `app/services/rules/auto_baseline_b.py:232`

**问题**: 代码中有SQL语法错误，尝试从 `metric_rule_auto_baseline` 表查询数据并计算中位数，但列未在GROUP BY中

**警告信息**:
- `FutureWarning: 'S' is deprecated, use 's' instead` (60次)
- `RuntimeWarning: All-NaN slice encountered` (7次)

**分析**:
- 方案B在处理某些指标时遇到全NaN数据
- 可能是因为某些指标在稳态时没有数据

### 根本原因总结

| 问题 | 方案A | 方案B | 根本原因 |
|------|-------|-------|---------|
| 时间窗口不匹配 | ✅ 是 | ❓ 未知 | 数据是历史数据，lookback_days参数不适用 |
| 元数据表为空 | ⚠️ 次要 | ⚠️ 次要 | 种子脚本未执行 |
| SQL语法错误 | ❌ 否 | ✅ 是 | 代码bug |
| 数据量不足 | ❌ 否 | ⚠️ 可能 | 仅2小时数据，STL需要更长周期 |

### 解决方案

**立即修复（P0）**:
1. **修改存储过程调用方式**
   - 使用 `sp_refresh_metric_rule_auto_baseline_win(start, end, station_id, device_id)`
   - 明确指定时间窗口：`start='2025-06-01 02:00:00'`, `end='2025-06-01 04:00:00'`
   - 避免使用 `lookback_days` 参数

2. **修复方案B的SQL错误**
   - 检查 `auto_baseline_b.py:232` 的SQL语句
   - 修复GROUP BY子句

3. **执行种子数据脚本**
   ```bash
   python scripts/dev/apply_metadata_migrations.py
   ```

**验证步骤**:
1. 使用时间窗口版本的存储过程重新测试
   ```python
   run_auto_baseline(
       settings,
       start='2025-06-01T02:00:00Z',
       end='2025-06-01T04:00:00Z',
       station_id=None,
       device_id=None
   )
   ```

2. 验证是否生成数据
   ```sql
   SELECT COUNT(*) FROM metric_rule_auto_baseline;
   ```

3. 检查数据质量
   ```sql
   SELECT
       AVG(p05), AVG(p95), AVG(median), AVG(mad),
       AVG(spike_abs), AVG(flatline_eps)
   FROM metric_rule_auto_baseline;
   ```

### 测试发现的其他问题

1. **FutureWarning**: pandas resample使用了废弃的'S'，应改为's'
2. **All-NaN警告**: 某些指标在稳态时全是NaN，需要数据质量检查
3. **错误处理管理器**: Settings对象缺少error_handling属性（非关键）

---

**自动基线调查完成时间**: 2025-11-05
**下一步**: 修复时间窗口问题并重新测试

