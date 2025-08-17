#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAYBOOKS 统计分析工具
用法：
  python scripts/playbooks_stats.py --month "2025-01"
  python scripts/playbooks_stats.py --summary
  python scripts/playbooks_stats.py --trends
"""

import argparse
from collections import defaultdict, Counter
from pathlib import Path
import yaml
import re


class PlaybooksStats:
    def __init__(self, playbooks_dir: str = "docs/PLAYBOOKS"):
        self.playbooks_dir = Path(playbooks_dir)
        self.records = []
        self.load_all_records()

    def load_all_records(self):
        """加载所有 PLAYBOOKS 记录"""
        for file_path in self.playbooks_dir.glob("*.md"):
            if file_path.name.startswith("_"):  # 跳过模板文件
                continue
            self.load_records_from_file(file_path)

    def load_records_from_file(self, file_path: Path):
        """从单个文件加载记录"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析 YAML frontmatter 记录
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

    def generate_summary(self) -> str:
        """生成总体统计摘要"""
        total_records = len(self.records)
        if total_records == 0:
            return "暂无记录。"

        # 按类型统计
        type_counts = Counter(record["type"] for record in self.records)

        # 按模块统计
        module_counts = Counter(
            record["metadata"].get("module", "unknown") for record in self.records
        )

        # 按日期统计（按月）
        date_counts = defaultdict(int)
        for record in self.records:
            date_str = record["metadata"].get("date", "")
            if date_str:
                month = date_str[:7]  # YYYY-MM
                date_counts[month] += 1

        # 标签统计
        tag_counts = Counter()
        for record in self.records:
            tags = record["metadata"].get("tags", [])
            tag_counts.update(tags)

        output = f"PLAYBOOKS 统计摘要\n{'='*50}\n\n"
        output += f"总记录数: {total_records}\n\n"

        output += "按类型分布:\n"
        for record_type, count in type_counts.most_common():
            percentage = (count / total_records) * 100
            output += f"  {record_type:12} {count:3d} ({percentage:5.1f}%)\n"

        output += "\n按模块分布:\n"
        for module, count in module_counts.most_common():
            percentage = (count / total_records) * 100
            output += f"  {module:12} {count:3d} ({percentage:5.1f}%)\n"

        output += "\n按月份分布:\n"
        for month in sorted(date_counts.keys()):
            count = date_counts[month]
            percentage = (count / total_records) * 100
            output += f"  {month:7} {count:3d} ({percentage:5.1f}%)\n"

        output += "\n热门标签 (Top 10):\n"
        for tag, count in tag_counts.most_common(10):
            percentage = (count / total_records) * 100
            output += f"  {tag:15} {count:3d} ({percentage:5.1f}%)\n"

        return output

    def generate_monthly_report(self, month: str) -> str:
        """生成月度报告"""
        monthly_records = [
            r for r in self.records if r["metadata"].get("date", "").startswith(month)
        ]

        if not monthly_records:
            return f"{month} 月无记录。"

        output = f"{month} 月度报告\n{'='*50}\n\n"
        output += f"总记录数: {len(monthly_records)}\n\n"

        # 按类型分组
        by_type = defaultdict(list)
        for record in monthly_records:
            by_type[record["type"]].append(record)

        for record_type, records in by_type.items():
            output += f"{record_type.upper()} ({len(records)} 条):\n"
            for record in records:
                metadata = record["metadata"]
                output += f"  - {metadata.get('id', 'N/A')}: "

                # 提取标题
                content_lines = record["content"].split("\n")
                title_line = next(
                    (line for line in content_lines if "标题：" in line), ""
                )
                if title_line and "：" in title_line:
                    title = title_line.split("：", 1)[1].strip()
                    output += f"{title}\n"
                else:
                    output += f"[{metadata.get('module', 'unknown')}]\n"
            output += "\n"

        return output

    def generate_trends(self) -> str:
        """生成趋势分析"""
        if len(self.records) < 2:
            return "记录数量不足，无法生成趋势分析。"

        # 按日期排序
        sorted_records = sorted(
            self.records, key=lambda r: r["metadata"].get("date", "")
        )

        # 按月统计各类型记录数量
        monthly_stats = defaultdict(lambda: defaultdict(int))
        for record in sorted_records:
            date_str = record["metadata"].get("date", "")
            if date_str:
                month = date_str[:7]  # YYYY-MM
                record_type = record["type"]
                monthly_stats[month][record_type] += 1

        output = "趋势分析\n{'='*50}\n\n"

        # 总体趋势
        output += "月度记录数量趋势:\n"
        for month in sorted(monthly_stats.keys()):
            total = sum(monthly_stats[month].values())
            output += f"  {month}: {total:2d} 条记录\n"

        output += "\n各类型记录趋势:\n"
        all_types = set()
        for month_data in monthly_stats.values():
            all_types.update(month_data.keys())

        for record_type in sorted(all_types):
            output += f"\n{record_type.upper()}:\n"
            for month in sorted(monthly_stats.keys()):
                count = monthly_stats[month][record_type]
                output += f"  {month}: {count:2d}\n"

        return output


def main():
    parser = argparse.ArgumentParser(description="PLAYBOOKS 统计分析")
    parser.add_argument("--summary", action="store_true", help="生成总体统计摘要")
    parser.add_argument("--month", help="生成月度报告 (YYYY-MM)")
    parser.add_argument("--trends", action="store_true", help="生成趋势分析")

    args = parser.parse_args()

    stats = PlaybooksStats()

    if args.summary:
        print(stats.generate_summary())
    elif args.month:
        print(stats.generate_monthly_report(args.month))
    elif args.trends:
        print(stats.generate_trends())
    else:
        # 默认显示摘要
        print(stats.generate_summary())


if __name__ == "__main__":
    main()
