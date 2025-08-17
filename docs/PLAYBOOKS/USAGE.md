# PLAYBOOKS 使用说明（自动化记忆与变更记录）

## 1. 触发关键词（看到即执行三步）

- 记录变更 / 更新 PLAYBOOKS / 保存记忆 / 按照 PLAYBOOKS 流程完成 / 记忆和文档都更新了吗？ / PLAYBOOKS
- 同义词（可选）：记录决策 / 记录配置变更 / 记录改进 / 记录经验教训 / 记录性能基准

## 2. 三步流程（标准动作）

1. 更新 PLAYBOOKS：在 DECISIONS / CONFIGURATION_CHANGES / IMPROVEMENTS / LESSONS_LEARNED / PERFORMANCE_BENCHMARKS 中记录对应条目
1. 保存关键记忆：将重要约束/决策/路径以持久化方式保存（本地 + 云端）
1. 同步文档：将本次变更反映到相关 docs/ 中文文档（总览/计划/数据库/函数参考/测试/质量）

## 3. 条目模板

- 决策（DECISIONS）

```
---
id: DEC-YYYYMMDD-XXX
date: YYYY-MM-DD
scope: <范围，例如 docs-refactor | time-alignment | scheduling>
summary: <一句话总结>
---
- 背景：<问题与上下文>
- 决策：<选择的方案>
- 影响：<对系统/流程/文档的影响>
```

- 配置变更（CONFIGURATION_CHANGES）

```
---
id: CONF-YYYYMMDD-XXX
date: YYYY-MM-DD
module: <模块，例如 db | docs | scheduler>
summary: <一句话总结>
---
- 变更内容：<配置/脚本/作业>
- 回滚方案：<如需撤销的操作步骤>
```

- 改进（IMPROVEMENTS）

```
---
id: IMP-YYYYMMDD-XXX
date: YYYY-MM-DD
area: <领域，例如 docs | perf | testing>
summary: <一句话总结>
---
- 痛点：<问题>
- 动作：<做了什么>
- 效果：<指标或可见改进>
```

- 经验教训（LESSONS_LEARNED）

```
---
id: LES-YYYYMMDD-XXX
date: YYYY-MM-DD
scope: <范围>
summary: <一句话总结>
---
- 事件：<发生了什么>
- 根因：<根本原因>
- 教训：<得到的经验>
- 行动：<如何避免再次发生>
```

- 性能基准（PERFORMANCE_BENCHMARKS）

```
---
id: BENCH-YYYYMMDD-XXX
date: YYYY-MM-DD
scenario: <场景描述>
summary: <一句话结论>
---
- before：<关键指标>
- after：<关键指标>
- 收益与回滚：<收益/回滚条件>
```

## 4. 操作守则

- 真实唯一：所有事实以数据库与 scripts/sql 为准；文档必须与之同步
- 小步快跑：每次变更都要记录，不堆积
- 可回滚：每条配置变更必须附回滚方案
- 提交信息规范：在 commit message 中引用 PLAYBOOKS ID（如 DEC-20250816-010）
- PR 模板：包含 PLAYBOOKS 链接、影响文档列表、回滚方案（CONF 必填）

## 5. 示例（节选）

- 文档中文化重构：DEC-20250816-009 / CONF-20250816-007 / IMP-20250816-006（已登记）

## 6. 常见问题

- 忘记记录：回溯补记，并在改进中说明影响与补救
- 记录不一致：以数据库与脚本为准，修正文档并补登记
