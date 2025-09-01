# 现场数据驱动的泵/泵组计算方案（用于特性曲线拟合准备）

说明与约束：

- 不使用设备额定参数、管道几何/阻力参数；仅依赖现场采集点位（见 metric_key）。
- 单位归一：压力统一使用 MPa（不把变量转换为 Pa 存储/展示）。在涉及扬程等计算时，直接在公式中使用 Δp(MPa)×1e6 的因子完成换算。
- 常量：g=9.80665 m/s²；1 m³/h=1/3600 m³/s；1 kW=1000 W。
- 水密度 ρ：由 water_temperature（℃）估算（可选）；无温度修正时取 ρ=1000 kg/m³。温度修正近似：
  ρ(T)≈1000×\[1−((T+288.9414)/(508929.2×(T+68.12963)))×(T−3.9863)²\]（kg/m³，T∈\[0,60\]℃）。
- 稳态筛选建议：建立 run_flag、steady_flag，去除启停/阀位切换/异常振动与过温时段。

可用字段（节选）与中文释义（与表一致）：

- main_pipeline_outlet_pressure：总管出口压力（MPa）
- main_pipeline_inlet_pressure：总管进口压力（MPa）
- pump_inlet_pressure：泵进口压力（MPa）
- pump_outlet_pressure：泵出口压力（MPa，若无测点将推算）
- main_pipeline_flow_rate：总管瞬时流量（m³/h）
- main_pipeline_cumulative_flow：总管累计流量（m³）
- pump_cumulative_flow：泵累计流量（m³）
- pump_frequency：泵变频频率 f（Hz）
- pump_active_power：泵有功功率 P（kW）
- pump_voltage_a/b/c、pump_current_a/b/c、pump_power_factor：电参（V/A/功率因数）
- pump_kwh：泵电量（kWh）
- pool_liquid_level：水池液位（m）
- water_temperature：水温（℃）
- 设备振动/温度类：用于异常剔除

## 变量与符号对照表（中文注释，优先使用表中 metric_key）

- 直接量（来自采集，metric_key 与单位）：

  - main_pipeline_outlet_pressure：总管出口压力（MPa）
  - main_pipeline_inlet_pressure：总管进口压力（MPa）
  - pump_inlet_pressure：泵进口压力（MPa）
  - pump_outlet_pressure：泵出口压力（MPa）
  - main_pipeline_flow_rate：总管瞬时流量（m³/h）
  - main_pipeline_cumulative_flow：总管累计流量（m³）
  - pump_cumulative_flow：泵累计流量（m³）
  - pump_frequency：变频频率 f（Hz）
  - pump_active_power：有功功率 P（kW）
  - pump_voltage_a/b/c：三相电压（V）
  - pump_current_a/b/c：三相电流（A）
  - pump_power_factor：功率因数 cosφ（-）
  - pump_kwh：电量累计（kWh）
  - pool_liquid_level：水池液位 L（m）
  - water_temperature：水温 T（℃）

- 计算中使用的派生/临时符号（均在文中定义）：

  - Q_total：总管瞬时流量（=main_pipeline_flow_rate，m³/h）
  - P_in：电输入有功功率（默认取 pump_active_power，kW）
  - P_in_calc：由电参计算的有功功率（kW），用于替代 P_in
  - P_i：第 i 台泵的有功功率（=pump_active_power_i，kW）
  - f_i：第 i 台泵的变频频率（=pump_frequency_i，Hz）
  - w_i：第 i 台泵的分摊权重（无量纲）
  - α, β：权重指数（默认 α=1、β=1，可自校正）
  - f_thr, P_thr：频率/功率阈值用于判断运行状态（无量纲/物理量）
  - V_pump：泵累计流量（=pump_cumulative_flow，m³）
  - q_pump：由累计量求导得到的瞬时流量（m³/s）
  - Q_s：以秒计的瞬时流量（Q/3600，m³/s）
  - Δp_MPa：泵进出口压力差（MPa）
  - b_H、b_pout、b_Q：扬程/出口压力/流量的偏置项（用于位置差或系统性误差校正）
  - C_Q：流量缩放校正系数（仪表系统误差修正）
  - n\*：相对转速（=pump_frequency/f_ref，-）
  - f_ref：参考频率（Hz）
  - n_sync：同步转速（rpm）；P：电机极数；s：滑差（1%–3%）
  - P_shaft：水力轴功率（kW）
  - ω：角速度（rad/s）
  - Q_group, H_group, P_group, η_group：泵组的流量/扬程/功率/效率
  - r_HQ、\\hat{H}(Q)：相对当前 H–Q 曲线的扬程残差与预测值
  - r_QP、\\hat{P}(Q)：相对当前 P–Q 曲线的功率残差与预测值

## 参数默认值与阈值建议（可按数据自校正）

- 频率阈值 f_thr（用于判定泵是否运行，Hz）：
  - 建议：f_thr = max(2, 0.05·f_ref)；经验范围 3–5 Hz 或 f_ref 的 5%–10%。
  - 说明：f_ref 为参考频率，可取历史稳态下的最大频率。
- 功率阈值 P_thr（用于判定泵是否运行，kW）：
  - 建议：P_thr = max(0.5, 0.05·P_ref)，经验范围为 P_ref 的 5%–15%。
  - 说明：P_ref 可取在 f>f_thr 条件下 pump_active_power 的 95 分位值或上四分位数。
- 权重指数 α、β（功率×频率分摊中）：
  - 默认 α=1、β=1；建议调参范围 α∈\[0.8,1.2\]、β∈\[0.8,1.2\]，步长 0.05。
  - 自校正目标：最小化水量闭合残差与曲线残差（r_HQ、r_QP）。
- 流量校正系数与偏置：
  - C_Q 初始=1，建议范围 \[0.9, 1.1\]；b_Q 初始=0，建议范围 \[-5, 5\] m³/h。
- 扬程与压力偏置：
  - b_H 初始=0，建议范围 \[-5, 5\] m；b_pout 初始=0，建议范围 \[-0.02, 0.02\] MPa。
- 累计量求导窗口 W_d（s）：
  - 建议范围 60–180 s（默认 120 s）；动态变化快时可用 30–90 s。
- 稳态阈值（按每分钟变化率的经验范围）：
  - |dQ/dt| \< 1–5 m³/h/min；|dH/dt| \< 0.3–1 m/min；|df/dt| \< 0.2–1 Hz/min。
- 误差监控阈值（经验）：
  - r_HQ 的 RMS \< 2–4 m 或相对 \<10%–20%；r_QP 的相对误差 \< 5%–10%。

______________________________________________________________________

## 推算单泵瞬时流量（pump_flow_rate）

可用性与优先级（从高到低）：

- 方案 A：按“功率×频率”分摊（并联系统首选）；
- 方案 B：由泵累计量求导（单泵计量首选，若可用）；
- 方案 C：单泵运行时直接取总管流量；
- 方案 D：仅功率分摊；
- 方案 E：仅频率分摊；
- 方案 F：数据驱动回归融合（长期优化）。

方案 A：功率×频率分摊（首选并联近似）

- 是否需要前置计算：需要（识别运行台数 N_running；同步读取各泵 pump_active_power 与 pump_frequency；可选稳态筛选）
- 已知：main_pipeline_flow_rate=Q_total（总管瞬时流量，m³/h）；各泵 P_i=pump_active_power_i（kW）；各泵 f_i=pump_frequency_i（Hz）。
- 计算：
  - 设权重 w_i = (P_i^α × f_i^β) / Σ(P_j^α × f_j^β)，默认 α=1，β=1（建议 α、β 调参范围 \[0.8,1.2\]）；
  - 若 f_i \< f_thr（建议 3–5 Hz）或 P_i \< P_thr（建议 P_ref 的 5%–15%），则将该泵 w_i 置 0；
  - 归一化权重：w_i ← w_i / Σw_i；
  - pump_flow_rate_i = Q_total × w_i（m³/h）。
- 说明：功率反映负载，频率反映调速指令；二者联合能更好刻画并联不同工况下的分配。
- 置信度：Medium→High（随数据校准提高）。

方案 B：累计量求导（单泵计量可达高精度）

- 是否需要前置计算：需要（对 pump_cumulative_flow 做平滑+滑动线性回归求导）
- 已知：pump_cumulative_flow=V_pump（m³）。
- 计算：q_pump(t)=dV_pump/dt（m³/s）；pump_flow_rate=3600×q_pump（m³/h）。
- 注意：处理清零/回卷；对导数做中值/低通滤波以抑制噪声。
- 置信度：High（计量点可靠时）。

方案 C：单泵运行直接取总管流量

- 是否需要前置计算：不需要（仅需 run_flag 确认只有该泵运行）
- 计算：pump_flow_rate≈main_pipeline_flow_rate。
- 置信度：High（条件满足时）。

方案 D：仅功率分摊

- 是否需要前置计算：需要（识别 N_running）
- 计算：w_i=P_i/ΣP；pump_flow_rate_i=Q_total×w_i。
- 置信度：Medium。

方案 E：仅频率分摊

- 是否需要前置计算：需要（识别 N_running）
- 计算：w_i=f_i/Σf；pump_flow_rate_i=Q_total×w_i。
- 置信度：Low–Medium。

方案 F：数据驱动回归融合

- 是否需要前置计算：需要（构造训练集与稳态筛选）
- 思路：拟合 pump_flow_rate_i = F(P_i,f_i,cosφ_i,…)；在线用递推最小二乘/卡尔曼更新参数；
- 作用：作为 A/B 的增强与自校正来源，长期可达 High。

精度优化（通用）

- 使用滑动窗口对 V_pump 求导（60–180 s）降低噪声；
- 在 A/D/E 中引入偏置与缩放：Q_i = C_Q·(Q_total×w_i) + b_Q，并用历史闭合校验更新 C_Q、b_Q；
- 异常剔除：振动/温度异常、频繁启停、阀位切换时段；
- 与后续拟合出的 H–Q 曲线联动：当点位显著偏离曲线时触发权重/系数再估计。

______________________________________________________________________

## 推算泵出口压力（pump_outlet_pressure）

方案 A：直接读取（有测点时）

- 是否需要前置计算：不需要。

方案 B：以总管出口压力代替

- 是否需要前置计算：不需要。
- 计算：pump_outlet_pressure ≈ main_pipeline_outlet_pressure（MPa）。
- 适用：泵出口并入总管且测点位置接近。

方案 C：由进口压力与扬程回推

- 是否需要前置计算：需要（先得 pump_head）。
- 已知：pump_inlet_pressure=p_in（MPa）、pump_head=H（m）、ρ。
- 计算：pump_outlet_pressure = p_in + (ρ·g·H)/1e6（MPa）。

方案 D：泵组层面近似

- 是否需要前置计算：不需要。
- 计算：泵组出口压力 ≈ main_pipeline_outlet_pressure。

优化：

- 引入固定偏置 b_pout：p_out≈替代量+b_pout；b_pout 由历史稳态段最小二乘估计。

______________________________________________________________________

## 推算泵扬程（pump_head）

核心：采用 MPa 单位直接计算，不把变量转换/保存为 Pa。

- 是否需要前置计算：需要（密度 ρ 可选；压力单位为 MPa 即可）。
- 已知：pump_outlet_pressure=p_out（MPa）、pump_inlet_pressure=p_in（MPa）、ρ。
- 计算：
  - Δp_MPa = p_out − p_in（MPa）
  - pump_head = H ≈ (Δp_MPa×1e6)/(ρ·g)（m）
  - 若测点标高/动压存在系统差，加入常数偏置：H≈(Δp_MPa×1e6)/(ρ·g)+b_H。

泵组扬程（可选）：

- H_group ≈ ((main_pipeline_outlet_pressure − main_pipeline_inlet_pressure)×1e6)/(ρ·g)。

优化：

- 用 pool_liquid_level 变化修正 b_H（如 b_H=f(L)）；
- 采用鲁棒回归抑制异常压力点。

______________________________________________________________________

## 推算泵效率（pump_efficiency）

定义（总效率，电→水）：η = (ρ·g·Q_s·H)/(P_in×1000)。

- 是否需要前置计算：需要（得到 Q_s、H、P_in；单位归一）。
- 已知：pump_active_power=P_in（kW）、pump_flow_rate=Q（m³/h）、pump_head=H（m）、ρ。
- 计算：Q_s=Q/3600（m³/s）；
  pump_efficiency = η = (ρ·g·Q_s·H)/(P_in×1000)。

替代功率来源：

- 若无 pump_active_power，可由电参计算：
  - 取等效线电压/电流 U_line、I_line 与 pump_power_factor（cosφ），
  - P_in_calc = √3·U_line·I_line·cosφ（kW），替代进入上式。
- 或由 pump_kwh 求导：P_in≈d(pump_kwh)/dt（kW）（需平滑）。

边界与异常：η 不应超出 \[0,1\]；超界时回溯 Q/H/P 的异常与单位。

______________________________________________________________________

## 推算泵转速（pump_speed）

方案 A：相对转速（推荐用于归一化）

- 是否需要前置计算：需要（选定参考频率 f_ref，例如历史稳态最大频率）。
- 计算：n\* = pump_frequency / f_ref（无量纲）。

方案 B：经验极数后的绝对转速（可选）

- 是否需要前置计算：需要（推断极数 P∈{2,4}，滑差 s≈1%–3%）。
- 计算：n_sync = 120·pump_frequency / P（rpm）；pump_speed ≈ n_sync·(1−s)。

方案 C：一次性标定 n–f 关系

- 是否需要前置计算：需要（选取参考点）；
- 计算：pump_speed = a·pump_frequency + b，a,b 由一次性标定得到。

______________________________________________________________________

## 推算泵扭矩（pump_torque）

方案 A：由水力功率与转速

- 是否需要前置计算：需要（Q、H、n 或 n\*）。
- 计算：P_shaft = ρ·g·(pump_flow_rate/3600)·pump_head/1000（kW）；
  ω = 2π·pump_speed/60（rad/s）；
  pump_torque = (P_shaft×1000)/ω（N·m）。

方案 B：由电功率与频率（趋势）

- 是否需要前置计算：需要（pump_frequency）。
- 计算：以 P_in 为上限估计：pump_torque ≈ (pump_active_power×1000)/ω；
  无 pump_speed 时可用相对扭矩 T\*∝pump_active_power/pump_frequency。

______________________________________________________________________

## 泵组层面的派生量（用于并联特性）

- Q_group = main_pipeline_flow_rate。
- H_group ≈ ((main_pipeline_outlet_pressure − main_pipeline_inlet_pressure)×1e6)/(ρ·g)。
- P_group = Σ pump_active_power（运行泵）。
- η_group = (ρ·g·(Q_group/3600)·H_group)/(P_group×1000)。

______________________________________________________________________

## 持续优化与精度提升（误差监控 + 数据驱动自校正 + 曲线闭环）

目标与范围（可直接落地）：

- 通过“在线误差监控 + 递推自校正 + 曲线闭环”三层机制，长期提升 pump_flow_rate、pump_head、pump_efficiency 等计算结果的准确性与稳定性。
- 不依赖设备额定与管道参数，仅使用文档中的采集量/派生量。

一、在线误差监控（每 1 分钟触发一次）

- 物理边界检查（按泵与泵组）：
  - η∈\[0,1\]；pump_flow_rate≥0；pump_head≥0；pressure（MPa）在合理范围内（可站点配置）。
  - 若越界：记录告警、冻结参数更新、切换到保守方案（如仅功率或频率分摊）。
- 残差指标（在 steady_flag=1 的时段计算）：
  - r_HQ = pump_head − \\hat{H}(pump_flow_rate)（使用当前 H–Q 曲线，单位 m）。
  - r_QP = pump_active_power − \\hat{P}(pump_flow_rate)（使用当前 P–Q 曲线，单位 kW）。
  - r_Qbal = main_pipeline_flow_rate − Σ pump_flow_rate_i（m³/h，泵组水量闭合）。
- 阈值与动态调整：
  - 使用“经验阈值”与“MAD 鲁棒阈值”并行：|r|>max(阈值经验, k·MAD) 判为异常，k 建议 3。
  - 异常占比超过 10% 的时间窗，则触发自校正任务并降级权重（如 β↓、α↓）。

二、数据驱动自校正（递推，窗口 30–120 分钟）

- 需更新的参数（含中文含义）：
  - α、β：功率/频率分摊公式的指数（决定 w_i 对 P_i、f_i 的敏感度）。
  - C_Q、b_Q：流量缩放/偏置（修正总管计量与分摊误差）。
  - b_H：扬程偏置（吸/排标高差、动压差等合并项）。
  - b_pout：出口压力偏置（测点位置差/局部损失）。
- 基本思想：以“最小化残差”为目标函数，使用递推最小二乘（RLS）或一阶梯度下降在线更新。

(1) 流量分摊参数 {α, β, C_Q, b_Q} 的更新

- 观测：Q_total=main_pipeline_flow_rate，P_i=pump_active_power_i，f_i=pump_frequency_i。
- 当前估计：w_i(α,β)=(P_i^α f_i^β)/Σ(P_j^α f_j^β)；\\tilde{Q}\_i=C_Q·(Q_total·w_i)+b_Q。
- 目标：最小化 r_Qbal = Q_total − Σ \\tilde{Q}\_i 以及曲线残差 r_HQ、r_QP。
- 梯度近似与更新（示意）：
  - α ← clip(α − η_α·∂J/∂α, \[0.5, 2.0\])；β 同理（η 为学习率，建议 1e−3~1e−2）。
  - C_Q ← clip(C_Q − η_Q·∂J/∂C_Q, \[0.8, 1.2\])；b_Q ← clip(b_Q − η_b·∂J/∂b_Q, \[-10,10\])。
- RLS 版本（对 C_Q、b_Q）：
  - 设 y=Q_total，φ=\[Σ(Q_total·w_i), 1\]，参数 θ=\[C_Q, b_Q\]^T。
  - 递推：K=Pφ/(λ+φ^T P φ)，θ←θ+K(y−φ^T θ)，P←(I−Kφ^T)P/λ（λ 为遗忘因子 0.98–0.995）。

(2) 扬程/压力偏置 {b_H, b_pout} 的更新

- 观测：r_HQ 与 r_pout，其中 r_pout = pump_outlet_pressure_proxy − pump_outlet_pressure_est（若有代理）。
- 简化一阶更新：
  - b_H ← clip(b_H + k_H·median(r_HQ_window), \[-10,10\])，k_H 建议 0.1–0.3。
  - b_pout ← clip(b_pout + k_p·median(r_pout_window), \[-0.05,0.05\])，k_p 建议 0.3–0.6。
- 若存在泵累计量（pump_cumulative_flow）可信片段，可用其推得的 pump_flow_rate 作为教师信号强化 b_H 更新。

三、与特性曲线的闭环（离线/准在线，按日/周）

- 数据选择：steady_flag=1，剔除异常与报警时段；按不同 N_running、频率分段分别拟合。
- 拟合：
  - H–Q：二/三次多项式或物理一致的单调函数；
  - P–Q：二次多项式（保证 P≥0）；
  - η–Q：峰形函数（如二次/三次并加 0–1 约束）。
- 验证：交叉验证 + 留出集；若新曲线使 r_HQ、r_QP 的 RMS 下降 ≥5% 且物理边界满足，则替换线上版本。
- 版本化：保存曲线参数与时间戳、适用频率/台数范围；支持回滚。
- 闭环：线上监控使用最新 \\hat{H}(Q)、\\hat{P}(Q)，其残差用于推动“二、数据驱动自校正”。

四、实施与存储（建议）

- 在线任务（每 1 分钟）：
  1. 同步数据、单位校验（压力仍为 MPa）；2) 运行/稳态判断；3) 计算 Q/H/η；
  1. 误差监控与告警；5) 递推更新 {α,β,C_Q,b_Q,b_H,b_pout}（满足稳态与安全阈值才更新）；
  1. 记录日志到数据库。
- 离线任务（每日/每周）：
  1. 曲线拟合与验证；2) 更新参考频率 f_ref；3) 生成新版本参数并灰度发布。
- 数据库存储建议：
  - 表 pump_calibration：pump_id、α、β、C_Q、b_Q、b_H、b_pout、f_ref、updated_at、data_window。
  - 表 pump_curve：type(HQ|PQ|ηQ)、coeffs、freq_range、n_running、version、created_at、note。
- 安全保护：
  - 所有参数更新均使用 clip 限幅；异常比例高或数据质量差时自动冻结更新、回退至保守方案。

五、伪代码（注释为中文，便于直接实现）

```
# 每分钟调度（稳态时才更新）
if run_flag and steady_flag:
    # 1) 计算派生量（Q/H/η 等）与残差
    Q_total = main_pipeline_flow_rate
    P = pump_active_power; f = pump_frequency
    # 计算 w_i 与分摊得到的 Q_i（功率×频率）
    w_i = (P_i**α * f_i**β)
    w_i = w_i / sum(w_j)
    Q_i = C_Q * (Q_total * w_i) + b_Q

    # 2) 误差监控
    r_Qbal = Q_total - sum(Q_i)
    r_HQ = pump_head - H_hat(Q_i)
    r_QP = pump_active_power - P_hat(Q_i)
    if any_violate_bounds([η, Q_i, pump_head]) or too_many_outliers([r_HQ, r_QP]):
        freeze_update(); use_fallback_weights(); log_alarm()
    else:
        # 3) 递推更新参数（示例：RLS 更新 C_Q、b_Q）
        phi = [sum(Q_total * w_i), 1]
        theta, P = RLS_update(theta, P, y=Q_total, phi=phi, λ)
        C_Q, b_Q = theta
        # 4) 一阶更新 α、β、b_H、b_pout（带限幅）
        α = clip(α - η_α * dJ_dα, 0.5, 2.0)
        β = clip(β - η_β * dJ_dβ, 0.5, 2.0)
        b_H = clip(b_H + k_H * median(window(r_HQ)), -10, 10)
        b_pout = clip(b_pout + k_p * median(window(r_pout)), -0.05, 0.05)
        log_update()
```

______________________________________________________________________

## Postgres 数据落地（计算/优化全过程表结构，直接可建）

仅使用 Postgres（推荐加 Timescale 扩展做分区亦可）。字段单位与本文保持一致：压力 MPa、流量 m³/h、功率 kW、频率 Hz。

一、计算流程表（对应 compute_pipeline_h.html）

- compute_runs（计算批次元数据）

```
create table if not exists compute_runs (
  run_id text primary key,
  trace_id text,
  trace_url text,
  window_start timestamptz,
  window_end   timestamptz,
  site text,
  pump_count int,
  strategy text,            -- 方案：功率×频率/累计量求导/…
  formula_version text,     -- 计算公式版本
  data_delay_s double precision,
  missing_rate double precision,
  run_flag boolean,
  steady_flag boolean,
  status text,              -- 正常/警告/错误
  duration_ms int,
  created_at timestamptz default now()
);
```

- compute_steps（步骤级留痕，含阈值命中明细）

```
create table if not exists compute_steps (
  id bigserial primary key,
  run_id text references compute_runs(run_id) on delete cascade,
  step_key text,            -- ingest/validate/gate/select/qcalc/hcalc/etacalc/persist
  step_name_cn text,        -- 中文名
  status text,              -- 正常/警告/错误
  start_ts timestamptz,
  end_ts   timestamptz,
  duration_ms int,
  input_json  jsonb,        -- 输入快照（按 metric_key）
  output_json jsonb,        -- 输出快照（w_i、pump_flow_rate、pump_head、η 等）
  rules_json  jsonb,        -- 阈值命中明细：[{name,expr,left,right,pass}]
  error_msg   text,
  created_at timestamptz default now()
);
create index if not exists idx_compute_steps_run on compute_steps(run_id);
create index if not exists idx_compute_steps_step on compute_steps(step_key);
```

- compute_metrics（按时间/泵写入的计算结果）

```
create table if not exists compute_metrics (
  ts timestamptz,
  pump_id text,
  pump_flow_rate double precision,  -- m³/h
  pump_head      double precision,  -- m
  pump_efficiency double precision, -- %
  pump_speed     double precision,  -- rpm 或 n*（建议另列 n_rel）
  pump_torque    double precision,  -- N·m（可选）
  run_id text,
  primary key (ts, pump_id)
);
create index if not exists idx_compute_metrics_run on compute_metrics(run_id);
```

二、优化流程表（对应 optimize_pipeline_h.html）

- optimize_runs / optimize_steps / calibration_log / curve_versions

```
create table if not exists optimize_runs (
  run_id text primary key,
  trace_id text,
  trace_url text,
  window_start timestamptz,
  window_end   timestamptz,
  curve_version text,
  status text,
  duration_ms int,
  created_at timestamptz default now()
);

create table if not exists optimize_steps (
  id bigserial primary key,
  run_id text references optimize_runs(run_id) on delete cascade,
  step_key text,            -- gate/resid/update/freeze/log/offline
  step_name_cn text,
  status text,
  start_ts timestamptz,
  end_ts   timestamptz,
  duration_ms int,
  input_json  jsonb,
  output_json jsonb,
  rules_json  jsonb,
  error_msg   text,
  created_at timestamptz default now()
);
create index if not exists idx_opt_steps_run on optimize_steps(run_id);

create table if not exists calibration_log (
  id bigserial primary key,
  run_id text references optimize_runs(run_id) on delete cascade,
  param_name text,          -- α/β/C_Q/b_Q/b_H/b_pout
  old_value double precision,
  new_value double precision,
  learn_rate double precision,
  clip_hit boolean,
  residuals_snapshot jsonb, -- {r_Qbal:..., r_HQ:..., r_QP:...}
  created_at timestamptz default now()
);

create table if not exists curve_versions (
  id bigserial primary key,
  version text,
  curve_type text,          -- HQ/PQ/ηQ
  coeffs jsonb,
  validated_metrics jsonb,  -- {rms_drop_pct:..., constraints_ok:true}
  status text default 'active',
  created_at timestamptz default now(),
  published_at timestamptz
);
```

三、查询示例（供前端拉取流水线数据）

```
-- 计算流程：拉取批次与步骤
select * from compute_runs where run_id = $1;
select step_key,step_name_cn,status,duration_ms,input_json,output_json,rules_json
from compute_steps where run_id = $1 order by id;

-- 优化流程：批次、步骤、参数更新日志
select * from optimize_runs where run_id = $1;
select step_key,step_name_cn,status,duration_ms,input_json,output_json,rules_json
from optimize_steps where run_id = $1 order by id;
select * from calibration_log where run_id = $1 order by id;
```

说明：

- rules_json 应包含中文可读表达式与左右操作数（便于前端展示“阈值命中明细”）。
- 生产中建议对常用字段（如 pump_flow_rate、pump_head）在 compute_steps.output_json 里冗余出简短标量列以便索引统计（可选）。

______________________________________________________________________

## 数据清洗与稳态筛选（建议实现）

- run_flag：pump_frequency>f_thr 且 任一(pump_current_a/b/c) 或 pump_active_power>P_thr。
- steady_flag：|dQ/dt|、|dH/dt|、|df/dt| 小于阈值，且振动/电机温度在正常范围。
- 过滤规则：
  - 开停机与阀位切换窗口（±Δt）剔除；
  - 传感器跳变、负值/缺失值剔除；
  - 使用鲁棒统计（如 MAD）识别离群点。

______________________________________________________________________

结论：

- 在“无额定与管道参数”的前提下，以上方法可直接生成特性拟合所需的 H、Q、P、η、n 等核心字段；
- 并联系统推荐优先使用“功率×频率”分摊获得 pump_flow_rate，配合累计量求导与曲线闭环进行长期自校准；
- 压力始终以 MPa 存储/展示，涉及计算时在公式中使用 ×1e6 因子，不改变变量单位。
