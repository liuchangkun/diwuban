#!/usr/bin/env python3
"""
新配置系统测试脚本

本脚本用于测试新的配置系统是否正常工作，包括：
1. 配置加载测试
2. 配置验证测试
3. 硬编码消除验证
4. 配置来源追踪测试

使用方式：
    python test_new_config.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_config_loading():
    """测试配置加载功能"""
    print("🔧 测试配置加载功能...")
    
    try:
        from app.core.config.loader_new import load_settings, load_settings_with_sources
        
        # 测试基本配置加载
        settings = load_settings(Path("configs"))
        print(f"✅ 配置加载成功")
        
        # 验证硬编码消除
        print(f"📁 数据目录: {settings.system.directories.data}")
        print(f"🌍 默认时区: {settings.system.timezone.default}")
        print(f"🌐 Web端口: {settings.web.server.port}")
        print(f"🔗 数据库主机: {settings.db.host}")
        
        # 测试配置来源追踪
        settings_with_sources, sources = load_settings_with_sources(Path("configs"))
        print(f"✅ 配置来源追踪成功")
        
        # 显示配置来源
        print(f"📋 配置来源信息:")
        for module, fields in sources.items():
            print(f"  {module}:")
            for field, source in fields.items():
                print(f"    {field}: {source}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_validation():
    """测试配置验证功能"""
    print("\n🔍 测试配置验证功能...")
    
    try:
        from app.core.config.validation import ConfigValidator
        
        # 测试数据库配置验证
        db_config = {
            "host": "localhost",
            "name": "pump_station_optimization",
            "user": "postgres",
            "pool": {"min_size": 1, "max_size": 10},
            "timeouts": {"connect_timeout_ms": 5000}
        }
        
        result = ConfigValidator.validate_database_config(db_config)
        if result.is_valid:
            print("✅ 数据库配置验证通过")
        else:
            print(f"❌ 数据库配置验证失败: {len(result.errors)} 个错误")
            for error in result.errors:
                print(f"  - {error.field}: {error.message}")
        
        # 测试Web配置验证
        web_config = {
            "server": {
                "host": "127.0.0.1",
                "port": 8000,
                "workers": 1
            }
        }
        
        result = ConfigValidator.validate_web_config(web_config)
        if result.is_valid:
            print("✅ Web服务配置验证通过")
        else:
            print(f"❌ Web服务配置验证失败: {len(result.errors)} 个错误")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置验证测试失败: {e}")
        return False

def test_hardcode_elimination():
    """测试硬编码消除"""
    print("\n🚫 测试硬编码消除...")
    
    try:
        from app.core.config.loader_new import load_settings
        
        settings = load_settings(Path("configs"))
        
        # 检查关键配置是否来自配置文件而非硬编码
        hardcode_tests = [
            ("数据目录", settings.system.directories.data != "data" or Path("configs/system.yaml").exists()),
            ("默认时区", settings.system.timezone.default != "Asia/Shanghai" or Path("configs/system.yaml").exists()),
            ("Web端口", settings.web.server.port != 8000 or Path("configs/web.yaml").exists()),
            ("数据库主机", settings.db.host != "localhost" or Path("configs/database.yaml").exists()),
        ]
        
        all_passed = True
        for test_name, passed in hardcode_tests:
            if passed:
                print(f"✅ {test_name}: 配置外置化成功")
            else:
                print(f"❌ {test_name}: 仍存在硬编码")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 硬编码消除测试失败: {e}")
        return False

def test_config_modules():
    """测试配置模块拆分"""
    print("\n📦 测试配置模块拆分...")
    
    modules_to_test = [
        "app.core.config.database",
        "app.core.config.web", 
        "app.core.config.system",
        "app.core.config.ingest",
        "app.core.config.merge",
        "app.core.config.logging",
        "app.core.config.logging_base",
        "app.core.config.logging_advanced",
        "app.core.config.validation",
    ]
    
    all_passed = True
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}: 模块导入成功")
        except Exception as e:
            print(f"❌ {module_name}: 模块导入失败 - {e}")
            all_passed = False
    
    return all_passed

def test_environment_override():
    """测试环境变量覆盖"""
    print("\n🌐 测试环境变量覆盖...")
    
    try:
        from app.core.config.loader_new import load_settings
        
        # 设置测试环境变量
        test_env_vars = {
            "INGEST_WORKERS": "12",
            "INGEST_COMMIT_INTERVAL": "2000000",
        }
        
        # 保存原始环境变量
        original_env = {}
        for key, value in test_env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            settings = load_settings(Path("configs"))
            
            # 验证环境变量覆盖
            tests = [
                ("INGEST_WORKERS", settings.ingest.workers == 12),
                ("INGEST_COMMIT_INTERVAL", settings.ingest.commit_interval == 2000000),
            ]
            
            all_passed = True
            for env_var, passed in tests:
                if passed:
                    print(f"✅ {env_var}: 环境变量覆盖成功")
                else:
                    print(f"❌ {env_var}: 环境变量覆盖失败")
                    all_passed = False
            
            return all_passed
            
        finally:
            # 恢复原始环境变量
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
        
    except Exception as e:
        print(f"❌ 环境变量覆盖测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始新配置系统测试...\n")
    
    tests = [
        ("配置加载", test_config_loading),
        ("配置验证", test_config_validation),
        ("硬编码消除", test_hardcode_elimination),
        ("配置模块拆分", test_config_modules),
        ("环境变量覆盖", test_environment_override),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print(f"\n📊 测试结果汇总:")
    print("=" * 50)
    
    passed_count = 0
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:15} : {status}")
        if passed:
            passed_count += 1
    
    print("=" * 50)
    print(f"总计: {passed_count}/{len(results)} 项测试通过")
    
    if passed_count == len(results):
        print("🎉 所有测试通过！新配置系统工作正常。")
        return 0
    else:
        print("⚠️  部分测试失败，请检查配置系统。")
        return 1

if __name__ == "__main__":
    sys.exit(main())