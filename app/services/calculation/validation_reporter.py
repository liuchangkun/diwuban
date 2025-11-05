"""
验证报告生成器

功能：
1. 收集验证结果
2. 生成JSON格式报告
3. 保存到文件
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """单个验证结果"""
    metric_key: str
    is_valid: bool
    total_count: int
    valid_count: int
    invalid_count: int
    valid_rate: float
    errors: List[str]
    warnings: List[str]
    duration: float
    timestamp: str
    context: Dict[str, Any]


class ValidationReporter:
    """验证报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        self.results: List[ValidationResult] = []
        self.start_time = datetime.now()
    
    def add_result(
        self,
        metric_key: str,
        is_valid: bool,
        total_count: int,
        valid_count: int,
        errors: List[str],
        warnings: List[str],
        duration: float,
        context: Dict[str, Any] = None
    ):
        """添加验证结果"""
        invalid_count = total_count - valid_count
        valid_rate = valid_count / total_count if total_count > 0 else 0.0
        
        result = ValidationResult(
            metric_key=metric_key,
            is_valid=is_valid,
            total_count=total_count,
            valid_count=valid_count,
            invalid_count=invalid_count,
            valid_rate=valid_rate,
            errors=errors,
            warnings=warnings,
            duration=duration,
            timestamp=datetime.now().isoformat(),
            context=context or {}
        )
        
        self.results.append(result)
        
        logger.debug(
            "[报告-记录] [验证结果]",
            extra={
                "extra_data": {
                    "指标": metric_key,
                    "有效率": f"{valid_rate:.1%}",
                    "耗时": f"{duration:.3f}s"
                }
            }
        )
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成验证摘要"""
        if not self.results:
            return {
                "total_validations": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0
            }
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.is_valid)
        failed = total - passed
        pass_rate = passed / total if total > 0 else 0.0
        
        total_data_points = sum(r.total_count for r in self.results)
        total_valid_points = sum(r.valid_count for r in self.results)
        overall_valid_rate = total_valid_points / total_data_points if total_data_points > 0 else 0.0
        
        total_duration = sum(r.duration for r in self.results)
        
        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": pass_rate,
            "total_data_points": total_data_points,
            "total_valid_points": total_valid_points,
            "overall_valid_rate": overall_valid_rate,
            "total_duration": total_duration,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
    
    def save_to_file(self, filepath: Path):
        """保存到JSON文件"""
        report = {
            "summary": self.generate_summary(),
            "results": [asdict(r) for r in self.results]
        }
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.info(
            "[报告-保存] [验证报告]",
            extra={
                "extra_data": {
                    "文件路径": str(filepath),
                    "验证数": len(self.results)
                }
            }
        )
    
    def clear(self):
        """清空结果"""
        self.results.clear()
        self.start_time = datetime.now()

