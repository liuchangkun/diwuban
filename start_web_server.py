#!/usr/bin/env python3
"""
Web服务启动脚本

本脚本从配置文件读取Web服务配置并启动FastAPI应用程序。
解决了硬编码端口问题，支持配置外置化。

使用方式：
    python start_web_server.py
    
配置文件：
    configs/web.yaml - Web服务配置
    configs/system.yaml - 系统通用配置
"""

import sys
from pathlib import Path

def main():
    """主函数：读取配置并启动Web服务"""
    try:
        # 添加项目根目录到Python路径
        project_root = Path(__file__).resolve().parent
        sys.path.insert(0, str(project_root))
        
        # 导入配置加载器
        from app.core.config.loader import load_settings
        
        # 加载配置
        settings = load_settings(Path("configs"))
        
        # 获取Web服务配置
        host = settings.web.server.host
        port = settings.web.server.port
        reload = settings.web.server.reload
        
        print(f"🚀 启动Web服务...")
        print(f"📍 服务地址: http://{host}:{port}")
        print(f"📚 API文档: http://{host}:{port}{settings.web.api.docs_url}")
        print(f"🔄 热重载: {'启用' if reload else '禁用'}")
        
        # 启动uvicorn服务器
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            workers=settings.web.server.workers if not reload else 1,
            access_log=settings.web.app.log_requests,
        )
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装所需依赖：pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()