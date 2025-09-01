"""
API 请求日志中间件

记录所有 HTTP 请求和响应的详细信息，用于调试和监控。
包含：
- 请求信息：方法、URL、头、参数、body
- 响应信息：状态码、头、body（可选）
- 性能指标：处理时间、内存使用
- 错误信息：异常详情、堆栈跟踪
"""

import time
import traceback
import uuid
from typing import Dict, Optional

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging_ext import EventLogger

# 获取结构化日志器
logger = structlog.get_logger("api")
event_logger = EventLogger(logger)


class APILoggingMiddleware(BaseHTTPMiddleware):
    """
    API 请求日志中间件

    记录每个 HTTP 请求的完整生命周期信息
    """

    def __init__(
        self,
        app: ASGIApp,
        log_request_body: bool = True,
        log_response_body: bool = False,
        max_body_size: int = 8192,
        sensitive_headers: Optional[list] = None,
    ):
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_size = max_body_size
        self.sensitive_headers = sensitive_headers or [
            "authorization",
            "cookie",
            "x-api-key",
            "x-auth-token",
        ]

    async def dispatch(self, request: Request, call_next):
        """处理请求并记录日志"""

        # 生成请求 ID
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # 记录请求开始
        await self._log_request_start(request, request_id, start_time)

        try:
            # 处理请求
            response = await call_next(request)

            # 记录成功响应
            end_time = time.time()
            await self._log_request_success(
                request, response, request_id, start_time, end_time
            )

            return response

        except Exception as exc:
            # 记录错误响应
            end_time = time.time()
            await self._log_request_error(
                request, exc, request_id, start_time, end_time
            )
            raise

    async def _log_request_start(
        self, request: Request, request_id: str, start_time: float
    ):
        """记录请求开始"""

        # 解析查询参数
        query_params = dict(request.query_params)

        # 解析路径参数
        path_params = dict(request.path_params)

        # 过滤敏感头信息
        headers = self._filter_sensitive_headers(dict(request.headers))

        # 读取请求体
        request_body = None
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if len(body_bytes) <= self.max_body_size:
                    request_body = body_bytes.decode("utf-8")
                else:
                    request_body = f"<body too large: {len(body_bytes)} bytes>"
            except Exception as e:
                request_body = f"<error reading body: {str(e)}>"

        # 记录请求事件
        event_logger.info(
            "api.request.start",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=query_params,
            path_params=path_params,
            headers=headers,
            request_body=request_body,
            client_ip=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            content_type=request.headers.get("content-type"),
            content_length=request.headers.get("content-length"),
            timestamp=start_time,
        )

    async def _log_request_success(
        self,
        request: Request,
        response: Response,
        request_id: str,
        start_time: float,
        end_time: float,
    ):
        """记录成功响应"""

        duration_ms = (end_time - start_time) * 1000

        # 过滤响应头
        response_headers = self._filter_sensitive_headers(dict(response.headers))

        # 记录响应体（可选）
        response_body = None
        if self.log_response_body:
            # 注意：这里需要特殊处理，因为响应体可能已经被消费
            # 在生产环境中，建议只在调试模式下启用
            response_body = "<response body logging disabled>"

        # 记录成功事件
        event_logger.info(
            "api.request.success",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            response_headers=response_headers,
            response_body=response_body,
            content_type=response.headers.get("content-type"),
            content_length=response.headers.get("content-length"),
        )

    async def _log_request_error(
        self,
        request: Request,
        exception: Exception,
        request_id: str,
        start_time: float,
        end_time: float,
    ):
        """记录错误响应"""

        duration_ms = (end_time - start_time) * 1000

        # 获取错误详情
        error_type = type(exception).__name__
        error_message = str(exception)
        error_traceback = traceback.format_exc()

        # 记录错误事件
        event_logger.error(
            "api.request.error",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=round(duration_ms, 2),
            error_type=error_type,
            error_message=error_message,
            error_traceback=error_traceback,
        )

    def _filter_sensitive_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """过滤敏感头信息"""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "<redacted>"
            else:
                filtered[key] = value
        return filtered

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端 IP 地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # 使用客户端地址
        client = getattr(request, "client", None)
        if client:
            return client.host

        return "unknown"


class DatabaseLoggingMixin:
    """数据库操作日志混入类"""

    @staticmethod
    def log_sql_execution(
        sql: str,
        params: Optional[tuple] = None,
        duration_ms: Optional[float] = None,
        affected_rows: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """记录 SQL 执行"""

        # 截断长 SQL
        truncated_sql = sql[:2000] + "..." if len(sql) > 2000 else sql

        event_data = {
            "sql": truncated_sql,
            "params": str(params) if params else None,
            "duration_ms": round(duration_ms, 2) if duration_ms else None,
            "affected_rows": affected_rows,
        }

        if error:
            event_logger.error("api.sql.error", error=error, **event_data)
        else:
            # 检查是否为慢查询
            if duration_ms and duration_ms > 1000:  # 1秒阈值
                event_logger.info("api.sql.slow", **event_data)
            else:
                event_logger.info("api.sql.executed", **event_data)


def setup_api_logging():
    """设置 API 日志"""

    # 配置结构化日志
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
