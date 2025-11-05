"""
深度代码质量检查脚本
用于研究模式下的全面代码审查
"""
import os
import re
from pathlib import Path
from typing import List, Tuple, Dict

def check_placeholders(directory: str) -> List[Tuple[str, int, str]]:
    """检查代码占位符 (TODO, FIXME, etc.)"""
    results = []
    patterns = [r'TODO', r'FIXME', r'HACK', r'XXX', r'TEMP', r'PLACEHOLDER']
    pattern = re.compile('|'.join(patterns), re.IGNORECASE)
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if pattern.search(line):
                                results.append((filepath, i, line.strip()))
                except Exception as e:
                    pass
    return results

def check_english_logs(directory: str) -> List[Tuple[str, int, str]]:
    """检查英文日志消息"""
    results = []
    log_pattern = re.compile(r'logger\.(info|debug|warning|error|critical)\s*\(')
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines, 1):
                            if log_pattern.search(line):
                                # 提取日志消息
                                match = re.search(r'["\']([^"\']+)["\']', line)
                                if match:
                                    msg = match.group(1)
                                    # 检查是否包含英文字母
                                    if re.search(r'[a-zA-Z]', msg):
                                        # 排除变量名和格式化字符串
                                        if not re.match(r'^[a-z_]+$', msg):  # 不是纯变量名
                                            results.append((filepath, i, line.strip()))
                except Exception as e:
                    pass
    return results

def check_sql_concatenation(directory: str) -> List[Tuple[str, int, str]]:
    """检查SQL字符串拼接"""
    results = []
    # 查找 SELECT/INSERT/UPDATE/DELETE + 字符串拼接
    pattern = re.compile(r'(SELECT|INSERT|UPDATE|DELETE).*\+', re.IGNORECASE)
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            if pattern.search(line):
                                results.append((filepath, i, line.strip()))
                except Exception as e:
                    pass
    return results

def check_file_sizes(directory: str, limit: int = 600) -> List[Tuple[str, int]]:
    """检查超过行数限制的文件"""
    results = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        if lines > limit:
                            results.append((filepath, lines))
                except Exception as e:
                    pass
    return sorted(results, key=lambda x: x[1], reverse=True)

def check_hardcoded_values(directory: str) -> Dict[str, List[Tuple[int, str]]]:
    """检查硬编码值"""
    results = {}
    # 常见的硬编码模式
    patterns = {
        '魔法数字': re.compile(r'\b(9\.80665|1000|3600|60|24|365)\b'),  # 常见物理常数
        '硬编码路径': re.compile(r'["\']/(home|usr|var|tmp|data)/'),
        '硬编码IP': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
    }
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for i, line in enumerate(f, 1):
                            for name, pattern in patterns.items():
                                if pattern.search(line):
                                    if filepath not in results:
                                        results[filepath] = []
                                    results[filepath].append((i, line.strip(), name))
                except Exception as e:
                    pass
    return results

def main():
    calc_dir = 'app/services/calculation'
    
    print("="*80)
    print("深度代码质量检查报告")
    print("="*80)
    
    # 1. 检查代码占位符
    print("\n### 1. 代码占位符检查 (TODO, FIXME, etc.)")
    print("-"*80)
    placeholders = check_placeholders(calc_dir)
    if placeholders:
        print(f"❌ 发现 {len(placeholders)} 个代码占位符（违反项目规则）:")
        for filepath, line_num, line in placeholders[:10]:
            rel_path = filepath.replace('app/services/calculation/', '')
            print(f"  {rel_path}:{line_num}")
            print(f"    {line}")
    else:
        print("✅ 未发现代码占位符")
    
    # 2. 检查英文日志
    print("\n### 2. 英文日志消息检查")
    print("-"*80)
    en_logs = check_english_logs(calc_dir)
    if en_logs:
        print(f"⚠️  发现 {len(en_logs)} 个可能的英文日志消息:")
        for filepath, line_num, line in en_logs[:10]:
            rel_path = filepath.replace('app/services/calculation/', '')
            print(f"  {rel_path}:{line_num}")
            print(f"    {line}")
    else:
        print("✅ 所有日志消息使用中文")
    
    # 3. 检查SQL拼接
    print("\n### 3. SQL字符串拼接检查")
    print("-"*80)
    sql_concat = check_sql_concatenation(calc_dir)
    if sql_concat:
        print(f"❌ 发现 {len(sql_concat)} 处SQL字符串拼接（违反项目规则）:")
        for filepath, line_num, line in sql_concat[:10]:
            rel_path = filepath.replace('app/services/calculation/', '')
            print(f"  {rel_path}:{line_num}")
            print(f"    {line}")
    else:
        print("✅ 所有SQL使用参数化查询")
    
    # 4. 检查文件大小
    print("\n### 4. 文件大小检查 (>600行)")
    print("-"*80)
    large_files = check_file_sizes(calc_dir, 600)
    if large_files:
        print(f"❌ 发现 {len(large_files)} 个超过600行的文件:")
        for filepath, lines in large_files:
            rel_path = filepath.replace('app/services/calculation/', '')
            print(f"  {rel_path}: {lines} 行")
    else:
        print("✅ 所有文件符合600行限制")
    
    # 5. 检查硬编码值
    print("\n### 5. 硬编码值检查")
    print("-"*80)
    hardcoded = check_hardcoded_values(calc_dir)
    if hardcoded:
        print(f"⚠️  发现 {sum(len(v) for v in hardcoded.values())} 处可能的硬编码值:")
        for filepath, items in list(hardcoded.items())[:5]:
            rel_path = filepath.replace('app/services/calculation/', '')
            print(f"  {rel_path}:")
            for line_num, line, pattern_name in items[:3]:
                print(f"    Line {line_num} ({pattern_name}): {line[:60]}...")
    else:
        print("✅ 未发现明显的硬编码值")
    
    print("\n" + "="*80)
    print("检查完成")
    print("="*80)

if __name__ == '__main__':
    main()

