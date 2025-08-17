#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动 PLAYBOOKS 检查工具
在开始任何重要工作前，自动检查相关的历史记录，避免重复犯错
"""

import re
import sys
from pathlib import Path
from typing import List, Dict
import yaml


class AutoPlaybooksCheck:
    def __init__(self, playbooks_dir: str = "docs/PLAYBOOKS"):
        self.playbooks_dir = Path(playbooks_dir)
        self.records = []
        self.load_all_records()

    def load_all_records(self):
        """加载所有 PLAYBOOKS 记录"""
        for file_path in self.playbooks_dir.glob("*.md"):
            if file_path.name.startswith("_"):
                continue
            self.load_records_from_file(file_path)

    def load_records_from_file(self, file_path: Path):
        """从单个文件加载记录"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            records = re.findall(
                r"---\n(.*?)\n---\n(.*?)(?=\n---|\Z)", content, re.DOTALL
            )

            for yaml_content, markdown_content in records:
                try:
                    metadata = yaml.safe_load(yaml_content)
                    if metadata and "id" in metadata:
                        record = {
                            "file": file_path.name,
                            "metadata": metadata,
                            "content": markdown_content.strip(),
                            "type": self.get_record_type(file_path.name),
                        }
                        self.records.append(record)
                except yaml.YAMLError:
                    continue
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    def get_record_type(self, filename: str) -> str:
        """根据文件名确定记录类型"""
        type_map = {
            "ERROR_FIX_LOG.md": "error",
            "IMPROVEMENTS.md": "improvement",
            "DECISIONS.md": "decision",
            "LESSONS_LEARNED.md": "lesson",
            "PERFORMANCE_BENCHMARKS.md": "performance",
            "CONFIGURATION_CHANGES.md": "configuration",
        }
        return type_map.get(filename, "unknown")

    def check_for_context(
        self, keywords: List[str], modules: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """根据关键词和模块检查相关历史记录"""
        relevant_records = {
            "errors": [],
            "lessons": [],
            "decisions": [],
            "improvements": [],
            "configurations": [],
            "performance": [],
        }

        for record in self.records:
            metadata = record["metadata"]
            content = record["content"].lower()

            # 检查模块匹配
            module_match = True
            if modules:
                module_match = metadata.get("module") in modules

            # 检查关键词匹配
            keyword_match = any(
                keyword.lower() in content or keyword.lower() in str(metadata).lower()
                for keyword in keywords
            )

            if module_match and keyword_match:
                record_type = record["type"]
                if record_type == "error":
                    relevant_records["errors"].append(record)
                elif record_type == "lesson":
                    relevant_records["lessons"].append(record)
                elif record_type == "decision":
                    relevant_records["decisions"].append(record)
                elif record_type == "improvement":
                    relevant_records["improvements"].append(record)
                elif record_type == "configuration":
                    relevant_records["configurations"].append(record)
                elif record_type == "performance":
                    relevant_records["performance"].append(record)

        return relevant_records

    def generate_context_report(
        self, keywords: List[str], modules: List[str] = None
    ) -> str:
        """生成上下文报告"""
        relevant_records = self.check_for_context(keywords, modules)

        # 统计相关记录数量
        total_relevant = sum(len(records) for records in relevant_records.values())

        if total_relevant == 0:
            return f"✅ 未发现与 {', '.join(keywords)} 相关的历史问题或经验。"

        report = f"🔍 发现 {total_relevant} 条相关历史记录，请参考：\n\n"

        # 优先显示错误和经验教训
        priority_types = [
            ("errors", "❌ 历史错误", "避免重复犯错"),
            ("lessons", "📚 经验教训", "参考最佳实践"),
            ("decisions", "🎯 技术决策", "了解选择背景"),
            ("improvements", "⚡ 改进记录", "参考优化经验"),
            ("configurations", "⚙️ 配置变更", "了解变更历史"),
            ("performance", "📊 性能基准", "参考性能数据"),
        ]

        for key, title, description in priority_types:
            records = relevant_records[key]
            if records:
                report += f"{title} ({len(records)} 条) - {description}:\n"
                for record in records[:3]:  # 最多显示3条
                    metadata = record["metadata"]
                    # 提取标题
                    content_lines = record["content"].split("\n")
                    title_line = next(
                        (line for line in content_lines if "标题：" in line), ""
                    )
                    if title_line and "：" in title_line:
                        title = title_line.split("：", 1)[1].strip()
                    else:
                        title = f"[{metadata.get('module', 'unknown')}] {metadata.get('id', 'N/A')}"

                    report += f"  • {metadata.get('id', 'N/A')}: {title}\n"

                if len(records) > 3:
                    report += f"  ... 还有 {len(records) - 3} 条记录\n"
                report += "\n"

        report += "💡 建议：开始工作前仔细阅读相关记录，避免重复问题。\n"
        return report

    def auto_suggest_record_type(self, keywords: List[str]) -> str:
        """根据关键词自动建议记录类型"""
        error_keywords = ["错误", "失败", "问题", "error", "fail", "bug", "修复"]
        decision_keywords = ["选择", "决策", "方案", "vs", "对比", "选型"]
        performance_keywords = ["性能", "优化", "基准", "performance", "速度", "吞吐"]
        config_keywords = ["配置", "设置", "参数", "config", "变更"]

        keyword_text = " ".join(keywords).lower()

        if any(kw in keyword_text for kw in error_keywords):
            return "建议记录类型: ERROR_FIX_LOG (错误修复)"
        elif any(kw in keyword_text for kw in decision_keywords):
            return "建议记录类型: DECISIONS (技术决策)"
        elif any(kw in keyword_text for kw in performance_keywords):
            return "建议记录类型: PERFORMANCE_BENCHMARKS (性能基准)"
        elif any(kw in keyword_text for kw in config_keywords):
            return "建议记录类型: CONFIGURATION_CHANGES (配置变更)"
        else:
            return "建议记录类型: IMPROVEMENTS (改进优化)"


def main():
    if len(sys.argv) < 2:
        print(
            "用法: python scripts/auto_playbooks_check.py <关键词1> [关键词2] [--module 模块名]"
        )
        print(
            "示例: python scripts/auto_playbooks_check.py database postgresql --module infra"
        )
        return

    keywords = []
    modules = []

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--module" and i + 1 < len(sys.argv):
            modules.append(sys.argv[i + 1])
            i += 2
        else:
            keywords.append(sys.argv[i])
            i += 1

    checker = AutoPlaybooksCheck()

    # 生成上下文报告
    report = checker.generate_context_report(keywords, modules if modules else None)
    print(report)

    # 建议记录类型
    suggestion = checker.auto_suggest_record_type(keywords)
    print(f"\n{suggestion}")


if __name__ == "__main__":
    main()
