"""
泵组优化服务（app.services.optimization）

提供泵组运行优化的核心功能：
- 能耗优化：最小化电力消耗
- 效率优化：最大化系统效率
- 成本优化：最小化运行成本
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from app.core.config.loader import Settings
from app.core.exceptions import OptimizationError, error_handler
from app.models import (
    Optimization,
    OptimizationCreate,
    OptimizationRequest,
    OptimizationResult,
    OptimizationTarget,
    Device,
)
from app.adapters.db.gateway import get_conn

logger = logging.getLogger(__name__)


class OptimizationService:
    """
    泵组优化服务

    提供完整的泵组运行优化功能。
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.electricity_price = 0.8  # 电价（元/kWh）

    @error_handler(context_fields=["station_id", "target"])
    async def optimize(self, request: OptimizationRequest) -> OptimizationResult:
        """
        执行泵组优化
        """
        start_time = time.time()

        try:
            # 1. 获取泵站设备信息
            devices = await self._get_station_devices(request.station_id)
            if not devices:
                return OptimizationResult(
                    success=False,
                    error_message=f"未找到泵站 {request.station_id} 的设备信息",
                )

            # 2. 获取当前运行状态
            current_state = await self._get_current_operation_state(
                request.station_id, devices
            )

            # 3. 执行优化算法
            optimization_result = await self._optimize_pump_configuration(
                request, devices, current_state
            )

            # 4. 计算收益分析
            analysis = await self._calculate_savings_analysis(
                current_state, optimization_result, request.target
            )

            # 5. 生成优化记录
            optimization_record = await self._create_optimization_record(
                request, optimization_result, analysis
            )

            # 6. 组装结果
            result = OptimizationResult(
                success=True,
                optimization=optimization_record,
                improvement_percentage=analysis.get("improvement_percentage"),
                annual_savings_estimate=analysis.get("annual_savings"),
                current_performance=current_state,
                optimized_performance=optimization_result,
                implementation_steps=[
                    "1. 关闭部分水泵进行系统检查",
                    "2. 逐步调整水泵频率至推荐值",
                    "3. 监控系统运行状态和效果",
                    "4. 如果效果良好，固化优化参数",
                ],
                risks=[
                    "频率调整过快可能影响系统稳定性",
                    "需要监控水泵运行在高效区间",
                    "外部用水需求变化时需重新优化",
                ],
            )

            logger.info(
                "优化计算完成",
                extra={
                    "event": "optimization.completed",
                    "extra": {
                        "station_id": request.station_id,
                        "target": request.target,
                        "improvement": float(analysis.get("improvement_percentage", 0)),
                        "duration_ms": (time.time() - start_time) * 1000,
                    },
                },
            )

            return result

        except Exception as e:
            logger.error(f"优化计算失败: {e}")
            raise OptimizationError(f"优化计算失败: {e}") from e

    async def _get_station_devices(self, station_id: str) -> List[Device]:
        """获取泵站设备信息"""
        sql = """
        SELECT device_id, name, type, pump_type, rated_power,
               rated_flow, rated_head, status
        FROM device
        WHERE station_id = %s AND status = 'active'
        ORDER BY device_id
        """

        devices = []
        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (station_id,))

                for row in cur.fetchall():
                    (
                        device_id,
                        name,
                        device_type,
                        pump_type,
                        rated_power,
                        rated_flow,
                        rated_head,
                        status,
                    ) = row

                    device = Device(
                        device_id=device_id,
                        station_id=station_id,
                        name=name,
                        type=device_type,
                        pump_type=pump_type,
                        rated_power=Decimal(str(rated_power)) if rated_power else None,
                        rated_flow=Decimal(str(rated_flow)) if rated_flow else None,
                        rated_head=Decimal(str(rated_head)) if rated_head else None,
                        status=status,
                    )
                    devices.append(device)

        return devices

    async def _get_current_operation_state(
        self, station_id: str, devices: List[Device]
    ) -> Dict[str, Any]:
        """获取当前运行状态"""
        sql = """
        SELECT device_id, flow_rate, pressure, power, frequency
        FROM operation_data
        WHERE station_id = %s
            AND timestamp >= %s
        ORDER BY timestamp DESC
        LIMIT %s
        """

        recent_time = datetime.now() - timedelta(minutes=30)
        device_states = {}
        total_power = 0
        total_flow = 0

        with get_conn(self.settings) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (station_id, recent_time, len(devices) * 10))

                for row in cur.fetchall():
                    device_id, flow_rate, pressure, power, frequency = row

                    if device_id not in device_states:
                        device_states[device_id] = {
                            "flow_rate": float(flow_rate) if flow_rate else 0,
                            "power": float(power) if power else 0,
                            "pressure": float(pressure) if pressure else 0,
                            "frequency": float(frequency) if frequency else 0,
                        }
                        total_power += device_states[device_id]["power"]
                        total_flow += device_states[device_id]["flow_rate"]

        return {
            "device_states": device_states,
            "total_power": total_power,
            "total_flow": total_flow,
            "energy_cost_per_hour": total_power * self.electricity_price,
        }

    async def _optimize_pump_configuration(
        self,
        request: OptimizationRequest,
        devices: List[Device],
        current_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """优化水泵配置"""
        pump_devices = [d for d in devices if d.type == "pump"]

        if not pump_devices:
            raise OptimizationError("没有找到可优化的水泵设备")

        # 简化的优化策略
        optimized_config = {}

        for device in pump_devices:
            current_freq = (
                current_state["device_states"]
                .get(device.device_id, {})
                .get("frequency", 45.0)
            )

            if request.target == OptimizationTarget.MIN_ENERGY:
                # 能耗优化：适当降低频率
                optimized_freq = max(35.0, current_freq * 0.9)
            elif request.target == OptimizationTarget.MAX_EFFICIENCY:
                # 效率优化：调整到高效区间
                optimized_freq = 42.0  # 假设高效点
            else:
                # 默认保持当前频率
                optimized_freq = current_freq

            optimized_config[device.device_id] = {
                "frequency": round(optimized_freq, 2),
                "power_estimate": (
                    float(device.rated_power) * ((optimized_freq / 50.0) ** 3)
                    if device.rated_power
                    else 0
                ),
                "flow_estimate": (
                    float(device.rated_flow) * (optimized_freq / 50.0)
                    if device.rated_flow
                    else 0
                ),
            }

        return {
            "recommended_config": optimized_config,
            "optimization_success": True,
            "algorithm": "heuristic",
        }

    async def _calculate_savings_analysis(
        self,
        current_state: Dict[str, Any],
        optimization_result: Dict[str, Any],
        target: str,
    ) -> Dict[str, Any]:
        """计算收益分析"""
        current_power = current_state["total_power"]

        # 计算优化后的总功率
        optimized_power = sum(
            config["power_estimate"]
            for config in optimization_result["recommended_config"].values()
        )

        # 改进百分比
        if current_power > 0:
            improvement_percentage = (
                (current_power - optimized_power) / current_power * 100
            )
        else:
            improvement_percentage = 0

        # 年度节约估算（假设年运行 8760 小时）
        annual_energy_savings = (current_power - optimized_power) * 8760  # kWh
        annual_cost_savings = annual_energy_savings * self.electricity_price  # 元

        return {
            "improvement_percentage": Decimal(str(round(improvement_percentage, 2))),
            "annual_savings": Decimal(str(round(annual_cost_savings, 2))),
            "current_power": current_power,
            "optimized_power": optimized_power,
        }

    async def _create_optimization_record(
        self,
        request: OptimizationRequest,
        optimization_result: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Optimization:
        """创建优化记录"""
        optimization_data = OptimizationCreate(
            station_id=request.station_id,
            target=request.target,
            recommended_config=optimization_result["recommended_config"],
            expected_savings=analysis.get("improvement_percentage"),
            algorithm=optimization_result.get("algorithm"),
            constraints=request.constraints,
        )

        # 实际应该调用数据库网关保存
        optimization = Optimization(**optimization_data.model_dump())
        optimization.opt_id = 1  # 模拟数据库自增ID
        optimization.run_timestamp = datetime.now()

        return optimization
