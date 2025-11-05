# 数据库字典

**生成时间**: 2025-10-30 13:36:06

**数据库**: pump_station_optimization

---

## 目录

- [核心参数表](#核心参数表)
- [维度表](#维度表)
- [事实表](#事实表)
- [配置表](#配置表)
- [日志表](#日志表)
- [视图](#视图)

---

## 核心参数表

### global_default_rated_params

**表注释**:

```

全局默认额定参数表

用途：
  存储全局默认的额定参数，作为设备参数的后备值。
  当设备没有配置特定的额定参数时，使用全局默认值。
  在5层参数优先级系统中处于第2层（global → global_default_rated → device_rated → station → device）。

参数粒度：
  - 全局级参数：所有设备共享的默认值
  - 不支持时间有效性：全局默认值始终有效

📚 参数字典（按类型分类）：

【额定运行参数】
  • rated_frequency（额定频率）
    - 物理含义：设备的额定运行频率，用于计算泵的实际转速
    - 计算公式：n = (f / f_ref) × n_ref × (1 - slip)
      其中：n = 转速 (rpm)
           f = 实际频率 (Hz)
           f_ref = 额定频率 (Hz)
           n_ref = 额定转速 (rpm)
           slip = 电机转差率 (无量纲)
    - 单位：Hz
    - 典型值：50（中国）、60（美国）
    - 默认值：50.0
    - 用途：作为转速计算的参考频率，反映电网频率标准

  • poles_pair（极对数）
    - 物理含义：电机的极对数，决定电机的同步转速
    - 计算公式：n_sync = (60 × f) / p
      其中：n_sync = 同步转速 (rpm)
           f = 频率 (Hz)
           p = 极对数 (无量纲)
    - 单位：无量纲
    - 典型值：2（对应1500rpm@50Hz）、3（对应1000rpm@50Hz）
    - 默认值：2
    - 用途：计算电机的同步转速，用于转速计算

  • rated_efficiency（额定效率）
    - 物理含义：设备在额定工况下的效率
    - 计算公式：eta = P_out / P_in = (rho × g × Q × H) / (P_e × 1000)
      其中：eta = 效率 (无量纲)
           P_out = 输出功率 (W)
           P_in = 输入功率 (W)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
           Q = 流量 (m³/s)
           H = 扬程 (m)
           P_e = 电功率 (kW)
    - 单位：无量纲
    - 典型范围：0.60 ~ 0.85
    - 默认值：0.75
    - 用途：作为效率计算的参考值，用于性能评估

  • rated_flow（额定流量）
    - 物理含义：设备在额定工况下的流量
    - 单位：m³/h
    - 典型范围：100 ~ 1000（根据泵型号）
    - 默认值：400.0
    - 用途：作为流量计算的参考值，用于性能曲线拟合

  • rated_head（额定扬程）
    - 物理含义：设备在额定工况下的扬程
    - 单位：m
    - 典型范围：20 ~ 100（根据泵型号）
    - 默认值：50.0
    - 用途：作为扬程计算的参考值，用于性能曲线拟合

  • rated_power（额定功率）
    - 物理含义：设备的额定电功率
    - 单位：kW
    - 典型范围：50 ~ 500（根据泵型号）
    - 默认值：110.0
    - 用途：作为功率计算的参考值，用于能耗分析

【效率参数】
  • eta_motor（电机效率）
    - 物理含义：电机的效率，反映电能转换为机械能的效率
    - 计算公式：eta_pump = eta_measured / (eta_motor × eta_vfd)
      其中：eta_pump = 泵效率 (无量纲)
           eta_measured = 测量效率 (无量纲)
           eta_motor = 电机效率 (无量纲)
           eta_vfd = 变频器效率 (无量纲)
    - 单位：无量纲
    - 典型范围：0.85 ~ 0.95
    - 默认值：0.92
    - 用途：用于效率计算，将电功率转换为轴功率

  • eta_vfd（变频器效率）
    - 物理含义：变频器的效率，反映电能通过变频器的损耗
    - 单位：无量纲
    - 典型范围：0.95 ~ 0.98
    - 默认值：0.97
    - 用途：用于效率计算，考虑变频器的能量损耗

数据来源：
  - SQL脚本初始化：系统初始化时导入默认值
  - 手动配置：根据实际情况调整默认值

更新机制：
  - 手动更新：通过SQL语句更新默认值
  - 全局生效：更新后立即对所有未配置设备参数的设备生效

使用示例：
  -- 查询所有全局默认参数
  SELECT param_key, default_value, param_unit
  FROM global_default_rated_params
  ORDER BY param_key;

  -- 查询额定频率的默认值
  SELECT default_value
  FROM global_default_rated_params
  WHERE param_key = 'rated_frequency'
  LIMIT 1;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| param_key | text | 否 | - | 参数键：参数的唯一标识符（如rated_frequency, poles_pair, rated_efficiency等），详见表注释中的参数字典 |
| default_value | numeric | 否 | - | 默认值：参数的默认数值，当设备没有配置特定参数时使用此值 |
| param_unit | text | 是 | - | 参数单位：参数的物理单位（如Hz, rpm, kW等） |
| description | text | 是 | - | 参数描述：参数的中文描述，说明参数的物理含义和用途 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| updated_at | timestamp with time zone | 否 | now() | 更新时间：记录最后更新的时间戳 |
| created_by | text | 是 | 'system'::text | 创建者：创建记录的用户或系统标识 |

---

### device_rated_params

**表注释**:

```

设备额定参数表

用途：
  存储每个设备的额定参数（如额定功率、额定流量、额定扬程等），用于计算流程中的参数加载。
  在5层参数优先级系统中处于第3层（global → global_default_rated → device_rated → station → device）。

参数粒度：
  - 设备级参数：每个设备可以有不同的额定参数
  - 支持时间有效性：通过 effective_from 和 effective_to 字段控制参数的有效期

📚 参数字典（按类型分类）：

【额定运行参数】
  • rated_frequency（额定频率）
    - 物理含义：设备的额定运行频率，用于计算泵的实际转速
    - 计算公式：n = (f / f_ref) × n_ref × (1 - slip)
      其中：n = 转速 (rpm)
           f = 实际频率 (Hz)
           f_ref = 额定频率 (Hz)
           n_ref = 额定转速 (rpm)
           slip = 电机转差率 (无量纲)
    - 单位：Hz
    - 典型值：50（中国）、60（美国）
    - 示例值：50.0
    - 用途：作为转速计算的参考频率，反映电网频率标准

  • poles_pair（极对数）
    - 物理含义：电机的极对数，决定电机的同步转速
    - 计算公式：n_sync = (60 × f) / p
      其中：n_sync = 同步转速 (rpm)
           f = 频率 (Hz)
           p = 极对数 (无量纲)
    - 单位：无量纲
    - 典型值：2（对应1500rpm@50Hz）、3（对应1000rpm@50Hz）
    - 示例值：2
    - 用途：计算电机的同步转速，用于转速计算

  • rated_efficiency（额定效率）
    - 物理含义：设备在额定工况下的效率
    - 计算公式：eta = P_out / P_in = (rho × g × Q × H) / (P_e × 1000)
      其中：eta = 效率 (无量纲)
           P_out = 输出功率 (W)
           P_in = 输入功率 (W)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
           Q = 流量 (m³/s)
           H = 扬程 (m)
           P_e = 电功率 (kW)
    - 单位：无量纲
    - 典型范围：0.60 ~ 0.85
    - 示例值：0.75
    - 用途：作为效率计算的参考值，用于性能评估

  • rated_flow（额定流量）
    - 物理含义：设备在额定工况下的流量
    - 单位：m³/h
    - 典型范围：100 ~ 1000（根据泵型号）
    - 示例值：400.0
    - 用途：作为流量计算的参考值，用于性能曲线拟合

  • rated_head（额定扬程）
    - 物理含义：设备在额定工况下的扬程
    - 单位：m
    - 典型范围：20 ~ 100（根据泵型号）
    - 示例值：50.0
    - 用途：作为扬程计算的参考值，用于性能曲线拟合

  • rated_power（额定功率）
    - 物理含义：设备的额定电功率
    - 单位：kW
    - 典型范围：50 ~ 500（根据泵型号）
    - 示例值：110.0
    - 用途：作为功率计算的参考值，用于能耗分析

【效率参数】
  • eta_motor（电机效率）
    - 物理含义：电机的效率，反映电能转换为机械能的效率
    - 计算公式：eta_pump = eta_measured / (eta_motor × eta_vfd)
      其中：eta_pump = 泵效率 (无量纲)
           eta_measured = 测量效率 (无量纲)
           eta_motor = 电机效率 (无量纲)
           eta_vfd = 变频器效率 (无量纲)
    - 单位：无量纲
    - 典型范围：0.85 ~ 0.95
    - 示例值：0.92
    - 用途：用于效率计算，将电功率转换为轴功率

  • eta_vfd（变频器效率）
    - 物理含义：变频器的效率，反映电能通过变频器的损耗
    - 单位：无量纲
    - 典型范围：0.95 ~ 0.98
    - 示例值：0.97
    - 用途：用于效率计算，考虑变频器的能量损耗

【管道参数】
  • pipe_diameter（管道直径）
    - 物理含义：与设备连接的管道内径
    - 单位：m
    - 典型范围：0.2 ~ 1.0
    - 示例值：0.5
    - 用途：用于流速计算和水力损失计算

  • pipe_length（管道长度）
    - 物理含义：管道的总长度
    - 单位：m
    - 典型范围：10 ~ 1000
    - 示例值：100.0
    - 用途：用于沿程损失计算

  • C_hazen（海曾-威廉系数）
    - 物理含义：管道粗糙度系数，用于海曾-威廉公式计算沿程损失
    - 计算公式：h_f = 10.67 × L × Q^1.852 / (C^1.852 × D^4.87)
      其中：h_f = 沿程损失 (m)
           L = 管道长度 (m)
           Q = 流量 (m³/s)
           C = 海曾-威廉系数 (无量纲)
           D = 管道直径 (m)
    - 单位：无量纲
    - 典型范围：100 ~ 140（新管道140，旧管道100）
    - 示例值：120
    - 用途：用于沿程损失计算

  • roughness_rel（相对粗糙度）
    - 物理含义：管道内壁的相对粗糙度，用于达西-魏斯巴赫公式计算沿程损失
    - 计算公式：epsilon_rel = epsilon / D
      其中：epsilon_rel = 相对粗糙度 (无量纲)
           epsilon = 绝对粗糙度 (m)
           D = 管道直径 (m)
    - 单位：无量纲
    - 典型范围：0.0001 ~ 0.01
    - 示例值：0.001
    - 用途：用于达西-魏斯巴赫公式计算摩擦系数

数据来源：
  - 设备铭牌：rated_frequency, poles_pair, rated_efficiency, rated_flow, rated_head, rated_power
  - 技术文档：eta_motor, eta_vfd
  - 现场测量：pipe_diameter, pipe_length, C_hazen, roughness_rel
  - SQL脚本导入：批量导入设备参数

更新机制：
  - 设备参数变更时手动更新
  - 支持时间有效性（effective_from, effective_to）
  - 新参数自动生效（effective_to IS NULL）
  - 旧参数自动失效（effective_to <= NOW()）

使用示例：
  -- 查询设备的所有有效额定参数
  SELECT param_key, value_numeric, unit
  FROM device_rated_params
  WHERE device_id = 1
    AND (effective_to IS NULL OR effective_to > NOW())
  ORDER BY param_key;

  -- 查询设备的额定频率
  SELECT value_numeric
  FROM device_rated_params
  WHERE device_id = 1
    AND param_key = 'rated_frequency'
    AND (effective_to IS NULL OR effective_to > NOW())
  LIMIT 1;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('device_rated_params_id_seq'::regclass) | ID（PK）
 |
| device_id | bigint | 否 | - | 设备ID
 |
| param_key | text | 否 | - | 参数键（如 rated_power）
 |
| value_numeric | numeric | 是 | - | 数值（numeric）
 |
| value_text | text | 是 | - | 文本值
 |
| unit | text | 是 | - | 单位
 |
| source | text | 是 | - | 来源
 |
| effective_from | timestamp with time zone | 是 | - | 生效起
 |
| effective_to | timestamp with time zone | 是 | - | 生效止
 |
| created_at | timestamp with time zone | 是 | now() | 创建时间
 |
| updated_at | timestamp with time zone | 是 | now() | 更新时间
 |

---

### calculation_parameters

**表注释**:

```

计算参数表

用途：
  存储计算方法的参数，支持全局、泵站级、设备级三个粒度。
  在5层参数优先级系统中处于第1层（全局）、第4层（泵站级）、第5层（设备级）。

参数粒度：
  - 全局参数：station_id=NULL, device_id=NULL（优先级最低，第1层）
  - 泵站级参数：station_id=X, device_id=NULL（优先级中等，第4层）
  - 设备级参数：station_id=X, device_id=Y（优先级最高，第5层）

优先级系统（5层）：
  1. 全局计算参数（calculation_parameters, device_id=NULL, station_id=NULL）
  2. 全局默认额定参数（global_default_rated_params）
  3. 设备额定参数（device_rated_params, device_id=X）
  4. 泵站级计算参数（calculation_parameters, station_id=X, device_id=NULL）
  5. 设备级计算参数（calculation_parameters, device_id=X）- 最高优先级

📚 参数字典（按计算方法分类）：

【流量计算参数】
  • alpha（流量系数）
    - 物理含义：功率权重指数，反映功率变化对流量分配的影响程度
    - 计算公式：Q_i = Q_total × (P_i^alpha × f_i^beta) / Σ(P_j^alpha × f_j^beta)
      其中：Q_i = 第i台泵的流量 (m³/h)
           Q_total = 总流量 (m³/h)
           P_i = 第i台泵的功率 (kW)
           f_i = 第i台泵的频率 (Hz)
           alpha = 功率权重指数 (无量纲)
           beta = 频率权重指数 (无量纲)
    - 单位：无量纲
    - 典型范围：0.5 ~ 1.5
    - 示例值：1.0
    - 用途：用于流量分配计算，反映功率对流量的影响
    - 是否可优化：是

  • beta（频率权重指数）
    - 物理含义：频率权重指数，反映频率变化对流量分配的影响程度
    - 计算公式：Q_i = Q_total × (P_i^alpha × f_i^beta) / Σ(P_j^alpha × f_j^beta)
      其中：Q_i = 第i台泵的流量 (m³/h)
           Q_total = 总流量 (m³/h)
           P_i = 第i台泵的功率 (kW)
           f_i = 第i台泵的频率 (Hz)
           alpha = 功率权重指数 (无量纲)
           beta = 频率权重指数 (无量纲)
    - 单位：无量纲
    - 典型范围：0.5 ~ 1.5
    - 示例值：1.0
    - 用途：用于流量分配计算，反映频率对流量的影响
    - 是否可优化：是

  • f_thr（频率阈值）
    - 物理含义：最小有效频率阈值，低于此频率的泵不参与流量分配
    - 单位：Hz
    - 典型范围：5 ~ 15
    - 示例值：10.0
    - 用途：过滤低频运行的泵，避免流量分配错误
    - 是否可优化：否

  • p_thr（功率阈值）
    - 物理含义：最小有效功率阈值，低于此功率的泵不参与流量分配
    - 单位：kW
    - 典型范围：1 ~ 10
    - 示例值：5.0
    - 用途：过滤低功率运行的泵，避免流量分配错误
    - 是否可优化：否

【扬程计算参数】
  • rho（流体密度）
    - 物理含义：流体的密度，用于扬程计算
    - 计算公式：H = (P_out - P_in) × 10^6 / (rho × g)
      其中：H = 扬程 (m)
           P_out = 出口压力 (MPa)
           P_in = 进口压力 (MPa)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
    - 单位：kg/m³
    - 典型值：1000（清水）
    - 示例值：1000.0
    - 用途：用于压力差转换为扬程
    - 是否可优化：否

  • g（重力加速度）
    - 物理含义：重力加速度，物理常数
    - 计算公式：H = (P_out - P_in) × 10^6 / (rho × g)
      其中：H = 扬程 (m)
           P_out = 出口压力 (MPa)
           P_in = 进口压力 (MPa)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
    - 单位：m/s²
    - 标准值：9.80665
    - 示例值：9.81
    - 用途：用于压力差转换为扬程
    - 是否可优化：否

  • b_H（扬程偏移量）
    - 物理含义：扬程计算的偏移量修正，用于校准测量误差
    - 计算公式：H_corrected = H_measured + b_H
      其中：H_corrected = 修正后扬程 (m)
           H_measured = 测量扬程 (m)
           b_H = 扬程偏移量 (m)
    - 单位：m
    - 典型范围：-5 ~ 5
    - 示例值：0.0
    - 用途：用于扬程计算的偏移量修正
    - 是否可优化：是

【转速计算参数】
  • f_ref（参考频率）
    - 物理含义：设备的参考频率，通常为额定频率
    - 计算公式：n = (f / f_ref) × n_ref × (1 - slip)
      其中：n = 转速 (rpm)
           f = 实际频率 (Hz)
           f_ref = 参考频率 (Hz)
           n_ref = 参考转速 (rpm)
           slip = 电机转差率 (无量纲)
    - 单位：Hz
    - 典型值：50（中国）、60（美国）
    - 示例值：50.0
    - 用途：用于转速计算的参考频率
    - 是否可优化：否

  • n_ref（参考转速）
    - 物理含义：设备在参考频率下的转速
    - 计算公式：n = (f / f_ref) × n_ref × (1 - slip)
      其中：n = 转速 (rpm)
           f = 实际频率 (Hz)
           f_ref = 参考频率 (Hz)
           n_ref = 参考转速 (rpm)
           slip = 电机转差率 (无量纲)
    - 单位：rpm
    - 典型值：1500（50Hz, 2极）、1000（50Hz, 3极）
    - 示例值：1500.0
    - 用途：用于转速计算的参考转速
    - 是否可优化：否

  • slip（电机转差率）
    - 物理含义：电机的转差率，反映实际转速与同步转速的差异
    - 计算公式：n = (f / f_ref) × n_ref × (1 - slip)
      其中：n = 转速 (rpm)
           f = 实际频率 (Hz)
           f_ref = 参考频率 (Hz)
           n_ref = 参考转速 (rpm)
           slip = 电机转差率 (无量纲)
    - 单位：无量纲
    - 典型范围：0.01 ~ 0.05
    - 示例值：0.02
    - 用途：用于转速计算，考虑电机转差
    - 是否可优化：否

  • pole_pairs（极对数）
    - 物理含义：电机的极对数，决定电机的同步转速
    - 计算公式：n_sync = (60 × f) / p
      其中：n_sync = 同步转速 (rpm)
           f = 频率 (Hz)
           p = 极对数 (无量纲)
    - 单位：无量纲
    - 典型值：2（对应1500rpm@50Hz）、3（对应1000rpm@50Hz）
    - 示例值：2
    - 用途：用于计算电机的同步转速
    - 是否可优化：否

  • calibration_a（标定斜率）
    - 物理含义：转速标定的线性关系斜率
    - 计算公式：n = a × f + b
      其中：n = 转速 (rpm)
           f = 频率 (Hz)
           a = 标定斜率 (rpm/Hz)
           b = 标定截距 (rpm)
    - 单位：rpm/Hz
    - 典型范围：20 ~ 40
    - 示例值：30.0
    - 用途：用于转速标定方法，建立频率与转速的线性关系
    - 是否可优化：是

  • calibration_b（标定截距）
    - 物理含义：转速标定的线性关系截距
    - 计算公式：n = a × f + b
      其中：n = 转速 (rpm)
           f = 频率 (Hz)
           a = 标定斜率 (rpm/Hz)
           b = 标定截距 (rpm)
    - 单位：rpm
    - 典型范围：-100 ~ 100
    - 示例值：0.0
    - 用途：用于转速标定方法，建立频率与转速的线性关系
    - 是否可优化：是

【效率计算参数】
  • eta_motor（电机效率）
    - 物理含义：电机的效率，反映电能转换为机械能的效率
    - 计算公式：eta = (rho × g × Q × H) / (P_e × eta_motor × 1000)
      其中：eta = 泵效率 (无量纲)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
           Q = 流量 (m³/s)
           H = 扬程 (m)
           P_e = 电功率 (kW)
           eta_motor = 电机效率 (无量纲)
    - 单位：无量纲
    - 典型范围：0.85 ~ 0.95
    - 示例值：0.92
    - 用途：用于效率计算，将电功率转换为轴功率
    - 是否可优化：否

  • eta_vfd（变频器效率）
    - 物理含义：变频器的效率，反映电能通过变频器的损耗
    - 单位：无量纲
    - 典型范围：0.95 ~ 0.98
    - 示例值：0.97
    - 用途：用于效率计算，考虑变频器的能量损耗
    - 是否可优化：否

  • eta_max（最大效率）
    - 物理含义：效率的最大值约束，用于限制计算结果
    - 单位：无量纲
    - 典型范围：0.80 ~ 0.90
    - 示例值：0.85
    - 用途：用于效率计算，限制计算结果的上限
    - 是否可优化：否

【压力系数化参数】
  • k_pin（进口压力系数）
    - 物理含义：进口压力的线性系数
    - 计算公式：P_in = k_pin × level + b_pin
      其中：P_in = 进口压力 (MPa)
           level = 液位 (m)
           k_pin = 进口压力系数 (MPa/m)
           b_pin = 进口压力偏移量 (MPa)
    - 单位：MPa/m
    - 典型范围：0.008 ~ 0.012
    - 示例值：0.00981
    - 用途：用于进口压力计算，建立液位与压力的线性关系
    - 是否可优化：是

  • b_pin（进口压力偏移量）
    - 物理含义：进口压力的偏移量
    - 计算公式：P_in = k_pin × level + b_pin
      其中：P_in = 进口压力 (MPa)
           level = 液位 (m)
           k_pin = 进口压力系数 (MPa/m)
           b_pin = 进口压力偏移量 (MPa)
    - 单位：MPa
    - 典型范围：-0.1 ~ 0.1
    - 示例值：0.0
    - 用途：用于进口压力计算，建立液位与压力的线性关系
    - 是否可优化：是

  • b0, b1, b2, b3（PIN_COEF_V1方法系数）
    - 物理含义：进口压力系数化方法的多项式系数
    - 计算公式：P_in(Pa) = b0 + b1 × (rho × g × level) - b2 × Q_st² - b3 × Q_st
      其中：P_in = 进口压力 (Pa)
           b0 = 常数项 (Pa)
           b1 = 液位系数 (无量纲)
           b2 = 流量平方系数 (Pa·s²/m⁶)
           b3 = 流量线性系数 (Pa·s/m³)
           rho = 流体密度 (kg/m³)
           g = 重力加速度 (m/s²)
           level = 液位 (m)
           Q_st = 泵站总流量 (m³/s)
    - 单位：b0 (Pa), b1 (无量纲), b2 (Pa·s²/m⁶), b3 (Pa·s/m³)
    - 典型值：b0=0, b1=1.0, b2=0, b3=0
    - 用途：用于进口压力系数化计算，考虑液位和流量的影响
    - 是否可优化：是

【扬程系数化参数】
  • a0, a1, a2, a3, a4, a5（HEAD_COEF_V1方法系数）
    - 物理含义：扬程系数化方法的多项式系数
    - 计算公式：H = a0 + a1 × head_out - a2 × level - a3 × Q_i² - a4 × Q_st² - a5 × Q_i
      其中：H = 扬程 (m)
           a0 = 常数项 (m)
           a1 = 出口水头系数 (无量纲)
           a2 = 液位系数 (无量纲)
           a3 = 单泵流量平方系数 (s²/m⁵)
           a4 = 泵站流量平方系数 (s²/m⁵)
           a5 = 单泵流量线性系数 (s/m²)
           head_out = 出口水头 (m) = (P_out × 10^6) / (rho × g)
           level = 液位 (m)
           Q_i = 单泵流量 (m³/s)
           Q_st = 泵站总流量 (m³/s)
    - 单位：a0 (m), a1 (无量纲), a2 (无量纲), a3 (s²/m⁵), a4 (s²/m⁵), a5 (s/m²)
    - 典型值：a0=0, a1=1.0, a2=1.0, a3=0, a4=0, a5=0
    - 用途：用于扬程系数化计算，考虑出口水头、液位和流量的影响
    - 是否可优化：是

数据来源：
  - 系统初始化：全局参数（rho, g, f_ref, n_ref, eta_motor, eta_vfd）
  - 参数优化：RLS算法优化（alpha, beta, calibration_a, calibration_b, k_pin, b_pin, b0-b3, a0-a5）
  - 手动配置：阈值参数（f_thr, p_thr, eta_max）

更新机制：
  - RLS算法自动更新可优化参数（is_optimizable=true）
  - 手动调整不可优化参数（is_optimizable=false）
  - 支持参数范围约束（param_min, param_max）

使用示例：
  -- 查询设备的流量计算参数
  SELECT param_name, param_value
  FROM calculation_parameters
  WHERE device_id = 1
    AND metric_key = 'pump_flow_rate'
    AND method_id = 'FLOW_RATE_METHOD_A'
  ORDER BY param_name;

  -- 查询全局默认参数
  SELECT param_name, param_value
  FROM calculation_parameters
  WHERE device_id IS NULL
    AND station_id IS NULL
  ORDER BY param_name;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('calculation_parameters_id_seq'::regclass) | 主键：计算参数记录的唯一标识符 |
| station_id | bigint | 是 | - | 泵站ID：参数所属的泵站ID，NULL表示全局参数 |
| device_id | bigint | 是 | - | 设备ID：参数所属的设备ID，NULL表示泵站级或全局参数 |
| metric_key | text | 否 | - | 指标键：参数所属的指标键（如pump_flow_rate, pump_head等） |
| method_id | text | 否 | - | 方法ID：参数所属的计算方法ID（如FLOW_RATE_METHOD_A, HEAD_MAIN等） |
| param_name | text | 否 | - | 参数名称：参数的标识符（如alpha, beta, rho, g等），详见表注释中的参数字典 |
| param_value | numeric | 否 | - | 参数值：参数的数值，具体含义取决于param_name，详见表注释中的参数字典 |
| param_type | text | 否 | 'float'::text | 参数类型：参数的数据类型（numeric, integer, boolean, string） |
| is_optimizable | boolean | 否 | true | 是否可优化：标记参数是否可以通过RLS算法自动优化（true=可优化, false=不可优化） |
| optimization_history | jsonb | 是 | - | 优化历史记录（JSON格式） |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| updated_at | timestamp with time zone | 否 | now() | 更新时间：记录最后更新的时间戳 |
| updated_by | text | 否 | 'system'::text | 更新者：更新记录的用户或系统标识（如RLS算法、手动调整） |
| confidence_score | numeric | 是 | 0.5 | 参数置信度（0-1），越高表示参数越可靠 |
| last_optimized_at | timestamp with time zone | 是 | - | 最后一次优化时间 |
| optimization_count | integer | 是 | 0 | 参数优化次数 |
| param_min | numeric | 是 | - | 参数最小值：参数的最小有效值，用于参数优化时的约束 |
| param_max | numeric | 是 | - | 参数最大值：参数的最大有效值，用于参数优化时的约束 |
| covariance_matrix | jsonb | 是 | - | - |
| rls_iterations | integer | 是 | 0 | - |
| last_p_trace | numeric | 是 | - | - |
| param_value_text | text | 是 | - | String type parameter value (used when param_type=string) |

---

## 维度表

### dim_stations

**表注释**:

```

泵站维度表

用途：
  存储泵站的基本信息，是系统的顶层组织单位。
  每个泵站包含多个设备（泵、管道、清水池等）。

业务逻辑：
  - 泵站是系统的顶层组织单位，用于组织和管理设备
  - 每个泵站有唯一的ID和名称
  - 支持活跃状态标记（is_active），用于过滤停用的泵站
  - 支持扩展信息（extra），存储时区、地理位置等额外信息

关键字段：
  - id：泵站ID，主键
  - name：泵站名称，唯一
  - extra：扩展信息（JSON格式），存储时区、地理位置等
  - is_active：活跃状态（true=活跃, false=停用）

数据来源：
  - 配置文件：从YAML配置文件导入（configs/dimensions.yaml）
  - 手动配置：通过SQL语句或API手动添加

更新机制：
  - UPSERT模式：根据name字段进行插入或更新
  - smart模式：保留已有的extra字段，只更新name和is_active
  - truncate模式：清空表后重新导入

使用示例：
  -- 查询所有活跃泵站
  SELECT id, name, extra
  FROM dim_stations
  WHERE is_active = true
  ORDER BY id;

  -- 查询泵站的时区信息
  SELECT name, extra->>'timezone' AS timezone
  FROM dim_stations
  WHERE id = 1;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | - | 泵站ID（PK）
 |
| name | text | 否 | - | 泵站名称
 |
| extra | jsonb | 是 | - | 额外信息（jsonb，建议包含 tz）
 |
| created_at | timestamp with time zone | 是 | now() | 创建时间
 |
| is_active | boolean | 否 | true | 活跃状态：标记泵站是否活跃（true=活跃, false=停用），用于过滤停用的泵站 |

---

### dim_devices

**表注释**:

```

设备维度表

用途：
  存储设备的基本信息，是系统的基本监控单位。
  每个设备属于一个泵站，有特定的设备类型和泵类型。

业务逻辑：
  - 设备是系统的基本监控单位，用于采集和计算数据
  - 每个设备属于一个泵站（station_id）
  - 支持多种设备类型（type）和泵类型（pump_type）
  - 支持活跃状态标记（is_active），用于过滤停用的设备

设备类型（type）：
  - pump：泵（主要监控对象）
  - main_pipeline：主管道（用于流量和压力监控）
  - clear_water_pool：清水池（用于液位监控）

泵类型（pump_type）：
  - variable_frequency：变频泵（支持频率调节）
  - constant_speed：定速泵（固定频率运行）
  - null：非泵设备（main_pipeline, clear_water_pool）

关键字段：
  - id：设备ID，主键
  - station_id：所属泵站ID，外键
  - name：设备名称，在泵站内唯一
  - type：设备类型（pump, main_pipeline, clear_water_pool）
  - pump_type：泵类型（variable_frequency, constant_speed, null）
  - is_active：活跃状态（true=活跃, false=停用）

数据来源：
  - 配置文件：从YAML配置文件导入（configs/dimensions.yaml）
  - 手动配置：通过SQL语句或API手动添加

更新机制：
  - UPSERT模式：根据station_id和name字段进行插入或更新
  - smart模式：保留已有的字段，只更新变化的字段
  - truncate模式：清空表后重新导入

使用示例：
  -- 查询泵站的所有活跃泵
  SELECT id, name, pump_type
  FROM dim_devices
  WHERE station_id = 1
    AND type = 'pump'
    AND is_active = true
  ORDER BY id;

  -- 查询所有变频泵
  SELECT d.id, s.name AS station_name, d.name AS device_name
  FROM dim_devices d
  JOIN dim_stations s ON d.station_id = s.id
  WHERE d.pump_type = 'variable_frequency'
    AND d.is_active = true
  ORDER BY s.id, d.id;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | - | 设备ID（PK）
 |
| station_id | bigint | 否 | - | 泵站ID
 |
| name | text | 否 | - | 设备名称（站内唯一）
 |
| type | text | 否 | - | 设备类型（pump 等）
 |
| pump_type | text | 是 | - | 泵类型（variable_frequency/soft_start 等）
 |
| extra | jsonb | 是 | - | 额外信息（jsonb）
 |
| created_at | timestamp with time zone | 是 | now() | 创建时间
 |
| is_active | boolean | 否 | true | 活跃状态：标记设备是否活跃（true=活跃, false=停用），用于过滤停用的设备 |

---

### dim_metric_config

**表注释**:

```

指标配置维度表

用途：
  存储指标的元数据配置，是系统的元数据基础。
  定义每个指标的单位、取值范围、数据类型、显示格式等。

业务逻辑：
  - 指标配置是系统的元数据基础，定义所有可用的指标
  - 每个指标有唯一的metric_key和ID
  - 支持单位转换（unit和unit_display）
  - 支持数据类型定义（value_type）
  - 支持取值范围约束（valid_min, valid_max）
  - 支持显示精度控制（fixed_decimals）

关键字段：
  - id：指标ID，主键
  - metric_key：指标键，唯一（如pump_flow_rate, pump_head）
  - unit：物理单位（如m³/h, m, kW）
  - unit_display：显示单位（如m³/h, 米, 千瓦）
  - value_type：数据类型（numeric, integer, boolean, string）
  - fixed_decimals：显示小数位数
  - valid_min：最小有效值
  - valid_max：最大有效值

使用场景：
  - 数据导入：根据metric_key查询指标ID，用于写入fact_measurements
  - API查询：根据metric_key查询指标元数据，用于前端显示
  - 数据验证：根据valid_min和valid_max验证数据有效性
  - 前端显示：根据unit_display和fixed_decimals格式化显示

数据来源：
  - SQL脚本：从SQL脚本导入（scripts/sql/migrations/）
  - 配置文件：从YAML配置文件导入（configs/metrics.yaml）
  - 手动配置：通过SQL语句或API手动添加

更新机制：
  - UPSERT模式：根据metric_key字段进行插入或更新
  - 保留已有的valid_min和valid_max：避免覆盖手动调整的取值范围
  - 更新unit、unit_display、value_type、fixed_decimals

使用示例：
  -- 查询指标ID
  SELECT id
  FROM dim_metric_config
  WHERE metric_key = 'pump_flow_rate'
  LIMIT 1;

  -- 查询所有流量相关指标
  SELECT id, metric_key, unit, unit_display
  FROM dim_metric_config
  WHERE metric_key LIKE '%flow%'
  ORDER BY metric_key;

  -- 查询指标的取值范围
  SELECT metric_key, valid_min, valid_max
  FROM dim_metric_config
  WHERE metric_key = 'pump_efficiency'
  LIMIT 1;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('dim_metric_config_id_seq'::regclass) | 指标ID（PK）
 |
| metric_key | text | 否 | - | 指标键（唯一，如 pump_frequency）
 |
| unit | text | 否 | - | 单位（如 Hz、kW、A）
 |
| unit_display | text | 是 | - | 单位显示
 |
| decimals_policy | text | 是 | 'as_is'::text | 小数策略（as_is 等）
 |
| fixed_decimals | smallint | 是 | - | 固定小数位（可选）
 |
| value_type | text | 是 | - | 值类型（number 等）
 |
| valid_min | numeric | 是 | - | 有效最小值
 |
| valid_max | numeric | 是 | - | 有效最大值
 |
| created_at | timestamp with time zone | 是 | now() | 创建时间
 |
| updated_at | timestamp with time zone | 是 | now() | 更新时间
 |

---

## 事实表

### fact_measurements

**表注释**:

```

事实测量表（TimescaleDB Hypertable）

用途：
  存储所有时间序列测量数据，包括原始数据和计算数据。
  采用秒级时间对齐，支持高效的时间范围查询和聚合分析。

分区策略：
  - 时间分区：按 ts_bucket 字段分区，Chunk时间间隔为1周
  - 空间分区：按 device_id 字段哈希分区，分区数量为8
  - 分区列：ts_bucket（时间维度）, device_id（空间维度）
  - 优势：支持分区裁剪，提高查询性能

质量管理机制：
  - quality_status：质量状态（0=正常, 1=可疑, 2=错误, 3=缺失）
  - quality_codes：质量码数组，记录所有检测到的质量问题
  - quality_type：质量类型（raw=原始数据, calculated=计算数据, corrected=修正数据）
  - quality_meta：质量元数据（JSON格式），存储质量检查的详细信息

📚 质量码字典：

【物理边界检查】
  • 101（物理边界违规）
    - 含义：测量值超出物理可能的范围
    - 示例：负流量、负功率、超过100%的效率
    - 处理：标记为错误，不参与计算

【统计异常检查】
  • 111（尖峰检测）
    - 含义：测量值出现异常尖峰，与前后值差异过大
    - 检测方法：|value - median(window)| > threshold × std(window)
    - 处理：标记为可疑，可选择性过滤

  • 121（平线检测）
    - 含义：测量值长时间保持不变，可能是传感器故障
    - 检测方法：std(window) < threshold
    - 处理：标记为可疑，可选择性过滤

【逻辑一致性检查】
  • 401（状态矛盾）
    - 含义：设备状态与测量值不一致
    - 示例：设备停机但有流量、设备运行但无功率
    - 处理：标记为可疑，需人工审核

【电气参数检查】
  • 701（功率因数异常）
    - 含义：功率因数超出合理范围
    - 检测方法：power_factor < 0.5 或 power_factor > 1.0
    - 处理：标记为可疑，可选择性过滤

  • 702（三相不平衡）
    - 含义：三相电流或电压不平衡度超出限值
    - 检测方法：imbalance > threshold（通常5%）
    - 处理：标记为可疑，可能影响设备寿命

【计数器检查】
  • 751（计数器单调性违规）
    - 含义：累计量计数器出现回退
    - 示例：累计电量减少、累计流量减少
    - 处理：标记为错误，需重新计算增量

数据来源：
  - CSV导入：历史数据批量导入
  - 计算流程：计算指标（pump_flow_rate, pump_head, pump_speed, pump_efficiency等）
  - API写入：实时数据写入
  - 数据补全：缺失数据补全

查询优化建议：
  - 必须包含时间范围过滤（WHERE ts_bucket BETWEEN ... AND ...）
  - 利用分区裁剪（WHERE device_id = ...）
  - 使用索引（idx_fact_measurements_device_metric, idx_fact_measurements_quality）
  - 避免全表扫描

使用示例：
  -- 查询设备在指定时间范围内的测量数据（带质量过滤）
  SELECT ts_bucket, metric_id, value_numeric, quality_status
  FROM fact_measurements
  WHERE device_id = 1
    AND ts_bucket BETWEEN '2024-01-01' AND '2024-01-02'
    AND quality_status IN (0, 1)  -- 只查询正常和可疑数据
  ORDER BY ts_bucket;

  -- 查询设备的流量数据（过滤质量码）
  SELECT ts_bucket, value_numeric
  FROM fact_measurements
  WHERE device_id = 1
    AND metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = 'pump_flow_rate')
    AND ts_bucket BETWEEN '2024-01-01' AND '2024-01-02'
    AND (quality_codes IS NULL OR NOT (101 = ANY(quality_codes)))  -- 排除物理边界违规
  ORDER BY ts_bucket;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | - | ID（PK）
 |
| station_id | bigint | 否 | - | 泵站ID
 |
| device_id | bigint | 否 | - | 设备ID
 |
| metric_id | bigint | 否 | - | 指标ID
 |
| ts_raw | timestamp with time zone | 否 | - | 原始时间（建议 UTC）
 |
| ts_bucket | timestamp with time zone | 否 | - | 整秒对齐时间
 |
| value | numeric | 否 | - | 数值
 |
| source_hint | text | 是 | - | 来源提示
 |
| inserted_at | timestamp with time zone | 是 | now() | 插入时间
 |
| quality_status | smallint | 否 | 0 | 数据质量状态码：0=正常；>0 为异常码（参见 quality_code_dict）。 |
| quality_type | text | 是 | - | 数据质量中文标签（如：越界、异常跳变、平台期、状态矛盾、功率因数异常、液位流量守恒异常等）。 |
| quality_meta | jsonb | 是 | - | 质量判定元数据（JSON）：阈值、证据、参与信号、相位、规则版本等。 |
| quality_codes | ARRAY | 是 | '{}'::integer[] | 质量码数组：记录所有检测到的质量问题的代码数组（INTEGER[]）。
质量码字典：
  101 - 物理边界违规：测量值超出物理可能的范围
  111 - 尖峰检测：测量值出现异常尖峰，与前后... |

---

## 配置表

### calculation_method_registry

**表注释**:

```
计算方法注册表

用途：
  记录每个指标的所有可用计算方法，支持计算编排和方法选择

业务逻辑：
  - 注册所有可用的计算方法
  - 每个方法有优先级，按优先级顺序尝试
  - 支持方法启用/禁用控制

方法分类：
  - direct：直接测量（从传感器直接获取）
  - formula：公式计算（基于其他指标计算）
  - curve：曲线拟合（基于泵特性曲线）
  - regression：回归模型（基于历史数据训练）

关键字段：
  - metric_id：指标ID
  - method_name：方法名称（如 "formula_power_from_current"）
  - method_type：方法类型（direct/formula/curve/regression）
  - priority：优先级（数值越小优先级越高）
  - enabled：是否启用（true/false）
  - description：方法描述

使用场景：
  - 计算编排时选择计算方法
  - 方法优先级管理
  - 方法启用/禁用控制

使用示例：
  -- 查询某指标的所有计算方法（按优先级）
  SELECT *
  FROM calculation_method_registry
  WHERE metric_id = 14
    AND enabled = true
  ORDER BY priority;

  -- 注册新的计算方法
  INSERT INTO calculation_method_registry (metric_id, method_name, method_type, priority, enabled, description)
  VALUES (14, 'formula_flow_from_level', 'formula', 10, true, '基于液位计算流量');

注意事项：
  - 优先级数值越小优先级越高
  - 计算编排时按优先级顺序尝试方法
  - 禁用的方法不会被尝试

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| method_id | text | 否 | - | 方法ID：计算方法的唯一标识符（如FLOW_RATE_METHOD_A, HEAD_MAIN等） |
| metric_key | text | 否 | - | 指标键：方法所属的指标键（如pump_flow_rate, pump_head等） |
| method_name | text | 否 | - | 方法名称：计算方法的中文名称 |
| method_code | text | 否 | - | 方法代码：计算方法的Python函数名 |
| priority | integer | 否 | 100 | 优先级：方法的优先级，数值越小优先级越高 |
| dependencies | ARRAY | 否 | '{}'::text[] | 依赖的指标列表（metric_key数组） |
| conditions | jsonb | 否 | '{}'::jsonb | 使用条件（JSON）：如{"running_count": {"min": 2}, "device_type": "pump"} |
| formula_ref | text | 是 | - | - |
| accuracy_level | text | 否 | 'medium'::text | 精度等级：high（高精度）/medium（中等）/low（低精度） |
| is_enabled | boolean | 否 | true | - |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| updated_at | timestamp with time zone | 否 | now() | 更新时间：记录最后更新的时间戳 |
| allowed_device_types | ARRAY | 否 | '{}'::text[] | - |

---

### metric_calculation_order

**表注释**:

```
指标计算顺序表：记录指标的依赖关系和计算顺序
```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| metric_key | text | 否 | - | 指标键：指标的唯一标识符 |
| depends_on | ARRAY | 否 | '{}'::text[] | 依赖指标：当前指标依赖的其他指标键数组 |
| priority | integer | 否 | 100 | - |
| order_index | integer | 否 | - | 拓扑排序后的计算顺序（从0开始） |
| is_circular | boolean | 否 | false | 是否涉及循环依赖 |
| circular_group | text | 是 | - | 循环依赖组ID（用于标识哪些指标形成循环） |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| updated_at | timestamp with time zone | 否 | now() | 更新时间：记录最后更新的时间戳 |
| updated_by | text | 否 | 'system'::text | - |

---

### metric_quality_rules

**表注释**:

```
指标质量规则表

用途：
  配置指标的质量检查规则阈值，支持按站点/设备/指标粒度覆盖

业务逻辑：
  - 支持3级粒度：全局 → 站点级 → 设备级
  - 优先级：设备级 > 站点级 > 全局级
  - 手工配置优先于自动基线

📚 规则参数字典（9类）：

【数值区间】
  • value_min / value_max (double precision)
    - 用途：物理越界检查（质量码101）
    - 物理含义：测量值的合理区间
    - 示例：流量 value_min=0, value_max=500
    - 注意：NULL表示不检查该边界

【跳变检查】
  • spike_abs (double precision)
    - 用途：异常跳变检查（质量码111）
    - 物理含义：相邻秒绝对差值阈值
    - 计算公式：|value(t) - value(t-1)| > spike_abs
    - 示例：流量 spike_abs=50（相邻秒差值不超过50）

【变化率检查】
  • roc_abs (double precision)
    - 用途：变化率异常检查（质量码112）
    - 物理含义：绝对变化率阈值（单位/秒）
    - 计算公式：|value(t) - value(t-1)| / Δt > roc_abs
    - 示例：流量 roc_abs=10（每秒变化不超过10）

  • roc_ratio (double precision)
    - 用途：变化率异常检查（质量码112）
    - 物理含义：相对变化率阈值（百分比）
    - 计算公式：|value(t) - value(t-1)| / |value(t-1)| > roc_ratio
    - 示例：流量 roc_ratio=0.5（变化率不超过50%）

【平台期检查】
  • flatline_secs (int)
    - 用途：平台期检查（质量码121）
    - 物理含义：平台期持续秒数阈值
    - 示例：flatline_secs=60（连续60秒不变视为平台期）

  • flatline_eps (double precision)
    - 用途：平台期检查（质量码121）
    - 物理含义：平台期容差（标准差阈值）
    - 示例：flatline_eps=0.01（标准差小于0.01视为不变）

  • flatline_delta (double precision)
    - 用途：平台期检查（质量码121）
    - 物理含义：平台期最大变化量（极差阈值）
    - 示例：flatline_delta=0.1（极差小于0.1视为不变）

【饱和检查】
  • saturation_min / saturation_max (double precision)
    - 用途：饱和检查（质量码131/132）
    - 物理含义：接近量程边界的阈值
    - 示例：压力 saturation_min=0.1, saturation_max=9.9（量程0-10）

【噪声检查】
  • noise_stddev_max (double precision)
    - 用途：高噪声检查（质量码201）
    - 物理含义：短窗标准差上限
    - 示例：noise_stddev_max=5.0（短窗标准差超过5.0视为高噪声）

使用场景：
  - 质量标注窗口（sp_mark_quality_window）
  - 质量规则配置管理
  - 自动基线调整

使用示例：
  -- 查询某指标的质量规则（按优先级）
  SELECT *
  FROM metric_quality_rules
  WHERE metric_id = 14
  ORDER BY device_id NULLS LAST, station_id NULLS LAST;

  -- 插入设备级规则
  INSERT INTO metric_quality_rules (device_id, metric_id, value_min, value_max, spike_abs)
  VALUES (121, 14, 0, 500, 50);

  -- 更新全局规则
  UPDATE metric_quality_rules
  SET value_min = 0, value_max = 600
  WHERE metric_id = 14
    AND station_id IS NULL
    AND device_id IS NULL;

注意事项：
  - 优先级：设备级 > 站点级 > 全局级
  - NULL值表示不检查该规则
  - 手工配置优先于自动基线

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| rule_id | bigint | 否 | nextval('metric_quality_rules_rule_id_seq'::reg... | - |
| station_id | bigint | 是 | - | 站点ID（可空，表示全站通用默认）。 |
| device_id | bigint | 是 | - | 设备ID（可空，表示该站点通用或全局默认）。 |
| metric_id | bigint | 否 | - | 指标ID（必填）。 |
| value_min | double precision | 是 | - | 越界下限（可空则使用自动基线 p05）。 |
| value_max | double precision | 是 | - | 越界上限（可空则使用自动基线 p95）。 |
| spike_abs | double precision | 是 | - | 异常跳变阈值（相邻秒绝对差）。 |
| roc_abs | double precision | 是 | - | 变化率绝对差阈值。 |
| roc_ratio | double precision | 是 | - | 相对变化率阈值（\|Δx/prev\|）。 |
| flatline_secs | integer | 是 | - | 平台期判定最小持续秒数。 |
| flatline_eps | double precision | 是 | - | 平台期窗口内标准差上限。 |
| flatline_delta | double precision | 是 | - | 平台期窗口内最大-最小差上限。 |
| saturation_min | double precision | 是 | - | 下饱和阈值。 |
| saturation_max | double precision | 是 | - | 上饱和阈值。 |
| noise_stddev_max | double precision | 是 | - | 短窗噪声标准差上限。 |
| remark | text | 是 | - | 中文备注/规则说明。 |
| updated_at | timestamp with time zone | 是 | now() | 更新时间：记录最后更新的时间戳 |
| updated_by | text | 是 | - | - |

---

### quality_code_dict

**表注释**:

```
质量码字典表

用途：
  映射质量状态码（数值）到中文标签、类别、严重度、描述

业务逻辑：
  - 定义所有质量检查规则对应的质量码
  - 支持质量报表的分组和统计
  - 支持质量问题的严重度分级

📚 质量码完整字典（15个）：

【数值特性】（6个）
  • 101 - 越界
    - 严重度：3（高）
    - 检查逻辑：value < valid_min OR value > valid_max
    - 示例：流量值为-10（负值越界）

  • 111 - 异常跳变
    - 严重度：3（高）
    - 检查逻辑：abs(value - prev_value) > spike_abs
    - 示例：流量从100突变到500

  • 112 - 变化率异常
    - 严重度：3（高）
    - 检查逻辑：abs(value - prev_value) / prev_value > roc_ratio
    - 示例：流量变化率超过50%

  • 121 - 平台期
    - 严重度：2（中）
    - 检查逻辑：连续N秒值不变（可能传感器卡死）
    - 示例：流量连续60秒保持100不变

  • 131 - 上饱和
    - 严重度：3（高）
    - 检查逻辑：value >= saturation_max（接近量程上限）
    - 示例：压力值持续在量程上限

  • 132 - 下饱和
    - 严重度：3（高）
    - 检查逻辑：value <= saturation_min（接近量程下限）
    - 示例：流量值持续在量程下限

【噪声/完整性】（1个）
  • 201 - 高噪声
    - 严重度：2（中）
    - 检查逻辑：短窗标准差 > noise_stddev_max
    - 示例：流量值在短时间内剧烈波动

【跨指标/跨设备】（1个）
  • 401 - 状态矛盾
    - 严重度：4（极高）
    - 检查逻辑：运行状态与测量值矛盾
    - 示例：运行状态=0但功率>0，或运行状态=1但功率≈0

【时间一致性】（2个）
  • 501 - 时间漂移
    - 严重度：2（中）
    - 检查逻辑：ts_raw 与 ts_bucket 偏差过大
    - 示例：原始时间与对齐时间相差超过5秒

  • 502 - 重复秒
    - 严重度：2（中）
    - 检查逻辑：同一秒出现多条记录
    - 示例：同一设备同一指标在同一秒有2条数据

【机理/物理】（5个）
  • 701 - 功率因数异常
    - 严重度：3（高）
    - 检查逻辑：power_factor < 0 OR power_factor > 1
    - 示例：功率因数为1.2（超出物理范围）

  • 711 - 液位流量守恒异常
    - 严重度：4（极高）
    - 检查逻辑：dLevel/dt 与流量不一致（违反能量守恒）
    - 示例：液位上升但流量为负

  • 721 - 相似定律异常
    - 严重度：3（高）
    - 检查逻辑：与变频相似定律偏差过大
    - 示例：频率变化50%但流量变化10%（不符合相似定律）

  • 731 - 泵曲线偏差
    - 严重度：3（高）
    - 检查逻辑：与泵特性曲线偏差过大
    - 示例：实际扬程与曲线预测值偏差超过20%

  • 751 - 计数器非单调
    - 严重度：3（高）
    - 检查逻辑：累计量出现回退
    - 示例：累计电量从1000降到900

使用场景：
  - 质量检查规则配置
  - 质量报表生成
  - 质量问题分析

使用示例：
  -- 查询所有质量码
  SELECT code, label_zh, category, severity, description
  FROM quality_code_dict
  ORDER BY code;

  -- 查询高严重性质量问题
  SELECT *
  FROM quality_code_dict
  WHERE severity >= 3;

注意事项：
  - 质量码与 fact_measurements.quality_status 字段对应
  - 严重度范围：1（低）到 4（极高）

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| code | smallint | 否 | - | 质量码：质量问题的代码（如101, 111, 121等） |
| label_zh | text | 否 | - | 中文标签（如：越界、异常跳变、平台期、状态矛盾、功率因数异常等）。 |
| category | text | 是 | - | 类别：质量问题的类别（physical, statistical, logical, electrical等） |
| severity | integer | 是 | - | 严重程度：质量问题的严重程度（low, medium, high, critical） |
| description | text | 是 | - | 描述：质量码的详细描述 |

---

## 日志表

### calculation_failures_log

**表注释**:

```
计算失败日志表：记录所有计算和验证失败的情况
```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('calculation_failures_log_id_seq'::regc... | 主键：失败日志记录的唯一标识符 |
| station_id | bigint | 否 | - | - |
| device_id | bigint | 否 | - | 设备ID：失败所属的设备ID |
| metric_key | text | 否 | - | 指标键：失败所属的指标键 |
| ts_second | timestamp with time zone | 否 | - | - |
| method_id | text | 是 | - | 方法ID：失败所属的计算方法ID |
| error_type | text | 否 | - | 错误类型：missing_data（缺失数据）/validation_failed（验证失败）/calculation_error（计算错误）/circular_dependency（循环依赖） |
| error_message | text | 否 | - | 错误消息：失败的详细错误消息 |
| error_details | jsonb | 是 | - | 错误详情（JSON格式）：包含更多上下文信息 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |

---

### completion_audit

**表注释**:

```
补全审计表

用途：
  记录每次数据补全运行的审计信息，提供结构化对账与统计摘要

业务逻辑：
  - 每次补全运行生成一条审计记录
  - 记录补全前后的数据质量指标（覆盖率、缺失点数、最大缺口）
  - 统计各种补全方法的使用次数
  - 记录拒绝计数和组一致性审计信息

关键字段：
  - run_id：运行ID（唯一，关联 completion_runs 表）
  - coverage_before/coverage_after：补全前后的数据覆盖率
  - missing_before/missing_after：补全前后的缺失点数
  - max_gap_before_sec/max_gap_after_sec：补全前后的最大缺口（秒）
  - count_ffill：前向填充次数
  - count_mean：均值填充次数
  - count_reg：回归填充次数
  - count_curve：曲线填充次数
  - count_skipped_long_gap：跳过的长缺口次数
  - startup_drop_ratio：启停落点剔除比例
  - rejects_counts：拒绝计数（JSONB格式，按类别统计）
  - thresholds_snapshot_ref：阈值快照引用（文本）
  - group_consistency：组一致性审计（JSONB格式）
  - audit_time：审计时间

数据来源：
  - 代码位置：app/services/device_running_job.py
  - 写入时机：补全运行完成后

使用场景：
  - 补全效果评估
  - 补全方法统计
  - 数据质量趋势分析

使用示例：
  -- 查询补全效果审计
  SELECT
      run_id,
      coverage_before,
      coverage_after,
      (coverage_after - coverage_before) AS coverage_improvement,
      missing_before,
      missing_after,
      count_ffill + count_mean + count_reg + count_curve AS total_filled
  FROM completion_audit
  ORDER BY audit_time DESC;

注意事项：
  - 每个 run_id 只有一条记录（UNIQUE约束）
  - 与 completion_runs 表通过 run_id 关联（ON DELETE CASCADE）

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('completion_audit_id_seq'::regclass) | 主键：审计记录的唯一标识符 |
| run_id | bigint | 否 | - | 运行ID：关联的补全运行ID |
| coverage_before | numeric | 是 | - | 补全前覆盖率
 |
| coverage_after | numeric | 是 | - | 补全后覆盖率
 |
| missing_before | bigint | 是 | - | 补全前缺失点数
 |
| missing_after | bigint | 是 | - | 补全后缺失点数
 |
| max_gap_before_sec | integer | 是 | - | 补全前最大缺口（秒）
 |
| max_gap_after_sec | integer | 是 | - | 补全后最大缺口（秒）
 |
| count_ffill | integer | 是 | - | 前向填充次数
 |
| count_mean | integer | 是 | - | 均值填充次数
 |
| count_reg | integer | 是 | - | 回归填充次数
 |
| count_curve | integer | 是 | - | 曲线填充次数
 |
| count_skipped_long_gap | integer | 是 | - | 跳过的长缺口次数
 |
| startup_drop_ratio | numeric | 是 | - | 启停落点剔除比例
 |
| rejects_counts | jsonb | 是 | - | 拒绝计数（jsonb，按类别）
 |
| thresholds_snapshot_ref | text | 是 | - | 阈值快照引用（文本）
 |
| group_consistency | jsonb | 是 | - | 组一致性审计（jsonb）
 |
| audit_time | timestamp with time zone | 否 | now() | 审计时间
 |

---

### completion_failures

**表注释**:

```
补全失败清单表

用途：
  记录数据补全过程中的失败记录，便于问题排查和分析

业务逻辑：
  - 逐条记录补全失败的详细信息
  - 提供失败原因代码和证据URI
  - 建议修复动作

关键字段：
  - run_id：所属运行ID（关联 completion_runs 表）
  - object_key：失败对象键（JSONB格式：{station_id, device_id, metric_id}）
  - gap_id：缺口段ID
  - reason_code：失败原因代码
  - evidence_uri：证据URI（如日志文件路径）
  - suggested_action：建议动作（如"检查参数配置"、"补充额定参数"）
  - created_at：创建时间

数据来源：
  - 代码位置：补全任务失败时写入
  - 写入时机：补全方法失败时

使用场景：
  - 补全失败原因分析
  - 问题排查和修复
  - 失败模式统计

使用示例：
  -- 查询失败原因分布
  SELECT reason_code, COUNT(*) AS count
  FROM completion_failures
  GROUP BY reason_code
  ORDER BY count DESC;

  -- 查询某次运行的失败记录
  SELECT *
  FROM completion_failures
  WHERE run_id = 12345
  ORDER BY created_at;

注意事项：
  - 与 completion_runs 表通过 run_id 关联（ON DELETE CASCADE）
  - object_key 使用 JSONB 格式存储，便于灵活查询

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('completion_failures_id_seq'::regclass) | 主键：失败记录的唯一标识符 |
| run_id | bigint | 否 | - | 运行ID：关联的补全运行ID |
| object_key | jsonb | 是 | - | 对象键（jsonb：station_id/device_id/metric_id）
 |
| gap_id | bigint | 是 | - | 缺口段ID
 |
| reason_code | text | 是 | - | 失败原因代码
 |
| evidence_uri | text | 是 | - | 证据URI
 |
| suggested_action | text | 是 | - | 建议动作
 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |

---

### completion_runs

**表注释**:

```
用途: 数据表：public.completion_runs（用途待补充）
使用方法: 常规SELECT/过滤/排序
-- 示例：读取前100行
SELECT * FROM public.completion_runs LIMIT 100;

-- 示例：按维度过滤
SELECT * FROM public.completion_runs
WHERE station_id = :station_id AND device_id = :device_id
ORDER BY 1
LIMIT 100;

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| run_id | bigint | 否 | nextval('completion_runs_run_id_seq'::regclass) | 运行ID
 |
| station_id | bigint | 否 | - | 泵站ID：运行所属的泵站ID |
| device_id | bigint | 否 | - | 设备ID：运行所属的设备ID |
| start_ts | timestamp with time zone | 否 | - | 运行时间窗起（timestamptz）
 |
| end_ts | timestamp with time zone | 否 | - | 运行时间窗止（timestamptz）
 |
| code_version | text | 是 | - | 代码版本标识（如 git 哈希）
 |
| imputation_version | text | 是 | - | 补全过程版本/算法版本
 |
| config_snapshot | jsonb | 是 | - | 配置快照（jsonb）
 |
| thresholds_snapshot | jsonb | 是 | - | 阈值快照（jsonb）
 |
| rows_read | bigint | 是 | - | 读取的事实点数量
 |
| duration_ms | integer | 是 | - | 运行耗时（毫秒）
 |
| steps_total | integer | 是 | - | 步骤数量
 |
| rerun_policy | text | 是 | - | 复跑策略：append/overwrite/skip
 |
| parent_run_id | bigint | 是 | - | 父运行ID（复跑来源）
 |
| superseded_by_run_id | bigint | 是 | - | 被替代运行ID（被后续运行覆盖）
 |
| idempotency_key | text | 是 | - | 幂等键（避免重复写入）
 |
| group_context | jsonb | 是 | - | 泵组上下文（jsonb）
 |
| status_reason | text | 是 | - | 状态原因摘要
 |
| error_code | text | 是 | - | 错误代码摘要
 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |

---

### completion_steps

**表注释**:

```
补全步骤表

用途：
  记录数据补全过程中的每个步骤详情，提供段级审计

业务逻辑：
  - 记录每个缺口的处理过程
  - 记录尝试的补全方法和回退路径
  - 记录残差统计信息

关键字段：
  - run_id：所属运行ID（关联 completion_runs 表）
  - gap_start_ts/gap_end_ts：缺口起止时间
  - gap_len_sec：缺口长度（秒）
  - gap_class：缺口分类（short/medium/long）
  - methods_tried：尝试的方法列表（JSONB数组）
  - fallback_path：回退路径（如 "curve -> reg -> mean"）
  - residual_stats：残差统计（JSONB格式：{mean, std, max}）
  - created_at：创建时间

数据来源：
  - 代码位置：app/services/device_running_job.py
  - 写入时机：每个缺口处理完成后

使用场景：
  - 补全方法使用情况统计
  - 补全质量分析
  - 回退路径分析

使用示例：
  -- 查询补全方法使用情况
  SELECT
      fallback_path,
      COUNT(*) AS count,
      AVG(gap_len_sec) AS avg_gap_len
  FROM completion_steps
  GROUP BY fallback_path
  ORDER BY count DESC;

  -- 查询某次运行的步骤详情
  SELECT *
  FROM completion_steps
  WHERE run_id = 12345
  ORDER BY gap_start_ts;

注意事项：
  - 与 completion_runs 表通过 run_id 关联（ON DELETE CASCADE）
  - methods_tried 和 residual_stats 使用 JSONB 格式存储

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('completion_steps_id_seq'::regclass) | 主键：步骤记录的唯一标识符 |
| run_id | bigint | 否 | - | 运行ID：关联的补全运行ID |
| device_id | bigint | 否 | - | 设备ID：步骤所属的设备ID |
| metric_id | bigint | 是 | - | 指标ID：步骤所属的指标ID |
| gap_id | bigint | 是 | - | 缺口段ID
 |
| gap_start_ts | timestamp with time zone | 是 | - | 缺口开始时间
 |
| gap_end_ts | timestamp with time zone | 是 | - | 缺口结束时间
 |
| gap_len_sec | integer | 是 | - | 缺口时长（秒）
 |
| gap_class | text | 是 | - | 缺口分类（short/medium/long/in_startstop）
 |
| in_startstop_window | boolean | 是 | - | 是否位于启停窗口内
 |
| methods_tried | jsonb | 是 | - | 尝试的方法列表（jsonb）
 |
| fallback_path | text | 是 | - | 回退路径
 |
| confidence_reason | ARRAY | 是 | - | 置信理由（数组）
 |
| residual_stats | jsonb | 是 | - | 残差统计（jsonb，可选）
 |
| step_duration_ms | integer | 是 | - | 步骤耗时（毫秒）
 |
| rows_considered | bigint | 是 | - | 考虑的点数量
 |
| data_source | text | 是 | - | 数据来源（original/derived）
 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |

---

### optimization_history

**表注释**:

```
优化历史表：记录参数优化的历史
```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('optimization_history_id_seq'::regclass) | 主键：优化历史记录的唯一标识符 |
| station_id | bigint | 否 | - | - |
| device_id | bigint | 否 | - | 设备ID：优化所属的设备ID |
| metric_key | text | 否 | - | 指标键：优化所属的指标键 |
| optimization_type | text | 否 | - | 优化类型：rls（递归最小二乘）/curve（特性曲线优化）/manual（手动调整） |
| params_before | jsonb | 否 | - | 优化前的参数（JSON格式） |
| params_after | jsonb | 否 | - | 优化后的参数（JSON格式） |
| improvement_score | numeric | 是 | - | 改进分数：如RMS误差降低百分比 |
| data_window_start | timestamp with time zone | 否 | - | 优化使用的数据窗口起始时间 |
| data_window_end | timestamp with time zone | 否 | - | 优化使用的数据窗口结束时间 |
| data_points_count | integer | 是 | - | - |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| created_by | text | 否 | 'system'::text | - |
| method_id | text | 是 | - | 方法ID：优化所属的计算方法ID |
| covariance_matrix | jsonb | 是 | - | - |
| rls_state | jsonb | 是 | - | - |

---

### quality_diagnosis_log

**表注释**:

```
质量诊断日志表

用途：
  记录质量标注过程的诊断信息，支持性能分析和问题排查

业务逻辑：
  - 记录每个质量标注窗口的开始/结束时间
  - 记录每个阶段的执行时间和影响行数
  - 支持3级诊断（off/brief/full）

关键字段：
  - window_start/window_end：标注窗口起止时间
  - station_id/device_id：站点/设备ID（可选过滤）
  - stage：阶段名称（如 "update_101"、"update_111"）
  - level：日志级别（INFO/WARNING/ERROR）
  - diag_level：诊断级别（off/brief/full）
  - duration_ms：执行时间（毫秒）
  - rows_affected：影响行数
  - detail：详细信息（JSONB格式）
  - created_at：创建时间

数据来源：
  - 代码位置：sp_mark_quality_window_vfast_diag 存储过程
  - 写入时机：质量标注过程中

使用场景：
  - 质量标注过程追踪
  - 性能分析
  - 问题排查

使用示例：
  -- 查询质量标注错误日志
  SELECT *
  FROM quality_diagnosis_log
  WHERE level = 'ERROR'
  ORDER BY created_at DESC;

  -- 查询某窗口的性能统计
  SELECT
      stage,
      duration_ms,
      rows_affected,
      CASE WHEN rows_affected > 0 THEN duration_ms::numeric / rows_affected ELSE 0 END AS ms_per_row
  FROM quality_diagnosis_log
  WHERE window_start = '2025-09-01T00:00:00Z'
    AND window_end = '2025-09-02T00:00:00Z'
  ORDER BY duration_ms DESC;

注意事项：
  - diag_level 控制日志详细程度（off不记录、brief记录摘要、full记录详情）
  - detail 字段使用 JSONB 格式存储，便于灵活查询

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('quality_diagnosis_log_id_seq'::regclass) | 主键：诊断日志记录的唯一标识符 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| window_start | timestamp with time zone | 否 | - | 诊断窗口起（UTC，半开区间 [start,end)） |
| window_end | timestamp with time zone | 否 | - | 诊断窗口止（UTC，半开区间 [start,end)） |
| station_id | bigint | 是 | - | 可选：站点ID |
| device_id | bigint | 是 | - | 设备ID：诊断所属的设备ID |
| stage | text | 否 | - | 流程阶段（如 compute/merge/mark 等） |
| level | text | 否 | 'INFO'::text | 阶段内级别/粒度（实现自定义） |
| message | text | 是 | - | 摘要信息（文本） |
| detail | jsonb | 是 | - | 结构化细节（JSONB） |
| diag_level | text | 否 | 'off'::text | 诊断详略级别：off\|brief\|full |
| run_id | text | 是 | - | 运行ID（用于一次调用/作业的关联） |

---

### quality_eval_by_device_metric

**表注释**:

```
质量评估统计表

用途：
  按窗口/设备/指标生成质量码分布统计，支持质量报表生成

业务逻辑：
  - 离线统计，由 sp_generate_quality_eval_by_device_metric 存储过程生成
  - 统计每个质量码的行数和占比
  - 支持质量趋势分析

关键字段：
  - window_start/window_end：统计窗口起止时间
  - station_id/device_id/metric_id：站点/设备/指标ID
  - quality_status：质量状态码
  - rows_count：该质量码的行数
  - total_count：总行数
  - ratio：占比（rows_count / total_count）
  - created_at：创建时间

数据来源：
  - 代码位置：sp_generate_quality_eval_by_device_metric 存储过程
  - 写入时机：质量报表生成时

使用场景：
  - 质量报表生成
  - 质量趋势分析
  - 质量问题统计

使用示例：
  -- 查询某设备某指标的质量分布
  SELECT
      quality_status,
      rows_count,
      total_count,
      ratio,
      ROUND(ratio * 100, 2) || '%' AS percentage
  FROM quality_eval_by_device_metric
  WHERE device_id = 121
    AND metric_id = 14
    AND window_start = '2025-09-01T00:00:00Z'
    AND window_end = '2025-09-02T00:00:00Z'
  ORDER BY quality_status;

  -- 查询质量问题最多的设备
  SELECT
      device_id,
      SUM(CASE WHEN quality_status > 0 THEN rows_count ELSE 0 END) AS problem_count,
      SUM(total_count) AS total_count,
      ROUND(SUM(CASE WHEN quality_status > 0 THEN rows_count ELSE 0 END)::numeric / SUM(total_count), 4) AS problem_ratio
  FROM quality_eval_by_device_metric
  WHERE window_start = '2025-09-01T00:00:00Z'
    AND window_end = '2025-09-02T00:00:00Z'
  GROUP BY device_id
  ORDER BY problem_ratio DESC;

注意事项：
  - 主键：(window_start, window_end, station_id, device_id, metric_id, quality_status)
  - ratio 字段精度：numeric(9,6)

```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| window_start | timestamp with time zone | 否 | - | - |
| window_end | timestamp with time zone | 否 | - | - |
| station_id | bigint | 否 | 0 | - |
| device_id | bigint | 否 | 0 | 设备ID：评估所属的设备ID |
| metric_id | bigint | 否 | - | 指标ID：评估所属的指标ID |
| quality_status | integer | 否 | - | - |
| rows_count | bigint | 否 | - | - |
| total_count | bigint | 否 | - | - |
| ratio | numeric | 否 | - | - |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |

---

### quality_profile_log

**表注释**:

```
质量过程性能剖析日志（按窗口/阶段记录耗时与行数）
```

**字段列表**:

| 字段名 | 数据类型 | 可空 | 默认值 | 注释 |
|--------|----------|------|--------|------|
| id | bigint | 否 | nextval('quality_profile_log_id_seq'::regclass) | 主键：质量画像日志记录的唯一标识符 |
| created_at | timestamp with time zone | 否 | now() | 创建时间：记录创建的时间戳 |
| window_start | timestamp with time zone | 否 | - | - |
| window_end | timestamp with time zone | 否 | - | - |
| station_id | bigint | 是 | - | - |
| device_id | bigint | 是 | - | 设备ID：画像所属的设备ID |
| stage | text | 否 | - | - |
| duration_ms | numeric | 是 | - | - |
| rows_affected | bigint | 是 | - | - |
| details | jsonb | 是 | - | - |
| code | integer | 是 | - | - |

---

