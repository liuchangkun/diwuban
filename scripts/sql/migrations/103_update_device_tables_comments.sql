-- ============================================================================
-- 迁移脚本：更新 dim_device_capabilities 和 device_rated_params 表的注释
-- ============================================================================
-- 文件：scripts/sql/migrations/103_update_device_tables_comments.sql
-- 版本：v103
-- 日期：2025-11-08
-- 用途：为设备能力表和设备额定参数表添加完整的中文注释说明
-- 依赖：dim_device_capabilities 和 device_rated_params 表必须存在
-- ============================================================================

BEGIN;

-- ============================================================================
-- 第一部分：dim_device_capabilities 表注释
-- ============================================================================

-- 1.1 表级注释
COMMENT ON TABLE public.dim_device_capabilities IS '
设备物理能力边界配置表（A类手动配置表）

【核心定位】
  设备物理能力边界配置表，记录设备的硬件能力范围和约束条件。

【功能用途】
  为启停阈值建模、分工况建模和优化计算提供设备能力边界信息。
  定义设备的物理能力范围（如变频范围、额定功率/电流），用于约束和验证设备的运行参数。

【数据模型】
  • 模式：宽表模式（Wide Table）
  • 关系：与 dim_devices 表 1:1 关系（每个设备一行）
  • 字段：9个固定字段，结构简单，查询高效
  • 扩展性：较差，新增参数需要 ALTER TABLE

【使用场景】
  1. 优化计算
     - 读取 freq_min/max 用于频率优化约束
     - 读取 rated_power_kw 用于功率估算（相似律：P ∝ f³）
     - 代码位置：app/services/optimization.py

  2. 阈值设置
     - 读取 rated_current_a 用于设置电流启停阈值
     - 代码位置：app/services/rules/running_thresholds.py

  3. 能力验证
     - 读取 vfd_enabled 判断设备是否支持变频
     - 读取 freq_min/max 验证频率设置是否在允许范围内

  4. 效率计算
     - 读取 rated_power_kw 用于效率计算的边界验证
     - 代码位置：app/services/calculation/calculators/eff_simple_v1.py

【与 device_rated_params 的关系】
  • 功能互补：
    - dim_device_capabilities：能力边界（硬件约束）
    - device_rated_params：详细参数（铭牌参数）
  
  • 数据模型互补：
    - dim_device_capabilities：宽表模式（查询高效）
    - device_rated_params：EAV模式（灵活扩展）
  
  • 字段关系：
    - rated_power_kw：用于能力边界约束（优化计算）
    - device_rated_params.rated_power：用于详细参数记录（计算逻辑）
    - 两者用途不同，不是真正的冗余

【数据来源】
  • 自适应SQL脚本自动填充（scripts/sql/adaptive/02_device_related.sql）
  • 根据 dim_devices.pump_type 自动设置默认值：
    - 变频泵：vfd_enabled=TRUE, freq 25-50 Hz, 75kW, 150A
    - 软启泵：vfd_enabled=FALSE, freq 50 Hz, 55kW, 110A
  • 手动更新（设备硬件升级时）

【更新频率】
  极低（只有设备硬件变更时才更新）

【备份策略】
  • 分类：A类手动配置表（7个核心配置表之一）
  • 备份：每次 prepare_dim 执行时自动备份
  • 恢复：支持从备份文件恢复
  • 代码位置：app/services/ingest/prepare_dim/__init__.py

【使用示例】
  -- 查询设备的能力边界
  SELECT 
      device_id,
      vfd_enabled,
      freq_min,
      freq_max,
      rated_power_kw,
      rated_current_a
  FROM dim_device_capabilities
  WHERE device_id = 1;

  -- 查询所有变频设备
  SELECT d.name, dc.freq_min, dc.freq_max
  FROM dim_device_capabilities dc
  JOIN dim_devices d ON dc.device_id = d.id
  WHERE dc.vfd_enabled = TRUE;

  -- 验证频率是否在允许范围内
  SELECT 
      CASE 
          WHEN 45.0 BETWEEN freq_min AND freq_max THEN ''有效''
          ELSE ''超出范围''
      END AS validation_result
  FROM dim_device_capabilities
  WHERE device_id = 1;

【注意事项】
  1. 本表记录的是设备的物理能力边界，不是实时运行参数
  2. 更新本表时需要同时更新备份文件
  3. 不要在本表中存储详细的额定参数（使用 device_rated_params）
  4. 频率范围（freq_min/max）与额定频率（rated_frequency）是不同的概念
';

-- 1.2 字段注释
COMMENT ON COLUMN public.dim_device_capabilities.device_id IS '设备ID（主键，外键关联 dim_devices.id）
• 关系：与 dim_devices 表 1:1 关系
• 约束：NOT NULL, PRIMARY KEY, FOREIGN KEY ON DELETE CASCADE
• 说明：每个设备只有一行能力配置记录';

COMMENT ON COLUMN public.dim_device_capabilities.vfd_enabled IS '是否为变频驱动设备（VFD - Variable Frequency Drive）
• 数据类型：BOOLEAN
• 取值：TRUE=变频泵, FALSE=软启泵, NULL=未知
• 用途：
  - 判断设备是否支持变频调速
  - 优化计算时决定是否可以调整频率
  - 阈值设置时选择不同的策略
• 典型值：
  - 变频泵：TRUE（支持频率调节，freq_min ~ freq_max）
  - 软启泵：FALSE（固定频率50Hz，freq_min = freq_max = 50）
• 使用场景：
  - 优化计算：判断是否可以调整频率
  - 阈值设置：变频泵和软启泵使用不同的阈值策略';

COMMENT ON COLUMN public.dim_device_capabilities.freq_min IS '变频最小频率（Hz）
• 数据类型：DOUBLE PRECISION
• 单位：Hz（赫兹）
• 物理含义：设备变频器允许的最小运行频率（能力下限）
• 典型值：
  - 变频泵：25.0 Hz（允许降频运行）
  - 软启泵：50.0 Hz（固定频率，不可调）
• 用途：
  - 优化计算：作为频率优化的下限约束
  - 参数验证：验证频率设置是否在允许范围内
• 注意：
  - 这是能力边界，不是额定频率
  - 与 device_rated_params.rated_frequency（额定频率50Hz）是不同的概念
  - freq_min 是设备能力的下限，rated_frequency 是设计工作点';

COMMENT ON COLUMN public.dim_device_capabilities.freq_max IS '变频最大频率（Hz）
• 数据类型：DOUBLE PRECISION
• 单位：Hz（赫兹）
• 物理含义：设备变频器允许的最大运行频率（能力上限）
• 典型值：
  - 变频泵：50.0 Hz（额定频率）
  - 软启泵：50.0 Hz（固定频率，不可调）
• 用途：
  - 优化计算：作为频率优化的上限约束
  - 参数验证：验证频率设置是否在允许范围内
• 注意：
  - 通常设置为额定频率（50Hz），不建议超频运行
  - 超频运行可能导致设备损坏或效率下降';

COMMENT ON COLUMN public.dim_device_capabilities.rated_power_kw IS '额定功率（kW）
• 数据类型：DOUBLE PRECISION
• 单位：kW（千瓦）
• 物理含义：设备的额定电功率（铭牌功率）
• 典型值：
  - 变频泵：75.0 kW
  - 软启泵：55.0 kW
• 用途：
  - 优化计算：使用相似律估算不同频率下的功率（P ∝ f³）
  - 效率计算：作为功率计算的参考值
  - 能耗分析：作为能耗分析的基准
• 计算公式（相似律）：
  P_actual = P_rated × (f_actual / f_rated)³
  其中：P_actual = 实际功率 (kW)
       P_rated = 额定功率 (kW)
       f_actual = 实际频率 (Hz)
       f_rated = 额定频率 (Hz, 通常为50)
• 与 device_rated_params 的关系：
  - dim_device_capabilities.rated_power_kw：用于能力边界约束（优化计算）
  - device_rated_params.rated_power：用于详细参数记录（计算逻辑）
  - 两者用途不同，不是真正的冗余
• 代码位置：app/services/optimization.py (lines 241-274)';

COMMENT ON COLUMN public.dim_device_capabilities.rated_current_a IS '额定电流（A）
• 数据类型：DOUBLE PRECISION
• 单位：A（安培）
• 物理含义：设备的额定工作电流（铭牌电流）
• 典型值：
  - 变频泵：150.0 A
  - 软启泵：110.0 A
• 用途：
  - 阈值设置：用于设置电流启停阈值
  - 异常检测：判断电流是否超过额定值
  - 保护逻辑：作为过载保护的参考值
• 计算示例：
  - 启动阈值：rated_current_a × 0.1（10%额定电流）
  - 运行阈值：rated_current_a × 0.3（30%额定电流）
  - 过载阈值：rated_current_a × 1.2（120%额定电流）
• 代码位置：app/services/rules/running_thresholds.py';

COMMENT ON COLUMN public.dim_device_capabilities.remark IS '中文备注与口径说明
• 数据类型：TEXT
• 用途：记录数据来源、配置说明、特殊情况等
• 典型值：
  - "自适应SQL脚本生成 - 变频泵"
  - "自适应SQL脚本生成 - 软启泵"
  - "手动更新 - 设备硬件升级"
• 建议：
  - 记录数据来源（SQL脚本、手动更新、设备铭牌等）
  - 记录更新原因（硬件升级、参数调整等）
  - 记录特殊情况（非标准配置、临时调整等）';

COMMENT ON COLUMN public.dim_device_capabilities.updated_at IS '更新时间（自动）
• 数据类型：TIMESTAMPTZ
• 约束：NOT NULL, DEFAULT NOW()
• 说明：记录最后一次更新的时间戳，由数据库自动维护
• 用途：
  - 追踪数据变更历史
  - 数据一致性检查
  - 备份恢复验证';

COMMENT ON COLUMN public.dim_device_capabilities.updated_by IS '更新人（可空）
• 数据类型：TEXT
• 约束：NULL
• 说明：记录最后一次更新的操作人员
• 典型值：
  - "system"（系统自动更新）
  - "admin"（管理员手动更新）
  - "migration:103"（迁移脚本更新）
• 用途：
  - 追踪数据变更责任人
  - 审计和合规
  - 问题排查';

-- ============================================================================
-- 第二部分：device_rated_params 字段注释（表注释已经很完整，只更新字段注释）
-- ============================================================================

COMMENT ON COLUMN public.device_rated_params.id IS '自增主键（ID）
• 数据类型：BIGSERIAL
• 约束：PRIMARY KEY, NOT NULL
• 说明：每个参数记录的唯一标识符
• 用途：作为主键，保证每行记录的唯一性';

COMMENT ON COLUMN public.device_rated_params.device_id IS '设备ID（外键关联 dim_devices.id）
• 数据类型：BIGINT
• 约束：NULL（支持泵站级和全局级参数）
• 关系：FOREIGN KEY ON DELETE CASCADE
• 三级参数体系：
  - device_id IS NULL AND station_id IS NULL：全局级参数
  - device_id IS NULL AND station_id IS NOT NULL：泵站级参数
  - device_id IS NOT NULL：设备级参数
• 优先级：设备级 > 泵站级 > 全局级
• 说明：NULL 表示该参数不是设备级参数（可能是泵站级或全局级）';

COMMENT ON COLUMN public.device_rated_params.param_key IS '参数键（动态扩展）
• 数据类型：TEXT
• 约束：NOT NULL
• 说明：参数的唯一标识符，采用 snake_case 命名规范
• 参数分类：
  【额定运行参数】
    - rated_frequency：额定频率（Hz）
    - poles_pair：极对数（无量纲）
    - rated_efficiency：额定效率（无量纲）
    - rated_flow：额定流量（m³/h）
    - rated_head：额定扬程（m）
    - rated_power：额定功率（kW）
  【效率参数】
    - eta_motor：电机效率（无量纲）
    - eta_vfd：变频器效率（无量纲）
  【管道参数】
    - pipe_diameter：管道直径（m）
    - pipe_length：管道长度（m）
    - C_hazen：海曾-威廉系数（无量纲）
    - roughness_rel：相对粗糙度（无量纲）
• 扩展性：可随时添加新的参数键，无需修改表结构
• 唯一性：通过唯一索引保证 (station_id, device_id, param_key, effective_from) 的唯一性';

COMMENT ON COLUMN public.device_rated_params.value_numeric IS '数值型参数值
• 数据类型：NUMERIC
• 约束：NULL（与 value_text 二选一，至少一个非空）
• 说明：存储数值型参数（如频率、功率、效率等）
• 精度：NUMERIC 类型支持任意精度，避免浮点数精度问题
• 用途：大多数参数使用此字段存储（频率、功率、效率、流量、扬程等）
• 检查约束：chk_rated_value_presence（value_numeric 或 value_text 必须有一个非空）';

COMMENT ON COLUMN public.device_rated_params.value_text IS '文本型参数值
• 数据类型：TEXT
• 约束：NULL（与 value_numeric 二选一，至少一个非空）
• 说明：存储文本型参数（如设备型号、配置描述等）
• 用途：存储无法用数值表示的参数（如设备型号、配置描述、状态标识等）
• 检查约束：chk_rated_value_presence（value_numeric 或 value_text 必须有一个非空）';

COMMENT ON COLUMN public.device_rated_params.unit IS '参数单位
• 数据类型：TEXT
• 约束：NULL
• 说明：参数的物理单位（如 Hz、kW、m³/h、m 等）
• 典型值：
  - Hz：频率
  - kW：功率
  - A：电流
  - m³/h：流量
  - m：长度、扬程
  - NULL：无量纲参数（如效率、极对数、系数等）
• 用途：
  - 数据展示时显示单位
  - 单位转换和验证
  - 文档和报表生成';

COMMENT ON COLUMN public.device_rated_params.source IS '数据来源
• 数据类型：TEXT
• 约束：NULL
• 说明：记录参数的数据来源，用于追溯和审计
• 典型值：
  - "自适应SQL脚本生成"：由 scripts/sql/adaptive/02_device_related.sql 生成
  - "migration:071:station_level"：由迁移脚本 071 生成的泵站级参数
  - "设备铭牌"：从设备铭牌录入
  - "技术文档"：从技术文档录入
  - "现场测量"：从现场测量获得
  - "手动更新"：管理员手动更新
• 用途：
  - 数据质量评估
  - 问题排查
  - 审计和合规';

COMMENT ON COLUMN public.device_rated_params.effective_from IS '生效起始时间
• 数据类型：TIMESTAMPTZ
• 约束：NULL
• 说明：参数开始生效的时间戳
• 用途：
  - 支持参数历史版本管理
  - 查询特定时间点的参数值
  - 参数变更追溯
• 查询逻辑：
  - effective_from IS NULL：从最早时间开始生效
  - effective_from <= NOW()：当前时间已生效
• 唯一性：通过唯一索引保证 (station_id, device_id, param_key, effective_from) 的唯一性';

COMMENT ON COLUMN public.device_rated_params.effective_to IS '生效结束时间
• 数据类型：TIMESTAMPTZ
• 约束：NULL
• 说明：参数停止生效的时间戳
• 用途：
  - 支持参数历史版本管理
  - 标记过期参数
  - 参数变更追溯
• 查询逻辑：
  - effective_to IS NULL：永久有效（当前生效的参数）
  - effective_to > NOW()：当前时间仍有效
  - effective_to <= NOW()：已过期
• 典型查询：WHERE effective_to IS NULL OR effective_to > NOW()';

COMMENT ON COLUMN public.device_rated_params.created_at IS '创建时间
• 数据类型：TIMESTAMPTZ
• 约束：DEFAULT NOW()
• 说明：记录参数首次创建的时间戳，由数据库自动维护
• 用途：
  - 追踪参数创建历史
  - 数据审计
  - 问题排查';

COMMENT ON COLUMN public.device_rated_params.updated_at IS '更新时间
• 数据类型：TIMESTAMPTZ
• 约束：DEFAULT NOW()
• 说明：记录参数最后一次更新的时间戳，由数据库自动维护
• 用途：
  - 追踪参数变更历史
  - 数据一致性检查
  - 备份恢复验证';

COMMENT ON COLUMN public.device_rated_params.station_id IS '泵站ID（外键关联 dim_stations.id）
• 数据类型：BIGINT
• 约束：NULL（NULL 表示全局参数）
• 关系：FOREIGN KEY ON DELETE CASCADE
• 三级参数体系：
  - station_id IS NULL AND device_id IS NULL：全局级参数
  - station_id IS NOT NULL AND device_id IS NULL：泵站级参数
  - station_id IS NOT NULL AND device_id IS NOT NULL：设备级参数
• 优先级：设备级 > 泵站级 > 全局级
• 用途：
  - 支持泵站级参数配置（如管道参数、环境参数）
  - 实现参数继承机制
  - 简化参数管理（泵站内设备共享参数）
• 迁移历史：由迁移脚本 071 添加，支持三级参数体系';

COMMIT;

-- ============================================================================
-- 迁移完成
-- ============================================================================
-- 说明：
--   1. 已为 dim_device_capabilities 表添加完整的表注释和字段注释
--   2. 已为 device_rated_params 表的所有字段添加详细注释
--   3. 注释包含：数据类型、约束、物理含义、典型值、用途、使用场景等
--   4. 注释符合项目的数据库规范（中文注释、详细说明）
-- ============================================================================

