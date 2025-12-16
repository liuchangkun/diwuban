"""
日志字段中文化工具

功能：
1. 批量替换日志中 extra_data 字典的英文键名为中文
2. 保持代码变量名不变，只修改日志输出
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Tuple

# 英文→中文映射表
FIELD_TRANSLATIONS = {
    'autocommit': '自动提交',
    'autocommit_before': '自动提交（修改前）',
    'autocommit_after': '自动提交（修改后）',
    'autocommit_original': '自动提交（原始）',
    'autocommit_current': '自动提交（当前）',
    'available_columns': '可用列',
    'avg_duration_per_batch': '平均每批耗时',
    'avg_duration_per_batch_ms': '平均每批耗时（毫秒）',
    'avg_duration_per_batch_seconds': '平均每批耗时（秒）',
    'avg_torque': '平均扭矩',
    'batch_size': '批次大小',
    'calc_duration_ms': '计算耗时（毫秒）',
    'calculated_rows': '计算行数',
    'columns': '列名',
    'config_path': '配置路径',
    'count_after_insert': '插入后数量',
    'count_in_transaction': '事务内数量',
    'current_device_rows': '当前设备行数',
    'data_rows': '数据行数',
    'device': '设备',
    'device_id': '设备ID',
    'device_name': '设备名称',
    'device_running': '设备运行状态',
    'device_type': '设备类型',
    'devices_count': '设备数量',
    'duration_hours': '持续时长（小时）',
    'duration_ms': '耗时（毫秒）',
    'duration_s': '耗时（秒）',
    'enable_i': '启用电流检测',
    'end_ts': '结束时间戳',
    'end_utc': '结束时间（UTC）',
    'ensure_rows': '确保行数',
    'file_path': '文件路径',
    'files_failed': '失败文件数',
    'files_succeeded': '成功文件数',
    'files_total': '文件总数',
    'filter_ratio': '过滤比例',
    'filtered_rows': '过滤后行数',
    'final_count': '最终数量',
    'final_rows': '最终行数',
    'function': '函数',
    'has_pump_active_power': '有泵有功功率数据',
    'has_pump_speed': '有泵转速数据',
    'i_off': '电流关闭阈值',
    'i_on': '电流开启阈值',
    'inserted_rows': '插入行数',
    'loaded_rows': '加载行数',
    'max_torque': '最大扭矩',
    'method': '方法',
    'method_id': '方法ID',
    'metrics_count': '指标数量',
    'min_torque': '最小扭矩',
    'metric_key': '指标键',
    'original_count': '原始数量',
    'original_rows': '原始行数',
    'other_devices_count': '其他设备数量',
    'params': '参数',
    'phase': '阶段',
    'proc': '存储过程',
    'quality_code': '质量代码',
    'quality_code_distribution': '质量代码分布',
    'query_duration_ms': '查询耗时（毫秒）',
    'reason': '原因',
    'remaining_count': '剩余数量',
    'removed_nan': '移除NaN数量',
    'removed_negative': '移除负值数量',
    'removed_outlier': '移除异常值数量',
    'removed_stopped': '移除停机数量',
    'result_rows': '结果行数',
    'rows_loaded': '加载行数',
    'rows_read': '读取行数',
    'rows_rejected': '拒绝行数',
    'sample_count': '样本数量',
    'samples': '样本',
    'selected_method': '选择的方法',
    'sequence': '序号',
    'skip_shadow_rules': '跳过影子规则',
    'stage': '阶段',
    'start_ts': '开始时间戳',
    'start_utc': '开始时间（UTC）',
    'station': '泵站',
    'station_id': '泵站ID',
    'stations_count': '泵站数量',
    'steps_total': '总步骤数',
    'summary': '摘要',
    'tables': '表名',
    'task_id': '任务ID',
    'time_span_hours': '时间跨度（小时）',
    'total_batches': '总批次数',
    'total_devices': '设备总数',
    'total_duration_ms': '总耗时（毫秒）',
    'total_duration_seconds': '总耗时（秒）',
    'trace_id': '追踪ID',
    'transaction_status': '事务状态',
    'transaction_status_after': '事务状态（修改后）',
    'transaction_status_before': '事务状态（修改前）',
    'updated_by': '更新者',
    'validation_type': '验证类型',
    'valid_cross': '交叉验证通过',
    'valid_outlier': '异常值验证通过',
    'valid_range': '范围验证通过',
    'window_end_utc': '窗口结束时间（UTC）',
    'window_start_utc': '窗口开始时间（UTC）',
}


def localize_log_fields_in_file(file_path: Path) -> Tuple[int, List[str]]:
    """
    在单个文件中替换日志字段名
    
    Returns:
        (替换次数, 修改的行列表)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    replacements = 0
    modified_lines = []
    
    # 替换 extra_data 字典中的英文键名
    for en_field, cn_field in FIELD_TRANSLATIONS.items():
        # 匹配模式：'field_name': value 或 "field_name": value
        pattern = rf"(['\"]){en_field}\1\s*:"
        
        def replace_func(match):
            nonlocal replacements, modified_lines
            replacements += 1
            # 获取行号
            line_num = content[:match.start()].count('\n') + 1
            modified_lines.append(f"  Line {line_num}: '{en_field}' → '{cn_field}'")
            return f"'{cn_field}':"
        
        content = re.sub(pattern, replace_func, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return replacements, modified_lines


def main():
    """主函数"""
    print("=" * 80)
    print("日志字段中文化工具")
    print("=" * 80)
    
    # 目标目录
    target_dirs = [
        Path('app/services/calculation'),
        Path('app/adapters/db'),
    ]
    
    total_files = 0
    total_replacements = 0
    
    for target_dir in target_dirs:
        if not target_dir.exists():
            print(f"\n⚠️  目录不存在: {target_dir}")
            continue
        
        print(f"\n处理目录: {target_dir}")
        print("-" * 80)
        
        # 遍历所有 Python 文件
        for py_file in target_dir.rglob('*.py'):
            replacements, modified_lines = localize_log_fields_in_file(py_file)
            
            if replacements > 0:
                total_files += 1
                total_replacements += replacements
                try:
                    rel_path = py_file.relative_to(Path.cwd())
                except ValueError:
                    rel_path = py_file
                print(f"\n✅ {rel_path}")
                print(f"   替换次数: {replacements}")
                for line in modified_lines[:5]:  # 只显示前5个修改
                    print(line)
                if len(modified_lines) > 5:
                    print(f"   ... 还有 {len(modified_lines) - 5} 个修改")
    
    print("\n" + "=" * 80)
    print(f"✅ 完成！")
    print(f"   修改文件数: {total_files}")
    print(f"   总替换次数: {total_replacements}")
    print("=" * 80)


if __name__ == '__main__':
    main()

