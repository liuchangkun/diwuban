# Memory MCP 使用规范

> MCP Memory 工具使用标准和最佳实践
>
> 创建时间：2025-12-16
> 状态：✅ 已定义标准

---

## 📋 目录

- [概述](#概述)
- [核心概念](#核心概念)
- [使用标准](#使用标准)
- [实体定义](#实体定义)
- [关系定义](#关系定义)
- [使用场景](#使用场景)
- [最佳实践](#最佳实践)
- [示例](#示例)

---

## 🎯 概述

Memory MCP 是一个知识图谱工具，用于持久化项目知识，避免重复读取代码和文档。

### 核心优势

- ✅ **持久化知识**：跨会话保存项目理解
- ✅ **减少Token消耗**：避免重复读取代码（节省70-90%）
- ✅ **快速检索**：基于关系的知识查询
- ✅ **自动更新**：配合Git Hooks自动维护

### 使用原则

1. **结构化优先**：使用实体-关系模型，不是自由文本
2. **增量更新**：仅记录变更，不重复记录
3. **分层管理**：区分架构/业务/实现层级
4. **及时维护**：每次重大变更后更新

---

## 🧩 核心概念

### 实体（Entity）

实体是知识图谱的节点，代表项目中的关键概念。

**实体类型**：
- **架构实体**：模块、服务、组件
- **业务实体**：业务流程、指标、规则
- **技术实体**：类、函数、API、数据表
- **文档实体**：规范、指南、决策记录

### 关系（Relation）

关系是实体之间的连接，描述它们如何相互作用。

**关系类型**：
- **依赖关系**：depends_on, uses, imports
- **层级关系**：contains, part_of, belongs_to
- **实现关系**：implements, extends, overrides
- **数据流**：reads_from, writes_to, transforms
- **文档关系**：documents, specifies, defines

### 观察（Observation）

观察是对实体的额外说明，用于记录细节信息。

**适用场景**：
- 实体的详细描述
- 设计决策和原因
- 性能特征
- 已知问题和限制

---

## 📐 使用标准

### 1. 实体命名规范

**格式**：`{层级}::{类型}::{名称}`

**示例**：
```
architecture::module::characteristic_curves
service::component::CurveFittingPipeline
business::metric::pump_efficiency
data::table::pump_characteristic_curves
doc::spec::encoding_standard
```

**层级定义**：
- `architecture` - 架构层
- `service` - 服务层
- `business` - 业务层
- `data` - 数据层
- `doc` - 文档层
- `tool` - 工具层

**类型定义**：
- `module` - 模块
- `component` - 组件
- `class` - 类
- `function` - 函数
- `api` - API接口
- `table` - 数据表
- `metric` - 业务指标
- `process` - 业务流程
- `spec` - 规范
- `guide` - 指南

### 2. 关系命名规范

**格式**：`{动词}_{对象}`（使用下划线分隔）

**常用关系**：

| 关系名 | 说明 | 示例 |
|--------|------|------|
| `depends_on` | A依赖B | PipelineService depends_on DatabaseGateway |
| `contains` | A包含B | ModuleA contains ComponentB |
| `implements` | A实现B | ConcreteClass implements Interface |
| `uses` | A使用B | ServiceA uses UtilityB |
| `reads_from` | A从B读取 | Service reads_from Table |
| `writes_to` | A写入B | Service writes_to Table |
| `documents` | A文档化B | SpecDoc documents Feature |
| `validates` | A验证B | Validator validates Data |
| `transforms` | A转换B | Transformer transforms RawData |

### 3. 观察记录规范

**格式**：结构化的Markdown文本

**必需字段**：
- **描述**：简明扼要的说明（1-2句）
- **职责**：主要功能和责任
- **关键特性**：重要特征（列表）
- **限制**：已知限制和注意事项

**可选字段**：
- **设计决策**：为什么这样设计
- **性能特征**：性能相关信息
- **依赖项**：外部依赖
- **示例**：使用示例

---

## 🗂️ 实体定义

### 架构层实体

#### 模块实体

```typescript
实体: architecture::module::characteristic_curves
观察: |
  描述: 泵特性曲线分析模块
  职责:
    - 曲线拟合和分析
    - 泵组性能评估
    - 异常检测
  关键特性:
    - 支持多种拟合方法（数学/物理/ML）
    - 自动方法选择
    - 高精度拟合（R²>0.95）
  依赖项:
    - NumPy, SciPy
    - scikit-learn
    - PostgreSQL
```

### 服务层实体

#### 组件实体

```typescript
实体: service::component::CurveFittingPipeline
观察: |
  描述: 曲线拟合主流程管理器
  职责:
    - 数据预处理
    - 方法选择
    - 拟合执行
    - 结果验证
  文件位置: app/services/characteristic_curves/pipeline/curve_fitting_pipeline.py
  关键方法:
    - process() - 主处理流程
    - validate_data() - 数据验证
    - select_method() - 方法选择
```

### 业务层实体

#### 指标实体

```typescript
实体: business::metric::pump_efficiency
观察: |
  描述: 泵运行效率指标
  计算公式: η = (ρ * g * Q * H) / (1000 * P)
  单位: 百分比
  正常范围: 60% - 85%
  关键影响因素:
    - 流量偏离额定值
    - 扬程变化
    - 设备老化
```

### 数据层实体

#### 表实体

```typescript
实体: data::table::pump_characteristic_curves
观察: |
  描述: 泵特性曲线结果存储表
  主键: device_id, curve_type, time_window_start
  索引:
    - btree(device_id, time_window_start)
    - brin(time_window_start)
  分区策略: 按月分区
  数据保留: 2年
  关键字段:
    - curve_coefficients (JSONB) - 曲线系数
    - r_squared (FLOAT) - 拟合优度
    - method_used (TEXT) - 使用的方法
```

### 文档层实体

#### 规范实体

```typescript
实体: doc::spec::encoding_standard
观察: |
  描述: 项目编码规范
  文件位置: docs/编码规范.md
  关键要求:
    - 100% 类型注解
    - SQL参数化（%s占位符）
    - SOLID原则
    - 结构化日志
  工具链:
    - Ruff (lint + format)
    - MyPy (类型检查)
    - Bandit (安全扫描)
```

---

## 🔗 关系定义

### 依赖关系示例

```typescript
// 服务依赖数据库网关
service::component::CurveFittingPipeline
  depends_on
data::component::DatabaseGateway

// 管道使用拟合方法
service::component::CurveFittingPipeline
  uses
service::component::PolynomialMethod

// 方法读取数据表
service::component::CurveFittingPipeline
  reads_from
data::table::device_running_data

// 方法写入结果表
service::component::CurveFittingPipeline
  writes_to
data::table::pump_characteristic_curves
```

### 文档关系示例

```typescript
// 规范文档化模块
doc::spec::encoding_standard
  documents
architecture::module::characteristic_curves

// 指南定义流程
doc::guide::development_workflow
  defines
business::process::feature_development

// API规范定义接口
doc::spec::api_specification
  specifies
service::api::curve_fitting_endpoint
```

---

## 🎯 使用场景

### 场景1：新成员加入项目

**目标**：快速了解项目架构

**操作**：
1. 查询所有架构模块：
   ```
   list entities where type="architecture::module"
   ```

2. 查询模块依赖关系：
   ```
   query relations from "architecture::module::characteristic_curves"
   ```

3. 查看核心组件：
   ```
   get entity "service::component::CurveFittingPipeline"
   ```

### 场景2：重构代码模块

**目标**：了解影响范围

**操作**：
1. 查询所有依赖此模块的组件：
   ```
   query entities depending_on "service::component::TargetComponent"
   ```

2. 查询被依赖的组件：
   ```
   query entities used_by "service::component::TargetComponent"
   ```

3. 记录重构决策：
   ```
   add observation to "service::component::TargetComponent"
   content: "重构原因: 提高性能，拆分职责"
   ```

### 场景3：追踪数据流

**目标**：理解数据处理流程

**操作**：
1. 从源头追踪：
   ```
   query path from "data::table::raw_data"
   to "data::table::pump_characteristic_curves"
   ```

2. 查看转换步骤：
   ```
   list entities where relation="transforms"
   ```

### 场景4：查找文档

**目标**：快速找到相关文档

**操作**：
1. 查询功能相关文档：
   ```
   query entities documenting "architecture::module::characteristic_curves"
   ```

2. 查询规范定义：
   ```
   list entities where type="doc::spec"
   ```

---

## 💡 最佳实践

### 1. 初始化知识图谱

**第一次使用时**，按照以下顺序创建实体：

1. **架构层**：先建立顶层模块
2. **服务层**：再定义核心组件
3. **业务层**：记录业务概念
4. **数据层**：最后映射数据结构
5. **文档层**：关联相关文档

**建议使用脚本**：
```python
# scripts/tools/init_memory.py
def init_knowledge_graph():
    # 1. 创建架构模块
    create_entity("architecture::module::characteristic_curves", ...)

    # 2. 创建核心服务
    create_entity("service::component::CurveFittingPipeline", ...)

    # 3. 建立依赖关系
    create_relation("service::component::CurveFittingPipeline",
                   "depends_on",
                   "data::component::DatabaseGateway")
```

### 2. 增量更新策略

**何时更新**：
- ✅ 新增模块/组件
- ✅ 修改核心架构
- ✅ 重构重要功能
- ✅ 更新文档规范
- ❌ 微小的bug修复（不需要）
- ❌ 注释修改（不需要）

**配合Git Hooks自动化**：
```bash
# .git/hooks/post-commit
if [[ "$COMMIT_MSG" =~ ^feat:|^refactor:|^docs: ]]; then
    python scripts/tools/update_memory.py
fi
```

### 3. 查询优化

**高效查询技巧**：

```typescript
// ❌ 低效：遍历所有实体
list all entities

// ✅ 高效：使用类型过滤
list entities where type="service::component"

// ❌ 低效：递归查询所有依赖
query all relations from "entity_name"

// ✅ 高效：限制深度
query relations from "entity_name" depth=2
```

### 4. 观察记录技巧

**好的观察**：
- ✅ 结构化、清晰
- ✅ 包含关键信息
- ✅ 可快速扫描
- ✅ 包含文件位置

**示例**：
```markdown
描述: 泵特性曲线拟合管道
职责: 数据预处理、方法选择、拟合执行
位置: app/services/characteristic_curves/pipeline/curve_fitting_pipeline.py
关键方法:
  - process() - 主流程
  - validate() - 验证
设计决策: 使用策略模式支持多种拟合方法
性能: 处理1000点数据 <100ms
```

**坏的观察**：
```markdown
❌ 这是一个拟合的东西，用来做曲线的
❌ 很重要的组件
❌ 在某个文件里面
```

### 5. 避免过度记录

**应该记录**：
- ✅ 架构级别的决策
- ✅ 核心业务逻辑
- ✅ 复杂算法和数据流
- ✅ 重要的设计权衡

**不应该记录**：
- ❌ 每个小函数的细节
- ❌ 临时变量和局部逻辑
- ❌ 显而易见的信息
- ❌ 会频繁变更的细节

---

## 📝 示例

### 完整示例：记录曲线拟合模块

```typescript
// 1. 创建模块实体
实体: architecture::module::characteristic_curves
观察: |
  描述: 泵特性曲线分析模块
  职责:
    - Q-H曲线拟合（流量-扬程）
    - Q-P曲线拟合（流量-功率）
    - Q-η曲线拟合（流量-效率）
  关键特性:
    - 支持10+种拟合方法
    - 自动方法选择（基于数据特征）
    - R²>0.95 的高精度拟合
  设计决策: 采用策略模式实现方法可扩展性

// 2. 创建核心组件
实体: service::component::CurveFittingPipeline
观察: |
  描述: 曲线拟合主流程
  位置: app/services/characteristic_curves/pipeline/curve_fitting_pipeline.py
  主要方法:
    - process(device_id, time_window)
    - validate_data(raw_data)
    - select_method(data_characteristics)
  性能: 1000数据点拟合 <100ms

// 3. 建立关系
CurveFittingPipeline depends_on DatabaseGateway
CurveFittingPipeline uses PolynomialMethod
CurveFittingPipeline reads_from device_running_data
CurveFittingPipeline writes_to pump_characteristic_curves

// 4. 创建文档关联
实体: doc::spec::curve_fitting_specification
观察: |
  描述: 曲线拟合技术规范
  位置: 特性曲线开发/端到端验证-技术规范-2025-12-09.md
  关键要求:
    - 最小样本点: 20点
    - 拟合优度: R²>0.9
    - 异常点过滤: 3σ原则

curve_fitting_specification documents characteristic_curves
curve_fitting_specification specifies CurveFittingPipeline
```

---

## 🔄 维护计划

### 定期审查

**频率**：每月一次

**检查项**：
1. 实体是否需要更新
2. 关系是否仍然准确
3. 观察是否过时
4. 是否有新的重要知识需要记录

### 清理策略

**何时删除**：
- 模块已废弃超过3个月
- 文档已归档
- 临时实验代码已删除

**如何清理**：
```bash
# 删除废弃实体
python scripts/tools/cleanup_memory.py --remove-deprecated

# 验证关系完整性
python scripts/tools/validate_memory.py
```

---

## 🎓 学习资源

### MCP Memory文档
- 官方文档：https://github.com/modelcontextprotocol/memory
- API参考：查看MCP Memory工具说明

### 项目相关文档
- [知识管理系统方案.md](知识管理系统方案.md) - 整体知识管理架构
- [AI助手能力提升完整建议清单.md](AI助手能力提升完整建议清单.md) - 工具使用路线图

---

## ✅ 检查清单

在使用Memory MCP之前，确认：

- [ ] 已理解实体-关系模型
- [ ] 已掌握命名规范
- [ ] 已了解何时记录、何时不记录
- [ ] 已配置自动化更新流程
- [ ] 已创建初始知识图谱

---

**维护者**：AI助手
**最后更新**：2025-12-16
**状态**：✅ 已生效
