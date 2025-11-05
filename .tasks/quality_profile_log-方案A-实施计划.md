# quality_profile_log 表注释补全计划（方案A）

> **创建时间**: 2025-09-30  
> **计划模式**: RIPER-5 协议 - 计划阶段  
> **方案**: 方案A - 最小化补全方案  
> **状态**: 待执行

---

## 📋 计划概述

### 目标
为 `quality_profile_log` 表补全所有缺失的字段注释，并丰富表级注释，使其符合项目数据库规范要求。

### 范围
1. **补全7个缺失注释的字段**
2. **丰富表级注释**（增加使用场景、关联模块说明）
3. **优化1个注释不够详细的字段**（device_id）

### 实施方式
- 执行 `COMMENT ON COLUMN` 语句添加字段注释
- 执行 `COMMENT ON TABLE` 语句更新表注释
- **不修改表结构**，仅变更元数据

### 预期成果
- **字段注释完整率**: 36.4% (4/11) → **100%** (11/11)
- **符合规范**: 满足项目数据库规范"关键列必须有注释"的强制要求
- **零风险**: 仅元数据变更，不影响现有代码和数据

---

## 🔍 规范依据

### 数据库规范要求（强制）
根据 `.memory/规则层/数据库规范.md` 第6.2节：

- ✅ **关键列必须有注释**（主键、外键、业务字段）
- ✅ **注释语言**: 必须使用中文
- ✅ **注释内容**: 说明字段的含义、单位、取值范围

### 注释编写原则
1. **准确性**: 基于代码实际使用情况编写
2. **完整性**: 包含字段含义、单位（如有）、取值范围（如有）
3. **简洁性**: 避免冗余信息，一句话说清楚
4. **一致性**: 与项目其他表的注释风格保持一致

---

## 📊 字段注释详细规划

### 1. window_start（时间窗口开始时间）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，传入参数 `p_start`
- **读取**: `mark_window.py` 查询条件 `WHERE window_start >= %s`
- **用途**: 标识质量标注窗口的起始时间（UTC时区）

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.window_start IS 
'时间窗口开始时间（UTC时区，质量标注的起始时间戳）';
```

**验证要点**:
- ✅ 字段类型: `timestamptz` (已确认)
- ✅ 非空约束: `NOT NULL` (已确认)
- ✅ 实际用途: 质量标注窗口起始边界

---

### 2. window_end（时间窗口结束时间）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，传入参数 `p_end`
- **读取**: `mark_window.py` 查询条件 `WHERE window_end <= %s`
- **用途**: 标识质量标注窗口的结束时间（UTC时区）

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.window_end IS 
'时间窗口结束时间（UTC时区，质量标注的结束时间戳）';
```

**验证要点**:
- ✅ 字段类型: `timestamptz` (已确认)
- ✅ 非空约束: `NOT NULL` (已确认)
- ✅ 实际用途: 质量标注窗口结束边界

---

### 3. station_id（泵站ID）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，传入参数 `p_station_id`
- **读取**: 未在查询条件中使用（仅写入）
- **外键约束**: `FOREIGN KEY (station_id) REFERENCES dim_stations(id) ON UPDATE CASCADE ON DELETE CASCADE`
- **用途**: 关联泵站维表，标识质量标注所属的泵站

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.station_id IS 
'泵站ID（外键，关联dim_stations表，标识质量标注所属的泵站）';
```

**验证要点**:
- ✅ 字段类型: `bigint` (已确认)
- ✅ 外键约束: 已确认指向 `dim_stations(id)`
- ✅ 可空性: `NULL` (允许为空)

---

### 4. device_id（设备ID）

**当前状态**: ⚠️ 有注释但不够详细

**现有注释**: "设备ID:画像所属的设备ID"

**问题分析**:
- 未说明是外键
- 未说明关联的表
- "画像"一词不够准确（应为"质量标注"）

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，传入参数 `p_device_id`
- **读取**: 未在查询条件中使用（仅写入）
- **外键约束**: `FOREIGN KEY (device_id) REFERENCES dim_devices(id) ON UPDATE CASCADE ON DELETE CASCADE`
- **用途**: 关联设备维表，标识质量标注所属的设备

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.device_id IS 
'设备ID（外键，关联dim_devices表，标识质量标注所属的设备）';
```

**验证要点**:
- ✅ 字段类型: `bigint` (已确认)
- ✅ 外键约束: 已确认指向 `dim_devices(id)`
- ✅ 可空性: `NULL` (允许为空)

---

### 5. stage（执行阶段标识）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，写入值如 `'fwin_build'`, `'update_101'`, `'update_751'` 等
- **读取**: `mark_window.py` 查询条件 `WHERE stage LIKE 'update_%%'`，并通过 `split_part(stage, '_', 2)` 解析质量码
- **用途**: 标识质量标注流程中的具体执行阶段（如窗口构建、质量规则更新等）

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.stage IS 
'执行阶段标识（如fwin_build表示窗口构建，update_XXX表示质量规则XXX的更新阶段）';
```

**验证要点**:
- ✅ 字段类型: `text` (已确认)
- ✅ 非空约束: `NOT NULL` (已确认)
- ✅ 实际值: 已确认包含 `fwin_build`, `update_101`, `update_111`, `update_751` 等

---

### 6. duration_ms（执行耗时）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，计算值为 `EXTRACT(MILLISECOND FROM (clock_timestamp()-v_t))`
- **读取**: 未在查询中使用（仅写入）
- **用途**: 记录该阶段的执行耗时（毫秒）

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.duration_ms IS 
'执行耗时（毫秒，记录该阶段从开始到结束的时间消耗）';
```

**验证要点**:
- ✅ 字段类型: `numeric` (已确认)
- ✅ 可空性: `NULL` (允许为空)
- ✅ 实际值: 已确认为毫秒级数值

---

### 7. rows_affected（影响行数）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，写入值为 `GET DIAGNOSTICS v_rc = ROW_COUNT` 获取的行数
- **读取**: `mark_window.py` 聚合查询 `SUM(rows_affected)::bigint AS cnt`
- **用途**: 记录该阶段影响的数据行数（如更新了多少条质量码）

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.rows_affected IS 
'影响行数（该阶段操作影响的数据行数，如更新质量码的记录数）';
```

**验证要点**:
- ✅ 字段类型: `bigint` (已确认)
- ✅ 可空性: `NULL` (允许为空)
- ✅ 实际用途: 用于统计质量规则命中数量

---

### 8. details（详细信息）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: `sp_mark_quality_window_vfast` 存储过程，所有写入都是 `NULL`
- **读取**: 未在查询中使用
- **用途**: 预留字段，用于存储额外的JSON格式详细信息（当前未使用）

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.details IS 
'详细信息（JSONB格式，预留字段，用于存储额外的执行细节，当前未使用）';
```

**验证要点**:
- ✅ 字段类型: `jsonb` (已确认)
- ✅ 可空性: `NULL` (允许为空)
- ✅ 实际值: 所有记录都是 `NULL`

---

### 9. code（质量规则代码）

**当前状态**: ❌ 无注释

**代码使用分析**:
- **写入**: 通过触发器 `trg_qprof_set_code` 自动填充，解析 `stage` 字段得出
- **读取**: 索引 `idx_qprof_time_dev_code` 使用该字段优化查询
- **用途**: 质量规则代码（如101、111、751等），从stage字段自动解析得出，用于优化查询性能

**拟定注释**:
```sql
COMMENT ON COLUMN public.quality_profile_log.code IS 
'质量规则代码（整数，如101、111、751等，由触发器从stage字段自动解析填充，用于优化查询）';
```

**验证要点**:
- ✅ 字段类型: `integer` (已确认)
- ✅ 可空性: `NULL` (允许为空)
- ✅ 触发器: 已确认存在 `trg_qprof_set_code` 触发器

---

## 📝 表级注释规划

### 当前表注释
```sql
COMMENT ON TABLE public.quality_profile_log IS 
'质量过程性能剖析日志(按窗口/阶段记录耗时与行数)';
```

### 问题分析
- ✅ 已有注释，但不够详细
- ❌ 未说明该表与质量标注流程的关系
- ❌ 未说明使用场景和关联模块
- ❌ 未说明数据保留策略

### 拟定新注释
```sql
COMMENT ON TABLE public.quality_profile_log IS $DOC$
质量过程性能剖析日志（按窗口/阶段记录耗时与行数）

用途: 记录质量标注流程（sp_mark_quality_window_vfast）中每个执行阶段的性能指标，
包括窗口构建、各质量规则更新等阶段的耗时和影响行数。

使用场景:
- 性能监控: 分析质量标注流程的性能瓶颈
- 统计分析: 汇总各质量规则的命中数量（通过rows_affected聚合）
- 故障排查: 定位质量标注过程中的异常阶段

关联模块:
- 写入: sp_mark_quality_window_vfast 存储过程
- 读取: app/services/quality/mark_window.py（质量规则命中统计）
- 读取: scripts/verify_quality_counts.py（质量统计验证）

数据特征:
- 写入频率: 每次质量标注窗口执行时写入约15条记录（对应15个阶段）
- 数据增长: 持续增长，建议定期归档或清理历史数据
$DOC$;
```

---

## ✅ 执行检查清单

### 执行前检查
- [ ] 确认数据库连接正常
- [ ] 确认当前用户有 COMMENT 权限
- [ ] 备份当前表注释（通过查询 pg_description）
- [ ] 验证所有字段名拼写正确

### 执行步骤
1. [ ] 执行表级注释更新（1条语句）
2. [ ] 执行字段注释更新（9条语句，包含1条优化）
3. [ ] 验证注释已成功添加（查询 pg_description）
4. [ ] 验证注释内容准确性（人工审查）

### 执行后验证
- [ ] 查询所有字段注释，确认无遗漏
- [ ] 查询表注释，确认内容完整
- [ ] 检查注释语言是否全部为中文
- [ ] 检查注释是否符合项目规范

### 回滚方案
如发现注释有误，可通过以下方式回滚:
```sql
-- 恢复原表注释
COMMENT ON TABLE public.quality_profile_log IS 
'质量过程性能剖析日志(按窗口/阶段记录耗时与行数)';

-- 删除错误的字段注释
COMMENT ON COLUMN public.quality_profile_log.字段名 IS NULL;
```

---

## 📄 SQL实施脚本（待执行模式生成）

**注意**: 以下SQL脚本将在**执行模式**中生成并执行，此处仅作为计划参考。

### 脚本结构
1. 表级注释更新（1条）
2. 字段注释更新（9条）
3. 验证查询（2条）

### 预期执行时间
- 执行时间: < 1秒（仅元数据变更）
- 锁定影响: 无（COMMENT 操作不锁表）

---

## 🎯 成功标准

### 功能性标准
- ✅ 所有11个字段都有注释
- ✅ 表级注释包含用途、使用场景、关联模块说明
- ✅ 所有注释使用中文
- ✅ 注释内容准确反映实际用途

### 质量标准
- ✅ 符合项目数据库规范（`.memory/规则层/数据库规范.md`）
- ✅ 注释简洁清晰，无冗余信息
- ✅ 注释风格与项目其他表保持一致

### 验收标准
- ✅ 通过代码审查
- ✅ 通过业务确认（注释准确性）
- ✅ 通过规范检查（中文、格式、完整性）

---

## 📊 风险评估

### 风险等级: 极低

### 风险分析
1. **技术风险**: 无（仅元数据变更，不影响数据和代码）
2. **业务风险**: 无（不影响现有功能）
3. **性能风险**: 无（COMMENT 操作不影响查询性能）
4. **回滚风险**: 极低（可随时修改注释）

### 注意事项
1. **注释准确性**: 必须基于代码实际使用情况编写，避免误导
2. **注释维护**: 后续代码变更时需同步更新注释
3. **审查确认**: 注释编写后需经过代码审查和业务确认

---

## 📅 实施时间表

### 预计时间
- **计划阶段**: 已完成
- **执行阶段**: 5分钟（生成SQL + 执行 + 验证）
- **审查阶段**: 10分钟（代码审查 + 业务确认）
- **总计**: 15分钟

### 里程碑
1. ✅ 计划完成（当前）
2. ⏳ 用户确认计划
3. ⏳ 执行SQL脚本
4. ⏳ 验证结果
5. ⏳ 代码审查
6. ⏳ 完成

---

**计划模式已完成，等待用户确认后进入执行模式。**

