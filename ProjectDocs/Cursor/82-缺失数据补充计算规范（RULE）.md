# 缺失数据补充计算规范（RULE）

版本：v2.2（整合简化：去除安全相关条目）

## 目标与边界
- 目标：当单泵/总管缺少部分字段时，基于现有数据按统一、可审计、幂等的规则计算近似值，保障对齐与质量门禁。
- 边界：仅写回 `aligned_data.data_json`（不改表结构）；同秒最早去重；`JSON_MERGE_PATCH` 合并；不覆盖真实测量；`null` 不覆盖有效值。

## 字段与单位（写回键）
- flow_rate（m3/h）、cumulative_flow（m3）、load_rate（1）、head（m，需先在 `field_units` 登记）、pressure（kPa，限“总管设备”）。
- 精度：比率/频率 ≤3 位；电压/电流/功率/压力/流量/扬程 ≤2 位。

## 通用门禁
- 范围建议：frequency 45–65 Hz；power_factor 0–1；flow_rate 0–20000 m3/h；pressure 0–2000 kPa；head 0–150 m（可配）。
- data_quality：1=可靠/直接推导；2=累计复位/边界异常；3=工程近似（分摊/假设/回退）。

## 计算矩阵（缺失时才计算）
1) load_rate（变频泵）：load_rate = frequency/50.0，裁剪[0,1.3]。
2) flow_rate ⇄ cumulative_flow：
   - 差分：flow_rate = max(0, Δcum / (Δt/3600))；若 cum 回落（复位）该点不写（或0）并标记 2。
   - 积分：cum = cum_prev + flow_rate × (Δt/3600)。
3) kwh ⇄ power：
   - 积分/差分互推；现状已有，默认不补算，仅在确实缺失且可安全推导时启用。
4) power / power_factor：
   - P=√3·V_ll·I_l·PF 或 PF = P/(√3·V_ll·I_l)；逐相近似或三相平衡近似为 data_quality=3；无 PF 不算。
5) head（扬程，m）：
   - H-1（优先，传感器）：H=(p_dis−p_suc)/9.80665（kPa→m）。缺吸水侧时用配置 `p_suction_cfg_kpa`。
   - H-2（功率/流量反推）：H≈(η·P)/(ρgQ)，并联同秒取按流量加权平均 H_common。
   - H-3（频率比例）：H≈H_rated·(f/50)^2（需额定扬程）。
6) pressure（总管压力，kPa）：
   - P-1（优先，扬程换算）：p_dis = p_suction + 9.80665·H_common。
   - P-2（功率+总流量）：先按 H-2 得 H_common 再换算。
   - P-3（频率+额定扬程）：先按 H-3 得 H_common 再换算。

## 单泵流量分摊（无单泵瞬时时）
优先级：A（有压力，功率/扬程权重 w_i=ηP_i/H）→ A0（无压力，w_i=P_i）→ B（频率法，仅纳入有 frequency 的变频泵，w_i=f_i）→ C（运行泵等分）。

- 运行判定（任一）：power>0.5 kW 或 任一相电流>阈 或 frequency>1 Hz；允许轻微抖动的滑窗判定。
- 极小流量噪声门限：0<Q_total<q_noise_min（默认1 m3/h）跳过。
- 唯一运行短路：|R|=1 时 q=Q_total（做上限与舍入）。
- 尾差修正：Σq_i 与 Q_total 的尾差分配给权重最大泵后再裁剪。

## 执行顺序（每秒、每站点）
1) 聚合 Q_total；识别运行泵 R。
2) 基础互推：flow_rate⇄cumulative_flow、kwh⇄power（必要时）。
3) 变频泵：load_rate=frequency/50.0。
4) 单泵流量：A → A0 → B → C。
5) 扬程：H-1 → H-2 → H-3。
6) 总管压力：P-1 → P-2 → P-3。
7) 门禁/舍入/尾差修正；幂等写回（不覆盖真实测量）。

## 参数（建议默认，可配置）
- run_power_kw_threshold=0.5；run_freq_hz_threshold=1.0；run_current_a_threshold=3.0。
- q_noise_min=1.0 m3/h；head_range_m_max=150 m；pressure_range_kpa_max=2000 kPa；p_suction_cfg_kpa=0.0。
- efficiency_eta_default=0.75；流量小数=2；比率/频率小数=3。

## 校验与自修正（概要）
- 一致性：残差 r=Q_total−Σq_i；功率-水力平衡 η·ΣP_i vs ρgQ_totalH_common；差分→积分闭环；频率归一曲线一致性；稳态窗口方差。
- 自动修正：尾差分配；η_hat、p_suction_cfg_kpa、α_freq 的稳态窗口自校准（仅配置/计算使用，不落库）。
- 护栏：P95(|r|)/median(Q_total)≤3%；失配>25% 连续→降级或暂停；稳态占比骤降→降并发/减批次。
- 验收（建议）：RMSE 相对误差 ≤5–10%；闭环误差 ≤2%。

## 版本与兼容性
- 文档版本：v2.1（详见 `docs/缺失数据补充计算说明书.md`）。
- 不向 `data_json` 写入方法标识/版本号；仅日志记录来源方法与置信度。
- 所有计算为“新增或补齐缺失键”，不覆盖已有有效测量值；重复执行幂等。

## 参考
- 细节与示例：`docs/缺失数据补充计算说明书.md`（v2.1）。
- 相关规则：02-db-import-align、30-domain-dictionary、31-业务质量与边界、47-CSV方言、08-code-conventions、日志与追责 217。

