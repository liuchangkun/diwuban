"""
FastAPI 主应用程序

本模块定义了 FastAPI 应用程序的主入口，包括：
- 应用初始化和配置
- 数据库连接池管理
- API 路由注册
- 应用生命周期管理

使用方式：
    从配置文件读取端口和其他Web服务配置
    uvicorn app.main:app --host {web.server.host} --port {web.server.port}
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.config.loader_new import load_settings
from app.adapters.db import init_database, cleanup_database

# 加载配置（包括Web服务配置）
_settings = load_settings(Path("configs"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    负责在应用启动时初始化资源，在应用关闭时清理资源。
    """
    # 应用启动
    try:
        # 使用已加载的配置
        settings = _settings
        
        # 初始化数据库连接池
        init_database(settings)
        
        print(f"✅ 应用初始化完成，Web服务配置: {settings.web.server.host}:{settings.web.server.port}")
        
    except Exception as e:
        print(f"❌ 应用初始化失败: {e}")
        raise
    
    yield  # 应用运行期间
    
    # 应用关闭
    try:
        cleanup_database()
        print("✅ 应用清理完成")
    except Exception as e:
        print(f"⚠️ 应用清理失败: {e}")


# 创建 FastAPI 应用实例，使用配置中的参数
app = FastAPI(
    title=_settings.web.api.title,
    description=_settings.web.api.description,
    version=_settings.web.api.version,
    docs_url=_settings.web.api.docs_url,
    redoc_url=_settings.web.api.redoc_url,
    lifespan=lifespan
)


@app.get("/health")
def health():
    """
    健康检查接口
    
    返回服务的基本状态信息和数据库连接池统计。
    """
    from app.adapters.db import get_pool_stats, is_initialized
    
    return {
        "status": "ok",
        "database": {
            "pool_initialized": is_initialized(),
            "pool_stats": get_pool_stats()
        }
    }


# 注册 API 路由
app.include_router(api_v1_router, prefix="/api/v1")
