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

# 基础依赖
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.adapters.db import cleanup_database, init_database
from app.api.v1.router import api_v1_router
from app.core.config.loader_new import load_settings
from app.core.logging.setup import (
    clear_context,
    init_logging,
    log_activity,
    set_context,
)

# 加载配置（包括Web服务配置）
_settings = load_settings(Path("configs"))
# 初始化日志（使用 system.yaml 时区作为兜底）
try:
    init_logging("configs", _settings.system.timezone.default)
except Exception:
    # 兜底避免因日志初始化失败阻断应用
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    负责在应用启动时初始化资源，在应用关闭时清理资源。
    """

    try:
        # 使用已加载的配置
        settings = _settings

        # 初始化数据库连接池
        init_database(settings)

        print(
            f"[OK] 应用初始化完成，Web服务配置: {settings.web.server.host}:{settings.web.server.port}"
        )

    except Exception as e:
        print(f"[ERROR] 应用初始化失败: {e}")
        raise

    yield  # 应用运行期间

    # 应用关闭
    try:
        cleanup_database()
        print("[OK] 应用清理完成")
    except Exception as e:
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


# HTTP 请求日志与上下文中间件
@app.middleware("http")
async def logging_context_middleware(request: Request, call_next):
    # 生成/提取 request_id & trace_id
    rid = request.headers.get("x-request-id") or f"req-{int(time.time()*1000)}"
    tid = request.headers.get("x-trace-id") or rid
    set_context(request_id=rid, trace_id=tid)
    path = str(request.url.path)
    method = request.method
    client_ip = request.client.host if request.client else "unknown"

    # 进入日志
    with log_activity(
        name=f"http {method} {path}",
        params={
            "客户端IP": client_ip,
            "请求头": {
                k: v
                for k, v in request.headers.items()
                if k.lower() not in {"authorization"}
            },
        },
    ):
        try:
            response = await call_next(request)
            status = getattr(response, "status_code", 200)
            # 退出日志（在 log_activity 中自动记录耗时）
            return response
        except Exception:
            # 错误日志由 log_activity 捕获
            raise
        finally:
            clear_context()


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


@app.get("/health")
def health(request: Request):
    """
    健康检查接口

    返回服务的基本状态信息和数据库连接池统计。
    """
    from app.adapters.db import get_pool_stats, is_initialized

    try:
        from app.adapters.db.pool_telemetry import snapshot as _pool_telemetry_snapshot
    except Exception:

        def _pool_telemetry_snapshot():  # fallback
            return {"error": "telemetry_unavailable"}





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
                "pool_events": _pool_telemetry_snapshot(),
            },
            "request_info": {
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        }

        return response_data

    except Exception as e:
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
