#!/usr/bin/env python3
"""
恢复 calculation_parameters 表的备份数据

用途：从 BackupManager 的备份文件中恢复 calculation_parameters 表数据
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
    """恢复 calculation_parameters 表"""
    print("=" * 80)
    print("恢复 calculation_parameters 表备份")
    print("=" * 80)
    
    # 初始化配置
    config_dir = project_root / "configs"
    settings = load_settings(config_dir)
    
    # 创建 BackupManager
    backup_manager = BackupManager()
    
    # 检查备份文件
    backup_dir = backup_manager.backup_dir / "calculation_parameters"
    if not backup_dir.exists():
        print(f"❌ 备份目录不存在: {backup_dir}")
        return False
    
    backup_files = sorted(
        backup_dir.glob("calculation_parameters_v*.sql"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not backup_files:
        print(f"❌ 没有找到备份文件: {backup_dir}")
        return False
    
    print(f"\n📁 备份目录: {backup_dir}")
    print(f"📄 找到 {len(backup_files)} 个备份文件")
    print(f"📄 最新备份: {backup_files[0].name}")
    print(f"📄 文件大小: {backup_files[0].stat().st_size} bytes")
    print(f"📄 修改时间: {backup_files[0].stat().st_mtime}")
    
    # 恢复备份
    print("\n🔄 开始恢复备份...")
    
    try:
        with get_conn(settings) as conn:
            with conn.cursor() as cur:
                # 检查当前表数据
                cur.execute("SELECT COUNT(*) FROM calculation_parameters")
                current_count = cur.fetchone()[0]
                print(f"📊 当前表行数: {current_count}")
                
                if current_count > 0:
                    print("⚠️  警告: 表中已有数据，恢复操作将覆盖现有数据")
                    response = input("是否继续？(y/n): ")
                    if response.lower() != 'y':
                        print("❌ 用户取消操作")
                        return False
                    
                    # 清空表
                    print("🗑️  清空表...")
                    cur.execute("TRUNCATE TABLE calculation_parameters CASCADE")
                
                # 恢复备份
                result = backup_manager.restore_table(cur, "calculation_parameters")
                
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
                        LIMIT 10
                    """)
                    rows = cur.fetchall()
                    
                    print("\n📊 前10行数据：")
                    for row in rows:
                        station = row[4] or "全局"
                        device = row[5] or "全局"
                        print(f"  - {row[0]}.{row[1]}.{row[2]} = {row[3]} (站点={station}, 设备={device})")
                    
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

