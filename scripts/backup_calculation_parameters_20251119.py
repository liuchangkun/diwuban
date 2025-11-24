"""
备份 calculation_parameters 表

使用 BackupManager 进行版本化备份（prepare_dim 阶段1备份机制）

执行方式:
    python scripts/backup_calculation_parameters_20251119.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.ingest.prepare_dim.backup import BackupManager
from app.adapters.db.gateway import get_conn
from app.core.config.loader import load_settings

def main():
    """备份 calculation_parameters 表"""
    print("=" * 100)
    print("开始备份 calculation_parameters 表")
    print("=" * 100)
    
    # 加载配置
    settings = load_settings(Path("configs"))
    
    # 创建备份管理器
    backup_manager = BackupManager(
        backup_dir=Path("backups"),
        keep_versions=60
    )
    
    # 执行备份
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            try:
                # 备份 calculation_parameters 表
                tables_to_backup = ["calculation_parameters"]
                
                print(f"\n正在备份表: {', '.join(tables_to_backup)}")
                backup_result = backup_manager.backup_tables(cur, tables_to_backup)
                
                # 显示备份结果
                print("\n" + "=" * 100)
                print("备份结果:")
                print("=" * 100)
                
                for table_name, result in backup_result.items():
                    status = result["status"]
                    message = result["message"]
                    
                    if status == "ok":
                        version = result["version"]
                        rows = result["rows"]
                        file_path = result["file"]
                        print(f"\n✅ {table_name}:")
                        print(f"   状态: 成功")
                        print(f"   版本: v{version}")
                        print(f"   行数: {rows}")
                        print(f"   文件: {file_path}")
                    elif status == "skipped":
                        print(f"\n⏭️  {table_name}:")
                        print(f"   状态: 跳过")
                        print(f"   原因: {message}")
                    else:  # error
                        print(f"\n❌ {table_name}:")
                        print(f"   状态: 失败")
                        print(f"   错误: {message}")
                
                # 统计
                ok_count = sum(1 for r in backup_result.values() if r["status"] == "ok")
                skipped_count = sum(1 for r in backup_result.values() if r["status"] == "skipped")
                error_count = sum(1 for r in backup_result.values() if r["status"] == "error")
                
                print("\n" + "=" * 100)
                print(f"备份完成: 成功 {ok_count} 个, 跳过 {skipped_count} 个, 失败 {error_count} 个")
                print("=" * 100)
                
                if error_count > 0:
                    sys.exit(1)
                    
            except Exception as e:
                print(f"\n❌ 备份失败: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

if __name__ == "__main__":
    main()

