# TESTING_STRATEGY（测试策略）

## 1. 范围
- 解析/对齐/质量/派生/拟合/优化/可视化 的单元与集成测试。

## 2. 目标
- 关键模块覆盖率 ≥ 80%；边界与异常场景覆盖。

## 3. 组织
- tests/unit/*：纯函数与小模块
- tests/integration/*：从 data/ 小样到结果的端到端
- tests/perf/*（可选）：大文件/长时间基线

## 4. 工具
- pytest + hypothesis（可选）+ coverage；CI 中与 quality_gate 一起运行。

