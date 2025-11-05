# 任务: quality_profile_log 表全面分析

## 任务概述
- **目标**: 全面分析数据库表 `quality_profile_log` 的结构、文档质量和使用情况
- **创建时间**: 2025-09-30
- **模式**: 研究模式

---

## 项目规则摘要

### 数据库规范（已读取）
- **表注释**: 所有表必须有注释（COMMENT ON TABLE），使用中文
- **列注释**: 关键列必须有注释（COMMENT ON COLUMN），包含含义、单位、取值范围
- **命名规范**: 小写+下划线（snake_case），复数形式
- **字段后缀**: `_id`（ID字段）、`_at`（时间字段）、`_ms`（毫秒）、`_sec`（秒）

---

## 记忆检索结果

### 研究模式检索
已通过 `codebase-retrieval` 和 `query_PostgreSQL` 检索到以下信息:
- 表创建脚本: `scripts/sql/migrations/037_create_quality_profile_log.sql`
- 表结构扩展: `scripts/sql/migrations/041_alter_quality_profile_log_add_code.sql`
- 主要使用文件:
  - `app/services/quality/mark_window.py`
  - `scripts/verify_quality_counts.py`
  - `app/services/run_all/orchestrator.py`
- 存储过程: `sp_mark_quality_window_vfast`, `sp_mark_quality_window_vfast_diag`

---

## 记忆验证结果

### 表结构验证（通过 PostgreSQL 查询）
✅ 表存在: `quality_profile_log`
✅ 表注释存在: "质量过程性能剖析日志（按窗口/阶段记录耗时与行数）"
✅ 字段数量: 11个字段
✅ 索引数量: 5个索引
✅ 外键约束: 2个（station_id, device_id）

---

## 代码分析

### 表的业务用途
**核心功能**: 质量标注过程的性能剖析和监控日志表

**业务场景**:
1. **性能监控**: 记录质量标注各阶段的执行时间和影响行数
2. **规则命中统计**: 统计各质量规则（质量码）的命中次数
3. **诊断分析**: 支持质量标注过程的诊断和问题定位
4. **报表生成**: 为质量码分布报表提供数据源

### 写入路径
**主要写入者**: 存储过程 `sp_mark_quality_window_vfast`

**写入时机**: 每个质量检查规则执行后插入一条记录
- `fwin_build`: 窗口临时表构建阶段
- `update_751`: 计数器单调性检查
- `update_701_pf`: 功率因数越界检查
- `update_702_current/voltage`: 三相不平衡检查
- `update_401`: 状态矛盾检查
- `update_101`: 物理越界检查
- `update_111`: 异常跳变检查
- `update_112`: 变化率异常检查
- `update_121`: 平台期检查
- `update_131/132`: 饱和检查
- `update_141`: 量化步长异常检查
- `update_201/202`: 启动/停机异常检查
- `update_301/302/303`: 启动过程异常检查
- `update_401/402/403`: 状态矛盾检查
- `update_501/502/503`: 时间一致性检查
- `update_601/602/603`: 传感器健康检查

### 读取路径
**主要读取者**:
1. **Python代码**:
   - `app/services/quality/mark_window.py`: 读取规则命中摘要
   - `scripts/verify_quality_counts.py`: 验证质量码统计
   - `app/services/run_all/orchestrator.py`: 生成规则级摘要

2. **存储过程**:
   - `sp_mark_quality_window_vfast_diag`: 读取规则命中摘要写入诊断日志

**查询模式**:
```sql
-- 规则命中摘要（最常见）
SELECT split_part(stage, '_', 2)::int AS code, 
       SUM(rows_affected)::bigint AS cnt
FROM public.quality_profile_log
WHERE window_start >= ? AND window_end <= ? 
  AND stage LIKE 'update_%'
GROUP BY split_part(stage, '_', 2)
```

---

## 关键发现

### 1. 表结构完整性
✅ **优点**:
- 主键、索引、外键约束完整
- 表级注释清晰
- 字段命名规范

❌ **缺陷**:
- **11个字段中有7个字段缺少注释**（63.6%缺失率）
- 部分字段注释不够详细

### 2. 字段使用情况分析

#### 高频使用字段
- `window_start`, `window_end`: 时间窗口过滤（所有查询）
- `stage`: 阶段标识（所有查询，用于过滤和解析质量码）
- `rows_affected`: 影响行数统计（所有聚合查询）
- `station_id`, `device_id`: 设备过滤（部分查询）

#### 中频使用字段
- `duration_ms`: 性能监控（写入但较少读取）
- `code`: 质量码（新增字段，用于优化聚合查询）

#### 低频使用字段
- `details`: JSONB详细信息（写入但极少读取）
- `created_at`: 记录创建时间（写入但极少读取）
- `id`: 主键（仅用于唯一标识）

#### 未使用字段
- 无明显未使用字段，所有字段都有其用途

### 3. 索引使用情况
✅ **有效索引**:
- `idx_qprof_time`: 时间范围查询（高频使用）
- `idx_qprof_stage`: 阶段过滤（高频使用）
- `idx_qprof_time_dev_code`: 组合索引（优化聚合查询）

⚠️ **可优化索引**:
- `idx_qprof_device`: 使用频率较低，可考虑合并到组合索引

### 4. 数据质量问题
⚠️ **发现的问题**:
1. **字段注释缺失严重**: 7个字段无注释
2. **stage字段值不规范**: 混合使用 `update_XXX` 和其他格式
3. **code字段冗余**: 可从stage解析，但为性能优化而冗余存储

---

## 需要澄清的问题

1. **details字段用途**: 该JSONB字段在代码中写入NULL，是否有计划使用？
2. **数据保留策略**: 该日志表是否需要定期清理？当前无分区策略
3. **code字段必要性**: 是否所有查询都已迁移到使用code字段？

---

## 创新模式方案选择

用户已选择**方案A（最小化补全方案）**，现进入计划模式制定详细实施计划。

---

## 计划模式 - 实施计划

### 规范文档读取确认
✅ 已读取以下规范文档:
- 项目规则.md
- 编码规范.md
- 质量标准.md
- 数据库规范.md（注释规范章节）

### 计划概述
**目标**: 为 `quality_profile_log` 表补全所有缺失的字段注释和丰富表级注释

**范围**:
1. 补全7个缺失注释的字段
2. 丰富表级注释，增加使用场景说明
3. 优化1个注释不够详细的字段（device_id）

**实施方式**: 执行 ALTER TABLE ... COMMENT 语句

**预期成果**:
- 字段注释完整率: 36.4% → 100%
- 符合项目数据库规范要求
- 零风险（仅元数据变更）

---

## 记忆更新日志

### 研究模式更新
- 创建实体: `quality_profile_log` 表（数据表类型）
- 记录关系:
  - `sp_mark_quality_window_vfast` → 写入 → `quality_profile_log`
  - `mark_window.py` → 读取 → `quality_profile_log`
- 记录观察:
  - 表用途: 质量标注性能剖析日志
  - 主要问题: 字段注释缺失严重（7/11字段无注释）
  - 使用模式: 写入频繁，读取集中在聚合查询

---

📊 **上下文状态**
- **Token使用**: 99,171 / 200,000 (49.6%)
- **对话轮次**: 3轮
- **知识图谱**: 待更新
- **已读文件**: 11个 (规则文档6个, SQL脚本2个, Python代码3个)
- **数据库查询**: 6次
- **记忆文档**: 0个已加载
- **任务文件**: 已创建并更新
- **工具使用**:
  - view: 读取规则文档和代码文件
  - query_PostgreSQL: 验证表结构和数据
  - codebase-retrieval: 检索使用情况
  - save-file/str-replace-editor: 创建和更新任务文件

