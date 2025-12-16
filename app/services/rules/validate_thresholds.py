"""
设备运行阈值验证模块

职责：
- 验证 device_running_thresholds 表的完整性
- 检查核心字段是否为 NULL
- 检查是否所有设备都有阈值配置
- 提供详细的验证报告和警告信息

依赖：
- app.adapters.db.gateway: 数据库连接
- logging: 日志记录

作者：AI
创建日期：2025-10-24
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from app.adapters.db.gateway import get_conn

_act = logging.getLogger(__name__)


def validate_device_running_thresholds(
    settings,
    device_id: Optional[int] = None,
) -> Dict[str, Any]:
    """验证 device_running_thresholds 表的完整性。
    
    验证内容：
    1. 检查表是否为空
    2. 检查核心字段是否为 NULL：
       - enable_i, i_on, i_off（电流阈值）
       - grace_hold_secs, min_run_secs, min_stop_secs, smoothing_secs（时间参数）
    3. 检查是否所有 dim_devices 中的设备都有对应的阈值配置
    
    参数：
    - settings: 应用配置
    - device_id: 设备ID过滤（NULL则验证所有设备）
    
    返回值：
    - is_valid: bool，是否通过验证
    - total_devices: int，总设备数
    - configured_devices: int，已配置阈值的设备数
    - missing_devices: List[int]，缺少阈值配置的设备ID列表
    - incomplete_devices: List[Dict]，阈值配置不完整的设备列表
    - warnings: List[str]，警告信息列表
    - summary: str，验证摘要
    """
    _act.info(
        "[验证-开始] [设备运行阈值验证]",
        extra={"extra_data": {"device_id": device_id}},
    )

    result: Dict[str, Any] = {
        "is_valid": True,
        "total_devices": 0,
        "configured_devices": 0,
        "missing_devices": [],
        "incomplete_devices": [],
        "warnings": [],
        "summary": "",
    }

    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # =====================================================================
            # 步骤1：检查表是否为空
            # =====================================================================
            _act.info("[验证-步骤1] [检查表是否为空]")
            cur.execute("SELECT COUNT(*) FROM device_running_thresholds")
            threshold_count = int(cur.fetchone()[0])

            if threshold_count == 0:
                result["is_valid"] = False
                result["warnings"].append("device_running_thresholds 表为空，没有任何阈值配置")
                _act.warning(
                    "[验证-失败] [表为空]",
                    extra={"extra_data": {"threshold_count": threshold_count}},
                )
                result["summary"] = "验证失败：device_running_thresholds 表为空"
                return result

            _act.info(
                "[验证-步骤1] [表不为空]",
                extra={"extra_data": {"threshold_count": threshold_count}},
            )

            # =====================================================================
            # 步骤2：检查是否所有设备都有阈值配置
            # =====================================================================
            _act.info("[验证-步骤2] [检查设备覆盖率]")
            cur.execute(
                """
                SELECT COUNT(*)
                FROM dim_devices d
                WHERE d.is_active = TRUE
                  AND COALESCE(NULLIF(d.type,''),'') NOT IN ('main_pipeline','clear_water_pool','other')
                  AND (%s::bigint IS NULL OR d.id = %s::bigint)
                """,
                (device_id, device_id),
            )
            total_devices = int(cur.fetchone()[0])
            result["total_devices"] = total_devices

            cur.execute(
                """
                SELECT d.id
                FROM dim_devices d
                LEFT JOIN device_running_thresholds t ON t.device_id = d.id
                WHERE d.is_active = TRUE
                  AND COALESCE(NULLIF(d.type,''),'') NOT IN ('main_pipeline','clear_water_pool','other')
                  AND (%s::bigint IS NULL OR d.id = %s::bigint)
                  AND t.device_id IS NULL
                ORDER BY d.id
                """,
                (device_id, device_id),
            )
            missing_devices = [int(row[0]) for row in cur.fetchall()]
            result["missing_devices"] = missing_devices

            if missing_devices:
                result["is_valid"] = False
                result["warnings"].append(
                    f"发现 {len(missing_devices)} 个设备缺少阈值配置：{missing_devices}"
                )
                _act.warning(
                    "[验证-失败] [设备缺少阈值配置]",
                    extra={"extra_data": {"missing_devices": missing_devices}},
                )

            result["configured_devices"] = total_devices - len(missing_devices)
            _act.info(
                "[验证-步骤2] [设备覆盖率检查完成]",
                extra={
                    "extra_data": {
                        "total_devices": total_devices,
                        "configured_devices": result["configured_devices"],
                        "missing_devices_count": len(missing_devices),
                    }
                },
            )

            # =====================================================================
            # 步骤3：检查核心字段是否为 NULL
            # =====================================================================
            _act.info("[验证-步骤3] [检查核心字段完整性]")
            cur.execute(
                """
                SELECT 
                    t.device_id,
                    d.name AS device_name,
                    t.enable_i,
                    t.i_on,
                    t.i_off,
                    t.grace_hold_secs,
                    t.min_run_secs,
                    t.min_stop_secs,
                    t.smoothing_secs
                FROM device_running_thresholds t
                JOIN dim_devices d ON d.id = t.device_id
                WHERE (%s::bigint IS NULL OR t.device_id = %s::bigint)
                  AND (
                    t.i_on IS NULL 
                    OR t.i_off IS NULL
                    OR t.grace_hold_secs = 0
                    OR t.min_run_secs = 0
                    OR t.min_stop_secs = 0
                    OR t.smoothing_secs = 0
                  )
                ORDER BY t.device_id
                """,
                (device_id, device_id),
            )

            incomplete_devices: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                device_info = {
                    "device_id": int(row[0]),
                    "device_name": row[1],
                    "enable_i": row[2],
                    "i_on": float(row[3]) if row[3] is not None else None,
                    "i_off": float(row[4]) if row[4] is not None else None,
                    "grace_hold_secs": int(row[5]),
                    "min_run_secs": int(row[6]),
                    "min_stop_secs": int(row[7]),
                    "smoothing_secs": int(row[8]),
                    "missing_fields": [],
                }

                # 检查哪些字段缺失
                if row[3] is None:
                    device_info["missing_fields"].append("i_on")
                if row[4] is None:
                    device_info["missing_fields"].append("i_off")
                if row[5] == 0:
                    device_info["missing_fields"].append("grace_hold_secs")
                if row[6] == 0:
                    device_info["missing_fields"].append("min_run_secs")
                if row[7] == 0:
                    device_info["missing_fields"].append("min_stop_secs")
                if row[8] == 0:
                    device_info["missing_fields"].append("smoothing_secs")

                incomplete_devices.append(device_info)

            result["incomplete_devices"] = incomplete_devices

            if incomplete_devices:
                result["is_valid"] = False
                result["warnings"].append(
                    f"发现 {len(incomplete_devices)} 个设备的阈值配置不完整"
                )
                for device in incomplete_devices[:5]:  # 只记录前5个
                    result["warnings"].append(
                        f"  设备 {device['device_id']} ({device['device_name']}): "
                        f"缺失字段 {', '.join(device['missing_fields'])}"
                    )
                if len(incomplete_devices) > 5:
                    result["warnings"].append(f"  ... 还有 {len(incomplete_devices) - 5} 个设备")

                _act.warning(
                    "[验证-失败] [阈值配置不完整]",
                    extra={
                        "extra_data": {
                            "incomplete_devices_count": len(incomplete_devices),
                            "sample_devices": incomplete_devices[:3],
                        }
                    },
                )

            _act.info(
                "[验证-步骤3] [核心字段完整性检查完成]",
                extra={"extra_data": {"incomplete_devices_count": len(incomplete_devices)}},
            )

    # =====================================================================
    # 生成验证摘要
    # =====================================================================
    if result["is_valid"]:
        result["summary"] = (
            f"验证通过：所有 {total_devices} 个设备的阈值配置完整"
        )
        _act.info(
            "[验证-成功] [所有设备阈值配置完整]",
            extra={"extra_data": {"total_devices": total_devices}},
        )
    else:
        result["summary"] = (
            f"验证失败：{len(missing_devices)} 个设备缺少配置，"
            f"{len(incomplete_devices)} 个设备配置不完整"
        )
        _act.warning(
            "[验证-失败] [存在配置问题]",
            extra={
                "extra_data": {
                    "missing_devices_count": len(missing_devices),
                    "incomplete_devices_count": len(incomplete_devices),
                }
            },
        )

    _act.info(
        "[验证-完成] [设备运行阈值验证]",
        extra={"extra_data": {"is_valid": result["is_valid"], "summary": result["summary"]}},
    )

    return result

