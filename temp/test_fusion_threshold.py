#!/usr/bin/env python3
"""测试融合阈值配置功能"""

import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from sqlalchemy import text, create_engine

def main():
    """测试融合阈值功能"""
    print("=" * 80)
    print("测试融合阈值配置功能")
    print("=" * 80)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 创建数据库引擎
    db_url = settings.db.dsn_write or f"postgresql://{settings.db.user}:{settings.db.password}@{settings.db.host}/{settings.db.name}"
    engine = create_engine(db_url)
    
    # 测试参数
    device_id = 5
    start_ts = "2025-06-01 02:00:00"
    end_ts = "2025-06-01 04:00:00"
    
    print(f"\n📋 测试参数:")
    print(f"  - device_id: {device_id}")
    print(f"  - 时间范围: {start_ts} 到 {end_ts}")
    
    with engine.connect() as conn:
        # 1. 检查device_id=5的fusion_threshold配置
        print(f"\n" + "=" * 80)
        print(f"1. 检查device_id={device_id}的融合阈值配置")
        print("=" * 80)
        
        result = conn.execute(text("""
            SELECT device_id, fusion_threshold, use_weighted_fusion,
                   signal_weight_current, signal_weight_power, signal_weight_frequency
            FROM device_running_thresholds
            WHERE device_id = :device_id
        """), {"device_id": device_id})
        
        row = result.fetchone()
        if row:
            print(f"✅ 找到配置:")
            print(f"  - fusion_threshold: {row[1]}")
            print(f"  - use_weighted_fusion: {row[2]}")
            print(f"  - signal_weight_current: {row[3]}")
            print(f"  - signal_weight_power: {row[4]}")
            print(f"  - signal_weight_frequency: {row[5]}")
        else:
            print(f"❌ 未找到device_id={device_id}的配置")
            return False
        
        # 2. 调用fn_running_state_1s函数
        print(f"\n" + "=" * 80)
        print(f"2. 调用fn_running_state_1s函数")
        print("=" * 80)
        
        result = conn.execute(text("""
            SELECT ts_bucket, is_running, max_i, p, f, source
            FROM fn_running_state_1s(
                1,
                :device_id,
                CAST(:start_ts AS timestamptz),
                CAST(:end_ts AS timestamptz)
            )
            ORDER BY ts_bucket
            LIMIT 20
        """), {
            "device_id": device_id,
            "start_ts": start_ts,
            "end_ts": end_ts
        })
        
        rows = result.fetchall()
        if rows:
            print(f"✅ 函数调用成功，返回 {len(rows)} 条记录（显示前20条）:")
            print(f"\n{'时间':<20} {'运行状态':<10} {'电流(A)':<10} {'功率(kW)':<10} {'频率(Hz)':<10} {'数据源':<10}")
            print("-" * 80)
            for row in rows:
                ts_bucket, is_running, max_i, p, f, source = row
                status = "运行" if is_running else "停止"
                print(f"{ts_bucket} {status:<10} {max_i:<10.2f} {p:<10.2f} {f:<10.2f} {source:<10}")
        else:
            print(f"⚠️ 函数返回0条记录")
            return False
        
        # 3. 统计运行状态分布
        print(f"\n" + "=" * 80)
        print(f"3. 统计运行状态分布")
        print("=" * 80)
        
        result = conn.execute(text("""
            SELECT
                COUNT(*) AS total_records,
                SUM(CASE WHEN is_running THEN 1 ELSE 0 END) AS running_count,
                SUM(CASE WHEN NOT is_running THEN 1 ELSE 0 END) AS stopped_count,
                ROUND(100.0 * SUM(CASE WHEN is_running THEN 1 ELSE 0 END) / COUNT(*), 2) AS running_percentage
            FROM fn_running_state_1s(
                1,
                :device_id,
                CAST(:start_ts AS timestamptz),
                CAST(:end_ts AS timestamptz)
            )
        """), {
            "device_id": device_id,
            "start_ts": start_ts,
            "end_ts": end_ts
        })
        
        row = result.fetchone()
        if row:
            total, running, stopped, percentage = row
            print(f"✅ 统计结果:")
            print(f"  - 总记录数: {total}")
            print(f"  - 运行状态: {running} ({percentage}%)")
            print(f"  - 停止状态: {stopped} ({100-percentage}%)")

        # 4. 测试修改fusion_threshold后的效果
        print(f"\n" + "=" * 80)
        print(f"4. 测试修改fusion_threshold后的效果")
        print("=" * 80)

        # 保存原始值（从第一步查询的结果中获取）
        result_threshold = conn.execute(text("""
            SELECT fusion_threshold
            FROM device_running_thresholds
            WHERE device_id = :device_id
        """), {"device_id": device_id})
        row_threshold = result_threshold.fetchone()
        original_threshold = row_threshold[0] if row_threshold else 0.6
        
        # 修改为0.8（更严格）
        print(f"  修改fusion_threshold: {original_threshold} -> 0.8")
        conn.execute(text("""
            UPDATE device_running_thresholds
            SET fusion_threshold = 0.8
            WHERE device_id = :device_id
        """), {"device_id": device_id})
        conn.commit()
        
        # 重新调用函数
        result = conn.execute(text("""
            SELECT
                COUNT(*) AS total_records,
                SUM(CASE WHEN is_running THEN 1 ELSE 0 END) AS running_count,
                ROUND(100.0 * SUM(CASE WHEN is_running THEN 1 ELSE 0 END) / COUNT(*), 2) AS running_percentage
            FROM fn_running_state_1s(
                1,
                :device_id,
                CAST(:start_ts AS timestamptz),
                CAST(:end_ts AS timestamptz)
            )
        """), {
            "device_id": device_id,
            "start_ts": start_ts,
            "end_ts": end_ts
        })
        
        row = result.fetchone()
        if row:
            total, running, percentage = row
            print(f"✅ 修改后统计结果:")
            print(f"  - 总记录数: {total}")
            print(f"  - 运行状态: {running} ({percentage}%)")
            print(f"  - 预期: 运行比例应该降低（阈值更严格）")
        
        # 恢复原始值
        print(f"\n  恢复fusion_threshold: 0.8 -> {original_threshold}")
        conn.execute(text("""
            UPDATE device_running_thresholds
            SET fusion_threshold = :threshold
            WHERE device_id = :device_id
        """), {"device_id": device_id, "threshold": original_threshold})
        conn.commit()
        
        print(f"\n" + "=" * 80)
        print("✅ 所有测试完成")
        print("=" * 80)
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

