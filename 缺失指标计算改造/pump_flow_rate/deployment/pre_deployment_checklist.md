# pump_flow_rate 重构 - 部署前检查清单

## 📋 部署前检查

### 1. 数据库检查

- [ ] calculation_logs 表已创建
- [ ] 30个分区已创建
- [ ] 5个索引已创建
- [ ] 分区维护函数已创建
- [ ] f_thr 和 p_thr 参数已删除
- [ ] 12个新参数已初始化

**验证命令**:
```sql
-- 检查表
SELECT COUNT(*) FROM pg_tables WHERE tablename = 'calculation_logs';

-- 检查分区
SELECT COUNT(*) FROM pg_tables WHERE tablename LIKE 'calculation_logs_%';

-- 检查索引
SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'calculation_logs';

-- 检查参数
SELECT COUNT(*) FROM calculation_parameters 
WHERE metric_key = 'pump_flow_rate' 
  AND station_id IS NULL 
  AND device_id IS NULL;
```

### 2. 代码检查

- [ ] 所有新文件已创建（20个Python文件）
- [ ] calculators.py 硬编码阈值已移除
- [ ] orchestrator.py 已标记为 deprecated
- [ ] 无语法错误
- [ ] 导入语句正确

**验证命令**:
```bash
# 检查语法错误
python -m py_compile app/services/calculation/shared/*.py
python -m py_compile app/services/calculation/metrics/pump_flow_rate/*.py
python -m py_compile app/services/calculation/metrics/pump_flow_rate/methods/*.py

# 检查导入
python -c "from app.services.calculation.shared import Scheduler, DataWriter, ParameterManager, SharedServices"
python -c "from app.services.calculation.metrics.pump_flow_rate import PumpFlowRatePipeline"
```

### 3. 测试检查

- [ ] 单元测试已创建
- [ ] 集成测试已创建
- [ ] 测试数据已准备
- [ ] 所有测试通过（待实现后执行）

**验证命令**:
```bash
# 运行测试（待实现后执行）
pytest tests/services/calculation/metrics/pump_flow_rate/ -v
pytest tests/services/calculation/shared/ -v
pytest tests/services/calculation/test_integration.py -v
```

### 4. 文档检查

- [ ] 任务跟踪文档已更新
- [ ] 检查清单已更新
- [ ] 完成追踪表已更新
- [ ] README 已更新

### 5. 配置检查

- [ ] 数据库连接配置正确
- [ ] 日志配置正确
- [ ] 参数配置正确

---

## 🚀 部署步骤

### 步骤1：备份

```bash
# 备份数据库
pg_dump -h localhost -U postgres -d pump_station_optimization > backup_$(date +%Y%m%d_%H%M%S).sql

# 备份代码
git commit -am "Backup before pump_flow_rate refactoring deployment"
git tag "pre-pump-flow-rate-refactor-$(date +%Y%m%d)"
```

### 步骤2：执行数据库迁移

```bash
cd 缺失指标计算改造/pump_flow_rate/migrations

# 执行迁移
python -m app.cli.database execute-migration --file 001_create_calculation_logs.sql
python -m app.cli.database execute-migration --file 002_delete_garbage_parameters.sql
python -m app.cli.database execute-migration --file 003_verification_tests.sql
python -m app.cli.database execute-migration --file 004_initialize_parameters.sql
```

### 步骤3：部署代码

```bash
# 重启应用（如果需要）
# systemctl restart pump_station_app
```

### 步骤4：验证部署

```bash
# 运行验证脚本
python 缺失指标计算改造/pump_flow_rate/deployment/verify_deployment.py
```

---

## ✅ 部署后验证

- [ ] 数据库表和索引正常
- [ ] 参数加载正常
- [ ] 日志记录正常
- [ ] 计算结果正确
- [ ] 性能符合预期

---

## 🔄 回滚计划

如果部署失败，执行以下回滚步骤：

```bash
# 1. 回滚数据库
python -m app.cli.database execute-migration --file 004_rollback_initialize_parameters.sql
python -m app.cli.database execute-migration --file 002_rollback_delete_garbage_parameters.sql
python -m app.cli.database execute-migration --file 001_rollback_calculation_logs.sql

# 2. 回滚代码
git revert HEAD
# 或
git reset --hard pre-pump-flow-rate-refactor-<tag>

# 3. 重启应用
# systemctl restart pump_station_app
```

