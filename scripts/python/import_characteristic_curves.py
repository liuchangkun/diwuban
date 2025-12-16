"""
导入水泵特性曲线数据

从CSV文件导入特性曲线数据到数据库。

CSV格式：
device_id,curve_type,speed,frequency,flow_rate,value,source

使用示例：
    python scripts/python/import_characteristic_curves.py scripts/data/sample_curves.csv
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db import get_connection, init_database
from app.core.config.loader_new import load_settings
from app.core.logging.setup import init_logging


def validate_row(row: Dict, line_num: int) -> List[str]:
    """
    验证CSV行数据
    
    Args:
        row: CSV行数据字典
        line_num: 行号
    
    Returns:
        错误列表（空列表表示无错误）
    """
    errors = []
    
    # 检查必需字段
    required_fields = ['device_id', 'curve_type', 'flow_rate', 'value']
    for field in required_fields:
        if field not in row or not row[field]:
            errors.append(f"行 {line_num}: 缺少必需字段 {field}")
    
    if errors:
        return errors
    
    # 验证curve_type
    if row['curve_type'] not in ['Q-H', 'Q-P', 'Q-eta']:
        errors.append(f"行 {line_num}: 无效的curve_type: {row['curve_type']}")
    
    # 验证数值
    try:
        device_id = int(row['device_id'])
        if device_id <= 0:
            errors.append(f"行 {line_num}: device_id必须为正整数")
    except ValueError:
        errors.append(f"行 {line_num}: device_id必须为整数")
    
    try:
        flow_rate = float(row['flow_rate'])
        if flow_rate < 0:
            errors.append(f"行 {line_num}: flow_rate不能为负数")
    except ValueError:
        errors.append(f"行 {line_num}: flow_rate必须为数字")
    
    try:
        value = float(row['value'])
        if value < 0:
            errors.append(f"行 {line_num}: value不能为负数")
    except ValueError:
        errors.append(f"行 {line_num}: value必须为数字")
    
    # 验证可选字段
    if row.get('speed'):
        try:
            speed = float(row['speed'])
            if speed <= 0:
                errors.append(f"行 {line_num}: speed必须为正数")
        except ValueError:
            errors.append(f"行 {line_num}: speed必须为数字")
    
    if row.get('frequency'):
        try:
            frequency = float(row['frequency'])
            if frequency <= 0:
                errors.append(f"行 {line_num}: frequency必须为正数")
        except ValueError:
            errors.append(f"行 {line_num}: frequency必须为数字")
    
    if row.get('source') and row['source'] not in ['manufacturer', 'measured', 'calibrated']:
        errors.append(f"行 {line_num}: 无效的source: {row['source']}")
    
    return errors


def import_curves_from_csv(csv_file: Path) -> Dict:
    """
    从CSV文件导入特性曲线数据
    
    Args:
        csv_file: CSV文件路径
    
    Returns:
        导入结果字典
    """
    print(f"\n读取CSV文件: {csv_file}")
    
    if not csv_file.exists():
        print(f"❌ 文件不存在: {csv_file}")
        return {'success': False, 'error': '文件不存在'}
    
    # 读取CSV
    rows = []
    all_errors = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for line_num, row in enumerate(reader, start=2):  # 从第2行开始（第1行是标题）
            # 验证行
            errors = validate_row(row, line_num)
            if errors:
                all_errors.extend(errors)
                continue
            
            rows.append(row)
    
    if all_errors:
        print(f"\n❌ CSV验证失败：")
        for error in all_errors:
            print(f"  {error}")
        return {'success': False, 'errors': all_errors}
    
    print(f"✅ CSV验证通过：{len(rows)} 行数据")
    
    # 导入到数据库
    print(f"\n导入数据到数据库...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 使用UPSERT语法
                upsert_query = """
                    INSERT INTO pump_characteristic_curves (
                        device_id, curve_type, speed, frequency, 
                        flow_rate, value, source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (device_id, curve_type, 
                                 COALESCE(speed, -1), 
                                 COALESCE(frequency, -1), 
                                 flow_rate)
                    DO UPDATE SET
                        value = EXCLUDED.value,
                        source = EXCLUDED.source,
                        updated_at = NOW()
                """
                
                inserted = 0
                updated = 0
                
                for row in rows:
                    device_id = int(row['device_id'])
                    curve_type = row['curve_type']
                    speed = float(row['speed']) if row.get('speed') else None
                    frequency = float(row['frequency']) if row.get('frequency') else None
                    flow_rate = float(row['flow_rate'])
                    value = float(row['value'])
                    source = row.get('source') or 'imported'
                    
                    cur.execute(
                        upsert_query,
                        (device_id, curve_type, speed, frequency, flow_rate, value, source)
                    )
                    
                    if cur.rowcount > 0:
                        inserted += 1
                
                conn.commit()
                
                print(f"✅ 导入成功：{inserted} 条记录")
                
                # 统计结果
                cur.execute("""
                    SELECT 
                        device_id,
                        curve_type,
                        COUNT(*) as point_count,
                        MIN(flow_rate) as min_flow,
                        MAX(flow_rate) as max_flow
                    FROM pump_characteristic_curves
                    GROUP BY device_id, curve_type
                    ORDER BY device_id, curve_type
                """)
                
                stats = cur.fetchall()
                
                print("\n数据统计：")
                print("-"*80)
                print(f"{'设备ID':<10} {'曲线类型':<12} {'数据点':<8} {'流量范围':<20}")
                print("-"*80)
                
                for row in stats:
                    device_id, curve_type, count, min_flow, max_flow = row
                    flow_range = f"{min_flow:.1f} - {max_flow:.1f}"
                    print(f"{device_id:<10} {curve_type:<12} {count:<8} {flow_range:<20}")
                
                print("-"*80)
                
                return {
                    'success': True,
                    'inserted': inserted,
                    'stats': stats
                }
    
    except Exception as e:
        print(f"\n❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


def main():
    """主函数"""
    print("="*80)
    print("导入水泵特性曲线数据")
    print("="*80)
    
    # 检查参数
    if len(sys.argv) < 2:
        print("\n用法：python import_characteristic_curves.py <csv_file>")
        print("\nCSV格式：")
        print("device_id,curve_type,speed,frequency,flow_rate,value,source")
        print("\n示例：")
        print("1,Q-H,1450,50,0,32.0,manufacturer")
        print("1,Q-H,1450,50,50,31.5,manufacturer")
        return 1
    
    csv_file = Path(sys.argv[1])
    
    # 初始化
    init_logging()
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    init_database(settings)
    
    # 导入数据
    result = import_curves_from_csv(csv_file)
    
    if result['success']:
        print("\n" + "="*80)
        print("导入完成")
        print("="*80)
        return 0
    else:
        print("\n" + "="*80)
        print("导入失败")
        print("="*80)
        return 1


if __name__ == "__main__":
    exit(main())

