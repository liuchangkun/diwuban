"""
分析 data_mapping.v2.json 配置文件

检查是否需要修改以支持缺失指标计算功能
"""
import json
import sys
from pathlib import Path
from collections import Counter

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    """分析配置文件"""
    print("=" * 80)
    print("分析 data_mapping.v2.json 配置文件")
    print("=" * 80)
    print()
    
    # 读取配置文件
    config_file = project_root / "configs" / "data_mapping.v2.json"
    if not config_file.exists():
        print(f"❌ 配置文件不存在: {config_file}")
        return 1
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"✅ 配置文件加载成功: {config_file}")
    print()
    
    # 收集所有metric_key
    all_metric_keys = []
    for station in config['stations']:
        station_name = station['name']
        for device in station['devices']:
            device_name = device['name']
            device_type = device.get('type', 'unknown')
            for metric in device.get('metrics', []):
                metric_key = metric['key']
                all_metric_keys.append({
                    'station': station_name,
                    'device': device_name,
                    'device_type': device_type,
                    'metric_key': metric_key
                })
    
    print(f"📊 统计信息:")
    print(f"   站点数量: {len(config['stations'])}")
    print(f"   设备数量: {sum(len(s['devices']) for s in config['stations'])}")
    print(f"   指标映射数量: {len(all_metric_keys)}")
    print()
    
    # 统计每个metric_key的出现次数
    metric_key_counts = Counter([m['metric_key'] for m in all_metric_keys])
    
    print(f"📋 配置文件中的所有唯一metric_key ({len(metric_key_counts)}个):")
    for metric_key, count in sorted(metric_key_counts.items()):
        print(f"   {metric_key}: {count}次")
    print()
    
    # 检查大小写不一致
    print("🔍 检查大小写不一致:")
    has_case_issue = False
    for metric_key in metric_key_counts.keys():
        if metric_key != metric_key.lower():
            print(f"   ⚠️  {metric_key} (应为 {metric_key.lower()})")
            has_case_issue = True
    
    if not has_case_issue:
        print("   ✅ 所有metric_key都是小写格式")
    print()
    
    # 检查计算功能需要的关键指标
    print("🔍 检查计算功能需要的关键指标:")
    required_metrics = {
        'pump_inlet_pressure': '泵进口压力（计算pump_head需要）',
        'pump_outlet_pressure': '泵出口压力（计算pump_head需要）',
        'main_pipeline_flow_rate': '总管流量（计算pump_flow_rate需要）',
        'pump_cumulative_flow': '泵累计流量（计算pump_flow_rate方法B需要）',
        'pump_frequency': '泵频率（计算pump_flow_rate需要）',
        'pump_active_power': '泵有功功率（计算pump_flow_rate需要）',
        'main_pipeline_outlet_pressure': '总管出口压力（计算pump_outlet_pressure方法B需要）',
        'pump_group_outlet_pressure': '泵组出口压力（计算pump_outlet_pressure方法D需要）',
    }
    
    for metric_key, description in required_metrics.items():
        if metric_key in metric_key_counts:
            print(f"   ✅ {metric_key}: 已配置 ({metric_key_counts[metric_key]}次) - {description}")
        else:
            print(f"   ❌ {metric_key}: 未配置 - {description}")
    print()
    
    # 检查是否有Main_pipeline类型的设备
    print("🔍 检查Main_pipeline类型的设备:")
    main_pipeline_devices = [
        m for m in all_metric_keys 
        if m['device_type'] == 'Main_pipeline'
    ]
    
    if main_pipeline_devices:
        print(f"   ✅ 找到 {len(set(m['device'] for m in main_pipeline_devices))} 个Main_pipeline设备:")
        for device_name in sorted(set(m['device'] for m in main_pipeline_devices)):
            device_metrics = [m['metric_key'] for m in main_pipeline_devices if m['device'] == device_name]
            print(f"      - {device_name}: {', '.join(device_metrics)}")
    else:
        print("   ⚠️  未找到Main_pipeline类型的设备")
    print()
    
    # 总结
    print("=" * 80)
    print("📊 分析结果总结")
    print("=" * 80)
    
    if not has_case_issue:
        print("✅ 配置文件中所有metric_key都是小写格式，无需修改")
    else:
        print("⚠️  配置文件中存在大小写不一致的metric_key，需要修改")
    
    print()
    print("📋 关键指标配置情况:")
    configured_count = sum(1 for k in required_metrics.keys() if k in metric_key_counts)
    print(f"   已配置: {configured_count}/{len(required_metrics)}")
    print(f"   未配置: {len(required_metrics) - configured_count}/{len(required_metrics)}")
    
    if configured_count == len(required_metrics):
        print("\n✅ 所有关键指标都已配置，配置文件无需修改")
    else:
        print("\n⚠️  部分关键指标未配置，但这是正常的：")
        print("   - pump_inlet_pressure 和 pump_outlet_pressure 通常需要额外的传感器")
        print("   - pump_cumulative_flow 可能不是所有设备都有")
        print("   - pump_group_outlet_pressure 是泵组级别的指标")
        print("\n💡 建议：")
        print("   1. 如果有这些指标的数据源，可以添加到配置文件中")
        print("   2. 如果没有，计算功能会自动降级到其他可用的计算方法")
    
    print("\n" + "=" * 80)
    print("✅ 分析完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

