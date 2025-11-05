#!/usr/bin/env python3
"""
代码影响范围分析脚本

用途：分析ID迁移对代码的影响范围
作者：AI
创建日期：2025-10-30
"""
import sys
from pathlib import Path
import re

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


def search_code_patterns():
    """搜索代码中的ID相关模式"""
    print("=" * 80)
    print("代码影响范围分析")
    print("=" * 80)
    print()
    
    patterns = {
        'hardcoded_station_id': r'\bstation_id\s*=\s*\d+',
        'hardcoded_device_id': r'\bdevice_id\s*=\s*\d+',
        'hardcoded_metric_id': r'\bmetric_id\s*=\s*\d+',
        'sequential_id_assumption': r'(MAX\(id\)|MIN\(id\)|id\s*\+\s*1|SERIAL|BIGSERIAL)',
        'upsert_station_call': r'_upsert_station\s*\(',
        'upsert_device_call': r'_upsert_device\s*\(',
        'dim_stations_id': r'dim_stations\.id',
        'dim_devices_id': r'dim_devices\.id',
        'dim_metric_config_id': r'dim_metric_config\.id',
    }
    
    results = {}
    
    # 搜索Python文件
    py_files = list(project_root.glob('app/**/*.py'))
    py_files.extend(project_root.glob('scripts/**/*.py'))
    
    # 搜索SQL文件
    sql_files = list(project_root.glob('scripts/**/*.sql'))
    
    all_files = py_files + sql_files
    
    print(f"搜索文件数量: {len(all_files)}")
    print()
    
    for pattern_name, pattern in patterns.items():
        results[pattern_name] = []
        
        for file_path in all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    
                    for match in matches:
                        # 获取匹配行号
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1].strip()
                        
                        results[pattern_name].append({
                            'file': str(file_path.relative_to(project_root)),
                            'line': line_num,
                            'content': line_content[:100]  # 限制长度
                        })
            except Exception as e:
                pass
    
    # 打印结果
    for pattern_name, matches in results.items():
        print(f"### {pattern_name}")
        print(f"匹配数量: {len(matches)}")
        
        if matches:
            # 按文件分组
            by_file = {}
            for match in matches:
                file = match['file']
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(match)
            
            for file, file_matches in sorted(by_file.items()):
                print(f"\n  📄 {file}")
                for match in file_matches[:5]:  # 只显示前5个匹配
                    print(f"     Line {match['line']}: {match['content']}")
                if len(file_matches) > 5:
                    print(f"     ... 还有 {len(file_matches) - 5} 个匹配")
        
        print()
    
    return results


def analyze_function_calls():
    """分析 _upsert_station 和 _upsert_device 的调用"""
    print("=" * 80)
    print("函数调用分析")
    print("=" * 80)
    print()
    
    # 查找 prepare_dim/__init__.py
    prepare_dim_file = project_root / "app" / "services" / "ingest" / "prepare_dim" / "__init__.py"
    
    if not prepare_dim_file.exists():
        print("❌ 未找到 prepare_dim/__init__.py")
        return
    
    with open(prepare_dim_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 _upsert_station 调用
    print("### _upsert_station 调用")
    station_calls = re.finditer(r'_upsert_station\s*\([^)]+\)', content)
    for match in station_calls:
        line_num = content[:match.start()].count('\n') + 1
        print(f"  Line {line_num}: {match.group()}")
    print()
    
    # 查找 _upsert_device 调用
    print("### _upsert_device 调用")
    device_calls = re.finditer(r'_upsert_device\s*\([^)]+\)', content)
    for match in device_calls:
        line_num = content[:match.start()].count('\n') + 1
        print(f"  Line {line_num}: {match.group()}")
    print()


def check_hardcoded_ids():
    """检查硬编码的ID值"""
    print("=" * 80)
    print("硬编码ID检查")
    print("=" * 80)
    print()
    
    # 检查temp目录中的测试脚本
    temp_dir = project_root / "temp"
    if temp_dir.exists():
        print("### temp目录中的硬编码ID")
        for py_file in temp_dir.glob("*.py"):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 查找硬编码的ID
                hardcoded = re.findall(r'(station_id|device_id|metric_id)\s*=\s*(\d+)', content)
                if hardcoded:
                    print(f"\n  📄 {py_file.name}")
                    for var, value in hardcoded:
                        print(f"     {var} = {value}")
    print()


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "代码影响范围分析" + " " * 37 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # 执行各项分析
    search_code_patterns()
    analyze_function_calls()
    check_hardcoded_ids()
    
    print("=" * 80)
    print("分析完成")
    print("=" * 80)


if __name__ == "__main__":
    main()

