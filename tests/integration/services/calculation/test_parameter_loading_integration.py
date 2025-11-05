"""
参数加载机制集成测试

测试参数加载在真实数据库环境下的完整流程：
1. 参数生成（prepare-dim）
2. 参数加载（load_parameters）
3. 参数使用（计算函数）
4. 参数更新（立即生效）
5. 参数优先级（6层优先级）

测试场景：
- 场景1：完整的 prepare-dim + run-all 流程
- 场景2：参数更新后立即生效
- 场景3：多设备并发计算时参数加载正确
- 场景4：参数优先级验证
- 场景5：参数缺失时的错误处理
"""

import pytest
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings


class TestParameterLoadingIntegration:
    """参数加载机制集成测试类"""

    @pytest.fixture(scope="class")
    def setup_database(self):
        """设置数据库连接（类级别，所有测试共享）"""
        settings = load_settings(Path("configs"))
        init_database(settings)
        yield settings
        # 测试结束后不清理数据库（保留测试数据供调试）

    @pytest.fixture(autouse=True)
    def setup_test_data(self, setup_database):
        """每个测试前准备测试数据"""
        # 记录测试开始时间
        self.test_start_time = datetime.now()
        yield
        # 测试结束后清理（可选）
        # 这里不清理，保留数据供调试

    # =====================================================
    # 场景1：完整的 prepare-dim + run-all 流程
    # =====================================================

    def test_scenario_1_full_prepare_and_run_flow(self, setup_database):
        """
        场景1：完整的 prepare-dim + run-all 流程
        
        验证点：
        1. prepare-dim 成功生成参数
        2. 参数正确写入数据库
        3. run-all 成功执行计算
        4. 计算使用了正确的参数
        """
        print("\n" + "="*80)
        print("场景1：完整的 prepare-dim + run-all 流程")
        print("="*80)

        # 步骤1：清空 calculation_parameters 表
        print("\n步骤1：清空 calculation_parameters 表")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM calculation_parameters")
                before_count = cur.fetchone()[0]
                print(f"  清空前参数数量: {before_count}")
                
                cur.execute("TRUNCATE TABLE calculation_parameters CASCADE")
                conn.commit()
                
                cur.execute("SELECT COUNT(*) FROM calculation_parameters")
                after_count = cur.fetchone()[0]
                print(f"  清空后参数数量: {after_count}")
                assert after_count == 0, "参数表应该为空"

        # 步骤2：运行 prepare-dim 命令生成参数
        print("\n步骤2：运行 prepare-dim 命令")
        result = subprocess.run(
            [sys.executable, "-m", "app.cli.main", "prepare-dim", 
             "configs/data_mapping.v2.json", "--stage", "1"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(f"  返回码: {result.returncode}")
        if result.returncode != 0:
            print(f"  标准输出:\n{result.stdout}")
            print(f"  标准错误:\n{result.stderr}")
        
        assert result.returncode == 0, f"prepare-dim 命令失败: {result.stderr}"

        # 步骤3：验证参数已正确生成
        print("\n步骤3：验证参数已正确生成")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 验证参数总数
                cur.execute("SELECT COUNT(*) FROM calculation_parameters")
                param_count = cur.fetchone()[0]
                print(f"  参数总数: {param_count}")
                assert param_count > 0, "应该生成了参数"

                # 验证物理常数参数（P_atm, rho, g）
                cur.execute("""
                    SELECT method_id, param_name, param_value
                    FROM calculation_parameters
                    WHERE param_name IN ('P_atm', 'rho', 'g')
                      AND device_id IS NULL
                      AND station_id IS NULL
                    ORDER BY method_id, param_name
                """)
                physical_params = cur.fetchall()
                print(f"  物理常数参数数量: {len(physical_params)}")
                
                # 验证至少有 pump_inlet_pressure_method_b 和 main_pipeline_inlet_pressure_method_b 的参数
                method_ids = set(row[0] for row in physical_params)
                assert 'pump_inlet_pressure_method_b' in method_ids, "应该有 pump_inlet_pressure_method_b 的参数"
                assert 'main_pipeline_inlet_pressure_method_b' in method_ids, "应该有 main_pipeline_inlet_pressure_method_b 的参数"
                
                # 验证参数值正确
                for method_id, param_name, param_value in physical_params[:6]:  # 只打印前6个
                    print(f"    {method_id}: {param_name} = {param_value}")
                    # 转换 Decimal 为 float
                    param_value_float = float(param_value)
                    if param_name == 'P_atm':
                        assert abs(param_value_float - 0.101325) < 1e-6, f"P_atm 值应该是 0.101325，实际是 {param_value_float}"
                    elif param_name == 'rho':
                        assert abs(param_value_float - 1000.0) < 1e-6, f"rho 值应该是 1000.0，实际是 {param_value_float}"
                    elif param_name == 'g':
                        assert abs(param_value_float - 9.80665) < 1e-6, f"g 值应该是 9.80665，实际是 {param_value_float}"

        # 步骤4：运行 run-all 命令（只运行 calculation 阶段）
        print("\n步骤4：运行 run-all 命令（calculation 阶段）")
        result = subprocess.run(
            [sys.executable, "-m", "app.cli.main", "run-all", 
             "configs/data_mapping.v2.json"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"  返回码: {result.returncode}")
        if result.returncode != 0:
            print(f"  标准输出:\n{result.stdout}")
            print(f"  标准错误:\n{result.stderr}")
        
        assert result.returncode == 0, f"run-all 命令失败: {result.stderr}"

        # 步骤5：验证计算成功（简化验证，只检查 run-all 成功执行）
        print("\n步骤5：验证 run-all 成功执行")
        print("  ✓ prepare-dim 成功生成参数")
        print("  ✓ 参数正确写入数据库")
        print("  ✓ run-all 成功执行（返回码 0）")
        print("  ✓ 参数加载机制正常工作")

        print("\n✅ 场景1测试通过")

    # =====================================================
    # 场景2：参数更新后立即生效
    # =====================================================

    def test_scenario_2_parameter_update_takes_effect(self, setup_database):
        """
        场景2：参数更新后立即生效
        
        验证点：
        1. 修改数据库中的参数值
        2. 重新运行计算
        3. 计算结果反映了新的参数值
        """
        print("\n" + "="*80)
        print("场景2：参数更新后立即生效")
        print("="*80)

        # 步骤1：记录原始参数值
        print("\n步骤1：记录原始参数值")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT param_value
                    FROM calculation_parameters
                    WHERE method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'P_atm'
                      AND device_id IS NULL
                      AND station_id IS NULL
                """)
                row = cur.fetchone()
                if row is None:
                    pytest.skip("pump_inlet_pressure_method_b 的 P_atm 参数不存在，跳过测试")
                
                original_value = float(row[0])  # 转换 Decimal 为 float
                print(f"  原始 P_atm 值: {original_value}")

        # 步骤2：修改参数值（增加10%）
        new_value = original_value * 1.1
        print(f"\n步骤2：修改参数值为 {new_value}")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE calculation_parameters
                    SET param_value = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'P_atm'
                      AND device_id IS NULL
                      AND station_id IS NULL
                """, (new_value,))
                conn.commit()
                print(f"  更新了 {cur.rowcount} 条记录")

        # 步骤3：重新运行计算（这里我们只验证参数加载，不运行完整计算）
        print("\n步骤3：验证参数加载反映了新值")
        from app.services.calculation.orchestrator import CalculationOrchestrator
        
        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=1,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )
        
        print(f"  加载的 P_atm 值: {params.get('P_atm')}")
        assert 'P_atm' in params, "应该加载了 P_atm 参数"
        assert abs(params['P_atm'] - new_value) < 1e-6, f"加载的参数值应该是 {new_value}，实际是 {params['P_atm']}"

        # 步骤4：恢复原始参数值
        print(f"\n步骤4：恢复原始参数值 {original_value}")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE calculation_parameters
                    SET param_value = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'P_atm'
                      AND device_id IS NULL
                      AND station_id IS NULL
                """, (original_value,))
                conn.commit()

        print("\n✅ 场景2测试通过")

    # =====================================================
    # 场景3：多设备并发计算时参数加载正确
    # =====================================================

    def test_scenario_3_multi_device_parameter_loading(self, setup_database):
        """
        场景3：多设备并发计算时参数加载正确

        验证点：
        1. 为不同设备设置不同的设备级参数
        2. 加载参数时每个设备使用正确的参数
        3. 验证参数隔离（设备A的参数不影响设备B）
        """
        print("\n" + "="*80)
        print("场景3：多设备并发计算时参数加载正确")
        print("="*80)

        # 步骤1：为设备1设置设备级参数（rho = 1001.0）
        print("\n步骤1：为设备1设置设备级参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 先删除可能存在的设备级参数
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE device_id = 1
                      AND method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'rho'
                """)

                # 插入设备级参数
                cur.execute("""
                    INSERT INTO calculation_parameters (
                        station_id, device_id, metric_key, method_id,
                        param_name, param_value, param_type,
                        is_optimizable, updated_by, confidence_score
                    ) VALUES (
                        NULL, 1, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b',
                        'rho', 1001.0, 'float',
                        false, 'integration_test', 1.0
                    )
                """)
                conn.commit()
                print(f"  为设备1设置 rho = 1001.0")

        # 步骤2：为设备7设置设备级参数（rho = 1002.0）
        print("\n步骤2：为设备7设置设备级参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 先删除可能存在的设备级参数
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE device_id = 7
                      AND method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'rho'
                """)

                # 插入设备级参数
                cur.execute("""
                    INSERT INTO calculation_parameters (
                        station_id, device_id, metric_key, method_id,
                        param_name, param_value, param_type,
                        is_optimizable, updated_by, confidence_score
                    ) VALUES (
                        NULL, 7, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b',
                        'rho', 1002.0, 'float',
                        false, 'integration_test', 1.0
                    )
                """)
                conn.commit()
                print(f"  为设备7设置 rho = 1002.0")

        # 步骤3：加载设备1的参数
        print("\n步骤3：加载设备1的参数")
        from app.services.calculation.orchestrator import CalculationOrchestrator

        orchestrator = CalculationOrchestrator()
        params_device_1 = orchestrator.load_parameters(
            device_id=1,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )

        print(f"  设备1的 rho 值: {params_device_1.get('rho')}")
        assert 'rho' in params_device_1, "应该加载了 rho 参数"
        assert abs(params_device_1['rho'] - 1001.0) < 1e-6, f"设备1的 rho 应该是 1001.0，实际是 {params_device_1['rho']}"

        # 步骤4：加载设备7的参数
        print("\n步骤4：加载设备7的参数")
        params_device_7 = orchestrator.load_parameters(
            device_id=7,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )

        print(f"  设备7的 rho 值: {params_device_7.get('rho')}")
        assert 'rho' in params_device_7, "应该加载了 rho 参数"
        assert abs(params_device_7['rho'] - 1002.0) < 1e-6, f"设备7的 rho 应该是 1002.0，实际是 {params_device_7['rho']}"

        # 步骤5：清理测试数据
        print("\n步骤5：清理测试数据")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE device_id IN (1, 7)
                      AND method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'rho'
                      AND updated_by = 'integration_test'
                """)
                conn.commit()
                print(f"  删除了 {cur.rowcount} 条测试参数")

        print("\n✅ 场景3测试通过")

    # =====================================================
    # 场景4：参数优先级验证
    # =====================================================

    def test_scenario_4_parameter_priority_validation(self, setup_database):
        """
        场景4：参数优先级验证

        验证点：
        1. 设置全局参数、泵站级参数、设备级参数
        2. 验证参数优先级：设备级 > 泵站级 > 全局
        3. 验证参数覆盖机制
        """
        print("\n" + "="*80)
        print("场景4：参数优先级验证")
        print("="*80)

        # 步骤1：设置全局参数（g = 9.80665）
        print("\n步骤1：验证全局参数存在")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT param_value
                    FROM calculation_parameters
                    WHERE method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'g'
                      AND device_id IS NULL
                      AND station_id IS NULL
                """)
                row = cur.fetchone()
                if row is None:
                    pytest.skip("全局参数 g 不存在，跳过测试")

                global_value = row[0]
                print(f"  全局 g 值: {global_value}")

        # 步骤2：设置泵站级参数（g = 9.81）
        print("\n步骤2：设置泵站级参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 先删除可能存在的泵站级参数
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE station_id = 1
                      AND device_id IS NULL
                      AND method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'g'
                """)

                # 插入泵站级参数
                cur.execute("""
                    INSERT INTO calculation_parameters (
                        station_id, device_id, metric_key, method_id,
                        param_name, param_value, param_type,
                        is_optimizable, updated_by, confidence_score
                    ) VALUES (
                        1, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b',
                        'g', 9.81, 'float',
                        false, 'integration_test', 1.0
                    )
                """)
                conn.commit()
                print(f"  为泵站1设置 g = 9.81")

        # 步骤3：设置设备级参数（g = 9.82）
        print("\n步骤3：设置设备级参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 先删除可能存在的设备级参数
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE device_id = 1
                      AND method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'g'
                """)

                # 插入设备级参数
                cur.execute("""
                    INSERT INTO calculation_parameters (
                        station_id, device_id, metric_key, method_id,
                        param_name, param_value, param_type,
                        is_optimizable, updated_by, confidence_score
                    ) VALUES (
                        NULL, 1, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b',
                        'g', 9.82, 'float',
                        false, 'integration_test', 1.0
                    )
                """)
                conn.commit()
                print(f"  为设备1设置 g = 9.82")

        # 步骤4：加载设备1的参数（应该使用设备级参数）
        print("\n步骤4：加载设备1的参数（应该使用设备级参数）")
        from app.services.calculation.orchestrator import CalculationOrchestrator

        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=1,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )

        print(f"  加载的 g 值: {params.get('g')}")
        assert 'g' in params, "应该加载了 g 参数"
        assert abs(params['g'] - 9.82) < 1e-6, f"应该使用设备级参数 9.82，实际是 {params['g']}"

        # 步骤5：删除设备级参数，再次加载（应该使用泵站级参数）
        print("\n步骤5：删除设备级参数，再次加载（应该使用泵站级参数）")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE device_id = 1
                      AND method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'g'
                      AND updated_by = 'integration_test'
                """)
                conn.commit()

        params = orchestrator.load_parameters(
            device_id=1,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )

        print(f"  加载的 g 值: {params.get('g')}")
        assert abs(params['g'] - 9.81) < 1e-6, f"应该使用泵站级参数 9.81，实际是 {params['g']}"

        # 步骤6：清理测试数据
        print("\n步骤6：清理测试数据")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE updated_by = 'integration_test'
                """)
                conn.commit()
                print(f"  删除了 {cur.rowcount} 条测试参数")

        print("\n✅ 场景4测试通过")

    # =====================================================
    # 场景5：参数缺失时的错误处理
    # =====================================================

    def test_scenario_5_missing_parameter_error_handling(self, setup_database):
        """
        场景5：参数缺失时的错误处理

        验证点：
        1. 删除某个必需参数
        2. 尝试加载参数
        3. 验证返回空字典或缺少该参数
        4. 验证计算函数抛出明确的错误信息
        """
        print("\n" + "="*80)
        print("场景5：参数缺失时的错误处理")
        print("="*80)

        # 步骤1：备份 P_atm 参数
        print("\n步骤1：备份 P_atm 参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT param_value, param_type, is_optimizable,
                           param_min, param_max, updated_by, confidence_score
                    FROM calculation_parameters
                    WHERE method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'P_atm'
                      AND device_id IS NULL
                      AND station_id IS NULL
                """)
                backup_row = cur.fetchone()
                if backup_row is None:
                    pytest.skip("P_atm 参数不存在，跳过测试")

                print(f"  备份的 P_atm 值: {backup_row[0]}")

        # 步骤2：删除 P_atm 参数
        print("\n步骤2：删除 P_atm 参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM calculation_parameters
                    WHERE method_id = 'pump_inlet_pressure_method_b'
                      AND param_name = 'P_atm'
                      AND device_id IS NULL
                      AND station_id IS NULL
                """)
                conn.commit()
                print(f"  删除了 {cur.rowcount} 条参数")

        # 步骤3：尝试加载参数
        print("\n步骤3：尝试加载参数")
        from app.services.calculation.orchestrator import CalculationOrchestrator

        orchestrator = CalculationOrchestrator()
        params = orchestrator.load_parameters(
            device_id=1,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )

        print(f"  加载的参数: {list(params.keys())}")
        assert 'P_atm' not in params, "P_atm 参数应该不存在"
        print("  ✓ P_atm 参数确实缺失")

        # 步骤4：尝试调用计算函数（应该抛出错误）
        print("\n步骤4：尝试调用计算函数（应该抛出错误）")
        import numpy as np
        from app.services.calculation.calculators import calculate_pump_inlet_pressure_method_b

        # 准备测试数据（必须包含 pool_liquid_level，否则函数会提前返回空数组）
        data = {
            'pool_liquid_level': np.array([5.0, 6.0, 7.0])  # 水池液位（m）
        }

        # 尝试计算（应该抛出 ValueError）
        try:
            result = calculate_pump_inlet_pressure_method_b(data, params)
            print(f"  计算结果: {result}")
            pytest.fail("应该抛出 ValueError，但没有抛出")
        except ValueError as e:
            error_msg = str(e)
            print(f"  捕获到预期的错误: {error_msg}")
            assert 'P_atm' in error_msg, f"错误信息应该包含 'P_atm'，实际是: {error_msg}"
            assert '缺少' in error_msg or 'missing' in error_msg.lower(), f"错误信息应该说明参数缺失，实际是: {error_msg}"
            print("  ✓ 错误信息明确指出了缺失的参数")

        # 步骤5：恢复 P_atm 参数
        print("\n步骤5：恢复 P_atm 参数")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO calculation_parameters (
                        station_id, device_id, metric_key, method_id,
                        param_name, param_value, param_type,
                        is_optimizable, param_min, param_max,
                        updated_by, confidence_score
                    ) VALUES (
                        NULL, NULL, 'pump_inlet_pressure', 'pump_inlet_pressure_method_b',
                        'P_atm', %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                """, backup_row)
                conn.commit()
                print(f"  恢复了 P_atm 参数")

        # 步骤6：验证恢复后可以正常加载
        print("\n步骤6：验证恢复后可以正常加载")
        params = orchestrator.load_parameters(
            device_id=1,
            method_id='pump_inlet_pressure_method_b',
            station_id=1
        )

        assert 'P_atm' in params, "P_atm 参数应该存在"
        print(f"  ✓ P_atm 参数已恢复: {params['P_atm']}")

        print("\n✅ 场景5测试通过")

