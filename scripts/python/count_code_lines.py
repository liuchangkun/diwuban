"""
代码行数统计脚本

统计app/目录下所有Python文件的有效代码行数
排除注释、文档字符串和空行
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
import re


def count_code_lines(file_path: Path) -> Tuple[int, int, int]:
    """
    统计单个文件的代码行数
    
    Args:
        file_path: 文件路径
    
    Returns:
        (总行数, 有效代码行数, 注释行数)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"警告：无法读取文件 {file_path}: {e}")
        return 0, 0, 0
    
    lines = content.split('\n')
    total_lines = len(lines)
    code_lines = 0
    comment_lines = 0
    
    in_docstring = False
    docstring_delimiter = None
    
    for line in lines:
        stripped = line.strip()
        
        # 空行
        if not stripped:
            continue
        
        # 检查文档字符串开始/结束
        if '"""' in stripped or "'''" in stripped:
            if not in_docstring:
                # 开始文档字符串
                if '"""' in stripped:
                    docstring_delimiter = '"""'
                else:
                    docstring_delimiter = "'''"
                
                # 检查是否在同一行结束
                count = stripped.count(docstring_delimiter)
                if count >= 2:
                    # 单行文档字符串
                    comment_lines += 1
                    continue
                else:
                    in_docstring = True
                    comment_lines += 1
                    continue
            else:
                # 结束文档字符串
                if docstring_delimiter in stripped:
                    in_docstring = False
                    docstring_delimiter = None
                    comment_lines += 1
                    continue
        
        # 在文档字符串内
        if in_docstring:
            comment_lines += 1
            continue
        
        # 注释行
        if stripped.startswith('#'):
            comment_lines += 1
            continue
        
        # 有效代码行
        code_lines += 1
    
    return total_lines, code_lines, comment_lines


def scan_directory(directory: Path) -> Dict[str, Dict]:
    """
    递归扫描目录，统计所有Python文件
    
    Args:
        directory: 目录路径
    
    Returns:
        统计结果字典
    """
    results = {}
    
    for py_file in directory.rglob('*.py'):
        # 跳过__pycache__目录
        if '__pycache__' in str(py_file):
            continue
        
        total, code, comments = count_code_lines(py_file)
        
        # 相对路径
        rel_path = py_file.relative_to(directory.parent)
        
        results[str(rel_path)] = {
            'total': total,
            'code': code,
            'comments': comments,
            'blank': total - code - comments
        }
    
    return results


def print_statistics(results: Dict[str, Dict], base_dir: str):
    """
    打印统计结果
    
    Args:
        results: 统计结果
        base_dir: 基础目录名
    """
    print("\n" + "="*100)
    print(f"代码统计报告 - {base_dir}/")
    print("="*100)
    
    # 按子目录分组
    dir_stats = {}
    for file_path, stats in results.items():
        # 获取子目录
        parts = Path(file_path).parts
        if len(parts) > 1:
            subdir = parts[1]  # app/xxx
        else:
            subdir = "根目录"
        
        if subdir not in dir_stats:
            dir_stats[subdir] = {
                'files': 0,
                'total': 0,
                'code': 0,
                'comments': 0,
                'blank': 0
            }
        
        dir_stats[subdir]['files'] += 1
        dir_stats[subdir]['total'] += stats['total']
        dir_stats[subdir]['code'] += stats['code']
        dir_stats[subdir]['comments'] += stats['comments']
        dir_stats[subdir]['blank'] += stats['blank']
    
    # 打印子目录汇总
    print("\n📊 子目录汇总：")
    print("-"*100)
    print(f"{'子目录':<30} {'文件数':<10} {'总行数':<10} {'代码行数':<10} {'注释行数':<10} {'空行数':<10}")
    print("-"*100)
    
    total_files = 0
    total_total = 0
    total_code = 0
    total_comments = 0
    total_blank = 0
    
    for subdir in sorted(dir_stats.keys()):
        stats = dir_stats[subdir]
        print(f"{subdir:<30} {stats['files']:<10} {stats['total']:<10} "
              f"{stats['code']:<10} {stats['comments']:<10} {stats['blank']:<10}")
        
        total_files += stats['files']
        total_total += stats['total']
        total_code += stats['code']
        total_comments += stats['comments']
        total_blank += stats['blank']
    
    print("-"*100)
    print(f"{'总计':<30} {total_files:<10} {total_total:<10} "
          f"{total_code:<10} {total_comments:<10} {total_blank:<10}")
    print("-"*100)
    
    # 打印总体统计
    print("\n📈 总体统计：")
    print(f"  • 文件数量：{total_files} 个")
    print(f"  • 总代码行数：{total_code:,} 行")
    print(f"  • 总注释行数：{total_comments:,} 行")
    print(f"  • 总空行数：{total_blank:,} 行")
    print(f"  • 总行数：{total_total:,} 行")
    print(f"  • 平均每个文件：{total_code // total_files if total_files > 0 else 0} 行代码")
    print(f"  • 代码占比：{total_code / total_total * 100 if total_total > 0 else 0:.1f}%")
    print(f"  • 注释占比：{total_comments / total_total * 100 if total_total > 0 else 0:.1f}%")
    
    # 打印详细文件列表（按代码行数排序）
    print("\n📄 文件详情（按代码行数排序）：")
    print("-"*100)
    print(f"{'文件路径':<60} {'总行数':<10} {'代码行数':<10} {'注释行数':<10}")
    print("-"*100)
    
    sorted_files = sorted(results.items(), key=lambda x: x[1]['code'], reverse=True)
    
    for file_path, stats in sorted_files:
        print(f"{file_path:<60} {stats['total']:<10} {stats['code']:<10} {stats['comments']:<10}")
    
    print("-"*100)
    print(f"\n✅ 统计完成！共扫描 {total_files} 个Python文件")
    print("="*100)


def main():
    """主函数"""
    # 项目根目录
    project_root = Path(__file__).parent.parent.parent
    app_dir = project_root / "app"
    
    if not app_dir.exists():
        print(f"❌ 错误：找不到app目录：{app_dir}")
        return 1
    
    print(f"开始扫描目录：{app_dir}")
    
    # 扫描并统计
    results = scan_directory(app_dir)
    
    # 打印统计结果
    print_statistics(results, "app")
    
    return 0


if __name__ == "__main__":
    exit(main())

