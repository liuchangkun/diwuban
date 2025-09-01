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

# 日志落盘
import logging
import time
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.adapters.db import cleanup_database, init_database
from app.api.middleware import APILoggingMiddleware, setup_api_logging
from app.api.v1.router import api_v1_router
from app.core.config.loader_new import load_settings
from app.utils.logging_ext import JsonFormatter

# 加载配置（包括Web服务配置）
_settings = load_settings(Path("configs"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    负责在应用启动时初始化资源，在应用关闭时清理资源。
    """
    # 获取结构化日志器
    logger = structlog.get_logger("app.startup")

    # 应用启动
    try:
        # 设置 API 日志
        setup_api_logging()
        logger.info("日志系统初始化完成")

        # 使用已加载的配置
        settings = _settings

        # 初始化数据库连接池
        init_database(settings)
        logger.info("数据库连接池初始化完成")

        logger.info(
            "应用初始化完成",
            host=settings.web.server.host,
            port=settings.web.server.port,
            debug=getattr(settings.web.app, "debug", False),
            cors_enabled=getattr(settings.web.app, "cors_enabled", False),
        )
        print(
            f"[OK] 应用初始化完成，Web服务配置: {settings.web.server.host}:{settings.web.server.port}"
        )

    except Exception as e:
        logger.error("应用初始化失败", error=str(e), exc_info=True)
        print(f"[ERROR] 应用初始化失败: {e}")
        raise

    yield  # 应用运行期间

    # 应用关闭
    try:
        logger.info("开始应用清理")
        cleanup_database()
        logger.info("应用清理完成")
        print("[OK] 应用清理完成")
    except Exception as e:
        logger.error("应用清理失败", error=str(e), exc_info=True)
        print(f"[WARNING] 应用清理失败: {e}")


# 创建 FastAPI 应用实例，使用配置中的参数
app = FastAPI(
    title=_settings.web.api.title,
    description=_settings.web.api.description,
    version=_settings.web.api.version,
    docs_url=_settings.web.api.docs_url,
    redoc_url=_settings.web.api.redoc_url,
    lifespan=lifespan,
)

# 添加 CORS 中间件（如果启用）
if getattr(_settings.web.app, "cors_enabled", False):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=getattr(_settings.web.app, "cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加 API 日志中间件
app.add_middleware(
    APILoggingMiddleware,
    log_request_body=True,
    log_response_body=False,  # 生产环境建议关闭
    max_body_size=8192,
)

# 开发模式下，禁止对 /static 的缓存，避免前端调试缓存干扰
if getattr(_settings.web.app, "debug", False):

    @app.middleware("http")
    async def no_cache_static(request: Request, call_next):
        response = await call_next(request)
        try:
            if str(request.url.path).startswith("/static/"):
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
        except Exception:
            pass
        return response


# 配置 RotatingFileHandler 将结构化 JSON 日志落盘到 logs/api.log（10MB x 5）
logs_dir = Path("logs")
logs_dir.mkdir(parents=True, exist_ok=True)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(
    filename=str(logs_dir / "api.log"),
    maxBytes=10 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(JsonFormatter())
# 避免重复添加处理器
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    root_logger.addHandler(file_handler)


@app.get("/health")
def health(request: Request):
    """
    健康检查接口

    返回服务的基本状态信息和数据库连接池统计。
    """
    from app.adapters.db import get_pool_stats, is_initialized

    # 获取结构化日志器
    logger = structlog.get_logger("api.health")

    start_time = time.time()

    try:
        # 检查数据库状态
        db_initialized = is_initialized()
        pool_stats = get_pool_stats()

        response_data = {
            "status": "ok",
            "timestamp": time.time(),
            "uptime": time.time() - start_time,
            "database": {
                "pool_initialized": db_initialized,
                "pool_stats": pool_stats,
            },
            "request_info": {
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        }

        # 记录健康检查日志
        logger.info(
            "健康检查完成",
            status="ok",
            db_initialized=db_initialized,
            pool_stats=pool_stats,
            client_ip=request.client.host if request.client else "unknown",
        )

        return response_data

    except Exception as e:
        logger.error("健康检查失败", error=str(e), exc_info=True)
        return {
            "status": "error",
            "timestamp": time.time(),
            "error": str(e),
            "database": {
                "pool_initialized": False,
                "pool_stats": None,
            },
        }


# 注册 API 路由
app.include_router(api_v1_router, prefix="/api/v1")

# 添加静态文件服务
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/")
    async def serve_dashboard():
        """
        主页 - 返回可视化仪表板
        """
        index_file = static_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "可视化界面文件不存在"}

    @app.get("/favicon.ico")
    async def favicon():
        """提供站点图标，避免 404。"""
        ico = static_path / "favicon.ico"
        if ico.exists():
            return FileResponse(str(ico))
        # 若无图标，返回 204
        from fastapi import Response

        return Response(status_code=204)
