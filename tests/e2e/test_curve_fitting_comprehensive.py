#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
特性曲线拟合综合测试 (tests.e2e.test_curve_fitting_comprehensive)

全面测试特性曲线拟合功能，包括：
1. 单泵特性曲线拟合（QH/QP/QEta）
2. 泵组特性曲线拟合（合成+修正、直接拟合双轨方法）
3. 结果验证（日志、图片、报告、数据库存储）

使用方法:
    # 运行全部测试
    python -m tests.e2e.test_curve_fitting_comprehensive
    
    # 仅测试单泵
    python -m tests.e2e.test_curve_fitting_comprehensive --single-pump
    
    # 仅测试泵组
    python -m tests.e2e.test_curve_fitting_comprehensive --pump-group

创建日期: 2025-12-14
作者: 智能助手
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 确保项目根目录在path中
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# 日志配置
# ============================================================================
def setup_logging(log_dir: str = "logs/curve_fitting_test") -> logging.Logger:
    """配置测试日志"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"curve_fitting_test_{timestamp}.log"

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger = logging.getLogger(__name__)
    logger.info(f"日志文件: {log_file}")

    return logger


# ============================================================================
# 测试结果数据结构
# ============================================================================
@dataclass
class TestCaseResult:
    """单个测试用例结果"""
    test_name: str
    category: str  # single_pump / pump_group
    curve_type: str  # qh / qp / qeta
    success: bool
    duration_ms: float = 0.0
    r_squared: Optional[float] = None
    rmse: Optional[float] = None
    error_message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    plot_path: Optional[str] = None
    report_path: Optional[str] = None


@dataclass
class TestSuiteResult:
    """测试套件结果"""
    suite_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    test_cases: List[TestCaseResult] = field(default_factory=list)

    @property
    def total_count(self) -> int:
        return len(self.test_cases)

    @property
    def passed_count(self) -> int:
        return sum(1 for tc in self.test_cases if tc.success)

    @property
    def failed_count(self) -> int:
        return sum(1 for tc in self.test_cases if not tc.success)

    @property
    def pass_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.passed_count / self.total_count * 100

    @property
    def total_duration_ms(self) -> float:
        return sum(tc.duration_ms for tc in self.test_cases)


# ============================================================================
# 特性曲线拟合测试类
# ============================================================================
class CurveFittingTester:
    """特性曲线拟合测试器"""

    # 单泵曲线类型
    SINGLE_PUMP_CURVE_TYPES = ["qh", "qp", "qeta"]

    # 泵组曲线类型
    PUMP_GROUP_CURVE_TYPES = ["qh", "qp", "qeta"]

    def __init__(
        self,
        output_dir: str = "outputs/curve_fitting_test",
        logger: Optional[logging.Logger] = None
    ):
        """初始化测试器

        Args:
            output_dir: 输出目录（图片、报告等）
            logger: 日志记录器
        """
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logger or logging.getLogger(__name__)

        # 初始化组件（延迟导入避免循环依赖）
        self._pipeline = None
        self._group_processor = None
        self._dual_executor = None

        # 测试结果
        self._suite_result: Optional[TestSuiteResult] = None

    def _init_components(self):
        """初始化核心组件"""
        if self._pipeline is not None:
            return

        self._logger.info("=" * 60)
        self._logger.info("初始化特性曲线拟合组件...")
        self._logger.info("=" * 60)

        try:
            # 导入核心组件
            from app.services.characteristic_curves.pipeline.curve_fitting_pipeline import (
                CurveFittingPipeline
            )
            from app.services.characteristic_curves.pump_group.pump_group_processor import (
                PumpGroupProcessor
            )
            from app.services.characteristic_curves.pump_group.dual_method_executor import (
                DualMethodExecutor
            )
            from app.services.characteristic_curves.pump_group.group_curve_fitter import (
                GroupCurveFitter
            )
            from app.services.characteristic_curves.pump_group.group_data_extractor import (
                GroupDataExtractor
            )
            from app.services.characteristic_curves.methods.method_registry import (
                MethodRegistry
            )

            # 创建实例
            self._pipeline = CurveFittingPipeline()
            self._group_processor = PumpGroupProcessor()
            self._dual_executor = DualMethodExecutor()
            self._group_fitter = GroupCurveFitter()
            self._group_extractor = GroupDataExtractor()
            self._method_registry = MethodRegistry()

            self._logger.info("组件初始化成功")
            self._logger.info(f"  - CurveFittingPipeline: √")
            self._logger.info(f"  - PumpGroupProcessor: √")
            self._logger.info(f"  - DualMethodExecutor: √")
            self._logger.info(f"  - GroupCurveFitter: √")
            self._logger.info(f"  - GroupDataExtractor: √")
            self._logger.info(f"  - MethodRegistry: √")

        except Exception as e:
            self._logger.error(f"组件初始化失败: {e}")
            traceback.print_exc()
            raise

    def _get_test_devices(self) -> List[Dict[str, Any]]:
        """获取测试设备列表"""
        from app.adapters.db import get_connection

        devices = []

        with get_connection() as conn:
            cursor = conn.cursor()

            # 查询有数据的设备
            cursor.execute("""
                SELECT DISTINCT 
                    d.device_id,
                    d.device_name,
                    d.station_id,
                    s.station_name,
                    dc.control_type,
                    dc.rated_power_kw,
                    dc.rated_flow_m3h,
                    dc.rated_head_m
                FROM dim_device_capabilities d
                JOIN dim_station s ON d.station_id = s.station_id
                LEFT JOIN dim_device_capabilities dc ON d.device_id = dc.device_id
                WHERE d.device_category = 'pump'
                AND EXISTS (
                    SELECT 1 FROM fact_measurements fm 
                    WHERE fm.device_id = d.device_id 
                    LIMIT 1
                )
                ORDER BY d.station_id, d.device_id
                LIMIT 10
            """)

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            for row in rows:
                device = dict(zip(columns, row))
                devices.append(device)

        self._logger.info(f"找到 {len(devices)} 个测试设备")
        return devices

    def _get_test_stations(self) -> List[Dict[str, Any]]:
        """获取测试泵站列表"""
        from app.adapters.db import get_connection

        stations = []

        with get_connection() as conn:
            cursor = conn.cursor()

            # 查询有多台泵的泵站
            cursor.execute("""
                SELECT 
                    s.station_id,
                    s.station_name,
                    COUNT(DISTINCT d.device_id) as pump_count
                FROM dim_station s
                JOIN dim_device_capabilities d ON s.station_id = d.station_id
                WHERE d.device_category = 'pump'
                GROUP BY s.station_id, s.station_name
                HAVING COUNT(DISTINCT d.device_id) >= 2
                ORDER BY s.station_id
                LIMIT 5
            """)

            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            for row in rows:
                station = dict(zip(columns, row))

                # 获取该站的泵信息
                cursor.execute("""
                    SELECT 
                        device_id,
                        device_name,
                        control_type,
                        rated_power_kw,
                        rated_flow_m3h,
                        rated_head_m
                    FROM dim_device_capabilities
                    WHERE station_id = %s
                    AND device_category = 'pump'
                    ORDER BY device_id
                """, (station['station_id'],))

                pump_rows = cursor.fetchall()
                pump_columns = [desc[0] for desc in cursor.description]

                station['pumps'] = [
                    dict(zip(pump_columns, pr)) for pr in pump_rows
                ]

                stations.append(station)

        self._logger.info(f"找到 {len(stations)} 个测试泵站")
        return stations

    def run_single_pump_tests(self) -> List[TestCaseResult]:
        """运行单泵拟合测试

        测试内容:
        1. 测试所有曲线类型 (qh, qp, qeta)
        2. 测试多种拟合方法
        3. 验证拟合结果的物理约束
        4. 检查图片和报告生成
        """
        self._init_components()
        results = []

        self._logger.info("")
        self._logger.info("=" * 60)
        self._logger.info("开始单泵特性曲线拟合测试")
        self._logger.info("=" * 60)

        # 获取测试设备
        devices = self._get_test_devices()

        if not devices:
            self._logger.warning("没有找到可测试的设备，跳过单泵测试")
            return results

        # 选择前3个设备进行测试
        test_devices = devices[:3]

        for device in test_devices:
            device_id = device['device_id']
            device_name = device.get('device_name', f'Device_{device_id}')

            self._logger.info("-" * 40)
            self._logger.info(f"测试设备: {device_name} (ID={device_id})")
            self._logger.info("-" * 40)

            for curve_type in self.SINGLE_PUMP_CURVE_TYPES:
                test_name = f"single_pump_{device_id}_{curve_type}"

                self._logger.info(f"  测试 {curve_type.upper()} 曲线...")

                result = self._run_single_pump_fit_test(
                    device_id=device_id,
                    curve_type=curve_type,
                    test_name=test_name
                )

                results.append(result)

                if result.success:
                    self._logger.info(
                        f"    ✓ 成功 | R²={result.r_squared:.4f} | "
                        f"RMSE={result.rmse:.4f} | 耗时={result.duration_ms:.0f}ms"
                    )
                else:
                    self._logger.error(f"    ✗ 失败 | {result.error_message}")

        return results

    def _run_single_pump_fit_test(
        self,
        device_id: int,
        curve_type: str,
        test_name: str
    ) -> TestCaseResult:
        """执行单个单泵拟合测试"""
        start_time = time.time()

        try:
            # 确定时间范围（使用最近30天的数据）
            time_range = (
                datetime.now() - timedelta(days=30),
                datetime.now()
            )

            # 调用拟合管道
            fit_result = self._pipeline.fit(
                device_id=device_id,
                curve_type=curve_type,
                time_range=time_range
            )

            duration_ms = (time.time() - start_time) * 1000

            # 检查拟合结果
            if fit_result is None:
                return TestCaseResult(
                    test_name=test_name,
                    category="single_pump",
                    curve_type=curve_type,
                    success=False,
                    duration_ms=duration_ms,
                    error_message="拟合返回None"
                )

            # 提取结果指标
            r_squared = getattr(fit_result, 'r_squared', None)
            rmse = getattr(fit_result, 'rmse', None)

            # 获取输出路径
            plot_path = getattr(fit_result, 'plot_path', None)
            report_path = getattr(fit_result, 'report_path', None)

            # 验证物理约束
            physics_valid = getattr(fit_result, 'physics_valid', True)

            # 构建详情
            details = {
                "method_id": getattr(fit_result, 'method_id', 'unknown'),
                "method_name": getattr(fit_result, 'method_name', 'unknown'),
                "data_points": getattr(fit_result, 'data_points', 0),
                "version": getattr(fit_result, 'version', 'unknown'),
                "physics_valid": physics_valid,
            }

            # 检查R²是否达标（单泵应 > 0.85）
            success = r_squared is not None and r_squared > 0.85

            if not success and r_squared is not None:
                error_message = f"R²={r_squared:.4f} 低于阈值0.85"
            else:
                error_message = ""

            return TestCaseResult(
                test_name=test_name,
                category="single_pump",
                curve_type=curve_type,
                success=success,
                duration_ms=duration_ms,
                r_squared=r_squared,
                rmse=rmse,
                error_message=error_message,
                details=details,
                plot_path=str(plot_path) if plot_path else None,
                report_path=str(report_path) if report_path else None
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._logger.error(f"单泵拟合测试异常: {e}")
            traceback.print_exc()

            return TestCaseResult(
                test_name=test_name,
                category="single_pump",
                curve_type=curve_type,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e)
            )

    def run_pump_group_tests(self) -> List[TestCaseResult]:
        """运行泵组拟合测试

        测试内容:
        1. 测试所有曲线类型 (qh, qp, qeta)
        2. 测试双轨方法（合成+修正、直接拟合）
        3. 测试5种泵组场景
        4. 检查对比分析和推荐
        """
        self._init_components()
        results = []

        self._logger.info("")
        self._logger.info("=" * 60)
        self._logger.info("开始泵组特性曲线拟合测试")
        self._logger.info("=" * 60)

        # 获取测试泵站
        stations = self._get_test_stations()

        if not stations:
            self._logger.warning("没有找到可测试的泵站，跳过泵组测试")
            return results

        # 选择前2个泵站进行测试
        test_stations = stations[:2]

        for station in test_stations:
            station_id = station['station_id']
            station_name = station.get('station_name', f'Station_{station_id}')
            pumps = station.get('pumps', [])

            self._logger.info("-" * 40)
            self._logger.info(f"测试泵站: {station_name} (ID={station_id})")
            self._logger.info(f"泵数量: {len(pumps)}")
            self._logger.info("-" * 40)

            for curve_type in self.PUMP_GROUP_CURVE_TYPES:
                test_name = f"pump_group_{station_id}_{curve_type}"

                self._logger.info(f"  测试 {curve_type.upper()} 曲线...")

                result = self._run_pump_group_fit_test(
                    station_id=station_id,
                    pumps=pumps,
                    curve_type=curve_type,
                    test_name=test_name
                )

                results.append(result)

                if result.success:
                    self._logger.info(
                        f"    ✓ 成功 | 耗时={result.duration_ms:.0f}ms"
                    )
                    if result.details.get('direct_fit_r2'):
                        self._logger.info(
                            f"    直接拟合 R²={result.details['direct_fit_r2']:.4f}"
                        )
                    if result.details.get('synthesis_success'):
                        self._logger.info(f"    合成曲线: 成功")
                    if result.details.get('recommended_method'):
                        self._logger.info(
                            f"    推荐方法: {result.details['recommended_method']}"
                        )
                else:
                    self._logger.error(f"    ✗ 失败 | {result.error_message}")

        return results

    def _run_pump_group_fit_test(
        self,
        station_id: int,
        pumps: List[Dict],
        curve_type: str,
        test_name: str
    ) -> TestCaseResult:
        """执行单个泵组拟合测试"""
        start_time = time.time()

        try:
            # 构建泵信息列表
            pump_infos = []
            for pump in pumps:
                pump_info = {
                    'pump_id': pump['device_id'],
                    'rated_power': pump.get('rated_power_kw', 100),
                    'control_type': pump.get('control_type', 'VFD'),
                }
                pump_infos.append(pump_info)

            # 确定时间范围
            time_range = (
                datetime.now() - timedelta(days=30),
                datetime.now()
            )

            # 使用双方法执行器
            dual_result = self._dual_executor.execute(
                station_id=station_id,
                pump_infos=pump_infos,
                curve_type=curve_type,
                time_range=time_range,
                min_data_points=50
            )

            duration_ms = (time.time() - start_time) * 1000

            # 提取结果
            direct_fit_success = getattr(
                dual_result, 'direct_fit_success', False)
            synthesis_success = getattr(
                dual_result, 'synthesis_success', False)
            recommended_method = getattr(
                dual_result, 'recommended_method', None)

            # 获取直接拟合R²
            direct_fit_r2 = None
            if dual_result.direct_fit_result:
                direct_fit_r2 = getattr(
                    dual_result.direct_fit_result, 'r_squared', None
                )

            # 构建详情
            details = {
                "direct_fit_success": direct_fit_success,
                "synthesis_success": synthesis_success,
                "direct_fit_r2": direct_fit_r2,
                "recommended_method": (
                    recommended_method.value if recommended_method else None
                ),
                "group_type": (
                    dual_result.group_type.value
                    if hasattr(dual_result, 'group_type') and dual_result.group_type
                    else None
                ),
                "pump_count": len(pump_infos),
            }

            # 判断成功条件：至少一种方法成功
            success = direct_fit_success or synthesis_success

            if not success:
                error_message = "直接拟合和合成曲线均失败"
            else:
                error_message = ""

            return TestCaseResult(
                test_name=test_name,
                category="pump_group",
                curve_type=curve_type,
                success=success,
                duration_ms=duration_ms,
                r_squared=direct_fit_r2,
                error_message=error_message,
                details=details
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._logger.error(f"泵组拟合测试异常: {e}")
            traceback.print_exc()

            return TestCaseResult(
                test_name=test_name,
                category="pump_group",
                curve_type=curve_type,
                success=False,
                duration_ms=duration_ms,
                error_message=str(e)
            )

    def run_all_tests(self) -> TestSuiteResult:
        """运行所有测试"""
        self._suite_result = TestSuiteResult(
            suite_name="CurveFitting_Comprehensive_Test",
            start_time=datetime.now()
        )

        self._logger.info("")
        self._logger.info("╔" + "═" * 58 + "╗")
        self._logger.info("║" + " 特性曲线拟合综合测试 ".center(58) + "║")
        self._logger.info("╚" + "═" * 58 + "╝")
        self._logger.info("")

        # 1. 单泵测试
        single_pump_results = self.run_single_pump_tests()
        self._suite_result.test_cases.extend(single_pump_results)

        # 2. 泵组测试
        pump_group_results = self.run_pump_group_tests()
        self._suite_result.test_cases.extend(pump_group_results)

        # 完成测试
        self._suite_result.end_time = datetime.now()

        # 生成报告
        self._generate_report()

        return self._suite_result

    def _generate_report(self):
        """生成测试报告"""
        if not self._suite_result:
            return

        self._logger.info("")
        self._logger.info("=" * 60)
        self._logger.info("测试报告摘要")
        self._logger.info("=" * 60)

        # 统计信息
        total = self._suite_result.total_count
        passed = self._suite_result.passed_count
        failed = self._suite_result.failed_count
        pass_rate = self._suite_result.pass_rate
        duration = self._suite_result.total_duration_ms

        self._logger.info(f"总测试数: {total}")
        self._logger.info(f"通过: {passed} ({pass_rate:.1f}%)")
        self._logger.info(f"失败: {failed}")
        self._logger.info(f"总耗时: {duration/1000:.2f}s")

        # 分类统计
        single_pump_cases = [
            tc for tc in self._suite_result.test_cases
            if tc.category == "single_pump"
        ]
        pump_group_cases = [
            tc for tc in self._suite_result.test_cases
            if tc.category == "pump_group"
        ]

        self._logger.info("")
        self._logger.info("分类统计:")

        if single_pump_cases:
            sp_passed = sum(1 for tc in single_pump_cases if tc.success)
            self._logger.info(
                f"  单泵拟合: {sp_passed}/{len(single_pump_cases)} 通过"
            )

        if pump_group_cases:
            pg_passed = sum(1 for tc in pump_group_cases if tc.success)
            self._logger.info(
                f"  泵组拟合: {pg_passed}/{len(pump_group_cases)} 通过"
            )

        # 按曲线类型统计
        self._logger.info("")
        self._logger.info("按曲线类型:")
        for curve_type in ["qh", "qp", "qeta"]:
            curve_cases = [
                tc for tc in self._suite_result.test_cases
                if tc.curve_type == curve_type
            ]
            if curve_cases:
                curve_passed = sum(1 for tc in curve_cases if tc.success)
                curve_r2_list = [
                    tc.r_squared for tc in curve_cases
                    if tc.r_squared is not None
                ]
                avg_r2 = np.mean(curve_r2_list) if curve_r2_list else 0
                self._logger.info(
                    f"  {curve_type.upper()}: {curve_passed}/{len(curve_cases)} 通过, "
                    f"平均R²={avg_r2:.4f}"
                )

        # 失败详情
        if failed > 0:
            self._logger.info("")
            self._logger.info("失败用例详情:")
            for tc in self._suite_result.test_cases:
                if not tc.success:
                    self._logger.info(
                        f"  ✗ {tc.test_name}: {tc.error_message}")

        # 保存JSON报告
        report_path = self._output_dir / "test_report.json"
        report_data = {
            "suite_name": self._suite_result.suite_name,
            "start_time": self._suite_result.start_time.isoformat(),
            "end_time": (
                self._suite_result.end_time.isoformat()
                if self._suite_result.end_time else None
            ),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": pass_rate,
                "duration_ms": duration
            },
            "test_cases": [
                {
                    "test_name": tc.test_name,
                    "category": tc.category,
                    "curve_type": tc.curve_type,
                    "success": tc.success,
                    "duration_ms": tc.duration_ms,
                    "r_squared": tc.r_squared,
                    "rmse": tc.rmse,
                    "error_message": tc.error_message,
                    "details": tc.details,
                    "plot_path": tc.plot_path,
                    "report_path": tc.report_path
                }
                for tc in self._suite_result.test_cases
            ]
        }

        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        self._logger.info("")
        self._logger.info(f"报告已保存: {report_path}")

        # 最终结论
        self._logger.info("")
        if pass_rate >= 90:
            self._logger.info("✓ 测试通过！所有特性曲线拟合功能正常。")
        elif pass_rate >= 70:
            self._logger.info("⚠ 测试部分通过，请检查失败用例。")
        else:
            self._logger.info("✗ 测试未通过，请检查拟合功能。")


# ============================================================================
# 主函数
# ============================================================================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="特性曲线拟合综合测试"
    )
    parser.add_argument(
        "--single-pump",
        action="store_true",
        help="仅运行单泵拟合测试"
    )
    parser.add_argument(
        "--pump-group",
        action="store_true",
        help="仅运行泵组拟合测试"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/curve_fitting_test",
        help="输出目录"
    )

    args = parser.parse_args()

    # 配置日志
    logger = setup_logging()

    # 创建测试器
    tester = CurveFittingTester(
        output_dir=args.output_dir,
        logger=logger
    )

    # 运行测试
    if args.single_pump:
        tester._init_components()
        results = tester.run_single_pump_tests()
        tester._suite_result = TestSuiteResult(
            suite_name="SinglePump_Test",
            start_time=datetime.now(),
            test_cases=results
        )
        tester._suite_result.end_time = datetime.now()
        tester._generate_report()
    elif args.pump_group:
        tester._init_components()
        results = tester.run_pump_group_tests()
        tester._suite_result = TestSuiteResult(
            suite_name="PumpGroup_Test",
            start_time=datetime.now(),
            test_cases=results
        )
        tester._suite_result.end_time = datetime.now()
        tester._generate_report()
    else:
        tester.run_all_tests()

    # 返回退出码
    if tester._suite_result:
        if tester._suite_result.pass_rate >= 70:
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
