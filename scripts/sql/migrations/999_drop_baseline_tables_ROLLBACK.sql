-- ============================================================================
-- Rollback Script: 999_drop_baseline_tables_ROLLBACK.sql
-- Description: 回滚基线表删除操作（从归档恢复）
-- Date: 2025-11-07
-- Usage: 如果需要恢复基线表，请按以下步骤操作：
--        1. 执行归档中的迁移脚本重建表结构
--        2. 恢复 Python 代码文件
--        3. 恢复 CLI 命令和自动化流程
-- ============================================================================

-- ⚠️ 警告：此脚本仅提供回滚指导，不能自动恢复所有内容
-- ⚠️ 完整恢复需要手动执行多个步骤

-- ============================================================================
-- 回滚步骤说明
-- ============================================================================

/*
步骤1：恢复数据库表结构
-----------------------
执行以下归档的迁移脚本（按顺序）：

1. _archive/baseline_feature_20251107/sql/004_create_metric_rule_auto_baseline.sql
   - 创建 metric_rule_auto_baseline 表

2. _archive/baseline_feature_20251107/sql/025_create_metric_rule_auto_baseline_shadow.sql
   - 创建 metric_rule_auto_baseline_shadow 表

3. _archive/baseline_feature_20251107/sql/009_create_sp_refresh_metric_rule_auto_baseline.sql
   - 创建 sp_refresh_metric_rule_auto_baseline 存储过程

4. _archive/baseline_feature_20251107/sql/009_create_sp_refresh_metric_rule_auto_baseline_win.sql
   - 创建 sp_refresh_metric_rule_auto_baseline_win 存储过程

5. _archive/baseline_feature_20251107/sql/069_alter_sp_refresh_metric_rule_auto_baseline_use_mv.sql
   - 更新存储过程使用物化视图

6. _archive/baseline_feature_20251107/sql/070_alter_sp_refresh_metric_rule_auto_baseline_win_use_mv.sql
   - 更新存储过程使用物化视图


步骤2：恢复 Python 代码
-----------------------
从归档恢复以下文件：

1. 复制 _archive/baseline_feature_20251107/code/auto_baseline.py
   到 app/services/rules/auto_baseline.py

2. 复制 _archive/baseline_feature_20251107/code/auto_baseline_b.py
   到 app/services/rules/auto_baseline_b.py


步骤3：恢复 CLI 命令
--------------------
在 app/cli/main.py 中：
- 查找 "baseline:auto:compute command removed (2025-11-07)" 注释
- 从归档的 CLI指令使用手册_原始版.md 中恢复命令代码


步骤4：恢复自动化流程
---------------------
在 app/services/run_all/refresh_all.py 中：
- 取消注释基线导入语句
- 从归档恢复基线计算步骤（步骤2和步骤3）


步骤5：恢复备份系统配置
-----------------------
在 app/services/ingest/prepare_dim/__init__.py 中：
- 取消注释 backup_tables 集合中的基线表
- 取消注释清空影子表代码
- 取消注释 rule_tables 列表中的基线表
- 取消注释 tables_to_backup 列表中的基线表
- 在 _generate_rule_tables 函数中：
  - 取消注释基线导入语句
  - 恢复 C1 步骤（影子baseline）
  - 恢复 C2 步骤（生产baseline）


步骤6：恢复文档
---------------
从归档恢复以下文档：
- CLI指令使用手册.md
- 数据表清单.md
- 存储过程清单.md
- 其他相关文档


步骤7：验证恢复
---------------
1. 运行测试确保代码无错误
2. 执行 baseline:auto:compute 命令测试功能
3. 检查数据库表是否正常工作
*/

-- ============================================================================
-- 快速验证脚本（检查当前状态）
-- ============================================================================

DO $$
DECLARE
    v_table_count INTEGER;
    v_proc_count INTEGER;
BEGIN
    -- 检查表是否存在
    SELECT COUNT(*) INTO v_table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN ('metric_rule_auto_baseline', 'metric_rule_auto_baseline_shadow');
    
    -- 检查存储过程是否存在
    SELECT COUNT(*) INTO v_proc_count
    FROM information_schema.routines
    WHERE routine_schema = 'api'
      AND routine_name IN ('sp_refresh_metric_rule_auto_baseline', 'sp_refresh_metric_rule_auto_baseline_win');
    
    RAISE NOTICE '========================================';
    RAISE NOTICE '当前状态检查：';
    RAISE NOTICE '  - 基线表数量: %', v_table_count;
    RAISE NOTICE '  - 存储过程数量: %', v_proc_count;
    
    IF v_table_count = 2 AND v_proc_count = 2 THEN
        RAISE NOTICE '  - 状态: ✓ 已恢复';
    ELSIF v_table_count = 0 AND v_proc_count = 0 THEN
        RAISE NOTICE '  - 状态: ✗ 已删除（需要恢复）';
    ELSE
        RAISE NOTICE '  - 状态: ⚠ 部分恢复（不一致）';
    END IF;
    RAISE NOTICE '========================================';
END $$;

