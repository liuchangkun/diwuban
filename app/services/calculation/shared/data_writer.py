"""
数据写入器（DataWriter）

职责：
- 批量写入 fact_measurements
- 自适应批量大小调整
- 错误处理和重试
- 性能监控
"""

from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class WriteRecord:
    """写入记录"""
    device_id: int
    metric_key: str
    timestamp: datetime
    value: float
    quality_code: int = 0
    method_id: str = None  # 计算方法ID（例如：method_a）
    calculated_at: datetime = None  # 计算时间


class DataWriter:
    """
    数据写入器（单例）

    职责：
    - 批量写入 fact_measurements
    - 自适应批量大小调整
    - 错误处理和重试
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        initial_batch_size: int = 1000,
        min_batch_size: int = 100,
        max_batch_size: int = 10000,
        target_duration_ms: int = 500
    ):
        """
        初始化数据写入器

        Args:
            initial_batch_size: 初始批量大小
            min_batch_size: 最小批量大小
            max_batch_size: 最大批量大小
            target_duration_ms: 目标写入耗时（毫秒）
        """
        if hasattr(self, '_initialized'):
            return

        self.batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.target_duration_ms = target_duration_ms

        self.total_written = 0
        self.total_duration_ms = 0

        self.logger = logging.getLogger(__name__)
        self._initialized = True

    def write(self, records: List[WriteRecord], station_id: int = 1) -> int:
        """
        批量写入数据（分批处理）

        Args:
            records: 写入记录列表
            station_id: 泵站ID（默认为1）

        Returns:
            成功写入的记录数
        """
        if not records:
            return 0

        import time
        import numpy as np

        write_start_time = time.time()

        # 增强日志：数据摘要（开始前）
        values = [r.value for r in records]
        quality_codes = [r.quality_code for r in records]
        quality_code_dist = {}
        for qc in quality_codes:
            quality_code_dist[qc] = quality_code_dist.get(qc, 0) + 1

        # 提取设备ID、指标名称、时间范围
        device_ids = list(set(r.device_id for r in records))
        metric_keys = list(set(r.metric_key for r in records))
        timestamps = [r.timestamp for r in records]
        time_range_str = f"{min(timestamps).strftime('%Y-%m-%d %H:%M:%S')} ~ {max(timestamps).strftime('%Y-%m-%d %H:%M:%S')}"

        self.logger.info(
            f"[数据写入] 开始写入",
            extra={'extra_data': {
                '总记录数': len(records),
                '设备ID列表': device_ids,
                '指标键列表': metric_keys,
                '时间范围': time_range_str,
                '最小值': round(float(np.min(values)), 2),
                '最大值': round(float(np.max(values)), 2),
                '平均值': round(float(np.mean(values)), 2),
                '标准差': round(float(np.std(values)), 2),
                '质量码分布': quality_code_dist
            }}
        )

        total_written = 0
        batch_durations = []

        # 使用固定的批量大小进行分批（避免在循环中动态调整导致混乱）
        current_batch_size = self.batch_size
        total_batches = (len(records) + current_batch_size - 1) // current_batch_size

        # 分批写入
        for batch_idx, i in enumerate(range(0, len(records), current_batch_size), start=1):
            batch = records[i:i + current_batch_size]
            batch_start_time = time.time()
            written = self._write_batch(batch, station_id, batch_idx, total_batches, adjust_batch_size=False)
            batch_duration = time.time() - batch_start_time
            batch_durations.append(batch_duration)
            total_written += written

        total_duration = time.time() - write_start_time
        avg_batch_duration = np.mean(batch_durations) if batch_durations else 0

        # 增强日志：写入完成
        self.logger.info(
            f"[数据写入] 写入完成: {total_written}条记录",
            extra={'extra_data': {
                '总记录数': len(records),
                '已写入记录数': total_written,
                '设备ID列表': device_ids,
                '指标键列表': metric_keys,
                '时间范围': time_range_str,
                '批次大小': current_batch_size,
                '总批次数': total_batches,
                '总执行时长秒': round(total_duration, 2),
                '平均批次时长ms': round(avg_batch_duration * 1000, 2),
                '吞吐量行每秒': round(total_written / total_duration, 2) if total_duration > 0 else 0
            }}
        )

        return total_written

    def _write_batch(self, batch: List[WriteRecord], station_id: int, batch_idx: int = 1, total_batches: int = 1, adjust_batch_size: bool = True) -> int:
        """
        写入单个批次（包含 ON CONFLICT 处理和自适应批量大小）

        Args:
            batch: 批次记录
            station_id: 泵站ID
            adjust_batch_size: 是否调整批量大小（默认True）

        Returns:
            成功写入的记录数
        """
        import time
        from app.adapters.db.pool import get_connection

        start_time = time.time()

        try:
            # 构造SQL（使用 ON CONFLICT 处理重复数据）
            # 注意：id 使用随机大整数，ts_raw 和 ts_bucket 都使用相同的时间戳
            sql = """
                INSERT INTO fact_measurements (
                    id, station_id, device_id, metric_id, ts_raw, ts_bucket, value, source_hint
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (station_id, device_id, metric_id, ts_bucket)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    source_hint = EXCLUDED.source_hint
            """

            # 准备数据（需要查询 metric_id）
            # 为了性能，先批量查询所有需要的 metric_id
            metric_keys = list(set(r.metric_key for r in batch))
            metric_id_map = self._get_metric_ids(metric_keys)

            # 准备批量数据
            import random
            data = []
            for r in batch:
                metric_id = metric_id_map.get(r.metric_key)
                if metric_id is None:
                    self.logger.warning(
                        f"[数据写入] 警告: 未找到指标 {r.metric_key} 的 metric_id",
                        extra={'extra_data': {'指标键': r.metric_key}}
                    )
                    continue

                # station_id 从参数传入

                # 生成随机ID（与现有数据导入逻辑一致）
                record_id = random.randint(1000000000000000, 9999999999999999)

                # 构造 source_hint：格式为 "method_id:calculated_at"
                source_hint = None
                if r.method_id and r.calculated_at:
                    # 格式化时间为 "YYYY-MM-DD HH:MM:SS"
                    calculated_at_str = r.calculated_at.strftime('%Y-%m-%d %H:%M:%S')
                    source_hint = f"{r.method_id}:{calculated_at_str}"

                data.append((
                    record_id,  # id
                    station_id,
                    r.device_id,
                    metric_id,
                    r.timestamp,  # ts_raw
                    r.timestamp,  # ts_bucket
                    r.value,
                    source_hint  # source_hint
                ))

            # 批量执行
            with get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(sql, data)
                    affected_rows = cursor.rowcount
                    conn.commit()

            # 记录性能
            duration_ms = int((time.time() - start_time) * 1000)
            self.total_written += len(data)
            self.total_duration_ms += duration_ms

            # 提取批次时间范围
            batch_timestamps = [r.timestamp for r in batch]
            batch_time_range = f"{min(batch_timestamps).strftime('%Y-%m-%d %H:%M:%S')} ~ {max(batch_timestamps).strftime('%Y-%m-%d %H:%M:%S')}"

            # 增强日志：批次写入完成
            self.logger.info(
                f"[数据写入] 批次写入完成: {batch_idx}/{total_batches}",
                extra={'extra_data': {
                    '批次序号': batch_idx,
                    '总批次数': total_batches,
                    '批次大小': len(batch),
                    '已写入记录数': len(data),
                    '时间范围': batch_time_range,
                    '影响行数': affected_rows,
                    '耗时ms': round(duration_ms, 2),
                    '吞吐量行每秒': round(len(data) / (duration_ms / 1000), 2) if duration_ms > 0 else 0
                }}
            )

            # 自适应调整批量大小（仅在允许时）
            if adjust_batch_size:
                self._adjust_batch_size(duration_ms)

            return len(data)

        except Exception as e:
            self.logger.error(
                f"[数据写入] 批次写入失败: {str(e)}",
                extra={'extra_data': {
                    '批次序号': batch_idx,
                    '总批次数': total_batches,
                    '批次大小': len(batch),
                    '错误信息': str(e)
                }}
            )
            raise

    def _get_metric_ids(self, metric_keys: List[str]) -> Dict[str, int]:
        """
        批量查询 metric_id

        Args:
            metric_keys: 指标键列表

        Returns:
            {metric_key: metric_id} 映射
        """
        from app.adapters.db.pool import get_connection

        if not metric_keys:
            return {}

        placeholders = ','.join(['%s'] * len(metric_keys))
        sql = f"""
            SELECT id, metric_key
            FROM dim_metric_config
            WHERE metric_key IN ({placeholders})
        """

        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, metric_keys)
                rows = cursor.fetchall()

        return {row[1]: row[0] for row in rows}

    def _adjust_batch_size(self, duration_ms: int):
        """
        自适应调整批量大小

        目标：保持写入耗时在 target_duration_ms 附近

        Args:
            duration_ms: 本次写入耗时（毫秒）
        """
        old_batch_size = self.batch_size

        if duration_ms < self.target_duration_ms * 0.5:
            # 耗时太短，增加批量大小
            new_batch_size = int(self.batch_size * 1.5)
            self.batch_size = min(new_batch_size, self.max_batch_size)

        elif duration_ms > self.target_duration_ms * 2:
            # 耗时太长，减少批量大小
            new_batch_size = int(self.batch_size * 0.7)
            self.batch_size = max(new_batch_size, self.min_batch_size)

        # 记录调整
        if self.batch_size != old_batch_size:
            self.logger.info(
                f"[数据写入] 批量大小调整: {old_batch_size} → {self.batch_size}",
                extra={'extra_data': {
                    '耗时ms': duration_ms,
                    '目标耗时ms': self.target_duration_ms
                }}
            )

    def get_stats(self) -> Dict:
        """获取写入统计"""
        return {
            'total_written': self.total_written,
            '总耗时（毫秒）': self.total_duration_ms,
            'avg_duration_ms': self.total_duration_ms / max(1, self.total_written / self.batch_size),
            'current_batch_size': self.batch_size
        }

