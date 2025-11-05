"""
配置验证模块（app.core.config.validation）

本模块提供配置字段验证和错误处理功能，确保配置的正确性和完整性。

核心功能：
- 配置字段类型验证
- 配置值范围验证
- 配置依赖关系验证
- 配置错误报告
- 配置安全检查
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationError:
    """
    配置验证错误

    属性：
        field: 错误字段路径
        value: 错误值
        message: 错误消息
        severity: 错误严重程度 ("error" | "warning" | "info")
    """

    field: str
    value: Any
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    """
    验证结果

    属性：
        is_valid: 是否验证通过
        errors: 错误列表
        warnings: 警告列表
    """

    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]

    def add_error(self, field: str, value: Any, message: str) -> None:
        """添加错误"""
        self.errors.append(ValidationError(field, value, message, "error"))
        self.is_valid = False

    def add_warning(self, field: str, value: Any, message: str) -> None:
        """添加警告"""
        self.warnings.append(ValidationError(field, value, message, "warning"))

    def has_issues(self) -> bool:
        """是否存在问题（错误或警告）"""
        return len(self.errors) > 0 or len(self.warnings) > 0


class ConfigValidator:
    """
    配置验证器

    提供各种配置验证方法，确保配置的正确性。
    """

    @staticmethod
    def validate_database_config(db_config: Dict[str, Any]) -> ValidationResult:
        """
        验证数据库配置

        参数：
            db_config: 数据库配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 验证主机地址
        host = db_config.get("host", "")
        if not host or not isinstance(host, str):
            result.add_error("db.host", host, "数据库主机地址不能为空且必须是字符串")
        elif host.strip() == "":
            result.add_error("db.host", host, "数据库主机地址不能为空白字符")

        # 验证数据库名称
        name = db_config.get("dbname", "")
        if not name or not isinstance(name, str):
            result.add_error("db.dbname", name, "数据库名称不能为空且必须是字符串")
        elif not name.replace("_", "").replace("-", "").isalnum():
            result.add_warning(
                "db.dbname", name, "数据库名称建议只包含字母、数字、下划线和连字符"
            )

        # 验证用户名
        user = db_config.get("user", "")
        if not user or not isinstance(user, str):
            result.add_error("db.user", user, "数据库用户名不能为空且必须是字符串")

        # 验证连接池配置
        pool_config = db_config.get("pool", {})
        if isinstance(pool_config, dict):
            min_size = pool_config.get("min_size", 1)
            max_size = pool_config.get("max_size", 10)

            if not isinstance(min_size, int) or min_size < 0:
                result.add_error(
                    "db.pool.min_size", min_size, "连接池最小大小必须是非负整数"
                )

            if not isinstance(max_size, int) or max_size < 1:
                result.add_error(
                    "db.pool.max_size", max_size, "连接池最大大小必须是正整数"
                )

            if (
                isinstance(min_size, int)
                and isinstance(max_size, int)
                and min_size > max_size
            ):
                result.add_error(
                    "db.pool",
                    f"min_size={min_size}, max_size={max_size}",
                    "连接池最小大小不能大于最大大小",
                )

        # 验证超时配置
        timeouts = db_config.get("timeouts", {})
        if isinstance(timeouts, dict):
            timeout_fields = [
                "connect_timeout_ms",
                "statement_timeout_ms",
                "query_timeout_ms",
                "connection_acquire_timeout_ms",
                "connection_validation_timeout_ms",
                "pool_shutdown_timeout_ms",
            ]
            for field in timeout_fields:
                value = timeouts.get(field, 0)
                if not isinstance(value, int) or value < 0:
                    result.add_error(
                        f"db.timeouts.{field}", value, f"{field}必须是非负整数（毫秒）"
                    )

            # 使用 DbTimeoutSettings 的验证方法进行深度验证
            try:
                from app.core.config.database import DbTimeoutSettings

                timeout_settings = DbTimeoutSettings(
                    connect_timeout_ms=int(timeouts.get("connect_timeout_ms", 5000)),
                    statement_timeout_ms=int(
                        timeouts.get("statement_timeout_ms", 30000)
                    ),
                    query_timeout_ms=int(timeouts.get("query_timeout_ms", 60000)),
                    connection_acquire_timeout_ms=int(
                        timeouts.get("connection_acquire_timeout_ms", 10000)
                    ),
                    connection_validation_timeout_ms=int(
                        timeouts.get("connection_validation_timeout_ms", 1000)
                    ),
                    pool_shutdown_timeout_ms=int(
                        timeouts.get("pool_shutdown_timeout_ms", 30000)
                    ),
                )
                validation_errors = timeout_settings.validate()
                for error in validation_errors:
                    result.add_error("db.timeouts", timeouts, error)
            except Exception as e:
                result.add_error("db.timeouts", timeouts, f"超时配置验证失败: {e}")

        return result

    @staticmethod
    def validate_web_config(web_config: Dict[str, Any]) -> ValidationResult:
        """
        验证Web服务配置

        参数：
            web_config: Web配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 验证服务器配置
        server_config = web_config.get("server", {})
        if isinstance(server_config, dict):
            # 验证主机地址
            host = server_config.get("host", "")
            if not isinstance(host, str) or not host.strip():
                result.add_error(
                    "web.server.host", host, "Web服务器主机地址必须是非空字符串"
                )

            # 验证端口
            port = server_config.get("port", 8000)
            if not isinstance(port, int) or port < 1 or port > 65535:
                result.add_error(
                    "web.server.port", port, "Web服务器端口必须是1-65535之间的整数"
                )
            elif port < 1024:
                result.add_warning(
                    "web.server.port", port, "使用小于1024的端口可能需要管理员权限"
                )

            # 验证工作进程数
            workers = server_config.get("workers", 1)
            if not isinstance(workers, int) or workers < 1:
                result.add_error(
                    "web.server.workers", workers, "工作进程数必须是正整数"
                )

        return result

    @staticmethod
    def validate_system_config(system_config: Dict[str, Any]) -> ValidationResult:
        """
        验证系统配置

        参数：
            system_config: 系统配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 验证时区配置
        timezone_config = system_config.get("timezone", {})
        if isinstance(timezone_config, dict):
            valid_timezones = [
                "UTC",
                "Asia/Shanghai",
                "Asia/Beijing",
                "America/New_York",
                "Europe/London",
            ]

            default_tz = timezone_config.get("default", "")
            if not isinstance(default_tz, str) or default_tz.strip() == "":
                result.add_error(
                    "system.timezone.default", default_tz, "默认时区不能为空"
                )
            elif default_tz not in valid_timezones:
                result.add_warning(
                    "system.timezone.default",
                    default_tz,
                    f"时区 '{default_tz}' 不在推荐列表中: {valid_timezones}",
                )

        # 验证目录配置
        directories_config = system_config.get("directories", {})
        if isinstance(directories_config, dict):
            required_dirs = ["data", "logs", "configs"]
            for dir_name in required_dirs:
                dir_path = directories_config.get(dir_name, "")
                if not isinstance(dir_path, str) or dir_path.strip() == "":
                    result.add_error(
                        f"system.directories.{dir_name}",
                        dir_path,
                        f"{dir_name}目录路径不能为空",
                    )

        return result

    @staticmethod
    def validate_ingest_config(ingest_config: Dict[str, Any]) -> ValidationResult:
        """
        验证数据导入配置

        参数：
            ingest_config: 数据导入配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 验证工作线程数
        workers = ingest_config.get("workers", 6)
        if not isinstance(workers, int) or workers < 1 or workers > 100:
            result.add_error(
                "ingest.workers", workers, "工作线程数必须是1-100之间的整数"
            )
        elif workers > 20:
            result.add_warning(
                "ingest.workers", workers, "工作线程数较大，可能影响性能"
            )

        # 验证提交间隔
        commit_interval = ingest_config.get("commit_interval", 1000000)
        if not isinstance(commit_interval, int) or commit_interval < 1000:
            result.add_error(
                "ingest.commit_interval",
                commit_interval,
                "提交间隔必须是大于等于1000的整数",
            )

        # 验证CSV配置
        csv_config = ingest_config.get("csv", {})
        if isinstance(csv_config, dict):
            encoding = csv_config.get("encoding", "utf-8")
            valid_encodings = ["utf-8", "gbk", "gb2312", "ascii", "latin1"]
            if not isinstance(encoding, str) or encoding.lower() not in [
                e.lower() for e in valid_encodings
            ]:
                result.add_error(
                    "ingest.csv.encoding",
                    encoding,
                    f"编码格式必须是: {valid_encodings}",
                )

        # 验证批处理配置
        batch_config = ingest_config.get("batch", {})
        if isinstance(batch_config, dict):
            batch_size = batch_config.get("size", 50000)
            if (
                not isinstance(batch_size, int)
                or batch_size < 100
                or batch_size > 1000000
            ):
                result.add_error(
                    "ingest.batch.size",
                    batch_size,
                    "批次大小必须是100-1000000之间的整数",
                )

        return result

    @staticmethod
    def validate_merge_config(merge_config: Dict[str, Any]) -> ValidationResult:
        """
        验证数据合并配置

        参数：
            merge_config: 数据合并配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 验证时间窗口配置
        window_config = merge_config.get("window", {})
        if isinstance(window_config, dict):
            window_size = window_config.get("size", "7d")
            if isinstance(window_size, str):
                valid_units = ["d", "h", "m", "s"]
                if not any(window_size.endswith(unit) for unit in valid_units):
                    result.add_error(
                        "merge.window.size",
                        window_size,
                        f"时间窗口单位必须是: {valid_units}",
                    )
                else:
                    try:
                        value = int(window_size[:-1])
                        if value <= 0:
                            result.add_error(
                                "merge.window.size",
                                window_size,
                                "时间窗口值必须是正整数",
                            )
                    except ValueError:
                        result.add_error(
                            "merge.window.size",
                            window_size,
                            "时间窗口格式错误，应为数字+单位格式",
                        )

        # 验证分段合并配置
        segmented_config = merge_config.get("segmented", {})
        if isinstance(segmented_config, dict):
            granularity = segmented_config.get("granularity", "1h")
            valid_granularities = ["15m", "30m", "1h", "2h", "6h", "12h", "24h"]
            if granularity not in valid_granularities:
                result.add_warning(
                    "merge.segmented.granularity",
                    granularity,
                    f"分段粒度建议使用: {valid_granularities}",
                )

        return result

    @staticmethod
    def validate_logging_config(logging_config: Dict[str, Any]) -> ValidationResult:
        """已移除日志配置验证，保持兼容返回通过。"""
        return ValidationResult(True, [], [])

    @staticmethod
    def validate_paths_exist(config: Dict[str, Any]) -> ValidationResult:
        """
        验证配置中的文件路径是否存在

        参数：
            config: 完整配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 检查默认路径配置
        ingest_config = config.get("ingest", {})
        default_paths = ingest_config.get("default_paths", {})

        if isinstance(default_paths, dict):
            # 验证映射文件
            mapping_file = default_paths.get("mapping_file", "")
            if mapping_file and isinstance(mapping_file, str):
                mapping_path = Path(mapping_file)
                if not mapping_path.exists():
                    result.add_warning(
                        "ingest.default_paths.mapping_file",
                        mapping_file,
                        f"映射文件不存在: {mapping_file}",
                    )
                elif not mapping_path.is_file():
                    result.add_error(
                        "ingest.default_paths.mapping_file",
                        mapping_file,
                        f"映射文件路径不是文件: {mapping_file}",
                    )

        return result

    @staticmethod
    def validate_complete_config(config: Dict[str, Any]) -> ValidationResult:
        """
        验证完整配置

        参数：
            config: 完整配置字典

        返回：
            ValidationResult: 验证结果
        """
        result = ValidationResult(True, [], [])

        # 验证各个子模块配置
        validators = [
            ("database", ConfigValidator.validate_database_config),
            ("web", ConfigValidator.validate_web_config),
            ("system", ConfigValidator.validate_system_config),
            ("ingest", ConfigValidator.validate_ingest_config),
            ("merge", ConfigValidator.validate_merge_config),
            ("logging", ConfigValidator.validate_logging_config),
        ]

        for config_name, validator_func in validators:
            if config_name in config:
                sub_result = validator_func(config[config_name])
                result.errors.extend(sub_result.errors)
                result.warnings.extend(sub_result.warnings)
                if not sub_result.is_valid:
                    result.is_valid = False

        # 验证路径存在性
        path_result = ConfigValidator.validate_paths_exist(config)
        result.errors.extend(path_result.errors)
        result.warnings.extend(path_result.warnings)
        if not path_result.is_valid:
            result.is_valid = False

        return result


def log_validation_result(result: ValidationResult) -> None:
    """占位的验证结果处理（无日志输出）。"""
    return None
