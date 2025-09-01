"""
Web服务配置模块（app.core.config.web）

本模块包含Web服务相关的配置类定义，包括：
- 服务器配置
- API配置
- 应用配置
- 性能配置
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WebServerSettings:
    """
    Web服务器配置

    用于配置FastAPI应用程序的运行参数。

    属性：
        host: 服务器绑定地址
        port: 服务器端口
        reload: 开发模式下是否启用热重载
        workers: 生产环境下的工作进程数
    """

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    workers: int = 1


@dataclass(frozen=True)
class WebApiSettings:
    """
    Web API配置

    用于配置FastAPI应用程序的API相关设置。

    属性：
        title: API标题
        description: API描述
        version: API版本
        docs_url: Swagger文档路径
        redoc_url: ReDoc文档路径
    """

    title: str = "Pump Station Optimization API"
    description: str = "泵站运行数据优化系统 API"
    version: str = "1.0.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    # 新增：测量接口的最小默认时间窗口（分钟），用于控制默认查询范围，避免大查询
    minimal_window_minutes: int = 60  # 中文注释：默认 60 分钟


@dataclass(frozen=True)
class WebAppSettings:
    """
    Web应用配置

    用于配置应用程序的运行模式和行为。

    属性：
        debug: 调试模式
        log_requests: 是否记录HTTP请求日志
        cors_enabled: 是否启用CORS
        cors_origins: 允许的跨域来源
    """

    debug: bool = False
    log_requests: bool = True
    cors_enabled: bool = False
    cors_origins: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WebPerformanceSettings:
    """
    Web性能配置

    用于配置应用程序的性能相关参数。

    属性：
        request_timeout: 请求超时时间（秒）
        max_request_size: 最大请求大小（字节）
        keepalive_timeout: Keep-Alive超时时间（秒）
    """

    request_timeout: int = 30
    max_request_size: int = 16777216  # 16MB
    keepalive_timeout: int = 65


@dataclass(frozen=True)
class WebSettings:
    """
    Web服务完整配置

    集成所有Web相关配置，提供统一的配置访问接口。

    属性：
        server: 服务器配置
        api: API配置
        app: 应用配置
        performance: 性能配置
    """

    server: WebServerSettings = WebServerSettings()
    api: WebApiSettings = WebApiSettings()
    app: WebAppSettings = WebAppSettings()
    performance: WebPerformanceSettings = WebPerformanceSettings()
