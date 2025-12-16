#!/usr/bin/env python3
"""
Memory MCP 初始化示例脚本

演示如何使用Memory MCP记录项目知识图谱
根据 docs/Memory-MCP使用规范.md 编写

用途：
1. 初始化项目知识图谱
2. 记录核心模块和组件
3. 建立依赖关系
4. 演示查询和使用

作者：AI助手
日期：2025-12-16
"""

from typing import Dict, Any


class MemoryMCPExample:
    """Memory MCP 使用示例类"""

    def __init__(self):
        """初始化示例"""
        self.entities = []
        self.relations = []

    def create_entity(self, entity_id: str, observation: str) -> Dict[str, Any]:
        """
        创建实体

        Args:
            entity_id: 实体ID，格式：{层级}::{类型}::{名称}
            observation: 结构化观察信息

        Returns:
            实体字典
        """
        entity = {
            "id": entity_id,
            "observation": observation,
        }
        self.entities.append(entity)
        print(f"✅ 创建实体: {entity_id}")
        return entity

    def create_relation(
        self, from_entity: str, relation_type: str, to_entity: str
    ) -> Dict[str, Any]:
        """
        创建关系

        Args:
            from_entity: 源实体ID
            relation_type: 关系类型（使用下划线分隔）
            to_entity: 目标实体ID

        Returns:
            关系字典
        """
        relation = {
            "from": from_entity,
            "type": relation_type,
            "to": to_entity,
        }
        self.relations.append(relation)
        print(f"✅ 创建关系: {from_entity} --[{relation_type}]--> {to_entity}")
        return relation

    def init_characteristic_curves_knowledge(self):
        """初始化特性曲线模块的知识图谱"""
        print("\n" + "=" * 60)
        print("🚀 开始初始化特性曲线模块知识图谱")
        print("=" * 60 + "\n")

        # 1. 创建架构层实体
        print("📦 步骤1: 创建架构层实体")
        print("-" * 60)
        self.create_entity(
            "architecture::module::characteristic_curves",
            """
描述: 泵特性曲线分析模块
职责:
  - Q-H曲线拟合（流量-扬程）
  - Q-P曲线拟合（流量-功率）
  - Q-η曲线拟合（流量-效率）
  - 泵组性能评估
  - 异常检测与预警
关键特性:
  - 支持10+种拟合方法
  - 自动方法选择（基于数据特征）
  - R²>0.95 的高精度拟合
  - 支持单泵和泵组分析
位置: app/services/characteristic_curves/
依赖项:
  - NumPy, SciPy
  - scikit-learn
  - PostgreSQL
设计决策: 采用策略模式实现方法可扩展性
性能: 1000数据点拟合 <100ms
            """,
        )

        # 2. 创建服务层实体
        print("\n🔧 步骤2: 创建服务层实体")
        print("-" * 60)
        self.create_entity(
            "service::component::CurveFittingPipeline",
            """
描述: 曲线拟合主流程管理器
职责:
  - 数据预处理和清洗
  - 拟合方法选择
  - 拟合执行和验证
  - 结果质量评估
位置: app/services/characteristic_curves/pipeline/curve_fitting_pipeline.py
关键方法:
  - process(device_id, time_window) - 主处理流程
  - validate_data(raw_data) - 数据验证
  - select_method(data_characteristics) - 方法选择
  - execute_fitting(method, data) - 执行拟合
性能: 单次拟合 <100ms
设计模式: 管道模式 + 策略模式
            """,
        )

        self.create_entity(
            "service::component::PumpGroupProcessor",
            """
描述: 泵组处理器
职责:
  - 泵组数据提取
  - 并联/串联工况分析
  - 泵组特性曲线合成
  - 系统曲线修正
位置: app/services/characteristic_curves/pump_group/pump_group_processor.py
关键方法:
  - process_group(group_id, time_window) - 泵组处理
  - synthesize_parallel_curves(curves) - 并联曲线合成
  - synthesize_serial_curves(curves) - 串联曲线合成
特性: 支持复杂泵组配置（最多8台泵）
            """,
        )

        self.create_entity(
            "service::component::MethodRegistry",
            """
描述: 拟合方法注册中心
职责:
  - 管理所有拟合方法
  - 方法注册和查找
  - 方法优先级管理
位置: app/services/characteristic_curves/methods/method_registry.py
支持的方法类别:
  - mathematical: 数学方法（多项式、样条、核方法等）
  - physical: 物理方法（泵特性方程等）
  - machine_learning: 机器学习方法（随机森林、梯度提升等）
  - hybrid: 混合方法（物理+多项式等）
            """,
        )

        # 3. 创建业务层实体
        print("\n💼 步骤3: 创建业务层实体")
        print("-" * 60)
        self.create_entity(
            "business::metric::pump_efficiency",
            """
描述: 泵运行效率指标
计算公式: η = (ρ * g * Q * H) / (1000 * P)
单位: 百分比
正常范围: 60% - 85%
关键影响因素:
  - 流量偏离额定值
  - 扬程变化
  - 设备老化
  - 管道阻力
应用场景:
  - 泵性能评估
  - 运行优化建议
  - 异常检测
            """,
        )

        self.create_entity(
            "business::process::curve_fitting_workflow",
            """
描述: 曲线拟合业务流程
步骤:
  1. 数据采集: 从时序数据库提取运行数据
  2. 数据清洗: 去除异常点、插值缺失值
  3. 特征提取: 计算数据特征（分布、趋势等）
  4. 方法选择: 基于数据特征自动选择拟合方法
  5. 拟合执行: 运行拟合算法
  6. 结果验证: R²检查、物理约束验证
  7. 结果存储: 保存到数据库
  8. 可视化: 生成曲线图表
质量要求:
  - 最小样本点: 20点
  - 拟合优度: R²>0.9
  - 物理合理性: 必须通过
            """,
        )

        # 4. 创建数据层实体
        print("\n🗄️ 步骤4: 创建数据层实体")
        print("-" * 60)
        self.create_entity(
            "data::table::pump_characteristic_curves",
            """
描述: 泵特性曲线结果存储表
主键: (device_id, curve_type, time_window_start)
索引:
  - btree(device_id, time_window_start)
  - brin(time_window_start)
分区策略: 按月分区
数据保留: 2年
关键字段:
  - device_id (INT) - 设备ID
  - curve_type (TEXT) - 曲线类型（qh/qp/qeta）
  - time_window_start (TIMESTAMP) - 时间窗口起始
  - curve_coefficients (JSONB) - 曲线系数
  - r_squared (FLOAT) - 拟合优度
  - method_used (TEXT) - 使用的拟合方法
  - quality_grade (TEXT) - 质量等级（A/B/C/D）
备份: 定期备份到 backups/pump_characteristic_curves/
            """,
        )

        self.create_entity(
            "data::table::device_running_data",
            """
描述: 设备运行数据表（时序数据）
主键: (device_id, time)
索引: brin(time)
分区策略: 按天分区
关键字段:
  - device_id (INT) - 设备ID
  - time (TIMESTAMP) - 采集时间
  - flow_rate (FLOAT) - 流量 (m³/h)
  - head (FLOAT) - 扬程 (m)
  - power (FLOAT) - 功率 (kW)
  - efficiency (FLOAT) - 效率 (%)
  - frequency (FLOAT) - 频率 (Hz)
  - inlet_pressure (FLOAT) - 进口压力 (MPa)
  - outlet_pressure (FLOAT) - 出口压力 (MPa)
数据来源: 现场传感器（秒级采集）
            """,
        )

        # 5. 创建文档层实体
        print("\n📚 步骤5: 创建文档层实体")
        print("-" * 60)
        self.create_entity(
            "doc::spec::curve_fitting_specification",
            """
描述: 曲线拟合技术规范
位置: docs/特性曲线开发/
关键要求:
  - 最小样本点: 20点
  - 拟合优度: R²>0.9
  - 异常点过滤: 3σ原则
  - 物理约束: 必须满足泵特性规律
方法选择策略:
  1. 数据量<50点: 使用多项式方法
  2. 数据量50-200点: 使用样条方法
  3. 数据量>200点: 优先使用机器学习方法
质量分级:
  - A级: R²>0.98
  - B级: R²>0.95
  - C级: R²>0.90
  - D级: R²<0.90（需人工审核）
            """,
        )

        # 6. 建立关系
        print("\n🔗 步骤6: 建立实体关系")
        print("-" * 60)

        # 架构包含关系
        self.create_relation(
            "architecture::module::characteristic_curves",
            "contains",
            "service::component::CurveFittingPipeline",
        )

        self.create_relation(
            "architecture::module::characteristic_curves",
            "contains",
            "service::component::PumpGroupProcessor",
        )

        self.create_relation(
            "architecture::module::characteristic_curves",
            "contains",
            "service::component::MethodRegistry",
        )

        # 依赖关系
        self.create_relation(
            "service::component::CurveFittingPipeline",
            "depends_on",
            "data::component::DatabaseGateway",
        )

        self.create_relation(
            "service::component::PumpGroupProcessor",
            "uses",
            "service::component::CurveFittingPipeline",
        )

        self.create_relation(
            "service::component::CurveFittingPipeline",
            "uses",
            "service::component::MethodRegistry",
        )

        # 数据流关系
        self.create_relation(
            "service::component::CurveFittingPipeline",
            "reads_from",
            "data::table::device_running_data",
        )

        self.create_relation(
            "service::component::CurveFittingPipeline",
            "writes_to",
            "data::table::pump_characteristic_curves",
        )

        # 业务关系
        self.create_relation(
            "service::component::CurveFittingPipeline",
            "implements",
            "business::process::curve_fitting_workflow",
        )

        self.create_relation(
            "service::component::CurveFittingPipeline",
            "calculates",
            "business::metric::pump_efficiency",
        )

        # 文档关系
        self.create_relation(
            "doc::spec::curve_fitting_specification",
            "documents",
            "architecture::module::characteristic_curves",
        )

        self.create_relation(
            "doc::spec::curve_fitting_specification",
            "specifies",
            "service::component::CurveFittingPipeline",
        )

        print("\n" + "=" * 60)
        print("✅ 知识图谱初始化完成！")
        print("=" * 60)
        print(f"\n📊 统计信息:")
        print(f"  - 实体总数: {len(self.entities)}")
        print(f"  - 关系总数: {len(self.relations)}")

    def demo_queries(self):
        """演示常见查询场景"""
        print("\n" + "=" * 60)
        print("🔍 演示常见查询场景")
        print("=" * 60 + "\n")

        print("1️⃣ 查询特性曲线模块包含的所有组件:")
        print("-" * 60)
        module_components = [
            r["to"]
            for r in self.relations
            if r["from"] == "architecture::module::characteristic_curves"
            and r["type"] == "contains"
        ]
        for comp in module_components:
            print(f"  ✓ {comp}")

        print("\n2️⃣ 查询 CurveFittingPipeline 的所有依赖:")
        print("-" * 60)
        dependencies = [
            r["to"]
            for r in self.relations
            if r["from"] == "service::component::CurveFittingPipeline"
            and r["type"] in ["depends_on", "uses"]
        ]
        for dep in dependencies:
            print(f"  ✓ {dep}")

        print("\n3️⃣ 查询数据流（哪些组件读写数据表）:")
        print("-" * 60)
        data_flows = [
            (r["from"], r["type"], r["to"])
            for r in self.relations
            if r["type"] in ["reads_from", "writes_to"]
        ]
        for source, flow_type, target in data_flows:
            print(f"  ✓ {source} --[{flow_type}]--> {target}")

        print("\n4️⃣ 查询文档覆盖情况:")
        print("-" * 60)
        doc_relations = [
            (r["from"], r["type"], r["to"])
            for r in self.relations
            if r["from"].startswith("doc::")
        ]
        for doc, rel_type, target in doc_relations:
            print(f"  ✓ {doc} --[{rel_type}]--> {target}")

    def export_to_markdown(self, output_file: str):
        """导出知识图谱到Markdown文件"""
        print(f"\n📝 导出知识图谱到: {output_file}")

        content = "# 特性曲线模块知识图谱\n\n"
        content += f"> 自动生成时间: 2025-12-16\n"
        content += f"> 实体总数: {len(self.entities)}\n"
        content += f"> 关系总数: {len(self.relations)}\n\n"

        content += "---\n\n"
        content += "## 📦 实体列表\n\n"

        # 按层级分组
        layers = {
            "architecture": "架构层",
            "service": "服务层",
            "business": "业务层",
            "data": "数据层",
            "doc": "文档层",
        }

        for layer_key, layer_name in layers.items():
            layer_entities = [e for e in self.entities if e["id"].startswith(layer_key)]
            if layer_entities:
                content += f"### {layer_name}\n\n"
                for entity in layer_entities:
                    content += f"#### {entity['id']}\n\n"
                    content += f"```\n{entity['observation'].strip()}\n```\n\n"

        content += "---\n\n"
        content += "## 🔗 关系图\n\n"
        content += "```mermaid\n"
        content += "graph TD\n"
        for rel in self.relations:
            from_node = rel["from"].replace("::", "_")
            to_node = rel["to"].replace("::", "_")
            content += f'  {from_node}["{rel["from"]}"] -->|{rel["type"]}| {to_node}["{rel["to"]}"]\n'
        content += "```\n\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"✅ 导出完成！")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🎯 Memory MCP 使用示例")
    print("=" * 60)

    # 创建示例实例
    example = MemoryMCPExample()

    # 初始化知识图谱
    example.init_characteristic_curves_knowledge()

    # 演示查询
    example.demo_queries()

    # 导出到Markdown
    output_file = "docs/特性曲线模块知识图谱示例.md"
    example.export_to_markdown(output_file)

    print("\n" + "=" * 60)
    print("🎉 示例演示完成！")
    print("=" * 60)
    print("\n💡 下一步:")
    print("  1. 查看导出的知识图谱: docs/特性曲线模块知识图谱示例.md")
    print("  2. 参考 docs/Memory-MCP使用规范.md 了解详细规范")
    print("  3. 在实际项目中使用 Memory MCP 工具")
    print("\n")


if __name__ == "__main__":
    main()
