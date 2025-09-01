# 计算与优化可视化方案（jjjdash 模板说明）

目标
- 从“原始数据获取→方案选择→计算→结果入库”全过程可视化监控
- 在线优化闭环（门控/残差/递推更新/限幅）与离线曲线闭环（拟合/验证/版本）可视化

数据源（与 jjjj.md 对齐的字段）
- 输入：main_pipeline_*、pump_*、water_temperature
- 输出：pump_flow_rate、pump_head、pump_efficiency、pump_speed、pump_torque
- 辅助：run_flag、steady_flag、strategy（方案标签）、w_i、f_thr、P_thr、α、β、C_Q、b_Q、b_H、b_pout
- 残差：r_Qbal、r_HQ、r_QP
- 版本：curve_version_id、freq_range、n_running

目录结构（jjjdash）
- README.md：面板导入与数据源映射指南
- calc_overview.json：计算过程总览
- opt_overview.json：优化闭环总览
- curves_compare.json：H–Q / P–Q / η–Q 曲线对比
- params_residuals.json：参数与残差面板

计算过程总览（calc_overview）
- 数据质量：延迟/缺失/异常率
- 方案选择时间条：strategy（功率×频率/累计量求导/仅功率/仅频率/直取）
- 关键曲线：Q、H、P、η、n*；叠加输入点位
- 运行状态：run_flag、steady_flag
- 入库与追踪：批次成功率、耗时、trace 链接

优化闭环总览（opt_overview）
- 参数：α、β、C_Q、b_Q、b_H、b_pout（带限幅带）
- 残差：r_Qbal、r_HQ、r_QP（均值/RMS/分位数）、MAD 阈值
- 门控：稳态占比、冻结/降级状态
- 更新事件：参数更新日志与原因（残差/阈值）

曲线对比（curves_compare）
- H–Q、P–Q、η–Q：历史散点+当前曲线+新曲线（带置信区间）
- 版本：版本号/时间/适用范围，支持选择回滚

参数与残差（params_residuals）
- 参数与残差的多轴时序联动，支持窗口对齐与点选回放

落地建议
- 时序库：TimescaleDB/ClickHouse/InfluxDB 任意其一
- Grafana 导入模板后，配置数据源表/字段映射即可
- Trace/日志：OpenTelemetry + Jaeger/Tempo + Loki（可选）

---

## 数据源映射与 Postgres 表结构（仅 Postgres）

为实现 compute_pipeline_h.html 与 optimize_pipeline_h.html 的横向流程可视化，建议采用如下表结构（与 jjjj.md 对齐）：

- 计算过程：compute_runs、compute_steps、compute_metrics
- 优化过程：optimize_runs、optimize_steps、calibration_log、curve_versions

示例 DDL（可直接执行）
```
-- 计算批次
create table if not exists compute_runs (
  run_id text primary key,
  trace_id text,
  trace_url text,
  window_start timestamptz,
  window_end   timestamptz,
  site text,
  pump_count int,
  strategy text,
  formula_version text,
  data_delay_s double precision,
  missing_rate double precision,
  run_flag boolean,
  steady_flag boolean,
  status text,
  duration_ms int,
  created_at timestamptz default now()
);

-- 步骤留痕（含阈值命中明细）
create table if not exists compute_steps (
  id bigserial primary key,
  run_id text references compute_runs(run_id) on delete cascade,
  step_key text,
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

-- 计算结果（按泵按时刻）
create table if not exists compute_metrics (
  ts timestamptz,
  pump_id text,
  pump_flow_rate double precision,
  pump_head double precision,
  pump_efficiency double precision,
  run_id text,
  primary key (ts, pump_id)
);
```

查询与接口示例
```
-- 拉取计算流水线
select * from compute_runs where run_id=$1;
select step_key,step_name_cn,status,duration_ms,input_json,output_json,rules_json
from compute_steps where run_id=$1 order by id;

-- 拉取优化流水线
select * from optimize_runs where run_id=$1;
select step_key,step_name_cn,status,duration_ms,input_json,output_json,rules_json
from optimize_steps where run_id=$1 order by id;
select * from calibration_log where run_id=$1 order by id;
```

前端映射
- 运行ID、Trace 链接：来自 *runs 表*（compute_runs/optimize_runs）
- 步骤卡片：来自 *steps 表* 的 input_json/output_json/rules_json（中文表达式 + 通过/未通过）
- 关键曲线与 KPI：来自 compute_metrics 与原始 metric_key




---

## API 契约（只读接口，供可视化使用）

通用约定
- 基础路径：/api
- 鉴权：建议 Bearer JWT 或 API-Key（X-API-Key）。演示可关闭鉴权。
- 追踪：支持请求头 X-Trace-Id 透传；响应统一返回 trace_id 字段。
- 返回包裹：
```
{
  "code": 0,                 // 0=成功；其它=错误码
  "message": "ok",          // 错误时给出中文信息
  "trace_id": "...",        // 服务端生成或透传
  "data": { ... },
  "pagination": {            // 分页可选
    "limit": 50, "offset": 0, "total": 123
  }
}
```

错误码建议
- 0 成功；400 参数错误；401 未授权；403 禁止；404 未找到；409 冲突；429 频率限制；500 服务错误；503 暂不可用

### 计算过程（Compute）

1) GET /api/compute/runs
- 含义：查询计算批次（run）列表
- 查询参数：start、end（ISO8601）、site、status（ok|warn|err）、limit、offset
- 数据来源：compute_runs
- 响应 data 示例（省略分页）：
```
{
  "items": [
    {"run_id":"cmp-20250829-003","trace_id":"trace-cmp-3","window_start":"2025-08-29T11:15:00Z","window_end":"2025-08-29T11:16:00Z","site":"#A","pump_count":2,"strategy":"功率×频率分摊","status":"ok","duration_ms":2800}
  ]
}
```

2) GET /api/compute/runs/{run_id}
- 含义：获取某批次 run 元数据（含 Trace URL）
- 数据来源：compute_runs

3) GET /api/compute/runs/{run_id}/steps
- 含义：获取步骤级留痕，横向卡片的数据源
- 数据来源：compute_steps（按 id 排序）
- 响应 data.items[*] 字段：
  - step_key（如 qcalc）、step_name_cn（中文名）、status、duration_ms
  - input_json（输入快照，按 metric_key，例如 main_pipeline_outlet_pressure 等）
  - output_json（输出快照，如 w、pump_flow_rate、pump_head、pump_efficiency）
  - rules_json（阈值命中明细：name、expr、left、right、pass）

4) GET /api/compute/runs/{run_id}/metrics
- 含义：按泵返回本批次计算出的指标（可选 agg=raw|minute）
- 查询参数：pump_id、agg
- 数据来源：compute_metrics

5) GET /api/compute/steps/{id}
- 含义：单步明细（便于深挖或做跳转）
- 数据来源：compute_steps

SQL 模板参考（Postgres）
```
-- runs 列表
select * from compute_runs
where ($1::timestamptz is null or window_start >= $1)
  and ($2::timestamptz is null or window_end   <= $2)
  and ($3::text is null or site = $3)
  and ($4::text is null or status = $4)
order by window_start desc
limit $5 offset $6;

-- steps 列表
select step_key,step_name_cn,status,duration_ms,input_json,output_json,rules_json
from compute_steps where run_id = $1 order by id;
```

### 优化过程（Optimize）

1) GET /api/opt/runs
- 含义：查询优化批次列表
- 查询参数：start、end、status、limit、offset
- 数据来源：optimize_runs

2) GET /api/opt/runs/{run_id}
- 含义：获取某优化批次元数据（含 curve_version、Trace URL）
- 数据来源：optimize_runs

3) GET /api/opt/runs/{run_id}/steps
- 含义：获取优化步骤留痕（门控/残差/更新/限幅/记录/离线）
- 数据来源：optimize_steps
- 字段：同 compute.steps（含 rules_json）

4) GET /api/opt/runs/{run_id}/calibration-log
- 含义：参数更新日志（α/β/C_Q/b_Q/b_H/b_pout 的 old/new、是否限幅、残差快照）
- 数据来源：calibration_log

5) GET /api/curves/versions 与 /api/curves/versions/{version}
- 含义：曲线版本列表与明细（HQ/PQ/ηQ 系数、验证指标、状态）
- 数据来源：curve_versions

示例响应（/api/opt/runs/{run_id}/steps）
```
{
  "code":0,
  "message":"ok",
  "trace_id":"trace-opt-3",
  "data":{
    "items":[
      {"step_key":"gate","step_name_cn":"门控（边界/MAD/稳态）","status":"ok","duration_ms":120,
       "rules_json":[{"name":"物理边界","expr":"η∈[0,1] ∧ Q≥0 ∧ H≥0","pass":true}]},
      {"step_key":"update","step_name_cn":"参数递推更新","status":"ok","duration_ms":320,
       "input_json":{"alpha":1.00,"beta":1.00,"C_Q":1.00,"b_Q":0.0,"b_H":0.0,"b_pout":0.000},
       "output_json":{"alpha":1.02,"beta":0.99,"C_Q":1.01,"b_Q":-0.5,"b_H":0.2,"b_pout":0.003},
       "rules_json":[{"name":"限幅","expr":"C_Q∈[0.8,1.2], b_Q∈[-10,10], b_H∈[-10,10], b_pout∈[-0.05,0.05]","pass":true}]}
    ]
  }
}
```

### 安全与性能建议
- 限流：每 IP 每分钟请求数限制；错误重试的指数退避
- 字段裁剪：steps 接口支持 fields= 参数（如仅要 rules_json）
- 大 JSON 字段：为常用字段（status、duration_ms、strategy）冗余成列以便排序/筛选
- 追踪：所有响应统一含 trace_id；若未传 X-Trace-Id，服务端生成并写 runs 表
