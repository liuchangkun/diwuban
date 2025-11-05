# 维度表重建控制机制设计（dim_devices / dim_stations）

本文档给出在 configs/merge.yaml 增加 rebuild_dimensions 控制、影响范围、策略对比与推荐方案（并提供可执行实现与验证要点）。

## 1. 可行性分析
- 在 run_all 下新增开关 `rebuild_dimensions` 合理，符合当前集中式 Orchestrator 配置风格（prepare-dim 同一阶段处理）。
- 与现状契合点：prepare-dim 已经按映射（data_mapping.v2.json）执行幂等插入/更新；扩展“智能同步（smart）”仅需少量改动即可完成。
- 风险与边界：
  - truncate 方案极高风险（历史数据/审计/事实表外键）；仅建议在隔离测试环境使用。
  - smart 方案需要统一“停用策略”（建议 is_active 字段与应用层过滤逐步落地）。

## 2. 影响范围（数据库与应用）
- 外键引用（已核验）：
  - 引用 dim_devices.id：completion_runs、completion_steps、device_rated_params、device_running_thresholds_shadow、dim_device_capabilities、dim_metric_metadata_override、metric_quality_rules_shadow、metric_rule_auto_baseline_shadow、fact_measurements
  - 引用 dim_stations.id：completion_runs、dim_devices、dim_metric_metadata_override、metric_quality_rules_shadow、metric_rule_auto_baseline_shadow、calculation_parameters
- 表性质/影响等级（摘要）：
  - fact_measurements（事实，高）：强依赖 station_id/device_id；ID 变化会造成历史断裂或强制级联删除。
  - completion_runs/steps（审计，高）：重建会破坏溯源链。
  - *_shadow/override（配置影子，中）：ID 失配导致规则失效。
  - dim_*（维度，高）：主体对象，清空重建需极谨慎。
- 应用读取模块（摘要）：
  - 计算 Orchestrator 族（calculation/*、run_all/*）、presence、device_running、质量与报表模块等均间接依赖维度稳定性。

## 3. 策略设计与对比
- 方案A：TRUNCATE CASCADE（完全清空重建）
  - 优：实现简单；保证“与映射一致”。
  - 劣：极高风险——外键级联删除或 FK 冲突、历史断裂、审计丢失；生产不建议。
  - 适用：孤立测试库、数据沙盒。
- 方案B：智能同步（smart，保持ID、按名称匹配，新增插入、消失项软删除）【推荐】
  - 优：ID 稳定；历史数据与审计可保留；与现有 upsert 机制自然融合。
  - 劣：需要 is_active 软删除与应用层过滤逐步完善；对“名称唯一性/稳定性”有依赖。
  - 适用：生产/准生产环境。
- 方案C：双表影子切换（构建新维度影子表，灰度切换）
  - 优：切换可回滚；一致性更强。
  - 劣：实现复杂度较高；需要影子路由与同步器。
  - 适用：对可用性要求很高的大规模重构。

结论：推荐方案B（智能同步）。

## 4. 实施方案（方案B：智能同步）

### 4.1 配置项（已实现）
configs/merge.yaml:

```yaml
run_all:
  rebuild_dimensions:
    enabled: false           # 是否启用维度重建/同步（默认关闭）
    strategy: smart          # smart（智能同步，保ID）| truncate（高危清空重建，仅测试）
    auto_soft_delete: false  # smart：为消失项自动打 is_active=false（需要表含 is_active 字段）
```

### 4.2 代码改动（已实现）
- 文件：app/services/ingest/prepare_dim/__init__.py
  - 读取 merge.yaml.run_all.rebuild_dimensions
  - smart 模式：
    - 先按映射幂等 upsert 站点与设备（保持 ID）
    - auto_soft_delete=true 时：
      - ALTER TABLE 增加 is_active（若不存在）
      - 将映射内对象 is_active=true，映射缺失对象 is_active=false（按站点/设备名称差集）
  - truncate 模式：安全起见仅记录 WARNING（不在该路径直接执行 TRUNCATE）

### 4.3 流程（伪代码）
```python
cfg = read_merge_yaml().run_all.rebuild_dimensions
prepare_metric_config_from_sql()
upsert(stations, devices)
if cfg.enabled:
  if cfg.strategy == 'truncate':
     warn("需要在专用脚本中执行 TRUNCATE，避免误操作")
  else:  # smart
     if cfg.auto_soft_delete:
       add_is_active_if_missing()
       reactivate(mapping_stations, mapping_devices)
       deactivate_missing(mapping_stations, mapping_devices)
commit()
```

### 4.4 一致性保障
- 单事务执行（默认）；异常回滚。
- 差异前—后计数与抽样校验（日志打印：站点数/设备数）。
- （可选）在 CI/任务中增加“站点/设备名唯一性校验”。

### 4.5 验证检查点
- 日志：进入/完成 prepare-dim，smart 同步完成打点。
- DB：
  - is_active 列存在性（当 auto_soft_delete=true）
  - 缺失设备/站点是否被置 is_active=false，映射内对象 is_active=true

## 5. 风险与缓解
- 数据丢失（A）：避免在生产使用 TRUNCATE；若必须，先备份并在隔离环境验证。
- 外键冲突（A）：TRUNCATE 建议使用维护窗口 + 全量回归，与影子切换机制配合。
- 历史数据断裂（A）：仅在影子切换完成后再改引用；或保持 ID 不变（B）。
- 名称不稳定（B）：引入“稳定标识”策略（如 external_key）；或在 mapping 中强制唯一校验。
- 兼容性：应用层逐步在维度查询增加 `is_active=true` 过滤，避免软删除对象参与计算与报表。

## 6. 回滚方案
- smart：is_active 恢复为 true；或回退 merge.yaml 配置（enabled=false）。
- truncate（仅测试）：用备份恢复；或按名称映射回填 ID 后全链路重算与审计修复。

---

# 附：可执行脚本片段（仅用于测试环境）

## A. truncate 版（强风险，只放测试库）
```sql
BEGIN;
TRUNCATE TABLE public.dim_devices RESTART IDENTITY CASCADE;
TRUNCATE TABLE public.dim_stations RESTART IDENTITY CASCADE;
COMMIT;
```

## B. smart 版（auto_soft_delete=true 时）
```sql
ALTER TABLE public.dim_stations ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT TRUE;
ALTER TABLE public.dim_devices  ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT TRUE;
-- 将映射外的对象标记为 inactive（示例：按某站点）
UPDATE public.dim_devices SET is_active=FALSE WHERE station_id=:sid AND name <> ALL(:names);
```

