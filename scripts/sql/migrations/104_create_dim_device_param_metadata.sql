-- ============================================================================
-- 迁移脚本：创建设备参数元数据表
-- ============================================================================
-- 文件：scripts/sql/migrations/104_create_dim_device_param_metadata.sql
-- 版本：v104
-- 日期：2025-11-08
-- 用途：创建设备参数元数据表，存储所有参数的详细说明和元数据
-- 依赖：无
-- ============================================================================

BEGIN;

-- ============================================================================
-- 第一部分：创建表结构
-- ============================================================================

-- 1.1 创建表
CREATE TABLE IF NOT EXISTS public.dim_device_param_metadata (
    param_key TEXT PRIMARY KEY,                    -- 参数键（唯一标识符）
    param_name_cn TEXT NOT NULL,                   -- 中文名称
    param_name_en TEXT NOT NULL,                   -- 英文名称
    category TEXT NOT NULL,                        -- 参数分类
    description TEXT,                              -- 简要描述
    physical_meaning TEXT,                         -- 物理含义
    formula TEXT,                                  -- 计算公式
    unit TEXT,                                     -- 单位
    typical_range TEXT,                            -- 典型范围
    example_value TEXT,                            -- 示例值
    usage TEXT,                                    -- 用途说明
    data_source TEXT,                              -- 数据来源
    code_location TEXT,                            -- 代码位置
    remark TEXT,                                   -- 备注
    created_at TIMESTAMPTZ DEFAULT NOW(),          -- 创建时间
    updated_at TIMESTAMPTZ DEFAULT NOW()           -- 更新时间
);

-- 1.2 添加表注释
COMMENT ON TABLE public.dim_device_param_metadata IS '
设备参数元数据表（参数字典）

【核心定位】
  设备参数的元数据字典表，存储所有参数的详细说明、物理含义、计算公式、典型值等信息。

【功能用途】
  1. 参数文档管理：集中管理所有参数的定义和说明
  2. UI展示：为前端提供参数的中英文名称、单位、说明等
  3. 数据验证：提供参数的典型范围，用于数据验证
  4. 文档生成：自动生成参数文档和API文档
  5. 开发参考：为开发人员提供参数的详细说明和使用示例

【数据模型】
  • 模式：维度表（Dimension Table）
  • 主键：param_key（参数键）
  • 关系：被 device_rated_params 表引用（逻辑外键）

【使用场景】
  1. 查询参数说明：SELECT * FROM dim_device_param_metadata WHERE param_key = ''rated_frequency''
  2. 按分类查询：SELECT * FROM dim_device_param_metadata WHERE category = ''额定运行参数''
  3. 生成文档：导出所有参数的说明生成文档
  4. UI展示：为前端提供参数的元数据

【维护策略】
  • 新增参数：添加新的参数键和说明
  • 更新说明：修改参数的描述、公式、典型值等
  • 版本管理：通过 updated_at 字段追踪变更历史
';

-- 1.3 添加字段注释
COMMENT ON COLUMN public.dim_device_param_metadata.param_key IS '参数键（主键）
• 约束：PRIMARY KEY, NOT NULL
• 命名规范：snake_case（如 rated_frequency）
• 说明：参数的唯一标识符，与 device_rated_params.param_key 对应';

COMMENT ON COLUMN public.dim_device_param_metadata.param_name_cn IS '中文名称
• 约束：NOT NULL
• 说明：参数的中文名称，用于UI展示和文档生成';

COMMENT ON COLUMN public.dim_device_param_metadata.param_name_en IS '英文名称
• 约束：NOT NULL
• 说明：参数的英文名称，用于国际化和技术文档';

COMMENT ON COLUMN public.dim_device_param_metadata.category IS '参数分类
• 约束：NOT NULL
• 取值：额定运行参数、效率参数、管道参数、环境参数等
• 说明：参数的功能分类，用于分组展示和查询';

COMMENT ON COLUMN public.dim_device_param_metadata.description IS '简要描述
• 说明：参数的简要说明（1-2句话）';

COMMENT ON COLUMN public.dim_device_param_metadata.physical_meaning IS '物理含义
• 说明：参数的物理含义和工程意义的详细解释';

COMMENT ON COLUMN public.dim_device_param_metadata.formula IS '计算公式
• 说明：与参数相关的计算公式（如适用）';

COMMENT ON COLUMN public.dim_device_param_metadata.unit IS '单位
• 说明：参数的物理单位（如 Hz、kW、m³/h、m 等）';

COMMENT ON COLUMN public.dim_device_param_metadata.typical_range IS '典型范围
• 说明：参数的典型取值范围（如 "25 ~ 50"、"0.60 ~ 0.85"）';

COMMENT ON COLUMN public.dim_device_param_metadata.example_value IS '示例值
• 说明：参数的典型示例值（如 "50.0"、"0.78"）';

COMMENT ON COLUMN public.dim_device_param_metadata.usage IS '用途说明
• 说明：参数在系统中的具体使用场景和用途';

COMMENT ON COLUMN public.dim_device_param_metadata.data_source IS '数据来源
• 说明：参数数据的典型来源（如设备铭牌、技术文档、现场测量等）';

COMMENT ON COLUMN public.dim_device_param_metadata.code_location IS '代码位置
• 说明：使用该参数的代码文件路径（如 app/services/calculation/orchestrator.py）';

COMMENT ON COLUMN public.dim_device_param_metadata.remark IS '备注
• 说明：其他需要说明的信息';

COMMENT ON COLUMN public.dim_device_param_metadata.created_at IS '创建时间
• 约束：DEFAULT NOW()
• 说明：记录创建的时间戳';

COMMENT ON COLUMN public.dim_device_param_metadata.updated_at IS '更新时间
• 约束：DEFAULT NOW()
• 说明：记录最后更新的时间戳';

-- 1.4 创建索引
CREATE INDEX IF NOT EXISTS idx_dim_device_param_metadata_category 
ON public.dim_device_param_metadata(category);

COMMENT ON INDEX public.idx_dim_device_param_metadata_category IS '参数分类索引，用于按分类查询参数';

-- ============================================================================
-- 第二部分：插入参数元数据
-- ============================================================================

-- 2.1 额定运行参数

-- rated_frequency（额定频率）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'rated_frequency',
    '额定频率',
    'Rated Frequency',
    '额定运行参数',
    '设备的额定运行频率，用于计算泵的实际转速',
    '设备的额定运行频率，反映电网频率标准。在中国为50Hz，在美国为60Hz。用于计算电机的同步转速和实际转速。',
    'n = (f / f_rated) × n_rated × (1 - slip)
其中：n = 转速 (rpm)
     f = 实际频率 (Hz)
     f_rated = 额定频率 (Hz)
     n_rated = 额定转速 (rpm)
     slip = 电机转差率 (无量纲)',
    'Hz',
    '50（中国）、60（美国）',
    '50.0',
    '作为转速计算的参考频率，反映电网频率标准。用于计算电机的同步转速和实际转速。',
    '设备铭牌',
    'app/services/calculation/orchestrator.py',
    '中国电网标准频率为50Hz'
);

-- poles_pair（极对数）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'poles_pair',
    '极对数',
    'Poles Pair',
    '额定运行参数',
    '电机的极对数，决定电机的同步转速',
    '电机定子绕组的极对数，决定电机的同步转速。极对数越多，同步转速越低。常见的极对数有2（对应1500rpm@50Hz）、3（对应1000rpm@50Hz）。',
    'n_sync = (60 × f) / p
其中：n_sync = 同步转速 (rpm)
     f = 频率 (Hz)
     p = 极对数 (无量纲)',
    '无量纲',
    '2（1500rpm）、3（1000rpm）、4（750rpm）',
    '2',
    '计算电机的同步转速，用于转速计算和效率分析。',
    '设备铭牌、技术文档',
    'app/services/calculation/orchestrator.py',
    '极对数 = 磁极数 / 2'
);

-- rated_efficiency（额定效率）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'rated_efficiency',
    '额定效率',
    'Rated Efficiency',
    '额定运行参数',
    '设备在额定工况下的效率',
    '设备在额定工况（额定流量、额定扬程、额定频率）下的总效率，反映设备将电能转换为水力能的能力。效率越高，能耗越低。',
    'eta = P_out / P_in = (rho × g × Q × H) / (P_e × 1000)
其中：eta = 效率 (无量纲)
     P_out = 输出功率 (W)
     P_in = 输入功率 (W)
     rho = 流体密度 (kg/m³)
     g = 重力加速度 (m/s²)
     Q = 流量 (m³/s)
     H = 扬程 (m)
     P_e = 电功率 (kW)',
    '无量纲',
    '0.60 ~ 0.85',
    '0.78',
    '作为效率计算的参考值，用于性能评估和能耗分析。',
    '设备铭牌、性能测试报告',
    'app/services/calculation/calculators/eff_simple_v1.py',
    '额定效率通常在额定工况点附近最高'
);

-- rated_flow（额定流量）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'rated_flow',
    '额定流量',
    'Rated Flow',
    '额定运行参数',
    '设备在额定工况下的流量',
    '设备在额定工况（额定扬程、额定频率）下的流量，是泵性能曲线上的设计工作点。流量反映泵的输送能力。',
    'Q = A × v
其中：Q = 流量 (m³/s)
     A = 管道截面积 (m²)
     v = 流速 (m/s)',
    'm³/h',
    '100 ~ 1000（根据泵型号）',
    '400.0',
    '作为流量计算的参考值，用于性能曲线拟合和工况点分析。',
    '设备铭牌、性能曲线',
    'app/services/calculation/orchestrator.py',
    '实际流量随频率和扬程变化'
);

-- rated_head（额定扬程）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'rated_head',
    '额定扬程',
    'Rated Head',
    '额定运行参数',
    '设备在额定工况下的扬程',
    '设备在额定工况（额定流量、额定频率）下的扬程，反映泵将液体提升的高度。扬程包括实际提升高度和管道阻力损失。',
    'H = (P2 - P1) / (rho × g) + (v2² - v1²) / (2 × g) + (z2 - z1)
其中：H = 扬程 (m)
     P1, P2 = 进出口压力 (Pa)
     v1, v2 = 进出口流速 (m/s)
     z1, z2 = 进出口高度 (m)
     rho = 流体密度 (kg/m³)
     g = 重力加速度 (m/s²)',
    'm',
    '20 ~ 100（根据泵型号）',
    '50.0',
    '作为扬程计算的参考值，用于性能曲线拟合和工况点分析。',
    '设备铭牌、性能曲线',
    'app/services/calculation/orchestrator.py',
    '实际扬程随流量和频率变化'
);

-- rated_power（额定功率）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'rated_power',
    '额定功率',
    'Rated Power',
    '额定运行参数',
    '设备的额定电功率',
    '设备在额定工况下的电功率，反映设备的能耗水平。功率与流量、扬程、效率相关。',
    'P = (rho × g × Q × H) / (eta × 1000)
其中：P = 功率 (kW)
     rho = 流体密度 (kg/m³)
     g = 重力加速度 (m/s²)
     Q = 流量 (m³/s)
     H = 扬程 (m)
     eta = 效率 (无量纲)',
    'kW',
    '50 ~ 500（根据泵型号）',
    '110.0',
    '作为功率计算的参考值，用于能耗分析和成本计算。',
    '设备铭牌',
    'app/services/calculation/orchestrator.py',
    '实际功率随工况点变化'
);

-- 2.2 效率参数

-- eta_motor（电机效率）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'eta_motor',
    '电机效率',
    'Motor Efficiency',
    '效率参数',
    '电机的效率，反映电能转换为机械能的效率',
    '电机将电能转换为机械能（轴功率）的效率。电机效率受负载率、转速、温度等因素影响。高效电机的效率通常在90%以上。',
    'eta_pump = eta_measured / (eta_motor × eta_vfd)
其中：eta_pump = 泵效率 (无量纲)
     eta_measured = 测量效率 (无量纲)
     eta_motor = 电机效率 (无量纲)
     eta_vfd = 变频器效率 (无量纲)',
    '无量纲',
    '0.85 ~ 0.95',
    '0.92',
    '用于效率计算，将电功率转换为轴功率。在效率分解中，将总效率分解为泵效率、电机效率和变频器效率。',
    '设备铭牌、技术文档',
    'app/services/calculation/calculators/eff_simple_v1.py',
    '电机效率随负载率变化，通常在75%-100%负载时效率最高'
);

-- eta_vfd（变频器效率）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'eta_vfd',
    '变频器效率',
    'VFD Efficiency',
    '效率参数',
    '变频器的效率，反映电能通过变频器的损耗',
    '变频器（Variable Frequency Drive）将工频交流电转换为可调频率交流电的效率。变频器效率较高，通常在95%以上。软启动器不调频，效率为100%。',
    'eta_total = eta_pump × eta_motor × eta_vfd
其中：eta_total = 总效率 (无量纲)
     eta_pump = 泵效率 (无量纲)
     eta_motor = 电机效率 (无量纲)
     eta_vfd = 变频器效率 (无量纲)',
    '无量纲',
    '0.95 ~ 0.98（变频泵）、1.00（软启泵）',
    '0.97',
    '用于效率计算，考虑变频器的能量损耗。变频泵需要考虑变频器损耗，软启泵不需要（eta_vfd=1.0）。',
    '变频器技术文档',
    'app/services/calculation/calculators/eff_simple_v1.py',
    '软启动器不调频，效率为1.0；变频器效率随负载和频率变化'
);

-- 2.3 管道参数

-- pipe_diameter（管道直径）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'pipe_diameter',
    '管道直径',
    'Pipe Diameter',
    '管道参数',
    '与设备连接的管道内径',
    '管道的内径，影响流速和水力损失。管道直径越大，流速越低，沿程损失越小。管道直径的选择需要平衡投资成本和运行成本。',
    'v = Q / A = Q / (π × D² / 4)
其中：v = 流速 (m/s)
     Q = 流量 (m³/s)
     A = 管道截面积 (m²)
     D = 管道直径 (m)',
    'm',
    '0.2 ~ 1.0',
    '0.5',
    '用于流速计算和水力损失计算。流速影响沿程损失和局部损失。',
    '设计图纸、现场测量',
    'app/services/calculation/orchestrator.py',
    '通常指内径，不是外径'
);

-- pipe_length（管道长度）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'pipe_length',
    '管道长度',
    'Pipe Length',
    '管道参数',
    '管道的总长度',
    '管道的总长度，包括直管段和弯管段的等效长度。管道长度影响沿程损失，长度越长，沿程损失越大。',
    'h_f = lambda × (L / D) × (v² / (2 × g))
其中：h_f = 沿程损失 (m)
     lambda = 摩擦系数 (无量纲)
     L = 管道长度 (m)
     D = 管道直径 (m)
     v = 流速 (m/s)
     g = 重力加速度 (m/s²)',
    'm',
    '10 ~ 1000',
    '100.0',
    '用于沿程损失计算。沿程损失与管道长度成正比。',
    '设计图纸、现场测量',
    'app/services/calculation/orchestrator.py',
    '包括直管段和弯管段的等效长度'
);

-- C_hazen（海曾-威廉系数）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'C_hazen',
    '海曾-威廉系数',
    'Hazen-Williams Coefficient',
    '管道参数',
    '管道粗糙度系数，用于海曾-威廉公式计算沿程损失',
    '海曾-威廉系数（C值）反映管道内壁的光滑程度。C值越大，管道越光滑，沿程损失越小。新管道C值较高（140），旧管道C值较低（100）。',
    'h_f = 10.67 × L × Q^1.852 / (C^1.852 × D^4.87)
其中：h_f = 沿程损失 (m)
     L = 管道长度 (m)
     Q = 流量 (m³/s)
     C = 海曾-威廉系数 (无量纲)
     D = 管道直径 (m)',
    '无量纲',
    '100 ~ 140（新管道140，旧管道100）',
    '120',
    '用于海曾-威廉公式计算沿程损失。适用于水在常温下的流动。',
    '管道材质手册、经验值',
    'app/services/calculation/orchestrator.py',
    '常见材质C值：铸铁管100-130，钢管120-140，塑料管140-150'
);

-- roughness_rel（相对粗糙度）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'roughness_rel',
    '相对粗糙度',
    'Relative Roughness',
    '管道参数',
    '管道内壁的相对粗糙度，用于达西-魏斯巴赫公式计算沿程损失',
    '相对粗糙度是绝对粗糙度与管道直径的比值，反映管道内壁的粗糙程度。相对粗糙度越大，摩擦系数越大，沿程损失越大。',
    'epsilon_rel = epsilon / D
其中：epsilon_rel = 相对粗糙度 (无量纲)
     epsilon = 绝对粗糙度 (m)
     D = 管道直径 (m)

摩擦系数计算（Colebrook-White公式）：
1 / sqrt(lambda) = -2 × log10(epsilon_rel / 3.7 + 2.51 / (Re × sqrt(lambda)))
其中：lambda = 摩擦系数 (无量纲)
     Re = 雷诺数 (无量纲)',
    '无量纲',
    '0.0001 ~ 0.01',
    '0.001',
    '用于达西-魏斯巴赫公式计算摩擦系数和沿程损失。适用于各种流体和流动状态。',
    '管道材质手册、经验值',
    'app/services/calculation/orchestrator.py',
    '常见材质绝对粗糙度：铸铁管0.25mm，钢管0.05mm，塑料管0.0015mm'
);

-- 2.4 环境参数

-- ambient_temp（环境温度）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'ambient_temp',
    '环境温度',
    'Ambient Temperature',
    '环境参数',
    '环境温度，影响流体密度和粘度',
    '环境温度影响流体的物理性质（密度、粘度、饱和蒸汽压等），进而影响泵的性能和效率。温度升高，密度降低，粘度降低。',
    'rho(T) = rho_0 × (1 - beta × (T - T_0))
其中：rho(T) = 温度T时的密度 (kg/m³)
     rho_0 = 参考温度T_0时的密度 (kg/m³)
     beta = 体积膨胀系数 (1/K)
     T = 温度 (°C)
     T_0 = 参考温度 (°C)',
    '°C',
    '-10 ~ 40',
    '20.0',
    '用于流体物性计算，影响密度、粘度等参数。在精确计算中需要考虑温度影响。',
    '现场测量、气象数据',
    'app/services/calculation/orchestrator.py',
    '水的密度在4°C时最大（1000 kg/m³）'
);

-- ambient_pressure（环境压力）
INSERT INTO public.dim_device_param_metadata (
    param_key, param_name_cn, param_name_en, category, description,
    physical_meaning, formula, unit, typical_range, example_value,
    usage, data_source, code_location, remark
) VALUES (
    'ambient_pressure',
    '环境压力',
    'Ambient Pressure',
    '环境参数',
    '环境大气压力，影响汽蚀余量计算',
    '环境大气压力影响泵的汽蚀余量（NPSH）计算。大气压力随海拔高度变化，海拔越高，大气压力越低，汽蚀风险越大。',
    'NPSH_a = (P_atm / (rho × g)) + h_s - h_f - (P_v / (rho × g))
其中：NPSH_a = 有效汽蚀余量 (m)
     P_atm = 大气压力 (Pa)
     rho = 流体密度 (kg/m³)
     g = 重力加速度 (m/s²)
     h_s = 吸入液面高度 (m)
     h_f = 吸入管路损失 (m)
     P_v = 饱和蒸汽压 (Pa)',
    'kPa',
    '80 ~ 105（随海拔变化）',
    '101.325',
    '用于汽蚀余量计算，评估泵的汽蚀风险。海平面标准大气压为101.325 kPa。',
    '现场测量、气象数据',
    'app/services/calculation/orchestrator.py',
    '海拔每升高1000m，大气压降低约12 kPa'
);

-- ============================================================================
-- 第三部分：创建查询视图
-- ============================================================================

-- 3.1 创建参数分类统计视图
CREATE OR REPLACE VIEW public.v_param_metadata_summary AS
SELECT
    category AS 参数分类,
    COUNT(*) AS 参数数量,
    STRING_AGG(param_key, ', ' ORDER BY param_key) AS 参数列表
FROM public.dim_device_param_metadata
GROUP BY category
ORDER BY category;

COMMENT ON VIEW public.v_param_metadata_summary IS '参数元数据分类统计视图
用途：按分类统计参数数量和列表';

-- 3.2 创建参数完整信息视图（用于文档生成）
CREATE OR REPLACE VIEW public.v_param_metadata_full AS
SELECT
    param_key AS 参数键,
    param_name_cn AS 中文名称,
    param_name_en AS 英文名称,
    category AS 分类,
    description AS 描述,
    physical_meaning AS 物理含义,
    formula AS 计算公式,
    unit AS 单位,
    typical_range AS 典型范围,
    example_value AS 示例值,
    usage AS 用途,
    data_source AS 数据来源,
    code_location AS 代码位置,
    remark AS 备注
FROM public.dim_device_param_metadata
ORDER BY
    CASE category
        WHEN '额定运行参数' THEN 1
        WHEN '效率参数' THEN 2
        WHEN '管道参数' THEN 3
        WHEN '环境参数' THEN 4
        ELSE 5
    END,
    param_key;

COMMENT ON VIEW public.v_param_metadata_full IS '参数元数据完整信息视图
用途：用于文档生成和UI展示，按分类排序';

COMMIT;

-- ============================================================================
-- 迁移完成
-- ============================================================================
-- 说明：
--   1. 已创建 dim_device_param_metadata 表，包含16个字段
--   2. 已插入11个参数的详细元数据：
--      - 额定运行参数：6个（rated_frequency, poles_pair, rated_efficiency, rated_flow, rated_head, rated_power）
--      - 效率参数：2个（eta_motor, eta_vfd）
--      - 管道参数：4个（pipe_diameter, pipe_length, C_hazen, roughness_rel）
--      - 环境参数：2个（ambient_temp, ambient_pressure）
--   3. 已创建2个查询视图：
--      - v_param_metadata_summary：参数分类统计
--      - v_param_metadata_full：参数完整信息（用于文档生成）
--   4. 每个参数包含：中英文名称、分类、描述、物理含义、计算公式、单位、典型范围、示例值、用途、数据来源、代码位置、备注
--
-- 使用示例：
--   -- 查询所有参数
--   SELECT * FROM dim_device_param_metadata ORDER BY category, param_key;
--
--   -- 查询特定参数
--   SELECT * FROM dim_device_param_metadata WHERE param_key = 'rated_frequency';
--
--   -- 按分类查询
--   SELECT * FROM dim_device_param_metadata WHERE category = '额定运行参数';
--
--   -- 查询参数统计
--   SELECT * FROM v_param_metadata_summary;
--
--   -- 导出文档
--   SELECT * FROM v_param_metadata_full;
-- ============================================================================

