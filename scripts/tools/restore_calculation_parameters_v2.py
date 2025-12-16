#!/usr/bin/env python3
"""
恢复 calculation_parameters 表的 v2 备份数据

用途：从 BackupManager 的 v2 备份文件中恢复 calculation_parameters 表数据
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.adapters.db.gateway import get_conn
from app.core.config.loader_new import load_settings
from app.services.ingest.prepare_dim.backup import BackupManager


def main():
    """恢复 calculation_parameters 表的 v2 备份"""
    print("=" * 80)
    print("恢复 calculation_parameters 表 v2 备份")
    print("=" * 80)
    
    # 初始化配置
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    
    # 创建 BackupManager
    backup_manager = BackupManager()
    
    # 检查 v2 备份文件
    backup_file = backup_manager.backup_dir / "calculation_parameters" / "calculation_parameters_v2_20251114_143152.sql"
    
    if not backup_file.exists():
        print(f"❌ v2 备份文件不存在: {backup_file}")
        return False
    
    print(f"\n📁 备份文件: {backup_file}")
    print(f"📄 文件大小: {backup_file.stat().st_size} bytes")
    print(f"📄 修改时间: {backup_file.stat().st_mtime}")
    
    # 恢复备份
    print("\n🔄 开始恢复 v2 备份...")
    
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 检查当前表数据
                cur.execute("SELECT COUNT(*) FROM calculation_parameters")
                current_count = cur.fetchone()[0]
                print(f"📊 当前表行数: {current_count}")
                
                # 清空表
                print("🗑️  清空表...")
                cur.execute("TRUNCATE TABLE calculation_parameters CASCADE")
                
                # 恢复 v2 备份
                result = backup_manager.restore_table(cur, "calculation_parameters", version=2)
                
                if result["status"] == "ok":
                    conn.commit()
                    
                    # 验证恢复结果
                    cur.execute("SELECT COUNT(*) FROM calculation_parameters")
                    restored_count = cur.fetchone()[0]
                    
                    print(f"\n✅ 恢复成功！")
                    print(f"📊 恢复版本: v{result['version']}")
                    print(f"📊 恢复行数: {restored_count}")
                    print(f"📄 备份文件: {result['file']}")
                    
                    # 显示部分数据
                    cur.execute("""
                        SELECT metric_key, method_id, param_name, param_value, station_id, device_id
                        FROM calculation_parameters
                        ORDER BY metric_key, method_id, param_name
                        LIMIT 20
                    """)
                    rows = cur.fetchall()
                    
                    print(f"\n📊 前20行数据：")
                    for row in rows:
                        station = row[4] or "全局"
                        device = row[5] or "全局"
                        print(f"  - {row[0]}.{row[1]}.{row[2]} = {row[3]} (站点={station}, 设备={device})")
                    
                    # 统计数据
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(DISTINCT metric_key) as metrics,
                            COUNT(DISTINCT method_id) as methods,
                            COUNT(DISTINCT param_name) as params,
                            SUM(CASE WHEN station_id IS NULL AND device_id IS NULL THEN 1 ELSE 0 END) as global_params,
                            SUM(CASE WHEN station_id IS NOT NULL AND device_id IS NULL THEN 1 ELSE 0 END) as station_params,
                            SUM(CASE WHEN device_id IS NOT NULL THEN 1 ELSE 0 END) as device_params
                        FROM calculation_parameters
                    """)
                    stats = cur.fetchone()
                    
                    print(f"\n📊 数据统计：")
                    print(f"  - 总行数: {stats[0]}")
                    print(f"  - 指标数: {stats[1]}")
                    print(f"  - 方法数: {stats[2]}")
                    print(f"  - 参数数: {stats[3]}")
                    print(f"  - 全局参数: {stats[4]}")
                    print(f"  - 站点参数: {stats[5]}")
                    print(f"  - 设备参数: {stats[6]}")
                    
                    return True
                else:
                    print(f"\n❌ 恢复失败: {result['message']}")
                    return False
                    
    except Exception as e:
        print(f"\n❌ 恢复失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

