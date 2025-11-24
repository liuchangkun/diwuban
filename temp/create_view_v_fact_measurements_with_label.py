"""
创建 v_fact_measurements_with_label 视图

用途：为 fact_measurements 表添加组合描述性标识符视图
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader import load_settings
from app.adapters.db import get_conn


def create_view():
    """创建视图和索引"""
    settings = load_settings(project_root / "configs")
    
    # SQL语句
    sql = """
-- ============================================
-- 步骤1：创建优化索引
-- ============================================

-- 检查索引是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'fact_measurements' 
        AND indexname = 'idx_fm_station_device_metric'
    ) THEN
        CREATE INDEX idx_fm_station_device_metric 
        ON fact_measurements (station_id, device_id, metric_id);
        
        RAISE NOTICE '✅ 索引 idx_fm_station_device_metric 创建成功';
    ELSE
        RAISE NOTICE '⚠️  索引 idx_fm_station_device_metric 已存在，跳过创建';
    END IF;
END $$;

-- 添加索引注释
COMMENT ON INDEX idx_fm_station_device_metric IS '
优化 fact_measurements 与维度表的 JOIN 性能
用途：支持 v_fact_measurements_with_label 视图的高效查询
覆盖字段：(station_id, device_id, metric_id)
';

-- ============================================
-- 步骤2：创建视图
-- ============================================

-- 删除旧视图（如果存在）
DROP VIEW IF EXISTS v_fact_measurements_with_label;

-- 创建视图
CREATE VIEW v_fact_measurements_with_label AS
SELECT 
    -- 原始字段（保留所有 fact_measurements 的字段）
    fm.id,
    fm.station_id,
    fm.device_id,
    fm.metric_id,
    fm.ts_raw,
    fm.ts_bucket,
    fm.value,
    fm.source_hint,
    fm.inserted_at,
    
    -- 维度表字段（便于查询）
    ds.name AS station_name,
    dd.name AS device_name,
    dd.type AS device_type,
    dd.pump_type AS device_pump_type,
    dmc.metric_key,
    dmc.unit,
    dmc.unit_display AS metric_display,
    
    -- 组合描述性标识符（核心字段）
    ds.name || '-' || dd.name || '-' || dmc.unit_display AS display_label
    
FROM fact_measurements fm
JOIN dim_stations ds ON ds.id = fm.station_id
JOIN dim_devices dd ON dd.id = fm.device_id
JOIN dim_metric_config dmc ON dmc.id = fm.metric_id;

-- ============================================
-- 步骤3：添加注释
-- ============================================

-- 视图注释
COMMENT ON VIEW v_fact_measurements_with_label IS $DOC$
用途：事实测量表（带组合描述性标识符）

功能说明：
  在 fact_measurements 表的基础上，自动关联维度表并生成人类可读的组合标识符。
  
字段格式：
  display_label = {泵站名称}-{设备名称}-{指标名称}
  
示例值：
  - 二期供水泵房-二期供水泵房1#泵-泵变频器频率
  - 二期供水泵房-二期供水泵房2#泵-泵有功功率
  - 二期供水泵房-1#出厂水总管-压力
  
使用方法：
  -- 示例1：查询所有测量数据（带标识符）
  SELECT * FROM v_fact_measurements_with_label 
  WHERE ts_bucket >= '2025-10-01' AND ts_bucket < '2025-10-02'
  ORDER BY ts_bucket;
  
  -- 示例2：按组合标识符过滤
  SELECT * FROM v_fact_measurements_with_label 
  WHERE display_label LIKE '%1#泵%'
  ORDER BY ts_bucket DESC
  LIMIT 100;
  
  -- 示例3：按泵站和设备查询
  SELECT display_label, ts_bucket, value, unit
  FROM v_fact_measurements_with_label 
  WHERE station_name = '二期供水泵房'
    AND device_name LIKE '%1#泵%'
    AND ts_bucket >= NOW() - INTERVAL '1 hour'
  ORDER BY ts_bucket DESC;
  
  -- 示例4：统计每个设备的测量数据量
  SELECT display_label, COUNT(*) AS measurement_count
  FROM v_fact_measurements_with_label 
  WHERE ts_bucket >= NOW() - INTERVAL '1 day'
  GROUP BY display_label
  ORDER BY measurement_count DESC;
  
性能优化建议：
  1. 查询时必须包含时间范围过滤（利用 TimescaleDB 分区裁剪）
  2. 优先使用 station_id、device_id、metric_id 过滤（利用索引）
  3. 避免在 display_label 上使用 LIKE '%xxx%'（无法使用索引）
  4. 如果查询性能不足，考虑升级为物化视图
  
注意事项：
  - 此视图不占用额外存储空间
  - 维度表名称变化时，视图自动反映最新值
  - 不影响 fact_measurements 表的写入性能
  - 查询时会执行 3 个 JOIN，性能取决于索引和数据量
$DOC$;
"""
    
    try:
        with get_conn(settings) as conn:
            # 提交之前的事务
            try:
                conn.commit()
            except:
                pass
            
            # 设置自动提交模式
            conn.autocommit = True
            
            with conn.cursor() as cur:
                print("🔄 执行SQL...")
                cur.execute(sql)
                print("✅ 视图和索引创建成功")
        
        return True
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_view()
    sys.exit(0 if success else 1)

