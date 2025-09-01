#!/usr/bin/env python3
"""
硬编码检查脚本

本脚本用于扫描代码库中的硬编码问题，确保所有配置都已外置化。

检查项目：
1. 时区硬编码 (Asia/Shanghai, UTC等)
2. 目录路径硬编码 (data/, logs/, temp/等)
3. 端口号硬编码 (8000, 3306等)
4. 数据库连接信息硬编码
5. 文件路径硬编码
6. IP地址硬编码
7. 默认值硬编码
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Pattern
from dataclasses import dataclass

# 添加项目根目录到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@dataclass
class HardcodeIssue:
    """硬编码问题"""
    file_path: str
    line_number: int
    line_content: str
    issue_type: str
    matched_text: str
    severity: str  # "high", "medium", "low"


class HardcodeChecker:
    """硬编码检查器"""
    
    def __init__(self):
        self.issues: List[HardcodeIssue] = []
        self.excluded_files = {
            "__pycache__",
            ".git",
            ".pytest_cache",
            "test_config_migration.py",
            "hardcode_checker.py",
            ".venv",
            "node_modules",
        }
        self.excluded_extensions = {".pyc", ".pyo", ".log", ".json", ".md", ".txt", ".bat"}
        
        # 硬编码检测规则
        self.hardcode_patterns = {
            "timezone": [
                (r'"Asia/Shanghai"', "时区硬编码", "medium"),
                (r"'Asia/Shanghai'", "时区硬编码", "medium"),
                (r'"UTC"(?!\s*#.*配置)', "时区硬编码", "medium"),
                (r"'UTC'(?!\s*#.*配置)", "时区硬编码", "medium"),
                (r'"Asia/Beijing"', "时区硬编码", "medium"),
                (r'"America/New_York"', "时区硬编码", "medium"),
            ],
            "directory_paths": [
                (r'"data"(?!/)', "目录路径硬编码", "high"),
                (r"'data'(?!/)", "目录路径硬编码", "high"), 
                (r'"logs"(?!/)', "目录路径硬编码", "high"),
                (r"'logs'(?!/)", "目录路径硬编码", "high"),
                (r'"temp"(?!/)', "目录路径硬编码", "medium"),
                (r'"backup"(?!/)', "目录路径硬编码", "medium"),
                (r'"configs"(?!/)', "目录路径硬编码", "medium"),
            ],
            "port_numbers": [
                (r':\s*8000\b(?!.*#.*配置)', "Web端口硬编码", "high"),
                (r'port\s*=\s*8000\b', "端口硬编码", "high"),
                (r':\s*3306\b', "数据库端口硬编码", "high"),
                (r':\s*5432\b', "PostgreSQL端口硬编码", "high"),
                (r':\s*6379\b', "Redis端口硬编码", "medium"),
            ],
            "database_info": [
                (r'"localhost"(?!\s*#.*配置)', "数据库主机硬编码", "high"),
                (r"'localhost'(?!\s*#.*配置)", "数据库主机硬编码", "high"),
                (r'"127\.0\.0\.1"', "IP地址硬编码", "high"),
                (r'"pump_station_optimization"(?!\s*#.*配置)', "数据库名硬编码", "high"),
                (r'"postgres"(?!\s*#.*配置)', "数据库用户硬编码", "medium"),
            ],
            "file_paths": [
                (r'"config/data_mapping\.v2\.json"', "映射文件路径硬编码", "high"),
                (r'"config/dim_metric_config\.json"', "配置文件路径硬编码", "high"),
                (r'Path\("data"', "目录路径硬编码", "high"),
                (r'Path\("logs"', "目录路径硬编码", "high"),
                (r'Path\("temp"', "目录路径硬编码", "medium"),
            ],
            "encoding_and_format": [
                (r'"utf-8"(?!\s*#.*配置)', "编码硬编码", "low"),
                (r'"json"(?!\s*#.*配置|.*format)', "格式硬编码", "low"),
                (r'"csv"(?!\s*#.*配置)', "格式硬编码", "low"),
            ],
        }
        
        # 允许的例外情况（通过注释或上下文判断）
        self.allowed_contexts = [
            r"#.*配置",
            r"#.*default",
            r"#.*示例",
            r"#.*example",
            r"test_",
            r"Test",
            r"\.yaml",
            r"\.json",
            r"config",
            r"example",
        ]

    def should_exclude_file(self, file_path: Path) -> bool:
        """判断是否应该排除该文件"""
        # 排除特定目录
        for excluded in self.excluded_files:
            if excluded in str(file_path):
                return True
        
        # 排除特定扩展名
        if file_path.suffix in self.excluded_extensions:
            return True
            
        return False

    def is_allowed_context(self, line: str) -> bool:
        """判断是否是允许的上下文"""
        line_lower = line.lower()
        for pattern in self.allowed_contexts:
            if re.search(pattern, line_lower):
                return True
        return False

    def check_file(self, file_path: Path) -> List[HardcodeIssue]:
        """检查单个文件的硬编码问题"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for line_no, line in enumerate(lines, 1):
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith('#'):
                    continue
                
                # 跳过允许的上下文
                if self.is_allowed_context(line):
                    continue
                
                # 检查各类硬编码模式
                for category, patterns in self.hardcode_patterns.items():
                    for pattern, issue_type, severity in patterns:
                        matches = re.finditer(pattern, line)
                        for match in matches:
                            issue = HardcodeIssue(
                                file_path=str(file_path.relative_to(project_root)),
                                line_number=line_no,
                                line_content=line.strip(),
                                issue_type=issue_type,
                                matched_text=match.group(),
                                severity=severity
                            )
                            issues.append(issue)
                            
        except (UnicodeDecodeError, PermissionError):
            # 跳过无法读取的文件
            pass
        
        return issues

    def scan_directory(self, directory: Path) -> None:
        """扫描目录中的所有Python文件"""
        for file_path in directory.rglob("*.py"):
            if self.should_exclude_file(file_path):
                continue
                
            file_issues = self.check_file(file_path)
            self.issues.extend(file_issues)

    def generate_report(self) -> Dict:
        """生成检查报告"""
        # 按严重程度分组
        issues_by_severity = {"high": [], "medium": [], "low": []}
        for issue in self.issues:
            issues_by_severity[issue.severity].append(issue)
        
        # 按文件分组
        issues_by_file = {}
        for issue in self.issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue)
        
        return {
            "total_issues": len(self.issues),
            "by_severity": {k: len(v) for k, v in issues_by_severity.items()},
            "by_file": {k: len(v) for k, v in issues_by_file.items()},
            "issues": [
                {
                    "file": issue.file_path,
                    "line": issue.line_number,
                    "type": issue.issue_type,
                    "matched": issue.matched_text,
                    "severity": issue.severity,
                    "content": issue.line_content[:100] + "..." if len(issue.line_content) > 100 else issue.line_content
                }
                for issue in self.issues
            ]
        }

    def print_report(self) -> None:
        """打印检查报告"""
        print("🔍 硬编码检查报告")
        print("=" * 60)
        
        if not self.issues:
            print("✅ 未发现硬编码问题！")
            return
        
        # 按严重程度分组统计
        high_issues = [i for i in self.issues if i.severity == "high"]
        medium_issues = [i for i in self.issues if i.severity == "medium"]  
        low_issues = [i for i in self.issues if i.severity == "low"]
        
        print(f"📊 发现 {len(self.issues)} 个潜在硬编码问题:")
        print(f"  🔴 高风险: {len(high_issues)} 个")
        print(f"  🟡 中风险: {len(medium_issues)} 个") 
        print(f"  🔵 低风险: {len(low_issues)} 个")
        print()
        
        # 显示高风险问题
        if high_issues:
            print("🔴 高风险问题 (需要立即修复):")
            for issue in high_issues[:10]:  # 只显示前10个
                print(f"  📁 {issue.file_path}:{issue.line_number}")
                print(f"     类型: {issue.issue_type}")
                print(f"     匹配: {issue.matched_text}")
                print(f"     代码: {issue.line_content}")
                print()
        
        # 显示中风险问题
        if medium_issues:
            print("🟡 中风险问题 (建议修复):")
            for issue in medium_issues[:5]:  # 只显示前5个
                print(f"  📁 {issue.file_path}:{issue.line_number}")
                print(f"     类型: {issue.issue_type}")
                print(f"     匹配: {issue.matched_text}")
                print()
        
        # 文件统计
        file_stats = {}
        for issue in self.issues:
            if issue.file_path not in file_stats:
                file_stats[issue.file_path] = 0
            file_stats[issue.file_path] += 1
        
        if file_stats:
            print("📈 问题文件统计 (Top 5):")
            sorted_files = sorted(file_stats.items(), key=lambda x: x[1], reverse=True)
            for file_path, count in sorted_files[:5]:
                print(f"  📁 {file_path}: {count} 个问题")

    def check_hardcodes(self) -> Dict:
        """执行硬编码检查"""
        print("🚀 开始硬编码检查...")
        
        # 扫描app目录
        app_dir = project_root / "app"
        if app_dir.exists():
            self.scan_directory(app_dir)
        
        # 扫描根目录下的Python文件
        for file_path in project_root.glob("*.py"):
            if not self.should_exclude_file(file_path):
                file_issues = self.check_file(file_path)
                self.issues.extend(file_issues)
        
        return self.generate_report()


def main():
    """主函数"""
    checker = HardcodeChecker()
    report = checker.check_hardcodes()
    
    # 打印报告
    checker.print_report()
    
    # 保存详细报告
    import json
    report_path = project_root / "hardcode_check_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 详细报告已保存至: {report_path}")
    
    # 返回适当的退出码
    high_issues = [i for i in checker.issues if i.severity == "high"]
    sys.exit(1 if high_issues else 0)


if __name__ == "__main__":
    main()