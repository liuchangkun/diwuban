#!/usr/bin/env python3
"""
API检查脚本

本脚本用于检查API是否能正常工作，包括：
1. 健康检查端点
2. 数据查询端点
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def check_imports():
    """检查必要的模块是否能正常导入"""
    try:
        from app.main import app
        print("✓ FastAPI应用导入成功")
        
        from app.core.config.loader_new import load_settings
        settings = load_settings(Path("configs"))
        print("✓ 配置加载成功")
        print(f"  Web服务器地址: {settings.web.server.host}:{settings.web.server.port}")
        
        return True
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        return False

def check_routes():
    """检查路由是否正确设置"""
    try:
        from app.main import app
        routes = [route.path for route in app.routes]
        print(f"✓ 应用路由数量: {len(routes)}")
        
        # 检查关键路由是否存在
        required_routes = ["/health", "/api/v1/data/measurements", "/docs"]
        for route in required_routes:
            if route in routes:
                print(f"✓ 路由存在: {route}")
            else:
                print(f"✗ 路由缺失: {route}")
                
        return True
    except Exception as e:
        print(f"✗ 路由检查失败: {e}")
        return False

def main():
    """主函数"""
    print("开始检查API...")
    print("=" * 50)
    
    # 检查导入
    if not check_imports():
        print("导入检查失败，退出")
        return 1
    
    print()
    
    # 检查路由
    if not check_routes():
        print("路由检查失败，退出")
        return 1
    
    print()
    print("=" * 50)
    print("API检查完成")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())