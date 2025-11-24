# 核心问题总结：为什么修改 mv_device_running_1s 表后计算仍然失败？

**创建时间**: 2025-11-11  
**问题时间点**: 2025-10-23 10:48:08+08  

---

## ❓ 您的疑问

> "mv_device_running_1s 表中所有设备(1-6)的 running 字段都是 1，是我修改的用于排查问题，但是为什么我已经修改成1了，还是计算失败了。缺失指标计算判断设备都是运行，应该在mv_device_running_1s 表获取！"

---

## ✅ 简短答案

**`mv_device_running_1s.running` 字段只控制"数据是否被加载"，不控制"数据是否参与计算"。**

您的修改确实生效了（数据被成功加载），但计算引擎在**计算阶段**使用了另一套判断标准（硬编码的频率和功率阈值），导致停机设备的数据被过滤掉。

---

## 🔍 详细解释

### 两套判断标准

系统中存在**两套独立的"运行状态"判断标准**：

#### 标准1：数据加载阶段（您可以控制）

**位置**: `app/services/calculation/orchestrator.py` 第228-242行

```python
if filter_running:
    query_device = """
        SELECT fm.ts_bucket, fm.metric_id, fm.value
        FROM fact_measurements fm
        INNER JOIN mv_device_running_1s dr
            ON fm.station_id = dr.station_id
            AND fm.device_id = dr.device_id
            AND fm.ts_bucket = dr.ts_bucket
        WHERE ...
          AND dr.running = 1  ← 您修改的字段在这里生效
    """
```

**您的修改效果**:
- ✅ 设备1的 `running=1` → 数据被加载
- ✅ 13个指标数据进入内存，包括 `pump_frequency=0`, `pump_active_power=0`

---

#### 标准2：计算阶段（您无法通过修改表控制）

**位置**: `app/services/calculation/orchestrator.py` 第1676-1681行

```python
f_thr = float(params_cfg.get("f_thr", 3.0))  # 频率阈值 = 3.0 Hz
p_thr = float(params_cfg.get("p_thr", 0.5))  # 功率阈值 = 0.5 kW

valid_mask = (
    ~np.isnan(power)
    & ~np.isnan(freq)
    & (freq >= f_thr)      # ← 硬编码的阈值检查
    & (power >= p_thr)     # ← 硬编码的阈值检查
)
```

**设备1的实际情况**:
- ❌ `freq = 0 Hz < 3.0 Hz` → 不通过
- ❌ `power = 0 kW < 0.5 kW` → 不通过
- ❌ `valid_mask = False` → 权重为0
- ❌ 无法参与流量分摊计算

---

### 完整流程对比

| 阶段 | 判断标准 | 设备1状态 | 结果 |
|------|---------|----------|------|
| **数据加载** | `mv_device_running_1s.running = 1` | ✅ running=1 (您的修改) | ✅ 数据加载成功 |
| **权重计算** | `freq >= 3.0 AND power >= 0.5` | ❌ freq=0, power=0 | ❌ 权重为0 |
| **流量分摊** | `weight_i > 0` | ❌ weight_i=0 | ❌ share=NaN |
| **指标计算** | `share 不为 NaN` | ❌ share=NaN | ❌ result=NaN |
| **写入数据库** | `result 不为 NaN` | ❌ result=NaN | ❌ 不写入 |

---

## 🎯 为什么设计成两套标准？

### 设计意图

1. **数据加载阶段的 `running` 字段**:
   - 用途: 粗粒度过滤，减少数据加载量
   - 基于: 设备的运行状态标记（可能基于开关信号、运行时长等）

2. **计算阶段的阈值检查**:
   - 用途: 细粒度过滤，保证计算的数值稳定性
   - 基于: 实际的物理信号（频率、功率）
   - 原因: 
     * 停机设备的频率=0、功率=0会导致数学错误（除零、权重为0）
     * 低频率/低功率运行可能是异常状态，不应参与正常计算
     * 功率×频率分摊法需要至少2台泵有效运行才能准确

### 实际案例

**设备2和6（成功）**:
- 数据加载: `running=1` ✅
- 阈值检查: `freq=48.44 Hz > 3.0`, `power=269.6 kW > 0.5` ✅
- 权重计算: `weight = 269.6 × 48.44 = 13,059.42` ✅
- 流量分摊: `share = 13,059.42 / 21,987.66 = 59.4%` ✅
- 结果: 18个指标全部成功 ✅

**设备1、4、5（失败）**:
- 数据加载: `running=1` ✅ (您的修改生效)
- 阈值检查: `freq=0 < 3.0`, `power=0 < 0.5` ❌
- 权重计算: `weight = 0` ❌
- 流量分摊: `share = NaN` ❌
- 结果: 5个指标失败 ❌

---

## 📊 数据验证

### SQL验证：数据确实被加载了

```sql
SELECT fm.device_id, mc.metric_key, fm.value, dr.running
FROM fact_measurements fm
INNER JOIN mv_device_running_1s dr
    ON fm.station_id = dr.station_id
    AND fm.device_id = dr.device_id
    AND fm.ts_bucket = dr.ts_bucket
INNER JOIN dim_metric_config mc ON mc.id = fm.metric_id
WHERE fm.ts_bucket = '2025-10-23 10:48:08+08'
  AND fm.device_id = 1
  AND dr.running = 1;
```

**结果**: 13条记录，包括:
- `pump_frequency = 0` ✅ 被加载
- `pump_active_power = 0` ✅ 被加载
- `pump_head = 49.57` ✅ 被加载
- ... 其他10个指标

**结论**: 您的修改确实生效了，数据加载阶段没有问题。

---

### 代码验证：阈值过滤逻辑

**设备1的权重计算过程**:

```python
# 输入数据
freq = np.array([0.0])      # 设备1的频率
power = np.array([0.0])     # 设备1的功率
f_thr = 3.0                 # 频率阈值
p_thr = 0.5                 # 功率阈值

# 阈值检查
valid_mask = (freq >= f_thr) & (power >= p_thr)
# valid_mask = (0.0 >= 3.0) & (0.0 >= 0.5)
# valid_mask = False & False
# valid_mask = [False]

# 权重计算
weight_i = np.zeros_like(power)  # [0.0]
if np.any(valid_mask):           # if np.any([False]):
    # 这个分支不会执行
    weight_i[valid_mask] = power[valid_mask] * freq[valid_mask]

# 提前返回检查
if not np.any(weight_i > 0):     # if not np.any([0.0] > 0):
    # 这个分支会执行
    data["__pump_flow_rate_share"] = np.nan
    return  # ← 提前返回，后续计算不再执行
```

**结论**: 阈值过滤逻辑导致设备1的权重为0，无法参与计算。

---

## 🔧 解决方向（仅方向，不具体规划）

### 方向1: 统一判断标准
- 让计算阶段也使用 `mv_device_running_1s.running` 字段
- 移除硬编码的阈值检查
- 风险: 可能导致数值计算异常

### 方向2: 修正运行状态判断
- 基于频率/功率阈值自动更新 `mv_device_running_1s.running` 字段
- 确保两套标准一致
- 优点: 数据一致性更好

### 方向3: 停机设备特殊处理
- 停机设备直接写入0值，而不是尝试计算
- 明确区分"无法计算"和"计算结果为0"
- 优点: 逻辑更清晰

### 方向4: 调整阈值参数
- 降低 `f_thr` 和 `p_thr` 的值
- 允许更低的频率/功率参与计算
- 风险: 可能引入不准确的计算结果

---

## 📋 关键发现总结

1. ✅ **您的修改生效了**: `mv_device_running_1s.running=1` → 数据被加载
2. ❌ **但计算失败了**: 阈值检查 `freq >= 3.0 AND power >= 0.5` → 权重为0
3. 🎯 **根本原因**: 两套独立的判断标准，您只能控制第一套
4. 💡 **设计意图**: 阈值检查是为了保证计算的数值稳定性
5. 🔧 **解决方向**: 需要统一判断标准或特殊处理停机设备

---

**文档创建时间**: 2025-11-11  
**分析模式**: RIPER-5 研究模式  
**相关文档**: `.tasks/指标计算失败根因分析_2025-10-23_10-48-08.md`

