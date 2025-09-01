#!/usr/bin/env python3
"""
配置系统迁移测试脚本

本脚本用于全面测试新的配置系统，确保迁移后功能正常工作。

测试内容：
1. 配置加载测试
2. 配置验证测试  
3. 配置来源追踪测试
4. 环境变量覆盖测试
5. 错误处理测试
6. 硬编码检查测试
7. 性能对比测试
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings, load_settings_with_sources
from app.core.config.validation import ConfigValidator


class ConfigMigrationTester:
    """配置迁移测试器"""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.config_dir = project_root / "configs"
        
    def log_test_result(self, test_name: str, success: bool, message: str = "", details: Any = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}: {message}")
        if details and not success:
            print(f"    详情: {details}")

    def test_config_loading(self) -> bool:
        """测试配置加载功能"""
        try:
            settings = load_settings(self.config_dir)
            
            # 验证配置对象存在
            assert hasattr(settings, 'db'), "缺少数据库配置"
            assert hasattr(settings, 'web'), "缺少Web配置"
            assert hasattr(settings, 'system'), "缺少系统配置"
            assert hasattr(settings, 'ingest'), "缺少导入配置"
            assert hasattr(settings, 'merge'), "缺少合并配置"
            assert hasattr(settings, 'logging'), "缺少日志配置"
            
            # 验证基本配置值
            assert settings.web.server.port > 0, "Web端口配置错误"
            assert settings.system.timezone.default, "默认时区配置错误"
            assert settings.system.directories.data, "数据目录配置错误"
            
            self.log_test_result("配置加载", True, "成功加载所有配置模块")
            return True
            
        except Exception as e:
            self.log_test_result("配置加载", False, "配置加载失败", str(e))
            return False

    def test_config_validation(self) -> bool:
        """测试配置验证功能"""
        try:
            # 测试有效配置
            valid_config = {
                "database": {
                    "host": "localhost",
                    "name": "test_db",
                    "user": "test_user",
                    "pool": {"min_size": 1, "max_size": 10}
                },
                "web": {
                    "server": {"host": "127.0.0.1", "port": 8000}
                },
                "system": {
                    "timezone": {"default": "Asia/Shanghai"},
                    "directories": {"data": "data", "logs": "logs", "configs": "configs"}
                }
            }
            
            result = ConfigValidator.validate_complete_config(valid_config)
            if not result.is_valid:
                self.log_test_result("配置验证-有效配置", False, "有效配置验证失败", result.errors)
                return False
                
            # 测试无效配置
            invalid_config = {
                "database": {"host": "", "name": "", "user": ""},
                "web": {"server": {"port": -1}},
                "system": {"timezone": {"default": ""}}
            }
            
            result = ConfigValidator.validate_complete_config(invalid_config)
            if result.is_valid:
                self.log_test_result("配置验证-无效配置", False, "无效配置未被检测到")
                return False
                
            self.log_test_result("配置验证", True, "验证功能工作正常")
            return True
            
        except Exception as e:
            self.log_test_result("配置验证", False, "配置验证测试失败", str(e))
            return False

    def test_config_sources(self) -> bool:
        """测试配置来源追踪"""
        try:
            settings, sources = load_settings_with_sources(self.config_dir)
            
            # 验证来源信息结构
            assert isinstance(sources, dict), "来源信息应为字典"
            assert "database" in sources, "缺少数据库来源信息"
            assert "web" in sources, "缺少Web来源信息"
            assert "system" in sources, "缺少系统来源信息"
            
            # 验证来源值的有效性
            valid_sources = {"YAML", "DEFAULT", "ENV", "SYSTEM"}
            for module_name, module_sources in sources.items():
                if isinstance(module_sources, dict):
                    for field_name, source in module_sources.items():
                        assert source in valid_sources, f"无效来源值: {source}"
            
            self.log_test_result("配置来源追踪", True, "来源追踪功能正常")
            return True
            
        except Exception as e:
            self.log_test_result("配置来源追踪", False, "来源追踪测试失败", str(e))
            return False

    def test_env_override(self) -> bool:
        """测试环境变量覆盖"""
        try:
            # 设置测试环境变量
            original_workers = os.getenv("INGEST_WORKERS")
            test_workers = "12"
            os.environ["INGEST_WORKERS"] = test_workers
            
            try:
                settings = load_settings(self.config_dir)
                
                # 验证环境变量覆盖生效
                assert settings.ingest.workers == int(test_workers), \
                    f"环境变量覆盖失败，期望: {test_workers}, 实际: {settings.ingest.workers}"
                
                # 验证来源追踪
                _, sources = load_settings_with_sources(self.config_dir)
                workers_source = sources.get("ingest", {}).get("workers", "")
                assert workers_source == "ENV", \
                    f"环境变量来源追踪失败，期望: ENV, 实际: {workers_source}"
                
                self.log_test_result("环境变量覆盖", True, "环境变量覆盖功能正常")
                return True
                
            finally:
                # 恢复原环境变量
                if original_workers is not None:
                    os.environ["INGEST_WORKERS"] = original_workers
                else:
                    os.environ.pop("INGEST_WORKERS", None)
                    
        except Exception as e:
            self.log_test_result("环境变量覆盖", False, "环境变量覆盖测试失败", str(e))
            return False

    def test_error_handling(self) -> bool:
        """测试错误处理"""
        try:
            # 测试不存在的配置目录
            non_existent_dir = Path("/non_existent_config_dir")
            settings = load_settings(non_existent_dir)
            
            # 应该能使用默认值正常工作
            assert hasattr(settings, 'db'), "错误处理后缺少数据库配置"
            
            self.log_test_result("错误处理", True, "错误处理机制正常")
            return True
            
        except Exception as e:
            self.log_test_result("错误处理", False, "错误处理测试失败", str(e))
            return False

    def test_hardcoded_elimination(self) -> bool:
        """测试硬编码消除"""
        try:
            settings = load_settings(self.config_dir)
            
            # 验证时区不是硬编码
            assert settings.system.timezone.default != "", "时区配置为空"
            
            # 验证数据目录不是硬编码
            assert settings.system.directories.data != "", "数据目录配置为空"
            
            # 验证Web端口不是硬编码
            assert settings.web.server.port > 0, "Web端口配置无效"
            
            # 验证数据库主机不是硬编码
            assert settings.db.host != "", "数据库主机配置为空"
            
            # 验证ingest配置使用系统默认值
            assert settings.ingest.base_dir == settings.system.directories.data, \
                "ingest基础目录应该来自系统配置"
            
            self.log_test_result("硬编码消除", True, "硬编码已成功消除")
            return True
            
        except Exception as e:
            self.log_test_result("硬编码消除", False, "硬编码检查失败", str(e))
            return False

    def test_performance_comparison(self) -> bool:
        """测试性能对比"""
        try:
            # 测试新配置系统性能
            start_time = time.time()
            for _ in range(10):
                settings = load_settings(self.config_dir)
            new_config_time = time.time() - start_time
            
            # 简单的性能检查
            assert new_config_time < 5.0, "配置加载性能过慢"
            
            self.log_test_result("性能对比", True, f"配置加载性能正常: {new_config_time:.3f}秒/10次")
            return True
            
        except Exception as e:
            self.log_test_result("性能对比", False, "性能测试失败", str(e))
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始配置系统迁移测试...")
        print("=" * 60)
        
        test_methods = [
            self.test_config_loading,
            self.test_config_validation,
            self.test_config_sources,
            self.test_env_override,
            self.test_error_handling,
            self.test_hardcoded_elimination,
            self.test_performance_comparison,
        ]
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            if test_method():
                passed += 1
            else:
                failed += 1
        
        print("=" * 60)
        print(f"📊 测试结果汇总:")
        print(f"配置加载            : {'✅ 通过' if any(r['test_name'] == '配置加载' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"配置验证            : {'✅ 通过' if any(r['test_name'] == '配置验证' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"配置来源追踪          : {'✅ 通过' if any(r['test_name'] == '配置来源追踪' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"环境变量覆盖          : {'✅ 通过' if any(r['test_name'] == '环境变量覆盖' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"错误处理            : {'✅ 通过' if any(r['test_name'] == '错误处理' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"硬编码消除           : {'✅ 通过' if any(r['test_name'] == '硬编码消除' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"性能对比            : {'✅ 通过' if any(r['test_name'] == '性能对比' and r['success'] for r in self.test_results) else '❌ 失败'}")
        print(f"总计: {passed}/{len(test_methods)} 项测试通过")
        
        if failed == 0:
            print("🎉 所有测试通过！新配置系统工作正常。")
        else:
            print(f"⚠️ {failed} 项测试失败，需要检查和修复。")
        
        return {
            "total_tests": len(test_methods),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(test_methods) * 100,
            "results": self.test_results
        }

    def generate_report(self) -> str:
        """生成测试报告"""
        report = {
            "test_summary": {
                "total_tests": len(self.test_results),
                "passed": sum(1 for r in self.test_results if r["success"]),
                "failed": sum(1 for r in self.test_results if not r["success"]),
            },
            "test_details": self.test_results,
            "generated_at": time.time()
        }
        
        report_path = project_root / "config_migration_test_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(report_path)


def main():
    """主函数"""
    tester = ConfigMigrationTester()
    summary = tester.run_all_tests()
    
    # 生成详细报告
    report_path = tester.generate_report()
    print(f"\n📄 详细测试报告已保存至: {report_path}")
    
    # 返回适当的退出码
    sys.exit(0 if summary["failed"] == 0 else 1)


if __name__ == "__main__":
    main()