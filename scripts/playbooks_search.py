#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PLAYBOOKS 搜索工具
用法：
  python scripts/playbooks_search.py --tag "database" --module "infra"
  python scripts/playbooks_search.py --keyword "postgresql" --date "2025-01"
  python scripts/playbooks_search.py --type "error" --severity "Sev2"
"""

import argparse
import re
from pathlib import Path
from typing import List, Dict, Any
import yaml


class PlaybooksSearch:
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

    def search(self, **filters) -> List[Dict[Any, Any]]:
        """搜索记录"""
        results = []

        for record in self.records:
            if self.matches_filters(record, filters):
                results.append(record)

        return results

    def matches_filters(self, record: Dict[Any, Any], filters: Dict[str, Any]) -> bool:
        """检查记录是否匹配过滤条件"""
        metadata = record["metadata"]
        content = record["content"]

        # 类型过滤
        if "type" in filters and record["type"] != filters["type"]:
            return False

        # 模块过滤
        if "module" in filters and metadata.get("module") != filters["module"]:
            return False

        # 标签过滤
        if "tag" in filters:
            tags = metadata.get("tags", [])
            if filters["tag"] not in tags:
                return False

        # 日期过滤
        if "date" in filters:
            record_date = metadata.get("date", "")
            if not record_date.startswith(filters["date"]):
                return False

        # 严重程度过滤（仅适用于错误记录）
        if "severity" in filters and "severity" in metadata:
            if metadata["severity"] != filters["severity"]:
                return False

        # 关键词搜索
        if "keyword" in filters:
            keyword = filters["keyword"].lower()
            search_text = f"{content} {str(metadata)}".lower()
            if keyword not in search_text:
                return False

        return True

    def format_results(self, results: List[Dict[Any, Any]]) -> str:
        """格式化搜索结果"""
        if not results:
            return "未找到匹配的记录。"

        output = f"找到 {len(results)} 条记录：\n\n"

        for i, record in enumerate(results, 1):
            metadata = record["metadata"]
            output += f"{i}. [{record['type'].upper()}] {metadata.get('id', 'N/A')}\n"
            output += f"   日期: {metadata.get('date', 'N/A')}\n"
            output += f"   模块: {metadata.get('module', 'N/A')}\n"
            output += f"   标签: {', '.join(metadata.get('tags', []))}\n"

            # 提取标题
            content_lines = record["content"].split("\n")
            title_line = next(
                (
                    line
                    for line in content_lines
                    if line.startswith("- 标题：")
                    or line.startswith("- 决策标题：")
                    or line.startswith("- 经验标题：")
                    or line.startswith("- 测试标题：")
                    or line.startswith("- 变更标题：")
                ),
                "",
            )
            if title_line:
                title = (
                    title_line.split("：", 1)[1] if "：" in title_line else title_line
                )
                output += f"   内容: {title}\n"

            output += f"   文件: {record['file']}\n\n"

        return output


def main():
    parser = argparse.ArgumentParser(description="搜索 PLAYBOOKS 记录")
    parser.add_argument(
        "--type",
        choices=[
            "error",
            "improvement",
            "decision",
            "lesson",
            "performance",
            "configuration",
        ],
        help="记录类型",
    )
    parser.add_argument("--module", help="模块名称")
    parser.add_argument("--tag", help="标签")
    parser.add_argument("--date", help="日期（YYYY-MM 或 YYYY-MM-DD）")
    parser.add_argument(
        "--severity",
        choices=["Sev1", "Sev2", "Sev3", "Sev4"],
        help="严重程度（仅错误记录）",
    )
    parser.add_argument("--keyword", help="关键词搜索")

    args = parser.parse_args()

    # 构建过滤条件
    filters = {}
    for key, value in vars(args).items():
        if value is not None:
            filters[key] = value

    # 执行搜索
    searcher = PlaybooksSearch()
    results = searcher.search(**filters)

    # 输出结果
    print(searcher.format_results(results))


if __name__ == "__main__":
    main()
