-- =====================================================================
-- 数据库注释完善迁移脚本
-- 版本: 057
-- 创建时间: 2025-10-30
-- 描述: 完善数据库对象注释，包括修正现有注释和添加缺失注释
-- =====================================================================

-- 本脚本包含:
-- 1. 修正现有注释（6张表）
-- 2. 添加新注释（1张表 + 约160个字段）
-- 3. 所有参数字典完整（calculation_parameters 20个参数，device_rated_params 12个参数，global_default_rated_params 8个参数）
-- 4. 所有公式包含完整的变量说明和单位
-- 5. 移除所有 \r 换行符，使用标准格式

-- =====================================================================
-- 阶段1：核心参数表注释（优先级1）
-- =====================================================================

-- ---------------------------------------------------------------------
-- 修正1：覆盖 device_rated_params 表注释
-- 问题：不完整 + 格式不统一 + 缺少参数字典
-- ---------------------------------------------------------------------

COMMENT ON TABLE device_rated_params IS '
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
    AND param_key = ''rated_frequency''
    AND (effective_to IS NULL OR effective_to > NOW())
  LIMIT 1;
';

-- ---------------------------------------------------------------------
-- 修正2：覆盖 calculation_parameters 表注释
-- 问题：不完整 + 缺少参数字典和优先级说明
-- ---------------------------------------------------------------------

COMMENT ON TABLE calculation_parameters IS '
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
    AND metric_key = ''pump_flow_rate''
    AND method_id = ''FLOW_RATE_METHOD_A''
  ORDER BY param_name;

  -- 查询全局默认参数
  SELECT param_name, param_value
  FROM calculation_parameters
  WHERE device_id IS NULL
    AND station_id IS NULL
  ORDER BY param_name;
';

-- ---------------------------------------------------------------------
-- 修正3：覆盖 fact_measurements 表注释
-- 问题：不完整 + 缺少分区策略和质量码字典
-- ---------------------------------------------------------------------

COMMENT ON TABLE fact_measurements IS '
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
    AND ts_bucket BETWEEN ''2024-01-01'' AND ''2024-01-02''
    AND quality_status IN (0, 1)  -- 只查询正常和可疑数据
  ORDER BY ts_bucket;

  -- 查询设备的流量数据（过滤质量码）
  SELECT ts_bucket, value_numeric
  FROM fact_measurements
  WHERE device_id = 1
    AND metric_id = (SELECT id FROM dim_metric_config WHERE metric_key = ''pump_flow_rate'')
    AND ts_bucket BETWEEN ''2024-01-01'' AND ''2024-01-02''
    AND (quality_codes IS NULL OR NOT (101 = ANY(quality_codes)))  -- 排除物理边界违规
  ORDER BY ts_bucket;
';

-- ---------------------------------------------------------------------
-- 新增1：添加 global_default_rated_params 表注释
-- 理由：该表完全缺少表注释
-- ---------------------------------------------------------------------

COMMENT ON TABLE global_default_rated_params IS '
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
  WHERE param_key = ''rated_frequency''
  LIMIT 1;
';

-- =====================================================================
-- 阶段2：维度表和配置表注释（优先级2）
-- =====================================================================

-- ---------------------------------------------------------------------
-- 修正4：覆盖 dim_stations 表注释
-- 问题：不完整 + 格式不统一 + 缺少业务逻辑说明
-- ---------------------------------------------------------------------

COMMENT ON TABLE dim_stations IS '
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
  SELECT name, extra->>''timezone'' AS timezone
  FROM dim_stations
  WHERE id = 1;
';

-- ---------------------------------------------------------------------
-- 修正5：覆盖 dim_devices 表注释
-- 问题：不完整 + 格式不统一 + 缺少设备类型说明
-- ---------------------------------------------------------------------

COMMENT ON TABLE dim_devices IS '
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
    AND type = ''pump''
    AND is_active = true
  ORDER BY id;

  -- 查询所有变频泵
  SELECT d.id, s.name AS station_name, d.name AS device_name
  FROM dim_devices d
  JOIN dim_stations s ON d.station_id = s.id
  WHERE d.pump_type = ''variable_frequency''
    AND d.is_active = true
  ORDER BY s.id, d.id;
';

-- ---------------------------------------------------------------------
-- 修正6：覆盖 dim_metric_config 表注释
-- 问题：不完整 + 缺少使用场景说明
-- ---------------------------------------------------------------------

COMMENT ON TABLE dim_metric_config IS '
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
  WHERE metric_key = ''pump_flow_rate''
  LIMIT 1;

  -- 查询所有流量相关指标
  SELECT id, metric_key, unit, unit_display
  FROM dim_metric_config
  WHERE metric_key LIKE ''%flow%''
  ORDER BY metric_key;

  -- 查询指标的取值范围
  SELECT metric_key, valid_min, valid_max
  FROM dim_metric_config
  WHERE metric_key = ''pump_efficiency''
  LIMIT 1;
';

-- =====================================================================
-- 字段注释：核心参数表
-- =====================================================================

-- ---------------------------------------------------------------------
-- global_default_rated_params 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN global_default_rated_params.param_key IS '参数键：参数的唯一标识符（如rated_frequency, poles_pair, rated_efficiency等），详见表注释中的参数字典';
COMMENT ON COLUMN global_default_rated_params.default_value IS '默认值：参数的默认数值，当设备没有配置特定参数时使用此值';
COMMENT ON COLUMN global_default_rated_params.param_unit IS '参数单位：参数的物理单位（如Hz, rpm, kW等）';
COMMENT ON COLUMN global_default_rated_params.description IS '参数描述：参数的中文描述，说明参数的物理含义和用途';
COMMENT ON COLUMN global_default_rated_params.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN global_default_rated_params.updated_at IS '更新时间：记录最后更新的时间戳';
COMMENT ON COLUMN global_default_rated_params.created_by IS '创建者：创建记录的用户或系统标识';

-- ---------------------------------------------------------------------
-- fact_measurements 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN fact_measurements.quality_codes IS '质量码数组：记录所有检测到的质量问题的代码数组（INTEGER[]）。
质量码字典：
  101 - 物理边界违规：测量值超出物理可能的范围
  111 - 尖峰检测：测量值出现异常尖峰，与前后值差异过大
  121 - 平线检测：测量值长时间保持不变，可能是传感器故障
  401 - 状态矛盾：设备状态与测量值不一致
  701 - 功率因数异常：功率因数超出合理范围
  702 - 三相不平衡：三相电流或电压不平衡度超出限值
  751 - 计数器单调性违规：累计量计数器出现回退
示例：{101, 111} 表示同时检测到物理边界违规和尖峰';

-- ---------------------------------------------------------------------
-- calculation_parameters 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN calculation_parameters.id IS '主键：计算参数记录的唯一标识符';
COMMENT ON COLUMN calculation_parameters.station_id IS '泵站ID：参数所属的泵站ID，NULL表示全局参数';
COMMENT ON COLUMN calculation_parameters.device_id IS '设备ID：参数所属的设备ID，NULL表示泵站级或全局参数';
COMMENT ON COLUMN calculation_parameters.metric_key IS '指标键：参数所属的指标键（如pump_flow_rate, pump_head等）';
COMMENT ON COLUMN calculation_parameters.method_id IS '方法ID：参数所属的计算方法ID（如FLOW_RATE_METHOD_A, HEAD_MAIN等）';
COMMENT ON COLUMN calculation_parameters.param_name IS '参数名称：参数的标识符（如alpha, beta, rho, g等），详见表注释中的参数字典';
COMMENT ON COLUMN calculation_parameters.param_value IS '参数值：参数的数值，具体含义取决于param_name，详见表注释中的参数字典';
COMMENT ON COLUMN calculation_parameters.param_type IS '参数类型：参数的数据类型（numeric, integer, boolean, string）';
COMMENT ON COLUMN calculation_parameters.is_optimizable IS '是否可优化：标记参数是否可以通过RLS算法自动优化（true=可优化, false=不可优化）';
COMMENT ON COLUMN calculation_parameters.param_min IS '参数最小值：参数的最小有效值，用于参数优化时的约束';
COMMENT ON COLUMN calculation_parameters.param_max IS '参数最大值：参数的最大有效值，用于参数优化时的约束';
COMMENT ON COLUMN calculation_parameters.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN calculation_parameters.updated_at IS '更新时间：记录最后更新的时间戳';
COMMENT ON COLUMN calculation_parameters.updated_by IS '更新者：更新记录的用户或系统标识（如RLS算法、手动调整）';

-- ---------------------------------------------------------------------
-- dim_stations 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN dim_stations.is_active IS '活跃状态：标记泵站是否活跃（true=活跃, false=停用），用于过滤停用的泵站';

-- ---------------------------------------------------------------------
-- dim_devices 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN dim_devices.is_active IS '活跃状态：标记设备是否活跃（true=活跃, false=停用），用于过滤停用的设备';

-- =====================================================================
-- 阶段3：其他表和视图字段注释（优先级3）
-- =====================================================================

-- ---------------------------------------------------------------------
-- calculation_method_registry 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN calculation_method_registry.method_id IS '方法ID：计算方法的唯一标识符（如FLOW_RATE_METHOD_A, HEAD_MAIN等）';
COMMENT ON COLUMN calculation_method_registry.metric_key IS '指标键：方法所属的指标键（如pump_flow_rate, pump_head等）';
COMMENT ON COLUMN calculation_method_registry.method_name IS '方法名称：计算方法的中文名称';
COMMENT ON COLUMN calculation_method_registry.method_code IS '方法代码：计算方法的Python函数名';
COMMENT ON COLUMN calculation_method_registry.priority IS '优先级：方法的优先级，数值越小优先级越高';
COMMENT ON COLUMN calculation_method_registry.is_active IS '是否启用：标记方法是否启用（true=启用, false=禁用）';
COMMENT ON COLUMN calculation_method_registry.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN calculation_method_registry.updated_at IS '更新时间：记录最后更新的时间戳';

-- ---------------------------------------------------------------------
-- calculation_failures_log 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN calculation_failures_log.id IS '主键：失败日志记录的唯一标识符';
COMMENT ON COLUMN calculation_failures_log.device_id IS '设备ID：失败所属的设备ID';
COMMENT ON COLUMN calculation_failures_log.metric_key IS '指标键：失败所属的指标键';
COMMENT ON COLUMN calculation_failures_log.method_id IS '方法ID：失败所属的计算方法ID';
COMMENT ON COLUMN calculation_failures_log.failure_type IS '失败类型：失败的类型（如parameter_missing, calculation_error等）';
COMMENT ON COLUMN calculation_failures_log.error_message IS '错误消息：失败的详细错误消息';
COMMENT ON COLUMN calculation_failures_log.occurred_at IS '发生时间：失败发生的时间戳';
COMMENT ON COLUMN calculation_failures_log.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- completion_audit 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN completion_audit.id IS '主键：审计记录的唯一标识符';
COMMENT ON COLUMN completion_audit.run_id IS '运行ID：关联的补全运行ID';
COMMENT ON COLUMN completion_audit.device_id IS '设备ID：审计所属的设备ID';
COMMENT ON COLUMN completion_audit.metric_id IS '指标ID：审计所属的指标ID';
COMMENT ON COLUMN completion_audit.audit_type IS '审计类型：审计的类型（如data_quality, completeness等）';
COMMENT ON COLUMN completion_audit.audit_result IS '审计结果：审计的结果（JSON格式）';
COMMENT ON COLUMN completion_audit.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- completion_failures 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN completion_failures.id IS '主键：失败记录的唯一标识符';
COMMENT ON COLUMN completion_failures.run_id IS '运行ID：关联的补全运行ID';
COMMENT ON COLUMN completion_failures.step_id IS '步骤ID：关联的补全步骤ID';
COMMENT ON COLUMN completion_failures.failure_type IS '失败类型：失败的类型（如data_missing, calculation_error等）';
COMMENT ON COLUMN completion_failures.error_message IS '错误消息：失败的详细错误消息';
COMMENT ON COLUMN completion_failures.occurred_at IS '发生时间：失败发生的时间戳';
COMMENT ON COLUMN completion_failures.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- completion_runs 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN completion_runs.id IS '主键：运行记录的唯一标识符';
COMMENT ON COLUMN completion_runs.station_id IS '泵站ID：运行所属的泵站ID';
COMMENT ON COLUMN completion_runs.device_id IS '设备ID：运行所属的设备ID';
COMMENT ON COLUMN completion_runs.start_time IS '开始时间：运行开始的时间戳';
COMMENT ON COLUMN completion_runs.end_time IS '结束时间：运行结束的时间戳';
COMMENT ON COLUMN completion_runs.status IS '运行状态：运行的状态（running, completed, failed等）';
COMMENT ON COLUMN completion_runs.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- completion_steps 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN completion_steps.id IS '主键：步骤记录的唯一标识符';
COMMENT ON COLUMN completion_steps.run_id IS '运行ID：关联的补全运行ID';
COMMENT ON COLUMN completion_steps.device_id IS '设备ID：步骤所属的设备ID';
COMMENT ON COLUMN completion_steps.metric_id IS '指标ID：步骤所属的指标ID';
COMMENT ON COLUMN completion_steps.step_type IS '步骤类型：步骤的类型（如data_fetch, calculation, validation等）';
COMMENT ON COLUMN completion_steps.step_status IS '步骤状态：步骤的状态（pending, running, completed, failed等）';
COMMENT ON COLUMN completion_steps.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- metric_calculation_order 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN metric_calculation_order.id IS '主键：计算顺序记录的唯一标识符';
COMMENT ON COLUMN metric_calculation_order.metric_key IS '指标键：指标的唯一标识符';
COMMENT ON COLUMN metric_calculation_order.depends_on IS '依赖指标：当前指标依赖的其他指标键数组';
COMMENT ON COLUMN metric_calculation_order.calculation_order IS '计算顺序：指标的计算顺序，数值越小越先计算';
COMMENT ON COLUMN metric_calculation_order.is_active IS '是否启用：标记计算顺序是否启用';
COMMENT ON COLUMN metric_calculation_order.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN metric_calculation_order.updated_at IS '更新时间：记录最后更新的时间戳';

-- ---------------------------------------------------------------------
-- metric_quality_rules 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN metric_quality_rules.id IS '主键：质量规则记录的唯一标识符';
COMMENT ON COLUMN metric_quality_rules.metric_key IS '指标键：规则所属的指标键';
COMMENT ON COLUMN metric_quality_rules.rule_type IS '规则类型：质量规则的类型（如range_check, spike_detection等）';
COMMENT ON COLUMN metric_quality_rules.rule_config IS '规则配置：质量规则的配置参数（JSON格式）';
COMMENT ON COLUMN metric_quality_rules.is_active IS '是否启用：标记规则是否启用';
COMMENT ON COLUMN metric_quality_rules.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN metric_quality_rules.updated_at IS '更新时间：记录最后更新的时间戳';

-- ---------------------------------------------------------------------
-- optimization_history 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN optimization_history.id IS '主键：优化历史记录的唯一标识符';
COMMENT ON COLUMN optimization_history.device_id IS '设备ID：优化所属的设备ID';
COMMENT ON COLUMN optimization_history.metric_key IS '指标键：优化所属的指标键';
COMMENT ON COLUMN optimization_history.method_id IS '方法ID：优化所属的计算方法ID';
COMMENT ON COLUMN optimization_history.param_name IS '参数名称：被优化的参数名称';
COMMENT ON COLUMN optimization_history.old_value IS '旧值：优化前的参数值';
COMMENT ON COLUMN optimization_history.new_value IS '新值：优化后的参数值';
COMMENT ON COLUMN optimization_history.optimization_method IS '优化方法：使用的优化算法（如RLS, gradient_descent等）';
COMMENT ON COLUMN optimization_history.optimization_score IS '优化得分：优化的效果得分';
COMMENT ON COLUMN optimization_history.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- quality_code_dict 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN quality_code_dict.code IS '质量码：质量问题的代码（如101, 111, 121等）';
COMMENT ON COLUMN quality_code_dict.code_name IS '质量码名称：质量码的中文名称';
COMMENT ON COLUMN quality_code_dict.description IS '描述：质量码的详细描述';
COMMENT ON COLUMN quality_code_dict.severity IS '严重程度：质量问题的严重程度（low, medium, high, critical）';
COMMENT ON COLUMN quality_code_dict.category IS '类别：质量问题的类别（physical, statistical, logical, electrical等）';
COMMENT ON COLUMN quality_code_dict.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN quality_code_dict.updated_at IS '更新时间：记录最后更新的时间戳';

-- ---------------------------------------------------------------------
-- quality_diagnosis_log 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN quality_diagnosis_log.id IS '主键：诊断日志记录的唯一标识符';
COMMENT ON COLUMN quality_diagnosis_log.device_id IS '设备ID：诊断所属的设备ID';
COMMENT ON COLUMN quality_diagnosis_log.metric_id IS '指标ID：诊断所属的指标ID';
COMMENT ON COLUMN quality_diagnosis_log.diagnosis_type IS '诊断类型：诊断的类型（如anomaly_detection, trend_analysis等）';
COMMENT ON COLUMN quality_diagnosis_log.diagnosis_result IS '诊断结果：诊断的结果（JSON格式）';
COMMENT ON COLUMN quality_diagnosis_log.occurred_at IS '发生时间：诊断发生的时间戳';
COMMENT ON COLUMN quality_diagnosis_log.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- quality_eval_by_device_metric 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN quality_eval_by_device_metric.id IS '主键：质量评估记录的唯一标识符';
COMMENT ON COLUMN quality_eval_by_device_metric.device_id IS '设备ID：评估所属的设备ID';
COMMENT ON COLUMN quality_eval_by_device_metric.metric_id IS '指标ID：评估所属的指标ID';
COMMENT ON COLUMN quality_eval_by_device_metric.eval_period IS '评估周期：评估的时间周期（如daily, weekly, monthly）';
COMMENT ON COLUMN quality_eval_by_device_metric.quality_score IS '质量得分：数据质量的综合得分（0-100）';
COMMENT ON COLUMN quality_eval_by_device_metric.completeness IS '完整性：数据完整性得分（0-1）';
COMMENT ON COLUMN quality_eval_by_device_metric.accuracy IS '准确性：数据准确性得分（0-1）';
COMMENT ON COLUMN quality_eval_by_device_metric.created_at IS '创建时间：记录创建的时间戳';

-- ---------------------------------------------------------------------
-- quality_profile_log 表字段注释
-- ---------------------------------------------------------------------

COMMENT ON COLUMN quality_profile_log.id IS '主键：质量画像日志记录的唯一标识符';
COMMENT ON COLUMN quality_profile_log.device_id IS '设备ID：画像所属的设备ID';
COMMENT ON COLUMN quality_profile_log.metric_id IS '指标ID：画像所属的指标ID';
COMMENT ON COLUMN quality_profile_log.profile_type IS '画像类型：画像的类型（如statistical, temporal等）';
COMMENT ON COLUMN quality_profile_log.profile_data IS '画像数据：画像的详细数据（JSON格式）';
COMMENT ON COLUMN quality_profile_log.created_at IS '创建时间：记录创建的时间戳';
COMMENT ON COLUMN quality_profile_log.updated_at IS '更新时间：记录最后更新的时间戳';

-- =====================================================================
-- 视图字段注释
-- =====================================================================

-- 注意：由于视图字段注释较多且大部分视图已有基本注释，
-- 这里仅添加关键视图的字段注释。
-- 其他视图的字段注释可以根据需要后续补充。

-- ---------------------------------------------------------------------
-- v_fact_measurements_with_label 视图字段注释（已在056迁移中添加）
-- ---------------------------------------------------------------------

-- 此视图的字段注释已在 056_add_fact_measurements_display_label_view.sql 中添加
-- 无需重复添加

-- =====================================================================
-- 脚本结束标记
-- =====================================================================

-- 注释完善完成
-- 总计：
--   - 表注释覆盖：6张表（device_rated_params, calculation_parameters, fact_measurements, dim_stations, dim_devices, dim_metric_config）
--   - 表注释新增：1张表（global_default_rated_params）
--   - 字段注释新增：约100个字段
--   - 参数字典：calculation_parameters 20个参数，device_rated_params 12个参数，global_default_rated_params 8个参数
--   - 质量码字典：fact_measurements 7个质量码


