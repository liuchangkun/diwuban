"""
数据导入服务（app.services.data_import）

提供 CSV 数据导入和处理功能：
- CSV 文件解析和验证
- Staging 表数据导入（COPY/UPSERT）
- 数据质量检查和清洗
- 合并到事实表的管理
"""

from __future__ import annotations

import csv
import logging
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config.loader import Settings
from app.core.exceptions import (
    DataValidationError,
    FileProcessingError,
    ImportError,
    error_handler,
)
from app.models import (
    DataPoint,
    MeasurementData,
    OperationData,
    TimeSeriesQuery,
)
from app.adapters.db.gateway import (
    get_conn,
    create_staging_if_not_exists,
    copy_valid_rows,
    run_merge_window,
)
from app.core.types import ValidRow, RejectRow

logger = logging.getLogger(__name__)


class DataImportService:
    """
    数据导入服务
    
    提供完整的 CSV 数据导入、验证和处理功能。
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # 导入配置
        self.batch_size = 10000
        self.max_errors = 100
        self.default_encoding = 'utf-8'
        
        # 支持的列映射
        self.column_mapping = {
            'station_name': 'station_name',
            'device_name': 'device_name', 
            'timestamp': 'DataTime',
            'flow_rate': 'flow_rate',
            'pressure': 'pressure',
            'power': 'power',
            'frequency': 'frequency',
            'TagName': 'TagName',
            'DataValue': 'DataValue'
        }
    
    @error_handler(context_fields=['file_path'])
    async def import_csv_file(
        self, 
        file_path: Path, 
        station_id: str,
        source_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        导入 CSV 文件
        
        Args:
            file_path: CSV 文件路径
            station_id: 泵站ID
            source_hint: 数据来源提示
            
        Returns:
            导入结果统计
        """
        start_time = time.time()
        
        if not file_path.exists():
            raise FileProcessingError(f"文件不存在: {file_path}")
        
        try:
            # 1. 创建 staging 表
            with get_conn(self.settings) as conn:
                create_staging_if_not_exists(conn)
            
            # 2. 解析 CSV 文件
            valid_rows, rejected_rows = await self._parse_csv_file(
                file_path, station_id, source_hint
            )
            
            # 3. 导入数据到 staging 表
            import_stats = await self._import_to_staging(
                valid_rows, rejected_rows
            )
            
            # 4. 执行数据合并（可选）
            # merge_stats = await self._merge_to_fact_table(station_id)
            
            result = {
                "success": True,
                "file_path": str(file_path),
                "station_id": station_id,
                "processing_time_ms": (time.time() - start_time) * 1000,
                "total_rows_processed": len(valid_rows) + len(rejected_rows),
                "valid_rows": len(valid_rows),
                "rejected_rows": len(rejected_rows),
                "import_stats": import_stats,
                # "merge_stats": merge_stats
            }
            
            logger.info(
                f"CSV 导入完成: {file_path.name}",
                extra={
                    "event": "data_import.csv_completed",
                    "extra": result
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"CSV 导入失败: {e}")
            raise ImportError(f"CSV 导入失败: {e}") from e
    
    async def _parse_csv_file(
        self, 
        file_path: Path, 
        station_id: str,
        source_hint: Optional[str]
    ) -> Tuple[List[ValidRow], List[RejectRow]]:
        """
        解析 CSV 文件
        """
        valid_rows = []
        rejected_rows = []
        
        try:
            with open(file_path, 'r', encoding=self.default_encoding) as file:
                # 自动检测 CSV 方言
                sniffer = csv.Sniffer()
                sample = file.read(1024)
                file.seek(0)
                
                delimiter = sniffer.sniff(sample).delimiter
                reader = csv.DictReader(file, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):  # 从第2行开始（跳过表头）
                    try:
                        # 数据验证和转换
                        validated_row = await self._validate_and_transform_row(
                            row, station_id, source_hint, row_num
                        )
                        
                        if validated_row:
                            valid_rows.append(validated_row)
                        
                    except Exception as e:
                        # 记录拒绝的行
                        reject_row = RejectRow(
                            station_name=station_id,
                            device_name=row.get('device_name', ''),
                            metric_key='unknown',
                            TagName=row.get('TagName', ''),
                            DataTime=row.get('DataTime', ''),
                            DataValue=row.get('DataValue', ''),
                            source_hint=source_hint or file_path.name,
                            error_msg=str(e)
                        )
                        rejected_rows.append(reject_row)
                        
                        # 如果错误过多，停止处理
                        if len(rejected_rows) > self.max_errors:
                            raise ImportError(
                                f"错误行数超过限制 {self.max_errors}，停止处理"
                            )
        
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    reader = csv.DictReader(file)
                    # 重复上面的逻辑...
                    pass
            except Exception as e:
                raise FileProcessingError(f"文件编码错误: {e}")
        
        return valid_rows, rejected_rows
    
    async def _validate_and_transform_row(
        self, 
        row: Dict[str, str], 
        station_id: str,
        source_hint: Optional[str],
        row_num: int
    ) -> Optional[ValidRow]:
        """
        验证和转换数据行
        """
        try:
            # 提取必要字段
            device_name = row.get('device_name', '').strip()
            tag_name = row.get('TagName', '').strip()
            data_time = row.get('DataTime', '').strip()
            data_value = row.get('DataValue', '').strip()
            
            if not all([device_name, tag_name, data_time, data_value]):
                raise DataValidationError("必要字段缺失")
            
            # 时间戳验证
            try:
                # 支持多种时间格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        parsed_time = datetime.strptime(data_time, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"不支持的时间格式: {data_time}")
            except ValueError as e:
                raise DataValidationError(f"时间格式错误: {e}")
            
            # 数值验证
            try:
                numeric_value = float(data_value)
                if not (-999999 <= numeric_value <= 999999):  # 合理范围检查
                    raise ValueError("数值超出合理范围")
            except ValueError as e:
                raise DataValidationError(f"数值格式错误: {e}")
            
            # 构建有效行
            valid_row = ValidRow(
                station_name=station_id,
                device_name=device_name,
                metric_key=self._map_tag_to_metric(tag_name),
                TagName=tag_name,
                DataTime=data_time,
                DataValue=data_value,
                source_hint=source_hint or 'csv_import'
            )
            
            return valid_row
            
        except Exception as e:
            raise DataValidationError(f"第{row_num}行数据验证失败: {e}")
    
    def _map_tag_to_metric(self, tag_name: str) -> str:
        """
        将标签名映射到指标键
        """
        tag_lower = tag_name.lower()
        
        if 'flow' in tag_lower or '流量' in tag_name:
            return 'flow_rate'
        elif 'pressure' in tag_lower or '压力' in tag_name:
            return 'pressure'
        elif 'power' in tag_lower or '功率' in tag_name:
            return 'power'
        elif 'frequency' in tag_lower or '频率' in tag_name:
            return 'frequency'
        elif 'head' in tag_lower or '扬程' in tag_name:
            return 'head'
        else:
            return 'other'
    
    async def _import_to_staging(
        self, 
        valid_rows: List[ValidRow], 
        rejected_rows: List[RejectRow]
    ) -> Dict[str, Any]:
        """
        导入数据到 staging 表
        """
        start_time = time.time()
        
        with get_conn(self.settings) as conn:
            # 导入有效行
            valid_count = 0
            if valid_rows:
                valid_count = copy_valid_rows(conn, valid_rows)
            
            # 导入拒绝行（如果有）
            rejected_count = 0
            if rejected_rows:
                rejected_count = len(rejected_rows)
                # 这里可以添加导入拒绝行的逻辑
                # insert_rejected_rows(conn, rejected_rows)
        
        return {
            "valid_rows_imported": valid_count,
            "rejected_rows_recorded": rejected_count,
            "import_duration_ms": (time.time() - start_time) * 1000
        }
    
    async def get_import_statistics(
        self, 
        station_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取导入统计信息
        """
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                # 统计 staging 表中的数据
                staging_sql = """
                SELECT COUNT(*) as total_rows,
                       COUNT(DISTINCT device_name) as device_count,
                       MIN(loaded_at) as first_loaded,
                       MAX(loaded_at) as last_loaded
                FROM staging_raw
                WHERE station_name = %s
                """
                
                params = [station_id]
                if start_date:
                    staging_sql += " AND loaded_at >= %s"
                    params.append(start_date)
                if end_date:
                    staging_sql += " AND loaded_at <= %s"
                    params.append(end_date)
                
                cur.execute(staging_sql, params)
                staging_result = cur.fetchone()
                
                # 统计拒绝表中的数据
                reject_sql = """
                SELECT COUNT(*) as reject_count,
                       COUNT(DISTINCT error_msg) as error_types
                FROM staging_rejects
                WHERE station_name = %s
                """
                
                if start_date and end_date:
                    reject_sql += " AND rejected_at BETWEEN %s AND %s"
                    cur.execute(reject_sql, [station_id, start_date, end_date])
                else:
                    cur.execute(reject_sql, [station_id])
                
                reject_result = cur.fetchone()
                
                return {
                    "station_id": station_id,
                    "total_staging_rows": staging_result[0] if staging_result else 0,
                    "device_count": staging_result[1] if staging_result else 0,
                    "first_loaded": staging_result[2] if staging_result else None,
                    "last_loaded": staging_result[3] if staging_result else None,
                    "rejected_rows": reject_result[0] if reject_result else 0,
                    "error_types_count": reject_result[1] if reject_result else 0,
                }
    
    async def cleanup_old_staging_data(
        self, 
        days_to_keep: int = 7
    ) -> Dict[str, Any]:
        """
        清理老旧的 staging 数据
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                # 清理 staging_raw
                cur.execute(
                    "DELETE FROM staging_raw WHERE loaded_at < %s",
                    (cutoff_date,)
                )
                deleted_staging = cur.rowcount
                
                # 清理 staging_rejects
                cur.execute(
                    "DELETE FROM staging_rejects WHERE rejected_at < %s",
                    (cutoff_date,)
                )
                deleted_rejects = cur.rowcount
                
                conn.commit()
                
                logger.info(
                    f"清理完成: staging={deleted_staging}, rejects={deleted_rejects}"
                )
                
                return {
                    "deleted_staging_rows": deleted_staging,
                    "deleted_reject_rows": deleted_rejects,
                    "cutoff_date": cutoff_date
                }
