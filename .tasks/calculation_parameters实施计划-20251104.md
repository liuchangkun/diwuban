# calculation_parameters 表改进实施计划

**创建时间**：2025-11-04
**计划模式**：RIPER-5 协议 - 计划模式
**用户选择方案**：组合C - 激进组合（高风险、高成本）

---

## 执行摘要

### 用户决策
- **分层参数**：方案1C - 全面启用设备级参数（为所有设备配置设备级参数）
- **参数优化**：方案2C - 全面启用参数优化（为所有可优化参数启用RLS算法）
- **迁移脚本072**：方案3C - 修改脚本使用准确参数（从device_rated_params表获取准确的设备级参数）
- **审计字段**：方案4C - 完善所有审计字段（updated_by、notes等）

### 风险确认
- ⚠️ 当前系统只有2小时的历史数据（634,530行，8台设备）
- ⚠️ 不满足方案建议的"至少6个月数据积累"要求（相差2160倍）
- ⚠️ 用户已理解并接受高风险、高成本方案
- ⚠️ 用户承诺逐步补充历史数据并密切监控

### 设备范围
- **设备1-6**：二期供水泵房1-6#泵（type='pump', pump_type='variable_frequency'）
- **设备7**：二期供水泵房总管（type='main_pipeline'）
- **设备8**：其他（type='other', is_active=false）- 不配置

### prepare_dim 阶段影响分析
- ✅ **不会影响 prepare_dim 阶段**：calculation_parameters 表会被备份和恢复
- ✅ **不会影响 prepare_dim-2 阶段**：该阶段只生成规则表，不读取 calculation_parameters
- ✅ **configs/merge.yaml 中的 enable_optimization: true**：只影响 enable_calculation 阶段

---

## 阶段概览

| 阶段 | 名称 | 风险等级 | 预计耗时 | 暂停点 |
|------|------|----------|----------|--------|
| 1 | 数据补充要求说明 | 🟢 低风险 | 0.5小时 | CP-01 |
| 2 | 设备级参数配置 | 🟡 中风险 | 2小时 | CP-02, CP-03, CP-04 |
| 3 | 参数优化启用 | 🔴 高风险 | 4小时 | CP-05, CP-06, CP-07 |
| 4 | 审计字段完善 | 🟡 中风险 | 2小时 | CP-08 |
| 5 | 风险控制措施和应急预案 | 🟡 中风险 | 3小时 | CP-09 |

**总计**：11.5小时（不包括数据补充时间）

---

## 暂停点汇总

| 编号 | 名称 | 阶段 | 类型 | 说明 |
|------|------|------|------|------|
| CP-01 | 用户确认数据补充策略 | 1 | ⏸️ 暂停点 | 等待用户选择数据补充策略（等待实时数据/导入历史数据/模拟数据） |
| CP-02 | 验证备份成功 | 2 | 🟡 验证点 | 验证 calculation_parameters 表备份成功 |
| CP-03 | 验证迁移脚本执行成功 | 2 | 🟡 验证点 | 验证设备级参数插入成功 |
| CP-04 | 验证参数加载功能正常 | 2 | 🟡 验证点 | 验证 orchestrator.py 的 load_parameters() 方法正常工作 |
| CP-05 | 用户确认启用参数优化 | 3 | ⏸️ 暂停点 | 等待用户确认数据已补充并可以启用参数优化 |
| CP-06 | 验证参数优化代码修改成功 | 3 | 🟡 验证点 | 验证 orchestrator.py 修改成功 |
| CP-07 | 验证参数优化功能正常 | 3 | 🔴 验证点 | 验证 RLS 参数优化功能正常工作 |
| CP-08 | 验证审计字段完善成功 | 4 | 🟡 验证点 | 验证 updated_by 字段正常记录 |
| CP-09 | 验证监控和回滚机制 | 5 | 🟡 验证点 | 验证监控仪表板和回滚脚本正常工作 |

---

## 高风险步骤汇总

| 步骤编号 | 步骤名称 | 风险描述 | 应对措施 |
|----------|----------|----------|----------|
| 2.5.1 | 执行迁移脚本072_v2 | 可能插入错误的设备级参数 | 先在测试环境执行，验证后再在生产环境执行 |
| 3.4.1 | 修改 orchestrator.py 启用参数优化 | 可能导致参数优化失败或收敛到错误值 | 设置参数范围约束，添加监控和回滚机制 |
| 3.5.1 | 首次运行参数优化 | 数据不足可能导致优化失败 | 捕获异常，记录日志，跳过优化 |
| 5.3.1 | 创建参数优化监控仪表板 | 监控不及时可能导致错误参数未被发现 | 设置告警阈值，自动发送告警通知 |

---

## 阶段1：数据补充要求说明

### 1.1 目标
明确参数优化所需的最少数据量、数据质量标准和数据补充策略。

### 1.2 RLS参数优化的数据要求

#### 1.2.1 最少数据量要求 🔴

**理论要求**（基于RLS算法特性）：
- **最少样本数**：每个可优化参数至少需要 **1000个有效样本点**
- **推荐样本数**：每个可优化参数至少需要 **10000个有效样本点**
- **最佳样本数**：每个可优化参数至少需要 **100000个有效样本点**（约1个月的秒级数据）

**当前数据情况**：
- 总行数：634,530行
- 时间跨度：2小时（7200秒）
- 平均每秒样本数：634,530 / 7200 ≈ 88行/秒
- 平均每台设备每秒样本数：88 / 8 ≈ 11行/秒

**数据不足的影响**：
- ⚠️ **协方差矩阵不稳定**：样本不足会导致协方差矩阵奇异或病态
- ⚠️ **参数震荡**：优化过程中参数值可能剧烈波动
- ⚠️ **收敛到错误值**：可能收敛到局部最优而非全局最优
- ⚠️ **置信度低**：confidence_score 会很低（<0.3）

**最少数据量建议**：
- **立即启用参数优化**：至少需要 **1个月的历史数据**（720小时）
- **稳定运行参数优化**：至少需要 **3个月的历史数据**（2160小时）
- **高精度参数优化**：至少需要 **6个月的历史数据**（4320小时）

#### 1.2.2 数据质量标准 🟡

**有效样本的定义**：
1. **时间戳有效**：ts_bucket 不为 NULL，且在合理范围内
2. **设备运行**：设备处于运行状态（通过 device_running_thresholds 判定）
3. **指标完整**：计算所需的依赖指标都存在且有效
4. **质量合格**：quality_status = 0（原始数据）或 1（计算数据）
5. **数值合理**：指标值在合理范围内（不是异常值或缺失值）

**数据质量检查SQL**：
```sql
-- 检查有效样本数（以 pump_flow_rate 为例）
SELECT 
    device_id,
    COUNT(*) as total_samples,
    COUNT(CASE WHEN quality_status IN (0, 1) THEN 1 END) as valid_samples,
    MIN(ts_bucket) as earliest_time,
    MAX(ts_bucket) as latest_time,
    EXTRACT(EPOCH FROM (MAX(ts_bucket) - MIN(ts_bucket)))/3600 as hours_of_data
FROM fact_measurements
WHERE metric_key = 'pump_flow_rate'
GROUP BY device_id
ORDER BY device_id;
```

**质量标准**：
- **有效样本比例** ≥ 80%（valid_samples / total_samples ≥ 0.8）
- **数据连续性**：时间间隔不超过5分钟（避免大段数据缺失）
- **设备运行时间** ≥ 50%（设备至少运行一半时间）

#### 1.2.3 数据补充策略 ⏸️

**策略A：等待实时数据积累**（推荐）
- **优点**：数据真实可靠，质量高
- **缺点**：需要等待1-6个月
- **适用场景**：系统已上线，正在实时采集数据

**策略B：导入历史数据**（如果有）
- **优点**：可以立即获得大量数据
- **缺点**：需要历史数据源，可能需要数据清洗
- **适用场景**：有历史SCADA数据或PLC数据

**策略C：模拟数据生成**（不推荐）
- **优点**：可以立即获得大量数据
- **缺点**：数据不真实，优化结果不可靠
- **适用场景**：仅用于测试和验证，不用于生产环境

**⏸️ 暂停点 CP-01：用户确认数据补充策略**
- 请用户确认数据补充策略（A/B/C）
- 如果选择策略A，请确认可以等待的时间（1个月/3个月/6个月）
- 如果选择策略B，请提供历史数据源和数据格式
- 如果选择策略C，请明确这只是测试环境

### 1.3 数据不足时的风险和应对措施 🔴

#### 1.3.1 风险清单

**风险1：参数优化失败**
- **表现**：RLS算法抛出异常（协方差矩阵奇异）
- **概率**：高（样本数 < 1000时）
- **影响**：参数优化功能无法使用，参数值保持初始值
- **应对**：捕获异常，记录日志，跳过优化

**风险2：参数收敛到错误值**
- **表现**：优化后的参数值明显不合理（如 alpha < 0 或 alpha > 10）
- **概率**：中（样本数 1000-10000时）
- **影响**：计算结果误差增大，可能导致错误的业务决策
- **应对**：设置参数范围约束（param_min、param_max），超出范围时回滚

**风险3：参数震荡**
- **表现**：参数值在每次优化时剧烈波动
- **概率**：中（样本数 1000-10000时）
- **影响**：计算结果不稳定，置信度低
- **应对**：增大遗忘因子（forgetting_factor从0.98提高到0.995），减缓参数更新速度

**风险4：置信度低**
- **表现**：confidence_score < 0.3
- **概率**：高（样本数 < 10000时）
- **影响**：参数可靠性低，不适合用于生产环境
- **应对**：在UI中显示置信度，提醒用户参数可靠性低

#### 1.3.2 应对措施

**措施1：参数范围约束**（已实现）
- 在 calculation_parameters 表中设置 param_min 和 param_max
- 在 parameter_optimizer.py 中检查优化后的参数是否在范围内
- 超出范围时，记录警告日志，回滚到上一次有效值

**措施2：置信度阈值**（需要实现）
- 设置置信度阈值（如 0.5）
- 只有 confidence_score ≥ 0.5 的参数才会被使用
- confidence_score < 0.5 的参数继续使用初始值

**措施3：参数变化率限制**（需要实现）
- 限制参数每次优化的变化幅度（如 ±10%）
- 避免参数剧烈震荡

**措施4：优化频率控制**（需要实现）
- 数据不足时，降低优化频率（如每周优化1次，而非每天）
- 数据充足后，提高优化频率（如每天优化1次）

**措施5：人工审核机制**（需要实现）
- 每次优化后，生成优化报告（参数变化、置信度、误差变化）
- 需要人工审核并确认后，才能应用优化结果

### 1.4 阶段1总结

**输出文档**：
- ✅ 数据补充要求说明（最少数据量、数据质量标准）
- ✅ 数据不足时的风险清单和应对措施
- ✅ 数据补充策略（等待实时数据/导入历史数据/模拟数据）

**暂停点**：
- ⏸️ **CP-01**：用户确认数据补充策略

**下一步**：
- 等待用户确认数据补充策略后，进入阶段2

---

## 阶段2：设备级参数配置

### 2.1 目标
为设备1-7配置设备级参数，修改迁移脚本072使用准确的设备级参数（从 device_rated_params 表获取）。

### 2.2 前置条件
- ✅ device_rated_params 表有数据（46行，7台设备，11个参数）
- ✅ calculation_parameters 表有全局参数（50个）
- ✅ dim_devices 表有设备信息（8台设备，7台活跃）

### 2.3 备份策略 🟡

#### 步骤 2.3.1：备份 calculation_parameters 表

**文件**：无（使用 Python 代码）

**操作**：
```python
from app.services.ingest.prepare_dim.backup import BackupManager
from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings

settings = Settings()
backup_manager = BackupManager()

with get_conn(settings) as conn:
    with conn.cursor() as cur:
        result = backup_manager.backup_tables(cur, ["calculation_parameters"])
        print(f"备份结果: {result}")
```

**预期结果**：
- 备份文件创建成功：`backups/calculation_parameters/calculation_parameters_v{version}_{timestamp}_{md5}.sql`
- 备份文件大小 > 10KB
- 备份文件包含50行数据

**风险等级**：🟡 中风险

**🟡 验证检查点 CP-02：验证备份成功**

**验证方法**：
```python
from pathlib import Path
backup_dir = Path("backups/calculation_parameters")
backup_files = sorted(backup_dir.glob("calculation_parameters_v*.sql"), reverse=True)
if backup_files:
    latest_backup = backup_files[0]
    print(f"最新备份: {latest_backup}")
    print(f"文件大小: {latest_backup.stat().st_size} bytes")
    assert latest_backup.stat().st_size > 10000, "备份文件太小"
else:
    raise Exception("错误：没有找到备份文件")
```

**验证通过标准**：
- 备份文件存在
- 备份文件大小 > 10KB

**失败时的回滚步骤**：
- 如果备份失败，停止执行，不进行后续步骤
- 检查 backups 目录权限
- 检查磁盘空间
- 重新执行备份

### 2.4 修改迁移脚本072 🟡

#### 步骤 2.4.1：创建修订版迁移脚本

**文件**：`scripts/sql/migrations/072_add_device_level_calculation_params_v2.sql`

**操作**：已创建（见上方生成的文件）

**修改内容**：
1. 设备范围从1-6扩展到1-7（包含总管）
2. 步骤1：复制全局参数到设备级（作为基础）
3. 步骤2：从 device_rated_params 表更新准确的设备级参数（eta_motor, eta_vfd, pole_pairs, f_ref）

**预期结果**：
- 新文件创建成功
- 文件大小约 10KB

**风险等级**：🟢 低风险（只是创建文件，未执行）

### 2.5 执行迁移脚本 🔴

#### 步骤 2.5.1：执行迁移脚本072_v2

**文件**：`scripts/sql/migrations/072_add_device_level_calculation_params_v2.sql`

**操作**：
```bash
psql -h localhost -U postgres -d your_database -f scripts/sql/migrations/072_add_device_level_calculation_params_v2.sql
```

**预期结果**：
- 插入约175行设备级参数（7台设备 × 8个方法 × 平均3个参数/方法）
- 从 device_rated_params 更新约28行参数（7台设备 × 4个参数）
- 输出验证信息：设备数量7台，方法数量8个，参数总数约175行

**风险等级**：🔴 高风险

**⚠️ 注意事项**：
- 先在测试环境执行，验证后再在生产环境执行
- 执行前确保已备份 calculation_parameters 表（CP-02）
- 执行后立即验证结果（CP-03）

**🟡 验证检查点 CP-03：验证迁移脚本执行成功**

**验证方法**：
```sql
-- 验证1：检查设备级参数总数
SELECT COUNT(*) as device_level_params
FROM calculation_parameters
WHERE device_id IS NOT NULL;
-- 预期结果：约175行

-- 验证2：检查每台设备的参数数量
SELECT 
    device_id,
    COUNT(*) as param_count,
    COUNT(DISTINCT method_id) as method_count
FROM calculation_parameters
WHERE device_id IS NOT NULL
GROUP BY device_id
ORDER BY device_id;
-- 预期结果：每台设备约25行参数，8个方法

-- 验证3：检查从 device_rated_params 更新的参数
SELECT 
    device_id,
    param_name,
    param_value,
    updated_by
FROM calculation_parameters
WHERE updated_by LIKE 'migration:072_v2:step2:from_rated_params:%'
ORDER BY device_id, param_name;
-- 预期结果：约28行（7台设备 × 4个参数）
```

**验证通过标准**：
- 设备级参数总数约175行
- 每台设备约25行参数，8个方法
- 从 device_rated_params 更新的参数约28行

**失败时的回滚步骤**：
```python
# 回滚到备份
from app.services.ingest.prepare_dim.backup import BackupManager
from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import Settings

settings = Settings()
backup_manager = BackupManager()

with get_conn(settings) as conn:
    with conn.cursor() as cur:
        # 清空表
        cur.execute("TRUNCATE TABLE calculation_parameters CASCADE;")
        
        # 恢复备份
        result = backup_manager.restore_table(cur, "calculation_parameters")
        print(f"恢复结果: {result}")
        
        conn.commit()
```

### 2.6 验证参数加载功能 🟡

#### 步骤 2.6.1：验证 orchestrator.py 的 load_parameters() 方法

**文件**：`app/services/calculation/orchestrator.py`

**操作**：运行单元测试或集成测试

**测试代码**（示例）：
```python
from app.services.calculation.orchestrator import CalculationOrchestrator
from app.core.config.loader_new import Settings

settings = Settings()
orchestrator = CalculationOrchestrator(enable_adaptive=True, enable_optimization=False)

# 测试：加载设备1的 EFF_SIMPLE_V1 方法参数
params = orchestrator.load_parameters(device_id=1, method_id='EFF_SIMPLE_V1', station_id=1)

print(f"加载的参数: {params}")
print(f"eta_motor: {params.get('eta_motor')}")  # 应该是设备1的准确值（从 device_rated_params）
print(f"rho: {params.get('rho')}")  # 应该是全局参数值（1000.0）
```

**预期结果**：
- 参数加载成功
- eta_motor 是设备1的准确值（从 device_rated_params）
- rho 是全局参数值（1000.0）

**风险等级**：🟡 中风险

**🟡 验证检查点 CP-04：验证参数加载功能正常**

**验证通过标准**：
- 参数加载成功，无异常
- 设备级参数优先级高于全局参数（eta_motor 使用设备级值）
- 全局参数正常加载（rho 使用全局值）

**失败时的回滚步骤**：
- 检查 orchestrator.py 的 load_parameters() 方法是否正常
- 检查数据库连接是否正常
- 检查 calculation_parameters 表数据是否正确

### 2.7 阶段2总结

**完成的步骤**：
- ✅ 备份 calculation_parameters 表（CP-02）
- ✅ 创建修订版迁移脚本072_v2
- ✅ 执行迁移脚本072_v2（CP-03）
- ✅ 验证参数加载功能正常（CP-04）

**输出文件**：
- `scripts/sql/migrations/072_add_device_level_calculation_params_v2.sql`
- `backups/calculation_parameters/calculation_parameters_v{version}_{timestamp}_{md5}.sql`

**下一步**：
- 进入阶段3：参数优化启用

---

## 阶段3：参数优化启用

（由于篇幅限制，阶段3-5的详细步骤将在后续文件中补充）

**阶段3概要**：
- 修改 orchestrator.py 启用参数优化（enable_optimization=True）
- 添加参数优化监控和回滚机制
- 验证参数优化功能正常

**阶段4概要**：
- 修改相关代码完善审计字段（updated_by、notes）
- 验证审计字段正常记录

**阶段5概要**：
- 创建参数优化监控仪表板
- 创建参数回滚脚本
- 验证监控和回滚机制正常

---

## 执行检查清单（Checklist）

### 阶段1：数据补充要求说明
- [ ] 1.1 阅读数据补充要求说明
- [ ] 1.2 阅读数据不足时的风险和应对措施
- [ ] 1.3 ⏸️ CP-01：用户确认数据补充策略

### 阶段2：设备级参数配置
- [ ] 2.1 备份 calculation_parameters 表
- [ ] 2.2 🟡 CP-02：验证备份成功
- [ ] 2.3 创建修订版迁移脚本072_v2
- [ ] 2.4 执行迁移脚本072_v2
- [ ] 2.5 🟡 CP-03：验证迁移脚本执行成功
- [ ] 2.6 验证参数加载功能正常
- [ ] 2.7 🟡 CP-04：验证参数加载功能正常

### 阶段3：参数优化启用
- [ ] 3.1 ⏸️ CP-05：用户确认启用参数优化
- [ ] 3.2 修改 orchestrator.py 启用参数优化
- [ ] 3.3 🟡 CP-06：验证参数优化代码修改成功
- [ ] 3.4 首次运行参数优化
- [ ] 3.5 🔴 CP-07：验证参数优化功能正常

### 阶段4：审计字段完善
- [ ] 4.1 修改相关代码完善审计字段
- [ ] 4.2 🟡 CP-08：验证审计字段完善成功

### 阶段5：风险控制措施和应急预案
- [ ] 5.1 创建参数优化监控仪表板
- [ ] 5.2 创建参数回滚脚本
- [ ] 5.3 🟡 CP-09：验证监控和回滚机制

---

## 文档结束

**下一步**：等待用户确认 CP-01（数据补充策略），然后开始执行阶段2。

