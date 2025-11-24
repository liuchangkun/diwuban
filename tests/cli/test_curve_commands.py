"""
CLI命令测试 - 特性曲线相关命令

测试 validate-curve 和 compare-versions 命令的功能

版本: v1.0
创建日期: 2025-12-09
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


class TestValidateCurveCommand:
    """测试 validate-curve 命令"""

    def test_validate_existing_result(self):
        """场景1: 验证存在的拟合结果"""
        # 使用数据库中的真实ID
        result_id = 85
        
        cmd = [
            sys.executable, "-m", "app.cli.main",
            "validate-curve",
            f"--result-id={result_id}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 0, f"命令执行失败: {result.stderr}"
        
        # 解析输出
        output = json.loads(result.stdout)
        
        # 验证输出结构
        assert "result_id" in output
        assert "device_id" in output
        assert "curve_type" in output
        assert "version" in output
        assert "validation_passed" in output
        assert "checks" in output
        assert "overall_status" in output
        
        # 验证检查项
        assert "r_squared_check" in output["checks"]
        assert "rmse_check" in output["checks"]
        assert "data_points_check" in output["checks"]
        assert "status_check" in output["checks"]
        
        print(f"✅ 验证结果: {output['overall_status']}")
        print(f"   R²: {output['checks']['r_squared_check']['actual']}")
        print(f"   RMSE: {output['checks']['rmse_check']['actual']}")

    def test_validate_nonexistent_result(self):
        """场景2: 验证不存在的结果"""
        result_id = 999999
        
        cmd = [
            sys.executable, "-m", "app.cli.main",
            "validate-curve",
            f"--result-id={result_id}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 1, "应该返回错误码"
        assert "未找到结果" in result.stderr, "应该包含错误信息"
        
        print(f"✅ 正确处理不存在的结果")


class TestCompareVersionsCommand:
    """测试 compare-versions 命令"""

    def test_compare_two_versions(self):
        """场景1: 比较两个版本"""
        device_id = 1
        curve_type = "qh"
        v1 = "list_v1_e41b7bbd"
        v2 = "list_v2_e41b7bbd"
        
        cmd = [
            sys.executable, "-m", "app.cli.main",
            "compare-versions",
            f"--device-id={device_id}",
            f"--curve-type={curve_type}",
            f"--v1={v1}",
            f"--v2={v2}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 0, f"命令执行失败: {result.stderr}"
        
        # 解析输出
        output = json.loads(result.stdout)
        
        # 验证输出结构
        assert "device_id" in output
        assert "curve_type" in output
        assert "version_1" in output
        assert "version_2" in output
        assert "comparison" in output
        assert "recommendation" in output
        
        # 验证比较结果
        assert "r_squared_diff" in output["comparison"]
        assert "rmse_diff" in output["comparison"]
        assert "coefficient_changes" in output["comparison"]
        assert "fit_quality_change" in output["comparison"]
        
        print(f"✅ 比较完成")
        print(f"   版本1 R²: {output['version_1']['r_squared']}")
        print(f"   版本2 R²: {output['version_2']['r_squared']}")
        print(f"   R² 差值: {output['comparison']['r_squared_diff']}")
        print(f"   推荐版本: {output['recommendation']}")
        print(f"   推荐理由: {output['recommendation_reason']}")

    def test_compare_with_output_file(self, tmp_path):
        """场景2: 比较结果输出到文件"""
        device_id = 1
        curve_type = "qh"
        v1 = "list_v1_e41b7bbd"
        v2 = "list_v2_e41b7bbd"
        output_file = tmp_path / "comparison.json"
        
        cmd = [
            sys.executable, "-m", "app.cli.main",
            "compare-versions",
            f"--device-id={device_id}",
            f"--curve-type={curve_type}",
            f"--v1={v1}",
            f"--v2={v2}",
            f"--output={output_file}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 0, f"命令执行失败: {result.stderr}"
        assert output_file.exists(), "输出文件应该存在"
        
        # 验证文件内容
        with open(output_file) as f:
            output = json.load(f)
        
        assert "comparison" in output
        print(f"✅ 结果已保存到文件: {output_file}")

    def test_compare_nonexistent_version(self):
        """场景3: 比较不存在的版本"""
        device_id = 1
        curve_type = "qh"
        v1 = "nonexistent_v1"
        v2 = "nonexistent_v2"
        
        cmd = [
            sys.executable, "-m", "app.cli.main",
            "compare-versions",
            f"--device-id={device_id}",
            f"--curve-type={curve_type}",
            f"--v1={v1}",
            f"--v2={v2}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 1, "应该返回错误码"
        assert "未找到版本" in result.stderr, "应该包含错误信息"
        
        print(f"✅ 正确处理不存在的版本")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])

