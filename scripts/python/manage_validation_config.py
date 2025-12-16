"""
验证配置管理工具

功能：
1. 查看验证配置
2. 添加/更新验证配置
3. 删除验证配置
4. 启用/禁用验证规则
5. 测试验证配置
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def view_config(
    metric_key: Optional[str] = None,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None
):
    """查看验证配置"""
    print("\n" + "="*80)
    print("验证配置查看")
    print("="*80)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 构建查询
                conditions = ["is_enabled = TRUE"]
                params = []
                
                if metric_key:
                    conditions.append("metric_key = %s")
                    params.append(metric_key)
                
                if station_id is not None:
                    conditions.append("(station_id = %s OR station_id IS NULL)")
                    params.append(station_id)
                
                if device_id is not None:
                    conditions.append("(device_id = %s OR device_id IS NULL)")
                    params.append(device_id)
                
                query = f"""
                    SELECT 
                        id,
                        station_id,
                        device_id,
                        metric_key,
                        validator_type,
                        params,
                        priority,
                        is_enabled
                    FROM calculation_validation_config
                    WHERE {' AND '.join(conditions)}
                    ORDER BY metric_key, priority
                """
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                if not rows:
                    print("未找到匹配的配置")
                    return
                
                print(f"\n找到 {len(rows)} 条配置：\n")
                
                current_metric = None
                for row in rows:
                    id, station_id, device_id, metric_key, validator_type, params, priority, is_enabled = row
                    
                    if metric_key != current_metric:
                        if current_metric is not None:
                            print()
                        print(f"【{metric_key}】")
                        current_metric = metric_key
                    
                    level = "全局"
                    if device_id is not None:
                        level = f"设备{device_id}"
                    elif station_id is not None:
                        level = f"站点{station_id}"
                    
                    print(f"  ID: {id} | 级别: {level} | 类型: {validator_type} | 优先级: {priority}")
                    if params:
                        print(f"    参数: {json.dumps(params, ensure_ascii=False)}")
                
    except Exception as e:
        print(f"\n❌ 查看配置失败：{e}")
        import traceback
        traceback.print_exc()


def add_or_update_config(
    metric_key: str,
    validator_type: str,
    params: str,
    station_id: Optional[int] = None,
    device_id: Optional[int] = None,
    priority: int = 100,
    enabled: bool = True
):
    """添加或更新验证配置"""
    print("\n" + "="*80)
    print("添加/更新验证配置")
    print("="*80)
    
    try:
        # 解析参数
        params_dict = json.loads(params) if params else {}
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO calculation_validation_config (
                        station_id, device_id, metric_key, validator_type, 
                        params, is_enabled, priority
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT ON CONSTRAINT uq_validation_config
                    DO UPDATE SET
                        params = EXCLUDED.params,
                        is_enabled = EXCLUDED.is_enabled,
                        priority = EXCLUDED.priority,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """
                
                cur.execute(query, (
                    station_id, device_id, metric_key, validator_type,
                    json.dumps(params_dict), enabled, priority
                ))
                
                config_id = cur.fetchone()[0]
                conn.commit()
                
                print(f"\n✅ 配置已保存（ID: {config_id}）")
                print(f"   指标: {metric_key}")
                print(f"   验证器: {validator_type}")
                print(f"   参数: {json.dumps(params_dict, ensure_ascii=False)}")
                print(f"   优先级: {priority}")
                print(f"   启用: {enabled}")
                
    except json.JSONDecodeError as e:
        print(f"\n❌ 参数JSON格式错误：{e}")
    except Exception as e:
        print(f"\n❌ 保存配置失败：{e}")
        import traceback
        traceback.print_exc()


def delete_config(config_id: int):
    """删除验证配置"""
    print("\n" + "="*80)
    print("删除验证配置")
    print("="*80)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 先查询配置信息
                cur.execute("""
                    SELECT metric_key, validator_type
                    FROM calculation_validation_config
                    WHERE id = %s
                """, (config_id,))
                
                row = cur.fetchone()
                if not row:
                    print(f"\n❌ 未找到ID为 {config_id} 的配置")
                    return
                
                metric_key, validator_type = row
                
                # 删除配置
                cur.execute("""
                    DELETE FROM calculation_validation_config
                    WHERE id = %s
                """, (config_id,))
                
                conn.commit()
                
                print(f"\n✅ 配置已删除")
                print(f"   ID: {config_id}")
                print(f"   指标: {metric_key}")
                print(f"   验证器: {validator_type}")
                
    except Exception as e:
        print(f"\n❌ 删除配置失败：{e}")
        import traceback
        traceback.print_exc()


def toggle_config(config_id: int, enabled: bool):
    """启用/禁用验证配置"""
    action = "启用" if enabled else "禁用"
    print("\n" + "="*80)
    print(f"{action}验证配置")
    print("="*80)
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE calculation_validation_config
                    SET is_enabled = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING metric_key, validator_type
                """, (enabled, config_id))
                
                row = cur.fetchone()
                if not row:
                    print(f"\n❌ 未找到ID为 {config_id} 的配置")
                    return
                
                metric_key, validator_type = row
                conn.commit()
                
                print(f"\n✅ 配置已{action}")
                print(f"   ID: {config_id}")
                print(f"   指标: {metric_key}")
                print(f"   验证器: {validator_type}")
                
    except Exception as e:
        print(f"\n❌ {action}配置失败：{e}")
        import traceback
        traceback.print_exc()


def test_config(metric_key: str):
    """测试验证配置"""
    print("\n" + "="*80)
    print(f"测试验证配置：{metric_key}")
    print("="*80)
    
    try:
        from app.services.calculation.validator import PhysicsValidator
        import numpy as np
        
        validator = PhysicsValidator()
        
        # 获取配置
        configs = validator.get_config_for_metric(metric_key)
        
        if not configs:
            print(f"\n❌ 指标 {metric_key} 没有验证配置")
            return
        
        print(f"\n找到 {len(configs)} 个验证器：")
        for config in configs:
            print(f"  - {config['validator_type']} (优先级: {config['priority']})")
            if config['params']:
                print(f"    参数: {json.dumps(config['params'], ensure_ascii=False)}")
        
        # 生成测试数据
        test_values = np.array([50.0, 75.0, 100.0, -10.0, 150.0])
        print(f"\n测试数据: {test_values}")
        
        # 执行验证
        is_valid, mask, errors, warnings = validator.validate(
            metric_key, test_values, strict_mode=False
        )
        
        print(f"\n验证结果:")
        print(f"  全部通过: {is_valid}")
        print(f"  有效掩码: {mask}")
        print(f"  错误数: {len(errors)}")
        print(f"  警告数: {len(warnings)}")
        
        if errors:
            print(f"\n错误信息:")
            for err in errors:
                print(f"  - {err}")
        
        if warnings:
            print(f"\n警告信息:")
            for warn in warnings:
                print(f"  - {warn}")
        
        print(f"\n✅ 测试完成")
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="验证配置管理工具")
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # view命令
    view_parser = subparsers.add_parser('view', help='查看验证配置')
    view_parser.add_argument('--metric', help='指标键')
    view_parser.add_argument('--station-id', type=int, help='站点ID')
    view_parser.add_argument('--device-id', type=int, help='设备ID')
    
    # add命令
    add_parser = subparsers.add_parser('add', help='添加/更新验证配置')
    add_parser.add_argument('--metric', required=True, help='指标键')
    add_parser.add_argument('--type', required=True, help='验证器类型')
    add_parser.add_argument('--params', default='{}', help='参数（JSON格式）')
    add_parser.add_argument('--station-id', type=int, help='站点ID')
    add_parser.add_argument('--device-id', type=int, help='设备ID')
    add_parser.add_argument('--priority', type=int, default=100, help='优先级')
    add_parser.add_argument('--disabled', action='store_true', help='禁用')
    
    # delete命令
    delete_parser = subparsers.add_parser('delete', help='删除验证配置')
    delete_parser.add_argument('id', type=int, help='配置ID')
    
    # enable命令
    enable_parser = subparsers.add_parser('enable', help='启用验证配置')
    enable_parser.add_argument('id', type=int, help='配置ID')
    
    # disable命令
    disable_parser = subparsers.add_parser('disable', help='禁用验证配置')
    disable_parser.add_argument('id', type=int, help='配置ID')
    
    # test命令
    test_parser = subparsers.add_parser('test', help='测试验证配置')
    test_parser.add_argument('metric', help='指标键')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 执行命令
    if args.command == 'view':
        view_config(args.metric, args.station_id, args.device_id)
    elif args.command == 'add':
        add_or_update_config(
            args.metric, args.type, args.params,
            args.station_id, args.device_id, args.priority, not args.disabled
        )
    elif args.command == 'delete':
        delete_config(args.id)
    elif args.command == 'enable':
        toggle_config(args.id, True)
    elif args.command == 'disable':
        toggle_config(args.id, False)
    elif args.command == 'test':
        test_config(args.metric)
    
    return 0


if __name__ == "__main__":
    exit(main())

