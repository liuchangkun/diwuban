#!/usr/bin/env python3
"""
日志系统验证脚本：验证 P5 优化的诊断日志系统

用途：
1. 验证诊断日志是否正确记录
2. 验证日志内容完整性
3. 验证查询函数功能
4. 生成日志系统验证报告

使用方法：
    python scripts/test_diagnosis_log_validation.py --start "2025-11-06 14:00:00" --end "2025-11-06 16:00:00"
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime
import psycopg
from typing import Dict, List
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config.loader import load_settings


def query_diagnosis_logs(
    conn_str: str,
    start: str,
    end: str
) -> List[Dict]:
    """查询诊断日志"""
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT 
                        id,
                        created_at,
                        window_start,
                        window_end,
                        stage,
                        level,
                        diag_level,
                        message,
                        detail
                    FROM public.quality_diagnosis_log
                    WHERE window_start = %s::timestamptz
                      AND window_end = %s::timestamptz
                    ORDER BY created_at
                    """,
                    (start, end)
                )
                
                results = []
                for row in cur.fetchall():
                    results.append({
                        'id': row[0],
                        'created_at': row[1],
                        'window_start': row[2],
                        'window_end': row[3],
                        'stage': row[4],
                        'level': row[5],
                        'diag_level': row[6],
                        'message': row[7],
                        'detail': row[8]
                    })
                
                return results
                
    except Exception as e:
        print(f"❌ 查询诊断日志失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_query_functions(conn_str: str, start: str, end: str) -> Dict[str, bool]:
    """测试查询函数"""
    results = {}
    
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                # 测试函数1：fn_get_diagnosis_log
                try:
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM fn_get_diagnosis_log(NULL, 'INFO', NULL)
                        """
                    )
                    count = cur.fetchone()[0]
                    results['fn_get_diagnosis_log'] = True
                    print(f"✅ fn_get_diagnosis_log: 正常 (返回 {count} 行)")
                except Exception as e:
                    results['fn_get_diagnosis_log'] = False
                    print(f"❌ fn_get_diagnosis_log: 失败 - {e}")
                
                # 测试函数2：fn_get_diagnosis_log_by_device
                try:
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM fn_get_diagnosis_log_by_device(
                            1,
                            %s::timestamptz,
                            %s::timestamptz,
                            NULL
                        )
                        """,
                        (start, end)
                    )
                    count = cur.fetchone()[0]
                    results['fn_get_diagnosis_log_by_device'] = True
                    print(f"✅ fn_get_diagnosis_log_by_device: 正常 (返回 {count} 行)")
                except Exception as e:
                    results['fn_get_diagnosis_log_by_device'] = False
                    print(f"❌ fn_get_diagnosis_log_by_device: 失败 - {e}")
                
                # 测试函数3：fn_cleanup_diagnosis_log（不实际执行删除）
                try:
                    # 仅测试函数存在性，不实际删除
                    cur.execute(
                        """
                        SELECT proname 
                        FROM pg_proc 
                        WHERE proname = 'fn_cleanup_diagnosis_log'
                        """
                    )
                    exists = cur.fetchone() is not None
                    results['fn_cleanup_diagnosis_log'] = exists
                    if exists:
                        print(f"✅ fn_cleanup_diagnosis_log: 存在")
                    else:
                        print(f"❌ fn_cleanup_diagnosis_log: 不存在")
                except Exception as e:
                    results['fn_cleanup_diagnosis_log'] = False
                    print(f"❌ fn_cleanup_diagnosis_log: 失败 - {e}")
                
    except Exception as e:
        print(f"❌ 测试查询函数失败: {e}")
    
    return results


def verify_log_content(logs: List[Dict]) -> Dict[str, bool]:
    """验证日志内容完整性"""
    checks = {}
    
    # 检查1：是否有日志
    checks['has_logs'] = len(logs) > 0
    
    if not logs:
        return checks
    
    # 检查2：关键规则是否都有日志
    expected_stages = ['update_503', 'update_141', 'update_601', 'update_602']
    found_stages = set(log['stage'] for log in logs)
    
    for stage in expected_stages:
        checks[f'has_{stage}'] = stage in found_stages
    
    # 检查3：日志级别是否正确
    checks['correct_level'] = all(log['level'] == 'INFO' for log in logs)
    
    # 检查4：诊断级别是否正确
    checks['correct_diag_level'] = all(log['diag_level'] == 'normal' for log in logs)
    
    # 检查5：detail 字段是否有内容
    checks['has_detail'] = all(log['detail'] is not None for log in logs)
    
    # 检查6：detail 字段是否包含关键信息
    detail_keys_check = []
    for log in logs:
        if log['detail']:
            detail = log['detail']
            # 检查是否包含 rows_affected
            has_rows_affected = 'rows_affected' in detail
            detail_keys_check.append(has_rows_affected)
    
    checks['detail_has_rows_affected'] = all(detail_keys_check) if detail_keys_check else False
    
    return checks


def print_diagnosis_log_report(
    logs: List[Dict],
    query_functions_results: Dict[str, bool],
    content_checks: Dict[str, bool]
):
    """打印日志系统验证报告"""
    print("\n" + "="*80)
    print("日志系统验证报告")
    print("="*80)
    
    # 日志统计
    print(f"\n日志统计:")
    print("-"*80)
    print(f"总日志数: {len(logs)}")
    
    if logs:
        # 按阶段分组
        stage_counts = {}
        for log in logs:
            stage = log['stage']
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        print(f"\n按阶段分组:")
        for stage, count in sorted(stage_counts.items()):
            print(f"  {stage}: {count} 条")
    
    # 日志内容示例
    if logs:
        print(f"\n日志内容示例（前3条）:")
        print("-"*80)
        for i, log in enumerate(logs[:3], 1):
            print(f"\n日志 {i}:")
            print(f"  阶段: {log['stage']}")
            print(f"  级别: {log['level']}")
            print(f"  诊断级别: {log['diag_level']}")
            print(f"  消息: {log['message']}")
            if log['detail']:
                print(f"  详情: {json.dumps(log['detail'], indent=4, ensure_ascii=False)}")
    
    # 查询函数测试结果
    print(f"\n查询函数测试结果:")
    print("-"*80)
    for func_name, success in query_functions_results.items():
        status = "✅" if success else "❌"
        print(f"{status} {func_name}")
    
    # 内容完整性检查
    print(f"\n内容完整性检查:")
    print("-"*80)
    
    check_descriptions = {
        'has_logs': '存在日志记录',
        'has_update_503': '规则503有日志',
        'has_update_141': '规则141有日志',
        'has_update_601': '规则601有日志',
        'has_update_602': '规则602有日志',
        'correct_level': '日志级别正确(INFO)',
        'correct_diag_level': '诊断级别正确(normal)',
        'has_detail': 'detail字段有内容',
        'detail_has_rows_affected': 'detail包含rows_affected'
    }
    
    for check_name, result in content_checks.items():
        status = "✅" if result else "❌"
        description = check_descriptions.get(check_name, check_name)
        print(f"{status} {description}")
    
    # 总体结论
    print(f"\n总体结论:")
    print("-"*80)
    
    all_query_functions_ok = all(query_functions_results.values())
    all_content_checks_ok = all(content_checks.values())
    
    if all_query_functions_ok and all_content_checks_ok:
        print("✅ 日志系统验证通过")
    else:
        print("❌ 日志系统验证失败")
        if not all_query_functions_ok:
            print("  - 部分查询函数测试失败")
        if not all_content_checks_ok:
            print("  - 部分内容完整性检查失败")
    
    print("="*80)


def main():
    parser = argparse.ArgumentParser(description='日志系统验证脚本')
    parser.add_argument('--start', required=True, help='开始时间 (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True, help='结束时间 (YYYY-MM-DD HH:MM:SS)')
    
    args = parser.parse_args()
    
    # 加载配置
    config_dir = Path(__file__).parent.parent / "configs"
    settings = load_settings(config_dir)
    db_config = settings.db
    
    # 构建连接字符串
    conn_str = (
        f"host={db_config.host} "
        f"dbname={db_config.name} "
        f"user={db_config.user} "
        f"password={db_config.password}"
    )
    
    print(f"连接数据库: {db_config.name}@{db_config.host}")
    print(f"时间窗口: {args.start} ~ {args.end}")
    
    # 查询诊断日志
    print(f"\n查询诊断日志...")
    logs = query_diagnosis_logs(conn_str, args.start, args.end)
    
    if not logs:
        print("⚠️ 未找到诊断日志（可能时间窗口内未执行存储过程）")
    else:
        print(f"✅ 找到 {len(logs)} 条诊断日志")
    
    # 测试查询函数
    print(f"\n测试查询函数...")
    query_functions_results = test_query_functions(conn_str, args.start, args.end)
    
    # 验证日志内容
    print(f"\n验证日志内容...")
    content_checks = verify_log_content(logs)
    
    # 打印报告
    print_diagnosis_log_report(logs, query_functions_results, content_checks)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

